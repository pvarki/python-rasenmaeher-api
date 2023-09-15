"""Views dealing with login tokens issues by/via TILAUSPALVELU"""
from typing import Dict, Any
import logging
import secrets
import string
import json

from fastapi import APIRouter, HTTPException, Depends
from multikeyjwt import Verifier, Issuer
from multikeyjwt.middleware import JWTBearer, JWTPayload


from .schema import JWTExchangeRequestResponse, LoginCodeCreateRequest, LoginCodeRequestResponse

from ....settings import settings
from ....sqlitedatabase import sqlite

router = APIRouter()
LOGGER = logging.getLogger(__name__)
TOKEN_COPY_EXCLUDE_FIELDS = ("iat", "exp", "iss", "aud", "nonce")
CODE_CHAR_COUNT = 12  # TODO: Make configurable ??
CODE_ALPHABET = string.ascii_uppercase + string.digits


@router.post("/jwt/exchange", tags=["tokens"], response_model=JWTExchangeRequestResponse)
async def exchange_token(req: JWTExchangeRequestResponse) -> JWTExchangeRequestResponse:
    """API method for converting TILAUSPALVELU issues single-use JWT to RASENMAEHER session JWT"""
    LOGGER.debug("Called")
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
    resp = JWTExchangeRequestResponse(jwt=new_jwt)
    LOGGER.debug("returning {}".format(resp))
    return resp


@router.get("/jwt/refresh", tags=["tokens"], response_model=JWTExchangeRequestResponse)
async def refresh_token(jwt: JWTPayload = Depends(JWTBearer(auto_error=True))) -> JWTExchangeRequestResponse:
    """Refresh your JWT"""
    # Copy all claims to fresh token
    LOGGER.debug("Called")
    new_jwt = Issuer.singleton().issue({key: val for key, val in jwt.items() if key not in TOKEN_COPY_EXCLUDE_FIELDS})
    resp = JWTExchangeRequestResponse(jwt=new_jwt)
    LOGGER.debug("returning {}".format(resp))
    return resp


async def create_code_backend(claims: Dict[str, Any]) -> str:
    """Created the code to backend, used by console and REST endpoint"""
    code = "".join(secrets.choice(CODE_ALPHABET) for i in range(CODE_CHAR_COUNT))

    # TODO: Save the code and req.claims in database
    _q = settings.sqlite_jwt_sel_from_jwt_where_exchange.format(exchange_code=code)
    _success, _result = sqlite.run_command(_q)
    if _success is False:
        _reason = "Undefined backend error q_ssjsfjwe2"
        LOGGER.error("{}".format(_reason))
        raise HTTPException(status_code=500, detail=_reason)
    if len(_result) > 0:
        # Because of cosmic rays, same code has already been added. Adding a new one.
        code = "".join(secrets.choice(CODE_ALPHABET) for i in range(CODE_CHAR_COUNT))

    _q = settings.sqlite_insert_into_jwt.format(
        claims=json.dumps(claims), consumed="no", work_id_hash="NA", work_id="NA", exchange_code=code
    )
    _success, _result = sqlite.run_command(_q)
    if _success is False:
        _reason = "Undefined backend error q_ssiij1"
        LOGGER.error("{}".format(_reason))
        raise HTTPException(status_code=500, detail=_reason)

    return code


@router.post("/code/generate", tags=["tokens"], response_model=LoginCodeRequestResponse)
async def create_code(
    req: LoginCodeCreateRequest, jwt: JWTPayload = Depends(JWTBearer(auto_error=True))
) -> LoginCodeRequestResponse:
    """Generate an alphanumeric code that can be exchanged for JWT with the given claims"""
    LOGGER.debug("Called")
    if not jwt.get("anon_admin_session", False):
        LOGGER.error("Requesting JWT must have admin session claim")
        raise HTTPException(status_code=403, detail="Forbidden")
    code = await create_code_backend(req.claims)
    resp = LoginCodeRequestResponse(code=code)
    LOGGER.debug("returning {}".format(resp))
    return resp


@router.post("/code/exchange", tags=["tokens"], response_model=JWTExchangeRequestResponse)
async def exchange_code(req: LoginCodeRequestResponse) -> JWTExchangeRequestResponse:
    """Exchange code for JWT"""
    LOGGER.debug("Called")
    if not req.code:
        LOGGER.info("No code given")
        raise HTTPException(status_code=403, detail="Not authenticated")

    # TODO: Check if code exists and is not used
    _q = settings.sqlite_jwt_sel_from_jwt_where_exchange.format(exchange_code=req.code)
    _success, _result = sqlite.run_command(_q)

    if _success is False:
        _reason = "Undefined backend error q_ssjsfjwe1"
        LOGGER.error("{}".format(_reason))
        raise HTTPException(status_code=500, detail=_reason)

    if len(_result) == 0:
        LOGGER.error("code does not exist")
        raise HTTPException(status_code=404, detail="Unusable code")

    if _result[0][2].lower() != "no":
        LOGGER.error("code re-use forbidden")
        raise HTTPException(status_code=403, detail="code re-use forbidden")

    # Read the claims related to the code from DB
    print(_result[0][1])
    claims = json.loads(_result[0][1])

    # Mark the code as used
    _q = settings.sqlite_jwt_update_consumed_where_exchange.format(new_consumed_state="yes", exchange_code=req.code)

    _success, _result = sqlite.run_command(_q)
    if _success is False:
        _reason = "Undefined backend error q_sjucwe1"
        LOGGER.error("{}".format(_reason))
        raise HTTPException(status_code=500, detail=_reason)

    new_jwt = Issuer.singleton().issue(claims)
    resp = JWTExchangeRequestResponse(jwt=new_jwt)
    LOGGER.debug("returning {}".format(resp))
    return resp
