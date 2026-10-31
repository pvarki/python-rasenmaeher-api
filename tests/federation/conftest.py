"""Federation unit tests need no live CA, identity provider or products."""

from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from libpvarki.logging import add_trace_and_audit
from multikeyjwt import Verifier

from rasenmaeher_api.db.nonces import SeenToken
from rasenmaeher_api.rmsettings import RMSettings
from rasenmaeher_api.web.api.middleware.federation import authorize_federation
from tests.conftest import JWT_PATH

LOCAL = "localmaeher.dev.pvarki.fi"


@pytest.fixture(scope="session")
def session_env_config() -> None:
    """Override the integration suite's Docker setup for these isolated tests."""


@pytest.fixture
def consume(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    mock = AsyncMock()
    monkeypatch.setattr(SeenToken, "use_token", mock)
    return mock


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, consume: AsyncMock) -> TestClient:
    add_trace_and_audit()
    settings = RMSettings.singleton()
    monkeypatch.setattr(settings, "kraftwerk_manifest_bool", True)
    monkeypatch.setattr(settings, "kraftwerk_manifest_dict", {"dns": LOCAL, "products": {}})
    monkeypatch.setenv("JWT_COOKIE_NAME", "rm_jwt_cookie")
    monkeypatch.setattr(Verifier, "_singleton", Verifier(pubkeypath=JWT_PATH / "cl_jwtRS256.pub"))
    app = FastAPI()

    @app.post("/trust")
    @app.post("/outgoing")
    async def endpoint(payload: dict[str, Any] = Depends(authorize_federation)) -> dict[str, Any]:
        return {"sub": payload["sub"]}

    return TestClient(app)
