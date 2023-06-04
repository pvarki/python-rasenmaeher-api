"""Schema for enrollment."""
from typing import Optional
from pydantic import BaseModel


class EnrollmentConfigSetStateIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema in"""

    permit_str: str
    state: str
    work_id: Optional[str]
    enroll_str: Optional[str]


class EnrollmentConfigSetStateOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema out"""

    success: bool
    reason: Optional[str]


class EnrollmentConfigSetDLIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema in"""

    permit_str: str
    download_link: str
    work_id: Optional[str]
    enroll_str: Optional[str]


class EnrollmentConfigSetDLOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema out"""

    success: bool
    reason: Optional[str]


class EnrollmentConfigAddManagerIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema in"""

    permit_str: str
    new_permit_hash: str
    permissions_str: str


class EnrollmentConfigAddManagerOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment config add manager schema out"""

    success: bool
    reason: Optional[str]


class EnrollmentStatusOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment status check schema"""

    status: str
    work_id: str
    success: bool
    reason: Optional[str]


class EnrollmentInitIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init in response schema"""

    work_id: str


class EnrollmentInitOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    work_id: str
    enroll_str: str
    success: bool
    reason: Optional[str]


class EnrollmentDeliverOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    work_id: str
    enroll_str: str
    download_url: str
    success: bool
    reason: Optional[str]
    state: Optional[str]


class EnrollmentAcceptIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    enroll_str: str
    permit_str: str


class EnrollmentAcceptOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    work_id: str
    enroll_str: str
    permit_str: str
    success: bool
    reason: Optional[str]
