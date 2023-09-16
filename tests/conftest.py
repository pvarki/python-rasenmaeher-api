"""pytest automagics"""
from typing import Dict, Any, AsyncGenerator, Generator, Tuple, List
import logging
from pathlib import Path
import uuid
import json

import pytest
from multikeyjwt import Issuer, Verifier
from multikeyjwt.config import Secret
from async_asgi_testclient import TestClient  # pylint: disable=import-error
import pytest_asyncio  # pylint: disable=import-error
from _pytest.fixtures import SubRequest  # FIXME: Should we be importing from private namespaces ??
from libadvian.logging import init_logging
from libadvian.binpackers import uuid_to_b64
from libadvian.testhelpers import monkeysession, nice_tmpdir_mod, nice_tmpdir_ses  # pylint: disable=unused-import
from pytest_docker.plugin import Services

from rasenmaeher_api.web.application import get_app
from rasenmaeher_api.settings import settings
from rasenmaeher_api.prodcutapihelpers import check_kraftwerk_manifest
from rasenmaeher_api.sqlitedatabase import sqlite as sqlitewrapper

init_logging(logging.DEBUG)
LOGGER = logging.getLogger(__name__)
DATA_PATH = Path(__file__).parent / Path("data")
JWT_PATH = DATA_PATH / Path("jwt")


# FIXME: Set environment so the mTLS client loads certs from a temp dir


@pytest.fixture(scope="session")
def test_user_secrets() -> Tuple[List[str], List[str]]:
    """Create a few test users and work ids returns
    list of work-ids and their corresponding "hashes"

    First one has "enrollment" special role
    """
    # copied from the sqlitedb dev init so blame karppo :D
    work_ids: List[str] = []
    work_hashes: List[str] = []

    # FIXME: do not put these to settings
    work_ids.append(settings.sqlite_init_testing_management_username)
    work_hashes.append(settings.sqlite_init_testing_management_hash)
    # Create test admin credentials
    _q = sqlitewrapper.settings.sqlite_insert_into_enrollment.format(
        work_id=work_ids[-1],
        work_id_hash=work_hashes[-1],
        state="ReadyForDelivery",
        accepted="somehashwhoaccepted_this",
        cert_dl_link="https://www.kuvaton.com/kuvei/asiakkaamme_kissa.jpg",
        cert_howto_dl_link="https://www.kuvaton.com/kuvei/asiakkaamme_kissa.jpg",
        mtls_test_link="https://www.kuvaton.com/kuvei/asiakkaamme_kissa.jpg",
        verification_code="",
        locked="",
    )
    sqlitewrapper.run_command(_q)
    _q = sqlitewrapper.settings.sqlite_insert_into_management.format(
        management_hash=sqlitewrapper.settings.sqlite_init_testing_management_hash, special_rules="enrollment"
    )
    sqlitewrapper.run_command(_q)

    work_ids.append("kissa")
    work_hashes.append("kissa123")
    # Create kissa dummy role
    _q = sqlitewrapper.settings.sqlite_insert_into_enrollment.format(
        work_id=work_ids[-1],
        work_id_hash=work_hashes[-1],
        state="ReadyForDelivery",
        accepted="somehashwhoaccepted_this",
        cert_dl_link="https://www.kuvaton.com/kuvei/asiakkaamme_kissa.jpg",
        cert_howto_dl_link="https://www.kuvaton.com/kuvei/asiakkaamme_kissa.jpg",
        mtls_test_link="https://www.kuvaton.com/kuvei/asiakkaamme_kissa.jpg",
        verification_code="",
        locked="",
    )
    sqlitewrapper.run_command(_q)

    work_ids.append("koira")
    work_hashes.append("koira123")
    # Create koira dummy role
    _q = sqlitewrapper.settings.sqlite_insert_into_enrollment.format(
        work_id=work_ids[-1],
        work_id_hash=work_hashes[-1],
        state="init",
        accepted="",
        cert_dl_link="",
        cert_howto_dl_link="",
        mtls_test_link="",
        verification_code="",
        locked="",
    )
    sqlitewrapper.run_command(_q)
    work_ids.append("koira")
    work_hashes.append("koira123")
    _q = sqlitewrapper.settings.sqlite_insert_into_enrollment.format(
        work_id=work_ids[-1],
        work_id_hash=work_hashes[-1],
        state="init",
        accepted="",
        cert_dl_link="",
        cert_howto_dl_link="",
        mtls_test_link="",
        verification_code="",
        locked="",
    )
    sqlitewrapper.run_command(_q)
    return work_ids, work_hashes


