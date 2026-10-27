"""Public routes dispatch once to TAK without forwarding the service JWT."""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient
from multikeyjwt import Issuer

from rasenmaeher_api.db.errors import TokenReuse
from rasenmaeher_api.rmsettings import RMSettings
from rasenmaeher_api.web.api.federation import views

from .test_authorization import REMOTE, claims, sign

FINGERPRINT = ":".join(["AB"] * 32)


def success(action: str) -> dict[str, Any]:
    common = {"success": True, "operation": action, "remote_base": REMOTE, "changed": True}
    if action == "trust":
        return {**common, "ca_fingerprint": FINGERPRINT, "group": "default", "directions": ["INBOUND", "OUTBOUND"]}
    return {
        **common,
        "display_name": "fast flounder",
        "address": f"tak.{REMOTE}",
        "port": 9001,
        "protocol_version": 2,
        "enabled": True,
        "connection_status": "CONNECTING",
    }


@pytest.fixture
def public(client: TestClient, consume: AsyncMock) -> TestClient:
    client.app.include_router(views.router, prefix="/api/v1/federation")
    RMSettings.singleton().kraftwerk_manifest_dict["products"] = {"tak": {"api": "https://tak.local.example:4626/"}}
    used: set[str] = set()

    async def use_nonce(nonce: str, auditmeta: dict[str, Any]) -> None:
        await asyncio.sleep(0)
        if nonce in used:
            raise TokenReuse()
        used.add(nonce)

    consume.side_effect = use_nonce
    return client


@pytest.fixture
def product(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    response = MagicMock(status=200)
    response.json = AsyncMock(return_value=success("trust"))
    session.response = response
    session.post.return_value.__aenter__ = AsyncMock(return_value=response)
    session.post.return_value.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(views, "get_session_winit", AsyncMock(return_value=session))
    return session


def post(
    public: TestClient, issuer: Issuer, action: str = "trust", *, token: str | None = None, body: dict | None = None
):
    token = token or sign(issuer, claims(federation_action=action))
    return public.post(
        f"/api/v1/federation/tak/{action}",
        json=body or {"remote_base": REMOTE},
        headers={"Authorization": f"Bearer {token}"},
    )


@pytest.mark.parametrize("action", ["trust", "outgoing"])
@pytest.mark.parametrize("changed", [True, False])
def test_fixed_dispatch(public: TestClient, product: MagicMock, issuer_cl: Issuer, action: str, changed: bool) -> None:
    payload = {**success(action), "changed": changed}
    product.response.json.return_value = payload
    response = post(public, issuer_cl, action)
    assert response.status_code == 200
    assert response.json() == payload
    args, options = product.post.call_args
    assert args == (f"https://tak.local.example:4626/api/v1/federation/{action}",)
    assert options["json"] == {"remote_base": REMOTE}
    assert options["allow_redirects"] is False
    assert options["timeout"].total == 30
    assert "headers" not in options and "Authorization" not in str(options)
    product.post.assert_called_once()


@pytest.mark.parametrize("status", [409, 422, 502, 503, 504])
def test_product_error(public: TestClient, product: MagicMock, issuer_cl: Issuer, status: int) -> None:
    product.response.status = status
    product.response.json.return_value = {
        "detail": {
            "code": "test_failure",
            "stage": "groups",
            "message": "private path or credentials",
            "may_have_changed": True,
        }
    }
    response = post(public, issuer_cl)
    assert response.status_code == status
    detail = response.json()["detail"]
    assert detail["code"] == "test_failure"
    assert detail["stage"] == "groups"
    assert detail["may_have_changed"] is True
    assert "private path or credentials" not in response.text


@pytest.mark.parametrize("status", [302, 401, 403, 500])
def test_unexpected_status(public: TestClient, product: MagicMock, issuer_cl: Issuer, status: int) -> None:
    product.response.status = status
    response = post(public, issuer_cl)
    assert response.status_code == 502
    assert response.json()["detail"]["may_have_changed"] is True


@pytest.mark.parametrize(
    "override",
    [
        {"success": False},
        {"success": 1},
        {"changed": "true"},
        {"remote_base": "another.example"},
        {"operation": "outgoing"},
        {"group": "other"},
        {"directions": ["INBOUND"]},
        {"ca_fingerprint": "not a fingerprint"},
        {"extra": "field"},
    ],
)
def test_bad_success(public: TestClient, product: MagicMock, issuer_cl: Issuer, override: dict[str, Any]) -> None:
    product.response.json.return_value.update(override)
    assert post(public, issuer_cl).status_code == 502


@pytest.mark.parametrize(
    "field", ["success", "operation", "remote_base", "changed", "ca_fingerprint", "group", "directions"]
)
def test_incomplete_success(public: TestClient, product: MagicMock, issuer_cl: Issuer, field: str) -> None:
    product.response.json.return_value.pop(field)
    assert post(public, issuer_cl).status_code == 502


@pytest.mark.parametrize(
    "override",
    [
        {"enabled": False},
        {"enabled": 1},
        {"port": 9002},
        {"protocol_version": 1},
        {"address": "tak.another.example"},
        {"display_name": "bad-name"},
    ],
)
def test_bad_outgoing(public: TestClient, product: MagicMock, issuer_cl: Issuer, override: dict[str, Any]) -> None:
    product.response.json.return_value = {**success("outgoing"), **override}
    assert post(public, issuer_cl, "outgoing").status_code == 502


def test_non_json(public: TestClient, product: MagicMock, issuer_cl: Issuer) -> None:
    product.response.json.side_effect = ValueError("<html>private backend failure</html>")
    response = post(public, issuer_cl)
    assert response.status_code == 502
    assert "private backend" not in response.text


def test_missing_product(public: TestClient, product: MagicMock, issuer_cl: Issuer) -> None:
    RMSettings.singleton().kraftwerk_manifest_dict["products"] = {}
    assert post(public, issuer_cl).status_code == 404
    product.post.assert_not_called()


@pytest.mark.parametrize(
    "api",
    [
        "http://tak.local.example/",
        "https://user:pass@tak.local.example/",  # pragma: allowlist secret
        123,
    ],
)
def test_bad_product_config(public: TestClient, product: MagicMock, issuer_cl: Issuer, api: Any) -> None:
    RMSettings.singleton().kraftwerk_manifest_dict["products"]["tak"]["api"] = api
    assert post(public, issuer_cl).status_code == 503
    product.post.assert_not_called()


def test_timeout_consumes_nonce(public: TestClient, product: MagicMock, issuer_cl: Issuer) -> None:
    product.post.side_effect = TimeoutError("private URL")
    token = sign(issuer_cl, claims())
    response = post(public, issuer_cl, token=token)
    assert response.status_code == 504
    assert response.json()["detail"]["may_have_changed"] is True
    assert post(public, issuer_cl, token=token).status_code == 403
    product.post.assert_called_once()


@pytest.mark.asyncio
async def test_concurrent_replay(public: TestClient, product: MagicMock, issuer_cl: Issuer) -> None:
    token = sign(issuer_cl, claims())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=public.app), base_url="https://local.example"
    ) as client:

        async def send() -> httpx.Response:
            return await client.post(
                "/api/v1/federation/tak/trust",
                json={"remote_base": REMOTE},
                headers={"Authorization": f"Bearer {token}"},
            )

        responses = await asyncio.gather(send(), send())
    assert sorted(response.status_code for response in responses) == [200, 403]
    product.post.assert_called_once()


