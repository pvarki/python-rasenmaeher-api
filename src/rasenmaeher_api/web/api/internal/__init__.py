"""Internal (in-cluster only) API surface, not exposed through Traefik's routers."""

from fastapi import APIRouter

from . import callsign_validity

router = APIRouter()
router.include_router(callsign_validity.router, prefix="/callsign-validity", tags=["internal"])
