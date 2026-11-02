"""Header-only JWT authorization scoped to one deployment, peer and operation."""

import logging
from typing import Any, cast
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from multikeyjwt import Verifier
from sqlalchemy.exc import SQLAlchemyError

from rasenmaeher_api.db.errors import DBError, TokenReuse
from rasenmaeher_api.db.nonces import SeenToken
from rasenmaeher_api.rmsettings import RMSettings

from ..federation.schema import FederationRequest, normalize_peer
from ..utils.auditcontext import build_audit_extra

LOGGER = logging.getLogger(__name__)
FEDERATION_BEARER = HTTPBearer(auto_error=False)


def federation_error(
    status: int, code: str, stage: str, message: str, *, may_have_changed: bool = False
) -> HTTPException:
    """Fixed, public messages never expose JWTs or downstream response bodies."""
    return HTTPException(
        status_code=status,
        detail={"code": code, "stage": stage, "message": message, "may_have_changed": may_have_changed},
    )


def audit_federation(request: Request, peer: FederationRequest | None, *, error: HTTPException | None = None) -> None:
    """Attribute only cryptographically verified claims, never the encoded token."""
    claims = getattr(request.state, "jwt", None) or {}
    fields = {name: value[:256] for name in ("iss", "sub", "nonce") if isinstance(value := claims.get(name), str)}
    detail = cast(dict[str, Any], error.detail) if error else {}
    LOGGER.audit(  # type: ignore[attr-defined]
        "TAK federation request",
        extra=build_audit_extra(
            action=f"tak_federation_{request.url.path.rsplit('/', 1)[-1]}",
            outcome="failure" if error else "success",
            actor=fields.get("sub", "unknown"),
            target=peer.remote_base if peer else None,
            request=request,
            issuer=fields.get("iss"),
            nonce=fields.get("nonce"),
            stage=detail.get("stage", "verify"),
            error_code=detail.get("code"),
        ),
    )


def local_deployment_dns() -> str:
    """Deployment identity comes from the manifest, not an attacker-supplied Host."""
    try:
        settings = RMSettings.singleton()
        settings.load_manifest()
        dns = settings.kraftwerk_manifest_dict["dns"]
        if not isinstance(dns, str):
            raise TypeError("Invalid DNS")
        dns = normalize_peer(dns)
        if ":" in dns:
            raise ValueError("Expected DNS without a port")
        return dns
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise federation_error(
            503, "local_identity_unavailable", "authorize", "Local deployment identity unavailable"
        ) from exc


async def authorize_federation(
    peer: FederationRequest,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(FEDERATION_BEARER),
) -> dict[str, Any]:
    """Validate every authorization claim, then atomically consume the canonical nonce."""
    request.state.jwt = None
    try:
        if credentials is None or len(request.headers.getlist("authorization")) != 1:
            raise federation_error(403, "invalid_federation_token", "authorize", "A valid bearer header is required")
        local_dns = local_deployment_dns()
        if peer.hostname == local_dns:
            raise federation_error(422, "self_federation", "authorize", "Cannot federate with the local deployment")
        expected_audience = f"rasenmaeher:tak-federation:{local_dns}"
        try:
            verifier = Verifier.singleton()
            if not verifier.pubkeys:
                raise ValueError("No trusted keys")
        except (OSError, ValueError) as exc:
            raise federation_error(
                503, "trusted_keys_unavailable", "authorize", "Trusted signing keys unavailable"
            ) from exc
        try:
            claims = verifier.decode(credentials.credentials, audience=expected_audience)
        except (InvalidTokenError, ValueError, TypeError, OverflowError) as exc:
            raise federation_error(
                403, "invalid_federation_token", "authorize", "Invalid or expired federation token"
            ) from exc
        request.state.jwt = claims
        try:
            if any(not isinstance(claims.get(name), str) or not claims[name].strip() for name in ("iss", "sub")):
                raise ValueError("Missing attribution")
            if type(claims.get("aud")) is not str or claims["aud"] != expected_audience:
                raise ValueError("Expected one exact audience")
            if any(type(claims.get(name)) is not int for name in ("iat", "nbf", "exp")):
                raise ValueError("Expected integer timestamps")
            if not claims["iat"] <= claims["nbf"] < claims["exp"] or claims["exp"] - claims["iat"] > 300:
                raise ValueError("Invalid token lifetime")
            if claims.get("federation_action") != request.url.path.rsplit("/", 1)[-1]:
                raise ValueError("Wrong operation")
            if (
                not isinstance(claims.get("remote_base"), str)
                or normalize_peer(claims["remote_base"]) != peer.remote_base
            ):
                raise ValueError("Wrong peer")
            if not isinstance(claims.get("nonce"), str):
                raise TypeError("Missing nonce")
            nonce = str(UUID(claims["nonce"]))
        except (ValueError, TypeError) as exc:
            raise federation_error(
                403, "invalid_federation_claims", "authorize", "Invalid federation authorization claims"
            ) from exc
        try:
            await SeenToken.use_token(
                nonce,
                {
                    "iss": claims["iss"],
                    "sub": claims["sub"],
                    "action": claims["federation_action"],
                    "remote_base": peer.remote_base,
                },
            )
        except TokenReuse as exc:
            raise federation_error(
                403, "federation_token_reused", "authorize", "Federation nonce has already been used"
            ) from exc
        except (SQLAlchemyError, DBError) as exc:
            raise federation_error(
                503, "replay_state_unavailable", "authorize", "Federation replay state unavailable"
            ) from exc
        return claims
    except HTTPException as exc:
        audit_federation(request, peer, error=exc)
        raise
