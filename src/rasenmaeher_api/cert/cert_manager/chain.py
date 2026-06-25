"""Assemble a lean cert chain matching CFSSL's ``flavor=optimal`` bundle.

cert-manager hands us PEM blobs (the issued cert plus the trust bundle) that,
contain duplicate intermediates and the self-signed root. CFSSL's bundler
dedupes and drops the root for us; this reproduces that shape so both
backends yield identical PFX/bundle output.
"""

from typing import List, Set

import cryptography.x509
from cryptography.hazmat.primitives import hashes, serialization


def lean_chain(*pem_blobs: str) -> str:
    """Leaf first, then unique intermediate CAs; deduplicated by fingerprint
    and with any self-signed root removed. Empty/blank inputs are ignored."""
    certs: List[cryptography.x509.Certificate] = []
    for blob in pem_blobs:
        if blob and blob.strip():
            certs.extend(cryptography.x509.load_pem_x509_certificates(blob.encode("utf-8")))
    seen: Set[bytes] = set()
    ordered: List[cryptography.x509.Certificate] = []
    for cert in certs:
        fingerprint = cert.fingerprint(hashes.SHA256())
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        if cert.subject == cert.issuer:  # drop root
            continue
        ordered.append(cert)
    return b"".join(cert.public_bytes(serialization.Encoding.PEM) for cert in ordered).decode("utf-8")
