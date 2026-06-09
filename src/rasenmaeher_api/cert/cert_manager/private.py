"""Private APIs for cert-manager backend.

The signing flow creates a cert-manager ``CertificateRequest`` CR carrying the
caller-provided CSR, waits until cert-manager issues the certificate, and returns
the issued certificate as PEM. Revocation is DB-driven (consumed by the
Traefik callsign-validity plugin), so the revoke functions only best-effort
clean up the CR.
"""

from typing import List, Literal, Tuple, Union, Any, Optional, cast
from pathlib import Path
import base64
import logging

from cloudcoil.errors import ResourceConflict, APIError, ResourceNotFound, WaitTimeout
from cloudcoil.models.cert_manager.v1 import CertificateRequest
import cryptography.x509
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import ExtendedKeyUsageOID

from ...rmsettings import RMSettings
from .base import CertManagerError
from .names import cr_name
from .public import get_ca

LOGGER = logging.getLogger(__name__)

ReasonTypes = Union[cryptography.x509.ReasonFlags, str]


def _csr_pem_to_b64(csr_pem: str) -> str:
    """Encode a PEM-encoded CSR for cert-manager's ``spec.request`` field.

    cert-manager expects the PEM bytes (the entire ``-----BEGIN CERTIFICATE REQUEST-----``
    block) base64-encoded. The admission webhook will base64-decode and then PEM-decode.
    """
    # Round-trip through cryptography to validate the PEM and normalize whitespace.
    csr = cryptography.x509.load_pem_x509_csr(csr_pem.encode("utf-8"))
    normalized_pem = csr.public_bytes(encoding=serialization.Encoding.PEM)
    return base64.b64encode(normalized_pem).decode("ascii")


def _csr_common_name(csr_pem: str) -> Optional[str]:
    """Extract the CN attribute from a PEM CSR, if present."""
    csr = cryptography.x509.load_pem_x509_csr(csr_pem.encode("utf-8"))
    for attribute in csr.subject:
        if attribute.oid == cryptography.x509.NameOID.COMMON_NAME:
            return cast(str, attribute.value)
    return None


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

