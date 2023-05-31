"""Schema for enrollment."""
from pydantic import BaseModel


class EnrollmentStatusOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment status check schema"""

    status: str
    work_id: str


class EnrollmentInitIn(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init in response schema"""

    work_id: str


class EnrollmentInitOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    work_id: str
    enroll_str: str


class EnrollmentDeliverOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    work_id: str
    enroll_str: str
    download_url: str


class EnrollmentAcceptOut(BaseModel):  # pylint: disable=too-few-public-methods
    """Enrollment init out response schema"""

    work_id: str
    enroll_str: str
    permit_str: str
