"""Abstractions for people"""
import secrets
import string
from typing import Self, cast, Optional, AsyncGenerator, Dict, Any
import uuid
import logging
from pathlib import Path
import shutil

from OpenSSL import crypto  # FIXME: use cryptography instead of pyOpenSSL
import cryptography.x509
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as saUUID
import sqlalchemy as sa
from libpvarki.mtlshelp.csr import PRIVDIR_MODE, async_create_keypair, async_create_client_csr
from libpvarki.schemas.product import UserCRUDRequest
from libpvarki.schemas.generic import OperationResultResponse

from .base import ORMBaseModel, DBModel, utcnow, db
from ..web.api.middleware import MTLSorJWTPayload
from .errors import NotFound, Deleted, BackendError, CallsignReserved
from ..settings import settings
from ..cfssl.private import sign_csr, revoke_pem, validate_reason, ReasonTypes
from ..prodcutapihelpers import post_to_all_products

LOGGER = logging.getLogger(__name__)
CODE_CHAR_COUNT = 12
CODE_ALPHABET = string.ascii_uppercase + string.digits


class Person(ORMBaseModel):  # pylint: disable=R0903
    """People, pk is UUID and comes from basemodel

    NOTE: at some point we want to stop keeping track of people in our own db
    and only use keycloack as the store for actual users. In any case we need a nice pythonic
    abstraction layer so implement any queries you need to add as helpers here.
    """

    __tablename__ = "users"

    callsign = sa.Column(sa.String(), nullable=False, index=True, unique=True)
    # Directory with the key, cert and pfx
    certspath = sa.Column(sa.String(), nullable=False, index=False, unique=True)
    extra = sa.Column(JSONB, nullable=False, server_default="{}")
    revoke_reason = sa.Column(sa.String(), nullable=True, index=False)

    @classmethod
    async def create_with_cert(cls, callsign: str, extra: Optional[Dict[str, Any]] = None) -> "Person":
        """Create the cert etc and save the person"""
        try:
            await Person.by_callsign(callsign)
            raise CallsignReserved()
        except NotFound:
            pass
        async with db.acquire() as conn:
            async with conn.transaction():  # do it in a transaction so if something fails we can roll back
                puuid = uuid.uuid4()
                certspath = Path(settings.persistent_data_dir) / "private" / "people" / str(puuid)
                certspath.mkdir(parents=True)
                certspath.chmod(PRIVDIR_MODE)
                try:
                    newperson = Person(pk=puuid, callsign=callsign, certspath=str(certspath), extra=extra)
                    await newperson.create()
                    ckp = await async_create_keypair(newperson.privkeyfile, newperson.pubkeyfile)
                    csrpem = await async_create_client_csr(ckp, newperson.csrfile, newperson.certsubject)
                    certpem = (await sign_csr(csrpem)).replace("\\n", "\n")
                    newperson.certfile.write_text(certpem)
                except Exception as exc:
                    LOGGER.exception("Something went wrong, doing cleanup")
                    shutil.rmtree(certspath)
                    remaining = list(certspath.rglob("*"))
                    LOGGER.debug("Remaining files: {}".format(remaining))
                    raise BackendError(str(exc)) from exc
                # Return refreshed object if everything went ok
                refresh = await cls.by_pk(newperson.pk)
                await user_created(refresh)
                return refresh

    async def revoke(self, reason: ReasonTypes) -> bool:
        """Revokes the cert with given reason and makes user deleted see validate_reason for info on reasons"""
        reason = validate_reason(reason)
        async with db.acquire() as conn:
            async with conn.transaction():  # do it in a transaction so if CFSSL fails we can roll back
                try:
                    await self.update(deleted=utcnow, revoke_reason=str(reason.value)).apply()
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
        pfxpath = Path(self.certspath) / "mtls.pfx"
        if not pfxpath.exists():
            pfxpath.write_bytes(
                pem_to_pfx(
                    self.certfile.read_text("utf-8"),
                    self.privkeyfile.read_text("utf-8"),
                )
            )
        return pfxpath

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
    async def list(cls, include_deleted: bool = False) -> AsyncGenerator["Person", None]:
        """List people"""
        async with db.acquire() as conn:  # Cursors need transaction
            async with conn.transaction():
                query = Person.query
                if not include_deleted:
                    query = query.where(
                        Person.deleted == None  # pylint: disable=C0121 ; # "is None" will create invalid query
                    )
                async for person in query.order_by(Person.callsign).gino.iterate():
                    yield person

    @classmethod
    async def by_role(cls, role: str) -> AsyncGenerator["Person", None]:
        """List people that have given role, if role is None list all people"""
        async with db.acquire() as conn:  # Cursors need transaction
            async with conn.transaction():
                async for lnk in Role.load(user=Person).query.where(Role.role == role).where(
                    Person.deleted == None  # pylint: disable=C0121 ; # "is None" will create invalid query
                ).order_by(Person.callsign).gino.iterate():
                    yield lnk.user

    @classmethod
    async def by_callsign(cls, callsign: str, allow_deleted: bool = False) -> Self:
        """Get by callsign"""
        obj = await Person.query.where(Person.callsign == callsign).gino.first()
        if not obj:
            raise NotFound()
        if obj.deleted and not allow_deleted:
            raise Deleted()
        return cast(Person, obj)

    @classmethod
    async def by_verification_code(cls, verification_code: str, allow_deleted: bool = False) -> Self:
        """Get by verification_code"""
        obj = await Person.query.where(Person.verification_code == verification_code).gino.first()
        if not obj:
            raise NotFound()
        if obj.deleted and not allow_deleted:
            raise Deleted()
        return cast(Person, obj)

    @classmethod
    async def by_mtlsjwt_payload(cls, payload: MTLSorJWTPayload, allow_deleted: bool = False) -> Self:
        """Get by MTLSorJWTMiddleWare payload"""
        if not payload.userid:
            raise NotFound("No userid defined")
        return await cls.by_callsign(payload.userid, allow_deleted)

    async def get_key_pem(self) -> bytes:
        """Read the private key from under certspath and return the PEM"""
        raise NotImplementedError()

    async def get_cert_pem(self) -> bytes:
        """Read the cert from under certspath and return the PEM"""
        raise NotImplementedError()

    async def get_cert_pfx(self) -> bytes:
        """Read the cert and private key from under certspath and return the PFX container"""
        raise NotImplementedError()

    async def _get_role(self, role: str) -> Optional["Role"]:
        """Internal helper for DRY"""
        obj = await Role.query.where(Role.user == self.pk).where(Role.role == role).gino.first()
        if obj:
            return cast(Role, obj)
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
            return False
        role = Role(user=self.pk, role=role)
        await role.create()
        await self.update(updated=utcnow).apply()
        if role == "admin":
            await user_promoted(self)
        return True

    async def remove_role(self, role: str) -> bool:
        """Remove a role, return true if role was removed, false if it wasn't assigned"""
        obj = await self._get_role(role)
        if not obj:
            return False
        await obj.delete()
        await self.update(updated=utcnow).apply()
        if role == "admin":
            await user_demoted(self)
        return True

    @classmethod
    async def set_verification_code(cls, callsign: str) -> str:
        """Set verification code for callsign"""
        obj = await Person.by_callsign(callsign=callsign)
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_CHAR_COUNT))
        print(callsign)
        print(code)
        print(obj)
        await obj.update(verification_code=code).apply()

        return code


