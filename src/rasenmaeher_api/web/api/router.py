""" router.py: API router. """
from fastapi.routing import APIRouter
from rasenmaeher_api.web.api import takreg, crlproxy


api_router = APIRouter()
api_router.include_router(takreg.router, prefix="/takreg", tags=["takreg"])
api_router.include_router(crlproxy.router, prefix="/crlproxy", tags=["crlproxy"])
