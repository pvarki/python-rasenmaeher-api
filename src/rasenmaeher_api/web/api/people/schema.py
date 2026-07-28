"""Schema for people."""

from typing import Any

from pydantic import BaseModel


class CallSignPerson(BaseModel):
    """CallSignPerson schema for people list out response"""

    callsign: str
    roles: list[str]
    extra: dict[str, Any] | None
    revoked: str | None


class PeopleListOut(BaseModel, extra="forbid"):
    """People list out response schema"""

    callsign_list: list[CallSignPerson]
