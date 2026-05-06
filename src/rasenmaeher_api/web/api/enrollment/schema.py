"""Schema for enrollment."""

from typing import List, Dict, Any, Optional

from pydantic import BaseModel, Field, ConfigDict


class EnrollmentGenVerifiOut(BaseModel):
    """Enrollment gen verification code out"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={"example": {"verification_code": "[str] Generated verification code for enrollment."}},
    )

    verification_code: str


class EnrollmentConfigTaskDone(BaseModel):
    """Enrollment config add manager schema out"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "success_message": "[str] - Task completed message",
            }
        },
    )

    success_message: str


class EnrollmentStatusIn(BaseModel, extra="forbid"):
    """Enrollment status in schema"""

    callsign: str


class EnrollmentStatusOut(BaseModel):
    """Enrollment status check schema"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "state": "[int] - Current state of enrollment",
                "callsign": "[str] User defined username/id/callsign",
            }
        },
    )

    status: int
    callsign: str


class EnrollmentShowVerificationCodeIn(BaseModel, extra="forbid"):
    """Enrollment status in schema"""

    verification_code: str


class EnrollmentShowVerificationCodeOut(BaseModel):
    """Enrollment status check schema"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "state": "[str] - Current state of enrollment",
                "callsign": "[str] User defined username/id/callsign",
                "accepted": "[str] - Has this been already accepted, empty or 'na' == not accepted",
                "locked": "[str] - Contain info if the enrollment is locked. For unlocked enrollment, it's empty ''",
            }
        },
    )

    state: str
    callsign: str
    accepted: str
    locked: str


class EnrollmentHaveIBeenAcceptedOut(BaseModel):
    """Enrollment status check schema"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "have_i_been_accepted": "[bool] - Accepted status. True/False",
            }
        },
    )

    have_i_been_accepted: bool


class EnrollmentInitIn(BaseModel):
    """Enrollment init in response schema"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
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
        },
    )

    callsign: str = Field(description="Callsign to create enrollment for")
    csr: Optional[str] = Field(description="CSR for mTLS key in PEM format", default=None)


class EnrollmentInitOut(BaseModel):
    """Enrollment init out response schema"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "callsign": "OTTER01a",
                "approvecode": "12DFEE34555",
                "jwt": "...",
            }
        },
    )

    callsign: str = Field(description="Callsign for which the enrollment got initialized")
    approvecode: str = Field(description="Code used to approve the enrollment, must be delivered to an admin")
    jwt: str = Field(
        description="JWT that allows client to check enrollment approval status and fetc mTLS certs when approved"
    )


class EnrollmentDeliverIn(BaseModel, extra="forbid"):
    """Enrollment promote in schema"""

    callsign_hash: str


class EnrollmentDeliverOut(BaseModel):
    """Enrollment init out response schema"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "callsign": "[str] User defined username/id/callsign",
                "callsign_hash": "[str] - Hash string for callsign",
                "cert_download_link": "[str] - Link where certificate package can be downloaded",
                "howto_download_link": "[str] - Link where certificate install howto can be downloaded",
                "mtls_test_link": "[str] - Link that can be used to test mtls connection",
            }
        },
    )

    callsign: str
    callsign_hash: str
    cert_download_link: str
    howto_download_link: str
    mtls_test_link: str


class EnrollmentAcceptIn(BaseModel):
    """Enrollment init out response schema"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
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
        },
    )

    callsign: str = Field(description="Callsign to approve")
    approvecode: str = Field(
        description="Approval code for the callsign, this must have been delivered by the person to be enrolled"
    )


class EnrollmentAcceptOut(BaseModel):
    """Enrollment init out response schema"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "callsign": "[str] - Username/callsign/callsign",
            }
        },
    )

    callsign: str


class EnrollmentPromoteIn(BaseModel):
    """Enrollment promote in schema"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
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
        },
    )

    callsign: str


class EnrollmentDemoteIn(BaseModel):
    """Enrollment demote in schema"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
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
        },
    )

    callsign: str


class EnrollmentLockIn(BaseModel):
    """Enrollment lock in schema"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
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
        },
    )

    lock_reason: str
    callsign: str


class EnrollmentIsInvitecodeActiveIn(BaseModel):
    """Enrollment check if invitecode is still active"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"invitecode": "[str] - Code that can be used to validate enrollment init"},
            ]
        },
    )

    invitecode: str


class EnrollmentIsInvitecodeActiveOut(BaseModel):
    """Enrollment config add manager schema out"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "invitecode_is_active": "[bool] - True = this code can still be used",
            }
        },
    )

    invitecode_is_active: bool


class EnrollmentListOut(BaseModel, extra="forbid"):
    """Enrollment list out response schema"""

    callsign_list: List[Dict[Any, Any]]


class EnrollmentPoolListItem(BaseModel, extra="forbid"):
    """Items for EnrollmentPoolListOut"""

    invitecode: str = Field(description="The invitation code")
    active: bool = Field(description="Is this pool currently active, ie can it be used")
    owner_cs: str = Field(description="Pool wwners callsign")
    created: str = Field(description="ISO datetime of when this pool was created")


class EnrollmentPoolListOut(BaseModel, extra="forbid"):
    """Enrollment pools list out response schema"""

    pools: List[EnrollmentPoolListItem] = Field(description="The pools")


class EnrollmentInviteCodeCreateOut(BaseModel, extra="forbid"):
    """Enrollment Invite code response schema"""

    invite_code: str


class EnrollmentInviteCodeDeactivateIn(BaseModel):
    """Enrollment Invite code deactivate request schema"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"invite_code": "[str] - Invite code that will be deactivated"},
            ]
        },
    )

    invite_code: str


class EnrollmentInviteCodeDeactivateOut(BaseModel, extra="forbid"):
    """Enrollment Invite code deactivate response schema"""

    invite_code: str


class EnrollmentInviteCodeActivateIn(BaseModel):
    """Enrollment Invite code activate request schema"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"invite_code": "[str] - Invite code that will be reactivated"},
            ]
        },
    )

    invite_code: str


class EnrollmentInviteCodeActivateOut(BaseModel, extra="forbid"):
    """Enrollment Invite code activate response schema"""

    invite_code: str


class EnrollmentInviteCodeEnrollIn(BaseModel):
    """Enrollment Enrollment Invite code request schema"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "invite_code": "[str] - Code that is used validate enrollment init for callsign",
                    "callsign": "[str] User defined username/id/callsign",
                },
            ]
        },
    )

    invite_code: str
    callsign: str
    csr: Optional[str] = Field(description="CSR for mTLS key in PEM format", default=None)


class EnrollmentInviteCodeDeleteIn(BaseModel):
    """Enrollment Invite code deactivate request schema"""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {"invite_code": "[str] - Invite code that will be removed."},
            ]
        },
    )

    invite_code: str
