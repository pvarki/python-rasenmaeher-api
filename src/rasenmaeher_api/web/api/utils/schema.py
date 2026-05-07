"""Schema for utils."""

from typing import Optional
from pydantic import BaseModel


class LdapConnString(BaseModel, extra="forbid"):
    """Utils / LDAP conn string schema"""

    ldap_conn_string: Optional[str]
    ldap_user: Optional[str]
    ldap_client_secret: Optional[str]
    success: bool
    reason: Optional[str]
