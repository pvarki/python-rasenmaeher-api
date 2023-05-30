"""Schema for utils."""
from pydantic import BaseModel


class LdapConnString(BaseModel):  # pylint: disable=too-few-public-methods
    """Utils / LDAP conn string schema"""

    ldap_host: str
    ldap_user: str
    ldap_s_string: str


class KeyCloackConnString(BaseModel):  # pylint: disable=too-few-public-methods
    """Utils / Keycloack conn string schema"""

    # Keycloack configuration.
    keycloack_server_url: str
    keycloack_client_id: str
    keycloack_realm_name: str
    keycloack_client_s_sting: str
