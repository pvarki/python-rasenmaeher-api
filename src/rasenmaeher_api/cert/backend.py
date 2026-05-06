"""Certificate operations module with configurable backend."""

from .errors import CertError, NoResult, ErrorResult, DBLocked, NoValue
from ..rmsettings import RMSettings, CertBackend

_backend = RMSettings.singleton().cert_backend

if _backend == CertBackend.CERT_MANAGER:
    from .cert_manager import (
        get_ca,
        get_bundle,
        get_crl,
        get_ocsprest_crl,
        sign_csr,
        revoke_pem,
        revoke_serial,
        validate_reason,
        refresh_ocsp,
        dump_crlfiles,
        sign_ocsp,
        certadd_pem,
        anon_sign_csr,
        ReasonTypes,
    )
elif _backend == CertBackend.CFSSL:
    from .cfssl import (
        get_ca,
        get_bundle,
        get_crl,
        get_ocsprest_crl,
        sign_csr,
        revoke_pem,
        revoke_serial,
        validate_reason,
        refresh_ocsp,
        dump_crlfiles,
        sign_ocsp,
        certadd_pem,
        anon_sign_csr,
        ReasonTypes,
    )
else:
    raise ValueError(f"Unknown cert backend: {_backend}")

__all__ = [
    # Errors (always available)
    "CertError",
    "NoResult",
    "ErrorResult",
    "DBLocked",
    "NoValue",
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
]
