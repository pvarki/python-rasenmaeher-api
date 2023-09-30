"""Schema for people."""
from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Extra


class CallSignPerson(BaseModel):
    """CallSignPerson schema for people list out response"""

    callsign: str
    roles: List[str]
    extra: Optional[Dict[str, Any]]


class PeopleListOut(BaseModel, extra=Extra.forbid):
    """People list out response schema"""

    callsign_list: List[CallSignPerson]
