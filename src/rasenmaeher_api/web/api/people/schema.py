"""Schema for people."""

from typing import Any

from pydantic import BaseModel


class CallSignPerson(BaseModel):
    """CallSignPerson schema for people list out response"""

    callsign: str
    roles: list[str]
    extra: dict[str, Any] | None
    revoked: str | None
    #: When the person's certificate stops being valid, as ISO 8601 in UTC; None when it is not known
    cert_ends: str | None = None


class PeopleListOut(BaseModel, extra="forbid"):
    """People list out response schema"""

    callsign_list: list[CallSignPerson]
