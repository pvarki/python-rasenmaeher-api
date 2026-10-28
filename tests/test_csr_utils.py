"""Test CSR subject verification"""

from pathlib import Path

import pytest
from libpvarki.mtlshelp.csr import async_create_client_csr, async_create_keypair, async_create_server_csr

from rasenmaeher_api.web.api.utils.csr_utils import verify_csr


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "subject,callsign,expected",
    [
        pytest.param({"CN": "csr_test"}, "csr_test", True, id="exact-match"),
        pytest.param({"CN": "csr_test2"}, "csr_test", False, id="callsign-prefix-of-cn"),
        pytest.param({"CN": "csr_test", "O": "x"}, "csr_test", False, id="extra-subject-attribute"),
        pytest.param({"CN": "a,b"}, "a,b", True, id="rfc4514-escaped-char"),
    ],
)
async def test_verify_csr_subject(subject: dict[str, str], callsign: str, expected: bool, nice_tmpdir: str) -> None:
    """Only a CN-only subject exactly matching the callsign passes"""
    tempdir = Path(nice_tmpdir)
    ckp = await async_create_keypair(tempdir / "user.key", tempdir / "user.pub")
    csrpem = await async_create_client_csr(ckp, tempdir / "user.csr", subject)
    assert verify_csr(csrpem, callsign) is expected


@pytest.mark.asyncio
async def test_verify_csr_rejects_server_csr(nice_tmpdir: str) -> None:
    """A user callsign may not request server auth"""
    tempdir = Path(nice_tmpdir)
    ckp = await async_create_keypair(tempdir / "user.key", tempdir / "user.pub")
    csrpem = await async_create_server_csr(ckp, tempdir / "user.csr", ["csr_test"])
    assert verify_csr(csrpem, "csr_test") is False
