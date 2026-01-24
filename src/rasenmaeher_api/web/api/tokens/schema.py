"""Token exchange schemas"""

from typing import Any, Dict

from pydantic import BaseModel, Field, ConfigDict


class JWTExchangeRequestResponse(BaseModel):  # pylint: disable=too-few-public-methods
    """Exchange a TILAUSPALVELU single-use JWT for RASENMAEHER session JWT"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"jwt": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJw...jHv3f3MlSQswcHhM"},
            ]
        },
    )

    jwt: str = Field(description="The token")


class LoginCodeCreateRequest(BaseModel):  # pylint: disable=too-few-public-methods
    """TILAUSPALVELU asks us to create an one-time login code that user can input to a field.
    If TILAUSPALVELU wants to revoke a code it should just exchange it and discard the result"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "claims": {
                        "anon_admin_session": True,
                    },
                },
            ]
        },
    )

    claims: Dict[str, Any] = Field(description="The claims that should be issued when this token is redeemed")


class LoginCodeRequestResponse(BaseModel):  # pylint: disable=too-few-public-methods
    """The response to LoginCodeCreateRequest and also used to exchange the code"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "code": "ABC1233GHIJ",
                },
            ]
        },
    )

    code: str = Field(description="The code user must provide to get a session JWT")
