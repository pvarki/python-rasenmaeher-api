"""Internal (in-cluster only) API surface.

Endpoints under here are not intended to be exposed via Traefik — they are
reachable only on the in-cluster Service. They power infrastructure-side
features such as the callsign-validity websocket consumed by the Traefik
plugin.
"""

from fastapi import APIRouter

from . import callsign_validity


router = APIRouter()
router.include_router(callsign_validity.router, prefix="/callsign-validity", tags=["internal"])
