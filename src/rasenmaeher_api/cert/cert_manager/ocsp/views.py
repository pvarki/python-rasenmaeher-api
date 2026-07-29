"""HTTP endpoints for the OCSP responder (RFC 6960 A.1 / RFC 5019).

No auth dependencies: OCSP clients are anonymous, responses are self-authenticating.
"""

import base64
import binascii
import email.utils
import hashlib
import logging
import urllib.parse
from datetime import UTC, datetime

from cryptography.x509 import ocsp
from fastapi import APIRouter, Request, Response

from .responder import ResponseMeta, build_ocsp_response, unsuccessful

LOGGER = logging.getLogger(__name__)
router = APIRouter()

MAX_REQUEST_BYTES = 10_000  # real requests are ~100B


def _to_http(der: bytes, meta: ResponseMeta) -> Response:
    """Wrap a DER response, adding RFC 5019 cache headers when applicable"""
    headers = {}
    if meta.success:
        if meta.nonce:
            headers["Cache-Control"] = "no-store"
        elif meta.this_update and meta.next_update:
            max_age = max(0, int((meta.next_update - datetime.now(UTC)).total_seconds()))
            headers["Cache-Control"] = f"max-age={max_age},public,no-transform,must-revalidate"
            headers["Last-Modified"] = email.utils.format_datetime(meta.this_update, usegmt=True)
            headers["Expires"] = email.utils.format_datetime(meta.next_update, usegmt=True)
            headers["ETag"] = f'"{hashlib.sha1(der, usedforsecurity=False).hexdigest()}"'
    # OCSP-level errors still ride HTTP 200
    return Response(content=der, media_type="application/ocsp-response", headers=headers)


def _malformed() -> tuple[bytes, ResponseMeta]:
    return unsuccessful(ocsp.OCSPResponseStatus.MALFORMED_REQUEST)


@router.post("")
async def ocsp_post(request: Request) -> Response:
    """OCSP over HTTP POST: request DER in the body"""
    der = await request.body()
    if not der or len(der) > MAX_REQUEST_BYTES:
        return _to_http(*_malformed())
    return _to_http(*await build_ocsp_response(der))


@router.get("/{request_b64:path}")
async def ocsp_get(request_b64: str) -> Response:
    """OCSP over HTTP GET: base64-encoded request DER in the path"""
    try:
        der = base64.b64decode(urllib.parse.unquote(request_b64), validate=True)
    except (binascii.Error, ValueError):
        return _to_http(*_malformed())
    if not der or len(der) > MAX_REQUEST_BYTES:
        return _to_http(*_malformed())
    return _to_http(*await build_ocsp_response(der))
