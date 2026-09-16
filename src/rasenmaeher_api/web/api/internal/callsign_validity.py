"""Per-request mTLS authorization, answered for Traefik's ``forwardAuth`` middleware.

Traefik forwards the verified client certificate as ``X-Forwarded-Tls-Client-Cert``
(``passTLSClientCert`` with ``pem: true``). This endpoint recovers the leaf and
resolves its serial through :func:`lookup_status` -- the same function the OCSP
responder answers from, so the edge and OCSP clients can never disagree about
whether a certificate is revoked.

The response is always ``200`` when the endpoint successfully answers. The verdict
therefore travels in headers:

    Callsign               the certificate CN
    Callsign-Valid         "true" or "false"
    Callsign-Valid-Reason  ok | no_cert | invalid | error

SECURITY: the certificate header is authentication input. It is trustworthy only
because ``strip-identity-headers`` blanks it on the ``websecure`` entrypoint --
entrypoint middlewares run before router middlewares -- and ``mtls-pass-client-cert``
then sets it from the verified connection. This endpoint is reachable only from
Traefik's mesh identity; see the AuthorizationPolicy in the platform repo.

The certificate is not re-verified here. Traefik has already checked it against
the same trust-manager bundle on the TLS connection (see the mtls-optional and
mtls-strict TLSOptions), so a second check would only ever disagree when the
header did not come from the connection at all.
"""

import logging
import urllib.parse

from cryptography import x509
from cryptography.x509 import ocsp
from cryptography.x509.oid import NameOID
from fastapi import APIRouter, Header, Response

from ....cert.cert_manager.ocsp.status import lookup_status

LOGGER = logging.getLogger(__name__)
router = APIRouter()

CERT_HEADER = "X-Forwarded-Tls-Client-Cert"
CALLSIGN_HEADER = "Callsign"
VALIDITY_HEADER = "Callsign-Valid"
REASON_HEADER = "Callsign-Valid-Reason"

REASON_OK = "ok"
REASON_NO_CERT = "no_cert"
REASON_INVALID = "invalid"
REASON_ERROR = "error"

PEM_LINE_WIDTH = 64


def _rewrap(body: str) -> str:
    """Restore the PEM armour and line breaks Traefik strips from the header"""
    if "BEGIN CERTIFICATE" in body:
        return body
    body = "".join(body.split())
    lines = [body[offset : offset + PEM_LINE_WIDTH] for offset in range(0, len(body), PEM_LINE_WIDTH)]
    return "-----BEGIN CERTIFICATE-----\n" + "\n".join(lines) + "\n-----END CERTIFICATE-----\n"


def _candidates(header: str) -> list[str]:
    """Traefik sends the header url-encoded or literal.

    The literal form is tried first because unquoting unconditionally would turn
    a legal base64 ``+`` into a space.
    """
    out = [header]
    if "%" not in header:
        return out
    for decoded in (urllib.parse.unquote(header), urllib.parse.unquote_plus(header)):
        if decoded not in out:
            out.append(decoded)
    return out


def parse_leaf(header: str) -> x509.Certificate | None:
    """Recover the leaf certificate from a passTLSClientCert header value.

    Traefik comma-separates the chain; only the first entry is the leaf.
    """
    header = header.strip()
    if not header:
        return None
    for candidate in _candidates(header):
        first = candidate.split(",", 1)[0].strip()
        if not first:
            continue
        try:
            return x509.load_pem_x509_certificate(_rewrap(first).encode("utf-8"))
        except ValueError:
            continue
    return None


def common_name(cert: x509.Certificate) -> str:
    """Return the trimmed CN, which is the callsign"""
    attributes = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    if not attributes:
        return ""
    return str(attributes[0].value).strip()


def _verdict(callsign: str, valid: bool, reason: str) -> Response:
    headers = {
        VALIDITY_HEADER: "true" if valid else "false",
        REASON_HEADER: reason,
    }
    if callsign:
        headers[CALLSIGN_HEADER] = callsign
    return Response(status_code=200, headers=headers)


@router.get("/check")
async def callsign_validity_check(
    client_cert: str | None = Header(default=None, alias=CERT_HEADER),
) -> Response:
    """Answer Traefik's forwardAuth subrequest with the client certificate's verdict"""
    leaf = parse_leaf(client_cert or "")
    if leaf is None:
        return _verdict("", False, REASON_NO_CERT)

    callsign = common_name(leaf)
    if not callsign:
        return _verdict("", False, REASON_NO_CERT)

    try:
        result = await lookup_status(leaf.serial_number)
    except Exception:  # pylint: disable=broad-except
        LOGGER.exception("callsign validity lookup failed for %s", callsign)
        return _verdict(callsign, False, REASON_ERROR)

    if result.status == ocsp.OCSPCertStatus.GOOD:
        return _verdict(callsign, True, REASON_OK)

    # REVOKED and UNKNOWN both deny; an unknown serial is not one we issued.
    LOGGER.info("callsign %s denied, status=%s", callsign, result.status)
    return _verdict(callsign, False, REASON_INVALID)
