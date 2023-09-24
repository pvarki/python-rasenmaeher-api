"""Enduser API views."""
import logging

from fastapi import APIRouter, Request, Response, HTTPException, Depends
from multikeyjwt.middleware import JWTBearer, JWTPayload

from ....db import Person

router = APIRouter()
LOGGER = logging.getLogger(__name__)


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
    # Get the person (it will raise NotFound which is 404 HTTPException as well if callsign is not valid)
    person = await Person.by_callsign(callsign)
    return Response(content=person.pfxfile.read_bytes(), media_type="application/x-pkcs12")


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
    # Get the person (it will raise NotFound which is 404 HTTPException as well if callsign is not valid)
    person = await Person.by_callsign(callsign)
    return Response(content=person.pfxfile.read_bytes(), media_type="application/x-pkcs12")
