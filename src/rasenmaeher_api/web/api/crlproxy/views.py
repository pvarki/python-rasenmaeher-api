"""crlproxy API views."""
import base64
from typing import cast

from fastapi import APIRouter, Response
import requests

router = APIRouter()


async def get_crl() -> bytes:
    """
    Quick and dirty method to get CA from CFSSL
    returns: CA certificate
    """
    url = "http://127.0.0.1:8888/api/v1/cfssl/crl"

    response = requests.request("GET", url, timeout=5)
    data = response.json().get("result")
    # decode base64
    data = base64.b64decode(data)

    return cast(bytes, data)


@router.get("/")
async def return_crl() -> Response:
    """
    Method for TAK sign CSR and request CA
    params: csr
    """
    crl = await get_crl()

    return Response(content=crl, media_type="application/pkix-crl")
