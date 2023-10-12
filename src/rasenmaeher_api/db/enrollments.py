"""Abstractions for enrollments"""
from typing import Self, Dict, cast, Any, Optional, AsyncGenerator, Union
import string
import secrets
import logging
import enum
import warnings
import uuid

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as saUUID
import sqlalchemy as sa

from .base import ORMBaseModel, utcnow, db
from .people import Person
from .errors import ForbiddenOperation, CallsignReserved, NotFound, Deleted, PoolInactive
from ..rmsettings import RMSettings

LOGGER = logging.getLogger(__name__)
CODE_CHAR_COUNT = 8  # TODO: Make configurable ??
CODE_ALPHABET = string.ascii_uppercase + string.digits
CODE_MAX_ATTEMPTS = 100


class EnrollmentPool(ORMBaseModel):  # pylint: disable=R0903
    """Enrollment pools aka links, pk is UUID and comes from basemodel"""

    __tablename__ = "enrollmentpools"

    owner = sa.Column(saUUID(), sa.ForeignKey(Person.pk), nullable=False)  # whos mainly responsible
    active = sa.Column(sa.Boolean(), nullable=False, default=True)
    extra = sa.Column(JSONB, nullable=False, server_default="{}")  # Passed on to the enrollments
    invitecode = sa.Column(
        sa.String(), nullable=False, index=True, unique=True
    )  # More human writeable identifier than the UUID

    @classmethod
    async def by_pk_or_invitecode(cls, inval: Union[str, uuid.UUID], allow_deleted: bool = False) -> "EnrollmentPool":
        """Get pool by pk or by invitecode"""
        try:
            return await cls.by_pk(inval, allow_deleted)
        except ValueError:
            return await cls.by_invitecode(str(inval), allow_deleted)

    async def create_enrollment(self, callsign: str) -> "Enrollment":
        """Create enrollment from this pool"""
        if not self.active:
            raise PoolInactive()
        if self.deleted:
            raise Deleted("Can't create enrollments on deleted pools")
        return await Enrollment.create_for_callsign(callsign, self, self.extra)

    async def set_active(self, state: bool) -> Self:
        """Set active and return refreshed object"""
        await self.update(active=state).apply()
        return await EnrollmentPool.by_pk(self.pk, allow_deleted=True)

    @classmethod
    async def list(
        cls,
        by_owner: Optional[Person] = None,
        include_deleted: bool = False,
    ) -> AsyncGenerator["EnrollmentPool", None]:
        """List pools, optionally by owner or including deleted pools"""
        async with db.acquire() as conn:  # Cursors need transaction
            async with conn.transaction():
                query = EnrollmentPool.query
                if not include_deleted:
                    query = query.where(
                        EnrollmentPool.deleted == None  # pylint: disable=C0121 ; # "is None" will create invalid query
                    )
                if by_owner:
                    query = query.where(EnrollmentPool.owner == by_owner.pk)
                async for pool in query.order_by(EnrollmentPool.created).gino.iterate():
                    yield pool

    @classmethod
    async def _generate_unused_code(cls) -> str:
        """Internal helper to generate a code that is free
        NOTE: This MUST ONLY be used inside a transaction for nothing is guaranteed"""
        attempt = 0
        while True:
            attempt += 1
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_CHAR_COUNT))
            try:
                await EnrollmentPool.by_invitecode(code)
            except NotFound:
                break
            if attempt > CODE_MAX_ATTEMPTS:
                raise RuntimeError("Can't find unused code")
        return code

    @classmethod
    async def create_for_owner(cls, person: Person, extra: Optional[Dict[str, Any]] = None) -> Self:
        """Creates one for given owner"""
        async with db.acquire() as conn:
            async with conn.transaction():  # do it in a transaction so we can't have races with codes
                code = await cls._generate_unused_code()
                obj = EnrollmentPool(
                    invitecode=code,
                    active=True,
                    owner=person.pk,
                    extra=extra,
                )
                await obj.create()
                # refresh
                return await EnrollmentPool.by_pk(obj.pk)

    async def reset_invitecode(self) -> str:
        """Reset invitecode"""
        async with db.acquire() as conn:
            async with conn.transaction():  # do it in a transaction so we can't have races with codes
                code = await EnrollmentPool._generate_unused_code()
                await self.update(invitecode=code).apply()
                return code

    @classmethod
    async def by_invitecode(cls, invitecode: str, allow_deleted: bool = False) -> Self:
        """Get by invitecode"""
        obj = await EnrollmentPool.query.where(EnrollmentPool.invitecode == invitecode).gino.first()
        if not obj:
            raise NotFound()
        if obj.deleted and not allow_deleted:
            raise Deleted()
        return cast(EnrollmentPool, obj)

    # FIXME: same owner can have multiple pools, see list above
    @classmethod
    async def by_owner_old_tbremoved(cls, owner_uuid: str) -> Self:
        """Get by owner UUID"""
        warnings.warn("deprecated", DeprecationWarning)
        obj = await EnrollmentPool.query.where(EnrollmentPool.owner == owner_uuid).gino.first()
        if not obj:
            raise NotFound()
        return cast(EnrollmentPool, obj)

    # FIXME: This needs to go, firstly there may be multiple pools by same owner secondly the API user needs to know
    #        beforehand whether they are creating or updating something
    @classmethod
    async def old_invitecode_for_callsign_tobedeleted(
        cls, callsign: str, extra: Optional[Dict[str, Any]] = None
    ) -> Self:
        """Create enrollment pool owned by callsign, or update invitecode for existing one"""
        warnings.warn("deprecated", DeprecationWarning)
        _owner = await Person.by_callsign(callsign=callsign)

        _invitecode = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_CHAR_COUNT))
        try:
            existing_obj = await EnrollmentPool.by_owner_old_tbremoved(owner_uuid=_owner.pk)
            await existing_obj.update(invitecode=_invitecode).apply()

        except NotFound:
            obj = EnrollmentPool(owner=_owner.pk, active=True, extra=extra, invitecode=_invitecode)
            await obj.create()

        return await EnrollmentPool.by_owner_old_tbremoved(owner_uuid=_owner.pk)


