"""Keep existing RMAPI authentication usable after the JWT library upgrade."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from libpvarki.logging import add_trace_and_audit
from multikeyjwt import Issuer, Verifier

from rasenmaeher_api.web.api.checkauth import router as checkauth_router
from rasenmaeher_api.web.api.tokens import router as tokens_router
from tests.conftest import JWT_PATH


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch, issuer_cl: Issuer) -> TestClient:
    add_trace_and_audit()
    monkeypatch.setenv("JWT_COOKIE_NAME", "rm_jwt_cookie")
    monkeypatch.setattr(Verifier, "_singleton", Verifier(pubkeypath=JWT_PATH / "cl_jwtRS256.pub"))
    monkeypatch.setattr(Issuer, "_singleton", issuer_cl)
    app = FastAPI()
    app.include_router(checkauth_router, prefix="/check")
    app.include_router(tokens_router, prefix="/token")
    return TestClient(app)


def test_header_precedes_cookie(client: TestClient, issuer_cl: Issuer) -> None:
    client.cookies.set("rm_jwt_cookie", "invalid")
    token = issuer_cl.issue({"sub": "service"}, lifetime=60)
    response = client.get("/check/jwt", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["sub"] == "service"


@pytest.mark.parametrize("header", ["", "Basic ignored", "Bearer invalid"])
def test_invalid_header_cannot_use_cookie(client: TestClient, issuer_cl: Issuer, header: str) -> None:
    client.cookies.set("rm_jwt_cookie", issuer_cl.issue({"sub": "cookie"}, lifetime=60))
    assert client.get("/check/jwt", headers={"Authorization": header}).status_code == 403


def test_cookie_refresh(client: TestClient, issuer_cl: Issuer) -> None:
    client.cookies.set("rm_jwt_cookie", issuer_cl.issue({"sub": "cookie"}, lifetime=60))
    assert client.get("/check/jwt").json()["sub"] == "cookie"
    refreshed = client.get("/token/jwt/refresh")
    assert refreshed.status_code == 200
    assert Verifier.singleton().decode(refreshed.json()["jwt"])["sub"] == "cookie"


def test_optional_jwt_and_mtls(client: TestClient) -> None:
    assert client.get("/check/mtls_or_jwt", headers={"Authorization": "Bearer invalid"}).status_code == 403
    response = client.get(
        "/check/mtls_or_jwt", headers={"Authorization": "Bearer invalid", "X-ClientCert-DN": "CN=service,O=test"}
    )
    assert response.status_code == 200
    assert response.json()["type"] == "mtls"
