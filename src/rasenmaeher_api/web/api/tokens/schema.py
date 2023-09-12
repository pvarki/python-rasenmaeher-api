"""Token exchange schemas"""
from typing import Any, Dict
from pydantic import BaseModel, Field


class JWTExchangeRequestResponse(BaseModel):  # pylint: disable=too-few-public-methods
    """Exchange a TILAUSPALVELU single-use JWT for RASENMAEHER session JWT"""

    jwt: str = Field(description="The token")


class LoginCodeCreateRequest(BaseModel):  # pylint: disable=too-few-public-methods
    """TILAUSPALVELU asks us to create an one-time login code that user can input to a field.
    If TILAUSPALVELU wants to revoke a code it should just exchange it and discard the result"""

    claims: Dict[str, Any] = Field(description="The claims that should be issued when this token is redeemed")


class LoginCodeRequestResponse(BaseModel):  # pylint: disable=too-few-public-methods
    """The response to LoginCodeCreateRequest and also used to exchange the code"""

    code: str = Field(description="The code user must provide to get a session JWT")
