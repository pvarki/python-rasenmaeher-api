""" router.py: API router. """
from fastapi.routing import APIRouter
from rasenmaeher_api.web.api import takreg, crlproxy, checkauth, enrollment, tokens, roles, users


api_router = APIRouter()
api_router.include_router(tokens.router, prefix="/healthcheck", tags=["healthcheck"])
api_router.include_router(takreg.router, prefix="/takreg", tags=["takreg"])
api_router.include_router(crlproxy.router, prefix="/crlproxy", tags=["crlproxy"])
api_router.include_router(checkauth.router, prefix="/check-auth", tags=["info"])
api_router.include_router(enrollment.router, prefix="/enrollment", tags=["enrollment"])
api_router.include_router(tokens.router, prefix="/tokens", tags=["tokens"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
