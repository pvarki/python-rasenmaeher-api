"""pytest automagics"""
# from typing import Any, Generator, AsyncGenerator, List, cast
from typing import Dict, Any, AsyncGenerator
import logging
from async_asgi_testclient import TestClient  # pylint: disable=import-error
import pytest_asyncio  # pylint: disable=import-error
from _pytest.fixtures import SubRequest
from libadvian.logging import init_logging
from rasenmaeher_api.web.application import get_app
from rasenmaeher_api.settings import settings

init_logging(logging.DEBUG)
LOGGER = logging.getLogger(__name__)

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
