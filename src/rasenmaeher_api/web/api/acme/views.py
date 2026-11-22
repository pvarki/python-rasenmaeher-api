"""The public ACME endpoints used by the Apple configuration profile."""

import re
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response
from fastapi.responses import JSONResponse

from ....cert.acme import ACMEError, decode_b64url
from ....db import acme
from ....db.enrollments import ACME_AUTHORIZATION_LIFETIME, Enrollment
from ....db.errors import NotFound
from ....db.people import Person
from .protocol import ACMERoute, SignedRequest, acme_url, new_account_request, signed_request

router = APIRouter(route_class=ACMERoute)
Registration = Annotated[SignedRequest, Depends(new_account_request)]
Authenticated = Annotated[SignedRequest, Depends(signed_request)]


def _account_response(account: str, status: int = 200) -> JSONResponse:
    url = acme_url(f"account/{account}")
    return JSONResponse({"status": "valid", "orders": f"{url}/orders"}, status_code=status, headers={"Location": url})


def _identifier(enrollment: Enrollment) -> dict[str, str | None]:
    return {"type": "permanent-identifier", "value": enrollment.acme_client_identifier}


def _challenge(enrollment: Enrollment) -> dict[str, Any]:
    data = acme.order_data(enrollment)
    result = {
        "type": "device-attest-01",
        "status": "pending",
        "url": acme_url(f"challenge/{enrollment.pk}"),
        "token": data["token"],
    }
    if "validated" in data:
        result.update(status="valid", validated=data["validated"])
    return result


def _order_response(enrollment: Enrollment, status: int = 200) -> JSONResponse:
    order_id = enrollment.pk
    result: dict[str, Any] = {
        "status": "ready" if "validated" in acme.order_data(enrollment) else "pending",
        "identifiers": [_identifier(enrollment)],
        "authorizations": [acme_url(f"authorization/{order_id}")],
        "finalize": acme_url(f"order/{order_id}/finalize"),
    }
    if enrollment.decided_on is not None:
        result["expires"] = (enrollment.decided_on + ACME_AUTHORIZATION_LIFETIME).isoformat()
    if enrollment.person is not None:
        result.update(status="valid", certificate=acme_url(f"certificate/{order_id}"))
    return JSONResponse(result, status_code=status, headers={"Location": acme_url(f"order/{order_id}")})


@router.get("/directory")
async def directory() -> dict[str, str]:
    """Discover the Apple pilot's supported ACME operations."""
    return {"newNonce": acme_url("new-nonce"), "newAccount": acme_url("new-account"), "newOrder": acme_url("new-order")}


@router.head("/new-nonce", status_code=200, response_class=Response)
@router.get("/new-nonce", status_code=204, response_class=Response)
async def new_nonce(response: Response) -> None:
    """Issue the first replay nonce for an ACME request."""
    response.headers["Replay-Nonce"] = acme.issue_nonce()


@router.post("/new-account")
async def new_account(message: Registration) -> JSONResponse:
    """Register the client's ACME public key or return its existing account."""
    payload = message.json()
    if payload.get("onlyReturnExisting") is True:
        if not acme.account_exists(message.account):
            raise ACMEError("accountDoesNotExist", "Unknown ACME account")
        return _account_response(message.account)
    return _account_response(message.account, 201 if acme.register_account(message.account) else 200)


@router.post("/account/{account}")
async def fetch_account(account: str, message: Authenticated) -> JSONResponse:
    """Retrieve the authenticated account."""
    message.require_post_as_get()
    if account != message.account:
        raise ACMEError("unauthorized", "Account is unavailable to this key", 403)
    return _account_response(account)


@router.post("/account/{account}/orders")
async def account_orders(account: str, message: Authenticated) -> dict[str, list[str]]:
    """List the authenticated account's orders."""
    message.require_post_as_get()
    if account != message.account:
        raise ACMEError("unauthorized", "Account is unavailable to this key", 403)
    return {"orders": [acme_url(f"order/{order_id}") for order_id in acme.list_orders(account)]}


@router.post("/new-order")
async def new_order(message: Authenticated) -> JSONResponse:
    """Bind the profile's permanent identifier to an approved enrollment and account."""
    payload = message.json()
    identifiers = payload.get("identifiers")
    if not isinstance(identifiers, list) or len(identifiers) != 1 or not isinstance(identifiers[0], dict):
        raise ACMEError("malformed", "Expected one device identifier")
    item = identifiers[0]
    if item.get("type") != "permanent-identifier":
        raise ACMEError("unsupportedIdentifier", "Use a permanent-identifier from the enrollment profile")
    identifier = item.get("value")
    if not isinstance(identifier, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", identifier):
        raise ACMEError("rejectedIdentifier", "Identifier does not belong to an approved enrollment")
    return _order_response(acme.new_order(identifier, message.account), 201)


@router.post("/order/{order_id}")
async def fetch_order(order_id: uuid.UUID, message: Authenticated) -> JSONResponse:
    """Return the current state of an order to its owner."""
    message.require_post_as_get()
    return _order_response(acme.get_order(order_id, message.account))


@router.post("/authorization/{order_id}")
async def authorization(order_id: uuid.UUID, message: Authenticated) -> dict[str, Any]:
    """Return the device-identifier authorization and its challenge."""
    message.require_post_as_get()
    enrollment = acme.get_order(order_id, message.account)
    challenge = _challenge(enrollment)
    result = {"status": challenge["status"], "identifier": _identifier(enrollment), "challenges": [challenge]}
    if enrollment.decided_on is not None:
        result["expires"] = (enrollment.decided_on + ACME_AUTHORIZATION_LIFETIME).isoformat()
    return result


@router.post("/challenge/{order_id}")
async def challenge(order_id: uuid.UUID, message: Authenticated) -> dict[str, Any]:
    """Acknowledge device-attest-01 using this pilot's one-time enrollment authorization."""
    if message.payload is None:
        return _challenge(acme.get_order(order_id, message.account))
    if message.payload:
        raise ACMEError("malformed", "This enrollment expects an empty challenge acknowledgment")
    return _challenge(acme.accept_challenge(order_id, message.account))


@router.post("/order/{order_id}/finalize")
async def finalize(order_id: uuid.UUID, message: Authenticated) -> JSONResponse:
    """Validate the CSR and issue the client certificate through RMAPI's signer."""
    try:
        csr = decode_b64url(message.json()["csr"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ACMEError("badCSR", "Expected a base64url-encoded DER CSR") from exc
    return _order_response(await acme.finalize_order(order_id, message.account, csr))


@router.post("/certificate/{order_id}")
async def certificate(order_id: uuid.UUID, message: Authenticated) -> Response:
    """Return the persisted leaf and issuing chain to the owning account."""
    message.require_post_as_get()
    enrollment = acme.get_order(order_id, message.account)
    if enrollment.person is None:
        raise ACMEError("orderNotReady", "Certificate has not yet issued", 403)
    try:
        person = await Person.by_pk(enrollment.person)
    except NotFound as exc:
        raise ACMEError("unauthorized", "Certificate is unavailable", 403) from exc
    return Response(person.get_cert_pem(), media_type="application/pem-certificate-chain")
