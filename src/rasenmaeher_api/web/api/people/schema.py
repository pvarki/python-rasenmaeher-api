"""Schema for people."""
from typing import List, Dict, Any

from pydantic import BaseModel, Extra


class PeopleListOut(BaseModel, extra=Extra.forbid):  # pylint: disable=too-few-public-methods
    """People list out response schema"""

    callsign_list: List[Dict[Any, Any]]
