"""Resource-name derivation helpers for cert-manager backend."""

import hashlib
import re


def cr_name(callsign: str) -> str:
    """Derive a Kubernetes resource name for a callsign's CertificateRequest.

    Callsigns can include characters outside the k8s ``[a-z0-9-]{1,253}`` set,
    so we slugify and append a stable hash to guarantee uniqueness even when
    sanitization would otherwise collide.
    """
    slug = re.sub(r"[^a-z0-9-]", "-", callsign.lower()).strip("-")[:40]
    digest = hashlib.sha256(callsign.encode("utf-8")).hexdigest()[:10]
    if slug:
        return f"rm-{slug}-{digest}"
    return f"rm-{digest}"


def cr_name_for_serial(serial: str) -> str:
    """Derive a Kubernetes resource name from a cert serial number.

    Used by revoke flows that only have a serial available — best-effort
    cleanup of any matching CertificateRequest.
    """
    digest = hashlib.sha256(serial.encode("utf-8")).hexdigest()[:10]
    return f"rm-serial-{digest}"
