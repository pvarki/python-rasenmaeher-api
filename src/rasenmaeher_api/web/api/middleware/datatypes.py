"""Data types needed by this module"""
from typing import Union, Optional
from dataclasses import dataclass, field
import enum

from multikeyjwt.middleware.jwtbearer import JWTPayload
from libpvarki.middleware.mtlsheader import DNDict


class MTLSorJWTPayloadType(enum.Enum):
    """Valid payload types"""

    JWT = "jwt"
    MTLS = "mtls"


@dataclass
class MTLSorJWTPayload:
    """payload either from mTLS or JWT auth"""

    type: MTLSorJWTPayloadType = field()
    userid: Optional[str] = field()
    payload: Union[DNDict, JWTPayload] = field()