# pylint: disable=redefined-outer-name
@pytest.fixture(scope="session")
def issuer_cl() -> Issuer:
    """issuer using cl-key"""
    return Issuer(
        privkeypath=JWT_PATH / Path("cl_jwtRS256.key"),
        keypasswd=Secret("Cache_Latitude_Displease_Hardcopy"),  # pragma: allowlist secret
    )


@pytest.fixture(scope="session")
def verifier() -> Verifier:
    """issuer using all keys in data"""
    return Verifier(pubkeypath=JWT_PATH)


@pytest.fixture(scope="session", autouse=True)
def session_env_config(
    monkeysession: pytest.MonkeyPatch, docker_ip: str, docker_services: Services, nice_tmpdir_ses: str
) -> Generator[None, None, None]:
    """set the JWT auth config"""
    sessionfiles = Path(nice_tmpdir_ses)
    sessionpersistent = sessionfiles / "data/persistent"
    kfmanifest = sessionfiles / "kraftwerk-rasenmaeher-init.json"
    fakeproduct_port = docker_services.port_for("fpapi_run", 7788)
    kfmanifest.write_text(
        json.dumps(
            {
                "dns": "localmaeher.pvarki.fi",
                "products": {
                    "fake": {
                        "api": f"https://fake.localmaeher.pvarki.fi:{fakeproduct_port}/",
                        "uri": "https://fake.localmaeher.pvarki.fi:844/",  # Not actually there
                        "certcn": "fake.localmaeher.pvarki.fi",
                    }
                },
            }
        )
    )
    capath = DATA_PATH / "ca_public"
    pubkeydir = sessionpersistent / "public"
    pubkeydir.mkdir(parents=True)
    sqlitepath = sessionpersistent / "private" / "test.db"
    sqlitepath.parent.mkdir(parents=True, mode=0o760)
    privkeypath = sqlitepath.parent / "rm_jwtsign.key"

    # Copy the datadir JWT keys to temp dir with test data
    for fpath in JWT_PATH.iterdir():
        if fpath.name.endswith(".key"):
            # skip these keys from the copy
            continue
        if fpath.name.endswith(".pub"):
            tgtpath = pubkeydir / fpath.name
        else:
            LOGGER.warning("Don't know what to do with {}".format(fpath))
            continue
        tgtpath.write_bytes(fpath.read_bytes())

    with monkeysession.context() as mpatch:
        mpatch.setenv("LOG_CONSOLE_FORMATTER", "utc")
        # Reset the singletons
        mpatch.setattr(Issuer, "_singleton", None)
        mpatch.setattr(Verifier, "_singleton", None)
        mpatch.setenv("JWT_PUBKEY_PATH", str(pubkeydir))
        mpatch.setenv("JWT_PRIVKEY_PATH", str(privkeypath))
        # Apparently we are too late in setting the env for settings to take effect
        mpatch.setattr(settings, "cfssl_port", docker_services.port_for("cfssl", 7777))
        mpatch.setenv("RM_CFSSL_PORT", str(settings.cfssl_port))
        mpatch.setattr(settings, "cfssl_host", f"http://{docker_ip}")
        mpatch.setenv("RM_CFSSL_HOST", settings.cfssl_host)

        mpatch.setenv("LOCAL_CA_CERTS_PATH", str(capath))
        mpatch.setattr(settings, "mtls_client_cert_path", str(sessionfiles / "rmmtlsclient.pem"))
        mpatch.setenv("RM_MTLS_CLIENT_CERT_PATH", settings.mtls_client_cert_path)
        mpatch.setattr(settings, "mtls_client_key_path", str(sessionfiles / "rmmtlsclient.key"))
        mpatch.setenv("RM_MTLS_CLIENT_KEY_PATH", settings.mtls_client_key_path)

        mpatch.setattr(settings, "kraftwerk_manifest_path", str(kfmanifest))
        mpatch.setenv("RM_KRAFTWERK_MANIFEST_PATH", settings.kraftwerk_manifest_path)
        # force manifest reload
        mpatch.setattr(settings, "kraftwerk_manifest_bool", False)
        check_kraftwerk_manifest()

        mpatch.setattr(settings, "sqlite_filepath_prod", str(sqlitepath))
        mpatch.setenv("RM_SQLITE_FILEPATH_PROD", settings.sqlite_filepath_prod)
        mpatch.setattr(settings, "sqlite_filepath_dev", str(sqlitepath))
        mpatch.setenv("RM_SQLITE_FILEPATH_DEV", settings.sqlite_filepath_prod)

        yield None


