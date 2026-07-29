"""Schema for utils."""

from pydantic import BaseModel


class LdapConnString(BaseModel, extra="forbid"):
    """Utils / LDAP conn string schema"""

    ldap_conn_string: str | None
    ldap_user: str | None
    ldap_client_secret: str | None
    success: bool
    reason: str | None
