"""Abstractions for people"""

from typing import Self, Optional, AsyncGenerator, Dict, Any, Set, Union
import asyncio
import uuid
import logging
from pathlib import Path
import shutil
import datetime

import cryptography.x509
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel, select
import sqlalchemy as sa
from sqlalchemy.sql import func
from libpvarki.mtlshelp.csr import PRIVDIR_MODE, async_create_keypair, async_create_client_csr
from libpvarki.schemas.product import UserCRUDRequest
from libpvarki.schemas.generic import OperationResultResponse
from libpvarki.mtlshelp.pkcs12 import convert_pem_to_pkcs12
from libadvian.tasks import TaskMaster


from .base import ORMBaseModel, utcnow
from ..web.api.middleware.datatypes import MTLSorJWTPayload
from .errors import NotFound, Deleted, BackendError, CallsignReserved
from ..cfssl.private import sign_csr, revoke_pem, validate_reason, ReasonTypes, refresh_ocsp
from ..productapihelpers import post_to_all_products
from ..rmsettings import RMSettings
from ..kchelpers import KCClient, KCUserData
from .engine import EngineWrapper
from ..web.api.utils.csr_utils import verify_csr

LOGGER = logging.getLogger(__name__)


class Person(ORMBaseModel, table=True):  # type: ignore[call-arg] # pylint: disable=too-many-public-methods
    """People, pk is UUID and comes from basemodel

    NOTE: at some point we want to stop keeping track of people in our own db
    and only use keycloack as the store for actual users. In any case we need a nice pythonic
    abstraction layer so implement any queries you need to add as helpers here.
    """

    __tablename__ = "users"

    callsign: str = Field(nullable=False, index=True, unique=True)
    # Directory with the key, cert and pfx
    certspath: str = Field(nullable=False, index=False, unique=True)
    extra: Dict[str, Any] = Field(sa_type=JSONB, nullable=False, sa_column_kwargs={"server_default": "{}"})
    revoke_reason: str = Field(nullable=True, index=False)

    @classmethod
    async def update_from_kcdata(cls, kcdata: Dict[str, Any], person: Optional["Person"] = None) -> "Person":
        """Update the local record with KC deta"""
        if not person:
            if "callsign" in kcdata:
                person = await cls.by_callsign(kcdata["callsign"])
            else:
                person = await cls.by_callsign(kcdata["username"])
            if person.extra is None:
                LOGGER.warning("self.extra was None for some reason, this should not happen")
                person.extra = {}
        # This *is* in correct indent
        # Do not bother having second copy of local properties
        for key in ("callsign", "certpem"):
            if key not in kcdata:
                continue
            del kcdata[key]
        person.extra.update(
            {
                "kc_uuid": kcdata["id"],
                "kc_data": kcdata,
            }
        )
        try:
            LOGGER.debug("Updating extra for {}".format(person.callsign))
            with EngineWrapper.get_session() as session:
                session.add(person)
                session.commit()
                session.refresh(person)
                return person
        except Exception as exc:
            raise BackendError(str(exc)) from exc

    @classmethod
    async def by_pk_or_callsign(cls, inval: Union[str, uuid.UUID], allow_deleted: bool = False) -> "Person":
        """Get person by pk or by callsign"""
        try:
            return await cls.by_pk(inval, allow_deleted)
        except ValueError:
            return await cls.by_callsign(str(inval), allow_deleted)

    @classmethod
    async def create_with_cert(
        cls, callsign: str, extra: Optional[Dict[str, Any]] = None, csrpem: Optional[str] = None
    ) -> "Person":
        """Create the cert etc and save the person"""
        if csrpem and not verify_csr(csrpem, callsign):
            raise CallsignReserved("CSR CN must match callsign")
        cnf = RMSettings.singleton()
        if callsign in cnf.valid_product_cns:
            raise CallsignReserved("Using product CNs as callsigns is forbidden")
        try:
            await Person.by_callsign(callsign)
            raise CallsignReserved()
        except NotFound:
            pass

        with EngineWrapper.get_session() as session:
            puuid = uuid.uuid4()
            certspath = Path(cnf.persistent_data_dir) / "private" / "people" / str(puuid)
            certspath.mkdir(parents=True)
            certspath.chmod(PRIVDIR_MODE)
            try:
                newperson = Person(pk=puuid, callsign=callsign, certspath=str(certspath), extra=extra)
                session.add(newperson)
                session.commit()
                if csrpem:
                    newperson.csrfile.write_text(csrpem, encoding="utf-8")
                else:
                    ckp = await async_create_keypair(newperson.privkeyfile, newperson.pubkeyfile)
                    csrpem = await async_create_client_csr(ckp, newperson.csrfile, newperson.certsubject)
                certpem = (await sign_csr(csrpem)).replace("\\n", "\n")
                newperson.certfile.write_text(certpem)
            except Exception as exc:
                LOGGER.exception("Something went wrong, doing cleanup")
                shutil.rmtree(certspath)
                remaining = list(certspath.rglob("*"))
                LOGGER.debug("Remaining files: {}".format(remaining))
                session.rollback()
                raise BackendError(str(exc)) from exc
            # refresh object if everything went ok
            session.refresh(newperson)
        # Drop the DB transaction for rest of the actions
        return await newperson._post_create()  # pylint: disable=W0212

    async def _post_create(self) -> "Person":
        """Post creation actions, in separate method for readability"""
        refresh = self
        kclient = KCClient.singleton()
        kcdata = await kclient.create_kc_user(await refresh.get_kcdata())
        if not kcdata:
            LOGGER.warning("create_kc_user returned none")
        else:
            LOGGER.debug("Calling update_from_kcdata")
            refresh = await Person.update_from_kcdata(kcdata.kc_data, refresh)
        # Trigger some background tasks
        TaskMaster.singleton().create_task(refresh.create_pfx())
        TaskMaster.singleton().create_task(refresh_ocsp())
        TaskMaster.singleton().create_task(user_created(refresh))
        return refresh

    async def create_pfx(self) -> Path:
        """Put cert and key to PKCS12 container"""
        if self.pfxfile.exists():
            return self.pfxfile

        def write_pfx() -> None:
            """Do the IO"""
            nonlocal self
            if self.privkeyfile.exists():
                p12bytes = convert_pem_to_pkcs12(self.certfile, self.privkeyfile, self.callsign, None, self.callsign)
            else:
                p12bytes = convert_pem_to_pkcs12(self.certfile, None, self.callsign, None, self.callsign)
            self.pfxfile.write_bytes(p12bytes)

        await asyncio.get_event_loop().run_in_executor(None, write_pfx)
        return self.pfxfile

    async def revoke(self, reason: ReasonTypes) -> bool:
        """Revokes the cert with given reason and makes user deleted see validate_reason for info on reasons"""
        reason = validate_reason(reason)
        with EngineWrapper.get_session() as session:
            try:
                self.deleted = datetime.datetime.now(datetime.UTC)
                self.revoke_reason = str(reason.value)
                session.add(self)
                session.commit()
                await revoke_pem(self.certfile, reason)
                await user_revoked(self)
            except Exception as exc:
                LOGGER.exception("Something went wrong, rolling back")
                raise BackendError(str(exc)) from exc
            return True

    async def delete(self) -> bool:
        """Revoke the cert on delete"""
        if self.certfile.exists():
            LOGGER.info("Calling self.revoke with reason=privilege_withdrawn")
            return await self.revoke(cryptography.x509.ReasonFlags.privilege_withdrawn)
        LOGGER.error("User has no certificate, this indicates someone created user without using create_with_cert")
        return await super().delete()

    @property
    def productapidata(self) -> UserCRUDRequest:
        """Return a model that is usable with the product integration APIs"""
        if not self.certfile.exists():
            LOGGER.error("User has no certificate, this indicates someone created user without using create_with_cert")
            cert_pem = "NOCERTFOUND"
        else:
            cert_pem = self.certfile.read_text("utf-8")
        return UserCRUDRequest(uuid=str(self.pk), callsign=self.callsign, x509cert=cert_pem.replace("\n", "\\n"))

    async def get_kcdata(self) -> KCUserData:
        """KC integration data"""
        pdata = self.productapidata
        if self.extra is None:
            LOGGER.warning("self.extra was None for some reason, this should not happen")
            self.extra = {}
        if "kc_uuid" not in self.extra:
            self.extra["kc_uuid"] = None
        if "kc_data" not in self.extra:
            self.extra["kc_data"] = {}
        return KCUserData(
            productdata=pdata,
            roles=await self.roles_set(),
            kc_id=self.extra["kc_uuid"],
            kc_data=self.extra["kc_data"],
        )

    @property
    def certsubject(self) -> Dict[str, str]:
        """Return the dict that gets set to cert DN"""
        return {"CN": self.callsign}

    @property
    def privkeyfile(self) -> Path:
        """Path to the private key"""
        return Path(self.certspath) / "mtls.key"

    @property
    def pfxfile(self) -> Path:
        """Return a PKCS12 PFX file"""
        return Path(self.certspath) / "mtls.pfx"

    @property
    def certfile(self) -> Path:
        """Path to the public cert"""
        return Path(self.certspath) / "mtls.pem"

    @property
    def csrfile(self) -> Path:
        """Path to the CSR file"""
        return Path(self.certspath) / "mtls.csr"

    @property
    def pubkeyfile(self) -> Path:
        """Path to the public key"""
        return Path(self.certspath) / "mtls.pub"

    @classmethod
    async def list(cls, include_deleted: bool = False, *, only_deleted: bool = False) -> AsyncGenerator["Person", None]:
        """List people"""
        with EngineWrapper.get_session() as session:
            statement = select(cls)
            if only_deleted:
                include_deleted = True
                statement = statement.where(
                    cls.deleted != None  # pylint: disable=C0121 ; # "is not None" will create invalid query
                )
            if not include_deleted:
                statement = statement.where(
                    cls.deleted == None  # pylint: disable=C0121 ; # "is None" will create invalid query
                )
            results = session.exec(statement)
            for result in results:
                yield result

    @classmethod
    async def by_role(cls, role: str) -> AsyncGenerator["Person", None]:
        """List people that have given role, if role is None list all people"""
        with EngineWrapper.get_session() as session:
            statement = select(Person, Role).join(Role).where(Role.role == role)
            results = session.exec(statement)
            for person, _roleobj in results:
                yield person

    @classmethod
    async def by_callsign(cls, callsign: str, allow_deleted: bool = False) -> Self:
        """Get by callsign"""
        with EngineWrapper.get_session() as session:
            statement = select(cls).where(func.lower(cls.callsign) == func.lower(callsign))
            obj = session.exec(statement).first()
            if not obj:
                raise NotFound()
            if obj.deleted and not allow_deleted:
                raise Deleted()
            return obj

    # FIXME: Change the method name to be clearer about the purpose
    @classmethod
    async def is_callsign_available(cls, callsign: str) -> bool:
        """Is user with this callsign available?"""
        with EngineWrapper.get_session() as session:
            statement = select(cls).where(func.lower(cls.callsign) == func.lower(callsign))
            data = session.exec(statement).first()
            if not data:
                return False
            return True

    @classmethod
    async def by_mtlsjwt_payload(cls, payload: MTLSorJWTPayload, allow_deleted: bool = False) -> Self:
        """Get by MTLSorJWTMiddleWare payload"""
        if not payload.userid:
            raise NotFound("No userid defined")
        return await cls.by_callsign(payload.userid, allow_deleted)

    def get_cert_pem(self) -> bytes:
        """Read the cert from under certspath and return the PEM"""
        return self.certfile.read_bytes()

    def get_cert_pfx(self) -> bytes:
        """Read the cert and private key from under certspath and return the PFX container"""
        return self.pfxfile.read_bytes()

    async def _get_role(self, role: str) -> Optional["Role"]:
        """Internal helper for DRY"""
        with EngineWrapper.get_session() as session:
            statement = select(Role).where(Role.role == role, Role.user == self.pk)
            obj = session.exec(statement).first()
            if obj:
                return obj
        return None

    async def has_role(self, role: str) -> bool:
        """Check if this user has given role"""
        obj = await self._get_role(role)
        if obj:
            return True
        return False

    async def assign_role(self, role: str) -> bool:
        """Assign a role, return true if role was created, false if it already existed"""
        if await self.has_role(role):
            if role == "admin":
                LOGGER.debug("{} already promoted but informing anyway".format(self.callsign))
                TaskMaster.singleton().create_task(user_promoted(self))
            return False
        with EngineWrapper.get_session() as session:
            dbrole = Role(user=self.pk, role=role)
            session.add_all([dbrole])
            self.updated = datetime.datetime.now(datetime.UTC)
            session.add(self)
            session.commit()
            session.refresh(self)
        if role == "admin":
            LOGGER.debug("{} promoted, informing".format(self.callsign))
            TaskMaster.singleton().create_task(user_promoted(self))
        return True

    async def remove_role(self, role: str) -> bool:
        """Remove a role, return true if role was removed, false if it wasn't assigned"""
        obj = await self._get_role(role)
        if not obj:
            if role == "admin":
                LOGGER.debug("{} already demoted but informing anyway".format(self.callsign))
                TaskMaster.singleton().create_task(user_demoted(self))
            return False
        with EngineWrapper.get_session() as session:
            session.delete(obj)
            self.updated = datetime.datetime.now(datetime.UTC)
            session.add(self)
            session.commit()
            session.refresh(self)
        if role == "admin":
            LOGGER.debug("{} demoted, informing".format(self.callsign))
            TaskMaster.singleton().create_task(user_demoted(self))
        return True

    async def roles_set(self) -> Set[str]:
        """Shorthand"""
        return {role async for role in self.roles()}

    async def roles(self) -> AsyncGenerator[str, None]:
        """Roles of this person"""
        with EngineWrapper.get_session() as session:
            statement = select(Role).where(Role.user == self.pk)
            results = session.exec(statement)
            for result in results:
                yield result.role


