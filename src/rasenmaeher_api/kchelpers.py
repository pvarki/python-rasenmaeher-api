"""Keycloak helpers"""
from typing import Optional, Any, ClassVar, Dict
from dataclasses import dataclass, field
import logging
import time

import aiohttp

from .mtlsinit import get_session_winit
from .rmsettings import RMSettings

LOGGER = logging.getLogger(__name__)


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
    #       create a service account for each product in manifest as well, just in case...

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
