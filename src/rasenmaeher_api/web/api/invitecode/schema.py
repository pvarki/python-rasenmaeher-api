"""Schema for enrollment."""
from typing import List
from pydantic import BaseModel, Extra, Field


class EnrollmentInitOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    callsign: str = Field(description="Callsign for which the enrollment got initialized")
    approvecode: str = Field(description="Code used to approve the enrollment, must be delivered to an admin")
    jwt: str = Field(
        description="JWT that allows client to check enrollment approval status and fetc mTLS certs when approved"
    )

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "example": {
                "callsign": "OTTER01a",
                "approvecode": "12DFEE34555",
                "jwt": "...",
            }
        }


class EnrollmentIsInvitecodeActiveOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema out"""

    invitecode_is_active: bool

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "example": {
                "invitecode_is_active": "[bool] - True = this code can still be used",
            }
        }


class EnrollmentPoolListItem(BaseModel, extra=Extra.forbid):  # pylint: disable=too-few-public-methods
    """Items for EnrollmentPoolListOut"""

    invitecode: str = Field(description="The invitation code")
    active: bool = Field(description="Is this pool currently active, ie can it be used")
    owner_cs: str = Field(description="Pool wwners callsign")
    created: str = Field(description="ISO datetime of when this pool was created")


class EnrollmentPoolListOut(BaseModel, extra=Extra.forbid):  # pylint: disable=too-few-public-methods
    """Enrollment pools list out response schema"""

    pools: List[EnrollmentPoolListItem] = Field(description="The pools")


class EnrollmentInviteCodeCreateOut(BaseModel, extra=Extra.forbid):  # pylint: disable=too-few-public-methods
    """Enrollment Invite code response schema"""

    invite_code: str


class EnrollmentInviteCodeEnrollIn(BaseModel):
    """Enrollment Enrollment Invite code request schema"""

    callsign: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "examples": [
                {
                    "callsign": "[str] User defined username/id/callsign",
                },
            ]
        }
