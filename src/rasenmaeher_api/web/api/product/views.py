"""Product registration API views."""

import logging
from typing import cast

import aiohttp
from cryptography import x509
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.x509.oid import ExtensionOID, NameOID
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from libadvian.binpackers import ensure_utf8
from libpvarki.middleware.mtlsheader import MTLSHeader
from libpvarki.schemas.generic import OperationResultResponse
from libpvarki.schemas.product import ReadyRequest, UserCRUDRequest
from multikeyjwt.middleware import JWTBearer

from rasenmaeher_api.db.issuedcerts import record_issued_cert

from ....cert.backend import CertError, get_bundle, get_ca, revoke_pem, sign_csr
from ....cert.usages import KeyUsages, csr_usages
from ....db import Person
from ....db.errors import NotFound
from ....db.nonces import SeenToken
from ....kchelpers import KCClient
from ....mtlsinit import get_session_winit
from ....productapihelpers import post_to_product
from ....rmsettings import RMSettings
from ..middleware.user import ValidUser
from ..utils.auditcontext import build_audit_extra
from .schema import CertificatesRequest, CertificatesResponse, KCClientToken, ProductAddRequest, RevokeRequest

router = APIRouter()
LOGGER = logging.getLogger(__name__)

# What a product's own CSR carries when its certificate is first issued: client and server auth, its name as DNS SAN
RENEW_USAGES: frozenset[KeyUsages] = frozenset(
    {"digital signature", "key encipherment", "data encipherment", "client auth", "server auth"}
)
RENEW_EXTENSIONS = frozenset(
    {
        ExtensionOID.BASIC_CONSTRAINTS,
        ExtensionOID.KEY_USAGE,
        ExtensionOID.EXTENDED_KEY_USAGE,
        ExtensionOID.SUBJECT_ALTERNATIVE_NAME,
    }
)
RENEW_REFUSED = "Renewal not allowed"


async def csr_common(certs: CertificatesRequest) -> CertificatesResponse:
    """Common parts of CSR handling"""
    try:
        signed_by_own_key = x509.load_pem_x509_csr(ensure_utf8(certs.csr)).is_signature_valid
    except ValueError:
        signed_by_own_key = False
    if not signed_by_own_key:
        raise HTTPException(status_code=400, detail="CSR is not signed by its own key")
    cachain = await get_ca()
    try:
        certpem = (await sign_csr(certs.csr)).replace("\\n", "\n")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    bundlepem = await get_bundle(certpem)

    await record_issued_cert(certpem)

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
    except CertError as exc:
        LOGGER.error(f"Revoke failed: {exc}")
        return OperationResultResponse(success=False, error=str(exc))


def renewal_error(csrpem: str, peer_cn: str | None) -> str | None:
    """Why the CSR is not a renewal of the calling product's own certificate, None when it is"""
    if peer_cn is None or peer_cn not in RMSettings.singleton().valid_product_cns:
        return "NOT_A_PRODUCT"
    try:
        csr = x509.load_pem_x509_csr(ensure_utf8(csrpem))
        if not csr.is_signature_valid:
            return "CSR_SIGNATURE_INVALID"
        cns = csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        if len(csr.subject) != 1 or len(cns) != 1 or cns[0].value != peer_cn:
            return "CSR_SUBJECT_MISMATCH"
        if [attribute.oid.dotted_string for attribute in csr.attributes] not in ([], ["1.2.840.113549.1.9.14"]):
            return "CSR_EXTENSION_NOT_ALLOWED"
        for ext in csr.extensions:
            if ext.oid not in RENEW_EXTENSIONS:
                return "CSR_EXTENSION_NOT_ALLOWED"
            if isinstance(ext.value, x509.BasicConstraints) and ext.value.ca:
                return "CSR_EXTENSION_NOT_ALLOWED"
            if isinstance(ext.value, x509.SubjectAlternativeName) and list(ext.value) != [x509.DNSName(peer_cn)]:
                return "CSR_SUBJECT_MISMATCH"
        if not set(csr_usages(csrpem)) <= RENEW_USAGES:
            return "CSR_USAGE_NOT_ALLOWED"
    except (ValueError, x509.DuplicateExtension, x509.UnsupportedGeneralNameType, UnsupportedAlgorithm):
        return "CSR_INVALID"
    return None


