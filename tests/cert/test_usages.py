"""Test key usage extraction and the allowed usage rules"""

import pytest
from cryptography.x509 import ObjectIdentifier
from cryptography.x509.oid import ExtendedKeyUsageOID

from rasenmaeher_api.cert.usages import csr_usages, disallowed_usages
from tests.cert.helpers import CsrFactory, KeyUsageFactory


def test_usages_empty_without_extensions(csr_pem: str) -> None:
    """A CSR with no KeyUsage or ExtendedKeyUsage extensions derives no usages"""
    assert csr_usages(csr_pem) == []


def test_key_usage_flags_mapped(mint_csr: CsrFactory, key_usage: KeyUsageFactory) -> None:
    """KeyUsage bits map to their cert-manager names, dependent flags last"""
    plain = mint_csr("example", key_usage(digital_signature=True, key_encipherment=True))
    assert csr_usages(plain) == ["digital signature", "key encipherment"]
    agreement_only = mint_csr("example", key_usage(key_agreement=True))
    assert csr_usages(agreement_only) == ["key agreement"]
    agreement = mint_csr("example", key_usage(key_agreement=True, encipher_only=True, decipher_only=True))
    assert csr_usages(agreement) == ["key agreement", "encipher only", "decipher only"]


def test_ext_key_usage_oids_mapped(mint_csr: CsrFactory) -> None:
    """Known ExtendedKeyUsage OIDs map to their names, unknown ones are dropped"""
    known = mint_csr("example", ext_key_usage=[ExtendedKeyUsageOID.SERVER_AUTH])
    assert csr_usages(known) == ["server auth"]
    unknown = mint_csr("example", ext_key_usage=[ExtendedKeyUsageOID.KERBEROS_PKINIT_KDC])
    assert csr_usages(unknown) == []


@pytest.mark.parametrize(
    ("cn", "key_usage_flags", "ext_key_usage", "expected"),
    [
        ("kissa", {}, None, set()),
        (
            "kissa",
            {"digital_signature": True, "content_commitment": True, "key_encipherment": True},
            [ExtendedKeyUsageOID.CLIENT_AUTH],
            set(),
        ),
        ("fake.localmaeher.dev.pvarki.fi", {}, [ExtendedKeyUsageOID.SERVER_AUTH], set()),
        ("kissa", {}, [ExtendedKeyUsageOID.SERVER_AUTH], {"server auth"}),
        (None, {}, [ExtendedKeyUsageOID.SERVER_AUTH], {"server auth"}),
        (
            "fake.localmaeher.dev.pvarki.fi",
            {},
            [ExtendedKeyUsageOID.SERVER_AUTH, ExtendedKeyUsageOID.CODE_SIGNING],
            {"server auth", "code signing"},
        ),
        ("kissa", {"key_cert_sign": True}, None, {"cert sign"}),
    ],
)
def test_disallowed_usages(
    mint_csr: CsrFactory,
    key_usage: KeyUsageFactory,
    cn: str | None,
    key_usage_flags: dict[str, bool],
    ext_key_usage: list[ObjectIdentifier] | None,
    expected: set[str],
) -> None:
    """Client usages are open to all, server auth only to service CNs, everything else to nobody"""
    csr = mint_csr(cn, key_usage(**key_usage_flags) if key_usage_flags else None, ext_key_usage)
    assert disallowed_usages(csr, cn) == expected
