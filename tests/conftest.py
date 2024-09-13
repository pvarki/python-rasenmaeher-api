"""pytest automagics"""
from typing import Dict, Any, AsyncGenerator, Generator, Tuple, List
import logging
from pathlib import Path
import uuid
import json
import asyncio
import random

import pytest
from multikeyjwt import Issuer, Verifier
from multikeyjwt.config import Secret
from async_asgi_testclient import TestClient  # pylint: disable=import-error
from httpx import AsyncClient
import pytest  # pylint: disable=import-error
from _pytest.fixtures import SubRequest  # FIXME: Should we be importing from private namespaces ??
from libadvian.tasks import TaskMaster
from libadvian.logging import init_logging
from libadvian.binpackers import uuid_to_b64
from libadvian.testhelpers import monkeysession, nice_tmpdir_mod, nice_tmpdir_ses  # pylint: disable=unused-import
from pytest_docker.plugin import Services
from aiohttp import web

import pytest_asyncio  # pylint: disable=import-error

from rasenmaeher_api.web.application import get_app
from rasenmaeher_api.rmsettings import switchme_to_singleton_call
from rasenmaeher_api.prodcutapihelpers import check_kraftwerk_manifest
from rasenmaeher_api.testhelpers import create_test_users
from rasenmaeher_api.mtlsinit import check_settings_clientpaths, CERT_NAME_PREFIX
from rasenmaeher_api.db.base import init_db, bind_config

init_logging(logging.DEBUG)
LOGGER = logging.getLogger(__name__)
DATA_PATH = Path(__file__).parent / Path("data")
JWT_PATH = DATA_PATH / Path("jwt")


@pytest_asyncio.fixture(scope="session")
async def ginosession() -> None:
    """make sure db is bound etc"""
    await bind_config()
    await init_db()


# pylint: disable=W0621
@pytest.fixture(scope="session", autouse=True)
def session_env_config(  # pylint: disable=R0915,R0914
    monkeysession: pytest.MonkeyPatch,
    docker_ip: str,
    docker_services: Services,
    nice_tmpdir_ses: str,
    announce_server: str,
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
                    },
                    "nonexistent": {
                        "api": "https://localhost:4657/",
                        "uri": "https://nonexistent.localmaeher.pvarki.fi:844/",  # Not actually there
                        "certcn": "nonexistent.localmaeher.pvarki.fi",
                    },
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
        mpatch.setenv("RM_DATABASE_PORT", str(docker_services.port_for("postgres", 5432)))
        mpatch.setenv("RM_DATABASE_HOST", docker_ip)
        mpatch.setenv("RM_DATABASE_PASSWORD", "raesenmaehertestpwd")

        # Reset the singletons
        mpatch.setattr(Issuer, "_singleton", None)
        mpatch.setattr(Verifier, "_singleton", None)
        mpatch.setenv("JWT_PUBKEY_PATH", str(pubkeydir))
        mpatch.setenv("JWT_PRIVKEY_PATH", str(privkeypath))
        # Apparently we are too late in setting the env for settings to take effect
        mpatch.setattr(switchme_to_singleton_call, "integration_api_timeout", 6.0)
        mpatch.setenv("RM_INTEGRATION_API_TIMEOUT", str(switchme_to_singleton_call.integration_api_timeout))
        mpatch.setattr(switchme_to_singleton_call, "cfssl_timeout", 5.0)
        mpatch.setenv("RM_CFSSL_TIMEOUT", str(switchme_to_singleton_call.cfssl_timeout))
        mpatch.setattr(switchme_to_singleton_call, "cfssl_port", docker_services.port_for("cfssl", 7777))
        mpatch.setenv("RM_CFSSL_PORT", str(switchme_to_singleton_call.cfssl_port))
        mpatch.setattr(switchme_to_singleton_call, "cfssl_host", f"http://{docker_ip}")
        mpatch.setenv("RM_CFSSL_HOST", switchme_to_singleton_call.cfssl_host)
        mpatch.setattr(switchme_to_singleton_call, "ocsprest_port", docker_services.port_for("ocsprest", 7776))
        mpatch.setenv("RM_OCSPREST_PORT", str(switchme_to_singleton_call.ocsprest_port))
        mpatch.setattr(switchme_to_singleton_call, "ocsprest_host", f"http://{docker_ip}")
        mpatch.setenv("RM_OCSPREST_HOST", switchme_to_singleton_call.ocsprest_host)
        mpatch.setattr(switchme_to_singleton_call, "persistent_data_dir", str(sessionpersistent))

        mpatch.setenv("RM_PERSISTENT_DATA_DIR", switchme_to_singleton_call.persistent_data_dir)

        mpatch.setenv("LOCAL_CA_CERTS_PATH", str(capath))
        mpatch.setattr(
            switchme_to_singleton_call,
            "mtls_client_cert_path",
            str(sessionpersistent / "public" / f"{CERT_NAME_PREFIX}.pem"),
        )
        mpatch.setenv("RM_MTLS_CLIENT_CERT_PATH", str(switchme_to_singleton_call.mtls_client_cert_path))
        mpatch.setattr(
            switchme_to_singleton_call,
            "mtls_client_key_path",
            str(sessionpersistent / "private" / f"{CERT_NAME_PREFIX}.key"),
        )
        mpatch.setenv("RM_MTLS_CLIENT_KEY_PATH", str(switchme_to_singleton_call.mtls_client_key_path))

        mpatch.setattr(
            switchme_to_singleton_call,
            "tilauspalvelu_jwt",
            "file://{}".format(str(DATA_PATH / "jwt" / "cl_jwtRS256.pub")),
        )
        mpatch.setenv("RM_TILAUSPALVELU_JWT", str(switchme_to_singleton_call.tilauspalvelu_jwt))
        mpatch.setattr(
            switchme_to_singleton_call,
            "kraftwerk_announce",
            f"{announce_server}/announce",
        )
        mpatch.setenv("RM_KRAFTWERK_ANNOUNCE", str(switchme_to_singleton_call.kraftwerk_announce))

        assert not check_settings_clientpaths()

        mpatch.setattr(switchme_to_singleton_call, "kraftwerk_manifest_path", str(kfmanifest))
        mpatch.setenv("RM_KRAFTWERK_MANIFEST_PATH", switchme_to_singleton_call.kraftwerk_manifest_path)
        # force manifest reload
        mpatch.setattr(switchme_to_singleton_call, "kraftwerk_manifest_bool", False)
        check_kraftwerk_manifest()

        yield None


