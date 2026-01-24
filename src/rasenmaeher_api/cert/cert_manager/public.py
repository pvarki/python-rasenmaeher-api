"""Public things for cert-manager backend - CA cert, CRL etc.

All functions are placeholders that raise NotImplementedError.
"""


async def get_ca() -> str:
    """
    Get CA certificate from cert-manager.
    returns: CA certificate
    """
    raise NotImplementedError("cert-manager backend: get_ca not implemented")


async def get_ocsprest_crl(suffix: str) -> bytes:
    """Fetch CRL from cert-manager."""
    raise NotImplementedError("cert-manager backend: get_ocsprest_crl not implemented")


async def get_crl() -> bytes:
    """
    Get CRL from cert-manager.
    returns: DER binary encoded Certificate Revocation List
    """
    raise NotImplementedError("cert-manager backend: get_crl not implemented")


async def get_bundle(cert: str) -> str:
    """
    Get the optimal cert bundle for given cert.
    """
    raise NotImplementedError("cert-manager backend: get_bundle not implemented")
