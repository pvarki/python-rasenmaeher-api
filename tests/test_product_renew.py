"""Test product certificate renewal"""

import ipaddress
import logging
from collections.abc import Callable

import pytest
from async_asgi_testclient import TestClient  # type: ignore[import-untyped]
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from rasenmaeher_api.web.api.product import views
from tests.cert.helpers import invalidate_signature, make_key_usage, make_name

LOGGER = logging.getLogger(__name__)
PRODUCT = "fake.localmaeher.dev.pvarki.fi"
OTHER_PRODUCT = "interoptest.localmaeher.dev.pvarki.fi"


def product_csr(
    common_name: str = PRODUCT,
    *,
    key: ec.EllipticCurvePrivateKey | rsa.RSAPrivateKey | None = None,
    subject: x509.Name | None = None,
    names: list[x509.GeneralName] | None = None,
    ca: bool = False,
    key_usage: x509.KeyUsage | None = None,
    ext_key_usage: list[x509.ObjectIdentifier] | None = None,
    extra: x509.ExtensionType | None = None,
) -> str:
    """A CSR shaped like the one a product sends when its certificate is first issued"""
    builder = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(subject or make_name(common_name))
        .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
        .add_extension(
            x509.ExtendedKeyUsage(ext_key_usage or [ExtendedKeyUsageOID.CLIENT_AUTH, ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=True,
        )
        .add_extension(key_usage or make_key_usage(digital_signature=True), critical=True)
        .add_extension(
            x509.SubjectAlternativeName(names if names is not None else [x509.DNSName(common_name)]), critical=False
        )
    )
    if extra is not None:
        builder = builder.add_extension(extra, critical=False)
    signer = key or ec.generate_private_key(ec.SECP256R1())
    return builder.sign(signer, hashes.SHA256()).public_bytes(serialization.Encoding.PEM).decode("utf-8")


async def renew(client: TestClient, csr: str, caller: str = PRODUCT) -> x509.Certificate | None:
    """POST the renewal as the given caller, return the issued leaf or None when refused"""
    client.headers.update({"X-ClientCert-DN": f"CN={caller},O=N/A"})
    resp = await client.post("/api/v1/product/renew_csr", json={"csr": csr})
    if resp.status_code == 200:
        return x509.load_pem_x509_certificates(resp.json()["certificate"].encode("utf-8"))[0]
    assert resp.status_code == 403
    assert resp.json()["detail"] == "Renewal not allowed"
    return None


def renew_records(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    """The audit records written for renewals"""
    return [record for record in caplog.records if record.__dict__.get("event.action") == "product_cert_renew"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "csr_factory",
    [
        pytest.param(product_csr, id="ec"),
        pytest.param(
            lambda: product_csr(
                key=rsa.generate_private_key(public_exponent=65537, key_size=2048),
                key_usage=make_key_usage(digital_signature=True, key_encipherment=True, data_encipherment=True),
            ),
            id="rsa",
        ),
    ],
)
async def test_product_renews_own_certificate(
    dbinit_func: None, unauth_client: TestClient, caplog: pytest.LogCaptureFixture, csr_factory: Callable[[], str]
) -> None:
    """A product renewing its own certificate gets it signed, and the success is audited"""
    _ = dbinit_func
    with caplog.at_level("AUDIT"):
        cert = await renew(unauth_client, csr_factory())
    assert cert is not None
    assert cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value == PRODUCT
    records = renew_records(caplog)
    assert len(records) == 1
    assert records[0].__dict__["event.outcome"] == "success"
    assert records[0].__dict__["user.name"] == PRODUCT


REFUSALS: list[tuple[str, Callable[[], str], str]] = [
    ("callsigndude", lambda: product_csr("callsigndude"), "NOT_A_PRODUCT"),
    (PRODUCT, lambda: product_csr(OTHER_PRODUCT), "CSR_SUBJECT_MISMATCH"),
    (
        PRODUCT,
        lambda: product_csr(
            subject=x509.Name(
                [
                    x509.NameAttribute(NameOID.COMMON_NAME, PRODUCT),
                    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "x"),
                ]
            )
        ),
        "CSR_SUBJECT_MISMATCH",
    ),
    (
        PRODUCT,
        lambda: product_csr(
            subject=x509.Name(
                [x509.NameAttribute(NameOID.COMMON_NAME, PRODUCT), x509.NameAttribute(NameOID.COMMON_NAME, PRODUCT)]
            )
        ),
        "CSR_SUBJECT_MISMATCH",
    ),
    (PRODUCT, lambda: product_csr(names=[x509.DNSName(PRODUCT), x509.DNSName(OTHER_PRODUCT)]), "CSR_SUBJECT_MISMATCH"),
    (
        PRODUCT,
        lambda: product_csr(names=[x509.DNSName(PRODUCT), x509.IPAddress(ipaddress.ip_address("192.0.2.1"))]),
        "CSR_SUBJECT_MISMATCH",
    ),
    (PRODUCT, lambda: product_csr(ca=True), "CSR_EXTENSION_NOT_ALLOWED"),
    (
        PRODUCT,
        lambda: product_csr(
            extra=x509.UnrecognizedExtension(x509.ObjectIdentifier("1.3.6.1.4.1.99999.1"), b"\x05\x00")
        ),
        "CSR_EXTENSION_NOT_ALLOWED",
    ),
    (
        PRODUCT,
        lambda: product_csr(ext_key_usage=[ExtendedKeyUsageOID.CLIENT_AUTH, ExtendedKeyUsageOID.CODE_SIGNING]),
        "CSR_USAGE_NOT_ALLOWED",
    ),
    (
        PRODUCT,
        lambda: product_csr(key_usage=make_key_usage(digital_signature=True, key_cert_sign=True)),
        "CSR_USAGE_NOT_ALLOWED",
    ),
    (
        PRODUCT,
        lambda: product_csr(
            ext_key_usage=[ExtendedKeyUsageOID.CLIENT_AUTH, ExtendedKeyUsageOID.ANY_EXTENDED_KEY_USAGE]
        ),
        "CSR_INVALID",
    ),
    (PRODUCT, lambda: invalidate_signature(product_csr()), "CSR_SIGNATURE_INVALID"),
    (PRODUCT, lambda: "not a CSR", "CSR_INVALID"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "caller,csr_factory,error_code",
    REFUSALS,
    ids=[
        "caller-not-a-product",
        "other-common-name",
        "extra-subject-attribute",
        "two-common-names",
        "extra-dns-name",
        "ip-address-name",
        "ca-constraint",
        "unknown-extension",
        "code-signing-usage",
        "cert-sign-usage",
        "unknown-extended-usage",
        "invalid-signature",
        "not-a-csr",
    ],
)
async def test_renewal_refused(
    unauth_client: TestClient,
    caplog: pytest.LogCaptureFixture,
    caller: str,
    csr_factory: Callable[[], str],
    error_code: str,
) -> None:
    """Renewal is only for the calling product's own name and usages, and every refusal is audited"""
    with caplog.at_level("AUDIT"):
        assert await renew(unauth_client, csr_factory(), caller) is None
    records = renew_records(caplog)
    assert len(records) == 1
    assert records[0].__dict__["event.outcome"] == "failure"
    assert records[0].__dict__["error_code"] == error_code
    assert records[0].__dict__["user.name"] == caller


@pytest.mark.asyncio
async def test_renewal_refused_by_signer(
    unauth_client: TestClient, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A CSR the signing backend refuses is a refused renewal"""

    async def refuse(csr: str) -> str:
        raise ValueError("refused")

    monkeypatch.setattr(views, "sign_csr", refuse)
    with caplog.at_level("AUDIT"):
        assert await renew(unauth_client, product_csr()) is None
    records = renew_records(caplog)
    assert len(records) == 1
    assert records[0].__dict__["error_code"] == "SIGNING_REFUSED"
