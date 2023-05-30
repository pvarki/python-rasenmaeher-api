""" router.py: API router. """
from fastapi.routing import APIRouter
from rasenmaeher_api.web.api import takreg, crlproxy, info


api_router = APIRouter()
api_router.include_router(takreg.router, prefix="/takreg", tags=["takreg"])
api_router.include_router(crlproxy.router, prefix="/crlproxy", tags=["crlproxy"])
api_router.include_router(info.router, prefix="/info", tags=["info"])
