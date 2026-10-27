"""Signed service requests must authorize exactly one federation operation."""

import json
import time
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import jwt
import pytest
from fastapi.testclient import TestClient
from multikeyjwt import Issuer, Verifier
from sqlalchemy.exc import OperationalError

from rasenmaeher_api.rmsettings import RMSettings

LOCAL = "localmaeher.dev.pvarki.fi"
REMOTE = "fast-flounder.other.example"
AUDIENCE = f"rasenmaeher:tak-federation:{LOCAL}"


def claims(**overrides: Any) -> dict[str, Any]:
    now = int(time.time())
    return {
        "iss": "orchestrator",
        "sub": "orchestrator",
        "aud": AUDIENCE,
        "iat": now,
        "nbf": now,
        "exp": now + 60,
        "nonce": str(uuid4()),
        "federation_action": "trust",
        "remote_base": REMOTE,
        **overrides,
    }


def sign(issuer: Issuer, payload: dict[str, Any]) -> str:
    return jwt.api_jws.encode(json.dumps(payload).encode(), issuer._privkey, algorithm="RS256")


def post(client: TestClient, token: str, *, endpoint: str = "trust", remote: str = REMOTE):
    return client.post(f"/{endpoint}", json={"remote_base": remote}, headers={"Authorization": f"Bearer {token}"})


@pytest.mark.parametrize("action", ["trust", "outgoing"])
def test_valid_service_request(client: TestClient, consume: AsyncMock, issuer_cl: Issuer, action: str) -> None:
    payload = claims(federation_action=action)
    token = issuer_cl.issue(payload, lifetime=60)
    client.cookies.set("rm_jwt_cookie", "invalid cookie must not override bearer")
    assert post(client, token, endpoint=action).status_code == 200
    assert consume.call_args.args[0] == payload["nonce"]
    assert consume.call_args.args[1]["action"] == action


@pytest.mark.parametrize("header", [None, "", "Basic ignored", "Bearer", "Bearer invalid"])
def test_header_only(client: TestClient, consume: AsyncMock, issuer_cl: Issuer, header: str | None) -> None:
    client.cookies.set("rm_jwt_cookie", sign(issuer_cl, claims()))
    headers = {"Authorization": header} if header is not None else {}
    response = client.post("/trust", json={"remote_base": REMOTE}, headers=headers)
    assert response.status_code == 403
    consume.assert_not_called()


@pytest.mark.parametrize(
    "field,value",
    [
        ("iss", ""),
        ("sub", ""),
        ("iss", []),
        ("sub", "  "),
        ("aud", "wrong"),
        ("aud", [AUDIENCE]),
        ("federation_action", "outgoing"),
        ("federation_action", ["trust"]),
        ("remote_base", "other.example"),
        ("remote_base", "https://" + REMOTE),
        ("remote_base", REMOTE + ":4439"),
        ("nonce", "invalid"),
        ("nonce", 1),
        ("iat", True),
        ("nbf", True),
        ("exp", True),
        ("iat", "1"),
        ("nbf", "1"),
        ("exp", "9999999999"),
        ("iat", 1.5),
        ("nbf", 1.5),
        ("exp", 9999999999.5),
        ("iat", None),
        ("nbf", None),
        ("exp", None),
    ],
)
def test_invalid_claims(client: TestClient, consume: AsyncMock, issuer_cl: Issuer, field: str, value: Any) -> None:
    response = post(client, sign(issuer_cl, claims(**{field: value})))
    assert response.status_code == 403
    consume.assert_not_called()


@pytest.mark.parametrize("case", ["expired", "future_iat", "future_nbf", "long_lifetime"])
def test_invalid_times(client: TestClient, consume: AsyncMock, issuer_cl: Issuer, case: str) -> None:
    payload = claims()
    now = payload["iat"]
    payload.update(
        {
            "expired": {"exp": now - 1},
            "future_iat": {"iat": now + 60},
            "future_nbf": {"nbf": now + 60},
            "long_lifetime": {"exp": now + 301},
        }[case]
    )
    assert post(client, sign(issuer_cl, payload)).status_code == 403
    consume.assert_not_called()


@pytest.mark.parametrize(
    "field", ["iss", "sub", "aud", "iat", "nbf", "exp", "nonce", "federation_action", "remote_base"]
)
def test_required_claims(client: TestClient, consume: AsyncMock, issuer_cl: Issuer, field: str) -> None:
    payload = claims()
    payload.pop(field)
    assert post(client, sign(issuer_cl, payload)).status_code == 403
    consume.assert_not_called()


