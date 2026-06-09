"""Resource-name derivation helpers for cert-manager backend."""

import hashlib
import re
from typing import Optional


def cr_name(csr: str, callsign: Optional[str]) -> str:
    """Derive a Kubernetes resource name for a callsign's CertificateRequest.

    Callsigns can include characters outside the k8s ``[a-z0-9-]{1,253}`` set,
    so we slugify and append a hash generated from the certificate signing
    request to ensure uniqueness.
    """
    identifier: str = callsign or "anon"

    slug = re.sub(r"[^a-z0-9-]", "-", identifier.lower()).strip("-")[:40]
    digest = hashlib.sha256(csr.encode("utf-8")).hexdigest()[:10]
    return "-".join(filter(None, ("rm", slug, digest)))


def cr_name_for_serial(serial: str) -> str:
    """Derive a Kubernetes resource name from a cert serial number.

    Used by revoke flows that only have a serial available — best-effort
    cleanup of any matching CertificateRequest.
    """
    digest = hashlib.sha256(serial.encode("utf-8")).hexdigest()[:10]
    return f"rm-serial-{digest}"
