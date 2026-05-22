"""Private APIs for cert-manager backend.

All functions are placeholders that raise NotImplementedError.
"""

from typing import Union, Any
from pathlib import Path

import cryptography.x509

ReasonTypes = Union[cryptography.x509.ReasonFlags, str]


async def dump_crlfiles() -> None:
    """Dump CRL files."""
    raise NotImplementedError("cert-manager backend: dump_crlfiles not implemented")


async def refresh_ocsp() -> None:
    """Refresh OCSP."""
    raise NotImplementedError("cert-manager backend: refresh_ocsp not implemented")


async def sign_csr(csr: str, bundle: bool = True) -> str:
    """
    Sign CSR using cert-manager.
    params: csr, whether to return cert of full bundle
    returns: certificate as PEM
    """
    raise NotImplementedError("cert-manager backend: sign_csr not implemented")


async def sign_ocsp(cert: str, status: str = "good") -> Any:
    """
    Sign OCSP response.
    """
    raise NotImplementedError("cert-manager backend: sign_ocsp not implemented")


def validate_reason(reason: ReasonTypes) -> cryptography.x509.ReasonFlags:
    """Resolve the given reason into the actual flag."""
    by_name = {str(flag.name): flag for flag in cryptography.x509.ReasonFlags}
    by_value = {str(flag.value): flag for flag in cryptography.x509.ReasonFlags}
    str_reasons = dict(by_value)
    str_reasons.update(by_name)
    if isinstance(reason, str):
        by_val = str_reasons.get(reason)
        if by_val is None:
            raise ValueError(f"Could not resolve '{reason}' into cryptography.x509.ReasonFlags")
        return by_val
    if not isinstance(reason, cryptography.x509.ReasonFlags):
        raise ValueError(f"{reason} is not valid cryptography.x509.ReasonFlags (or string version of the value)")
    return reason


async def revoke_pem(pem: Union[str, Path], reason: ReasonTypes) -> None:
    """Revoke certificate by PEM.

    Reason must be one of the enumerations of cryptography.x509.ReasonFlags.
    If path is given it's read_text()d.
    """
    raise NotImplementedError("cert-manager backend: revoke_pem not implemented")


async def revoke_serial(serialno: str, authority_key_id: str, reason: ReasonTypes) -> None:
    """Revoke certificate by serial number.

    authority_key_id must be formatted correctly.
    Reason must be one of the enumerations of cryptography.x509.ReasonFlags.
    """
    raise NotImplementedError("cert-manager backend: revoke_serial not implemented")


async def certadd_pem(pem: Union[str, Path], status: str = "good") -> Any:
    """Add certificate to database.

    If path is given it's read_text()d.
    """
    raise NotImplementedError("cert-manager backend: certadd_pem not implemented")
