"""Users API views."""
from fastapi import APIRouter

from rasenmaeher_api.web.api.users.schema import Placeholder

router = APIRouter()


@router.get("/me")
async def request_users_me(
    response: Placeholder,
) -> Placeholder:
    """
    TODO get /me
    """
    Placeholder.placeholder2 = "2193287298371"

    return response


@router.get("/me/acl")
async def request_users_me_acl(
    response: Placeholder,
) -> Placeholder:
    """
    TODO get /me/acl
    """
    Placeholder.placeholder2 = "28327648273648732"

    return response


@router.get("/{pkstr}")
async def request_users_pkstr(
    response: Placeholder,
) -> Placeholder:
    """
    TODO get /{pkstr}
    """
    Placeholder.placeholder2 = "200980980980"

    return response


@router.delete("/{pkstr}")
async def delete_users_pkstr(
    response: Placeholder,
) -> Placeholder:
    """
    TODO delete {pkstr}
    """
    Placeholder.placeholder2 = "193287129387212"

    return response


@router.post("/{pkstr}/roles")
async def post_users_pkstr_roles(
    response: Placeholder,
) -> Placeholder:
    """
    TODO post /{pkstr}/roles
    """
    Placeholder.placeholder2 = "2120938120938210938"

    return response


@router.delete("/{pkstr}/roles/{userid}")
async def delete_users_pkstr_roles_userid(
    response: Placeholder,
) -> Placeholder:
    """
    TODO delete /{pkstr}/roles/{userid}
    """
    Placeholder.placeholder2 = "254554545454555454"

    return response
