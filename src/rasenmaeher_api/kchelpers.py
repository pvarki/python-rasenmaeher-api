"""Keycloak helpers"""

from typing import Optional, Any, ClassVar, Dict, Set, Union, cast
from dataclasses import dataclass, field
import logging
import uuid
import json

from libpvarki.schemas.product import UserCRUDRequest
from pydantic import BaseModel, Extra, Field
from keycloak.keycloak_admin import KeycloakAdmin
from keycloak.exceptions import KeycloakError


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
    _product_initial_grps: Optional[Dict[str, Dict[str, Any]]] = None

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
        # If multiple roles match the search choose exact match
        flt = [rolerep for rolerep in ret if rolerep["name"] == "admin"]
        if not flt:
            raise ValueError("KC has no configured 'admin' role")
        self._kc_admin_role = flt[0]

    async def check_user_roles(self, user: KCUserData) -> bool:
        """Check users roles in KC and update as needed, returns true if changes were made"""
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

    async def resolve_kc_id(self, email: str) -> Optional[str]:
        """Find user with given email"""
        found = await self.kcadmin.a_get_users({"email": email})
        if not found:
            return None
        LOGGER.debug("found: {}".format(found))
        if len(found) > 1:
            LOGGER.warning("Found more than one result, using the first one")
        item = found[0]
        if "id" not in item:
            LOGGER.error("Found user does not have id")
            return None
        return str(item["id"])

    def user_kc_email(self, user: KCUserData) -> str:
        """Return the unique email for user in KC"""
        conf = RMSettings.singleton()
        manifest = conf.kraftwerk_manifest_dict
        return f"{user.productdata.uuid}@{manifest['dns']}"

    async def create_kc_user(self, user: KCUserData) -> Optional[KCUserData]:
        """Create a new user in KC"""
        conf = RMSettings.singleton()
        if not conf.kc_enabled:
            return None
        manifest = conf.kraftwerk_manifest_dict
        if user.kc_id:
            raise ValueError("Cannot specify KC id when creating")
        pdata = user.productdata
        user_email = self.user_kc_email(user)

        send_payload = {
            "username": pdata.callsign,  # NOTE: KeyCloak now forces this all lowercase
            "email": user_email,
            "firstName": pdata.callsign,
            "lastName": manifest["deployment"],
            "enabled": True,
            "emailVerified": True,
            "attributes": {
                "callsign": pdata.callsign,
                "certpem": pdata.x509cert,
                "altUsernames": [f"{pdata.callsign}_{productname}" for productname in manifest["products"].keys()],
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
        if pdata.callsign != "anon_admin":
            await self.user_initial_groups(user)
        await self.check_user_roles(user)
        return await self._refresh_user(user_id, pdata)

    async def user_initial_groups(self, user: KCUserData) -> Optional[bool]:
        """Assign user to initial product groups"""
        conf = RMSettings.singleton()
        if not conf.kc_enabled:
            return None
        if not user.kc_id:
            LOGGER.error("No KC id defined")
            return None
        await self.ensure_product_groups()
        if not self._product_initial_grps:
            return None
        pdata = user.productdata
        for group in self._product_initial_grps.values():
            LOGGER.info("Assigning {} to {}".format(pdata.callsign, group["path"]))
            await self.kcadmin.a_group_user_add(user.kc_id, group["id"])
        return True

    async def update_kc_user(self, user: KCUserData) -> Optional[KCUserData]:
        """Update user"""
        conf = RMSettings.singleton()
        if not conf.kc_enabled:
            return None
        manifest = conf.kraftwerk_manifest_dict
        pdata = user.productdata
        user_email = self.user_kc_email(user)

        if not user.kc_id:
            LOGGER.warning("No KC id defined, trying to resolve")
            resolved = await self.resolve_kc_id(user_email)
            if not resolved:
                LOGGER.error("Could not resolve KC id, trying to create the user")
                return await self.create_kc_user(user)
            user.kc_id = resolved
        await self.check_user_roles(user)
        send_payload = user.kc_data
        send_payload.update(
            {
                "email": user_email,
                "firstName": pdata.callsign,
                "lastName": manifest["deployment"],
                "enabled": True,
            }
        )
        if "attributes" not in send_payload:
            send_payload["attributes"] = {
                "callsign": pdata.callsign,
            }
        send_payload["attributes"].update(
            {
                "certpem": pdata.x509cert,
                "altUsernames": [f"{pdata.callsign}_{productname}" for productname in manifest["products"].keys()],
            }
        )
        for rofieldname in ("createTimestamp", "createdTimestamp", "modifyTimestamp"):
            if rofieldname in send_payload:
                del send_payload[rofieldname]
            if rofieldname in send_payload["attributes"]:
                del send_payload["attributes"][rofieldname]
        LOGGER.debug("Sending payload: {}".format(send_payload))
        try:
            await self.kcadmin.a_update_user(user.kc_id, send_payload)
        except KeycloakError as exc:
            LOGGER.exception("Could not update KC user: {}".format(exc))
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

    async def client_access_token(self) -> Dict[str, Union[str, int]]:
        """Create initial access token for a client to register for OIDC"""
        return cast(Dict[str, Union[str, int]], json.loads(await self.kcadmin.a_create_initial_access_token()))

    async def ensure_product_groups(self) -> Optional[bool]:
        """Make sure each product in manifest has a root level group and initial child-group"""
        conf = RMSettings.singleton()
        if not conf.kc_enabled:
            return None
        manifest = conf.kraftwerk_manifest_dict
        groups = await self.kcadmin.a_get_groups()
        groups_by_name = {group["name"]: group for group in groups}
        created = False
        for productname in manifest["products"].keys():
            if productname not in groups_by_name:
                LOGGER.info("Creating KC group /{}".format(productname))
                new_id = await self.kcadmin.a_create_group({"name": productname})
                groups_by_name[productname] = await self.kcadmin.a_get_group(new_id)
                created = True
            group = groups_by_name[productname]
            subgroups_by_name: Dict[str, Dict[str, Any]] = {
                subgroup["name"]: subgroup for subgroup in group["subGroups"]
            }
            for suffix in ("default", "admins"):
                subgrpname = f"{productname}_{suffix}"
                if subgrpname not in subgroups_by_name:
                    LOGGER.info("Creating KC group /{}/{}".format(productname, subgrpname))
                    new_id = await self.kcadmin.a_create_group({"name": subgrpname}, parent=group["id"])
                    subgroups_by_name[subgrpname] = await self.kcadmin.a_get_group(new_id)
                    created = True
                if self._product_initial_grps is None:
                    self._product_initial_grps = {}
                if suffix == "default":
                    self._product_initial_grps[productname] = subgroups_by_name[subgrpname]
        LOGGER.debug("Product initial KC groups: {}".format(self._product_initial_grps))
        return created
