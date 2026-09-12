"""Select a CFSSL TLS profile from the CSR's requested extended key usages."""

from typing import Literal

from cryptography import x509
from cryptography.x509.oid import ExtendedKeyUsageOID


def signing_profile(csr_pem: str) -> Literal["client", "server", "peer"]:
    """Keep client signing as the default and honor explicit server-auth requests."""
    csr = x509.load_pem_x509_csr(csr_pem.encode("utf-8"))
    try:
        usages = csr.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
    except x509.ExtensionNotFound:
        return "client"
    if ExtendedKeyUsageOID.SERVER_AUTH not in usages:
        return "client"
    return "peer" if ExtendedKeyUsageOID.CLIENT_AUTH in usages else "server"
