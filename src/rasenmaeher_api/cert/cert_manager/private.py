"""Private APIs for cert-manager backend.

The signing flow creates a cert-manager ``CertificateRequest`` CR carrying the
caller-provided CSR, polls until cert-manager marks it ``Ready``, and returns
the issued certificate as PEM. Revocation is DB-driven (consumed by the
Traefik callsign-validity plugin), so the revoke functions only best-effort
clean up the CR.
"""

from typing import Union, Any, Dict, Optional, cast
from pathlib import Path
import asyncio
import base64
import logging

import cryptography.x509
from cryptography.hazmat.primitives import serialization
from cryptography.x509.oid import ExtendedKeyUsageOID
from kubernetes.client import ApiException

from ...rmsettings import RMSettings
from .base import CertManagerError
from .k8s import (
    get_custom_objects_api,
    CERT_MANAGER_GROUP,
    CERT_MANAGER_VERSION,
    CERTIFICATEREQUESTS_PLURAL,
)
from .names import cr_name


LOGGER = logging.getLogger(__name__)
_POLL_INTERVAL = 1.0  # seconds between status polls

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


_KEY_USAGE_NAMES = (
    ("digital_signature", "digital signature"),
    ("content_commitment", "content commitment"),
    ("key_encipherment", "key encipherment"),
    ("data_encipherment", "data encipherment"),
    ("key_agreement", "key agreement"),
    ("key_cert_sign", "cert sign"),
    ("crl_sign", "crl sign"),
)

_EXT_KEY_USAGE_NAMES = {
    ExtendedKeyUsageOID.SERVER_AUTH: "server auth",
    ExtendedKeyUsageOID.CLIENT_AUTH: "client auth",
    ExtendedKeyUsageOID.CODE_SIGNING: "code signing",
    ExtendedKeyUsageOID.EMAIL_PROTECTION: "email protection",
    ExtendedKeyUsageOID.TIME_STAMPING: "timestamping",
    ExtendedKeyUsageOID.OCSP_SIGNING: "ocsp signing",
}


def _csr_usages(csr_pem: str) -> list[str]:
    """Extract cert-manager `spec.usages` values from a CSR's KeyUsage extensions.

    cert-manager's admission webhook rejects requests whose declared ``usages``
    don't match the KeyUsage/ExtendedKeyUsage extensions in the CSR. Derive the
    list dynamically so we honor whatever the caller embedded.
    """
    csr = cryptography.x509.load_pem_x509_csr(csr_pem.encode("utf-8"))
    out: list[str] = []
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