@pytest_asyncio.fixture(scope="session")
async def announce_server() -> AsyncGenerator[str, None]:
    """Simple test server"""
    bind_port = random.randint(1000, 64000)  # nosec
    hostname = "localmaeher.pvarki.fi"

    request_payloads: List[Dict[str, Any]] = []

    async def handle_announce(request: web.Request) -> web.Response:
        """Handle the POST"""
        nonlocal request_payloads
        LOGGER.debug("request={}".format(request))
        payload = await request.json()
        request_payloads.append(payload)
        return web.json_response(payload)

    async def handle_log(request: web.Request) -> web.Response:
        """Return payload log"""
        nonlocal request_payloads
        LOGGER.debug("request={}".format(request))
        return web.json_response({"payloads": request_payloads})

    app = web.Application()
    app.add_routes([web.post("/announce", handle_announce), web.get("/log", handle_log)])

    LOGGER.debug("Starting the async server task(s)")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=hostname, port=bind_port)
    await site.start()

    uri = f"http://{hostname}:{bind_port}"
    LOGGER.debug("yielding {}".format(uri))
    yield uri

    LOGGER.debug("Stopping the async server task(s)")
    await runner.cleanup()


@pytest_asyncio.fixture(scope="session")
async def mtls_client() -> AsyncGenerator[TestClient, None]:
    """Client with mocked NGinx mTLS headers"""
    # TODO: make sure this user is in db, should it be admin too ??
    user_uuid = str(uuid.uuid4())
    async with TestClient(get_app()) as instance:
        instance.headers.update({"X-ClientCert-DN": f"CN={user_uuid},O=N/A"})
        yield instance


@pytest_asyncio.fixture(scope="session")
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
async def unauth_client() -> AsyncGenerator[TestClient, None]:
    """Client with no auth headers"""
    async with TestClient(get_app()) as instance:
        yield instance


