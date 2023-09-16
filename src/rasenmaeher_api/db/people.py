"""Abstractions for people"""
from typing import Self, cast, Optional
import uuid

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as saUUID
import sqlalchemy as sa

from .base import BaseModel, DBModel, utcnow
from ..web.api.middleware import MTLSorJWTPayload
from .errors import NotFound, Deleted


class Person(BaseModel):  # pylint: disable=R0903
    """People, pk is UUID and comes from basemodel"""

    __tablename__ = "users"

    callsign = sa.Column(sa.String(), nullable=False, index=True, unique=True)
    pfxpath = sa.Column(sa.String(), nullable=False, index=False, unique=True)
    extra = sa.Column(JSONB, nullable=False, server_default="{}")

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
