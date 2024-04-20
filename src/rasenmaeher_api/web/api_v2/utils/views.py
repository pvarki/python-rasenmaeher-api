"""Utils API views."""
import logging

from fastapi import APIRouter, Depends, Response
from fastapi.responses import FileResponse
from libpvarki.middleware.mtlsheader import MTLSHeader


from .schema import LdapConnString, KeyCloakConnString
from ....rmsettings import RMSettings
from ....cfssl.public import get_crl
from ....jwtinit import resolve_rm_jwt_pubkey_path


LOGGER = logging.getLogger(__name__)
router = APIRouter()


@router.get("/ldap-conn-string", dependencies=[Depends(MTLSHeader(auto_error=True))])
async def request_utils_ldap_conn_string() -> LdapConnString:
    """
    TODO ldap-conn-string
    """

    conf = RMSettings.singleton()
    if None in (
        conf.ldap_conn_string,
        conf.ldap_username,
        conf.ldap_client_secret,
    ):
        return LdapConnString(
            success=False,
            reason="One or more ldap connection variables are undefined.",
            ldap_conn_string=conf.ldap_conn_string,
            ldap_user=conf.ldap_username,
            ldap_client_secret=conf.ldap_client_secret,
        )

    return LdapConnString(
        success=True,
        ldap_conn_string=conf.ldap_conn_string,
        ldap_user=conf.ldap_username,
        ldap_client_secret=conf.ldap_client_secret,
        reason="",
    )


@router.get("/keycloak-conn-string", dependencies=[Depends(MTLSHeader(auto_error=True))])
async def request_utils_keycloak_conn_string() -> KeyCloakConnString:
    """
    TODO keycloak-conn-string
    """

    conf = RMSettings.singleton()
    if None in (
        conf.keycloak_server_url,
        conf.keycloak_client_id,
        conf.keycloak_realm_name,
        conf.keycloak_client_secret,
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
        keycloak_server_url=conf.keycloak_server_url,
        keycloak_client_id=conf.keycloak_client_id,
        keycloak_realm_name=conf.keycloak_realm_name,
        keycloak_client_s_sting=conf.keycloak_client_secret,
        reason="",
    )


@router.get("/crl")
async def return_crl() -> Response:
    """Get the CRL from CFSSL. NOTE: This should not be used anymore, use the cosprest helper for CRLs"""
    crl_der = await get_crl()
    return Response(content=crl_der, media_type="application/pkix-crl")


@router.get("/jwt.pub")
async def return_jwt_pubkey() -> FileResponse:
    """Return PEM encoded public key for tokens that RASENMAEHER issues"""
    my_dn = RMSettings.singleton().kraftwerk_manifest_dict["dns"]
    deployment_name = my_dn.split(".")[0]
    return FileResponse(
        resolve_rm_jwt_pubkey_path(), media_type="application/x-pem-file", filename=f"{deployment_name}_rm_jwt.pub"
    )
