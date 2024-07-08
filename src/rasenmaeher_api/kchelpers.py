"""Keycloak helpers"""
from typing import Optional, Any, ClassVar, Dict, Set
from dataclasses import dataclass, field
import logging
import time
import uuid

import aiohttp
from libpvarki.schemas.product import UserCRUDRequest
from pydantic import BaseModel, Extra, Field


from .mtlsinit import get_session_winit
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


@dataclass
class KCClient:
    """Client for Keycloak"""

    _tokeninfo: Optional[Dict[str, Any]] = field(default=None)  # FIXME: Make pydantic class for this
    _singleton: ClassVar[Optional["KCClient"]] = None

    @classmethod
    def singleton(cls) -> "KCClient":
        """Return singleton"""
        if not KCClient._singleton:
            KCClient._singleton = KCClient()
        return KCClient._singleton

    # TODO: Use the root admin account to create a service account that uses our mTLS cert
    #       product integrations must make all user manipulations through rasenmaeher so we can
    #       tall other products about changes too.
    # TODO: Make sure the group "admins" exists, or should we use direct role for that ??

    async def refresh_token(self) -> None:
        """Check token and refresh if needed"""
        if not self._tokeninfo:
            return await self.new_token()
        if "expires_at" not in self._tokeninfo:
            return await self.new_token()
        # Valid for more than 2.5s, still time to use it
        if self._tokeninfo["expires_at"] - time.time() > 2.5:
            return
        if "refresh_expires_at" not in self._tokeninfo:
            return await self.new_token()
        # Too little time to do a refresh
        if self._tokeninfo["refresh_expires_at"] - time.time() < 0.5:
            return await self.new_token()
        # FIXME: Do the proper refresh
        return await self.new_token()

    async def new_token(self) -> None:
        """Get a completely fresh token"""
        conf = RMSettings.singleton()
        session = await get_session_winit()
        async with session as client:
            uri = f"{conf.kc_url}/realms/{conf.kc_user_realm}/protocol/openid-connect/token"
            resp = await client.post(
                uri,
                data={
                    "client_id": "admin-cli",
                    "username": conf.kc_username,
                    "password": conf.kc_password,
                    "grant_type": "password",
                },
            )
            resp.raise_for_status()
            payload = await resp.json()
            if payload is None:
                raise ValueError("Did not get payload")
            payload["expires_at"] = time.time() + payload["expires_in"]
            payload["refresh_expires_at"] = time.time() + payload["refresh_expires_in"]
            self._tokeninfo = payload

    async def get_kc_client(self) -> aiohttp.ClientSession:
        """Get a session, re-use token if still valid"""
        await self.refresh_token()
        if not self._tokeninfo:
            raise RuntimeError("no tokeninfo, this should be impossible")
        tinfo = self._tokeninfo
        session = await get_session_winit()
        session.headers.update(
            {
                "Authorization": f"{tinfo['token_type']} {tinfo['access_token']}",
            }
        )
        return session

    async def _refresh_user(self, client: aiohttp.ClientSession, uri: str, pdata: UserCRUDRequest) -> KCUserData:
        """Refresh user"""
        lresp = await client.get(uri)
        lresp_payload = await lresp.json()
        LOGGER.debug(lresp_payload)
        return KCUserData(
            kc_id=lresp_payload["id"],
            productdata=pdata,
            kc_data=lresp_payload,
        )

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
            "username": pdata.callsign,
            "email": f"{pdata.uuid}@{manifest['dns']}",
            "firstName": pdata.callsign,
            "lastName": manifest["deployment"],
            "enabled": True,
            "emailVerified": True,
            "credentials": [
                {  # FIXME: How to allow only x509 ??
                    "type": "password",
                    "value": str(uuid.uuid4()),
                    "temporary": False,
                }
            ],
        }
        uri = f"{conf.kc_url}/admin/realms/{conf.kc_realm}/users"
        session = await self.get_kc_client()
        async with session as client:
            LOGGER.debug("POSTing to {}".format(uri))
            resp = await client.post(
                uri,
                json=send_payload,
            )
            resp.raise_for_status()
            return await self._refresh_user(client, resp.headers["Location"], pdata)

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
            "username": pdata.callsign,
            "email": f"{pdata.uuid}@{manifest['dns']}",
            "firstName": pdata.callsign,
            "lastName": manifest["deployment"],
            "enabled": True,
        }
        # FIXME: How to add admin to correct group/role ??
        kc_uuid = user.kc_id
        uri = f"{conf.kc_url}/admin/realms/{conf.kc_realm}/users/{kc_uuid}"
        session = await self.get_kc_client()
        async with session as client:
            LOGGER.debug("PUTting to {}".format(uri))
            resp = await client.put(
                uri,
                json=send_payload,
            )
            resp.raise_for_status()
            LOGGER.debug("resp={}".format(resp))
            return await self._refresh_user(client, uri, pdata)

    async def delete_kc_user(self, user: KCUserData) -> bool:
        """delete user"""
        conf = RMSettings.singleton()
        if not conf.kc_enabled:
            return False
        if not user.kc_id:
            LOGGER.error("No KC id defined")
            return False
        uri = f"{conf.kc_url}/admin/realms/{conf.kc_realm}/users/{user.kc_id}"
        session = await self.get_kc_client()
        async with session as client:
            LOGGER.info("Calling DELETE at {}".format(uri))
            resp = await client.delete(
                uri,
            )
            resp.raise_for_status()
            LOGGER.debug("resp={}".format(resp))
            return True
