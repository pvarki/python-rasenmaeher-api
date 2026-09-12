"""CFSSL must issue the server authentication requested by product CSRs."""

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from rasenmaeher_api.cert.cfssl.profiles import signing_profile


@pytest.mark.parametrize("keytype", ["EC", "RSA"])
@pytest.mark.parametrize(
    ("usages", "expected"),
    [
        (None, "client"),
        ([ExtendedKeyUsageOID.CLIENT_AUTH], "client"),
        ([ExtendedKeyUsageOID.SERVER_AUTH], "server"),
        ([ExtendedKeyUsageOID.SERVER_AUTH, ExtendedKeyUsageOID.CLIENT_AUTH], "peer"),
    ],
)
def test_signing_profile(keytype: str, usages: list[x509.ObjectIdentifier] | None, expected: str) -> None:
    """Preserve client defaults and select dual-purpose certificates for TAK."""
    key = ec.generate_private_key(ec.SECP256R1()) if keytype == "EC" else rsa.generate_private_key(65537, 2048)
    builder = x509.CertificateSigningRequestBuilder().subject_name(
        x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "tak.example.test")])
    )
    if usages is not None:
        builder = builder.add_extension(x509.ExtendedKeyUsage(usages), critical=True)
    csr = builder.sign(key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM).decode("utf-8")
    assert signing_profile(csr) == expected
