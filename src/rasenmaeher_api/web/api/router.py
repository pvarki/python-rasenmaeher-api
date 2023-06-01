""" router.py: API router. """
from fastapi.routing import APIRouter
from rasenmaeher_api.web.api import healthcheck, takreg, crlproxy, checkauth, enrollment, tokens, roles, users


api_router = APIRouter()
api_router.include_router(healthcheck.router, prefix="/healthcheck", tags=["healthcheck"])
api_router.include_router(takreg.router, prefix="/takreg", tags=["cfssl"])
api_router.include_router(crlproxy.router, prefix="/crlproxy", tags=["cfssl"])
api_router.include_router(checkauth.router, prefix="/check-auth", tags=["info"])
api_router.include_router(enrollment.router, prefix="/enrollment", tags=["enrollment"])
api_router.include_router(tokens.router, prefix="/tokens", tags=["tokens", "legacy"])
api_router.include_router(roles.router, prefix="/roles", tags=["roles", "legacy"])
api_router.include_router(users.router, prefix="/users", tags=["users", "legacy"])
