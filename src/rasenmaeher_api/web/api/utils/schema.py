"""Schema for utils."""
from typing import Optional
from pydantic import BaseModel


class LdapConnString(BaseModel):  # pylint: disable=too-few-public-methods
    """Utils / LDAP conn string schema"""

    ldap_conn_string: Optional[str]
    ldap_user: Optional[str]
    ldap_client_secret: Optional[str]
    success: bool
    reason: Optional[str]


class KeyCloakConnString(BaseModel):  # pylint: disable=too-few-public-methods
    """Utils / Keycloak conn string schema"""

    # Keycloack configuration.
    keycloak_server_url: Optional[str]
    keycloak_client_id: Optional[str]
    keycloak_realm_name: Optional[str]
    keycloak_client_s_sting: Optional[str]
    success: bool
    reason: Optional[str]