def test_time_order(client: TestClient, consume: AsyncMock, issuer_cl: Issuer) -> None:
    now = int(time.time())
    assert post(client, sign(issuer_cl, claims(iat=now, nbf=now - 10))).status_code == 403
    consume.assert_not_called()


@pytest.mark.parametrize("algorithm", ["HS256", "none"])
def test_wrong_algorithm(client: TestClient, consume: AsyncMock, algorithm: str) -> None:
    key = "a-test-hmac-key-at-least-32-characters" if algorithm == "HS256" else None
    assert post(client, jwt.encode(claims(), key, algorithm=algorithm)).status_code == 403
    consume.assert_not_called()


def test_untrusted_key(client: TestClient, consume: AsyncMock) -> None:
    from cryptography.hazmat.primitives.asymmetric import ec

    key = ec.generate_private_key(ec.SECP256R1())
    assert post(client, jwt.encode(claims(), key, algorithm="ES256")).status_code == 403
    consume.assert_not_called()


def test_normalization_and_nonce(client: TestClient, consume: AsyncMock, issuer_cl: Issuer) -> None:
    nonce = uuid4()
    token = sign(issuer_cl, claims(remote_base=REMOTE.upper() + ":0443", nonce=nonce.hex.upper()))
    assert post(client, token, remote=REMOTE.upper() + ":443").status_code == 200
    assert consume.call_args.args[0] == str(nonce)


def test_wrong_target_host(client: TestClient, consume: AsyncMock, issuer_cl: Issuer) -> None:
    token = sign(issuer_cl, claims(aud="rasenmaeher:tak-federation:attacker.example"))
    client.headers["Host"] = "attacker.example"
    assert post(client, token).status_code == 403
    consume.assert_not_called()


def test_self_federation(client: TestClient, consume: AsyncMock, issuer_cl: Issuer) -> None:
    token = sign(issuer_cl, claims(remote_base=LOCAL))
    assert post(client, token, remote=LOCAL + ":4439").status_code == 422
    consume.assert_not_called()


def test_unavailable_replay_state(client: TestClient, consume: AsyncMock, issuer_cl: Issuer) -> None:
    consume.side_effect = OperationalError("query", {}, Exception("private database path"))
    response = post(client, sign(issuer_cl, claims()))
    assert response.status_code == 503
    assert "private database path" not in response.text


def test_empty_keys(client: TestClient, consume: AsyncMock, issuer_cl: Issuer, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Verifier.singleton(), "pubkeys", [])
    assert post(client, sign(issuer_cl, claims())).status_code == 503
    consume.assert_not_called()


def test_audit_no_token(client: TestClient, issuer_cl: Issuer, caplog: pytest.LogCaptureFixture) -> None:
    token = sign(issuer_cl, claims(federation_action="outgoing"))
    with caplog.at_level("AUDIT"):
        assert post(client, token).status_code == 403
    records = [r for r in caplog.records if r.message == "TAK federation request"]
    assert records[-1].issuer == "orchestrator"
    assert records[-1].stage == "authorize"
    assert token not in caplog.text


@pytest.mark.parametrize("field", ["iat", "nbf", "exp"])
def test_nonfinite_timestamp(client: TestClient, consume: AsyncMock, issuer_cl: Issuer, field: str) -> None:
    assert post(client, sign(issuer_cl, claims(**{field: float("inf")}))).status_code == 403
    consume.assert_not_called()


def test_audience_isolation(client: TestClient, consume: AsyncMock, issuer_cl: Issuer) -> None:
    original_config = issuer_cl.config
    assert post(client, sign(issuer_cl, claims())).status_code == 200
    RMSettings.singleton().kraftwerk_manifest_dict["dns"] = "another.example"
    consume.reset_mock()
    assert post(client, sign(issuer_cl, claims())).status_code == 403
    consume.assert_not_called()
    assert post(client, sign(issuer_cl, claims(aud="rasenmaeher:tak-federation:another.example"))).status_code == 200
    assert issuer_cl.config == original_config
    assert Verifier.singleton().decode(issuer_cl.issue({"sub": "ordinary-session"}))["sub"] == "ordinary-session"
