"""Keycloak helper tests"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from rasenmaeher_api.kchelpers import KCClient


@pytest.mark.asyncio
async def test_client_access_token_outlives_registration() -> None:
    """The initial access token must stay valid long enough to register a client"""
    kcadmin = MagicMock()
    kcadmin.a_create_initial_access_token = AsyncMock(return_value={"token": "x"})
    assert await KCClient(kcadmin).client_access_token() == {"token": "x"}
    kcadmin.a_create_initial_access_token.assert_awaited_once_with(count=1, expiration=60)
