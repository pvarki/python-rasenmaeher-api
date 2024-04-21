""" router.py: API router. """
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
    people_v2,
    invitecode,
    enrollment_v2,
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

# V2
api_router2 = APIRouter()
api_router2.include_router(healthcheck.router, prefix="/healthcheck", tags=["healthcheck"])
api_router2.include_router(product.router, prefix="/product", tags=["product"])
api_router2.include_router(checkauth.router, prefix="/check-auth", tags=["info"])
api_router2.include_router(enduserpfx.router, prefix="/enduserpfx", tags=["enduserpfx"])
api_router2.include_router(utils.router, prefix="/utils", tags=["utils"])
api_router2.include_router(firstuser.router, prefix="/firstuser", tags=["firstuser"])
api_router2.include_router(tokens.router, prefix="/token", tags=["tokens"])
api_router2.include_router(instructions.router, prefix="/instructions", tags=["instructions"])


api_router2.include_router(people_v2.router, prefix="/people", tags=["people"])
api_router2.include_router(invitecode.NO_JWT_ENROLLMENT_ROUTER, prefix="/invite-code", tags=["invite-code"])
api_router2.include_router(invitecode.ENROLLMENT_ROUTER, prefix="/invite-code", tags=["invite-code"])
api_router2.include_router(enrollment_v2.NO_JWT_ENROLLMENT_ROUTER, prefix="/enrollment", tags=["now_jwt_enrollment"])
api_router2.include_router(enrollment_v2.ENROLLMENT_ROUTER, prefix="/enrollment", tags=["enrollment"])
