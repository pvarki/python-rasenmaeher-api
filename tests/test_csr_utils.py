"""Unit tests for CSR verification

Build certificate requests in memory and check what
``verify_csr`` accepts.
"""

import logging
from typing import Any

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import NameOID

from rasenmaeher_api.web.api.utils.csr_utils import csr_carries_enrolment_proof, verify_csr

LOGGER = logging.getLogger(__name__)


def _csr(subject: x509.Name, key: object | None = None) -> str:
    """A signed CSR for the given subject, EC by default"""
    signing_key = key or ec.generate_private_key(ec.SECP256R1())
    csr = x509.CertificateSigningRequestBuilder().subject_name(subject).sign(signing_key, hashes.SHA256())
    return csr.public_bytes(serialization.Encoding.PEM).decode("utf-8")


def _cn(value: str) -> x509.NameAttribute:
    return x509.NameAttribute(NameOID.COMMON_NAME, value)


def test_exact_common_name_passes() -> None:
    """The normal case"""
    assert verify_csr(_csr(x509.Name([_cn("OTTER1")])), "OTTER1")


def test_rsa_key_passes() -> None:
    """Key type is not what is being checked -- RSA is still what SCEP devices mostly send"""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    assert verify_csr(_csr(x509.Name([_cn("OTTER1")]), key), "OTTER1")


def test_extra_non_cn_attributes_pass() -> None:
    """An MDM may fill O/OU/ST from its own template and nothing downstream reads them"""
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Example"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Devices"),
            _cn("OTTER1"),
        ]
    )
    assert verify_csr(_csr(subject), "OTTER1")


def test_longer_common_name_is_refused() -> None:
    """``CN=OTTER1X`` contains ``CN=OTTER1`` as a substring, which used to be enough"""
    assert not verify_csr(_csr(x509.Name([_cn("OTTER1X")])), "OTTER1")


def test_second_common_name_is_refused() -> None:
    """The escalation: the issued certificate would carry ADMIN, the Person would be OTTER1"""
    subject = x509.Name([_cn("ADMIN"), _cn("OTTER1")])
    assert not verify_csr(_csr(subject), "OTTER1")


def test_callsign_smuggled_into_another_attribute_is_refused() -> None:
    """``OU=CN=OTTER1,CN=ADMIN`` renders a DN containing ``CN=OTTER1`` while the CN is ADMIN"""
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "CN=OTTER1"),
            _cn("ADMIN"),
        ]
    )
    rendered = x509.load_pem_x509_csr(_csr(subject).encode("utf-8")).subject.rfc4514_string()
    assert "CN=OTTER1" in rendered, "precondition: the old substring test would have accepted this"
    assert not verify_csr(_csr(subject), "OTTER1")


def test_subject_without_common_name_is_refused() -> None:
    """An empty callsign used to match ``CN=`` in almost anything"""
    subject = x509.Name([x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Example")])
    assert not verify_csr(_csr(subject), "")


def test_unsigned_csr_is_refused() -> None:
    """Proof of possession: the request must be signed by the key it carries"""
    pem = _csr(x509.Name([_cn("OTTER1")]))
    csr = x509.load_pem_x509_csr(pem.encode("utf-8"))
    der = bytearray(csr.public_bytes(serialization.Encoding.DER))
    der[-1] ^= 0xFF  # break the signature, keep the structure parseable
    try:
        broken = x509.load_der_x509_csr(bytes(der))
    except ValueError:
        pytest.skip("mangled DER no longer parses, cannot exercise the signature path this way")
    broken_pem = broken.public_bytes(serialization.Encoding.PEM).decode("utf-8")
    assert not broken.is_signature_valid, "precondition: the signature must actually be invalid"
    assert not verify_csr(broken_pem, "OTTER1")


def _csr_with_subject(attrs: list[tuple[Any, str]]) -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(oid, value) for oid, value in attrs])
    csr = x509.CertificateSigningRequestBuilder().subject_name(name).sign(key, hashes.SHA256())
    return csr.public_bytes(serialization.Encoding.PEM).decode("utf-8")


def test_the_enrolment_proof_is_required_and_exact() -> None:
    """The callsign alone is a short guessable string, so it cannot be the last gate"""
    good = _csr_with_subject([(NameOID.COMMON_NAME, "OTTER1"), (NameOID.ORGANIZATIONAL_UNIT_NAME, "OTTER1@7F3A9C2B")])
    assert csr_carries_enrolment_proof(good, "OTTER1", "7F3A9C2B")
    assert not csr_carries_enrolment_proof(good, "OTTER1", "WRONGONE")
    assert not csr_carries_enrolment_proof(good, "OTTER2", "7F3A9C2B"), "a code is bound to its callsign"

    bare = _csr_with_subject([(NameOID.COMMON_NAME, "OTTER1")])
    assert not csr_carries_enrolment_proof(bare, "OTTER1", "7F3A9C2B"), "what a guesser would send"


def test_the_proof_is_found_wherever_the_mdm_renders_it() -> None:
    """Which attribute carries it is the MDM's business, so do not hard-code one"""
    for oid in (NameOID.ORGANIZATIONAL_UNIT_NAME, NameOID.ORGANIZATION_NAME, NameOID.STATE_OR_PROVINCE_NAME):
        csrpem = _csr_with_subject([(NameOID.COMMON_NAME, "OTTER1"), (oid, "OTTER1@7F3A9C2B")])
        assert csr_carries_enrolment_proof(csrpem, "OTTER1", "7F3A9C2B")


def test_one_request_is_one_guess() -> None:
    """A guess per attribute would test hundreds of codes in one request, so two proofs are none"""
    batched = _csr_with_subject(
        [
            (NameOID.COMMON_NAME, "OTTER1"),
            (NameOID.ORGANIZATIONAL_UNIT_NAME, "OTTER1@AAAAAAAA"),
            (NameOID.ORGANIZATIONAL_UNIT_NAME, "OTTER1@7F3A9C2B"),
        ]
    )
    assert not csr_carries_enrolment_proof(batched, "OTTER1", "7F3A9C2B")


def test_the_common_name_cannot_be_the_proof() -> None:
    """Otherwise a caller who guessed the callsign could satisfy the check with it"""
    csrpem = _csr_with_subject([(NameOID.COMMON_NAME, "OTTER1@7F3A9C2B")])
    assert not csr_carries_enrolment_proof(csrpem, "OTTER1@7F3A9C2B", "7F3A9C2B")


def test_odd_input_is_refused_rather_than_raising() -> None:
    """This runs on bytes that reached us from a public endpoint"""
    assert not csr_carries_enrolment_proof("not a csr", "OTTER1", "7F3A9C2B")
    assert not csr_carries_enrolment_proof(_csr_with_subject([(NameOID.COMMON_NAME, "OTTER1")]), "OTTER1", "")
    unicode_ou = _csr_with_subject([(NameOID.COMMON_NAME, "OTTER1"), (NameOID.ORGANIZATIONAL_UNIT_NAME, "ÄÄÄ")])
    assert not csr_carries_enrolment_proof(unicode_ou, "OTTER1", "7F3A9C2B"), "must not raise on non-ascii"
