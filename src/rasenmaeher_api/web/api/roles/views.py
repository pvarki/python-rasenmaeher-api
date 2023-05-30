"""Roles API views."""
from fastapi import APIRouter

from rasenmaeher_api.web.api.roles.schema import Placeholder

router = APIRouter()


@router.get("/")
async def request_roles(
    response: Placeholder,
) -> Placeholder:
    """
    TODO get /
    """
    Placeholder.placeholder2 = "2123123"

    return response


@router.post("/")
async def post_roles(
    response: Placeholder,
) -> Placeholder:
    """
    TODO post /
    """
    Placeholder.placeholder2 = "4090909432"

    return response


@router.get("/{pkstr}")
async def request_roles_pkstr(
    response: Placeholder,
) -> Placeholder:
    """
    TODO get /{pkstr}
    """
    Placeholder.placeholder2 = "2923432424"
    return response


@router.delete("/{pkstr}")
async def delete_roles_pkstr(
    response: Placeholder,
) -> Placeholder:
    """
    TODO delete {pkstr}
    """
    Placeholder.placeholder2 = "2093092130"
    return response


@router.get("/{pkstr}/users")
async def request_roles_pkstr_users(
    response: Placeholder,
) -> Placeholder:
    """
    TODO get {pkstr}/users
    """
    Placeholder.placeholder2 = "2091204912039"
    return response


@router.post("/{pkstr}/users")
async def post_roles_pkstr_users(
    response: Placeholder,
) -> Placeholder:
    """
    TODO post /{pkstr}/users
    """
    Placeholder.placeholder2 = "269512039213"
    return response


@router.delete("/{pkstr}/users/{userid}")
async def request_roles_pkstr_users_userid(
    response: Placeholder,
) -> Placeholder:
    """
    TODO delete /{pkstr}/users/{userid}
    """
    Placeholder.placeholder2 = "1293021932"
    return response
