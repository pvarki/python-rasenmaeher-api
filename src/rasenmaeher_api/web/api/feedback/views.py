"""Feedback API views.

Proxies the app's feedback dialog to the ingest endpoint the operator configured,
so that the ingest URL and key stay server-side and are never shipped in the
frontend bundle. RASENMAEHER does not care what the far end is, it only has to
accept a JSON POST.
"""

import logging
import os
from uuid import uuid4

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request

from ....db.people import Person
from ....rmsettings import RMSettings
from ..middleware.user import ValidUser
from ..utils.auditcontext import build_audit_extra, get_audit_request_context
from .schema import FeedbackIn, FeedbackOut

router = APIRouter()
LOGGER = logging.getLogger(__name__)


def _deployment_version() -> str:
    """Release tag of this deployment, same values the healthcheck reports."""
    version = os.environ.get("RELEASE_TAG", "undefined")
    if release_status := os.environ.get("RELEASE_STATUS", ""):
        version += f"-{release_status}"
    return version


@router.post("")
async def submit_feedback(
    feedback: FeedbackIn,
    request: Request,
    person: Person | None = Depends(ValidUser()),
) -> FeedbackOut:
    """Forward a feedback submission to the configured ingest."""
    conf = RMSettings.singleton()
    if not conf.feedback_ingest_url or not conf.feedback_ingest_key:
        LOGGER.error("Feedback ingest is not configured (RM_FEEDBACK_INGEST_URL / RM_FEEDBACK_INGEST_KEY missing)")
        raise HTTPException(status_code=503, detail="Feedback submission is not configured")

    source_ip = get_audit_request_context(request).get("source.ip", "unknown")
    callsign = person.callsign if person else None
    # Which deployment and release this came from is resolved here rather than trusted
    # from the client, the browser has no business asserting it.
    deployment = conf.deployment_name

    # Not every ingest renders the structured keys, so the triage metadata is also folded
    # into the message body. Keep both, the duplication is cheaper than a lost bug report.
    metadata_lines = [
        f"{label}: {value}"
        for label, value in (
            ("role", feedback.role),
            ("os", feedback.os),
            ("version", feedback.version),
            ("deployment", deployment),
            ("page", feedback.web_address),
        )
        if value
    ]
    message = feedback.comments
    if metadata_lines:
        message = f"{feedback.comments}\n\n" + "\n".join(metadata_lines)

    payload = {
        "id": str(uuid4()),
        "subject": f"{deployment} feedback: {feedback.rating}",
        "message": message,
        "name": callsign,
        "rating": feedback.rating,
        "role": feedback.role,
        "os": feedback.os,
        "version": feedback.version,
        "deployment": deployment,
        "deployment_version": _deployment_version(),
        "web_address": feedback.web_address,
    }

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=conf.feedback_timeout)) as session:
            headers = {
                "content-type": "application/json",
                conf.feedback_ingest_key_header: conf.feedback_ingest_key,
                "x-forwarded-for": source_ip,
            }
            async with session.post(conf.feedback_ingest_url, json=payload, headers=headers) as response:
                if response.status == 429:
                    LOGGER.warning("Feedback ingest rate-limited the submission")
                    raise HTTPException(status_code=429, detail="Too many feedback submissions, try again shortly")
                response.raise_for_status()
    except aiohttp.ClientError as exc:
        LOGGER.error(
            "Failed to forward feedback to ingest: %s",
            exc,
            extra=build_audit_extra(action="feedback.submit", outcome="failure", actor=callsign, request=request),
        )
        raise HTTPException(status_code=502, detail="Could not submit feedback, please try again") from exc
    except TimeoutError as exc:
        LOGGER.error(
            "Timed out forwarding feedback to ingest",
            extra=build_audit_extra(action="feedback.submit", outcome="failure", actor=callsign, request=request),
        )
        raise HTTPException(status_code=502, detail="Could not submit feedback, please try again") from exc

    LOGGER.audit(  # type: ignore[attr-defined]
        "Feedback submitted",
        extra=build_audit_extra(action="feedback.submit", outcome="success", actor=callsign, request=request),
    )
    return FeedbackOut(ok=True)