@pytest_asyncio.fixture(scope="session")
async def unauth_client_session() -> AsyncGenerator[TestClient, None]:
    """Client with no auth headers"""
    async with TestClient(get_app()) as instance:
        yield instance


@pytest.fixture(scope="session")
def issuer_cl() -> Issuer:
    """issuer using cl-key"""
    return Issuer(
        privkeypath=JWT_PATH / Path("cl_jwtRS256.key"),
        keypasswd=Secret("Cache_Latitude_Displease_Hardcopy"),  # pragma: allowlist secret
    )


@pytest_asyncio.fixture(scope="session")
async def tilauspalvelu_jwt_admin_client(
    issuer_cl: Issuer, test_user_secrets: Tuple[List[str], List[str]]
) -> AsyncGenerator[TestClient, None]:
    """Client with admin JWT"""
    async with TestClient(get_app()) as instance:
        work_ids, _ = test_user_secrets
        pyteststuff_id = work_ids[0]
        token = issuer_cl.issue(
            {
                "sub": pyteststuff_id,
                "anon_admin_session": True,
            }
        )
        instance.headers.update({"Authorization": f"Bearer {token}"})
        yield instance


@pytest_asyncio.fixture(scope="session")
async def tilauspalvelu_jwt_user_client(
    issuer_cl: Issuer, test_user_secrets: Tuple[List[str], List[str]]
) -> AsyncGenerator[TestClient, None]:
    """Client with normal user JWT"""
    async with TestClient(get_app()) as instance:
        work_ids, _ = test_user_secrets
        kissa_id = work_ids[2]
        token = issuer_cl.issue(
            {
                "sub": kissa_id,
                "anon_admin_session": True,
            }
        )
        instance.headers.update({"Authorization": f"Bearer {token}"})
        yield instance


@pytest_asyncio.fixture(scope="session")
async def tilauspalvelu_jwt_without_proper_user_client(issuer_cl: Issuer) -> AsyncGenerator[TestClient, None]:
    """Client with normal user JWT"""
    async with TestClient(get_app()) as instance:
        token = issuer_cl.issue(
            {
                "sub": "nosuchusershouldbefound",
                "anon_admin_session": True,
            }
        )
        instance.headers.update({"Authorization": f"Bearer {token}"})
        yield instance


@pytest_asyncio.fixture(scope="session")
async def tilauspalvelu_jwt_user_koira_client(
    issuer_cl: Issuer, test_user_secrets: Tuple[List[str], List[str]]
) -> AsyncGenerator[TestClient, None]:
    """Client with normal user JWT"""
    async with TestClient(get_app()) as instance:
        work_ids, _ = test_user_secrets
        koira_id = work_ids[3]
        token = issuer_cl.issue(
            {
                "sub": koira_id,
            }
        )
        instance.headers.update({"Authorization": f"Bearer {token}"})
        yield instance


@pytest_asyncio.fixture(scope="session")
async def test_user_secrets(session_env_config: None) -> Tuple[List[str], List[str]]:
    """Create a few test users and work ids returns
    list of work-ids and their corresponding "hashes"

    First one has "enrollment" special role
    """
    _ = session_env_config
    return await create_test_users()


# Issues in tests in ubuntu-latest
# error: Untyped decorator makes function "app_client" untyped  [misc] # no-untyped-def
# pyproject.toml
# [[tool.mypy.overrides]]
# disallow_untyped_decorators=false
# adding '# type: ignore' ends up giving 'error: Unused "type: ignore" comment'
# @pytest_asyncio.fixture(scope="function")
@pytest_asyncio.fixture(scope="session")
async def app_client(request: SubRequest) -> AsyncGenerator[TestClient, None]:
    """Create default client"""
    _request_params: Dict[Any, Any] = request.param
    async with TestClient(get_app()) as instance:
        if "xclientcert" in _request_params.keys() and _request_params["xclientcert"] is True:
            LOGGER.debug(
                "set header '{}:'{}'".format(
                    switchme_to_singleton_call.api_client_cert_header,
                    switchme_to_singleton_call.test_api_client_cert_header_value,
                )
            )
            instance.headers.update(
                {
                    switchme_to_singleton_call.api_client_cert_header: switchme_to_singleton_call.test_api_client_cert_header_value  # pylint: disable=C0301
                }
            )

        yield instance
