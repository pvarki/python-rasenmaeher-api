"""Enrollment API views."""
from fastapi import APIRouter
from rasenmaeher_api.web.api.enrollment.schema import (
    EnrollmentStatusOut,
    EnrollmentInitIn,
    EnrollmentInitOut,
    EnrollmentDeliverOut,
    EnrollmentAcceptOut,
)

# from ....settings import settings, sqlite


router = APIRouter()


@router.get("/status/{work_id}", response_model=EnrollmentStatusOut)
async def request_enrolment_status(work_id: str) -> EnrollmentStatusOut:
    """
    TODO Check sqlite for status
    """

    return EnrollmentStatusOut(work_id=work_id, status="TODO_QWEQWEOQIWEOQIE")


@router.post("/init", response_model=EnrollmentInitOut)
async def request_enrollment_init(
    request: EnrollmentInitIn,
) -> EnrollmentInitOut:
    """
    TODO Post enrollment to sqlite
    TODO init enrollment in background?
    """

    return EnrollmentInitOut(work_id=request.work_id, enroll_str="1239871239817abbabc")


@router.get("/deliver/{enroll_str}", response_model=EnrollmentDeliverOut)
async def request_enrollment_status(enroll_str: str) -> EnrollmentDeliverOut:
    """
    TODO deliver enrollment download url if enrollment status is complete???
    """

    return EnrollmentDeliverOut(work_id="TODO_SOME_WORK_ID", enroll_str=enroll_str, download_url="https://kuvaton.com")


@router.post("/accept/{enroll_str}/{permit_str}", response_model=EnrollmentAcceptOut)
async def post_enrollment_accept(
    enroll_str: str,
    permit_str: str,
) -> EnrollmentAcceptOut:
    """
    TODO accept something in sqlite
    """

    return EnrollmentAcceptOut(work_id="TODO_SOME_WORK_ID", enroll_str=enroll_str, permit_str=permit_str)
