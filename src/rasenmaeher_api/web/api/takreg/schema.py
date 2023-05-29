"""Schema for takreg."""
from typing import Optional
from pydantic import BaseModel


class Certificates(BaseModel):  # pylint: disable=too-few-public-methods
    """Simple takreg model."""

    ca: Optional[str]
    csr: str
    certificate: Optional[str]
