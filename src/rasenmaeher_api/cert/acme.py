"""Validation shared by the Apple ACME order and its certificate signer."""

import base64
import re

from cryptography import x509
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from .usages import csr_usages


class ACMEError(Exception):
    """An ACME problem response."""

    def __init__(self, code: str, detail: str, status: int = 400) -> None:
        super().__init__(detail)
        self.code = code
        self.status = status


def b64url(data: bytes) -> str:
    """Encode an unpadded base64url value."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def decode_b64url(value: str) -> bytes:
    """Decode a canonical, unpadded base64url value."""
    if not re.fullmatch(r"[A-Za-z0-9_-]*", value):
        raise ValueError("Invalid base64url")
    data = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    if b64url(data) != value:
        raise ValueError("Invalid base64url")
    return data


def validate_device_csr(der: bytes, callsign: str, identifier: str) -> str:
    """Validate the signed CSR and allow only the identity requested by the profile."""
    try:
        csr = x509.load_der_x509_csr(der)
        key = csr.public_key()
        pem = csr.public_bytes(serialization.Encoding.PEM).decode("ascii")
        if not (
            isinstance(key, ec.EllipticCurvePublicKey)
            and isinstance(key.curve, ec.SECP256R1)
            and isinstance(csr.signature_hash_algorithm, hashes.SHA256)
            and csr.is_signature_valid
            and csr.subject == x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, callsign)])
            and set(csr_usages(pem)) == {"digital signature", "client auth"}
        ):
            raise ValueError("CSR does not match the approved client certificate policy")
        for extension in csr.extensions:
            match extension.value:
                case x509.KeyUsage() | x509.ExtendedKeyUsage():
                    pass
                case x509.BasicConstraints(ca=False, path_length=None):
                    pass
                case x509.SubjectAlternativeName() as san:
                    # RFC 4043 permanentIdentifier with just the UTF8String identifierValue.
                    encoded = identifier.encode("ascii")
                    other_name = x509.OtherName(
                        x509.ObjectIdentifier("1.3.6.1.5.5.7.8.3"),
                        bytes((0x30, len(encoded) + 2, 0x0C, len(encoded))) + encoded,
                    )
                    if list(san) != [other_name]:
                        raise ValueError("CSR SAN does not match the approved identifier")
                case _:
                    raise ValueError("CSR contains an unsupported extension")
    except (ValueError, UnsupportedAlgorithm, x509.DuplicateExtension, x509.UnsupportedGeneralNameType) as exc:
        raise ACMEError("badCSR", "CSR does not match the approved client certificate policy") from exc
    return pem
