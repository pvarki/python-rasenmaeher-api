"""Product registeration API views."""
from typing import cast, Mapping, Union, Dict, Any


import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request
from libadvian.binpackers import ensure_utf8, ensure_str
from libpvarki.middleware.mtlsheader import MTLSHeader
from multikeyjwt.middleware import JWTBearer
from OpenSSL.crypto import load_certificate_request, FILETYPE_PEM  # FIXME: use cryptography instead of pyOpenSSL


from .schema import CertificatesResponse, CertificatesRequest, ReadyRequest, GenericResponse
from ....settings import settings
from ....db.nonces import SeenToken
from ....db.errors import NotFound


router = APIRouter()


async def get_ca() -> str:
    """
    Quick and dirty method to get CA from CFSSL
    returns: CA certificate
    """
    async with aiohttp.ClientSession() as session:
        session.headers.add("Content-Type", "application/json")
        url = f"{settings.cfssl_host}:{settings.cfssl_port}/api/v1/cfssl/info"
        payload: Dict[str, Any] = {}

        # FIXME: Why does this need to be a POST ??
        async with session.post(url, json=payload, timeout=2.0) as response:
            data = cast(Mapping[str, Union[Any, Mapping[str, Any]]], await response.json())
            result = data.get("result")
            if not result:
                raise ValueError("CFSSL did not return result")
            cert = result.get("certificate")
            if not cert:
                raise ValueError("CFSSL did not return certificate")
            return cast(str, cert)


async def sign_csr(csr: str) -> str:
    """
    Quick and dirty method to sign CSR from CFSSL
    params: csr
    returns: certificate
    """
    async with aiohttp.ClientSession() as session:
        session.headers.add("Content-Type", "application/json")
        url = f"{settings.cfssl_host}:{settings.cfssl_port}/api/v1/cfssl/sign"
        payload = {"certificate_request": csr}
        async with session.post(url, json=payload, timeout=2.0) as response:
            data = cast(Mapping[str, Union[Any, Mapping[str, Any]]], await response.json())
            result = data.get("result")
            if not result:
                raise ValueError("CFSSL did not return result")
            cert = result.get("certificate")
            if not cert:
                raise ValueError("CFSSL did not return certificate")
            return cast(str, cert)


@router.post("/sign_csr", dependencies=[Depends(JWTBearer(auto_error=True))])
async def return_ca_and_sign_csr(
    request: Request,
    certs: CertificatesRequest,
) -> CertificatesResponse:
    """Used by product integration API to request signing of their mTLS client cert"""
    jwtpayload = request.state.jwt
    if "csr" not in jwtpayload or not jwtpayload["csr"]:
        raise HTTPException(403, "JWT does not authorize signing")
    if "nonce" not in jwtpayload or not jwtpayload["nonce"]:
        raise HTTPException(403, "JWT does not provide nonce")

    try:
        # If we can get the token it was used
        await SeenToken.by_token(jwtpayload["nonce"])
        raise HTTPException(403, "This token was already used to sign a cert")
    except NotFound:
        pass

    # PONDER: Should we check jwtpayload["sub"] is among the products in KRAFTWERK manifest ??

    cachain = await get_ca()
    certificate = await sign_csr(certs.csr)

    await SeenToken.use_token(jwtpayload["nonce"])

    return CertificatesResponse(
        ca=cachain,
        certificate=certificate,
    )


@router.post("/renew_csr", dependencies=[Depends(MTLSHeader(auto_error=True))])
async def renew_csr(
    request: Request,
    certs: CertificatesRequest,
) -> CertificatesResponse:
    """Used by product integration API to request renew of their mTLS client cert"""
    req = load_certificate_request(FILETYPE_PEM, ensure_utf8(certs.csr))
    req_dn = dict(req.get_subject().get_components())
    peer_dn = request.state.mtlsdn
    # Make sure the renew is for same name
    if ensure_str(req_dn[b"CN"]) != ensure_str(peer_dn["CN"]):
        raise HTTPException(403, "Renewal must be for same name")

    cachain = await get_ca()
    certificate = await sign_csr(certs.csr)

    return CertificatesResponse(
        ca=cachain,
        certificate=certificate,
    )


@router.post("/ready", dependencies=[Depends(MTLSHeader(auto_error=True))])
async def signal_ready(
    meta: ReadyRequest,
) -> GenericResponse:
    """Used by product integration API to signify everything is ready in their end"""
    # FIXME: Actually do something
    _ = meta

    return GenericResponse(ok=True, message="This was actually NO-OP")
