"""OCSP request/response handler.

Wire formats (RFC 6960):
- ``POST /api/v1/ocsp`` with ``Content-Type: application/ocsp-request``, body is the
  DER-encoded OCSPRequest. Returns ``application/ocsp-response`` (DER).
- ``GET /api/v1/ocsp/{b64req}`` where ``b64req`` is the base64-encoded DER of the
  OCSPRequest. Equivalent semantics.

Lookup: the request's certificate serial is matched against ``Person.cert_serial``.
``good`` if the row exists with ``deleted IS NULL``, ``revoked`` if soft-deleted
(with ``revocation_time = Person.deleted`` and ``revocation_reason`` derived from
``Person.revoke_reason``), ``unknown`` otherwise.

We respond using ``add_response_by_hash`` — echoing the issuer hashes from the
request — so we don't need to load the subject cert from disk or the CA bundle
at request time. The OCSP responder cert is signed by the same CA, so clients
can verify the delegation via its embedded OCSPSigning EKU (RFC 6960 §4.2.2.2).
"""

import base64
import binascii
import datetime
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple, cast

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.types import CertificateIssuerPrivateKeyTypes
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.x509 import ocsp
from cryptography.x509.oid import ExtendedKeyUsageOID
from fastapi import APIRouter, Request, Response

from ....db.errors import NotFound
from ....db.people import Person
from ....rmsettings import RMSettings


LOGGER = logging.getLogger(__name__)
router = APIRouter()

_OCSP_REQUEST_MEDIA = "application/ocsp-request"
_OCSP_RESPONSE_MEDIA = "application/ocsp-response"


def _load_signer() -> Tuple[x509.Certificate, CertificateIssuerPrivateKeyTypes]:
    """Load the OCSP signer cert+key from the configured paths.

    Cached on (path, mtime) so a Secret rotation that rewrites the file is
    picked up without a restart.
    """
    settings = RMSettings.singleton()
    cert_path = Path(settings.cert_manager_ocsp_signer_cert_path)
    key_path = Path(settings.cert_manager_ocsp_signer_key_path)
    cert, key = _load_signer_cached(
        str(cert_path),
        cert_path.stat().st_mtime,
        str(key_path),
        key_path.stat().st_mtime,
    )
    return cert, key


@lru_cache(maxsize=2)
def _load_signer_cached(
    cert_path: str, _cert_mtime: float, key_path: str, _key_mtime: float
) -> Tuple[x509.Certificate, CertificateIssuerPrivateKeyTypes]:
    cert = x509.load_pem_x509_certificate(Path(cert_path).read_bytes())
    # cert-manager signer keys are RSA or EC in practice; the OCSP builder
    # signature surface (RSA/EC/Ed25519/Ed448/DSA) is narrower than what
    # ``load_pem_private_key`` can produce, so narrow with a cast.
    key = cast(CertificateIssuerPrivateKeyTypes, load_pem_private_key(Path(key_path).read_bytes(), password=None))
    try:
        eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
        if ExtendedKeyUsageOID.OCSP_SIGNING not in eku:
            raise ValueError(f"OCSP signer cert at {cert_path} is missing the OCSPSigning ExtendedKeyUsage")
    except x509.ExtensionNotFound as exc:
        raise ValueError(f"OCSP signer cert at {cert_path} has no ExtendedKeyUsage extension") from exc
    return cert, key


def _map_revocation_reason(stored: Optional[str]) -> Optional[x509.ReasonFlags]:
    """``Person.revoke_reason`` is a decimal string of ``ReasonFlags.value``."""
    if not stored:
        return None
    by_value = {str(flag.value): flag for flag in x509.ReasonFlags}
    by_name = {flag.name: flag for flag in x509.ReasonFlags}
    return by_value.get(stored) or by_name.get(stored)


def _unsuccessful(status: ocsp.OCSPResponseStatus) -> Response:
    """Build an unsuccessful OCSP response (no signature, no cert info)."""
    resp = ocsp.OCSPResponseBuilder.build_unsuccessful(status)
    return Response(
        content=resp.public_bytes(serialization.Encoding.DER),
        media_type=_OCSP_RESPONSE_MEDIA,
    )


async def _build_response(der: bytes) -> Response:
    try:
        req = ocsp.load_der_ocsp_request(der)
    except (ValueError, binascii.Error, TypeError) as exc:
        LOGGER.info("OCSP request was malformed: %s", exc)
        return _unsuccessful(ocsp.OCSPResponseStatus.MALFORMED_REQUEST)

    try:
        signer_cert, signer_key = _load_signer()
    except (FileNotFoundError, OSError, ValueError) as exc:
        LOGGER.error("OCSP signer load failed: %s", exc)
        return _unsuccessful(ocsp.OCSPResponseStatus.INTERNAL_ERROR)

    serial = req.serial_number
    now = datetime.datetime.now(datetime.UTC)
    next_update = now + datetime.timedelta(hours=RMSettings.singleton().cert_manager_ocsp_next_update_hours)

    try:
        person = await Person.by_cert_serial(str(serial), allow_deleted=True)
        if person.deleted is None:
            cert_status: ocsp.OCSPCertStatus = ocsp.OCSPCertStatus.GOOD
            revocation_time: Optional[datetime.datetime] = None
            revocation_reason: Optional[x509.ReasonFlags] = None
        else:
            cert_status = ocsp.OCSPCertStatus.REVOKED
            revocation_time = person.deleted
            revocation_reason = _map_revocation_reason(person.revoke_reason)
    except NotFound:
        cert_status = ocsp.OCSPCertStatus.UNKNOWN
        revocation_time = None
        revocation_reason = None

    try:
        builder = ocsp.OCSPResponseBuilder()
        builder = builder.add_response_by_hash(
            issuer_name_hash=req.issuer_name_hash,
            issuer_key_hash=req.issuer_key_hash,
            algorithm=req.hash_algorithm,
            serial_number=serial,
            cert_status=cert_status,
            this_update=now,
            next_update=next_update,
            revocation_time=revocation_time,
            revocation_reason=revocation_reason,
        )
        builder = builder.responder_id(ocsp.OCSPResponderEncoding.HASH, signer_cert)
        builder = builder.certificates([signer_cert])
        response = builder.sign(signer_key, hashes.SHA256())
    except Exception:
        LOGGER.exception("Failed to build OCSP response for serial=%s", serial)
        return _unsuccessful(ocsp.OCSPResponseStatus.INTERNAL_ERROR)

    return Response(
        content=response.public_bytes(serialization.Encoding.DER),
        media_type=_OCSP_RESPONSE_MEDIA,
    )


@router.post("")
@router.post("/")
async def ocsp_post(request: Request) -> Response:
    """Handle a binary OCSP request body."""
    body = await request.body()
    return await _build_response(body)


@router.get("/{b64req:path}")
async def ocsp_get(b64req: str) -> Response:
    """Handle a base64-in-URL OCSP request (RFC 6960 §A.1.1).

    Accepts either standard base64 (``+``/``/``, typically percent-encoded by
    well-behaved clients) or the URL-safe alphabet (``-``/``_``). Padding is
    optional.
    """
    # Normalize URL-safe alphabet to standard, then pad.
    normalized = b64req.replace("-", "+").replace("_", "/")
    padded = normalized + "=" * (-len(normalized) % 4)
    try:
        der = base64.b64decode(padded, validate=False)
    except (binascii.Error, ValueError) as exc:
        LOGGER.info("OCSP GET payload not base64: %s", exc)
        return _unsuccessful(ocsp.OCSPResponseStatus.MALFORMED_REQUEST)
    return await _build_response(der)
