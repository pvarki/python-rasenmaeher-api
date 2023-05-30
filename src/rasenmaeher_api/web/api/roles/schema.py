"""Schema for roles."""
from typing import Optional
from pydantic import BaseModel


class Placeholder(BaseModel):  # pylint: disable=too-few-public-methods
    """Simple roles model placeholder."""

    placeholder1: Optional[str]
    placeholder2: str
    placeholder3: Optional[str]
