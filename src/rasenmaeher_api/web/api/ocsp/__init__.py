"""OCSP responder API.

Answers RFC 6960 OCSP queries for certificates issued through the cert-manager
backend. Revocation state lives in the rmapi Postgres ``Person`` table; this
module just translates between the OCSP wire format and that table.

The OCSP response is signed by a dedicated cert-manager-issued signer
(``cert_manager_ocsp_signer_cert_path`` / ``cert_manager_ocsp_signer_key_path``
in RMSettings) — a Certificate CR with ``usages: [digital signature, ocsp
signing]`` and the same issuer as the client certs.
"""

from .views import router

__all__ = ["router"]
