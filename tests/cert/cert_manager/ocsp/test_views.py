"""Test the OCSP HTTP layer: the two transports, cache headers, and size guards."""

import base64
import logging
import os
import urllib.parse

import pytest
from async_asgi_testclient import TestClient  # type: ignore[import-untyped]
from cryptography.x509 import ocsp

from rasenmaeher_api.cert.cert_manager.ocsp import views
from rasenmaeher_api.cert.cert_manager.ocsp.responder import ResponseMeta

from .helpers import LeafFactory, RequestFactory, SigningCA

LOGGER = logging.getLogger(__name__)


def _status(der: bytes) -> ocsp.OCSPResponseStatus:
    """Parse the OCSP-level status out of a response body"""
    return ocsp.load_der_ocsp_response(der).response_status


@pytest.mark.asyncio(loop_scope="session")
async def test_http_post_and_get(
    installed_signer: SigningCA,
    make_leaf: LeafFactory,
    make_request: RequestFactory,
    ginosession: None,
    ocsp_client: TestClient,
) -> None:
    """POST body and GET base64-path forms return equivalent responses with cache headers"""
    _ = ginosession, installed_signer
    leaf = make_leaf("HTTPLEAF")
    reqder = make_request(leaf)

    postresp = await ocsp_client.post("/api/v1/ocsp", data=reqder)
    assert postresp.status_code == 200
    assert postresp.headers["content-type"] == "application/ocsp-response"
    assert "max-age=" in postresp.headers["cache-control"]
    parsed = ocsp.load_der_ocsp_response(postresp.content)
    assert parsed.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
    assert parsed.serial_number == leaf.serial_number

    b64 = urllib.parse.quote(base64.b64encode(reqder).decode("ascii"), safe="")
    getresp = await ocsp_client.get(f"/api/v1/ocsp/{b64}")
    assert getresp.status_code == 200
    gparsed = ocsp.load_der_ocsp_response(getresp.content)
    assert gparsed.response_status == ocsp.OCSPResponseStatus.SUCCESSFUL
    assert gparsed.serial_number == parsed.serial_number
    assert gparsed.certificate_status == parsed.certificate_status


@pytest.mark.asyncio(loop_scope="session")
async def test_http_nonce_no_store(
    installed_signer: SigningCA,
    make_leaf: LeafFactory,
    make_request: RequestFactory,
    ginosession: None,
    ocsp_client: TestClient,
) -> None:
    """Nonced responses must not be cached"""
    _ = ginosession, installed_signer
    leaf = make_leaf("NONCEHTTP")
    reqder = make_request(leaf, nonce=os.urandom(8))
    resp = await ocsp_client.post("/api/v1/ocsp", data=reqder)
    assert resp.status_code == 200
    assert resp.headers["cache-control"] == "no-store"


@pytest.mark.asyncio(loop_scope="session")
async def test_http_bad_base64(installed_signer: SigningCA, ocsp_client: TestClient) -> None:
    """Garbage in the GET path is an OCSP-level malformed response, still HTTP 200"""
    _ = installed_signer
    resp = await ocsp_client.get("/api/v1/ocsp/not!!!base64===")
    assert resp.status_code == 200
    assert _status(resp.content) == ocsp.OCSPResponseStatus.MALFORMED_REQUEST


@pytest.mark.parametrize("body", (b"", b"\x30" * (views.MAX_REQUEST_BYTES + 1)))
@pytest.mark.asyncio(loop_scope="function")
async def test_post_rejects_empty_and_oversize(ocsp_client: TestClient, body: bytes) -> None:
    """An empty or oversize POST body is refused before any parsing or DB work"""
    resp = await ocsp_client.post("/api/v1/ocsp", data=body)
    assert resp.status_code == 200  # OCSP errors ride HTTP 200
    assert _status(resp.content) == ocsp.OCSPResponseStatus.MALFORMED_REQUEST


@pytest.mark.asyncio(loop_scope="function")
async def test_get_rejects_oversize(ocsp_client: TestClient) -> None:
    """A GET whose base64 decodes to more than MAX_REQUEST_BYTES is refused"""
    oversize = base64.b64encode(b"\x30" * (views.MAX_REQUEST_BYTES + 1)).decode("ascii")
    resp = await ocsp_client.get(f"/api/v1/ocsp/{urllib.parse.quote(oversize, safe='')}")
    assert resp.status_code == 200
    assert _status(resp.content) == ocsp.OCSPResponseStatus.MALFORMED_REQUEST


def test_to_http_without_timestamps_adds_no_cache_headers() -> None:
    """A successful response lacking validity timestamps gets no cache headers.

    Defensive branch: the responder always sets both, so this pins that a future change
    cannot produce Cache-Control referring to timestamps that are not there.
    """
    resp = views._to_http(b"der", ResponseMeta(success=True))
    assert "Cache-Control" not in resp.headers
    assert "Expires" not in resp.headers


def test_to_http_error_response_is_uncached() -> None:
    """OCSP error responses carry no caching hints"""
    resp = views._to_http(b"der", ResponseMeta(success=False))
    assert "Cache-Control" not in resp.headers
    assert resp.media_type == "application/ocsp-response"
