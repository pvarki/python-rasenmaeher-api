"""Schema for enrollment."""
from typing import List, Dict, Any

from pydantic import BaseModel, Extra


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

    work_id: str


class EnrollmentStatusOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment status check schema"""

    status: int
    work_id: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "example": {
                "state": "[int] - Current state of enrollment",
                "work_id": "[str] User defined username/id/workname",
            }
        }


class EnrollmentShowVerificationCodeIn(BaseModel, extra=Extra.forbid):  # pylint: disable=too-few-public-methods
    """Enrollment status in schema"""

    verification_code: str


class EnrollmentShowVerificationCodeOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment status check schema"""

    state: str
    work_id: str
    accepted: str
    locked: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "example": {
                "state": "[str] - Current state of enrollment",
                "work_id": "[str] User defined username/id/workname",
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

    work_id: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "examples": [
                {
                    "name": "normal",
                    "summary": "Description text",
                    "description": "This containts **description** of values.",
                    "value": {
                        "work_id": "[str] - Plain text enrollment role id",
                    },
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** of values.",
                    "value": {
                        "work_id": "taikaponi",
                    },
                },
            ]
        }


class EnrollmentInitOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    work_id: str
    jwt: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "example": {
                "work_id": "[str] User defined username/id/workname",
                "jwt": "[str] jwt token needed for later use",
            }
        }


class EnrollmentDeliverIn(BaseModel, extra=Extra.forbid):  # pylint: disable=too-few-public-methods
    """Enrollment promote in schema"""

    work_id_hash: str


class EnrollmentDeliverOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    work_id: str
    work_id_hash: str
    cert_download_link: str
    howto_download_link: str
    mtls_test_link: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "example": {
                "work_id": "[str] User defined username/id/workname",
                "work_id_hash": "[str] - Hash string for work_id",
                "cert_download_link": "[str] - Link where certificate package can be downloaded",
                "howto_download_link": "[str] - Link where certificate install howto can be downloaded",
                "mtls_test_link": "[str] - Link that can be used to test mtls connection",
            }
        }


class EnrollmentAcceptIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    work_id: str

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
                        "work_id": "[str] - Enrollment callsign.",
                    },
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** values.",
                    "value": {
                        "work_id": "kissa123",
                    },
                },
            ]
        }


class EnrollmentAcceptOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    work_id: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "example": {
                "work_id": "[str] - Username/work_id/callsign",
            }
        }


class EnrollmentPromoteIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment promote in schema"""

    work_id: str

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
                        "work_id": "[str] User defined username/id/workname",
                    },
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** values.",
                    "value": {
                        "work_id": "kissa123",
                    },
                },
            ]
        }


class EnrollmentDemoteIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment demote in schema"""

    work_id: str

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
                        "work_id": "[str] User defined username/id/workname",
                    },
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** values.",
                    "value": {
                        "work_id": "kissa123",
                    },
                },
            ]
        }


class EnrollmentLockIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment lock in schema"""

    lock_reason: str
    work_id: str

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
                        "work_id": "[str] User defined username/id/workname",
                    },
                },
                {
                    "name": "with_values",
                    "summary": "Example values",
                    "description": "**Example** values.",
                    "value": {
                        "work_id": "kissa123",
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

    work_id_list: List[Dict[Any, Any]]


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
    work_id: str

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "examples": [
                {
                    "invite_code": "[str] - Code that is used validate enrollment init for work_id",
                    "work_id": "[str] User defined username/id/workname",
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
