"""Private apis"""
from typing import Union, Optional
import logging
import binascii
from pathlib import Path

import aiohttp
import cryptography.x509

from .base import base_url, get_result_cert, DEFAULT_TIMEOUT, CFSSLError, get_result, NoResult
from .mtls import mtls_session

LOGGER = logging.getLogger(__name__)


ReasonTypes = Union[cryptography.x509.ReasonFlags, str]


async def sign_csr(csr: str) -> str:
    """
    Quick and dirty method to sign CSR from CFSSL
    params: csr
    returns: certificate
    """
    async with (await mtls_session()) as session:
        url = f"{base_url()}/api/v1/cfssl/sign"
        payload = {"certificate_request": csr}
        try:
            async with session.post(url, json=payload, timeout=DEFAULT_TIMEOUT) as response:
                return await get_result_cert(response)
        except aiohttp.ClientError as exc:
            raise CFSSLError(str(exc)) from exc


def validate_reason(reason: ReasonTypes) -> cryptography.x509.ReasonFlags:
    """Resolve the given reason into the actual flag"""
    by_name = {str(flag.name): flag for flag in cryptography.x509.ReasonFlags}
    by_value = {str(flag.value): flag for flag in cryptography.x509.ReasonFlags}
    str_reasons = dict(by_value)
    str_reasons.update(by_name)
    if isinstance(reason, str):
        by_val = str_reasons.get(reason)
        if by_val is None:
            LOGGER.debug("reason '{}' not in {}".format(reason, str_reasons))
            raise ValueError(f"Could not resolve '{reason}' into cryptography.x509.ReasonFlags")
        return by_val
    if not isinstance(reason, cryptography.x509.ReasonFlags):
        raise ValueError(f"{reason} is not valid cryptography.x509.ReasonFlags (or string version of the value)")
    return reason


async def revoke_pem(pem: Union[str, Path], reason: ReasonTypes) -> None:
    """Read the serial number from the PEM cert and call revoke_serial
    Reason must be one of the enumerations of cryptography.x509.ReasonFlags

    If path is given it's read_text()d
    """
    if isinstance(pem, Path):
        pem = pem.read_text("utf-8")
    cert = cryptography.x509.load_pem_x509_certificate(pem.encode("utf-8"))
    kid: Optional[str] = None
    for extension in cert.extensions:
        if extension.oid.dotted_string != "2.5.29.35":  # oid=2.5.29.35, name=authorityKeyIdentifier
            continue
        kid = binascii.hexlify(extension.value.key_identifier).decode("ascii")
    if not kid:
        raise ValueError("Cannot resolve authority_key_id from the cert")
    return await revoke_serial(str(cert.serial_number), kid, reason)


async def revoke_serial(serialno: str, authority_key_id: str, reason: ReasonTypes) -> None:
    """Call the CFSSL revoke endpoint

    authority_key_id must be formatted in the way CFSSL expects it
    Reason must be one of the enumerations of cryptography.x509.ReasonFlags or it's string values (see REASONS_BY_VALUE)
    """
    reason = validate_reason(reason)
    async with (await mtls_session()) as session:
        url = f"{base_url()}/api/v1/cfssl/revoke"
        payload = {
            "serial": serialno,
            "authority_key_id": authority_key_id,
            "reason": str(reason.value).replace("_", ""),
        }
        try:
            async with session.post(url, json=payload, timeout=DEFAULT_TIMEOUT) as response:
                try:
                    await get_result(response)
                except NoResult:
                    # The result is expected to be empty
                    pass
        except aiohttp.ClientError as exc:
            raise CFSSLError(str(exc)) from exc
