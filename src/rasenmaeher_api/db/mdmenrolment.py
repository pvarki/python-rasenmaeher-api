"""Whether devices may enrol through an MDM right now, and the challenge they must bring"""

import datetime
import hmac
import logging
import secrets

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlmodel import Field, select

from .base import ORMBaseModel
from .engine import EngineWrapper
from .errors import ForbiddenOperation

LOGGER = logging.getLogger(__name__)


def new_challenge() -> str:
    """Hex, because the challenge travels as an X.509 attribute and some clients encode it as a
    PrintableString, which has no room for "_"."""
    return secrets.token_hex(16)


class MdmEnrolment(ORMBaseModel, table=True):
    """The one row saying when the MDM enrolment window closes

    Closed until an admin opens it, and it closes itself when the window runs out, so a deployment
    nobody is watching does not go on taking enrolments. Every window gets a new challenge: while
    it is open the challenge is all that stands between the public SCEP endpoint and a new
    identity, and every device enrolled so far holds the old one. So opening means putting the new
    challenge in the MDM.
    """

    __tablename__ = "mdmenrolment"

    # One row, and the unique key makes the database refuse a second one when workers race to
    # create it.
    slot: str = Field(default="mdm", nullable=False, unique=True)
    challenge: str = Field(nullable=False)
    open_until: datetime.datetime | None = Field(
        default=None, sa_column=sa.Column(sa.DateTime(timezone=True), nullable=True)
    )

    @classmethod
    async def current(cls) -> "MdmEnrolment":
        """The row, made with a fresh challenge and closed the first time anybody asks"""
        with EngineWrapper.get_session() as session:
            obj = session.exec(select(cls)).first()
            if obj:
                return obj
            obj = cls(challenge=new_challenge())
            session.add(obj)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                return session.exec(select(cls)).one()
            session.refresh(obj)
            return obj

    @property
    def is_open(self) -> bool:
        """Is the window open right now"""
        return self.open_until is not None and self.open_until > datetime.datetime.now(datetime.UTC)

    def accepts(self, challenge: str | None) -> bool:
        """Is this the challenge, compared without leaking how much of it matched"""
        if not challenge:
            return False
        return hmac.compare_digest(challenge.encode("utf-8"), self.challenge.encode("utf-8"))

    async def open_for(self, hours: int) -> "MdmEnrolment":
        """Open the window for this many hours from now, or close it with 0

        Opening a closed window makes a new challenge. Extending an open one keeps it, because the
        devices the MDM is enrolling at that moment were handed it.
        """
        until = datetime.datetime.now(datetime.UTC) + datetime.timedelta(hours=hours) if hours else None
        with EngineWrapper.get_session() as session:
            if until and not self.is_open:
                self.challenge = new_challenge()
            self.open_until = until
            session.add(self)
            session.commit()
            session.refresh(self)
        return self

    async def delete(self) -> bool:
        """The row is the setting; closing the window is what turns enrolment off"""
        raise ForbiddenOperation("Deletion of the MDM enrolment setting is not allowed")
