"""Token exchange schemas"""
from typing import Any, Dict

from pydantic import BaseModel, Field, Extra


class JWTExchangeRequestResponse(BaseModel, extra=Extra.forbid):  # pylint: disable=too-few-public-methods
    """Exchange a TILAUSPALVELU single-use JWT for RASENMAEHER session JWT"""

    jwt: str = Field(description="The token")

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "examples": [
                {"jwt": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJw...jHv3f3MlSQswcHhM"},
            ]
        }


class LoginCodeCreateRequest(BaseModel, extra=Extra.forbid):  # pylint: disable=too-few-public-methods
    """TILAUSPALVELU asks us to create an one-time login code that user can input to a field.
    If TILAUSPALVELU wants to revoke a code it should just exchange it and discard the result"""

    claims: Dict[str, Any] = Field(description="The claims that should be issued when this token is redeemed")

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "examples": [
                {
                    "claims": {
                        "anon_admin_session": True,
                    },
                },
            ]
        }


class LoginCodeRequestResponse(BaseModel, extra=Extra.forbid):  # pylint: disable=too-few-public-methods
    """The response to LoginCodeCreateRequest and also used to exchange the code"""

    code: str = Field(description="The code user must provide to get a session JWT")

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "examples": [
                {
                    "code": "ABC1233GHIJ",
                },
            ]
        }
