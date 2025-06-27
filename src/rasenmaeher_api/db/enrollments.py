"""Abstractions for enrollments"""

from typing import Dict, Any, Optional, AsyncGenerator, Union
import string
import secrets
import logging
import enum
import warnings
import uuid
import datetime

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlmodel import Field, select

from .base import ORMBaseModel
from .people import Person
from .errors import ForbiddenOperation, CallsignReserved, NotFound, Deleted, PoolInactive
from ..rmsettings import RMSettings
from .engine import EngineWrapper
from ..web.api.utils.csr_utils import verify_csr

LOGGER = logging.getLogger(__name__)
CODE_ALPHABET = string.ascii_uppercase + string.digits
CODE_MAX_ATTEMPTS = 100


def generate_code() -> str:
    """Generate a code"""
    settings = RMSettings.singleton()
    code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(settings.code_size))
    if settings.code_avoid_confusion:
        code = code.replace("0", "O").replace("1", "I")
    return code


class EnrollmentPool(ORMBaseModel, table=True):  # type: ignore[call-arg,misc]
    """Enrollment pools aka links, pk is UUID and comes from basemodel"""

    __tablename__ = "enrollmentpools"

    owner: uuid.UUID = Field(f"{ORMBaseModel.__table_args__['schema']}.users.pk", nullable=False)
    active: bool = Field(nullable=False, default=True)
    extra: Dict[str, Any] = Field(sa_type=JSONB, nullable=False, sa_column_kwargs={"server_default": "{}"})
    invitecode: str = Field(nullable=False, index=True, unique=True)

    @classmethod
    async def by_pk_or_invitecode(cls, inval: Union[str, uuid.UUID], allow_deleted: bool = False) -> "EnrollmentPool":
        """Get pool by pk or by invitecode"""
        try:
            return await cls.by_pk(inval, allow_deleted)
        except ValueError:
            return await cls.by_invitecode(str(inval), allow_deleted)

    async def create_enrollment(self, callsign: str, csr: Optional[str] = None) -> "Enrollment":
        """Create enrollment from this pool"""
        if not self.active:
            raise PoolInactive()
        if self.deleted:
            raise Deleted("Can't create enrollments on deleted pools")
        return await Enrollment.create_for_callsign(callsign, self, self.extra, csr)

    async def set_active(self, state: bool) -> "EnrollmentPool":
        """Set active and return refreshed object"""
        with EngineWrapper.get_session() as session:
            self.active = bool(state)
            session.add(self)
            session.commit()
            session.refresh(self)
            return self

    @classmethod
    async def list(
        cls,
        by_owner: Optional[Person] = None,
        include_deleted: bool = False,
    ) -> AsyncGenerator["EnrollmentPool", None]:
        """List pools, optionally by owner or including deleted pools"""
        with EngineWrapper.get_session() as session:
            statement = select(cls)
            if by_owner:
                statement = statement.where(cls.owner == by_owner.pk)
            if not include_deleted:
                statement = statement.where(
                    cls.deleted == None  # pylint: disable=C0121 ; # "is None" will create invalid query
                )
            results = session.exec(statement)
            for result in results:
                yield result

    @classmethod
    async def _generate_unused_code(cls) -> str:
        """Internal helper to generate a code that is free
        NOTE: This MUST ONLY be used inside a transaction for nothing is guaranteed"""
        attempt = 0
        while True:
            attempt += 1
            code = generate_code()
            try:
                await EnrollmentPool.by_invitecode(code)
            except NotFound:
                break
            if attempt > CODE_MAX_ATTEMPTS:
                raise RuntimeError("Can't find unused code")
        return code

    @classmethod
    async def create_for_owner(cls, person: Person, extra: Optional[Dict[str, Any]] = None) -> "EnrollmentPool":
        """Creates one for given owner"""
        with EngineWrapper.get_session() as session:
            code = await cls._generate_unused_code()
            obj = EnrollmentPool(
                invitecode=code,
                active=True,
                owner=person.pk,
                extra=extra,
            )
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return obj

    async def reset_invitecode(self) -> str:
        """Reset invitecode"""
        with EngineWrapper.get_session() as session:
            self.invitecode = await EnrollmentPool._generate_unused_code()
            session.add(self)
            session.commit()
            session.refresh(self)
            return self.invitecode

    @classmethod
    async def by_invitecode(cls, invitecode: str, allow_deleted: bool = False) -> "EnrollmentPool":
        """Get by invitecode"""
        with EngineWrapper.get_session() as session:
            statement = select(EnrollmentPool).where(EnrollmentPool.invitecode == invitecode)
            obj = session.exec(statement).first()
        if not obj:
            raise NotFound()
        if obj.deleted and not allow_deleted:
            raise Deleted()
        return obj


class EnrollmentState(enum.IntEnum):
    """Enrollment states"""

    PENDING = 0
    APPROVED = 1
    REJECTED = 2


