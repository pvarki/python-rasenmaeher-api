"""Internal (in-cluster only) API surface.

Endpoints here are not exposed through Traefik's public routers. They answer
infrastructure questions such as the per-request mTLS authorization that
Traefik's forwardAuth middleware asks on every request to an mTLS route.
"""

from fastapi import APIRouter

from . import callsign_validity

router = APIRouter()
router.include_router(callsign_validity.router, prefix="/callsign-validity", tags=["internal"])
