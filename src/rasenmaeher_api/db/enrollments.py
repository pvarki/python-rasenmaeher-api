"""Abstractions for enrollments"""
from typing import Self, Dict, cast, Any, Optional
import string
import secrets
import logging
import enum

from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as saUUID
import sqlalchemy as sa

from .base import BaseModel, utcnow
from .people import Person
from .errors import ForbiddenOperation, CallsignReserved, NotFound, Deleted

LOGGER = logging.getLogger(__name__)
CODE_CHAR_COUNT = 8  # TODO: Make configurable ??
CODE_ALPHABET = string.ascii_uppercase + string.digits


class EnrollmentState(enum.IntEnum):
    """Enrollment states"""

    PENDING = 0
    APPROVED = 1
    REJECTED = 2


class Enrollment(BaseModel):  # pylint: disable=R0903
    """Enrollments, pk is UUID and comes from basemodel"""

    __tablename__ = "enrollments"

    approvecode = sa.Column(sa.String(), nullable=False, index=True, unique=True)
    callsign = sa.Column(sa.String(), nullable=False, index=True, unique=True)
    decided_on = sa.Column(sa.DateTime(timezone=True), nullable=True)
    decided_by = sa.Column(saUUID(), sa.ForeignKey(Person.pk), nullable=True)
    person = sa.Column(saUUID(), sa.ForeignKey(Person.pk), nullable=True)
    state = sa.Column(sa.Integer(), nullable=False, index=False, unique=False, default=EnrollmentState.PENDING)
    extra = sa.Column(JSONB, nullable=False, server_default="{}")

    async def approve(self, approver: Person) -> Person:
        """Creates the person record, their certs etc"""
        # TODO: Do in a transaction so rollback on DB failures
        person = await Person.create_with_cert(self.callsign, extra=self.extra)
        self.update(state=EnrollmentState.APPROVED, decided_by=approver.pk, decided_on=utcnow, person=person.pk)
        return person

    async def reject(self, decider: Person) -> None:
        """Reject"""
        await self.update(state=EnrollmentState.REJECTED, decided_by=decider.pk, decided_on=utcnow)

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
    async def create_for_callsign(cls, callsign: str, extra: Optional[Dict[str, Any]] = None) -> Self:
        """Create a new one with random code for the callsign"""
        # TODO: Do this in a transaction to avoid race conditions
        try:
            await Enrollment.by_callsign(callsign)
            raise CallsignReserved()
        except NotFound:
            pass
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_CHAR_COUNT))
        obj = Enrollment(
            approvecode=code,
            callsign=callsign,
            state=EnrollmentState.PENDING,
            extra=extra,
        )
        await obj.create()
        # refresh
        return await Enrollment.by_callsign(callsign)

    async def delete(self) -> bool:
        """Deletion of enrollments is not allowed"""
        raise ForbiddenOperation("Deletion of enrollments is not allowed")
