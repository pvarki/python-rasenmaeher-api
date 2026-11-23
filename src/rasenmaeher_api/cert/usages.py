"""Key usages a CSR may request, shared by the signing backends and CSR verification"""

from typing import Literal

import cryptography.x509
from cryptography.x509.oid import ExtendedKeyUsageOID

from ..rmsettings import RMSettings

type KeyUsages = Literal[
    "signing",
    "digital signature",
    "content commitment",
    "key encipherment",
    "key agreement",
    "data encipherment",
    "cert sign",
    "crl sign",
    "encipher only",
    "decipher only",
    "any",
    "server auth",
    "client auth",
    "code signing",
    "email protection",
    "s/mime",
    "ipsec end system",
    "ipsec tunnel",
    "ipsec user",
    "timestamping",
    "ocsp signing",
    "microsoft sgc",
    "netscape sgc",
]

_KEY_USAGE_NAMES: tuple[tuple[str, KeyUsages], ...] = (
    ("digital_signature", "digital signature"),
    ("content_commitment", "content commitment"),
    ("key_encipherment", "key encipherment"),
    ("data_encipherment", "data encipherment"),
    ("key_agreement", "key agreement"),
    ("key_cert_sign", "cert sign"),
    ("crl_sign", "crl sign"),
)

_EXT_KEY_USAGE_NAMES: dict[cryptography.x509.ObjectIdentifier, KeyUsages] = {
    ExtendedKeyUsageOID.SERVER_AUTH: "server auth",
    ExtendedKeyUsageOID.CLIENT_AUTH: "client auth",
    ExtendedKeyUsageOID.CODE_SIGNING: "code signing",
    ExtendedKeyUsageOID.EMAIL_PROTECTION: "email protection",
    ExtendedKeyUsageOID.TIME_STAMPING: "timestamping",
    ExtendedKeyUsageOID.OCSP_SIGNING: "ocsp signing",
}

_CLIENT_USAGES: frozenset[KeyUsages] = frozenset(
    {"digital signature", "content commitment", "key encipherment", "client auth"}
)


def csr_usages(csr_pem: str) -> list[KeyUsages]:
    """Extract cert-manager `spec.usages` values from a CSR's KeyUsage extensions.

    cert-manager's admission webhook rejects requests whose declared ``usages``
    don't match the KeyUsage/ExtendedKeyUsage extensions in the CSR. Derive the
    list dynamically so we honor whatever the caller embedded.
    """
    csr = cryptography.x509.load_pem_x509_csr(csr_pem.encode("utf-8"))
    out: list[KeyUsages] = []
    try:
        ku = csr.extensions.get_extension_for_class(cryptography.x509.KeyUsage).value
        for attr, name in _KEY_USAGE_NAMES:
            if getattr(ku, attr, False):
                out.append(name)
        if ku.key_agreement:
            if getattr(ku, "encipher_only", False):
                out.append("encipher only")
            if getattr(ku, "decipher_only", False):
                out.append("decipher only")
    except cryptography.x509.ExtensionNotFound:
        pass
    try:
        eku = csr.extensions.get_extension_for_class(cryptography.x509.ExtendedKeyUsage).value
        for oid in eku:
            eku_name = _EXT_KEY_USAGE_NAMES.get(oid)
            if eku_name is None:
                raise ValueError(f"Unsupported extended key usage {oid.dotted_string}")
            out.append(eku_name)
    except cryptography.x509.ExtensionNotFound:
        pass
    return out


def disallowed_usages(csr_pem: str, cn: str | None) -> set[KeyUsages]:
    """Usages the CSR requests beyond client usages, with server auth allowed only for service CNs"""
    extra = set(csr_usages(csr_pem)) - _CLIENT_USAGES
    if extra == {"server auth"} and cn is not None and RMSettings.singleton().is_reserved_cn(cn):
        return set()
    return extra
