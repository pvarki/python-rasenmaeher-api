"""Middlewares"""
from typing import Union, Optional
from dataclasses import dataclass, field
import enum

from multikeyjwt.middleware.jwtbearer import JWTBearer, JWTPayload
from libpvarki.middleware.mtlsheader import MTLSHeader, DNDict
from fastapi import Request, HTTPException


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


class MTLSorJWT(JWTBearer, MTLSHeader):  # pylint: disable=too-few-public-methods
    """Auth either by JWT or mTLS header"""

    async def __call__(self, request: Request) -> Optional[MTLSorJWTPayload]:  # type: ignore[override]
        jwtdep = JWTBearer(auto_error=False)
        mtlsdep = MTLSHeader(auto_error=False)
        if mtlsrep := await mtlsdep(request=request):
            request.state.jwtormtls = MTLSorJWTPayload(
                type=MTLSorJWTPayloadType.MTLS, userid=mtlsrep.get("CN"), payload=mtlsrep
            )
            return request.state.jwtormtls
        if jwtrep := await jwtdep(request=request):
            request.state.jwtormtls = MTLSorJWTPayload(
                type=MTLSorJWTPayloadType.JWT, userid=jwtrep.get("sub"), payload=jwtrep
            )
            return request.state.jwtormtls
        if self.auto_error:
            raise HTTPException(status_code=403, detail="Not authenticated")
        request.state.jwtormtls = None
        return request.state.jwtormtls
