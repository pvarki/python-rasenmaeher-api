"""Schema for enrollment."""
from typing import List, Dict, Any

from pydantic import BaseModel, Extra, Field


class EnrollmentGenVerifiOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment gen verification code out"""

    verification_code: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {"example": {"verification_code": "[str] Generated verification code for enrollment."}}


class EnrollmentConfigTaskDone(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema out"""

    success_message: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "example": {
                "success_message": "[str] - Task completed message",
            }
        }


class EnrollmentStatusIn(BaseModel, extra=Extra.forbid):  # pylint: disable=too-few-public-methods
    """Enrollment status in schema"""

    callsign: str


class EnrollmentStatusOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment status check schema"""

    status: int
    callsign: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "example": {
                "state": "[int] - Current state of enrollment",
                "callsign": "[str] User defined username/id/callsign",
            }
        }


class EnrollmentShowVerificationCodeIn(BaseModel, extra=Extra.forbid):  # pylint: disable=too-few-public-methods
    """Enrollment status in schema"""

    verification_code: str


class EnrollmentShowVerificationCodeOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment status check schema"""

    state: str
    callsign: str
    accepted: str
    locked: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "example": {
                "state": "[str] - Current state of enrollment",
                "callsign": "[str] User defined username/id/callsign",
                "accepted": "[str] - Has this been already accepted, empty or 'na' == not accepted",
                "locked": "[str] - Contain info if the enrollment is locked. For unlocked enrollment, it's empty ''",
            }
        }


class EnrollmentHaveIBeenAcceptedOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment status check schema"""

    have_i_been_accepted: bool

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "example": {
                "have_i_been_accepted": "[bool] - Accepted status. True/False",
            }
        }


class EnrollmentInitIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init in response schema"""

    callsign: str = Field(description="Callsign to create enrollment for")

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "examples": [
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {
                        "callsign": "taikaponi",
                    },
                },
            ]
        }


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


class EnrollmentDeliverIn(BaseModel, extra=Extra.forbid):  # pylint: disable=too-few-public-methods
    """Enrollment promote in schema"""

    callsign_hash: str


class EnrollmentDeliverOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    callsign: str
    callsign_hash: str
    cert_download_link: str
    howto_download_link: str
    mtls_test_link: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "example": {
                "callsign": "[str] User defined username/id/callsign",
                "callsign_hash": "[str] - Hash string for callsign",
                "cert_download_link": "[str] - Link where certificate package can be downloaded",
                "howto_download_link": "[str] - Link where certificate install howto can be downloaded",
                "mtls_test_link": "[str] - Link that can be used to test mtls connection",
            }
        }


class EnrollmentAcceptIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    callsign: str = Field(description="Callsign to approve")
    approvecode: str = Field(
        description="Approval code for the callsign, this must have been delivered by the person to be enrolled"
    )

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "examples": [
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** values.",
                    "value": {
                        "callsign": "kissa123",
                        "approvecode": "HGRTR43267",
                    },
                },
            ]
        }


class EnrollmentAcceptOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    callsign: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "example": {
                "callsign": "[str] - Username/callsign/callsign",
            }
        }


class EnrollmentPromoteIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment promote in schema"""

    callsign: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "examples": [
                {
                    "name": "normal",
                    "summary": "Description text",
                    "description": "This contains **description** of values.",
                    "value": {
                        "callsign": "[str] User defined username/id/callsign",
                    },
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** values.",
                    "value": {
                        "callsign": "kissa123",
                    },
                },
            ]
        }


class EnrollmentDemoteIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment demote in schema"""

    callsign: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "examples": [
                {
                    "name": "normal",
                    "summary": "Description text",
                    "description": "This contains **description** of values.",
                    "value": {
                        "callsign": "[str] User defined username/id/callsign",
                    },
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** values.",
                    "value": {
                        "callsign": "kissa123",
                    },
                },
            ]
        }


class EnrollmentLockIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment lock in schema"""

    lock_reason: str
    callsign: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "examples": [
                {
                    "name": "normal",
                    "summary": "Description text",
                    "description": "This contains **description** of values.",
                    "value": {
                        "callsign": "[str] User defined username/id/callsign",
                    },
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** values.",
                    "value": {
                        "callsign": "kissa123",
                    },
                },
            ]
        }


class EnrollmentIsInvitecodeActiveIn(BaseModel):
    """Enrollment check if invitecode is still active"""

    invitecode: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "examples": [
                {"invitecode": "[str] - Code that can be used to validate enrollment init"},
            ]
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


class EnrollmentListOut(BaseModel, extra=Extra.forbid):  # pylint: disable=too-few-public-methods
    """Enrollment list out response schema"""

    callsign_list: List[Dict[Any, Any]]


class EnrollmentInviteCodeCreateOut(BaseModel, extra=Extra.forbid):  # pylint: disable=too-few-public-methods
    """Enrollment Invite code response schema"""

    invite_code: str


class EnrollmentInviteCodeDeactivateIn(BaseModel):
    """Enrollment Invite code deactivate request schema"""

    invite_code: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "examples": [
                {"invite_code": "[str] - Invite code that will be deactivated"},
            ]
        }


class EnrollmentInviteCodeDeactivateOut(BaseModel, extra=Extra.forbid):  # pylint: disable=too-few-public-methods
    """Enrollment Invite code deactivate response schema"""

    invite_code: str


class EnrollmentInviteCodeActivateIn(BaseModel):
    """Enrollment Invite code activate request schema"""

    invite_code: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "examples": [
                {"invite_code": "[str] - Invite code that will be reactivated"},
            ]
        }


class EnrollmentInviteCodeActivateOut(BaseModel, extra=Extra.forbid):  # pylint: disable=too-few-public-methods
    """Enrollment Invite code activate response schema"""

    invite_code: str


class EnrollmentInviteCodeEnrollIn(BaseModel):
    """Enrollment Enrollment Invite code request schema"""

    invite_code: str
    callsign: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "examples": [
                {
                    "invite_code": "[str] - Code that is used validate enrollment init for callsign",
                    "callsign": "[str] User defined username/id/callsign",
                },
            ]
        }


class EnrollmentInviteCodeDeleteIn(BaseModel):
    """Enrollment Invite code deactivate request schema"""

    invite_code: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "examples": [
                {"invite_code": "[str] - Invite code that will be removed."},
            ]
        }


class EnrollmentInviteCodeDeleteOut(BaseModel, extra=Extra.forbid):  # pylint: disable=too-few-public-methods
    """Enrollment Invite code deactivate response schema"""

    invite_code: str
