"""Test the cert-manager signing flow and its no-op revocation surface

Nothing here talks to a cluster. The CertificateRequest builder is exercised for
real, since building is pure client-side model construction, and only the four
async I/O methods are replaced by in-memory doubles (see FakeK8s).
"""

import base64
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any, NamedTuple
from unittest.mock import AsyncMock

import cryptography.x509
import pytest
from cloudcoil.errors import APIError, ResourceConflict, ResourceNotFound, WaitTimeout
from cloudcoil.models.cert_manager.v1 import CertificateRequest, CertificateRequestStatus
from cryptography.x509.oid import ExtendedKeyUsageOID

from rasenmaeher_api.cert.cert_manager import private
from rasenmaeher_api.cert.cert_manager.base import CertManagerError
from rasenmaeher_api.cert.cert_manager.names import cr_name
from rasenmaeher_api.rmsettings import RMSettings
from tests.cert.helpers import CsrFactory, FakePKI, KeyUsageFactory

LOGGER = logging.getLogger(__name__)

NAMESPACE = "test-ns"
ISSUER_NAME = "test-issuer"
ISSUER_KIND = "ClusterIssuer"
ISSUER_GROUP = "cert-manager.io"
DURATION = "8760h"


def _b64_pem(cert_pem: str) -> str:
    """Base64 of a PEM, the shape cert-manager writes into status.certificate"""
    return base64.b64encode(cert_pem.encode("utf-8")).decode("ascii")


def _subjects(pem: str) -> list[str]:
    """Subject DNs of every cert in a PEM blob, in order"""
    return [cert.subject.rfc4514_string() for cert in cryptography.x509.load_pem_x509_certificates(pem.encode("utf-8"))]


def _csr_subject(csr_pem: str) -> cryptography.x509.Name:
    """Subject of a PEM CSR, for comparing against a round-tripped copy"""
    return cryptography.x509.load_pem_x509_csr(csr_pem.encode("utf-8")).subject


def _build_cr(name: str = "rm-test-abc", namespace: str = NAMESPACE, request_b64: str = "Zm9v") -> CertificateRequest:
    """A CertificateRequest as cert-manager would have stored it, built by the real builder"""
    return (
        CertificateRequest.builder()
        .metadata(lambda metadata: metadata.name(name).namespace(namespace))
        .spec(
            lambda spec: (
                spec.duration(DURATION)
                .usages(["client auth"])
                .request(request_b64)
                .issuer_ref(lambda issuer_ref: issuer_ref.name(ISSUER_NAME).kind(ISSUER_KIND).group(ISSUER_GROUP))
            )
        )
    ).build()


class FakeK8s(NamedTuple):
    """What the patched CertificateRequest calls recorded, plus the status they serve"""

    created: list[CertificateRequest]
    deletes: list[tuple[str, str | None]]
    waits: list[float | None]
    predicates: list[Callable[..., Any]]
    status: CertificateRequestStatus


@pytest.fixture()
def fake_k8s(monkeypatch: pytest.MonkeyPatch, pki: FakePKI) -> FakeK8s:
    """Patch the four CertificateRequest I/O methods on the happy path.

    Plain closures rather than AsyncMock because a mock on a class attribute never
    receives ``self``, and the create recording is how tests inspect the built CR.
    To make a call fail or return something else, override that one method:

        monkeypatch.setattr(CertificateRequest, "async_create", AsyncMock(side_effect=APIError("boom")))
    """
    recorded = FakeK8s([], [], [], [], CertificateRequestStatus(certificate=_b64_pem(pki.leaf)))

    async def _async_create(self: CertificateRequest, dry_run: bool = False) -> CertificateRequest:
        recorded.created.append(self)
        return self  # cert-manager has not populated status yet at create time

    async def _async_get(name: str, namespace: str | None = None) -> CertificateRequest:
        if not recorded.created:
            raise ResourceNotFound(f"{namespace}/{name}")
        return recorded.created[-1].model_copy(update={"status": recorded.status})

    async def _async_delete(name: str, namespace: str | None = None, **kwargs: Any) -> CertificateRequest:
        recorded.deletes.append((name, namespace))
        return _build_cr(name=name, namespace=namespace or NAMESPACE)

    async def _async_wait_for(
        self: CertificateRequest, predicate: Callable[..., Any], timeout: float | None = None
    ) -> CertificateRequest:
        recorded.waits.append(timeout)
        recorded.predicates.append(predicate)
        return self.model_copy(update={"status": recorded.status})

    monkeypatch.setattr(CertificateRequest, "async_create", _async_create)
    monkeypatch.setattr(CertificateRequest, "async_get", _async_get)
    monkeypatch.setattr(CertificateRequest, "async_delete", _async_delete)
    monkeypatch.setattr(CertificateRequest, "async_wait_for", _async_wait_for)
    return recorded


