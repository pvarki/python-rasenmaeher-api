"""Shared cert fixtures: the real test CA PEMs and a throwaway generated PKI"""

import datetime
from pathlib import Path
from typing import NamedTuple, Protocol

import cryptography.x509
import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

NOT_BEFORE = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
CA_PUBLIC_PATH = Path(__file__).parents[1] / "data" / "ca_public"


def _name(common_name: str) -> cryptography.x509.Name:
    return cryptography.x509.Name([cryptography.x509.NameAttribute(NameOID.COMMON_NAME, common_name)])


def _mint(
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
        .subject_name(_name(subject_cn))
        .issuer_name(issuer or _name(subject_cn))
        .public_key(key.public_key())
        .serial_number(cryptography.x509.random_serial_number())
        .not_valid_before(NOT_BEFORE)
        .not_valid_after(NOT_BEFORE + datetime.timedelta(days=365))
        .add_extension(cryptography.x509.BasicConstraints(ca=ca, path_length=None), critical=True)
        .sign(signer or key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8"), key


def _key_usage(**flags: bool) -> cryptography.x509.KeyUsage:
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


def _mint_csr(
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


@pytest.fixture(scope="module")
def root_ca_pem() -> str:
    """The self-signed root CA, lean_chain must always drop this"""
    return (CA_PUBLIC_PATH / "root_ca.pem").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def intermediate_ca_pem() -> str:
    """The intermediate CA, lean_chain must keep exactly one copy of this"""
    return (CA_PUBLIC_PATH / "intermediate_ca.pem").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def ca_chain_pem() -> str:
    """The full trust bundle as cert-manager hands it to us (intermediate + root)"""
    return (CA_PUBLIC_PATH / "ca_chain.pem").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def pki() -> FakePKI:
    """A throwaway leaf -> intermediate -> self-signed root chain"""
    root_pem, root_key = _mint("test root", ca=True)
    inter_pem, inter_key = _mint("test intermediate", _name("test root"), root_key, ca=True)
    leaf, _ = _mint("test leaf", _name("test intermediate"), inter_key, ca=False)
    return FakePKI(root=root_pem, intermediate=inter_pem, leaf=leaf)


@pytest.fixture(scope="module")
def leaf_pem(pki: FakePKI) -> str:
    """A leaf (end-entity) certificate PEM issued by the generated intermediate"""
    return pki.leaf


@pytest.fixture(scope="session")
def mint_cert() -> CertFactory:
    """Factory for bespoke certs when the standard pki fixture is not enough"""
    return _mint


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


@pytest.fixture(scope="session")
def mint_csr() -> CsrFactory:
    """Factory for CSRs with whatever subject and usage extensions a test needs"""
    return _mint_csr


@pytest.fixture(scope="session")
def key_usage() -> KeyUsageFactory:
    """Helper for building KeyUsage extensions without spelling out all nine flags"""
    return _key_usage


@pytest.fixture(scope="module")
def csr_pem() -> str:
    """A plain CSR with a CN and no usage extensions, as most clients send"""
    return _mint_csr("test leaf")


@pytest.fixture(scope="module")
def ca_chain_path() -> Path:
    """Filesystem path to the trust bundle, for settings that read the CA from disk"""
    return CA_PUBLIC_PATH / "ca_chain.pem"
