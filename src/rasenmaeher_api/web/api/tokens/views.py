"""Views dealing with login tokens issues by/via TILAUSPALVELU"""
import logging

from fastapi import APIRouter, HTTPException, Depends
from multikeyjwt.jwt.verifier import Verifier
from multikeyjwt.jwt.issuer import Issuer
from multikeyjwt.middleware import JWTBearer, JWTPayload


from .schema import JWTExchangeRequestResponse


router = APIRouter()
LOGGER = logging.getLogger(__name__)
TOKEN_COPY_EXCLUDE_FIELDS = ("iat", "exp", "iss", "aud", "nonce")


@router.post("/exchange", tags=["tokens"], response_model=JWTExchangeRequestResponse)
async def exchange_token(req: JWTExchangeRequestResponse) -> JWTExchangeRequestResponse:
    """API method for converting TILAUSPALVELU issues single-use JWT to RASENMAEHER session JWT"""
    payload = Verifier.singleton().decode(req.jwt)
    if not payload:
        LOGGER.info("No acceptable token found")
        raise HTTPException(status_code=403, detail="Not authenticated")
    if "nonce" not in payload:
        LOGGER.error("No nonce given, this is not allowed")
        raise HTTPException(status_code=403, detail="Not authenticated")
    # TODO: Check if nonce is used
    if payload.get("dummyfield_replace_with_nonce_check", True):
        LOGGER.error("nonce re-use forbidden")
        raise HTTPException(status_code=403, detail="Not authenticated")
    # TODO: Mark the nonce as used
    if not payload.get("anon_admin_session", False):
        LOGGER.error("This token cannot be exchanged for anonymous admin session")
        raise HTTPException(status_code=403, detail="Not authenticated")

    # Copy the claims to the session token
    new_jwt = Issuer.singleton().issue(
        {key: val for key, val in payload.items() if key not in TOKEN_COPY_EXCLUDE_FIELDS}
    )
    return JWTExchangeRequestResponse(jwt=new_jwt)


@router.get("/refresh", tags=["tokens"], response_model=JWTExchangeRequestResponse)
async def refresh_token(jwt: JWTPayload = Depends(JWTBearer(auto_error=True))) -> JWTExchangeRequestResponse:
    """Refresh your JWT"""
    # Copy all claims to fresh token
    new_jwt = Issuer.singleton().issue({key: val for key, val in jwt.items() if key not in TOKEN_COPY_EXCLUDE_FIELDS})
    return JWTExchangeRequestResponse(jwt=new_jwt)
