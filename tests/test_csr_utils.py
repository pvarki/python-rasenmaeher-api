"""Test CSR subject verification"""

from pathlib import Path

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from libpvarki.mtlshelp.csr import async_create_client_csr, async_create_keypair, async_create_server_csr

from rasenmaeher_api.web.api.utils.csr_utils import verify_csr
from tests.cert.helpers import CsrFactory, invalidate_signature


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "subject,callsign,expected",
    [
        pytest.param({"CN": "csr_test"}, "csr_test", True, id="exact-match"),
        pytest.param({"CN": "csr_test2"}, "csr_test", False, id="callsign-prefix-of-cn"),
        pytest.param({"CN": "csr_test", "O": "x"}, "csr_test", False, id="extra-subject-attribute"),
        pytest.param({"CN": "a,b"}, "a,b", True, id="rfc4514-escaped-char"),
    ],
)
async def test_verify_csr_subject(subject: dict[str, str], callsign: str, expected: bool, nice_tmpdir: str) -> None:
    """Only a CN-only subject exactly matching the callsign passes"""
    tempdir = Path(nice_tmpdir)
    ckp = await async_create_keypair(tempdir / "user.key", tempdir / "user.pub")
    csrpem = await async_create_client_csr(ckp, tempdir / "user.csr", subject)
    assert verify_csr(csrpem, callsign) is expected


@pytest.mark.asyncio
async def test_verify_csr_rejects_server_csr(nice_tmpdir: str) -> None:
    """A user callsign may not request server auth"""
    tempdir = Path(nice_tmpdir)
    ckp = await async_create_keypair(tempdir / "user.key", tempdir / "user.pub")
    csrpem = await async_create_server_csr(ckp, tempdir / "user.csr", ["csr_test"])
    assert verify_csr(csrpem, "csr_test") is False


def test_verify_csr_rejects_unknown_ext_key_usage(mint_csr: CsrFactory) -> None:
    """An ExtendedKeyUsage OID without a name fails verification instead of raising"""
    csrpem = mint_csr(
        "csr_test", ext_key_usage=[ExtendedKeyUsageOID.CLIENT_AUTH, ExtendedKeyUsageOID.ANY_EXTENDED_KEY_USAGE]
    )
    assert verify_csr(csrpem, "csr_test") is False


def test_verify_csr_requires_valid_signature(mint_csr: CsrFactory) -> None:
    """A CSR must be signed by the key it carries"""
    csrpem = mint_csr("csr_test")
    assert verify_csr(csrpem, "csr_test") is True
    assert verify_csr(invalidate_signature(csrpem), "csr_test") is False


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


def test_extra_non_cn_attributes_are_refused() -> None:
    """The subject is the callsign and nothing else, for a device an MDM enrols too"""
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Example"),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, "Devices"),
            _cn("OTTER1"),
        ]
    )
    assert not verify_csr(_csr(subject), "OTTER1")


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
