"""Token exchange schemas"""
from pydantic import BaseModel, Field


class JWTExchangeRequestResponse(BaseModel):  # pylint: disable=too-few-public-methods
    """Exchange a TILAUSPALVELU single-use JWT for RASENMAEHER session JWT"""

    jwt: str = Field(description="The token")
