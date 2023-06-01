"""Schema for enrollment."""
from typing import Optional
from pydantic import BaseModel


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
    status: Optional[str]
    reason: Optional[str]


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
