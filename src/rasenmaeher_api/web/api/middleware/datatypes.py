"""Data types needed by this module"""

import enum
from dataclasses import dataclass, field

from libpvarki.middleware.mtlsheader import DNDict
from multikeyjwt.middleware.jwtbearer import JWTPayload


class MTLSorJWTPayloadType(enum.Enum):
    """Valid payload types"""

    JWT = "jwt"
    MTLS = "mtls"


@dataclass
class MTLSorJWTPayload:
    """payload either from mTLS or JWT auth"""

    type: MTLSorJWTPayloadType = field()
    userid: str | None = field()
    payload: DNDict | JWTPayload = field()
