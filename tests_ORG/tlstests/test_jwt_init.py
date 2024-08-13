"""JWT init tests"""
from typing import Generator, Tuple
import logging
from pathlib import Path
import uuid

import pytest
from multikeyjwt import Issuer, Verifier
from libadvian.testhelpers import nice_tmpdir  # pylint: disable=W0611
from async_asgi_testclient import TestClient  # pylint: disable=import-error

from rasenmaeher_api.jwtinit import check_public_keys, check_private_key, check_jwt_init, jwt_init, resolve_pubkeydir

LOGGER = logging.getLogger(__name__)


# pylint: disable=W0621


@pytest.fixture()
def empty_datadirs(nice_tmpdir: str, monkeypatch: pytest.MonkeyPatch) -> Generator[Tuple[Path, Path], None, None]:
    """Create fresh datadirs and set the environments"""
    datadir = Path(nice_tmpdir) / "data"
    arkikeys = datadir / "pvarki" / "publickeys"
    arkikeys.mkdir(parents=True)
    privdir = datadir / "private"
    privdir.mkdir(parents=True, mode=0o760)
    privkeypath = privdir / "rm_jwtsign.key"
    pubkeydir = datadir / "public"
    pubkeydir.mkdir(parents=True)
    with monkeypatch.context() as mpatch:
        mpatch.setattr(Issuer, "_singleton", None)
        mpatch.setattr(Verifier, "_singleton", None)
        mpatch.setenv("JWT_PUBKEY_PATH", str(pubkeydir))
        mpatch.setenv("JWT_PRIVKEY_PATH", str(privkeypath))
        mpatch.setenv("PVARKI_PUBLICKEYS_PATH", str(arkikeys))  # this is probably too late already
        mpatch.setenv("TILAUSPALVELU_JWT", "")
        yield privdir, pubkeydir


def test_tilaupalvelu_key() -> None:
    """Test that default env has copied tilauspalvelu key"""
    assert check_public_keys()
    tppath = resolve_pubkeydir() / "tilauspalvelu.pub"
    assert tppath.exists()


def test_empty_response(empty_datadirs: Tuple[Path, Path]) -> None:
    """Check tnat the checking functions return False"""
    LOGGER.debug("empty_datadirs={}".format(empty_datadirs))
    assert not check_jwt_init()
    assert not check_private_key()
    assert check_public_keys()  # This should always be true unless shit blows up


@pytest.mark.asyncio
async def test_create(empty_datadirs: Tuple[Path, Path]) -> None:
    """Test keypair create"""
    LOGGER.debug("empty_datadirs={}".format(empty_datadirs))
    assert not check_jwt_init()
    await jwt_init()
    assert check_jwt_init()


@pytest.mark.asyncio
async def test_create_password(empty_datadirs: Tuple[Path, Path], monkeypatch: pytest.MonkeyPatch) -> None:
    """Test keypair create"""
    LOGGER.debug("empty_datadirs={}".format(empty_datadirs))
    keypass = str(uuid.uuid4())
    with monkeypatch.context() as mpatch:
        mpatch.setenv("JWT_PRIVKEY_PASS", keypass)
        assert not check_jwt_init()
        await jwt_init()
        assert check_jwt_init()
        issuer = Issuer.singleton()
        assert issuer.keypasswd and str(issuer.keypasswd) == keypass


@pytest.mark.asyncio
async def test_rm_jwt_session(rm_jwt_client: TestClient) -> None:
    """Test that we can use JWTs issued by RASENMAEHER itself"""
    client = rm_jwt_client
    resp = await client.get("/api/v1/check-auth/jwt")
    LOGGER.debug("resp={}".format(resp))
    payload = resp.json()
    LOGGER.debug("payload={}".format(payload))
    assert resp.status_code == 200
    assert "sub" in payload
    assert payload["sub"] == "rmsession"
