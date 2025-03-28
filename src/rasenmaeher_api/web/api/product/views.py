"""Product registration API views."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from libadvian.binpackers import ensure_utf8, ensure_str
from libpvarki.middleware.mtlsheader import MTLSHeader
from libpvarki.schemas.generic import OperationResultResponse
from libpvarki.schemas.product import ReadyRequest
from multikeyjwt.middleware import JWTBearer
from OpenSSL.crypto import load_certificate_request, FILETYPE_PEM  # FIXME: use cryptography instead of pyOpenSSL


from .schema import CertificatesResponse, CertificatesRequest, RevokeRequest
from ....db.nonces import SeenToken
from ....db.errors import NotFound
from ....cfssl.public import get_ca, get_bundle
from ....cfssl.private import sign_csr, revoke_pem
from ....cfssl.base import CFSSLError
from ....rmsettings import RMSettings


router = APIRouter()
LOGGER = logging.getLogger(__name__)


async def csr_common(certs: CertificatesRequest) -> CertificatesResponse:
    """Common parts of CSR handling"""
    cachain = await get_ca()
    certpem = (await sign_csr(certs.csr)).replace("\\n", "\n")
    bundlepem = await get_bundle(certpem)

    return CertificatesResponse(
        ca=cachain,
        certificate=bundlepem,
    )


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

    resp = await csr_common(certs)
    await SeenToken.use_token(jwtpayload["nonce"])
    return resp


@router.post("/sign_csr/mtls", dependencies=[Depends(MTLSHeader(auto_error=True))])
async def return_ca_and_sign_csr_mtls(
    request: Request,
    certs: CertificatesRequest,
) -> CertificatesResponse:
    """Allow product with mTLS cert to request signatures for other certs"""
    payload = request.state.mtlsdn
    if payload.get("CN") not in RMSettings.singleton().valid_product_cns:
        raise HTTPException(status_code=403)
    return await csr_common(certs)


@router.post("/revoke/mtls", dependencies=[Depends(MTLSHeader(auto_error=True))])
async def revoke_cert(
    request: Request,
    cert: RevokeRequest,
) -> OperationResultResponse:
    """Allow product with mTLS cert to revoke a cert"""
    payload = request.state.mtlsdn
    if payload.get("CN") not in RMSettings.singleton().valid_product_cns:
        raise HTTPException(status_code=403)
    try:
        await revoke_pem(cert.cert, "unspecified")
        return OperationResultResponse(success=True)
    except CFSSLError as exc:
        LOGGER.error("Revoke failed: {}".format(exc))
        return OperationResultResponse(success=False, error=str(exc))


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
    certpem = (await sign_csr(certs.csr)).replace("\\n", "\n")
    bundlepem = await get_bundle(certpem)

    return CertificatesResponse(
        ca=cachain,
        certificate=bundlepem,
    )


@router.post("/ready", dependencies=[Depends(MTLSHeader(auto_error=True))])
async def signal_ready(
    meta: ReadyRequest,
) -> OperationResultResponse:
    """Used by product integration API to signify everything is ready in their end"""
    # FIXME: Actually do something
    _ = meta

    return OperationResultResponse(success=True, extra="This was actually NO-OP")
