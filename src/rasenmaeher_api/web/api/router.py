"""router.py: API router."""

from fastapi.routing import APIRouter

from rasenmaeher_api.web.api import (
    healthcheck,
    product,
    checkauth,
    enduserpfx,
    utils,
    enrollment,
    firstuser,
    tokens,
    instructions,
    people,
    descriptions,
)


api_router = APIRouter()
api_router.include_router(healthcheck.router, prefix="/healthcheck", tags=["healthcheck"])
api_router.include_router(product.router, prefix="/product", tags=["product"])
api_router.include_router(checkauth.router, prefix="/check-auth", tags=["info"])
api_router.include_router(enduserpfx.router, prefix="/enduserpfx", tags=["enduserpfx"])
api_router.include_router(utils.router, prefix="/utils", tags=["utils"])
api_router.include_router(enrollment.ENROLLMENT_ROUTER, prefix="/enrollment", tags=["enrollment"])
api_router.include_router(enrollment.NO_JWT_ENROLLMENT_ROUTER, prefix="/enrollment", tags=["now_jwt_enrollment"])
api_router.include_router(firstuser.router, prefix="/firstuser", tags=["firstuser"])
api_router.include_router(tokens.router, prefix="/token", tags=["tokens"])
api_router.include_router(instructions.router, prefix="/instructions", tags=["instructions"])
api_router.include_router(people.router, prefix="/people", tags=["people"])
api_router.include_router(descriptions.router, prefix="/descriptions", tags=["descriptions"])

api_router_v2 = APIRouter()
api_router_v2.include_router(instructions.router_v2, prefix="/instructions", tags=["instructions"])
