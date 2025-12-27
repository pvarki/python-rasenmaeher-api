"""Views dealing with login tokens issued by/via TILAUSPALVELU."""

import logging

from fastapi import APIRouter, HTTPException, Depends
from multikeyjwt import Verifier, Issuer
from multikeyjwt.middleware import JWTBearer, JWTPayload

from libpvarki.auditlogging import (
    audit_authentication,
    audit_authorization,
    audit_session,
    audit_iam,
    audit_anomaly,
    AUDIT,
)

from .schema import JWTExchangeRequestResponse, LoginCodeCreateRequest, LoginCodeRequestResponse
from ....db import SeenToken, LoginCode

router = APIRouter()
LOGGER = logging.getLogger(__name__)
TOKEN_COPY_EXCLUDE_FIELDS = ("iat", "exp", "iss", "aud", "nonce")


@router.post("/jwt/exchange", tags=["tokens"], response_model=JWTExchangeRequestResponse)
async def exchange_token(req: JWTExchangeRequestResponse) -> JWTExchangeRequestResponse:
    """API method for converting TILAUSPALVELU issues single-use JWT to RASENMAEHER session JWT"""
    LOGGER.debug("Called")
    payload = Verifier.singleton().decode(req.jwt)
    if not payload:
        LOGGER.log(
            AUDIT,
            "JWT exchange failed - no valid token",
            extra=audit_authentication(
                action="jwt_exchange",
                outcome="failure",
                error_code="INVALID_TOKEN",
                error_message="No acceptable token found in request",
            ),
        )
        LOGGER.info("No acceptable token found")
        raise HTTPException(status_code=403, detail="Not authenticated")

    token_subject = payload.get("sub", "unknown")

    if "nonce" not in payload:
        LOGGER.log(
            AUDIT,
            "JWT exchange failed - missing nonce: %s",
            token_subject,
            extra=audit_anomaly(
                action="jwt_exchange_no_nonce",
                error_code="MISSING_NONCE",
                error_message="JWT missing required nonce field - possible crafted token",
                target_user=token_subject,
            ),
        )
        LOGGER.error("No nonce given, this is not allowed")
        raise HTTPException(status_code=403, detail="Not authenticated")

    # This will throw 403 compatible exception for reuse
    try:
        await SeenToken.use_token(payload["nonce"])
    except HTTPException:
        LOGGER.log(
            AUDIT,
            "JWT exchange failed - token replay attempt: %s",
            token_subject,
            extra=audit_anomaly(
                action="jwt_exchange_replay",
                error_code="TOKEN_REUSED",
                error_message="Attempt to reuse single-use JWT - replay attack detected",
                target_user=token_subject,
            ),
        )
        raise

    # We don't strictly *need* to check this but it makes unusable claim sets much more obvious earlier
    if not payload.get("anon_admin_session", False):
        LOGGER.log(
            AUDIT,
            "JWT exchange failed - wrong token type: %s",
            token_subject,
            extra=audit_authorization(
                action="jwt_exchange",
                outcome="failure",
                target_user=token_subject,
                error_code="WRONG_TOKEN_TYPE",
                error_message="Token lacks anon_admin_session claim",
            ),
        )
        LOGGER.error("This token cannot be exchanged for anonymous admin session")
        raise HTTPException(status_code=403, detail="Not authenticated")

    # Copy the claims to the session token
    new_jwt = Issuer.singleton().issue(
        {key: val for key, val in payload.items() if key not in TOKEN_COPY_EXCLUDE_FIELDS}
    )

    LOGGER.log(
        AUDIT,
        "JWT exchange successful: %s",
        token_subject,
        extra=audit_authentication(
            action="jwt_exchange",
            outcome="success",
            target_user=token_subject,
        ),
    )

    resp = JWTExchangeRequestResponse(jwt=new_jwt)
    LOGGER.debug("returning {}".format(resp))
    return resp


@router.get("/jwt/refresh", tags=["tokens"], response_model=JWTExchangeRequestResponse)
async def refresh_token(jwt: JWTPayload = Depends(JWTBearer(auto_error=True))) -> JWTExchangeRequestResponse:
    """Refresh your JWT"""
    # Copy all claims to fresh token
    LOGGER.debug("Called")

    token_subject = jwt.get("sub", "unknown")

    new_jwt = Issuer.singleton().issue({key: val for key, val in jwt.items() if key not in TOKEN_COPY_EXCLUDE_FIELDS})

    LOGGER.log(
        AUDIT,
        "JWT refreshed: %s",
        token_subject,
        extra=audit_session(
            action="jwt_refresh",
            outcome="success",
            target_user=token_subject,
        ),
    )

    resp = JWTExchangeRequestResponse(jwt=new_jwt)
    LOGGER.debug("returning {}".format(resp))
    return resp


@router.post("/code/generate", tags=["tokens"], response_model=LoginCodeRequestResponse)
async def create_code(
    req: LoginCodeCreateRequest, jwt: JWTPayload = Depends(JWTBearer(auto_error=True))
) -> LoginCodeRequestResponse:
    """Generate an alphanumeric code that can be exchanged for JWT with the given claims"""
    LOGGER.debug("Called")

    initiator = jwt.get("sub", "unknown")

    if not jwt.get("anon_admin_session", False):
        LOGGER.log(
            AUDIT,
            "Login code generation blocked - unauthorized: %s",
            initiator,
            extra=audit_authorization(
                action="logincode_generate",
                outcome="failure",
                error_code="MISSING_CLAIM",
                error_message="JWT missing anon_admin_session claim",
            ),
        )
        LOGGER.error("Requesting JWT must have admin session claim")
        raise HTTPException(status_code=403, detail="Forbidden")

    code = await LoginCode.create_for_claims(req.claims)

    target_user = req.claims.get("sub", "unspecified")

    LOGGER.log(
        AUDIT,
        "Login code generated for: %s",
        target_user,
        extra=audit_iam(
            action="logincode_generate",
            outcome="success",
            target_user=target_user,
            target_resource=code,
            target_resource_type="logincode",
        ),
    )

    resp = LoginCodeRequestResponse(code=code)
    LOGGER.debug("returning {}".format(resp))
    return resp


@router.post("/code/exchange", tags=["tokens"], response_model=JWTExchangeRequestResponse)
async def exchange_code(req: LoginCodeRequestResponse) -> JWTExchangeRequestResponse:
    """Exchange code for JWT"""
    LOGGER.debug("Called")
    if not req.code:
        LOGGER.log(
            AUDIT,
            "Code exchange failed - no code provided",
            extra=audit_authentication(
                action="logincode_exchange",
                outcome="failure",
                error_code="NO_CODE",
                error_message="No login code provided in request",
            ),
        )
        LOGGER.info("No code given")
        raise HTTPException(status_code=403, detail="Not authenticated")

    try:
        new_jwt = await LoginCode.use_code(req.code)
    except HTTPException:
        LOGGER.log(
            AUDIT,
            "Code exchange failed - invalid or used code",
            extra=audit_authentication(
                action="logincode_exchange",
                outcome="failure",
                error_code="INVALID_CODE",
                error_message="Login code not found or already used",
            ),
        )
        raise

    LOGGER.log(
        AUDIT,
        "Code exchange successful",
        extra=audit_authentication(
            action="logincode_exchange",
            outcome="success",
        ),
    )

    resp = JWTExchangeRequestResponse(jwt=new_jwt)
    LOGGER.debug("returning {}".format(resp))
    return resp
