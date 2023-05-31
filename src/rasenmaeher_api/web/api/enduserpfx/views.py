"""Enduser API views."""
import logging
import os
import json
from typing import cast, Dict, Any

import OpenSSL.crypto
import requests
from fastapi import APIRouter, Response

router = APIRouter()

LOGGER = logging.getLogger(__name__)


async def pem_to_pfx(pem_key: str, pem_cert: str) -> bytes:
    """Convert PEM data to PFX (PKCS12)."""
    pfx = OpenSSL.crypto.PKCS12()
    pfx.set_privatekey(OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, bytes(pem_key, "UTF-8")))
    pfx.set_certificate(OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, bytes(pem_cert, "UTF-8")))
    pfxdata = pfx.export()
    return pfxdata


async def new_key(callsign: str) -> Dict[Any, Any]:
    """pfx"""
    url = "http://127.0.0.1:8888/api/v1/cfssl/newkey"

    payload = json.dumps(
        {
            "hosts": [callsign],
            "CN": callsign,
            "names": [{"C": "FI", "ST": "Helsinki", "L": "Etela-Suomi", "O": "Puolustusvoimat"}],
            "key": {"algo": "rsa", "size": 4096},
        }
    )
    headers = {"Content-Type": "application/json"}

    response = requests.request("POST", url, headers=headers, data=payload, timeout=10)
    data = response.json().get("result")
    return cast(Dict[Any, Any], data)


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


async def save_key(pem_key: str) -> None:
    """Save key to file."""
    callsign = "OTTER1"
    try:
        if not os.path.exists(f"/data/persistent/{callsign}"):
            os.makedirs(f"/data/persistent/{callsign}")
        with open(f"/data/persistent/{callsign}/{callsign}.pem", "wb") as file:
            file.write(bytes(pem_key, "UTF-8"))
    except OSError as _e:
        LOGGER.info("Error: %s : %s", _e.filename, _e.strerror)


async def save_pfx(pfx: bytes) -> None:
    """Save PFX to file."""
    callsign = "OTTER1"
    try:
        if not os.path.exists(f"/data/persistent/{callsign}"):
            os.makedirs(f"/data/persistent/{callsign}")
        with open(f"/data/persistent/{callsign}/{callsign}.pfx", "wb") as file:
            file.write(pfx)
    except OSError as _e:
        LOGGER.info("Error: %s : %s", _e.filename, _e.strerror)


@router.post("/")
async def return_enduser_certs() -> Response:
    """
    Method to create key, sign CSR and return PFX
    :returns pfx
    """
    _newkeybundle = await new_key("OTTER1")
    _key = cast(str, _newkeybundle.get("private_key"))
    _csr = cast(str, _newkeybundle.get("certificate_request"))
    _cert = await sign_csr(_csr)
    _pfx = await pem_to_pfx(_key, _cert)
    await save_key(_key)
    await save_pfx(_pfx)
    return Response(content=_pfx, media_type="application/x-pkcs12")
