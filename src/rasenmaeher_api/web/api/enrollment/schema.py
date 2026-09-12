"""Schema for enrollment."""

from typing import Any

from libpvarki.schemas.generic import OperationResultResponse
from pydantic import BaseModel, ConfigDict, Field


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
    csr: str | None = Field(description="CSR for mTLS key in PEM format", default=None)
    mdm: bool = Field(
        description=(
            "Mark this as a device enrolment planned for an MDM. The device supplies its own CSR later and an "
            "MDM agent completes the enrolment; no JWT is issued to the caller and approving it by hand is refused."
        ),
        default=False,
    )


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
        description=(
            "JWT that allows client to check enrollment approval status and fetc mTLS certs when approved. "
            "Empty for enrolments planned for an MDM: nobody should be holding a device's credential."
        )
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
        description=(
            "Approval code for the callsign, this must have been delivered by the person to be enrolled. "
            "Not used when an MDM agent completes a planned device enrolment: there is no human to deliver it, "
            "and the agent has authenticated with its own certificate."
        ),
        default="",
    )
    csr: str | None = Field(
        description=(
            "CSR the device generated, PEM. Only for an MDM agent completing an enrolment planned with mdm=true."
        ),
        default=None,
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


class EnrollmentAcceptResultOut(OperationResultResponse):
    """Result of accepting an enrollment

    Additive superset of the plain result: an MDM agent gets the issued certificate back here
    rather than fetching it afterwards. It has no user credential to fetch it with, and in a
    meshed deployment its own service identity would win over any bearer token anyway.
    """

    certificate: str | None = Field(
        description="Issued certificate, PEM. Only set when an MDM agent completed the enrolment.",
        default=None,
    )


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

    callsign_list: list[dict[Any, Any]]


class EnrollmentPoolListItem(BaseModel, extra="forbid"):
    """Items for EnrollmentPoolListOut"""

    invitecode: str = Field(description="The invitation code")
    active: bool = Field(description="Is this pool currently active, ie can it be used")
    owner_cs: str = Field(description="Pool wwners callsign")
    created: str = Field(description="ISO datetime of when this pool was created")


class EnrollmentPoolListOut(BaseModel, extra="forbid"):
    """Enrollment pools list out response schema"""

    pools: list[EnrollmentPoolListItem] = Field(description="The pools")


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
    csr: str | None = Field(description="CSR for mTLS key in PEM format", default=None)


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
