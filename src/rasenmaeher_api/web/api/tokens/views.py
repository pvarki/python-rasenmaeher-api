"""Tokoens API views."""
from fastapi import APIRouter

from rasenmaeher_api.web.api.tokens.schema import Placeholder

router = APIRouter()


@router.get("/pubkey")
async def request_tokens_pubkey(
    response: Placeholder,
) -> Placeholder:
    """
    TODO pubkey GET
    """
    Placeholder.placeholder2 = "22349187239"
    return response


@router.get("/")
async def request_tokens(
    response: Placeholder,
) -> Placeholder:
    """
    TODO tokens GET
    """
    Placeholder.placeholder2 = "2l92183982173981"
    return response


@router.post("/")
async def post_tokens(
    response: Placeholder,
) -> Placeholder:
    """
    TODO tokens POST
    """
    Placeholder.placeholder2 = "2120938102938"
    return response


@router.get("/refresh")
async def request_tokens_refresh(
    response: Placeholder,
) -> Placeholder:
    """
    TODO pubkey GET
    """
    Placeholder.placeholder2 = "212398120398"
    return response


@router.get("/use")
async def request_tokens_use(
    response: Placeholder,
) -> Placeholder:
    """
    TODO use GET
    """
    Placeholder.placeholder2 = "2098098098"
    return response


@router.post("/consume")
async def post_tokens_consume(
    response: Placeholder,
) -> Placeholder:
    """
    TODO consume POST
    """
    Placeholder.placeholder2 = "2123123123"
    return response


@router.get("/{pkstr}}")
async def request_tokens_pksrt(
    response: Placeholder,
) -> Placeholder:
    """
    TODO {pksrt} GET
    """
    Placeholder.placeholder2 = "2786876876"
    return response


@router.delete("/{pkstr}}")
async def delete_tokens_pksrt(
    response: Placeholder,
) -> Placeholder:
    """
    TODO {pksrt} DELETE
    """
    Placeholder.placeholder2 = "2"
    return response