class Role(SQLModel, table=True):  # type: ignore[call-arg]
    """Give a person a role"""

    __tablename__ = "roles"
    __table_args__ = ORMBaseModel.__table_args__

    pk: uuid.UUID = Field(primary_key=True, default_factory=uuid.uuid4)
    created: datetime.datetime = Field(sa_column_kwargs={"default": utcnow}, nullable=False)
    updated: datetime.datetime = Field(sa_column_kwargs={"default": utcnow, "onupdate": utcnow}, nullable=False)
    #    user: uuid.UUID = Field(foreign_key="users.pk")
    user: uuid.UUID = Field(foreign_key=f"{ORMBaseModel.__table_args__['schema']}.users.pk")
    role: str = Field(nullable=False, index=True)
    _idx = sa.Index("user_role_unique", "user", "role", unique=True)


async def post_user_crud(userinfo: UserCRUDRequest, endpoint_suffix: str) -> None:
    """Wrapper to be more DRY in the basic CRUD things"""
    endpoint = f"api/v1/users/{endpoint_suffix}"
    # We can't do anything about any issues with the responses so don't collect them
    await post_to_all_products(endpoint, userinfo.dict(), OperationResultResponse, collect_responses=False)


async def user_created(person: Person) -> None:
    """New user was created"""
    await post_user_crud(person.productapidata, "created")