class Role(DBModel):  # type: ignore[misc] # pylint: disable=R0903
    """Give a person a role"""

    __tablename__ = "roles"
    __table_args__ = {"schema": "raesenmaeher"}

    pk = sa.Column(saUUID(), primary_key=True, default=uuid.uuid4)
    created = sa.Column(sa.DateTime(timezone=True), default=utcnow, nullable=False)
    updated = sa.Column(sa.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    user = sa.Column(saUUID(), sa.ForeignKey(Person.pk))
    role = sa.Column(sa.String(), nullable=False, index=True)
    _idx = sa.Index("user_role_unique", "user", "role", unique=True)


async def post_user_crud(userinfo: UserCRUDRequest, endpoint_suffix: str) -> None:
    """Wrapper to be more DRY in the basic CRUD things"""
    endpoint = f"api/v1/users/{endpoint_suffix}"

    responses = await post_to_all_products(
        endpoint,
        userinfo.dict(),
        OperationResultResponse,
    )
    LOGGER.debug("got responses: {}".format(responses))
    # TODO: Check responses and log errors


async def user_created(person: Person) -> None:
    """New user was created"""
    return await post_user_crud(person.productapidata, "created")


async def user_revoked(person: Person) -> None:
    """Old user was revoked"""
    return await post_user_crud(person.productapidata, "revoked")


async def user_promoted(person: Person) -> None:
    """Old user was promoted to admin (granted role 'admin')"""
    return await post_user_crud(person.productapidata, "promoted")


async def user_demoted(person: Person) -> None:
    """Old user was demoted from admin (removed role 'admin')"""
    return await post_user_crud(person.productapidata, "demoted")


# FIXME: moving this to libpvarki would be a good idea
def pem_to_pfx(pem_key: str, pem_cert: str) -> bytes:
    """Convert PEM data to PFX (PKCS12)."""
    pfx = crypto.PKCS12()
    pfx.set_privatekey(crypto.load_privatekey(crypto.FILETYPE_PEM, pem_key.encode("utf-8")))
    pfx.set_certificate(crypto.load_certificate(crypto.FILETYPE_PEM, pem_cert.encode("utf-8")))
    pfxdata = pfx.export()
    return pfxdata
