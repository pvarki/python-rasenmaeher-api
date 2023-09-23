"""mTLS stuff, needs to be away from base to avoid cyclic imports"""
import logging

import aiohttp

from ..mtlsinit import get_session_winit

LOGGER = logging.getLogger(__name__)


async def mtls_session() -> aiohttp.ClientSession:
    """mTLS auth session with content-type set"""
    session = await get_session_winit()
    session.headers.add("Content-Type", "application/json")
    return session
