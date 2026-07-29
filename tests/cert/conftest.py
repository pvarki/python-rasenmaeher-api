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
