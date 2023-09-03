"""mTLS fixtures"""
from typing import Tuple, Generator
import random
from pathlib import Path
import logging
import asyncio
import ssl

import pytest
import pytest_asyncio
import aiohttp
from OpenSSL import crypto  # FIXME: use cryptography instead of pyOpenSSL
from libpvarki.mtlshelp import get_ssl_context, get_session
from pytest_httpserver import HTTPServer


from rasenmaeher_api.web.api.product.views import sign_csr, get_ca

LOGGER = logging.getLogger(__name__)

# pylint: disable=W0621,R0801


@pytest.fixture(scope="module")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Module scoped event loop so we don't have to regenrate keys etc for every test"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


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
    ckp = crypto.PKey()
    LOGGER.debug("Generating keypair, this will take a moment")
    ckp.generate_key(crypto.TYPE_RSA, 4096)
    LOGGER.debug("Done")
    with privkeypath.open("wb") as fpntr:
        fpntr.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, ckp))
    with pubkeypath.open("wb") as fpntr:
        fpntr.write(crypto.dump_publickey(crypto.FILETYPE_PEM, ckp))
    return ckp


@pytest.fixture(scope="module")
def csrfile(datadir: Path, keypair: crypto.PKey) -> Path:
    """Generate CSR file"""
    csrpath = datadir / "public" / "mtlsclient.csr"
    req = crypto.X509Req()
    req.get_subject().CN = "localmaeher.pvarki.fi"
    req.add_extensions(
        [
            crypto.X509Extension(b"keyUsage", True, b"digitalSignature,nonRepudiation,keyEncipherment"),
            crypto.X509Extension(b"extendedKeyUsage", True, b"clientAuth"),
        ]
    )
    req.set_pubkey(keypair)
    req.sign(keypair, "sha256")
    with csrpath.open("wb") as fpntr:
        fpntr.write(crypto.dump_certificate_request(crypto.FILETYPE_PEM, req))

    return csrpath


@pytest_asyncio.fixture(scope="module")
async def cafile(datadir: Path) -> Path:
    """Get the CA chain from CFSSL and save"""
    capath = datadir / "ca_public" / "mtlsca.pem"
    cadir = capath.parent
    cadir.mkdir(parents=True)
    capem = (await get_ca()).replace("\\n", "\n")
    LOGGER.debug("capem={}".format(capem))
    capath.write_text(capem)
    return capath


@pytest_asyncio.fixture(scope="module")
async def mtlsfiles(csrfile: Path, cafile: Path) -> Tuple[Path, Path, Path]:
    """Return cert, key and ca cert paths, this will sign the CSR again every time due to fixture scoping issues"""
    privkeypath = csrfile.parent.parent / "private" / "mtlsclient.key"
    assert privkeypath.exists()
    certpath = csrfile.parent / "mtlsclient.pem"
    certpem = (await sign_csr(csrfile.read_text())).replace("\\n", "\n")
    LOGGER.debug("certpem={}".format(certpem))
    certpath.write_text(certpem)
    return certpath, privkeypath, cafile


@pytest_asyncio.fixture(scope="module")
async def servertlsfiles(datadir: Path) -> Tuple[Path, Path]:
    """Generate a keypair, CSR"""
    privkeypath = datadir / "private" / "mtlsserver.key"
    pubkeypath = datadir / "public" / "mtlsserver.pub"
    certpath = datadir / "public" / "mtlsserver.pem"
    ckp = crypto.PKey()
    LOGGER.debug("Generating keypair, this will take a moment")
    ckp.generate_key(crypto.TYPE_RSA, 4096)
    LOGGER.debug("Done")
    with privkeypath.open("wb") as fpntr:
        fpntr.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, ckp))
    with pubkeypath.open("wb") as fpntr:
        fpntr.write(crypto.dump_publickey(crypto.FILETYPE_PEM, ckp))
    csrpath = datadir / "public" / "mtlsserver.csr"
    req = crypto.X509Req()
    req.get_subject().CN = "fake.localmaeher.pvarki.fi"
    req.add_extensions(
        [
            crypto.X509Extension(b"keyUsage", True, b"digitalSignature,nonRepudiation,keyEncipherment"),
        ]
    )
    req.set_pubkey(ckp)
    req.sign(ckp, "sha256")
    with csrpath.open("wb") as fpntr:
        fpntr.write(crypto.dump_certificate_request(crypto.FILETYPE_PEM, req))
    certpem = (await sign_csr(csrpath.read_text())).replace("\\n", "\n")
    certpath.write_text(certpem)

    return certpath, privkeypath


@pytest.fixture(scope="module")
def httpserver_ssl_context(servertlsfiles: Tuple[Path, Path], cafile: Path) -> ssl.SSLContext:
    """Create SSL context for pytest-httpserver"""
    ssl_ctx = get_ssl_context(servertlsfiles, cafile.parent)
    ssl_ctx.verify_mode = ssl.CERT_REQUIRED
    return ssl_ctx


@pytest.fixture()
def mtlsclient(mtlsfiles: Tuple[Path, Path, Path]) -> aiohttp.ClientSession:
    """fixture for client session with correct ssl context"""
    certpath, privkeypath, capath = mtlsfiles
    client = get_session((certpath, privkeypath), capath.parent)
    return client


@pytest.fixture(scope="module")
def make_httpserver(httpserver_ssl_context: ssl.SSLContext) -> Generator[HTTPServer, None, None]:
    """Module scoped server fixture"""
    port = random.randint(10000, 64000)  # nosec
    server = HTTPServer(host="fake.localmaeher.pvarki.fi", port=port, ssl_context=httpserver_ssl_context)
    server.start()  # type: ignore
    yield server
    server.clear()  # type: ignore
    if server.is_running():
        server.stop()  # type: ignore
