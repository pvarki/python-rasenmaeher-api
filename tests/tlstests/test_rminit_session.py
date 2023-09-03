"""Test the self-init certs get created"""
import logging

import pytest
from async_asgi_testclient import TestClient

from rasenmaeher_api.mtlsinit import get_session_winit

LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_session(app_client: TestClient) -> None:
    """Test that appclient initializes mtls certs so we can get a session"""
    _ = app_client  # we need get_app() to be run
    session = await get_session_winit()
    assert session
