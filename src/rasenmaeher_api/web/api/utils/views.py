"""Utils API views."""
import logging

from fastapi import APIRouter, Depends, Response
from libpvarki.middleware.mtlsheader import MTLSHeader


from .schema import LdapConnString, KeyCloakConnString
from ....settings import settings
from ....cfssl.public import get_crl


LOGGER = logging.getLogger(__name__)
router = APIRouter()


@router.get("/ldap-conn-string", dependencies=[Depends(MTLSHeader(auto_error=True))])
async def request_utils_ldap_conn_string() -> LdapConnString:
    """
    TODO ldap-conn-string
    """

    if None in (settings.ldap_conn_string, settings.ldap_username, settings.ldap_client_secret):
        return LdapConnString(
            success=False,
            reason="One or more ldap connection variables are undefined.",
            ldap_conn_string=settings.ldap_conn_string,
            ldap_user=settings.ldap_username,
            ldap_client_secret=settings.ldap_client_secret,
        )

    return LdapConnString(
        success=True,
        ldap_conn_string=settings.ldap_conn_string,
        ldap_user=settings.ldap_username,
        ldap_client_secret=settings.ldap_client_secret,
        reason="",
    )


@router.get("/keycloak-conn-string", dependencies=[Depends(MTLSHeader(auto_error=True))])
async def request_utils_keycloak_conn_string() -> KeyCloakConnString:
    """
    TODO keycloak-conn-string
    """

    if None in (
        settings.keycloak_server_url,
        settings.keycloak_client_id,
        settings.keycloak_realm_name,
        settings.keycloak_client_secret,
    ):
        return KeyCloakConnString(
            success=False,
            reason="One or more Keycloak connection variables are undefined.",
            keycloak_server_url="",
            keycloak_client_id="",
            keycloak_realm_name="",
            keycloak_client_s_sting="",
        )

    return KeyCloakConnString(
        success=True,
        keycloak_server_url=settings.keycloak_server_url,
        keycloak_client_id=settings.keycloak_client_id,
        keycloak_realm_name=settings.keycloak_realm_name,
        keycloak_client_s_sting=settings.keycloak_client_secret,
        reason="",
    )


@router.get("/crl")
async def return_crl() -> Response:
    """Get the CRL from CFSSL"""
    crl_der = await get_crl()
    return Response(content=crl_der, media_type="application/pkix-crl")