@pytest.fixture()
def cm_settings(monkeypatch: pytest.MonkeyPatch, ca_chain_path: Path) -> RMSettings:
    """cert-manager settings with the CA bundle pointed at the test data.

    Patches attributes on the live singleton, the same approach the root conftest uses.
    """
    settings = RMSettings.singleton()
    monkeypatch.setattr(settings, "cert_manager_namespace", NAMESPACE)
    monkeypatch.setattr(settings, "cert_manager_issuer_name", ISSUER_NAME)
    monkeypatch.setattr(settings, "cert_manager_issuer_kind", ISSUER_KIND)
    monkeypatch.setattr(settings, "cert_manager_issuer_group", ISSUER_GROUP)
    monkeypatch.setattr(settings, "cert_manager_cert_duration", DURATION)
    monkeypatch.setattr(settings, "cert_manager_timeout", 1.0)
    monkeypatch.setattr(settings, "cert_manager_ca_bundle_path", str(ca_chain_path))
    return settings


# _csr_pem_to_b64
def test_csr_to_b64_round_trips(csr_pem: str) -> None:
    """Decoding the result yields a PEM CSR block cert-manager can parse"""
    decoded = base64.b64decode(private._csr_pem_to_b64(csr_pem))
    assert decoded.startswith(b"-----BEGIN CERTIFICATE REQUEST-----")
    assert cryptography.x509.load_pem_x509_csr(decoded).subject == _csr_subject(csr_pem)


# _csr_common_name
def test_common_name_extracted(mint_csr: CsrFactory) -> None:
    """The CN is found whether or not it is the first subject attribute"""
    assert private._csr_common_name(mint_csr("example")) == "example"
    assert private._csr_common_name(mint_csr("example", organization="Acme")) == "example"


def test_common_name_absent_is_none(mint_csr: CsrFactory) -> None:
    """A CSR with an empty subject yields None, which cr_name turns into anon"""
    assert private._csr_common_name(mint_csr(None)) is None


# _csr_usages
def test_usages_empty_without_extensions(csr_pem: str) -> None:
    """A CSR with no KeyUsage or ExtendedKeyUsage extensions derives no usages"""
    assert private._csr_usages(csr_pem) == []


def test_key_usage_flags_mapped(mint_csr: CsrFactory, key_usage: KeyUsageFactory) -> None:
    """KeyUsage bits map to their cert-manager names, dependent flags last"""
    plain = mint_csr("example", key_usage(digital_signature=True, key_encipherment=True))
    assert private._csr_usages(plain) == ["digital signature", "key encipherment"]
    agreement_only = mint_csr("example", key_usage(key_agreement=True))
    assert private._csr_usages(agreement_only) == ["key agreement"]
    agreement = mint_csr("example", key_usage(key_agreement=True, encipher_only=True, decipher_only=True))
    assert private._csr_usages(agreement) == ["key agreement", "encipher only", "decipher only"]


def test_ext_key_usage_oids_mapped(mint_csr: CsrFactory) -> None:
    """Known ExtendedKeyUsage OIDs map to their names, unknown ones are dropped"""
    known = mint_csr("example", ext_key_usage=[ExtendedKeyUsageOID.SERVER_AUTH])
    assert private._csr_usages(known) == ["server auth"]
    unknown = mint_csr("example", ext_key_usage=[ExtendedKeyUsageOID.KERBEROS_PKINIT_KDC])
    assert private._csr_usages(unknown) == []


