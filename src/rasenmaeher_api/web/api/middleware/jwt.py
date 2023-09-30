"""JWTBearer with nonce checking"""
from typing import Optional, Sequence
import logging

from multikeyjwt.middleware.jwtbearer import JWTBearer, JWTPayload
from fastapi import Request, HTTPException

from ....db import SeenToken

LOGGER = logging.getLogger(__name__)


class JWTwNonceSubFilter(JWTBearer):  # pylint: disable=too-few-public-methods
    """Extent JWTBearer to do some extra checks"""

    def __init__(
        self,
        *,
        auto_error: bool = True,
        description: Optional[str] = None,
        disallow_jwt_sub: Sequence[str] = ("tpadminsession",),  # disallow TILAUSPALVELU sessions by default
    ):
        super().__init__(description=description, auto_error=auto_error)
        self.auto_error = auto_error
        self.disallow_jwt_sub = disallow_jwt_sub

    async def __call__(self, request: Request) -> Optional[JWTPayload]:  # type: ignore[override]
        jwtrep = await super().__call__(request)
        if not jwtrep:
            return jwtrep
        if nonce := jwtrep.get("nonce"):
            await SeenToken.use_token(nonce)
        jwt_sub = jwtrep.get("sub")
        if jwt_sub in self.disallow_jwt_sub:
            raise HTTPException(status_code=403, detail="Subject not allowed")
        return jwtrep


__all__ = ["JWTPayload", "JWTwNonceSubFilter"]
