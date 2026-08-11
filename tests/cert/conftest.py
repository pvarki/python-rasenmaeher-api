"""Fixtures for the cert backend tests: the real test CA PEMs and a throwaway generated PKI.

The builders and their types live in helpers.py; this file holds only fixtures.
"""

import logging
from pathlib import Path

import pytest

from .helpers import (
    CA_PUBLIC_PATH,
    CertFactory,
    CsrFactory,
    FakePKI,
    KeyUsageFactory,
    make_cert,
    make_csr,
    make_key_usage,
    make_name,
)

LOGGER = logging.getLogger(__name__)


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
def ca_chain_path() -> Path:
    """Filesystem path to the trust bundle, for settings that read the CA from disk"""
    return CA_PUBLIC_PATH / "ca_chain.pem"


@pytest.fixture(scope="module")
def pki() -> FakePKI:
    """A throwaway leaf -> intermediate -> self-signed root chain"""
    root_pem, root_key = make_cert("test root", ca=True)
    inter_pem, inter_key = make_cert("test intermediate", make_name("test root"), root_key, ca=True)
    leaf, _ = make_cert("test leaf", make_name("test intermediate"), inter_key, ca=False)
    return FakePKI(root=root_pem, intermediate=inter_pem, leaf=leaf)


@pytest.fixture(scope="module")
def leaf_pem(pki: FakePKI) -> str:
    """A leaf (end-entity) certificate PEM issued by the generated intermediate"""
    return pki.leaf


@pytest.fixture(scope="module")
def csr_pem() -> str:
    """A plain CSR with a CN and no usage extensions, as most clients send"""
    return make_csr("test leaf")


@pytest.fixture(scope="session")
def mint_cert() -> CertFactory:
    """Factory for bespoke certs when the standard pki fixture is not enough"""
    return make_cert


@pytest.fixture(scope="session")
def mint_csr() -> CsrFactory:
    """Factory for CSRs with whatever subject and usage extensions a test needs"""
    return make_csr


@pytest.fixture(scope="session")
def key_usage() -> KeyUsageFactory:
    """Helper for building KeyUsage extensions without spelling out all nine flags"""
    return make_key_usage