# sign_csr
@pytest.mark.asyncio(loop_scope="function")
async def test_sign_csr_returns_bundle(fake_k8s: FakeK8s, cm_settings: RMSettings, csr_pem: str) -> None:
    """The issued leaf comes back with the CA chain appended and the root stripped"""
    _ = cm_settings
    out = await private.sign_csr(csr_pem)
    assert _subjects(out) == ["CN=test leaf", "CN=localmaeher,OU=RASENMAEHER"]
    assert len(fake_k8s.created) == 1
    assert fake_k8s.waits == [1.0]


@pytest.mark.asyncio(loop_scope="function")
async def test_sign_csr_without_bundle(fake_k8s: FakeK8s, cm_settings: RMSettings, csr_pem: str) -> None:
    """bundle=False returns the leaf alone"""
    _ = cm_settings
    out = await private.sign_csr(csr_pem, bundle=False)
    assert _subjects(out) == ["CN=test leaf"]


@pytest.mark.asyncio(loop_scope="function")
async def test_sign_csr_builds_expected_cr(fake_k8s: FakeK8s, cm_settings: RMSettings, csr_pem: str) -> None:
    """Name, namespace, duration, issuerRef and the default usages all reach the CR"""
    _ = cm_settings
    await private.sign_csr(csr_pem, bundle=False)
    created = fake_k8s.created[0]
    assert created.metadata is not None
    assert created.metadata.name == cr_name(csr_pem, "test leaf")
    assert created.metadata.namespace == NAMESPACE
    assert created.spec is not None
    assert created.spec.duration == DURATION
    assert created.spec.issuer_ref.name == ISSUER_NAME
    assert created.spec.issuer_ref.kind == ISSUER_KIND
    assert created.spec.issuer_ref.group == ISSUER_GROUP
    # A CSR with no usage extensions falls back to the client-auth trio
    assert created.spec.usages == ["digital signature", "key encipherment", "client auth"]


@pytest.mark.asyncio(loop_scope="function")
async def test_sign_csr_honours_csr_usages(
    fake_k8s: FakeK8s, cm_settings: RMSettings, mint_csr: CsrFactory, key_usage: KeyUsageFactory
) -> None:
    """Usages derived from the CSR are sent instead of the default trio"""
    _ = cm_settings
    csr = mint_csr(
        "usage leaf",
        key_usage(digital_signature=True),
        [ExtendedKeyUsageOID.CLIENT_AUTH],
    )
    await private.sign_csr(csr, bundle=False)
    created = fake_k8s.created[0]
    assert created.spec is not None
    assert created.spec.usages == ["digital signature", "client auth"]


