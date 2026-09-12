"""Test feedback proxy endpoint"""

import logging
from types import TracebackType
from typing import Any, ClassVar, Self
from unittest.mock import patch

import aiohttp
import pytest
from async_asgi_testclient import TestClient  # type: ignore[import-untyped]

from rasenmaeher_api.rmsettings import RMSettings

LOGGER = logging.getLogger(__name__)

VALID_FEEDBACK = {
    "rating": "good",
    "comments": "Works fine",
    "role": "admin",
    "os": "macos",
    "version": "2.6.0+260729",
    "web_address": "https://example.pvarki.fi/app/settings",
}


class FakeResponse:
    """Minimal stand-in for an aiohttp response"""

    def __init__(self, status: int = 200) -> None:
        self.status = status

    def raise_for_status(self) -> None:
        """Mimic aiohttp raising on error statuses"""
        if self.status >= 400:
            raise aiohttp.ClientError(f"status {self.status}")

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        return None


class FakeSession:
    """Records the single post the endpoint is expected to make"""

    calls: ClassVar[list[dict[str, Any]]] = []

    def __init__(self, status: int = 200, raises: Exception | None = None) -> None:
        self.status = status
        self.raises = raises

    def __call__(self, *args: object, **kwargs: object) -> Self:
        return self

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tbk: TracebackType | None
    ) -> None:
        return None

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        """Capture the outgoing request instead of sending it"""
        FakeSession.calls.append({"url": url, **kwargs})
        if self.raises:
            raise self.raises
        return FakeResponse(self.status)


@pytest.fixture()
def configured_ingest(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the settings at a fake ingest"""
    conf = RMSettings.singleton()
    monkeypatch.setattr(conf, "feedback_ingest_url", "https://ingest.example.com/feedback")
    monkeypatch.setattr(conf, "feedback_ingest_key", "secretkey")
    monkeypatch.setattr(conf, "feedback_ingest_key_header", "x-test-key")
    FakeSession.calls = []


@pytest.mark.asyncio(loop_scope="session")
async def test_feedback_not_configured(user_mtls_client: TestClient) -> None:
    """Without an ingest url and key the endpoint refuses instead of silently dropping"""
    resp = await user_mtls_client.post("/api/v1/feedback", json=VALID_FEEDBACK)
    assert resp.status_code == 503


@pytest.mark.asyncio(loop_scope="session")
async def test_feedback_forwarded(user_mtls_client: TestClient, configured_ingest: None) -> None:
    """A valid submission reaches the ingest with server-resolved deployment context"""
    with patch("aiohttp.ClientSession", FakeSession()):
        resp = await user_mtls_client.post("/api/v1/feedback", json=VALID_FEEDBACK)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert len(FakeSession.calls) == 1
    call = FakeSession.calls[0]
    assert call["url"] == "https://ingest.example.com/feedback"
    assert call["headers"]["x-test-key"] == "secretkey"
    payload = call["json"]
    assert payload["rating"] == "good"
    assert payload["web_address"] == VALID_FEEDBACK["web_address"]
    # Deployment is resolved server side, the browser does not get to assert it
    assert payload["deployment"] == RMSettings.singleton().deployment_name
    assert payload["deployment"] in payload["subject"]
    # Triage metadata is also folded into the message body
    assert "os: macos" in payload["message"]


@pytest.mark.asyncio(loop_scope="session")
async def test_feedback_ingest_unreachable(user_mtls_client: TestClient, configured_ingest: None) -> None:
    """An ingest failure is reported as a bad gateway, not a success"""
    with patch("aiohttp.ClientSession", FakeSession(raises=aiohttp.ClientError("boom"))):
        resp = await user_mtls_client.post("/api/v1/feedback", json=VALID_FEEDBACK)
    assert resp.status_code == 502


@pytest.mark.asyncio(loop_scope="session")
async def test_feedback_ingest_rate_limited(user_mtls_client: TestClient, configured_ingest: None) -> None:
    """The ingest saying 429 is passed through so the user is told to retry"""
    with patch("aiohttp.ClientSession", FakeSession(status=429)):
        resp = await user_mtls_client.post("/api/v1/feedback", json=VALID_FEEDBACK)
    assert resp.status_code == 429


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"comments": "no rating"}, id="missing_rating"),
        pytest.param({"rating": "good", "comments": "x" * 5001}, id="comments_too_long"),
        pytest.param({"rating": "good", "comments": "ok", "sneaky": "field"}, id="extra_field"),
    ],
)
async def test_feedback_rejects_bad_payload(
    user_mtls_client: TestClient, configured_ingest: None, payload: dict[str, Any]
) -> None:
    """Unbounded or unexpected input never reaches the ingest"""
    with patch("aiohttp.ClientSession", FakeSession()):
        resp = await user_mtls_client.post("/api/v1/feedback", json=payload)
    assert resp.status_code == 422
    assert not FakeSession.calls
