"""Healthcheck API views."""
from typing import Any, Dict
from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def request_healthcheck() -> Dict[Any, Any]:
    """
    TODO check if healthcheck needs something more to do..
    """
    return {"healthcheck": "success"}
