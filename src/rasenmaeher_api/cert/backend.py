"""Certificate operations module with configurable backend."""

from ..rmsettings import CertBackend, RMSettings
from .errors import CertError, DBLocked, ErrorResult, NoResult, NoValue

_backend = RMSettings.singleton().cert_backend

if _backend == CertBackend.CERT_MANAGER:
    from .cert_manager import (
        ReasonTypes,
        anon_sign_csr,
        certadd_pem,
        dump_crlfiles,
        get_bundle,
        get_ca,
        get_crl,
        get_ocsprest_crl,
        refresh_ocsp,
        revoke_pem,
        revoke_serial,
        sign_csr,
        sign_ocsp,
        validate_reason,
    )
elif _backend == CertBackend.CFSSL:
    from .cfssl import (
        ReasonTypes,
        anon_sign_csr,
        certadd_pem,
        dump_crlfiles,
        get_bundle,
        get_ca,
        get_crl,
        get_ocsprest_crl,
        refresh_ocsp,
        revoke_pem,
        revoke_serial,
        sign_csr,
        sign_ocsp,
        validate_reason,
    )
else:
    raise ValueError(f"Unknown cert backend: {_backend}")

__all__ = [
    # Errors (always available)
    "CertError",
    "DBLocked",
    "ErrorResult",
    "NoResult",
    "NoValue",
    # Types
    "ReasonTypes",
    # Anonymous functions
    "anon_sign_csr",
    "certadd_pem",
    "dump_crlfiles",
    "get_bundle",
    # Public functions
    "get_ca",
    "get_crl",
    "get_ocsprest_crl",
    "refresh_ocsp",
    "revoke_pem",
    "revoke_serial",
    # Private functions
    "sign_csr",
    "sign_ocsp",
    "validate_reason",
]
