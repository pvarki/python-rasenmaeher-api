"""mTLS fixtures"""
from typing import Tuple
from pathlib import Path
import logging

import pytest
import pytest_asyncio
import aiohttp
from OpenSSL import crypto  # FIXME: use cryptography instead of pyOpenSSL
from libpvarki.mtlshelp import get_session
from libpvarki.mtlshelp.csr import create_keypair, create_client_csr


from rasenmaeher_api.cfssl.private import sign_csr


LOGGER = logging.getLogger(__name__)

# pylint: disable=W0621,R0801


@pytest.fixture(scope="module")
def datadir(nice_tmpdir_mod: str) -> Path:
    """Make sure we have a well known directory structure"""
    datadir = Path(nice_tmpdir_mod) / "persistent"
    datadir.mkdir(parents=True)
    privdir = datadir / "private"
    pubdir = datadir / "public"
    privdir.mkdir()
    pubdir.mkdir()
    return datadir


@pytest.fixture(scope="module")
def keypair(datadir: Path) -> crypto.PKey:
    """Generate a keypair"""
    privkeypath = datadir / "private" / "mtlsclient.key"
    pubkeypath = datadir / "public" / "mtlsclient.pub"
    ckp = create_keypair(privkeypath, pubkeypath)
    return ckp


@pytest.fixture(scope="module")
def csrfile(datadir: Path, keypair: crypto.PKey) -> Path:
    """Generate CSR file"""
    csrpath = datadir / "public" / "mtlsclient.csr"
    create_client_csr(keypair, csrpath, {"CN": "fake.localmaeher.pvarki.fi"})
    return csrpath


@pytest_asyncio.fixture(scope="module")
async def mtlsfiles(csrfile: Path) -> Tuple[Path, Path]:
    """Return cert, key and ca cert paths, this will sign the CSR again every time due to fixture scoping issues"""
    privkeypath = csrfile.parent.parent / "private" / "mtlsclient.key"
    assert privkeypath.exists()
    certpath = csrfile.parent / "mtlsclient.pem"
    certpem = (await sign_csr(csrfile.read_text())).replace("\\n", "\n")
    LOGGER.debug("certpem={}".format(certpem))
    certpath.write_text(certpem)
    return certpath, privkeypath


@pytest.fixture()
def mtlsclient(mtlsfiles: Tuple[Path, Path]) -> aiohttp.ClientSession:
    """fixture for client session with correct ssl context"""
    client = get_session(mtlsfiles)
    return client
