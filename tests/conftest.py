"""The conftest.py provides fixtures for the entire directory.
Fixtures defined can be used by any test in that package without needing to import them."""
from typing import Tuple, Dict, AsyncGenerator
import logging
from pathlib import Path
import ssl

import aiohttp
import pytest
import pytest_asyncio
from libadvian.logging import init_logging

init_logging(logging.DEBUG)
LOGGER = logging.getLogger(__name__)
CA_PATH = Path(__file__).parent / "testcas"


@pytest_asyncio.fixture
async def session_with_testcas() -> AsyncGenerator[aiohttp.ClientSession, None]:
    """aiohttp session with the mkcert CA enabled"""
    ssl_ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    LOGGER.info("Loading local CA certs from {}".format(CA_PATH))
    for cafile in CA_PATH.glob("*ca*.pem"):
        if not cafile.is_file():
            continue
        LOGGER.debug("Adding cert {}".format(cafile))
        ssl_ctx.load_verify_locations(str(cafile))
    conn = aiohttp.TCPConnector(ssl=ssl_ctx)
    async with aiohttp.ClientSession(connector=conn) as session:
        yield session


@pytest.fixture
def localmaeher_api() -> Tuple[str, str]:
    """Return url and version for https API"""
    return "https://localmaeher.pvarki.fi:4439/api", "v1"


@pytest.fixture
def localhost_api() -> Tuple[str, str]:
    """Return url and version for http API"""
    return "http://127.0.0.1:8000/api", "v1"


@pytest.fixture
def openapi_version() -> Tuple[str, str]:
    """Return expected openapi and fastapi versions"""
    # OpenAPI version, FastAPI version
    return "3.1.0", "0.1.0"


# FIXME: rename this, or if only needed in one test file=module, move it there
@pytest.fixture
def testdata() -> Dict[str, str]:
    """Return values needed for tests"""
    return {
        "permit_str": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
        "user_hash": "PerPerPerjantaiPulloParisee",
        "first_time_user_work_id1": "kukko",
        "first_time_user_work_id2": "kana",
        "invite_code_invalid_user_hash": "asdfaj3433423420342230942394",
        "invite_code_work_id1": "roosteri",
        "invite_code": "asdölfjasfrei33424äxcxc",
    }


# FIXME: if duplicate firstuser, it returns only HTTP Error 500
@pytest.fixture
def error_messages() -> Dict[str, str]:
    """Return values needed for verifying error messages in tests"""
    return {
        "NO_USERS_FOUND": "No users found...",
        "FIRSTUSER_API_IS_DISABLED": "/firstuser API is disabled",
        "NOT_FOUND": "Not Found",
        "INVITECODE_NOT_VALID": "Error. invitecode not valid.",
        "NO_ENROLLMENT_PERMISSIONS": "Error. Given management hash doesn't have 'enrollment' permissions.",
    }