class EnrollmentState(enum.IntEnum):
    """Enrollment states"""

    PENDING = 0
    APPROVED = 1
    REJECTED = 2


class Enrollment(ORMBaseModel):  # pylint: disable=R0903
    """Enrollments, pk is UUID and comes from basemodel"""

    __tablename__ = "enrollments"

    approvecode = sa.Column(sa.String(), nullable=False, index=True, unique=True)
    callsign = sa.Column(sa.String(), nullable=False, index=True, unique=True)
    decided_on = sa.Column(sa.DateTime(timezone=True), nullable=True)
    decided_by = sa.Column(saUUID(), sa.ForeignKey(Person.pk), nullable=True)
    person = sa.Column(saUUID(), sa.ForeignKey(Person.pk), nullable=True)
    pool = sa.Column(saUUID(), sa.ForeignKey(EnrollmentPool.pk), nullable=True)
    state = sa.Column(sa.Integer(), nullable=False, index=False, unique=False, default=EnrollmentState.PENDING)
    extra = sa.Column(JSONB, nullable=False, server_default="{}")  # Passed on to the Persons

    @classmethod
    async def by_pk_or_callsign(cls, inval: Union[str, uuid.UUID]) -> "Enrollment":
        """Get enrollment by pk or by callsign"""
        try:
            return await cls.by_pk(inval)
        except ValueError:
            return await cls.by_callsign(str(inval))

    async def approve(self, approver: Person) -> Person:
        """Creates the person record, their certs etc"""
        async with db.acquire() as conn:
            # Do in transaction so things get rolled back if shit hits the fan
            async with conn.transaction():
                person = await Person.create_with_cert(self.callsign, extra=self.extra)
                await self.update(
                    state=EnrollmentState.APPROVED, decided_by=approver.pk, decided_on=utcnow, person=person.pk
                ).apply()
                return person

    async def reject(self, decider: Person) -> None:
        """Reject"""
        await self.update(state=EnrollmentState.REJECTED, decided_by=decider.pk, decided_on=utcnow).apply()

    @classmethod
    async def list(cls, by_pool: Optional[EnrollmentPool] = None) -> AsyncGenerator["Enrollment", None]:
        """List enrollments, optionally by pool (enrollment deletion is not allowed, they can only be rejected)"""
        async with db.acquire() as conn:  # Cursors need transaction
            async with conn.transaction():
                query = Enrollment.query
                if by_pool:
                    query = query.where(Enrollment.pool == by_pool.pk)
                async for enrollment in query.order_by(Enrollment.callsign).gino.iterate():
                    yield enrollment

    @classmethod
    async def by_callsign(cls, callsign: str) -> Self:
        """Get by callsign"""
        obj = await Enrollment.query.where(Enrollment.callsign == callsign).gino.first()
        if not obj:
            raise NotFound()
        if obj.deleted:
            LOGGER.error("Got a deleted enrollment {}, this should not be possible".format(obj.pk))
            raise Deleted()  # This should *not* be happening
        return cast(Enrollment, obj)

    @classmethod
    async def by_approvecode(cls, code: str) -> Self:
        """Get by approvecode"""
        obj = await Enrollment.query.where(Enrollment.approvecode == code).gino.first()
        if not obj:
            raise NotFound()
        if obj.deleted:
            LOGGER.error("Got a deleted enrollment {}, this should not be possible".format(obj.pk))
            raise Deleted()  # This should *not* be happening
        return cast(Enrollment, obj)

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
        async with db.acquire() as conn:
            async with conn.transaction():  # do it in a transaction so we can't have races with codes
                code = await Enrollment._generate_unused_code()
                await self.update(approvecode=code).apply()
                return code

    @classmethod
    async def _generate_unused_code(cls) -> str:
        """Internal helper to generate a code that is free
        NOTE: This MUST ONLY be used inside a transaction for nothing is guaranteed"""
        attempt = 0
        while True:
            attempt += 1
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_CHAR_COUNT))
            try:
                await Enrollment.by_approvecode(code)
            except NotFound:
                break
            if attempt > CODE_MAX_ATTEMPTS:
                raise RuntimeError("Can't find unused code")
        return code

    @classmethod
    async def create_for_callsign(
        cls, callsign: str, pool: Optional[EnrollmentPool] = None, extra: Optional[Dict[str, Any]] = None
    ) -> Self:
        """Create a new one with random code for the callsign"""
        if callsign in RMSettings.singleton().valid_product_cns:
            raise CallsignReserved("Using product CNs as callsigns is forbidden")
        async with db.acquire() as conn:
            async with conn.transaction():  # do it in a transaction so we can't have races with codes
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
                )
                await obj.create()
                # refresh
                return await Enrollment.by_callsign(callsign)

    async def delete(self) -> bool:
        """Deletion of enrollments is not allowed"""
        raise ForbiddenOperation("Deletion of enrollments is not allowed")