def _ready_condition(cr_obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Return the Ready condition dict from a CertificateRequest, or None."""
    status = cr_obj.get("status") or {}
    for cond in status.get("conditions", []) or []:
        if cond.get("type") == "Ready":
            return cast(Dict[str, Any], cond)
    return None


def _build_cr_manifest(name: str, csr_pem: str, csr_b64: str, settings: RMSettings) -> Dict[str, Any]:
    """Build the CertificateRequest CR payload."""
    usages = _csr_usages(csr_pem)
    if not usages:
        # Default for clients that ship a CSR without explicit KeyUsage extensions.
        usages = ["digital signature", "key encipherment", "client auth"]
    return {
        "apiVersion": f"{CERT_MANAGER_GROUP}/{CERT_MANAGER_VERSION}",
        "kind": "CertificateRequest",
        "metadata": {
            "name": name,
            "namespace": settings.cert_manager_namespace,
        },
        "spec": {
            "duration": settings.cert_manager_cert_duration,
            "usages": usages,
            "request": csr_b64,
            "issuerRef": {
                "name": settings.cert_manager_issuer_name,
                "kind": settings.cert_manager_issuer_kind,
                "group": settings.cert_manager_issuer_group,
            },
        },
    }


def _create_cr_sync(name: str, manifest: Dict[str, Any], namespace: str) -> None:
    """Create the CertificateRequest, swallowing AlreadyExists (idempotent submit)."""
    api = get_custom_objects_api()
    try:
        api.create_namespaced_custom_object(
            group=CERT_MANAGER_GROUP,
            version=CERT_MANAGER_VERSION,
            namespace=namespace,
            plural=CERTIFICATEREQUESTS_PLURAL,
            body=manifest,
        )
        LOGGER.info("Created CertificateRequest %s/%s", namespace, name)
    except ApiException as exc:
        if exc.status == 409:
            LOGGER.info("CertificateRequest %s/%s already exists, will poll existing", namespace, name)
            return
        raise CertManagerError(f"Failed to create CertificateRequest {namespace}/{name}: {exc}") from exc


def _get_cr_sync(name: str, namespace: str) -> Dict[str, Any]:
    """Fetch a CertificateRequest. Raises on HTTP error."""
    api = get_custom_objects_api()
    return cast(
        Dict[str, Any],
        api.get_namespaced_custom_object(
            group=CERT_MANAGER_GROUP,
            version=CERT_MANAGER_VERSION,
            namespace=namespace,
            plural=CERTIFICATEREQUESTS_PLURAL,
            name=name,
        ),
    )


def _delete_cr_sync(name: str, namespace: str) -> bool:
    """Delete a CertificateRequest. Returns True if deleted, False if it didn't exist."""
    api = get_custom_objects_api()
    try:
        api.delete_namespaced_custom_object(
            group=CERT_MANAGER_GROUP,
            version=CERT_MANAGER_VERSION,
            namespace=namespace,
            plural=CERTIFICATEREQUESTS_PLURAL,
            name=name,
        )
        return True
    except ApiException as exc:
        if exc.status == 404:
            return False
        raise


async def sign_csr(csr: str, bundle: bool = True) -> str:
    """
    Sign CSR via cert-manager by submitting a CertificateRequest CR.
    params: csr, whether to return cert or full bundle
    returns: certificate as PEM (with bundle appended if requested)
    """
    settings = RMSettings.singleton()
    cn = _csr_common_name(csr)
    name = cr_name(cn) if cn else f"rm-anon-{base64.urlsafe_b64encode(csr.encode()).decode()[:10].lower()}"
    namespace = settings.cert_manager_namespace
    csr_b64 = _csr_pem_to_b64(csr)
    manifest = _build_cr_manifest(name, csr, csr_b64, settings)

    await asyncio.to_thread(_create_cr_sync, name, manifest, namespace)

    deadline = asyncio.get_event_loop().time() + settings.cert_manager_timeout
    while True:
        cr_obj = await asyncio.to_thread(_get_cr_sync, name, namespace)
        cond = _ready_condition(cr_obj)
        if cond is not None:
            status = cond.get("status")
            if status == "True":
                cert_b64 = (cr_obj.get("status") or {}).get("certificate")
                if not cert_b64:
                    raise CertManagerError(f"CertificateRequest {namespace}/{name} ready but no certificate in status")
                cert_pem = base64.b64decode(cert_b64).decode("utf-8")
                if bundle:
                    # Late import to avoid a cycle.
                    from .public import get_ca  # pylint: disable=import-outside-toplevel

                    ca_pem = await get_ca()
                    if not cert_pem.endswith("\n"):
                        cert_pem += "\n"
                    cert_pem += ca_pem
                return cert_pem
            if status == "False":
                reason = cond.get("reason", "Unknown")
                msg = cond.get("message", "")
                raise CertManagerError(f"CertificateRequest {namespace}/{name} failed: reason={reason} message={msg}")
        if asyncio.get_event_loop().time() >= deadline:
            raise CertManagerError(
                f"CertificateRequest {namespace}/{name} did not become Ready within {settings.cert_manager_timeout}s"
            )
        await asyncio.sleep(_POLL_INTERVAL)


async def sign_ocsp(cert: str, status: str = "good") -> Any:
    """OCSP signing — not used under cert-manager. No-op for compatibility."""
    LOGGER.debug("sign_ocsp called under cert-manager backend; no-op")
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
    if isinstance(pem, Path):
        pem = pem.read_text("utf-8")
    settings = RMSettings.singleton()
    if not settings.cert_manager_cleanup_on_revoke:
        return
    cert = cryptography.x509.load_pem_x509_certificate(pem.encode("utf-8"))
    cn: Optional[str] = None
    for attribute in cert.subject:
        if attribute.oid == cryptography.x509.NameOID.COMMON_NAME:
            cn = cast(str, attribute.value)
            break
    if not cn:
        LOGGER.warning("revoke_pem: cert has no CN, cannot derive CR name; skipping cleanup")
        return
    name = cr_name(cn)
    try:
        deleted = await asyncio.to_thread(_delete_cr_sync, name, settings.cert_manager_namespace)
    except ApiException as exc:
        LOGGER.warning("revoke_pem: failed to delete CR %s: %s", name, exc)
        return
    if deleted:
        LOGGER.info("revoke_pem: deleted CertificateRequest %s/%s", settings.cert_manager_namespace, name)


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
    LOGGER.debug("certadd_pem called under cert-manager backend; no-op")
    return None


async def dump_crlfiles() -> None:
    """CRL dumping is not applicable under cert-manager. No-op."""
    LOGGER.debug("dump_crlfiles called under cert-manager backend; no-op")


async def refresh_ocsp() -> None:
    """OCSP refresh is not applicable under cert-manager. No-op."""
    LOGGER.debug("refresh_ocsp called under cert-manager backend; no-op")
