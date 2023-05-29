"""Takreg API views."""
import json
from typing import cast
from fastapi import APIRouter
import requests

from rasenmaeher_api.web.api.takreg.schema import Certificates

router = APIRouter()


async def get_ca() -> str:
    """
    Quick and dirty method to get CA from CFSSL
    returns: CA certificate
    """
    url = "http://127.0.0.1:8888/api/v1/cfssl/info"

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
    url = "http://127.0.0.1:8888/api/v1/cfssl/sign"

    payload = json.dumps({"certificate_request": csr})
    headers = {"Content-Type": "application/json"}

    response = requests.request("POST", url, headers=headers, data=payload, timeout=5)
    data = response.json().get("result").get("certificate")

    return cast(str, data)


@router.post("/")
async def request_ca_and_certs(
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
