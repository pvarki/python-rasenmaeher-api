# src/rasenmaeher_api/web/api/utils/auditcontext.py
"""Audit logging helpers for extracting request context.

Intentionally a temporary solution until the libpvarki auditlogging is extended.

Assumes nginx overwrites the relevant headers:
- X-Real-IP
- X-Forwarded-For
- X-Request-ID
- X-SSL-Client-Fingerprint
- X-ClientCert-DN
- X-ClientCert-Serial
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
    if not cleaned:
        return ""
    return cleaned[:max_len]


def _first_xff_ip(xff: str) -> str:
    """Extract the first entry of X-Forwarded-For."""
    return xff.split(",", maxsplit=1)[0].strip()


def get_audit_request_context(
    request: Request,
    *,
    trust_proxy_headers: bool = True,
) -> Dict[str, str]:
    """Extract request context for audit logging.

    Returns the following ECS 1.6.0 compliant keys:
      - source.ip
      - client.ip
      - transaction.id
      - tls.client.hash.sha256 from X-SSL-Client-Fingerprint
      - tls.client.x509.subject.distinguished_name from X-ClientCert-DN
      - tls.client.x509.serial_number from X-ClientCert-Serial
    """
    client_ip = _clean_header(request.client.host) if request.client and request.client.host else "unknown"

    source_ip = "unknown"
    if trust_proxy_headers:
        x_real_ip = _clean_header(request.headers.get("X-Real-IP"))
        xff = _clean_header(request.headers.get("X-Forwarded-For"))
        if x_real_ip:
            source_ip = x_real_ip
        elif xff:
            source_ip = _first_xff_ip(xff)

    if source_ip == "unknown":
        source_ip = client_ip

    ctx: Dict[str, str] = {
        "source.ip": source_ip,
        "client.ip": client_ip,
    }

    request_id = _clean_header(request.headers.get("X-Request-ID"))
    if request_id:
        ctx["transaction.id"] = request_id

    cert_fp = _clean_header(
        request.headers.get("X-SSL-Client-Fingerprint"),
        max_len=_MAX_FINGERPRINT_LEN,
    )
    if cert_fp:
        ctx["tls.client.hash.sha256"] = cert_fp

    cert_dn = _clean_header(request.headers.get("X-ClientCert-DN"))
    if cert_dn:
        ctx["tls.client.x509.subject.distinguished_name"] = cert_dn

    cert_serial = _clean_header(request.headers.get("X-ClientCert-Serial"))
    if cert_serial:
        ctx["tls.client.x509.serial_number"] = cert_serial

    return ctx


def format_audit_request_context(ctx: Dict[str, str]) -> str:
    """Format request context as a stable, log-friendly string.

    Useful when extra fields aren't ingested into JSON by the log pipeline.
    """
    parts = [
        f"source.ip={ctx.get('source.ip', 'unknown')}",
        f"client.ip={ctx.get('client.ip', 'unknown')}",
    ]

    for key in (
        "transaction.id",
        "tls.client.hash.sha256",
        "tls.client.x509.serial_number",
        "tls.client.x509.subject.distinguished_name",
    ):
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
    request: Optional[Request] = None,
    trust_proxy_headers: bool = True,
    **extra_fields: Any,
) -> Dict[str, Any]:
    """Build ECS 1.6.0 compliant extra dict for audit logging.

    Produces:
      - event.action
      - event.outcome
      - user.name                 (actor)
      - destination.user.name     (target user)
      - + request context fields (source.ip, client.ip, transaction.id, tls.client.*)
      - + extra_fields
    """
    normalized_outcome = outcome.strip().lower()
    if normalized_outcome not in ("success", "failure", "unknown"):
        normalized_outcome = "unknown"

    extra: Dict[str, Any] = {
        "event.action": action,
        "event.outcome": normalized_outcome,
    }

    if actor:
        extra["user.name"] = actor

    if target:
        extra["destination.user.name"] = target

    if request:
        extra.update(
            get_audit_request_context(
                request,
                trust_proxy_headers=trust_proxy_headers,
            )
        )

    extra.update(extra_fields)
    return extra
