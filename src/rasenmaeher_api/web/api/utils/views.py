"""Utils API views."""
from fastapi import APIRouter
from rasenmaeher_api.web.api.utils.schema import LdapConnString, KeyCloakConnString

from ....settings import settings


router = APIRouter()


@router.get("/ldap-conn-string")
async def request_utils_ldap_conn_string() -> LdapConnString:
    """
    TODO ldap-conn-string
    """

    if None in (settings.ldap_conn_string, settings.ldap_username, settings.ldap_client_secret):
        return LdapConnString(success=False, reason="One or more ldap connection variables are undefined.")

    return LdapConnString(
        success=True,
        ldap_conn_string=settings.ldap_conn_string,
        ldap_user=settings.ldap_username,
        ldap_client_secret=settings.ldap_client_secret,
    )


@router.get("/keycloak-conn-string")
async def request_utils_keycloak_conn_string() -> KeyCloakConnString:
    """
    TODO ldap-conn-string
    """

    if None in (
        settings.keycloak_server_url,
        settings.keycloak_client_id,
        settings.keycloak_realm_name,
        settings.keycloak_client_secret,
    ):
        return KeyCloakConnString(success=False, reason="One or more Keycloak connection variables are undefined.")

    return KeyCloakConnString(
        success=True,
        keycloak_server_url=settings.keycloak_server_url,
        keycloak_client_id=settings.keycloak_client_id,
        keycloak_realm_name=settings.keycloak_realm_name,
        keycloak_client_s_sting=settings.keycloak_client_secret,
    )
