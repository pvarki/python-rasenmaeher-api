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


def invalidate_signature(csr_pem: str) -> str:
    """The same CSR with one bit of its signature flipped, so it no longer verifies"""
    der = cryptography.x509.load_pem_x509_csr(csr_pem.encode("utf-8")).public_bytes(serialization.Encoding.DER)
    altered = der[:-1] + bytes([der[-1] ^ 0x01])
    return cryptography.x509.load_der_x509_csr(altered).public_bytes(serialization.Encoding.PEM).decode("utf-8")


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


EXTENSION_REQUEST_OID = b"\x06\x09\x2a\x86\x48\x86\xf7\x0d\x01\x09\x0e"  # 1.2.840.113549.1.9.14
MS_EXTENSION_REQUEST_OID = b"\x06\x0a\x2b\x06\x01\x04\x01\x82\x37\x02\x01\x0e"  # 1.3.6.1.4.1.311.2.1.14
EC_PUBLIC_KEY_OID = b"\x06\x07\x2a\x86\x48\xce\x3d\x02\x01"  # 1.2.840.10045.2.1
UNKNOWN_KEY_OID = b"\x06\x07\x2a\x86\x48\xce\x3d\x02\x7f"  # 1.2.840.10045.2.127


def _der(tag: int, body: bytes) -> bytes:
    """One DER TLV"""
    if len(body) < 0x80:
        return bytes([tag, len(body)]) + body
    size = len(body).to_bytes((len(body).bit_length() + 7) // 8, "big")
    return bytes([tag, 0x80 | len(size)]) + size + body


def _der_header(data: bytes) -> tuple[int, int]:
    """Header and content lengths of the TLV at the start of data"""
    if data[1] & 0x80:
        header = 2 + (data[1] & 0x7F)
        return header, int.from_bytes(data[2:header], "big")
    return 2, data[1]


def _der_items(body: bytes) -> list[bytes]:
    """Split concatenated DER TLVs, each returned whole"""
    items = []
    while body:
        header, size = _der_header(body)
        items.append(body[: header + size])
        body = body[header + size :]
    return items


def _der_body(item: bytes) -> bytes:
    """The contents of one DER TLV"""
    return item[_der_header(item)[0] :]


def _csr_der(csr_pem: str) -> bytes:
    return cryptography.x509.load_pem_x509_csr(csr_pem.encode("utf-8")).public_bytes(serialization.Encoding.DER)


def csr_attributes(csr_pem: str) -> list[bytes]:
    """The DER attributes of a CSR"""
    info = _der_items(_der_body(_csr_der(csr_pem)))[0]
    return _der_items(_der_body(_der_items(_der_body(info))[3]))


def with_ms_extension_request_oid(attribute: bytes) -> bytes:
    """The same extension-request attribute under the Microsoft OID"""
    return _der(0x30, MS_EXTENSION_REQUEST_OID + _der_body(attribute)[len(EXTENSION_REQUEST_OID) :])


def with_attributes(csr_pem: str, key: ec.EllipticCurvePrivateKey, extra: list[bytes]) -> str:
    """The CSR with extra DER attributes, DER-sorted into its attribute set and signed again by key"""
    info, algorithm, _ = _der_items(_der_body(_csr_der(csr_pem)))
    version, subject, public_key, attributes = _der_items(_der_body(info))
    attribute_set = _der(0xA0, b"".join(sorted(_der_items(_der_body(attributes)) + extra)))
    info = _der(0x30, version + subject + public_key + attribute_set)
    signature = _der(0x03, b"\x00" + key.sign(info, ec.ECDSA(hashes.SHA256())))
    der = _der(0x30, info + algorithm + signature)
    return cryptography.x509.load_der_x509_csr(der).public_bytes(serialization.Encoding.PEM).decode("utf-8")


def with_unknown_key_type(csr_pem: str) -> str:
    """The same EC CSR with its public key algorithm replaced by an unknown one"""
    der = _csr_der(csr_pem).replace(EC_PUBLIC_KEY_OID, UNKNOWN_KEY_OID, 1)
    return cryptography.x509.load_der_x509_csr(der).public_bytes(serialization.Encoding.PEM).decode("utf-8")
