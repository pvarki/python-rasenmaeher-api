"""Feedback API views.

Proxies the app's feedback dialog to JOKE so the ingest URL and secret stay
server-side and are never shipped in the frontend bundle.
"""

import logging
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


@router.post("")
async def submit_feedback(
    feedback: FeedbackIn,
    request: Request,
    person: Person | None = Depends(ValidUser(auto_error=False)),
) -> FeedbackOut:
    """Forward a feedback submission to JOKE."""
    conf = RMSettings.singleton()
    if not conf.joke_ingest_url or not conf.joke_ingest_key:
        LOGGER.error("JOKE ingest is not configured (RM_JOKE_INGEST_URL / RM_JOKE_INGEST_KEY missing)")
        raise HTTPException(status_code=503, detail="Feedback submission is not configured")

    source_ip = get_audit_request_context(request).get("source.ip", "unknown")
    callsign = person.callsign if person else None

    # JOKE's embed-form ingest only reliably renders `message` as visible content, so the
    # metadata that matters for triage (version, platform) is folded into the
    # body text itself rather than relying on it being surfaced from the extra JSON keys.
    metadata_lines = [
        f"{label}: {value}"
        for label, value in (
            ("role", feedback.role),
            ("os", feedback.os),
            ("version", feedback.version),
        )
        if value
    ]
    message = feedback.comments
    if metadata_lines:
        message = f"{feedback.comments}\n\n" + "\n".join(metadata_lines)

    payload = {
        "_id": str(uuid4()),
        "subject": f"Deploy App version {feedback.version} feedback: {feedback.rating}",
        "message": message,
        "name": callsign,
        "rating": feedback.rating,
        "role": feedback.role,
        "os": feedback.os,
        "version": feedback.version,
    }

    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=conf.joke_timeout)) as session:
            headers = {
                "content-type": "application/json",
                "x-joke-key": conf.joke_ingest_key,
                "x-forwarded-for": source_ip,
            }
            async with session.post(conf.joke_ingest_url, json=payload, headers=headers) as response:
                if response.status == 429:
                    LOGGER.warning("JOKE rate-limited feedback submission")
                    raise HTTPException(status_code=429, detail="Too many feedback submissions, try again shortly")
                response.raise_for_status()
    except aiohttp.ClientError as exc:
        LOGGER.error(
            "Failed to forward feedback to JOKE: %s",
            exc,
            extra=build_audit_extra(action="feedback.submit", outcome="failure", actor=callsign, request=request),
        )
        raise HTTPException(status_code=502, detail="Could not submit feedback, please try again") from exc
    except TimeoutError as exc:
        LOGGER.error(
            "Timed out forwarding feedback to JOKE",
            extra=build_audit_extra(action="feedback.submit", outcome="failure", actor=callsign, request=request),
        )
        raise HTTPException(status_code=502, detail="Could not submit feedback, please try again") from exc

    LOGGER.audit(  # type: ignore[attr-defined]
        "Feedback submitted",
        extra=build_audit_extra(action="feedback.submit", outcome="success", actor=callsign, request=request),
    )
    return FeedbackOut(ok=True)
