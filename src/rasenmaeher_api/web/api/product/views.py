"""Product registeration API views."""
from typing import cast
import json


from fastapi import APIRouter
import requests  # FIXME: switch to aiohttp


from .schema import CertificatesResponse, CertificatesRequest, ReadyRequest, GenericResponse
from ....settings import settings


router = APIRouter()


async def get_ca() -> str:
    """
    Quick and dirty method to get CA from CFSSL
    returns: CA certificate
    """
    url = f"{settings.cfssl_host}:{settings.cfssl_port}/api/v1/cfssl/info"

    payload = json.dumps({})
    headers = {"Content-Type": "application/json"}

    response = requests.request("POST", url, headers=headers, data=payload, timeout=5)  # FIXME: switch to aiohttp
    data = response.json().get("result").get("certificate")

    return cast(str, data)


async def sign_csr(csr: str) -> str:
    """
    Quick and dirty method to sign CSR from CFSSL
    params: csr
    returns: certificate
    """
    url = f"{settings.cfssl_host}:{settings.cfssl_port}/api/v1/cfssl/sign"

    payload = json.dumps({"certificate_request": csr})
    headers = {"Content-Type": "application/json"}

    response = requests.request("POST", url, headers=headers, data=payload, timeout=5)  # FIXME: switch to aiohttp
    data = response.json().get("result").get("certificate")

    return cast(str, data)


# FIXME: Require JWT auth
@router.post("/sign_csr")
async def return_ca_and_sign_csr(
    certs: CertificatesRequest,
) -> CertificatesResponse:
    """Used by product integration API to request signing of their mTLS client cert"""
    cachain = await get_ca()
    certificate = await sign_csr(certs.csr)

    return CertificatesResponse(
        ca=cachain,
        certificate=certificate,
    )


# FIXME: Require mTLS auth
@router.post("/renew_csr")
async def renew_csr(
    certs: CertificatesRequest,
) -> CertificatesResponse:
    """Used by product integration API to request renew of their mTLS client cert"""
    cachain = await get_ca()
    certificate = await sign_csr(certs.csr)

    return CertificatesResponse(
        ca=cachain,
        certificate=certificate,
    )


# FIXME: Require mTLS auth
@router.post("/ready")
async def signal_ready(
    meta: ReadyRequest,
) -> GenericResponse:
    """Used by product integration API to signify everything is ready in their end"""
    # FIXME: Actually do something
    _ = meta

    return GenericResponse(ok=True, message="This was actually NO-OP")
