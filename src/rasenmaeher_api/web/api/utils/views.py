"""Utils API views."""
import logging

from fastapi import APIRouter, Depends, Response
from fastapi.responses import FileResponse
from libpvarki.middleware.mtlsheader import MTLSHeader


from .schema import LdapConnString
from ....rmsettings import RMSettings
from ....cfssl.public import get_ocsprest_crl
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


@router.get("/crl")
@router.get("/crl/crl.der")
async def return_crl_der() -> Response:
    """Get the DER CRL from OCSPREST"""
    crl_der = await get_ocsprest_crl("crl.der")
    return Response(content=crl_der, media_type="application/pkix-crl")


@router.get("/crl/crl.pem")
async def return_crl_pem() -> Response:
    """Get the PEM CRL from OCSPREST"""
    crl_pem = await get_ocsprest_crl("crl.pem")
    return Response(content=crl_pem, media_type="application/x-pem-file")


@router.get("/jwt.pub")
async def return_jwt_pubkey() -> FileResponse:
    """Return PEM encoded public key for tokens that RASENMAEHER issues"""
    my_dn = RMSettings.singleton().kraftwerk_manifest_dict["dns"]
    deployment_name = my_dn.split(".")[0]
    return FileResponse(
        resolve_rm_jwt_pubkey_path(), media_type="application/x-pem-file", filename=f"{deployment_name}_rm_jwt.pub"
    )
