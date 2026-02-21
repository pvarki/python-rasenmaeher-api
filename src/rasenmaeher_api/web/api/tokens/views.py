"""Views dealing with login tokens issues by/via TILAUSPALVELU"""

import logging

from fastapi import APIRouter, Request, HTTPException, Depends
from multikeyjwt import Verifier, Issuer
from multikeyjwt.middleware import JWTBearer, JWTPayload


from .schema import JWTExchangeRequestResponse, LoginCodeCreateRequest, LoginCodeRequestResponse
from ..utils.auditcontext import build_audit_extra
from ....db import SeenToken, LoginCode

router = APIRouter()
LOGGER = logging.getLogger(__name__)
TOKEN_COPY_EXCLUDE_FIELDS = ("iat", "exp", "iss", "aud", "nonce")


@router.post("/jwt/exchange", tags=["tokens"], response_model=JWTExchangeRequestResponse)
async def exchange_token(request: Request, req: JWTExchangeRequestResponse) -> JWTExchangeRequestResponse:
    """API method for converting TILAUSPALVELU issues single-use JWT to RASENMAEHER session JWT"""
    LOGGER.debug("Called")
    payload = Verifier.singleton().decode(req.jwt)
    if not payload:
        LOGGER.info("No acceptable token found")
        LOGGER.audit(  # type: ignore[attr-defined]
            "JWT exchange failed - invalid token",
            extra=build_audit_extra(
                action="jwt_exchange",
                outcome="failure",
                request=request,
                error_code="INVALID_TOKEN",
            ),
        )
        raise HTTPException(status_code=403, detail="Not authenticated")
    if "nonce" not in payload:
        LOGGER.error("No nonce given, this is not allowed")
        LOGGER.audit(  # type: ignore[attr-defined]
            "JWT exchange failed - missing nonce",
            extra=build_audit_extra(
                action="jwt_exchange",
                outcome="failure",
                request=request,
                error_code="MISSING_NONCE",
            ),
        )
        raise HTTPException(status_code=403, detail="Not authenticated")

    # This will throw 403 compatible exception for reuse
    try:
        await SeenToken.use_token(payload["nonce"])
    except HTTPException:
        LOGGER.audit(  # type: ignore[attr-defined]
            "JWT exchange failed - nonce reuse (possible replay attack)",
            extra=build_audit_extra(
                action="jwt_exchange",
                outcome="failure",
                request=request,
                error_code="NONCE_REUSE",
            ),
        )
        raise

    # We don't strictly *need* to check this but it makes unusable claim sets much more obvious earlier
    if not payload.get("anon_admin_session", False):
        LOGGER.error("This token cannot be exchanged for anonymous admin session")
        LOGGER.audit(  # type: ignore[attr-defined]
            "JWT exchange failed - not anon_admin_session token",
            extra=build_audit_extra(
                action="jwt_exchange",
                outcome="failure",
                request=request,
                error_code="NOT_ANON_ADMIN_SESSION",
            ),
        )
        raise HTTPException(status_code=403, detail="Not authenticated")

    # Copy the claims to the session token
    new_jwt = Issuer.singleton().issue(
        {key: val for key, val in payload.items() if key not in TOKEN_COPY_EXCLUDE_FIELDS}
    )

    LOGGER.audit(  # type: ignore[attr-defined]
        "JWT exchange successful - anon_admin session created",
        extra=build_audit_extra(
            action="jwt_exchange",
            outcome="success",
            request=request,
        ),
    )

    resp = JWTExchangeRequestResponse(jwt=new_jwt)
    LOGGER.debug("returning {}".format(resp))
    return resp


@router.get("/jwt/refresh", tags=["tokens"], response_model=JWTExchangeRequestResponse)
async def refresh_token(jwt: JWTPayload = Depends(JWTBearer(auto_error=True))) -> JWTExchangeRequestResponse:
    """Refresh your JWT"""
    # Copy all claims to fresh token
    # Note: Not audited - normal session maintenance, would be too noisy
    LOGGER.debug("Called")
    new_jwt = Issuer.singleton().issue({key: val for key, val in jwt.items() if key not in TOKEN_COPY_EXCLUDE_FIELDS})
    resp = JWTExchangeRequestResponse(jwt=new_jwt)
    LOGGER.debug("returning {}".format(resp))
    return resp


@router.post("/code/generate", tags=["tokens"], response_model=LoginCodeRequestResponse)
async def create_code(
    request: Request,
    req: LoginCodeCreateRequest,
    jwt: JWTPayload = Depends(JWTBearer(auto_error=True)),
) -> LoginCodeRequestResponse:
    """Generate an alphanumeric code that can be exchanged for JWT with the given claims"""
    LOGGER.debug("Called")

    # Actor from JWT subject (may be None for anon sessions)
    actor = jwt.get("sub")

    if not jwt.get("anon_admin_session", False):
        LOGGER.error("Requesting JWT must have admin session claim")
        LOGGER.audit(  # type: ignore[attr-defined]
            "Login code generation failed - missing anon_admin_session claim",
            extra=build_audit_extra(
                action="logincode_generate",
                outcome="failure",
                actor=actor,
                request=request,
                error_code="MISSING_ANON_ADMIN_CLAIM",
            ),
        )
        raise HTTPException(status_code=403, detail="Forbidden")

    code = await LoginCode.create_for_claims(req.claims)

    # Extract subject from claims if present for audit trail
    target_subject = req.claims.get("sub") if req.claims else None

    LOGGER.audit(  # type: ignore[attr-defined]
        "Login code generated",
        extra=build_audit_extra(
            action="logincode_generate",
            outcome="success",
            actor=actor,
            target=target_subject,
            request=request,
        ),
    )

    resp = LoginCodeRequestResponse(code=code)
    LOGGER.debug("returning {}".format(resp))
    return resp


@router.post("/code/exchange", tags=["tokens"], response_model=JWTExchangeRequestResponse)
async def exchange_code(request: Request, req: LoginCodeRequestResponse) -> JWTExchangeRequestResponse:
    """Exchange code for JWT"""
    LOGGER.debug("Called")
    if not req.code:
        LOGGER.info("No code given")
        LOGGER.audit(  # type: ignore[attr-defined]
            "Login code exchange failed - no code provided",
            extra=build_audit_extra(
                action="logincode_exchange",
                outcome="failure",
                request=request,
                error_code="NO_CODE_PROVIDED",
            ),
        )
        raise HTTPException(status_code=403, detail="Not authenticated")

    try:
        new_jwt = await LoginCode.use_code(req.code)
    except HTTPException:
        # LoginCode.use_code raises HTTPException for invalid/used codes
        LOGGER.audit(  # type: ignore[attr-defined]
            "Login code exchange failed - invalid or expired code",
            extra=build_audit_extra(
                action="logincode_exchange",
                outcome="failure",
                request=request,
                error_code="INVALID_CODE",
            ),
        )
        raise

    # Decode the new JWT to get subject for audit trail
    payload = Verifier.singleton().decode(new_jwt)
    target_subject = payload.get("sub") if payload else None

    LOGGER.audit(  # type: ignore[attr-defined]
        "Login code exchange successful",
        extra=build_audit_extra(
            action="logincode_exchange",
            outcome="success",
            target=target_subject,
            request=request,
        ),
    )

    resp = JWTExchangeRequestResponse(jwt=new_jwt)
    LOGGER.debug("returning {}".format(resp))
    return resp
