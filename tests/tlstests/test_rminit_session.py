"""Test the self-init certs get created"""
import logging
import ssl

import pytest
from async_asgi_testclient import TestClient
from libpvarki.mtlshelp.context import get_ca_context

from rasenmaeher_api.mtlsinit import get_session_winit

LOGGER = logging.getLogger(__name__)


def test_ssl_context() -> None:
    """Make sure we can get the context (ref sterlette issue)"""
    get_ca_context(ssl.Purpose.SERVER_AUTH)


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_session(app_client: TestClient) -> None:
    """Test that appclient initializes mtls certs so we can get a session"""
    _ = app_client  # we need get_app() to be run
    session = await get_session_winit()
    assert session
