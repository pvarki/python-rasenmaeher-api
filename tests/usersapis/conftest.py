"""fixtures"""
from typing import AsyncGenerator, cast
import logging
from pathlib import Path
import uuid

import pytest
import pytest_asyncio
from async_asgi_testclient import TestClient  # pylint: disable=import-error
from multikeyjwt import Issuer

from rasenmaeher_api.web.application import get_app

LOGGER = logging.getLogger(__name__)


# pylint: disable=W0621


@pytest.fixture(scope="session")
def datadir(nice_tmpdir_mod: str) -> Path:
    """Make sure we have a well known directory structure"""
    datadir = Path(nice_tmpdir_mod) / "persistent"
    datadir.mkdir(parents=True)
    privdir = datadir / "private"
    pubdir = datadir / "public"
    privdir.mkdir()
    pubdir.mkdir()
    return datadir


@pytest_asyncio.fixture(scope="session")
async def admin_mtls_client(issuer_cl: Issuer) -> AsyncGenerator[TestClient, None]:
    """(fake) mTLS client for admin"""
    async with TestClient(get_app()) as instance:
        token = issuer_cl.issue(
            {
                "sub": "tpadminsession",
                "anon_admin_session": True,
                "nonce": str(uuid.uuid4()),
            }
        )
        instance.headers.update({"Authorization": f"Bearer {token}"})
        url = "/api/v1/firstuser/add-admin"
        data = {
            "callsign": "FIRSTADMINa",
        }
        LOGGER.debug("Fetching {}".format(url))
        LOGGER.debug("Data: {}".format(data))
        response = await instance.post(url, json=data)
        response.raise_for_status()
        payload = response.json()
        assert "jwt_exchange_code" in payload
        del instance.headers["Authorization"]
        instance.headers.update({"X-ClientCert-DN": "CN=FIRSTADMINa,O=N/A"})
        yield instance


async def enroll_user(poolcode: str, callsign: str, admin: TestClient) -> bytes:
    """Enrolls a user, returns the p12 cert pkg"""
    async with TestClient(get_app()) as instance:
        # start enroll
        url = "/api/v1/enrollment/invitecode/enroll"
        data = {
            "invite_code": poolcode,
            "callsign": callsign,
        }
        LOGGER.debug("Fetching {}".format(url))
        LOGGER.debug("Data: {}".format(data))
        response = await instance.post(url, json=data)
        response.raise_for_status()
        enroll_payload = response.json()
        instance.headers.update({"Authorization": f"Bearer {enroll_payload['jwt']}"})

        # approve enrollment
        url = "/api/v1/enrollment/accept"
        data = {
            "callsign": callsign,
            "approvecode": enroll_payload["approvecode"],
        }
        LOGGER.debug("Fetching {}".format(url))
        LOGGER.debug("Data: {}".format(data))
        response = await admin.post(url, json=data)
        response.raise_for_status()

        # Fetch the p12 file
        p12url = f"/api/v1/enduserpfx/{callsign}.pfx"
        p12resp = await instance.get(p12url)
        p12resp.raise_for_status()
        return cast(bytes, p12resp.content)


@pytest_asyncio.fixture(scope="session")
async def enroll_poolcode(admin_mtls_client: TestClient) -> AsyncGenerator[str, None]:
    """Create enrollment pool"""
    admin = admin_mtls_client
    url = "/api/v1/enrollment/invitecode/create"
    LOGGER.debug("Fetching {}".format(url))
    response = await admin.post(url, json=None)
    response.raise_for_status()
    payload = response.json()
    poolcode = payload["invite_code"]
    yield poolcode
    # PONDER: Clean up ??


@pytest_asyncio.fixture(scope="session")
async def user_mtls_client(admin_mtls_client: TestClient, enroll_poolcode: str) -> AsyncGenerator[TestClient, None]:
    """mTLS client for user"""
    await enroll_user(enroll_poolcode, "ENROLLUSERa", admin_mtls_client)

    async with TestClient(get_app()) as instance:
        instance.headers.update({"X-ClientCert-DN": "CN=ENROLLUSERa,O=N/A"})
        yield instance


@pytest_asyncio.fixture(scope="session")
async def product_mtls_client(admin_mtls_client: TestClient) -> AsyncGenerator[TestClient, None]:
    """Client with mocked NGinx mTLS headers"""
    _ = admin_mtls_client  # Just make sure the db inits are done
    async with TestClient(get_app()) as instance:
        instance.headers.update({"X-ClientCert-DN": "CN=fake.localmaeher.pvarki.fi,O=N/A"})
        yield instance
