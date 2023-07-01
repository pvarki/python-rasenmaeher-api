"""Utils API views."""
import base64
from typing import cast
from fastapi import APIRouter, Response
import requests

from rasenmaeher_api.web.api.utils.schema import LdapConnString, KeyCloakConnString

from ....settings import settings


router = APIRouter()


@router.get("/ldap-conn-string")
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



async def get_crl() -> bytes:
    """
    Quick and dirty method to get CA from CFSSL
    returns: CA certificate
    """
    url = "http://127.0.0.1:8888/api/v1/cfssl/crl"

    response = requests.request("GET", url, timeout=5)
    data = response.json().get("result")
    # decode base64
    data = base64.b64decode(data)

    return cast(bytes, data)


@router.get("/crl")
async def return_crl() -> Response:
    """
    Method for TAK sign CSR and request CA
    params: csr
    """
    crl = await get_crl()

    return Response(content=crl, media_type="application/pkix-crl")
