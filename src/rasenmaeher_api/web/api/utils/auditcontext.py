# src/rasenmaeher_api/web/api/utils/auditcontext.py
"""Audit logging helpers for extracting request context.

This module is intentionally kept in the API layer (not libpvarki) as a
temporary solution until the logging utilities can be extended.

Assumes a trusted reverse proxy (nginx) overwrites the relevant headers:
- X-Real-IP
- X-Forwarded-For
- X-Request-ID
- X-SSL-Client-Verify
- X-SSL-Client-Fingerprint
"""

from __future__ import annotations
from typing import Dict, Optional
from fastapi import Request

_MAX_HEADER_LEN = 256
_MAX_FINGERPRINT_LEN = 128


def _clean_header(value: Optional[str], *, max_len: int = _MAX_HEADER_LEN) -> str:
    """Trim and clamp header values to avoid log injection / runaway payloads."""
    if not value:
        return ""
    cleaned = value.strip().replace("\n", "").replace("\r", "")
    if len(cleaned) > max_len:
        return cleaned[:max_len]
    return cleaned


def _first_xff_ip(xff: str) -> str:
    """Extract the first entry of X-Forwarded-For."""
    # XFF is typically: "client_ip, proxy1_ip, proxy2_ip"
    return xff.split(",", maxsplit=1)[0].strip()


def get_audit_request_context(
    request: Request,
    *,
    trust_proxy_headers: bool = True,
) -> Dict[str, str]:
    """Extract request context for audit logging.

    Args:
        request: FastAPI Request.
        trust_proxy_headers: If True, prefer nginx-injected headers
            (X-Real-IP/X-Forwarded-For). Set False if FastAPI is reachable
            directly by clients (headers become spoofable).

    Returns:
        Dict with keys like:
            - source_ip
            - request_id (if present)
            - cert_verify (if present)
            - cert_fp (if present)
    """
    source_ip = "unknown"

    if trust_proxy_headers:
        x_real_ip = _clean_header(request.headers.get("X-Real-IP"))
        xff = _clean_header(request.headers.get("X-Forwarded-For"))
        if x_real_ip:
            source_ip = x_real_ip
        elif xff:
            source_ip = _first_xff_ip(xff)

    if source_ip == "unknown":
        if request.client and request.client.host:
            source_ip = _clean_header(request.client.host)

    ctx: Dict[str, str] = {"source_ip": source_ip}

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

    return ctx


def format_audit_request_context(ctx: Dict[str, str]) -> str:
    """Format request context as a stable, log-friendly string.

    This is useful when you can't send structured fields to the logger yet.
    """
    parts = [f"source_ip={ctx.get('source_ip', 'unknown')}"]

    request_id = ctx.get("request_id")
    if request_id:
        parts.append(f"request_id={request_id}")

    cert_verify = ctx.get("cert_verify")
    if cert_verify:
        parts.append(f"cert_verify={cert_verify}")

    cert_fp = ctx.get("cert_fp")
    if cert_fp:
        parts.append(f"cert_fp={cert_fp}")

    return " ".join(parts)
