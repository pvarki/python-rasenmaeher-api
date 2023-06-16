"""Utils API views."""
from typing import Any, Dict
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

# https://pypi.org/project/xmlsec/
# poetry add python3-saml
# poetry add xmlsec

from onelogin.saml2.auth import OneLogin_Saml2_Auth

# from onelogin.saml2.settings import OneLogin_Saml2_Settings
# from onelogin.saml2.utils import OneLogin_Saml2_Utils

from rasenmaeher_api.web.api.utils.schema import LdapConnString, KeyCloakConnString

from ....settings import settings


router = APIRouter()


# https://github.com/SAML-Toolkits/python3-saml/tree/master

saml_settings = settings.saml_settings


async def prepare_from_fastapi_request(request, debug: bool = False):
    """asd testing saml stuff..."""

    if debug is True:
        print("TODO some debug stuff maybe....")

    form_data = await request.form()
    returnvalue: Dict[Any, Any] = {
        "http_host": request.client.host,
        "server_port": request.url.port,
        "script_name": request.url.path,
        "post_data": {},
        "get_data": {}
        # Advanced request options
        # "https": "",
        # "request_uri": "",
        # "query_string": "",
        # "validate_signature_from_qs": False,
        # "lowercase_urlencoding": False
    }
    if request.query_params:
        returnvalue["get_data"] = (request.query_params,)
    if "SAMLResponse" in form_data:
        saml_response = form_data["SAMLResponse"]
        returnvalue["post_data"]["SAMLResponse"] = saml_response
    if "RelayState" in form_data:
        relay_state = form_data["RelayState"]
        returnvalue["post_data"]["RelayState"] = relay_state
    return returnvalue


@router.post("/saml/test")
# async def test(request: Request, p1: Optional[str] = Form(None), p2: Optional[str] = Form(None)):
async def test(request: Request):
    """asd testing saml test uri"""
    req = await prepare_from_fastapi_request(request)
    return req


@router.get("/saml/login")
async def saml_login(request: Request):
    """asd testing saml login"""
    req = await prepare_from_fastapi_request(request)
    auth = OneLogin_Saml2_Auth(req, settings.saml_settings)
    # saml_settings = auth.get_settings()
    # metadata = saml_settings.get_sp_metadata()
    # errors = saml_settings.validate_metadata(metadata)
    # if len(errors) == 0:
    #   print(metadata)
    # else:
    #   print("Error found on Metadata: %s" % (', '.join(errors)))
    callback_url = auth.login()
    response = RedirectResponse(url=callback_url)
    return response


@router.post("/saml/callback")
async def saml_login_callback(request: Request):
    """asd testing saml callback"""
    req = await prepare_from_fastapi_request(request, True)
    auth = OneLogin_Saml2_Auth(req, settings.saml_settings)
    auth.process_response()  # Process IdP response
    errors = auth.get_errors()  # This method receives an array with the errors
    if len(errors) == 0:
        # This check if the response was ok and the user data retrieved or not (user authenticated)
        if not auth.is_authenticated():
            return "user Not authenticated"
        return "User authenticated"
    print("Error when processing SAML Response: %s %s" % (", ".join(errors), auth.get_last_error_reason()))
    return "Error in callback"


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
