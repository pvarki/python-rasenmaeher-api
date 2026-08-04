"""Test the lean chain assembly that mimics CFSSL's ``flavor=optimal`` bundle"""

import logging

import cryptography
import pytest

from rasenmaeher_api.cert.cert_manager.chain import lean_chain
from tests.cert.helpers import FakePKI

LOGGER = logging.getLogger(__name__)


def _subjects(pem: str) -> list[cryptography.x509.Name]:
    """Subject DNs of every cert in a PEM blob, in order"""
    return [cert.subject for cert in cryptography.x509.load_pem_x509_certificates(pem.encode("utf-8"))]


def test_empty_input() -> None:
    """No blobs at all yields an empty string"""
    assert lean_chain() == ""


@pytest.mark.parametrize("blob", ("", "   ", "\n"))
def test_blank_blobs_ignored(blob: str) -> None:
    """Empty and whitespace-only blobs are skipped instead of raising"""
    assert lean_chain(blob) == ""


def test_input_order_preserved(leaf_pem: str, intermediate_ca_pem: str) -> None:
    """The leaf stays first, intermediates follow in input order"""
    out = lean_chain(leaf_pem, intermediate_ca_pem)
    assert _subjects(out) == _subjects(leaf_pem) + _subjects(intermediate_ca_pem)


def test_root_dropped(root_ca_pem: str, intermediate_ca_pem: str) -> None:
    """A self-signed cert (subject == issuer) is not part of the output"""
    out = lean_chain(root_ca_pem, intermediate_ca_pem)
    assert _subjects(out) == _subjects(intermediate_ca_pem)


def test_only_root_yields_empty(root_ca_pem: str) -> None:
    """A bundle that is nothing but the root collapses to an empty string"""
    out = lean_chain(root_ca_pem)
    assert out == ""


def test_duplicate_intermediate_deduped(leaf_pem: str, intermediate_ca_pem: str, ca_chain_pem: str) -> None:
    """The same intermediate appearing in several blobs shows up exactly once"""
    out = lean_chain(leaf_pem, ca_chain_pem, intermediate_ca_pem)
    assert _subjects(out) == _subjects(leaf_pem) + _subjects(intermediate_ca_pem)


def test_multi_cert_blob_expanded(pki: FakePKI) -> None:
    """A single blob holding several PEM certs is parsed into all of them"""
    out = lean_chain(pki.leaf + pki.intermediate)
    assert _subjects(out) == _subjects(pki.leaf) + _subjects(pki.intermediate)


def test_output_is_canonical_pem(pki: FakePKI, ca_chain_pem: str) -> None:
    """Output is canonical PEM: no stray armor, and stable under a second pass"""
    out = lean_chain(pki.leaf, ca_chain_pem)
    assert out.startswith("-----BEGIN CERTIFICATE-----")
    assert out.endswith("-----END CERTIFICATE-----\n")
    assert out.count("-----BEGIN CERTIFICATE-----") == 2
    assert lean_chain(out) == out


def test_invalid_pem_raises() -> None:
    """Non-blank garbage that is not PEM propagates the parse error"""
    with pytest.raises(ValueError):
        lean_chain("not a cert")
