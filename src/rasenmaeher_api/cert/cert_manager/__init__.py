"""Cert-Manager wrappers"""

# pylint: disable=duplicate-code  # All cert backends expose identical API surface

from .public import get_ca, get_bundle, get_crl, get_ocsprest_crl
from .private import (
    sign_csr,
    revoke_pem,
    revoke_serial,
    validate_reason,
    refresh_ocsp,
    dump_crlfiles,
    sign_ocsp,
    certadd_pem,
    ReasonTypes,
)
from .anoncsr import anon_sign_csr
from .base import CertManagerError

__all__ = [
    # Public functions
    "get_ca",
    "get_bundle",
    "get_crl",
    "get_ocsprest_crl",
    # Private functions
    "sign_csr",
    "revoke_pem",
    "revoke_serial",
    "validate_reason",
    "refresh_ocsp",
    "dump_crlfiles",
    "sign_ocsp",
    "certadd_pem",
    # Anonymous functions
    "anon_sign_csr",
    # Types
    "ReasonTypes",
    # Errors
    "CertManagerError",
]
