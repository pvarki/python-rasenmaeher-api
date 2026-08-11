"""Fixtures for the cert-manager OCSP tests.

The signer cache is a module global, so it is reset for every test and only the
``installed_signer`` fixture seeds it. Tests that exercise the acquisition path itself
leave it empty. Builders, types and DB row inserters live in helpers.py.
"""

import logging
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from async_asgi_testclient import TestClient  # type: ignore[import-untyped]
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509 import ocsp
from fastapi import FastAPI

from rasenmaeher_api.cert.cert_manager.ocsp import signer
from rasenmaeher_api.cert.cert_manager.ocsp.responder import build_ocsp_response
from tests.cert.helpers import CertFactory

from .helpers import LeafFactory, RequestFactory, Responder, SigningCA, make_signing_ca

LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def reset_signer_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """The signer cache is a module global, so never let it leak between tests"""
    monkeypatch.setattr(signer, "_CACHED", None)


@pytest.fixture()
def ocsp_ca(mint_cert: CertFactory) -> SigningCA:
    """The CA whose responses we sign, standing in for the cert-manager intermediate"""
    return make_signing_ca(mint_cert, "test-intermediate")


@pytest.fixture()
def foreign_ca(mint_cert: CertFactory) -> SigningCA:
    """An unrelated CA, for requests that are none of our business"""
    return make_signing_ca(mint_cert, "foreign-ca")


@pytest.fixture()
def installed_signer(monkeypatch: pytest.MonkeyPatch, ocsp_ca: SigningCA) -> SigningCA:
    """Seed the signer cache so no k8s call is attempted"""
    monkeypatch.setattr(signer, "_CACHED", signer.SignerMaterial(cert=ocsp_ca.cert, key=ocsp_ca.key))
    return ocsp_ca


@pytest.fixture()
def make_leaf(ocsp_ca: SigningCA, foreign_ca: SigningCA, mint_cert: CertFactory) -> LeafFactory:
    """Factory for leaves signed by our CA, or by the foreign one"""

    def _make_leaf(common_name: str, foreign: bool = False) -> x509.Certificate:
        issuer = foreign_ca if foreign else ocsp_ca
        pem, _ = mint_cert(common_name, issuer.cert.subject, issuer.key, ca=False)
        return x509.load_pem_x509_certificate(pem.encode("utf-8"))

    return _make_leaf


@pytest.fixture()
def make_request(ocsp_ca: SigningCA, foreign_ca: SigningCA) -> RequestFactory:
    """Factory for DER OCSP requests, optionally nonced or naming the foreign issuer"""

    def _make_request(
        leaf: x509.Certificate,
        algorithm: hashes.HashAlgorithm | None = None,
        nonce: bytes | None = None,
        foreign: bool = False,
    ) -> bytes:
        issuer = (foreign_ca if foreign else ocsp_ca).cert
        builder = ocsp.OCSPRequestBuilder().add_certificate(leaf, issuer, algorithm or hashes.SHA1())
        if nonce is not None:
            builder = builder.add_extension(x509.OCSPNonce(nonce), critical=False)
        return builder.build().public_bytes(serialization.Encoding.DER)

    return _make_request


@pytest.fixture()
def ocsp_request_der(make_leaf: LeafFactory, make_request: RequestFactory) -> bytes:
    """A DER OCSP request about some leaf our CA issued"""
    return make_request(make_leaf("ocsp leaf"))


@pytest.fixture()
def respond() -> Responder:
    """Feed DER to the responder and hand back the parsed response"""

    async def _respond(der: bytes) -> ocsp.OCSPResponse:
        resp_der, _ = await build_ocsp_response(der)
        return ocsp.load_der_ocsp_response(resp_der)

    return _respond


@pytest_asyncio.fixture()
async def ocsp_client() -> AsyncGenerator[TestClient, None]:
    """An app carrying only the OCSP router, since the session app runs the cfssl backend"""
    from rasenmaeher_api.cert.cert_manager.ocsp import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1/ocsp")
    async with TestClient(app) as client:
        yield client
