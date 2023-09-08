"""The conftest.py provides fixtures for the entire directory. Fixtures defined can be used by any test in that package without needing to import them."""
import logging


import pytest
from libadvian.logging import init_logging

init_logging(logging.DEBUG)
LOGGER = logging.getLogger(__name__)


@pytest.fixture
def localmaeher_api():
    return "https://localmaeher.pvarki.fi:4439/api", "v1"

@pytest.fixture
def localhost_api():
    return "http://127.0.0.1:8000/api", "v1"

@pytest.fixture
def openapi_version():
    # OpenAPI version, FastAPI version
    return "3.1.0", "0.1.0"
