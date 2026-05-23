"""Anonymous CSR signing for cert-manager backend.

Under cert-manager the auth context is the pod's ServiceAccount (mounted via
the projected token), not the mTLS bootstrap state. There is no
``anonymous-vs-authenticated`` distinction at the CA layer, so we simply
delegate to the regular ``sign_csr``.
"""

from .private import sign_csr


async def anon_sign_csr(csr: str, bundle: bool = True) -> str:
    """Sign CSR without mTLS-context auth (used by ``mtls_init`` bootstrap)."""
    return await sign_csr(csr, bundle=bundle)
