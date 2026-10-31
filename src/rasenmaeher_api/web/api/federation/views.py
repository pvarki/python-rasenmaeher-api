"""Dispatch authorized requests only to the local TAK integration API."""

import asyncio
from collections.abc import Callable
from typing import Any, Literal
from urllib.parse import urlsplit

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from starlette.responses import Response

from rasenmaeher_api.mtlsinit import get_session_winit
from rasenmaeher_api.rmsettings import RMSettings

from ..middleware.federation import audit_federation, authorize_federation, federation_error
from .schema import FederationOutgoingResponse, FederationRequest, FederationTrustResponse


class FederationRoute(APIRoute):
    def get_route_handler(self) -> Callable[[Request], Any]:
        handler = super().get_route_handler()

        async def audited_handler(request: Request) -> Response:
            try:
                return await handler(request)
            except RequestValidationError:
                audit_federation(
                    request,
                    None,
                    error=federation_error(422, "invalid_request", "validate", "Invalid federation request"),
                )
                raise

        return audited_handler


router = APIRouter(route_class=FederationRoute)


async def dispatch[Response: (FederationTrustResponse, FederationOutgoingResponse)](
    peer: FederationRequest, operation: Literal["trust", "outgoing"], schema: type[Response]
) -> Response:
    """Keep federation timeouts and failures visible instead of using the generic proxy."""
    try:
        products = RMSettings.singleton().kraftwerk_manifest_dict.get("products", {})
        if not isinstance(products, dict):
            raise TypeError("Invalid product manifest")
        if "tak" not in products:
            raise federation_error(404, "tak_not_installed", "dispatch", "This deployment has no TAK product")
        base = products["tak"]["api"]
        if not isinstance(base, str):
            raise TypeError("Invalid product API")
        parsed = urlsplit(base)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Invalid product API")
        url = f"{base.rstrip('/')}/api/v1/federation/{operation}"
    except (KeyError, TypeError, ValueError) as exc:
        raise federation_error(503, "tak_unavailable", "dispatch", "Local TAK integration unavailable") from exc
    sent = False
    try:
        async with asyncio.timeout(30):
            async with await get_session_winit() as client:
                sent = True
                async with client.post(
                    url, json=peer.model_dump(), timeout=aiohttp.ClientTimeout(total=30), allow_redirects=False
                ) as response:
                    if response.status != 200:
                        # Only validated diagnostics may cross this boundary; messages are local constants.
                        if response.status in (409, 422, 502, 503, 504):
                            payload = await response.json()
                            detail = payload.get("detail") if isinstance(payload, dict) else None
                            if isinstance(detail, dict) and (
                                isinstance(detail.get("code"), str)
                                and 0 < len(detail["code"]) <= 64
                                and detail["code"].replace("_", "").isalnum()
                                and detail.get("stage")
                                in ("authorize", "dispatch", "fetch_ca", "upload_ca", "groups", "outgoing", "verify")
                                and type(detail.get("may_have_changed")) is bool
                            ):
                                messages = {
                                    409: "TAK federation prerequisites or settings conflict",
                                    422: "TAK rejected federation input",
                                    502: "TAK federation upstream failure",
                                    503: "TAK federation temporarily unavailable",
                                    504: "TAK federation operation timed out",
                                }
                                raise federation_error(
                                    response.status,
                                    detail["code"],
                                    detail["stage"],
                                    messages[response.status],
                                    may_have_changed=detail["may_have_changed"],
                                )
                        raise federation_error(
                            502,
                            "tak_dispatch_failed",
                            "dispatch",
                            "Unexpected TAK integration response",
                            may_have_changed=True,
                        )
                    payload = await response.json()
                    if (
                        not isinstance(payload, dict)
                        or payload.get("success") is not True
                        or (operation == "outgoing" and payload.get("enabled") is not True)
                    ):
                        raise ValueError("Missing successful configuration result")
                    result = schema.model_validate(payload)
                    if result.remote_base != peer.remote_base:
                        raise ValueError("Wrong response peer")
                    if isinstance(result, FederationOutgoingResponse) and result.address != f"tak.{peer.hostname}":
                        raise ValueError("Wrong outgoing destination")
                    return result
    except TimeoutError as exc:
        raise federation_error(
            504, "tak_dispatch_timeout", "dispatch", "TAK integration request timed out", may_have_changed=sent
        ) from exc
    except (aiohttp.ClientError, ValueError) as exc:
        raise federation_error(
            502,
            "invalid_tak_response",
            "verify" if sent else "dispatch",
            "Invalid TAK integration response",
            may_have_changed=sent,
        ) from exc
    except OSError as exc:
        raise federation_error(
            503, "tak_unavailable", "dispatch", "Local TAK integration unavailable", may_have_changed=sent
        ) from exc


async def handle[Response: (FederationTrustResponse, FederationOutgoingResponse)](
    peer: FederationRequest, request: Request, operation: Literal["trust", "outgoing"], schema: type[Response]
) -> Response:
    """Audit the final outcome after authorization has consumed the nonce."""
    try:
        result = await dispatch(peer, operation, schema)
    except HTTPException as exc:
        audit_federation(request, peer, error=exc)
        raise
    audit_federation(request, peer)
    return result


@router.post("/tak/trust")
async def trust(
    peer: FederationRequest, request: Request, claims: dict[str, Any] = Depends(authorize_federation)
) -> FederationTrustResponse:
    """Trust the peer CA locally; the caller must also prepare the other server."""
    return await handle(peer, request, "trust", FederationTrustResponse)


@router.post("/tak/outgoing")
async def outgoing(
    peer: FederationRequest, request: Request, claims: dict[str, Any] = Depends(authorize_federation)
) -> FederationOutgoingResponse:
    """Ensure outgoing only on the server selected by the caller."""
    return await handle(peer, request, "outgoing", FederationOutgoingResponse)
