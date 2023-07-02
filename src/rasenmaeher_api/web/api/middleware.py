"""Middlewares"""
from typing import Union, Optional, Sequence
from dataclasses import dataclass, field
import enum

from multikeyjwt.middleware.jwtbearer import JWTBearer, JWTPayload
from libpvarki.middleware.mtlsheader import MTLSHeader, DNDict
from fastapi import Request, HTTPException
from fastapi.security.http import HTTPBase


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


class MTLSorJWT(HTTPBase):  # pylint: disable=too-few-public-methods
    """Auth either by JWT or mTLS header"""

    def __init__(
        self,
        *,
        scheme: str = "header",
        scheme_name: Optional[str] = None,
        description: Optional[str] = None,
        auto_error: bool = True,
        disallow_jwt_sub: Sequence[str] = ("tpadminsession",),  # disallow TILAUSPALVELU sessions by default
    ):
        """initializer"""
        self.scheme_name = scheme_name or self.__class__.__name__
        super().__init__(scheme=scheme, scheme_name=scheme_name, description=description, auto_error=auto_error)
        self.auto_error = auto_error
        self.disallow_jwt_sub = disallow_jwt_sub

    async def __call__(self, request: Request) -> Optional[MTLSorJWTPayload]:  # type: ignore[override]
        jwtdep = JWTBearer(auto_error=False)
        mtlsdep = MTLSHeader(auto_error=False)
        if mtlsrep := await mtlsdep(request=request):
            request.state.mtls_or_jwt = MTLSorJWTPayload(
                type=MTLSorJWTPayloadType.MTLS, userid=mtlsrep.get("CN"), payload=mtlsrep
            )
            return request.state.mtls_or_jwt
        if jwtrep := await jwtdep(request=request):
            if jwtrep["sub"] in self.disallow_jwt_sub:
                raise HTTPException(status_code=403, detail="Subject not allowed")
            request.state.mtls_or_jwt = MTLSorJWTPayload(
                type=MTLSorJWTPayloadType.JWT, userid=jwtrep.get("sub"), payload=jwtrep
            )
            return request.state.mtls_or_jwt
        if self.auto_error:
            raise HTTPException(status_code=403, detail="Not authenticated")
        request.state.mtls_or_jwt = None
        return request.state.mtls_or_jwt