@pytest.mark.parametrize(
    "remote",
    [
        "https://remote.example",
        "127.0.0.1",
        "tak.remote.example",
        "remote.example/a",
        "user@remote.example",
        "a..example",
        "remote.example:0",
        "a" * 31 + ".example",
    ],
)
def test_invalid_peer(public: TestClient, product: MagicMock, issuer_cl: Issuer, remote: str) -> None:
    assert post(public, issuer_cl, body={"remote_base": remote}).status_code == 422
    product.post.assert_not_called()


def test_extra_body_fields(public: TestClient, product: MagicMock, issuer_cl: Issuer) -> None:
    assert post(public, issuer_cl, body={"remote_base": REMOTE, "product": "another"}).status_code == 422
    product.post.assert_not_called()


def test_invalid_token_no_dispatch(public: TestClient, product: MagicMock, issuer_cl: Issuer) -> None:
    assert post(public, issuer_cl, token="invalid").status_code == 403
    product.post.assert_not_called()


@pytest.mark.parametrize("action", ["trust", "outgoing"])
def test_audit_outcome(
    public: TestClient, product: MagicMock, issuer_cl: Issuer, caplog: pytest.LogCaptureFixture, action: str
) -> None:
    product.response.json.return_value = success(action)
    with caplog.at_level("AUDIT"):
        assert post(public, issuer_cl, action).status_code == 200
    records = [record for record in caplog.records if record.message == "TAK federation request"]
    assert len(records) == 1
    record = records[0]
    assert record.levelname == "AUDIT"
    assert record.__dict__["event.action"] == f"tak_federation_{action}"
    assert record.__dict__["event.outcome"] == "success"
    assert record.__dict__["destination.user.name"] == REMOTE
    assert record.issuer == "orchestrator"
    assert record.nonce


def test_audit_invalid_request(
    public: TestClient, product: MagicMock, issuer_cl: Issuer, caplog: pytest.LogCaptureFixture
) -> None:
    token = sign(issuer_cl, claims())
    with caplog.at_level("AUDIT"):
        response = public.post(
            "/api/v1/federation/tak/trust",
            json={"remote_base": "invalid peer", "secret": "do not log"},  # pragma: allowlist secret
            headers={"Authorization": f"Bearer {token}"},
        )
    assert response.status_code == 422
    records = [record for record in caplog.records if record.message == "TAK federation request"]
    assert len(records) == 1
    assert records[0].__dict__["event.outcome"] == "failure"
    assert records[0].stage == "validate"
    assert token not in caplog.text
    assert "do not log" not in caplog.text
    product.post.assert_not_called()
