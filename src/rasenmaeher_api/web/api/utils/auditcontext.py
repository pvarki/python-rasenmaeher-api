# src/rasenmaeher_api/web/api/utils/auditcontext.py
"""Audit logging helpers for extracting request context.

Intentionally a temporary solution until the libpvarki auditlogging is extended.

Assumes nginx overwrites the relevant headers:
- X-Real-IP
- X-Forwarded-For
- X-Request-ID
- X-SSL-Client-Verify
- X-SSL-Client-Fingerprint
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Request


_MAX_HEADER_LEN = 256
_MAX_FINGERPRINT_LEN = 128


def _clean_header(value: Optional[str], *, max_len: int = _MAX_HEADER_LEN) -> str:
    """Trim and clamp header values to avoid log injection / runaway payloads."""
    if not value:
        return ""
    cleaned = value.strip().replace("\n", "").replace("\r", "")
    return cleaned[:max_len]


def _first_xff_ip(xff: str) -> str:
    """Extract the first entry of X-Forwarded-For."""
    return xff.split(",", maxsplit=1)[0].strip()


def get_audit_request_context(
    request: Request,
    *,
    trust_proxy_headers: bool = True,
) -> Dict[str, str]:
    """Extract request context for audit logging."""
    peer_ip = _clean_header(request.client.host) if request.client and request.client.host else "unknown"

    source_ip = "unknown"
    if trust_proxy_headers:
        x_real_ip = _clean_header(request.headers.get("X-Real-IP"))
        xff = _clean_header(request.headers.get("X-Forwarded-For"))
        if x_real_ip:
            source_ip = x_real_ip
        elif xff:
            source_ip = _first_xff_ip(xff)

    if source_ip == "unknown":
        source_ip = peer_ip

    ctx: Dict[str, str] = {
        "source_ip": source_ip,
        "peer_ip": peer_ip,
    }

    request_id = _clean_header(request.headers.get("X-Request-ID"))
    if request_id:
        ctx["request_id"] = request_id

    cert_verify = _clean_header(request.headers.get("X-SSL-Client-Verify"))
    if cert_verify:
        ctx["cert_verify"] = cert_verify

    cert_fp = _clean_header(
        request.headers.get("X-SSL-Client-Fingerprint"),
        max_len=_MAX_FINGERPRINT_LEN,
    )
    if cert_fp:
        ctx["cert_fp"] = cert_fp

    cert_dn = _clean_header(request.headers.get("X-ClientCert-DN"))
    if cert_dn:
        ctx["cert_dn"] = cert_dn

    cert_serial = _clean_header(request.headers.get("X-ClientCert-Serial"))
    if cert_serial:
        ctx["cert_serial"] = cert_serial

    return ctx


def format_audit_request_context(ctx: Dict[str, str]) -> str:
    """Format request context as a stable, log-friendly string."""
    parts = [
        f"source_ip={ctx.get('source_ip', 'unknown')}",
        f"peer_ip={ctx.get('peer_ip', 'unknown')}",
    ]

    for key in ("request_id", "cert_verify", "cert_fp", "cert_dn", "cert_serial"):
        value = ctx.get(key)
        if value:
            parts.append(f"{key}={value}")

    return " ".join(parts)


def build_audit_extra(  # pylint: disable=too-many-arguments
    *,
    action: str,
    outcome: str,
    actor: Optional[str] = None,
    target: Optional[str] = None,
    target_type: str = "user",
    request: Optional[Request] = None,
    **extra_fields: Any,
) -> Dict[str, Any]:
    """Build structured extra dict for audit logging.

    Args:
        action: The action being performed (e.g., "enrollment_approve", "user_promote").
        outcome: "success" or "failure".
        actor: The user performing the action (callsign).
        target: The target of the action (callsign, invitecode_id, etc.).
        target_type: Type of target ("user", "enrollment", "invitecode").
        request: FastAPI Request for extracting context headers.
        **extra_fields: Additional fields to include (e.g., error_code, invitecode_id).

    Returns:
        Dict suitable for passing to LOGGER.audit(..., extra=).
    """
    normalized_outcome = outcome.strip().lower()
    if normalized_outcome not in ("success", "failure"):
        normalized_outcome = "unknown"

    extra: Dict[str, Any] = {
        "rm_audit_action": action,
        "rm_audit_outcome": normalized_outcome,
    }

    if actor:
        extra["rm_audit_actor"] = actor

    if target:
        extra["rm_audit_target"] = target
        extra["rm_audit_target_type"] = target_type

    if request:
        extra.update(get_audit_request_context(request))

    extra.update(extra_fields)
    return extra
