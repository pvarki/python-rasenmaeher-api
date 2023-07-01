""" router.py: API router. """
from fastapi.routing import APIRouter

from rasenmaeher_api.web.api import (
    healthcheck,
    product,
    checkauth,
    enduserpfx,
    utils,
    enrollment,
)


api_router = APIRouter()
api_router.include_router(healthcheck.router, prefix="/healthcheck", tags=["healthcheck"])
api_router.include_router(product.router, prefix="/product", tags=["product"])
api_router.include_router(checkauth.router, prefix="/check-auth", tags=["info"])
api_router.include_router(enduserpfx.router, prefix="/enduserpfx", tags=["enduserpfx"])
api_router.include_router(utils.router, prefix="/utils", tags=["utils"])
api_router.include_router(enrollment.router, prefix="/enrollment", tags=["enrollment"])
