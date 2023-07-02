"""Product registeration API views."""
import json
from typing import cast
from fastapi import APIRouter
import requests
from rasenmaeher_api.web.api.product.schema import Certificates
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

    response = requests.request("POST", url, headers=headers, data=payload, timeout=5)
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

    response = requests.request("POST", url, headers=headers, data=payload, timeout=5)
    data = response.json().get("result").get("certificate")

    return cast(str, data)


@router.post("/sign_csr")
async def return_ca_and_sign_csr(
    certs: Certificates,
) -> Certificates:
    """
    Method for TAK sign CSR and request CA
    params: csr
    """
    _ca = await get_ca()
    certs.ca = _ca
    certificate = await sign_csr(certs.csr)
    certs.certificate = certificate

    return certs