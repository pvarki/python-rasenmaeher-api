"""Cert material builders and their types, shared by the cert backend tests.

Lives outside conftest.py so tests can import it normally: conftest is pytest's
fixture and hook mechanism, and these are plain functions and types.
"""

import datetime
from pathlib import Path
from typing import NamedTuple, Protocol

import cryptography.x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

NOT_BEFORE = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
CA_PUBLIC_PATH = Path(__file__).parents[1] / "data" / "ca_public"


class FakePKI(NamedTuple):
    """Generated root, intermediate and leaf PEMs"""

    root: str
    intermediate: str
    leaf: str


class CertFactory(Protocol):
    """Mint a cert PEM plus its key; self-signed unless issuer and signer are given"""

    def __call__(
        self,
        subject_cn: str,
        issuer: cryptography.x509.Name | None = None,
        signer: ec.EllipticCurvePrivateKey | None = None,
        *,
        ca: bool,
    ) -> tuple[str, ec.EllipticCurvePrivateKey]: ...


class CsrFactory(Protocol):
    """Mint a PEM CSR, optionally carrying KeyUsage and ExtendedKeyUsage extensions"""

    def __call__(
        self,
        common_name: str | None = "test leaf",
        key_usage: cryptography.x509.KeyUsage | None = None,
        ext_key_usage: list[cryptography.x509.ObjectIdentifier] | None = None,
        organization: str | None = None,
    ) -> str: ...


class KeyUsageFactory(Protocol):
    """A KeyUsage extension with everything off except the named flags"""

    def __call__(self, **flags: bool) -> cryptography.x509.KeyUsage: ...


def make_name(common_name: str) -> cryptography.x509.Name:
    """A Name carrying just a CN"""
    return cryptography.x509.Name([cryptography.x509.NameAttribute(NameOID.COMMON_NAME, common_name)])


def make_cert(
    subject_cn: str,
    issuer: cryptography.x509.Name | None = None,
    signer: ec.EllipticCurvePrivateKey | None = None,
    *,
    ca: bool,
) -> tuple[str, ec.EllipticCurvePrivateKey]:
    """Mint a cert PEM plus its key; self-signed unless issuer and signer are given"""
    key = ec.generate_private_key(ec.SECP256R1())
    cert = (
        cryptography.x509.CertificateBuilder()
        .subject_name(make_name(subject_cn))
        .issuer_name(issuer or make_name(subject_cn))
        .public_key(key.public_key())
        .serial_number(cryptography.x509.random_serial_number())
        .not_valid_before(NOT_BEFORE)
        .not_valid_after(NOT_BEFORE + datetime.timedelta(days=365))
        .add_extension(cryptography.x509.BasicConstraints(ca=ca, path_length=None), critical=True)
        .sign(signer or key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8"), key


def make_key_usage(**flags: bool) -> cryptography.x509.KeyUsage:
    """A KeyUsage extension with everything off except the named flags"""
    off: dict[str, bool] = {
        "digital_signature": False,
        "content_commitment": False,
        "key_encipherment": False,
        "data_encipherment": False,
        "key_agreement": False,
        "key_cert_sign": False,
        "crl_sign": False,
        "encipher_only": False,
        "decipher_only": False,
    }
    return cryptography.x509.KeyUsage(**{**off, **flags})


def make_csr(
    common_name: str | None = "test leaf",
    key_usage: cryptography.x509.KeyUsage | None = None,
    ext_key_usage: list[cryptography.x509.ObjectIdentifier] | None = None,
    organization: str | None = None,
) -> str:
    """Mint a PEM CSR, optionally carrying KeyUsage and ExtendedKeyUsage extensions.

    An organization is prepended to the subject when given, which is how you get a
    CSR whose CN is not the first attribute.
    """
    key = ec.generate_private_key(ec.SECP256R1())
    attributes = []
    if organization is not None:
        attributes.append(cryptography.x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization))
    if common_name is not None:
        attributes.append(cryptography.x509.NameAttribute(NameOID.COMMON_NAME, common_name))
    builder = cryptography.x509.CertificateSigningRequestBuilder().subject_name(cryptography.x509.Name(attributes))
    if key_usage is not None:
        builder = builder.add_extension(key_usage, critical=True)
    if ext_key_usage is not None:
        builder = builder.add_extension(cryptography.x509.ExtendedKeyUsage(ext_key_usage), critical=False)
    return builder.sign(key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM).decode("utf-8")
