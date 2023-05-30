"""Utils API views."""
from fastapi import APIRouter
from rasenmaeher_api.web.api.utils.schema import LdapConnString, KeyCloackConnString

# from ....settings import settings


router = APIRouter()


@router.get("/ldap-conn-string")
async def request_utils_ldap_conn_string(
    response: LdapConnString,
) -> LdapConnString:
    """
    TODO ldap-conn-string
    """
    LdapConnString.ldap_host = "TODO_HOST_CONN_STR"
    LdapConnString.ldap_user = "TODO_HOST_CONN_USER"
    LdapConnString.ldap_s_string = "TODO_HOST_CONN_STRING"

    return response


@router.get("/keycloak-conn-string")
async def request_utils_keycloack_conn_string(
    response: KeyCloackConnString,
) -> KeyCloackConnString:
    """
    TODO ldap-conn-string
    """
    KeyCloackConnString.keycloack_server_url = "TODO_HOST_CONN_STR"
    KeyCloackConnString.keycloack_client_id = "TODO_HOST_CLIENT_ID"
    KeyCloackConnString.keycloack_realm_name = "TODO_HOST_REALM_NAME"
    KeyCloackConnString.keycloack_client_s_sting = "TODO_HOST_CLIENT_STRING"

    return response
