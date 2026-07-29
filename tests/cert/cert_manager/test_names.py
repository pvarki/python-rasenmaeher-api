"""Test the k8s resource name derivation for CertificateRequests"""

import logging
import re

import pytest

from rasenmaeher_api.cert.cert_manager.names import cr_name, cr_name_for_serial

LOGGER = logging.getLogger(__name__)

# Both helpers treat their input as an opaque string to hash, so no real CSR is needed
CSR = "-----BEGIN CERTIFICATE REQUEST-----\nZmFrZQ==\n-----END CERTIFICATE REQUEST-----\n"
CSR_DIGEST = "6a4eb91f0f"
SERIAL = "605615835623014850894526155906348132164161085188"
SERIAL_DIGEST = "4c84878cdc"
OTHER_CSR = "-----BEGIN CERTIFICATE REQUEST-----\nb3RoZXI=\n-----END CERTIFICATE REQUEST-----\n"
OTHER_CSR_DIGEST = "fc8a2f2d40"
OTHER_SERIAL = "162558639717621340102045078477713279414723498107"
OTHER_SERIAL_DIGEST = "463c091c8d"

# RFC 1123 subdomain, the rule k8s applies to CertificateRequest names
K8S_NAME_RE = re.compile(r"^[a-z0-9]([-a-z0-9]*[a-z0-9])?$")
K8S_NAME_MAX = 253

NASTY_CALLSIGNS = (
    "ANON",
    "Cat Moose",
    "crane.four",
    "under_score",
    "!!!",
    "-leading-and-trailing-",
    "ä" * 60,
    "x" * 200,
)


def test_cr_name_shape() -> None:
    """A plain lowercase callsign yields rm-<callsign>-<10 hex digest>"""
    out = cr_name(CSR, "mongoose")
    assert out == f"rm-mongoose-{CSR_DIGEST}"


@pytest.mark.parametrize("callsign", (None, ""))
def test_missing_callsign_becomes_anon(callsign: str | None) -> None:
    """Both None and an empty callsign fall back to the anon identifier"""
    out = cr_name(CSR, callsign)
    assert out == f"rm-anon-{CSR_DIGEST}"


def test_callsign_lowercased() -> None:
    """Uppercase callsigns are folded to lowercase, k8s names cannot hold capitals"""
    out = cr_name(CSR, "MONGOOSE")
    assert out == f"rm-mongoose-{CSR_DIGEST}"


@pytest.mark.parametrize(
    "callsign, expected_slug",
    (
        ("Cat Moose", "cat-moose"),
        ("crane.four", "crane-four"),
        ("under_score", "under-score"),
    ),
)
def test_illegal_characters_replaced(callsign: str, expected_slug: str) -> None:
    """Anything outside [a-z0-9-] becomes a hyphen"""
    out = cr_name(CSR, callsign)
    assert out == f"rm-{expected_slug}-{CSR_DIGEST}"


def test_slug_truncated() -> None:
    """The slug contributes at most 40 characters regardless of callsign length"""
    out = cr_name(CSR, "x" * 200)
    assert out == f"rm-{'x' * 40}-{CSR_DIGEST}"


@pytest.mark.parametrize("callsign", NASTY_CALLSIGNS)
def test_cr_name_is_valid_k8s_name(callsign: str) -> None:
    """Whatever goes in, the result matches K8S_NAME_RE and fits K8S_NAME_MAX"""
    out = cr_name(CSR, callsign)
    assert len(out) <= K8S_NAME_MAX
    assert K8S_NAME_RE.fullmatch(out)


def test_cr_name_varies_with_csr() -> None:
    """One callsign with two different CSRs gets two different names"""
    callsign = "mongoose"
    out = cr_name(CSR, callsign)
    other_out = cr_name(OTHER_CSR, callsign)
    assert out != other_out


def test_serial_name_shape() -> None:
    """A serial yields the fixed rm-serial- prefix plus a 10 hex digest"""
    out = cr_name_for_serial(SERIAL)
    assert out == f"rm-serial-{SERIAL_DIGEST}"


def test_serial_name_deterministic() -> None:
    """The same serial always derives the same name, revoke flows depend on it"""
    expected = f"rm-serial-{SERIAL_DIGEST}"
    out = cr_name_for_serial(SERIAL)
    assert out == expected
    out_again = cr_name_for_serial(SERIAL)
    assert out_again == expected


def test_serial_name_varies_with_serial() -> None:
    """Different serials derive different names"""
    out = cr_name_for_serial(SERIAL)
    assert out == f"rm-serial-{SERIAL_DIGEST}"
    other_out = cr_name_for_serial(OTHER_SERIAL)
    assert other_out == f"rm-serial-{OTHER_SERIAL_DIGEST}"


@pytest.mark.parametrize("serial", ("", "0A:1B:2C", "deadbeef", "1234567890" * 10))
def test_serial_name_is_valid_k8s_name(serial: str) -> None:
    """Any serial format still produces a valid k8s name"""
    out = cr_name(CSR, serial)
    assert len(out) <= K8S_NAME_MAX
    assert K8S_NAME_RE.fullmatch(out)
