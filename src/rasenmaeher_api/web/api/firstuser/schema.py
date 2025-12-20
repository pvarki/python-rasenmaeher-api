"""Schema for enrollment."""

from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class FirstuserCheckCodeIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init in response schema"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "name": "normal",
                    "summary": "Description text",
                    "description": "This contains **description** of values.",
                    "value": {"temp_admin_code": "[str] - temporary init admin users string"},
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {"temp_admin_code": "some_permit_hash_abba_abc"},
                },
            ]
        },
    )

    temp_admin_code: str


class FirstuserCheckCodeOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema out"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "code_ok": "[bool] - True = Requested 'first use admin code' was found and can be used.",
            }
        },
    )

    code_ok: bool


class FirstuserAddAdminIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init in response schema"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "name": "normal",
                    "summary": "Description text",
                    "description": "This contains **description** of values.",
                    "value": {
                        "callsign": "[str] - id/name for new user that is elevated to admin",
                    },
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {"callsign": "porakoira666"},
                },
            ]
        },
    )

    # temp_admin_code: str
    callsign: str
    csr: Optional[str] = Field(default=None, description="CSR for mTLS key in PEM format")


class FirstuserAddAdminOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema out"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "admin_added": "[bool] - True = admin user were added",
                "jwt_exchange_code": "[str] - Code that can be exchanged to jwt token",
            }
        },
    )

    admin_added: bool
    jwt_exchange_code: str
