"""Keycloak helpers"""
from typing import Optional, Any, ClassVar, Dict, Set, Union
from dataclasses import dataclass, field
import logging
import uuid

from libpvarki.schemas.product import UserCRUDRequest
from pydantic import BaseModel, Extra, Field
from keycloak.keycloak_admin import KeycloakAdmin


from .rmsettings import RMSettings

LOGGER = logging.getLogger(__name__)


class KCUserData(BaseModel):
    """Represent KC user object manipulations"""

    productdata: UserCRUDRequest = Field(description="Data that would be sent to productAPIs")
    roles: Set[str] = Field(default_factory=set, description="Local roles")
    kc_id: Optional[str] = Field(description="KC id (uuid)", default=None)
    kc_data: Dict[str, Any] = Field(description="Full KC data", default_factory=dict)

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid


# PONDER: Maybe switch to https://python-keycloak.readthedocs.io/en/latest/modules/async.html
@dataclass
class KCClient:
    """Client for Keycloak"""

    kcadmin: KeycloakAdmin = field()
    _kc_admin_role: Optional[dict[str, Union[str, bool]]] = field(default=None)
    _singleton: ClassVar[Optional["KCClient"]] = None

    @classmethod
    def singleton(cls) -> "KCClient":
        """Return singleton"""
        if not KCClient._singleton:
            conf = RMSettings.singleton()
            KCClient._singleton = KCClient(
                KeycloakAdmin(
                    server_url=conf.kc_url,
                    username=conf.kc_username,
                    password=conf.kc_password,
                    realm_name=conf.kc_realm,
                    user_realm_name=conf.kc_user_realm,
                )
            )
        return KCClient._singleton

    # TODO: Use the root admin account to create a service account that uses our mTLS cert
    #       product integrations must make all user manipulations through rasenmaeher so we can
    #       tall other products about changes too.
    # TODO: Make sure the group "admins" exists, or should we use direct role for that ??

    async def _refresh_user(self, user_id: str, pdata: UserCRUDRequest) -> KCUserData:
        """Refresh user"""
        lresp_payload = await self.kcadmin.a_get_user(user_id)
        LOGGER.debug(lresp_payload)
        return KCUserData(
            kc_id=lresp_payload["id"],
            productdata=pdata,
            kc_data=lresp_payload,
        )

    async def _check_admin_role(self) -> None:
        """Cache the admin role definition"""
        if self._kc_admin_role:
            return
        ret = await self.kcadmin.a_get_realm_roles(search_text="admin")
        # If multipe roles match the search choose exact match
        flt = [rolerep for rolerep in ret if rolerep["name"] == "admin"]
        if not flt:
            raise ValueError("KC has no configured 'admin' role")
        self._kc_admin_role = flt[0]

    async def check_user_roles(self, user: KCUserData) -> bool:
        """Chekc users roles in KC and update as needed, returns true if changes were made"""
        await self._check_admin_role()
        kc_roles = {role["name"]: role for role in await self.kcadmin.a_get_realm_roles_of_user(user.kc_id)}
        LOGGER.debug("Found KC roles: {} (user: {})".format(list(kc_roles.keys()), user.roles))
        if "admin" in user.roles:
            if "admin" not in kc_roles:
                LOGGER.info("Adding admin role in KC to {}".format(user.productdata.callsign))
                await self.kcadmin.a_assign_realm_roles(user.kc_id, [self._kc_admin_role])
                return True
        else:
            if "admin" in kc_roles:
                LOGGER.info("Removing admin role in KC from {}".format(user.productdata.callsign))
                await self.kcadmin.a_delete_realm_roles_of_user(user.kc_id, [self._kc_admin_role])
                return True
        return False

    async def create_kc_user(self, user: KCUserData) -> Optional[KCUserData]:
        """Create a new user in KC"""
        conf = RMSettings.singleton()
        if not conf.kc_enabled:
            return None
        manifest = conf.kraftwerk_manifest_dict
        if user.kc_id:
            raise ValueError("Cannot specify KC id when creating")
        pdata = user.productdata
        send_payload = {
            "username": pdata.callsign,  # NOTE: KeyCloak now forces this all lowercase
            "email": f"{pdata.uuid}@{manifest['dns']}",
            "firstName": pdata.callsign,
            "lastName": manifest["deployment"],
            "enabled": True,
            "emailVerified": True,
            "attributes": {
                "callsign": pdata.callsign,
                "certpem": pdata.x509cert,
            },
            "credentials": [
                {  # FIXME: How to allow only x509, especially with the LDAP there too ??
                    "type": "password",
                    "value": str(uuid.uuid4()),
                    "temporary": False,
                }
            ],
        }

        user_id = await self.kcadmin.a_create_user(send_payload, exist_ok=False)
        user.kc_id = user_id
        await self.check_user_roles(user)
        return await self._refresh_user(user_id, pdata)

    async def update_kc_user(self, user: KCUserData) -> Optional[KCUserData]:
        """Update user"""
        conf = RMSettings.singleton()
        if not conf.kc_enabled:
            return None
        if not user.kc_id:
            LOGGER.error("No KC id defined")
            return None
        manifest = conf.kraftwerk_manifest_dict
        pdata = user.productdata
        send_payload = {
            "username": pdata.callsign,  # NOTE: KeyCloak now forces this all lowercase
            "attributes": {
                "callsign": pdata.callsign,
                "certpem": pdata.x509cert,
            },
            "email": f"{pdata.uuid}@{manifest['dns']}",
            "firstName": pdata.callsign,
            "lastName": manifest["deployment"],
            "enabled": True,
        }
        await self.kcadmin.a_update_user(user.kc_id, send_payload)
        await self.check_user_roles(user)
        return await self._refresh_user(user.kc_id, pdata)

    async def delete_kc_user(self, user: KCUserData) -> bool:
        """delete user"""
        conf = RMSettings.singleton()
        if not conf.kc_enabled:
            return False
        if not user.kc_id:
            LOGGER.error("No KC id defined")
            return False
        await self.kcadmin.a_delete_user(user.kc_id)
        return True