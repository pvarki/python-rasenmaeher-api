"""pytest automagics"""
# from typing import Any, Generator, AsyncGenerator, List, cast
from typing import Dict, Any, AsyncGenerator
import logging
from async_asgi_testclient import TestClient
import pytest_asyncio
from libadvian.logging import init_logging
from rasenmaeher_api.web.application import get_app
from rasenmaeher_api.settings import settings

init_logging(logging.DEBUG)
LOGGER = logging.getLogger(__name__)


@pytest_asyncio.fixture(scope="function")
async def app_client(request: Any) -> AsyncGenerator[TestClient, None]:
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


@pytest_asyncio.fixture(scope="function")
async def unauth_client(unauth_client_sess: TestClient) -> AsyncGenerator[TestClient, None]:
    """Instantiated test client with no privileges, clear cookies between yields"""
    unauth_client_sess.cookie_jar.clear()
    yield unauth_client_sess
    unauth_client_sess.cookie_jar.clear()
