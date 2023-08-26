"""pytest automagics"""
from typing import Dict, Any, AsyncGenerator, Generator
import logging
from pathlib import Path
import uuid

import pytest
from multikeyjwt import Issuer, Verifier
from multikeyjwt.config import Secret
from async_asgi_testclient import TestClient  # pylint: disable=import-error
import pytest_asyncio  # pylint: disable=import-error
from _pytest.fixtures import SubRequest
from libadvian.logging import init_logging
from libadvian.testhelpers import monkeysession  # pylint: disable=unused-import

from rasenmaeher_api.web.application import get_app
from rasenmaeher_api.settings import settings

init_logging(logging.DEBUG)
LOGGER = logging.getLogger(__name__)
DATA_PATH = Path(__file__).parent / Path("data")
JWT_PATH = DATA_PATH / Path("jwt")


# pylint: disable=redefined-outer-name
@pytest.fixture(scope="session")
def issuer_cl() -> Issuer:
    """issuer using cl-key"""
    return Issuer(
        privkeypath=JWT_PATH / Path("cl_jwtRS256.key"),
        keypasswd=Secret("Cache_Latitude_Displease_Hardcopy"),  # pragma: allowlist secret
    )


@pytest.fixture(scope="session")
def verifier() -> Verifier:
    """issuer using all keys in data"""
    return Verifier(pubkeypath=JWT_PATH)


@pytest.fixture(scope="session", autouse=True)
def jwtauth_env_config(monkeysession: pytest.MonkeyPatch) -> Generator[None, None, None]:
    """set the JWT auth config"""
    with monkeysession.context() as mpatch:
        mpatch.setenv("JWT_PUBKEY_PATH", str(JWT_PATH))
        yield None


@pytest_asyncio.fixture()
async def tilauspalvelu_jwt_client(issuer_cl: Issuer) -> AsyncGenerator[TestClient, None]:
    """Client with tilauspalvely style JWT"""
    async with TestClient(get_app()) as instance:
        token = issuer_cl.issue(
            {
                "sub": "tpadminsession",
                "nonce": str(uuid.uuid4()),
            }
        )
        instance.headers.update({"Authorization": f"Bearer {token}"})
        yield instance


@pytest_asyncio.fixture()
async def mtls_client() -> AsyncGenerator[TestClient, None]:
    """Client with mocked NGinx mTLS headers"""
    # TODO: make sure this user is in db, should it be admin too ??
    user_uuid = str(uuid.uuid4())
    async with TestClient(get_app()) as instance:
        instance.headers.update({"X-ClientCert-DN": f"CN={user_uuid},O=N/A"})
        yield instance


# Issues in tests in ubuntu-latest
# error: Untyped decorator makes function "app_client" untyped  [misc] # no-untyped-def
# pyproject.toml
# [[tool.mypy.overrides]]
# disallow_untyped_decorators=false
# adding '# type: ignore' ends up giving 'error: Unused "type: ignore" comment'
@pytest_asyncio.fixture(scope="function")
async def app_client(request: SubRequest) -> AsyncGenerator[TestClient, None]:
    """Create default client"""
    _request_params: Dict[Any, Any] = request.param
    async with TestClient(get_app()) as instance:
        # print("DEBUG FIXTURE PARAMS")
        # print(request.param)
        # print("DONE DEBUG FIXTURE PARAMS")
        if "xclientcert" in _request_params.keys() and _request_params["xclientcert"] is True:
            LOGGER.debug(
                "set header '{}:'{}'".format(
                    settings.api_client_cert_header, settings.test_api_client_cert_header_value
                )
            )
            instance.headers.update({settings.api_client_cert_header: settings.test_api_client_cert_header_value})

        yield instance
