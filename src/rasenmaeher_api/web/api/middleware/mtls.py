"""Middleware to handle mTLS or JWT auth"""

from typing import Optional, Sequence
import logging

from multikeyjwt.middleware.jwtbearer import JWTBearer
from libpvarki.middleware.mtlsheader import MTLSHeader
from fastapi import Request, HTTPException
from fastapi.security.http import HTTPBase


from .datatypes import MTLSorJWTPayload, MTLSorJWTPayloadType

LOGGER = logging.getLogger(__name__)


class MTLSorJWT(HTTPBase):  # pylint: disable=too-few-public-methods
    """Auth either by JWT or mTLS header"""

    def __init__(  # pylint: disable=R0913
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
            jwt_sub = jwtrep.get("sub")
            if jwt_sub in self.disallow_jwt_sub:
                raise HTTPException(status_code=403, detail="Subject not allowed")
            request.state.mtls_or_jwt = MTLSorJWTPayload(type=MTLSorJWTPayloadType.JWT, userid=jwt_sub, payload=jwtrep)
            return request.state.mtls_or_jwt
        if self.auto_error:
            raise HTTPException(status_code=403, detail="Not authenticated")
        request.state.mtls_or_jwt = None
        return request.state.mtls_or_jwt
