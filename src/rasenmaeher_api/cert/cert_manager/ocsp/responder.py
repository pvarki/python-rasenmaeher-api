"""RFC 6960 OCSP responder core: DER request in, DER response out."""

from typing import Optional, Tuple
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import logging

from cryptography import x509
from cryptography.x509 import ocsp
from cryptography.hazmat.primitives import hashes, serialization

from rasenmaeher_api.rmsettings import RMSettings

from .signer import get_signer
from .status import lookup_status

LOGGER = logging.getLogger(__name__)

MAX_NONCE_BYTES = 32  # RFC 8954


@dataclass
class ResponseMeta:
    success: bool
    nonce: bool = False
    this_update: Optional[datetime] = None
    next_update: Optional[datetime] = None


def unsuccessful(status: ocsp.OCSPResponseStatus) -> Tuple[bytes, ResponseMeta]:
    """Build an unsigned OCSP error response"""
    der = ocsp.OCSPResponseBuilder.build_unsuccessful(status).public_bytes(serialization.Encoding.DER)
    return der, ResponseMeta(success=False)


async def build_ocsp_response(der: bytes) -> Tuple[bytes, ResponseMeta]:
    """Handle one OCSP request; never raises, errors become OCSP error responses"""
    try:
        req = ocsp.load_der_ocsp_request(der)
    except ValueError:
        return unsuccessful(ocsp.OCSPResponseStatus.MALFORMED_REQUEST)

    try:
        material = await get_signer()
        algkey = req.hash_algorithm.name
        if algkey not in material.name_hashes:
            return unsuccessful(ocsp.OCSPResponseStatus.UNAUTHORIZED)
        if req.issuer_name_hash != material.name_hashes[algkey] or req.issuer_key_hash != material.key_hashes[algkey]:
            return unsuccessful(ocsp.OCSPResponseStatus.UNAUTHORIZED)

        result = await lookup_status(req.serial_number)

        now = datetime.now(UTC)
        this_update = now - timedelta(seconds=60)
        next_update = now + timedelta(seconds=RMSettings.singleton().ocsp_response_validity)
        builder = (
            ocsp.OCSPResponseBuilder()
            .add_response_by_hash(
                issuer_name_hash=req.issuer_name_hash,
                issuer_key_hash=req.issuer_key_hash,
                algorithm=req.hash_algorithm,
                serial_number=req.serial_number,
                cert_status=result.status,
                this_update=this_update,
                next_update=next_update,
                revocation_time=result.revocation_time,
                revocation_reason=result.revocation_reason,
            )
            .responder_id(ocsp.OCSPResponderEncoding.HASH, material.cert)
        )

        has_nonce = False
        try:
            ext = req.extensions.get_extension_for_class(x509.OCSPNonce)
            if len(ext.value.nonce) > MAX_NONCE_BYTES:
                return unsuccessful(ocsp.OCSPResponseStatus.MALFORMED_REQUEST)
            builder = builder.add_extension(x509.OCSPNonce(ext.value.nonce), critical=False)
            has_nonce = True
        except x509.ExtensionNotFound:
            pass

        resp_der = builder.sign(material.key, hashes.SHA256()).public_bytes(encoding=serialization.Encoding.DER)
        return resp_der, ResponseMeta(
            success=True,
            nonce=has_nonce,
            this_update=this_update,
            next_update=next_update,
        )

    except Exception:
        LOGGER.exception("OCSP response building failed")
        return unsuccessful(ocsp.OCSPResponseStatus.INTERNAL_ERROR)
