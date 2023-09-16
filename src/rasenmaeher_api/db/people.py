"""Abstractions for people"""
from typing import Self, cast
from sqlalchemy.dialects.postgresql import JSONB
import sqlalchemy as sa

from .base import BaseModel
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
