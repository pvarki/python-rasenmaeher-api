""" router.py: API router. """
from fastapi.routing import APIRouter
from rasenmaeher_api.web.api import takreg, crlproxy, tokens, roles, users


api_router = APIRouter()
api_router.include_router(takreg.router, prefix="/takreg", tags=["takreg"])
api_router.include_router(crlproxy.router, prefix="/crlproxy", tags=["crlproxy"])
api_router.include_router(tokens.router, prefix="/tokens", tags=["tokens"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
