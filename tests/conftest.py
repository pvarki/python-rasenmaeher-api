"""The conftest.py provides fixtures for the entire directory.
Fixtures defined can be used by any test in that package without needing to import them."""
from typing import Tuple, Dict
import logging

import pytest
from libadvian.logging import init_logging

init_logging(logging.DEBUG)
LOGGER = logging.getLogger(__name__)


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
    """Return values needed for status tests"""
    return {
        "permit_str": "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1",
        "work_id1": "koira",
        "work_id2": "kissa",
    }
