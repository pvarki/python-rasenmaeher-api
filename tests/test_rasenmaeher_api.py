"""Package level tests"""
from typing import Any, Dict
from pathlib import Path

import pytest
from async_asgi_testclient import TestClient
import aiohttp
from multikeyjwt.jwt.issuer import Issuer
from multikeyjwt.jwt.verifier import Verifier


from rasenmaeher_api import __version__
from rasenmaeher_api.rmsettings import RMSettings


def test_version() -> None:
    """Make sure version matches expected"""
    assert __version__ == "1.3.2"


@pytest.mark.asyncio
@pytest.mark.parametrize("app_client", [{"test": "value", "xclientcert": False}], indirect=True)
async def test_get_openapi_json(app_client: TestClient) -> None:
    """Check that we can get the openapi spec"""
    resp = await app_client.get("/api/openapi.json")
    resp_dict: Dict[Any, Any] = resp.json()
    assert resp.status_code == 200
    assert len(resp_dict) > 0


def test_settings() -> None:
    """Test settings defaults"""
    conf = RMSettings.singleton()
    assert "fake.localmaeher.pvarki.fi" in conf.valid_product_cns


@pytest.mark.asyncio
async def test_announce(unauth_client: TestClient, announce_server: str) -> None:
    """Make sure we have seen at least one announce call"""
    # Make a request to make sure the app spins up
    resp = await unauth_client.get("/api/v1/healthcheck")
    assert resp
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{announce_server}/log") as response:
            response.raise_for_status()
            resp_json = await response.json()
            assert resp_json["payloads"]
            assert resp_json["payloads"][0]["version"] == __version__


@pytest.mark.asyncio
async def test_jwt_pub_url(unauth_client: TestClient, tmp_path: Path) -> None:
    """Test the JWT public key"""
    resp = await unauth_client.get("/api/v1/utils/jwt.pub")
    resp.raise_for_status()
    keypath = tmp_path / "jwt.pub"
    keypath.write_bytes(resp.content)
    verifier = Verifier(pubkeypath=tmp_path)
    issuer = Issuer.singleton()
    token = issuer.issue({"doggo": "besto"})
    decoded = verifier.decode(token)
    assert decoded["doggo"] == "besto"
