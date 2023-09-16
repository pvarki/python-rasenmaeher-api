"""Enduser API views."""
import logging
import os
import json
from typing import cast, Dict, Any

import OpenSSL.crypto
import requests
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from fastapi.responses import JSONResponse
from multikeyjwt.middleware import JWTBearer, JWTPayload
from ....settings import settings

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
    url = f"{settings.cfssl_host}:{settings.cfssl_port}/api/v1/cfssl/newkey"

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
    url = f"{settings.cfssl_host}:{settings.cfssl_port}/api/v1/cfssl/sign"

    payload = json.dumps({"certificate_request": csr})
    headers = {"Content-Type": "application/json"}

    response = requests.request("POST", url, headers=headers, data=payload, timeout=5)
    data = response.json().get("result").get("certificate")

    return cast(str, data)


async def save_key(pem_key: str, callsign: str) -> None:
    """Save key to file."""
    try:
        if not os.path.exists(f"/data/persistent/{callsign}"):
            os.makedirs(f"/data/persistent/{callsign}")
        with open(f"/data/persistent/{callsign}/{callsign}.pem", "w", encoding="UTF-8") as file:
            file.write(pem_key)
    except OSError as _e:
        LOGGER.info("Error: %s : %s", _e.filename, _e.strerror)


async def save_pfx(pfx: bytes, callsign: str) -> None:
    """Save PFX to file."""
    try:
        if not os.path.exists(f"/data/persistent/{callsign}"):
            os.makedirs(f"/data/persistent/{callsign}")
        with open(f"/data/persistent/{callsign}/{callsign}.pfx", "wb") as file:
            file.write(pfx)
    except OSError as _e:
        LOGGER.info("Error: %s : %s", _e.filename, _e.strerror)


def check_jwt(jwt: JWTPayload, callsign: str) -> bool:
    """Sanity checks for JWT payload here"""
    if not jwt.get("sub", False):
        LOGGER.error("Requesting JWT must have sub claim")
        raise HTTPException(status_code=403, detail="Forbidden")

    if jwt.get("sub") == callsign:
        return True
    LOGGER.error("Requesting JWT sub claim doesn't match requested callsign")
    raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/{callsign}")
async def return_enduser_certs(
    request: Request,
    callsign: str,
    jwt: JWTPayload = Depends(JWTBearer(auto_error=True)),
) -> Response:
    """
    Method to create key, sign CSR and return PFX
    :param callsign: OTTER1
    :returns pfx
    """
    if callsign is None or callsign == "":
        _reason = "Error. Callsign missing as last parameter"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    # Check that the JWT has sub claim and it mathes requested callsign
    check_jwt(jwt, callsign)

    _newkeybundle = await new_key(callsign)
    _key = cast(str, _newkeybundle.get("private_key"))
    _csr = cast(str, _newkeybundle.get("certificate_request"))
    _cert = await sign_csr(_csr)
    _pfx = await pem_to_pfx(_key, _cert)
    await save_key(_key, callsign)
    await save_pfx(_pfx, callsign)
    return Response(content=_pfx, media_type="application/x-pkcs12")


@router.get("/{callsign}")
async def check_enduser_bundle_available(
    request: Request,
    callsign: str,
    jwt: JWTPayload = Depends(JWTBearer(auto_error=True)),
) -> Response:
    """
    Method to check if bundle is available
    :param callsign: OTTER1
    :returns pfx or 404 error
    """

    if callsign is None or callsign == "":
        _reason = "Error. Callsign missing as last parameter"
        LOGGER.error("{} : {}".format(request.url, _reason))
        raise HTTPException(status_code=400, detail=_reason)

    # Check that the JWT has sub claim and it mathes requested callsign
    check_jwt(jwt, callsign)

    if os.path.exists(f"/data/persistent/{callsign}/{callsign}.pfx"):  # pylint: disable=R1705
        with open(f"/data/persistent/{callsign}/{callsign}.pfx", "rb") as file:
            _pfx = file.read()
        return Response(content=_pfx, media_type="application/x-pkcs12")
    return JSONResponse(content={"result": "Error bundle not found"}, media_type="application/json", status_code=404)