@router.post("/renew_csr", dependencies=[Depends(MTLSHeader(auto_error=True))])
async def renew_csr(
    request: Request,
    certs: CertificatesRequest,
) -> CertificatesResponse:
    """Used by product integration API to request renew of their mTLS client cert"""
    peer_cn = request.state.mtlsdn.get("CN")
    error_code = renewal_error(certs.csr, peer_cn)
    if error_code is None:
        try:
            resp = await csr_common(certs)
            LOGGER.audit(  # type: ignore[attr-defined]
                "Product certificate renewed",
                extra=build_audit_extra(action="product_cert_renew", outcome="success", actor=peer_cn, request=request),
            )
            return resp
        except HTTPException:
            error_code = "SIGNING_REFUSED"
    LOGGER.audit(  # type: ignore[attr-defined]
        "Product certificate renewal refused",
        extra=build_audit_extra(
            action="product_cert_renew",
            outcome="failure",
            actor=peer_cn,
            request=request,
            error_code=error_code,
        ),
    )
    raise HTTPException(403, RENEW_REFUSED)


@router.post("/ready", dependencies=[Depends(MTLSHeader(auto_error=True))])
async def signal_ready(
    meta: ReadyRequest,
) -> OperationResultResponse:
    """Used by product integration API to signify everything is ready in their end"""
    # FIXME: Actually do something
    _ = meta

    return OperationResultResponse(success=True, extra="This was actually NO-OP")


@router.post("/kctoken", dependencies=[Depends(MTLSHeader(auto_error=True))])
async def get_kc_token(
    request: Request,
) -> KCClientToken:
    """Get a token to self-register a client for OIDC"""
    payload = request.state.mtlsdn
    if payload.get("CN") not in RMSettings.singleton().valid_product_cns:
        raise HTTPException(status_code=403)
    if not RMSettings.singleton().kc_enabled:
        raise HTTPException(403, detail="KC is not enabled")
    data = await KCClient.singleton().client_access_token()
    return KCClientToken.parse_obj(data)


@router.post("/interop/{tgtproduct}", dependencies=[Depends(MTLSHeader(auto_error=True))])
async def add_interop(
    srcproduct: ProductAddRequest,
    tgtproduct: str,
    request: Request,
) -> OperationResultResponse:
    """Product needs interop privileges with another"""
    payload = request.state.mtlsdn
    if payload.get("CN") not in RMSettings.singleton().valid_product_cns:
        raise HTTPException(status_code=403)

    # TODO: Verify that srcproduct certcn and actual cert contents match

    manifest = RMSettings.singleton().kraftwerk_manifest_dict
    if "products" not in manifest:
        LOGGER.error("Manifest does not have products key")
        raise HTTPException(status_code=500, detail="Manifest does not have products key")
    if tgtproduct not in manifest["products"]:
        raise HTTPException(status_code=404, detail=f"Unknown product {tgtproduct}")
    resp = await post_to_product(tgtproduct, "/api/v1/interop/add", srcproduct.model_dump(), OperationResultResponse)
    if resp is None:
        return OperationResultResponse(success=False, error="post_to_product returned None")
    resp = cast(OperationResultResponse, resp)
    return resp


@router.get("/proxy/{tgtproduct}/{tgtpath:path}", dependencies=[Depends(ValidUser(auto_error=True))])
async def get_product_proxy(
    tgtproduct: str,
    tgtpath: str,
    request: Request,
) -> Response:
    """Proxy request to the product in any path, POSTing the user context"""
    rmconf = RMSettings.singleton()
    manifest = rmconf.kraftwerk_manifest_dict
    person = cast(Person, request.state.person)
    if tgtproduct not in manifest["products"]:
        raise HTTPException(status_code=404, detail=f"Unknown product {tgtproduct}")
    if "api/v1/users" in tgtpath:
        LOGGER.audit(f"User {person.callsign} (pk: {person.pk}) tried to access CRUD integration endpoint")  # type: ignore[attr-defined]
        raise HTTPException(status_code=403, detail="Accessing CRUD integration endpoints via proxy is forbidden")
    productconf = manifest["products"][tgtproduct]
    # We do not read the cert for these because it takes time and is not really needed
    user = UserCRUDRequest(uuid=str(person.pk), callsign=person.callsign, x509cert="")
    session = await get_session_winit()
    session.headers.update(
        {
            "X-Rasenmaeher-Proxy": "productproxy",
            "X-Proxy-Callsign": person.callsign,
        }
    )
    async with session as client:
        url = f"{productconf['api']}{tgtpath}"
        LOGGER.debug(f"calling POST({url})")
        response = await client.post(
            url, json=user.model_dump(), timeout=aiohttp.ClientTimeout(total=rmconf.integration_api_timeout * 2)
        )
        return Response(
            status_code=response.status,
            headers=response.headers,
            content=await response.read(),
        )
