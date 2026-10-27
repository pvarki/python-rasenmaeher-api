"""Federation unit tests need no live CA, identity provider or products."""

import pytest


@pytest.fixture(scope="session")
def session_env_config() -> None:
    """Override the integration suite's Docker setup for these isolated tests."""
