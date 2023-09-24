"""Abstractions for people"""
from typing import Self, cast, Optional, AsyncGenerator, Dict, Any
import uuid
import logging
from pathlib import Path
import shutil

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as saUUID
import sqlalchemy as sa
from libpvarki.mtlshelp.csr import PRIVDIR_MODE, async_create_keypair, async_create_client_csr

from .base import ORMBaseModel, DBModel, utcnow, db
from ..web.api.middleware import MTLSorJWTPayload
from .errors import NotFound, Deleted, BackendError, CallsignReserved
from ..settings import settings
from ..cfssl.private import sign_csr

LOGGER = logging.getLogger(__name__)


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

    @classmethod
    async def create_with_cert(cls, callsign: str, extra: Optional[Dict[str, Any]] = None) -> "Person":
        """Create the cert etc and save the person"""
        try:
            await Person.by_callsign(callsign)
            raise CallsignReserved()
        except NotFound:
            pass
        async with db.acquire() as conn:  # Cursors need transaction
            async with conn.transaction():
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
                return await cls.by_pk(newperson.pk)

    @property
    def certsubject(self) -> Dict[str, str]:
        """Return the dict that gets set to cert DN"""
        return {"CN": self.callsign}

    @property
    def privkeyfile(self) -> Path:
        """Path to the private key"""
        return Path(self.certspath) / "mtls.key"

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
        return True

    async def remove_role(self, role: str) -> bool:
        """Remove a role, return true if role was removed, false if it wasn't assigned"""
        obj = await self._get_role(role)
        if not obj:
            return False
        await obj.delete()
        await self.update(updated=utcnow).apply()
        return True


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