@pytest_asyncio.fixture()
async def tilauspalvelu_jwt_client(issuer_cl: Issuer) -> AsyncGenerator[TestClient, None]:
    """Client with tilauspalvely style JWT"""
    async with TestClient(get_app()) as instance:
        token = issuer_cl.issue(
            {
                "sub": "tpadminsession",
                "anon_admin_session": True,
                "nonce": str(uuid.uuid4()),
            }
        )
        instance.headers.update({"Authorization": f"Bearer {token}"})
        yield instance


@pytest_asyncio.fixture()
async def kraftwerk_jwt_client(issuer_cl: Issuer) -> AsyncGenerator[TestClient, None]:
    """Client with KRAFTWERK style JWT"""
    async with TestClient(get_app()) as instance:
        token = issuer_cl.issue(
            {
                "sub": "productname",
                "csr": True,
                "nonce": uuid_to_b64(uuid.uuid4()),
            }
        )
        instance.headers.update({"Authorization": f"Bearer {token}"})
        yield instance


@pytest_asyncio.fixture()
async def mtls_client() -> AsyncGenerator[TestClient, None]:
    """Client with mocked NGinx mTLS headers"""
    # TODO: make sure this user is in db, should it be admin too ??
    user_uuid = str(uuid.uuid4())
    async with TestClient(get_app()) as instance:
        instance.headers.update({"X-ClientCert-DN": f"CN={user_uuid},O=N/A"})
        yield instance


@pytest_asyncio.fixture()
async def unauth_client() -> AsyncGenerator[TestClient, None]:
    """Client with no auth headers"""
    async with TestClient(get_app()) as instance:
        yield instance


@pytest_asyncio.fixture()
async def rm_jwt_client() -> AsyncGenerator[TestClient, None]:
    """Client with no auth headers"""
    async with TestClient(get_app()) as instance:
        token = Issuer.singleton().issue(
            {
                "sub": "rmsession",
                "anon_admin_session": True,
            }
        )
        instance.headers.update({"Authorization": f"Bearer {token}"})
        yield instance


# Issues in tests in ubuntu-latest
# error: Untyped decorator makes function "app_client" untyped  [misc] # no-untyped-def
# pyproject.toml
# [[tool.mypy.overrides]]
# disallow_untyped_decorators=false
# adding '# type: ignore' ends up giving 'error: Unused "type: ignore" comment'
@pytest_asyncio.fixture(scope="function")
async def app_client(request: SubRequest) -> AsyncGenerator[TestClient, None]:
    """Create default client"""
    _request_params: Dict[Any, Any] = request.param
    async with TestClient(get_app()) as instance:
        if "xclientcert" in _request_params.keys() and _request_params["xclientcert"] is True:
            LOGGER.debug(
                "set header '{}:'{}'".format(
                    settings.api_client_cert_header, settings.test_api_client_cert_header_value
                )
            )
            instance.headers.update({settings.api_client_cert_header: settings.test_api_client_cert_header_value})

        yield instance