async def user_revoked(person: Person) -> None:
    """Old user was revoked"""
    kclient = KCClient.singleton()
    # NOTE: asyncio.gather breaks things in Gino
    # https://github.com/python-gino/gino/issues/313#issuecomment-427708709
    await post_user_crud(person.productapidata, "revoked")
    await kclient.delete_kc_user(await person.get_kcdata())


async def user_promoted(person: Person) -> None:
    """Old user was promoted to admin (granted role 'admin')"""
    kclient = KCClient.singleton()
    # NOTE: asyncio.gather breaks things in Gino
    # https://github.com/python-gino/gino/issues/313#issuecomment-427708709
    kcuser = await kclient.update_kc_user(await person.get_kcdata())
    if kcuser and isinstance(kcuser, KCUserData):
        await Person.update_from_kcdata(kcuser.kc_data)
    await post_user_crud(person.productapidata, "promoted")


async def user_demoted(person: Person) -> None:
    """Old user was demoted from admin (removed role 'admin')"""
    kclient = KCClient.singleton()
    # NOTE: asyncio.gather breaks things in Gino
    # https://github.com/python-gino/gino/issues/313#issuecomment-427708709
    kcuser = await kclient.update_kc_user(await person.get_kcdata())
    if kcuser and isinstance(kcuser, KCUserData):
        await Person.update_from_kcdata(kcuser.kc_data)
    await post_user_crud(person.productapidata, "demoted")
