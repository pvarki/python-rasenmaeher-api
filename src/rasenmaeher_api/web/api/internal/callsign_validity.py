"""HTTP endpoint that answers callsign validity queries.

Consumed by the Traefik ``callsign-validity`` plugin for per-request mTLS
authorization checks. A callsign is valid if EITHER:

* a ``Person`` exists with the given callsign and ``deleted IS NULL``, OR
* the callsign matches a product service CN listed in the kraftwerk manifest
  (``RMSettings.valid_product_cns``) — e.g. ``rasenmaeher`` / ``tak`` for
  inter-service mTLS calls. Matches the same trust model as the existing
  ``ValidUser`` dependency in ``middleware/user.py``.

Wire protocol:

    POST /api/v1/internal/callsign-validity/check
    {"callsign": "<name>"}
    -> 200 {"valid": <bool>}
    -> 400 if body is malformed

Auth: if ``RM_CALLSIGN_VALIDITY_SECRET`` is set, the client must send a
matching ``Validity-Secret`` header. Otherwise the endpoint is open
(suitable for in-cluster-only Service exposure).

Note: this used to be a websocket endpoint, but Traefik's Yaegi interpreter
cannot load ``golang.org/x/net/websocket``, so the plugin was switched to
stdlib ``net/http``. The per-request semantics are identical.
"""

from typing import Optional
import logging

from fastapi import APIRouter, Header, HTTPException, status
from pydantic import BaseModel

from ....db.errors import NotFound, Deleted
from ....db.people import Person
from ....rmsettings import RMSettings


LOGGER = logging.getLogger(__name__)
router = APIRouter()


class CheckRequest(BaseModel):
    callsign: str


class CheckResponse(BaseModel):
    valid: bool


def _check_secret(provided: Optional[str]) -> None:
    expected = RMSettings.singleton().callsign_validity_secret
    if not expected:
        return
    if provided != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid validity secret")


async def _is_valid(callsign: str) -> bool:
    settings = RMSettings.singleton()
    # Service identities from the kraftwerk manifest (product backends like TAK,
    # battlelog) and the rmapi self-CN are trusted by virtue of the CA chain;
    # they don't appear in the Person table.
    if callsign == settings.mtls_client_cert_cn:
        return True
    try:
        if callsign in settings.valid_product_cns:
            return True
    except Exception:  # pylint: disable=broad-except
        LOGGER.debug("valid_product_cns lookup failed", exc_info=True)
    try:
        await Person.by_callsign(callsign)
        return True
    except (NotFound, Deleted):
        return False


@router.post("/check", response_model=CheckResponse)
async def callsign_validity_check(
    req: CheckRequest,
    validity_secret: Optional[str] = Header(default=None, alias="Validity-Secret"),
) -> CheckResponse:
    """Return whether the given callsign is currently valid."""
    _check_secret(validity_secret)
    callsign = req.callsign.strip()
    if not callsign:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="callsign must be non-empty")
    return CheckResponse(valid=await _is_valid(callsign))