class Enrollment(ORMBaseModel, table=True):  # type: ignore[call-arg,misc]
    """Enrollments, pk is UUID and comes from basemodel"""

    __tablename__ = "enrollments"

    approvecode: str = Field(nullable=False, index=True, unique=True)
    callsign: str = Field(nullable=False, index=True, unique=True)
    decided_on: datetime.datetime = Field(nullable=True, default=None)
    decided_by: uuid.UUID = Field(
        foreign_key=f"{ORMBaseModel.__table_args__['schema']}.users.pk", nullable=True, default=None
    )
    person: uuid.UUID = Field(
        foreign_key=f"{ORMBaseModel.__table_args__['schema']}.users.pk", nullable=True, default=None
    )
    pool: uuid.UUID = Field(
        foreign_key=f"{ORMBaseModel.__table_args__['schema']}.enrollmentpools.pk", nullable=True, default=None
    )
    state: int = Field(nullable=False, index=False, unique=False, default=EnrollmentState.PENDING)
    extra: Dict[str, Any] = Field(sa_type=JSONB, nullable=False, sa_column_kwargs={"server_default": "{}"})
    csr: Optional[str] = Field(default=None, nullable=True)

    @classmethod
    async def by_pk_or_callsign(cls, inval: Union[str, uuid.UUID]) -> "Enrollment":
        """Get enrollment by pk or by callsign"""
        try:
            return await cls.by_pk(inval)
        except ValueError:
            return await cls.by_callsign(str(inval))

    async def approve(self, approver: Person) -> Person:
        """Creates the person record, their certs etc"""
        with EngineWrapper.get_session() as session:
            person = await Person.create_with_cert(self.callsign, extra=self.extra, csrpem=self.csr)
            self.state = EnrollmentState.APPROVED
            self.decided_by = approver.pk
            self.decided_on = datetime.datetime.now(datetime.UTC)
            self.person = person.pk
            session.add(self)
            session.commit()
            session.refresh(self)
            return person

    async def reject(self, decider: Person) -> None:
        """Reject"""
        with EngineWrapper.get_session() as session:
            self.state = EnrollmentState.REJECTED
            self.decided_by = decider.pk
            self.decided_on = datetime.datetime.now(datetime.UTC)
            session.add(self)
            session.commit()
            session.refresh(self)

    @classmethod
    async def list(cls, by_pool: Optional[EnrollmentPool] = None) -> AsyncGenerator["Enrollment", None]:
        """List enrollments, optionally by pool (enrollment deletion is not allowed, they can only be rejected)"""
        with EngineWrapper.get_session() as session:
            statement = select(Enrollment)
            if by_pool:
                statement = statement.where(Enrollment.pool == by_pool.pk)
            results = session.exec(statement)
            for result in results:
                yield result

    @classmethod
    async def by_callsign(cls, callsign: str) -> "Enrollment":
        """Get by callsign"""
        with EngineWrapper.get_session() as session:
            statement = select(Enrollment).where(func.lower(Enrollment.callsign) == func.lower(callsign))
            obj = session.exec(statement).first()
        if not obj:
            raise NotFound()
        if obj.deleted:
            LOGGER.error("Got a deleted enrollment {}, this should not be possible".format(obj.pk))
            raise Deleted()  # This should *not* be happening
        return obj

    @classmethod
    async def by_approvecode(cls, code: str) -> "Enrollment":
        """Get by approvecode"""
        with EngineWrapper.get_session() as session:
            statement = select(Enrollment).where(Enrollment.approvecode == code)
            obj = session.exec(statement).first()
        if not obj:
            raise NotFound()
        if obj.deleted:
            LOGGER.error("Got a deleted enrollment {}, this should not be possible".format(obj.pk))
            raise Deleted()  # This should *not* be happening
        return obj

    @classmethod
    async def reset_approvecode4callsign(cls, callsign: str) -> str:
        """Reset approvecode code for callsign"""
        # FIXME: I doubt there really is much need for this unless the same get and call to reset
        #        is done in many places
        warnings.warn("deprecated", DeprecationWarning)
        obj = await Enrollment.by_callsign(callsign=callsign)
        return await obj.reset_approvecode()

    async def reset_approvecode(self) -> str:
        """Reset approvecode"""
        with EngineWrapper.get_session() as session:
            code = await Enrollment._generate_unused_code()
            self.approvecode = code
            session.add(self)
            session.commit()
            return code

    @classmethod
    async def _generate_unused_code(cls) -> str:
        """Internal helper to generate a code that is free
        NOTE: This MUST ONLY be used inside a transaction for nothing is guaranteed"""
        attempt = 0
        while True:
            attempt += 1
            code = generate_code()
            try:
                await Enrollment.by_approvecode(code)
            except NotFound:
                break
            if attempt > CODE_MAX_ATTEMPTS:
                raise RuntimeError("Can't find unused code")
        return code

    @classmethod
    async def create_for_callsign(
        cls,
        callsign: str,
        pool: Optional[EnrollmentPool] = None,
        extra: Optional[Dict[str, Any]] = None,
        csr: Optional[str] = None,
    ) -> "Enrollment":
        """Create a new one with random code for the callsign"""
        if callsign in RMSettings.singleton().valid_product_cns:
            raise CallsignReserved("Using product CNs as callsigns is forbidden")
        if csr and not verify_csr(csr, callsign):
            raise CallsignReserved("CSR CN must match callsign")
        with EngineWrapper.get_session() as session:
            try:
                await Enrollment.by_callsign(callsign)
                raise CallsignReserved()
            except NotFound:
                pass
            code = await cls._generate_unused_code()
            poolpk = None
            if pool:
                poolpk = pool.pk
            obj = Enrollment(
                approvecode=code,
                callsign=callsign,
                state=EnrollmentState.PENDING,
                extra=extra,
                pool=poolpk,
                csr=csr,
            )
            session.add(obj)
            session.commit()
            session.refresh(obj)
            return obj

    async def delete(self) -> bool:
        """Deletion of enrollments is not allowed"""
        raise ForbiddenOperation("Deletion of enrollments is not allowed")