@pytest.mark.asyncio(loop_scope="function")
async def test_sign_csr_conflict_polls_existing(
    fake_k8s: FakeK8s, cm_settings: RMSettings, csr_pem: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A ResourceConflict on create is re-raised past the APIError wrapper so _upsert_cr
    can fall back to the CertificateRequest cert-manager already issued.
    """
    _ = cm_settings
    existing = _build_cr().model_copy(update={"status": fake_k8s.status})
    get_mock = AsyncMock(return_value=existing)
    monkeypatch.setattr(CertificateRequest, "async_create", AsyncMock(side_effect=ResourceConflict("exists")))
    monkeypatch.setattr(CertificateRequest, "async_get", get_mock)

    out = await private.sign_csr(csr_pem, bundle=False)

    assert _subjects(out) == ["CN=test leaf"]
    assert fake_k8s.created == []  # nothing new was created
    # The fallback fetched the CR under the name the CSR derives, rather than erroring out
    assert get_mock.await_args_list[0].kwargs == {
        "name": cr_name(csr_pem, "test leaf"),
        "namespace": NAMESPACE,
    }


@pytest.mark.asyncio(loop_scope="function")
async def test_sign_csr_api_error_wrapped(
    fake_k8s: FakeK8s, cm_settings: RMSettings, csr_pem: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An APIError on create surfaces as CertManagerError, not a cloudcoil type"""
    _ = cm_settings, fake_k8s
    monkeypatch.setattr(CertificateRequest, "async_create", AsyncMock(side_effect=APIError("boom")))
    with pytest.raises(CertManagerError):
        await private.sign_csr(csr_pem)


@pytest.mark.asyncio(loop_scope="function")
async def test_sign_csr_timeout_wrapped(
    fake_k8s: FakeK8s, cm_settings: RMSettings, csr_pem: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A WaitTimeout becomes CertManagerError naming the namespace, name and timeout"""
    _ = cm_settings, fake_k8s
    monkeypatch.setattr(CertificateRequest, "async_wait_for", AsyncMock(side_effect=WaitTimeout("did not issue")))
    with pytest.raises(CertManagerError, match=NAMESPACE):
        await private.sign_csr(csr_pem)


@pytest.mark.parametrize("status", (None, CertificateRequestStatus(certificate=None)))
@pytest.mark.asyncio(loop_scope="function")
async def test_sign_csr_incomplete_status_raises(
    fake_k8s: FakeK8s,
    cm_settings: RMSettings,
    csr_pem: str,
    monkeypatch: pytest.MonkeyPatch,
    status: CertificateRequestStatus | None,
) -> None:
    """A CR with no status, or a status with no certificate, raises RuntimeError"""
    _ = cm_settings, fake_k8s
    incomplete = _build_cr().model_copy(update={"status": status})
    monkeypatch.setattr(CertificateRequest, "async_get", AsyncMock(return_value=incomplete))
    with pytest.raises(RuntimeError):
        await private.sign_csr(csr_pem)


# --- _delete_cr ------------------------------------------------------------------------
@pytest.mark.asyncio(loop_scope="function")
async def test_delete_cr_true_when_present(fake_k8s: FakeK8s) -> None:
    """Deleting an existing CR reports True and records the name and namespace"""
    assert await private._delete_cr("rm-gone", NAMESPACE) is True
    assert fake_k8s.deletes == [("rm-gone", NAMESPACE)]


@pytest.mark.asyncio(loop_scope="function")
async def test_delete_cr_false_when_missing(fake_k8s: FakeK8s, monkeypatch: pytest.MonkeyPatch) -> None:
    """ResourceNotFound is swallowed and reported as False"""
    _ = fake_k8s
    monkeypatch.setattr(CertificateRequest, "async_delete", AsyncMock(side_effect=ResourceNotFound("gone")))
    assert await private._delete_cr("rm-gone", NAMESPACE) is False


# --- validate_reason -------------------------------------------------------------------
@pytest.mark.parametrize(
    "reason, expected",
    (
        ("key_compromise", cryptography.x509.ReasonFlags.key_compromise),
        ("keyCompromise", cryptography.x509.ReasonFlags.key_compromise),
        (cryptography.x509.ReasonFlags.unspecified, cryptography.x509.ReasonFlags.unspecified),
    ),
)
def test_validate_reason_resolves(reason: private.ReasonTypes, expected: cryptography.x509.ReasonFlags) -> None:
    """Reasons resolve from the flag name, its string value, or a flag itself"""
    assert private.validate_reason(reason) == expected


@pytest.mark.parametrize("reason, expected_error", (("nosuchreason", ValueError), (42, TypeError)))
def test_validate_reason_rejects(reason: Any, expected_error: type[Exception]) -> None:
    """An unresolvable string raises ValueError, a wrong type raises TypeError"""
    with pytest.raises(expected_error):
        private.validate_reason(reason)


# --- the deliberate no-ops -------------------------------------------------------------
@pytest.mark.asyncio(loop_scope="function")
async def test_revoke_is_noop_after_validating_reason() -> None:
    """Both revoke helpers validate the reason and otherwise do nothing"""
    await private.revoke_pem("pem", "key_compromise")
    await private.revoke_serial("123", "akid", "key_compromise")
    with pytest.raises(ValueError):
        await private.revoke_pem("pem", "nosuchreason")


@pytest.mark.parametrize(
    "coro_name, args",
    (
        ("sign_ocsp", ("pem",)),
        ("certadd_pem", ("pem",)),
        ("dump_crlfiles", ()),
        ("refresh_ocsp", ()),
    ),
)
@pytest.mark.asyncio(loop_scope="function")
async def test_unsupported_operations_return_none(coro_name: str, args: tuple[Any, ...]) -> None:
    """The cfssl-only surface is present but returns None under cert-manager"""
    assert await getattr(private, coro_name)(*args) is None
