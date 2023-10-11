"""Utils API views."""
import logging

from fastapi import APIRouter, Depends, Response
from libpvarki.middleware.mtlsheader import MTLSHeader


from .schema import LdapConnString, KeyCloakConnString
from ....rmsettings import switchme_to_singleton_call
from ....cfssl.public import get_crl


LOGGER = logging.getLogger(__name__)
router = APIRouter()


@router.get("/ldap-conn-string", dependencies=[Depends(MTLSHeader(auto_error=True))])
async def request_utils_ldap_conn_string() -> LdapConnString:
    """
    TODO ldap-conn-string
    """

    if None in (
        switchme_to_singleton_call.ldap_conn_string,
        switchme_to_singleton_call.ldap_username,
        switchme_to_singleton_call.ldap_client_secret,
    ):
        return LdapConnString(
            success=False,
            reason="One or more ldap connection variables are undefined.",
            ldap_conn_string=switchme_to_singleton_call.ldap_conn_string,
            ldap_user=switchme_to_singleton_call.ldap_username,
            ldap_client_secret=switchme_to_singleton_call.ldap_client_secret,
        )

    return LdapConnString(
        success=True,
        ldap_conn_string=switchme_to_singleton_call.ldap_conn_string,
        ldap_user=switchme_to_singleton_call.ldap_username,
        ldap_client_secret=switchme_to_singleton_call.ldap_client_secret,
        reason="",
    )


@router.get("/keycloak-conn-string", dependencies=[Depends(MTLSHeader(auto_error=True))])
async def request_utils_keycloak_conn_string() -> KeyCloakConnString:
    """
    TODO keycloak-conn-string
    """

    if None in (
        switchme_to_singleton_call.keycloak_server_url,
        switchme_to_singleton_call.keycloak_client_id,
        switchme_to_singleton_call.keycloak_realm_name,
        switchme_to_singleton_call.keycloak_client_secret,
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
        keycloak_server_url=switchme_to_singleton_call.keycloak_server_url,
        keycloak_client_id=switchme_to_singleton_call.keycloak_client_id,
        keycloak_realm_name=switchme_to_singleton_call.keycloak_realm_name,
        keycloak_client_s_sting=switchme_to_singleton_call.keycloak_client_secret,
        reason="",
    )


@router.get("/crl")
async def return_crl() -> Response:
    """Get the CRL from CFSSL"""
    crl_der = await get_crl()
    return Response(content=crl_der, media_type="application/pkix-crl")