_KEY_USAGE_NAMES: Tuple[Tuple[str, KeyUsages], ...] = (
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


def _csr_usages(csr_pem: str) -> List[KeyUsages]:
    """Extract cert-manager `spec.usages` values from a CSR's KeyUsage extensions.

    cert-manager's admission webhook rejects requests whose declared ``usages``
    don't match the KeyUsage/ExtendedKeyUsage extensions in the CSR. Derive the
    list dynamically so we honor whatever the caller embedded.
    """
    csr = cryptography.x509.load_pem_x509_csr(csr_pem.encode("utf-8"))
    out: List[KeyUsages] = []
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
            if eku_name:
                out.append(eku_name)
    except cryptography.x509.ExtensionNotFound:
        pass
    return out


async def _create_cr(name: str, namespace: str, csr_pem: str, csr_b64: str, settings: RMSettings) -> CertificateRequest:
    """Create the CertificateRequest and return it."""
    try:
        usages: List[KeyUsages] = _csr_usages(csr_pem)
        if not usages:
            # Default for clients that ship a CSR without explicit KeyUsage extensions.
            usages = ["digital signature", "key encipherment", "client auth"]

        certificate_request = (
            CertificateRequest.builder()
            .metadata(lambda metadata: metadata.name(name).namespace(namespace))
            .spec(
                lambda spec: spec.duration(settings.cert_manager_cert_duration)
                .usages(usages)
                .request(csr_b64)
                .issuer_ref(
                    lambda issuer_ref: issuer_ref.name(settings.cert_manager_issuer_name)
                    .kind(settings.cert_manager_issuer_kind)
                    .group(settings.cert_manager_issuer_group)
                )
            )
        ).build()

        LOGGER.info("Creating CertificateRequest %s/%s", namespace, name)
        LOGGER.debug("CertificateRequest: %s", certificate_request.model_dump_json())

        return await certificate_request.async_create()

    except APIError as exc:
        raise CertManagerError(f"Failed to create CertificateRequest {namespace}/{name}: {exc}") from exc


async def _upsert_cr(name: str, namespace: str, csr_pem: str, csr_b64: str, settings: RMSettings) -> CertificateRequest:
    """Create or fetch an existing CertificateRequest."""
    try:
        return await _create_cr(name, namespace, csr_pem, csr_b64, settings)
    except ResourceConflict:
        LOGGER.info("CertificateRequest %s/%s already exists, will poll existing", namespace, name)
        return await _get_cr(name, namespace)


async def _get_cr(name: str, namespace: str) -> CertificateRequest:
    """Fetch a CertificateRequest. Raises ``ResourceNotFound`` if missing."""
    return await CertificateRequest.async_get(name=name, namespace=namespace)


async def _delete_cr(name: str, namespace: str) -> bool:
    """Delete a CertificateRequest. Returns True if deleted, False if it didn't exist."""
    try:
        await CertificateRequest.async_delete(name=name, namespace=namespace)
        return True
    except ResourceNotFound:
        return False


async def sign_csr(csr: str, bundle: bool = True) -> str:
    """
    Sign CSR via cert-manager by submitting a CertificateRequest CR.
    params: csr, whether to return cert or full bundle
    returns: certificate as PEM (with bundle appended if requested)
    """
    settings = RMSettings.singleton()
    cn = _csr_common_name(csr)
    name = cr_name(csr, cn)
    namespace = settings.cert_manager_namespace
    csr_b64 = _csr_pem_to_b64(csr)

    certificate_request = await _upsert_cr(name, namespace, csr, csr_b64, settings)

    try:
        await certificate_request.async_wait_for(
            lambda _, cr: (req := cast(CertificateRequest, cr)).status is not None
            and req.status.certificate is not None,
            timeout=settings.cert_manager_timeout,
        )
    except WaitTimeout as exc:
        raise CertManagerError(
            f"CertificateRequest {namespace}/{name} did not issue a certificate within {settings.cert_manager_timeout}s"
        ) from exc

    certificate_request = await _get_cr(name, namespace)
    if certificate_request.status is None:
        raise RuntimeError("certificate request has no status")
    if certificate_request.status.certificate is None:
        raise RuntimeError("certificate request status has no certificate")

    cert_pem = base64.b64decode(certificate_request.status.certificate).decode("utf-8")

    if bundle:
        ca_pem = await get_ca()
        cert_pem = cert_pem.rstrip("\n") + "\n" + ca_pem
    return cert_pem


async def sign_ocsp(cert: str, status: str = "good") -> Any:
    """TODO Implement for TAK to use"""
    LOGGER.warning("sign_ocsp not implemented yet as part of cert manager")
    return None


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
    """Best-effort revoke. Under cert-manager, revocation is authoritative in
    the rmapi DB (``Person.deleted``) and is consumed by the Traefik plugin via
    websocket. This function only cleans up the matching CertificateRequest CR.
    """
    validate_reason(reason)
    LOGGER.debug(
        "revoke_pem called under cert-manager backend; no-op aside from DB-driven revocation",
    )


async def revoke_serial(serialno: str, authority_key_id: str, reason: ReasonTypes) -> None:
    """Best-effort revoke by serial. Cert-manager has no serial-indexed lookup,
    so this is effectively a no-op aside from validating the reason.
    """
    validate_reason(reason)
    LOGGER.debug(
        "revoke_serial called under cert-manager backend (serial=%s); no-op aside from DB-driven revocation",
        serialno,
    )


async def certadd_pem(pem: Union[str, Path], status: str = "good") -> Any:
    """Adding to a cert DB is a cfssl concept. No-op under cert-manager."""
    LOGGER.warning("certadd_pem called under cert-manager backend; no-op")
    return None


async def dump_crlfiles() -> None:
    """CRL dumping is not applicable under cert-manager. No-op."""
    LOGGER.warning("dump_crlfiles called under cert-manager backend; no-op")


async def refresh_ocsp() -> None:
    """TODO Implement for TAK to use"""
    LOGGER.debug("refresh_ocsp not implemented yet as part of cert manager")
