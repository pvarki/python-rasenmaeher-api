"""Anonymous CSR signing for cert-manager backend.

This is separated to avoid circular imports.
"""


async def anon_sign_csr(csr: str, bundle: bool = True) -> str:
    """
    Sign CSR without authentication (for initial mTLS setup).

    This should only be used by mtlsinit.

    params: csr
    returns: certificate
    """
    raise NotImplementedError("cert-manager backend: anon_sign_csr not implemented")
