"""Info API views."""
from typing import cast
from fastapi import APIRouter, Depends
from multikeyjwt.middleware import JWTBearer

router = APIRouter()


@router.get("/", dependencies=[Depends(JWTBearer())])
async def return_info() -> str:
    """
    Method for testing JWT
    """

    return cast(str, "Hello World")
