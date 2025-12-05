"""The quickest and dirtiest way to respond something to rasenmaehers product integration requests"""

import logging
from os import environ
import sys
import ssl
from pathlib import Path
import io
import zipfile
import base64


from aiohttp import web
from libadvian.logging import init_logging
from libpvarki.mtlshelp import get_ssl_context
from libpvarki.schemas.generic import OperationResultResponse
from libpvarki.schemas.product import (
    UserInstructionFragment,
    UserCRUDRequest,
)
from pydantic import BaseModel, Field, Extra


# FIXME: Move to libpvarki
class ProductAddRequest(BaseModel):  # pylint: disable=too-few-public-methods,R0801
    """Request to add product interoperability."""

    certcn: str = Field(description="CN of the certificate")
    x509cert: str = Field(description="Certificate encoded with CFSSL conventions (newlines escaped)")

    class Config:  # pylint: disable=too-few-public-methods
        """Example values for schema"""

        extra = Extra.forbid
        schema_extra = {
            "examples": [
                {
                    "certcn": "product.deployment.tld",
                    "x509cert": "-----BEGIN CERTIFICATE-----\\nMIIEwjCC...\\n-----END CERTIFICATE-----\\n",
                },
            ],
        }


LOGGER = logging.getLogger(__name__)


def zip_pem(pem: str, filename: str) -> bytes:
    """in-memory zip of the pem"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        zip_file.writestr(filename, pem)
    return zip_buffer.getvalue()


def check_peer_cert(request: web.Request) -> None:
    """Check the transport for peer cert, raise error if missing"""
    LOGGER.debug("request={}".format(request))
    LOGGER.debug("transport={}".format(request.transport))
    if not request.transport:
        raise web.HTTPError(reason="No transport")
    peer_cert = request.transport.get_extra_info("peercert")
    LOGGER.debug("peer_cert={}".format(peer_cert))
    if not peer_cert:
        raise web.HTTPError(reason="No peer cert")


async def handle_get_hello(request: web.Request) -> web.Response:
    """Hello world but check mTLS"""
    check_peer_cert(request)
    name = request.match_info.get("name", "Anonymous")
    text = "Hello, " + name
    return web.Response(text=text)


async def handle_user_crud(request: web.Request) -> web.Response:
    """Respond with success to all CRUD operations"""
    check_peer_cert(request)
    # Just to make sure the request itself uses valid schema
    _req = UserCRUDRequest.parse_raw(await request.text())
    resp = OperationResultResponse(success=True, extra="Nothing was actually done, this is a fake endpoint for testing")
    return web.json_response(resp.dict())


async def handle_fragment(request: web.Request) -> web.Response:
    """Respond with hello_world for user"""
    check_peer_cert(request)
    user = UserCRUDRequest.parse_raw(await request.text())
    LOGGER.info("Called with user={}".format(user))
    zip1_bytes = zip_pem(user.x509cert, f"{user.callsign}_1.pem")
    zip2_bytes = zip_pem(user.x509cert, f"{user.callsign}_2.pem")

    return web.json_response(
        [
            {
                "title": "iTAK",
                "data": f"data:application/zip;base64,{base64.b64encode(zip1_bytes).decode('ascii')}",
                "filename": f"{user.callsign}_1.zip",
            },
            {
                "title": "ATAK",
                "data": f"data:application/zip;base64,{base64.b64encode(zip2_bytes).decode('ascii')}",
                "filename": f"{user.callsign}_2.zip",
            },
        ]
    )


async def handle_description(request: web.Request) -> web.Response:
    """Respond with hello_world for user"""
    _lang = request.match_info.get("language", "en")
    LOGGER.info("Called")

    return web.json_response(
        {
            "shortname": "fake",
            "title": "Test fake product",
            "icon": None,
            "description": "Testing things",
            "language": "en",
        }
    )


async def handle_description_v2(request: web.Request) -> web.Response:
    """Respond with extended description for v2"""
    _lang = request.match_info.get("language", "en")
    LOGGER.info("Called with language={}".format(_lang))

    return web.json_response(
        {
            "shortname": "fake",
            "title": "Test fake product",
            "icon": None,
            "description": "Testing things",
            "language": _lang,
            "docs": "https://example.com/docs",
            "component": {"type": "link", "ref": "https://example.com/component"},
        }
    )


async def handle_clients_data_v2(request: web.Request) -> web.Response:
    """Respond with client data for v2"""
    check_peer_cert(request)
    payload = await request.json()
    LOGGER.info("Called with payload={}".format(payload))

    return web.json_response(
        {
            "data": {
                "tak_zips": [
                    {
                        "title": "atak.zip",
                        "filename": "FAKE_atak.zip",
                        "data": "data:application/zip;base64,iugdfibjsdfIBUSDCIBUSDAVIBUSADFIBHSDFAIBH",
                    },
                    {
                        "title": "itak.zip",
                        "filename": "FAKE_itak.zip",
                        "data": "data:application/zip;base64,UEsxcfbngghdmhgmfjmghmghmgmgmhghfngfsvfvf",
                    },
                    {
                        "title": "tak-tracker.zip",
                        "filename": "FAKE_tak-tracker.zip",
                        "data": "data:application/zip;base64,xbnbvnzdgdbfzdbfzdgbfdzbzdzdzggfnndgndgzdnggnzd",
                    },
                ]
            }
        }
    )


async def handle_instructions(request: web.Request) -> web.Response:
    """Respond with hello_world for user"""
    check_peer_cert(request)
    _lang = request.match_info.get("language", "en")
    payload = await request.json()
    LOGGER.info("Called with payload={}".format(payload))

    return web.json_response(
        {
            "callsign": payload["callsign"],
            "instructions": "FIXME: Return something sane",
            "language": "en",
        }
    )


async def handle_health(request: web.Request) -> web.Response:
    """healthcheck response"""
    check_peer_cert(request)
    return web.json_response({"healthy": True})


async def handle_admin_fragment(request: web.Request) -> web.Response:
    """Respond with success to all CRUD operations"""
    check_peer_cert(request)
    resp = UserInstructionFragment(html="<p>Hello admin!</p>")
    return web.json_response(resp.dict())


async def handle_interop_add(request: web.Request) -> web.Response:
    """Respond to additions"""
    _req = ProductAddRequest.parse_raw(await request.text())
    resp = OperationResultResponse(success=True, extra="Nothing was actually done, this is a fake endpoint for testing")
    return web.json_response(resp.dict())


async def handle_admin_clients_data_v2(request: web.Request) -> web.Response:
    """Respond with admin client data for v2"""
    check_peer_cert(request)
    payload = await request.json()
    LOGGER.info("Called admin with payload={}".format(payload))

    return web.json_response(
        {
            "data": {
                "tak_zips": [
                    {
                        "title": "atak.zip",
                        "filename": "FAKE_atak.zip",
                        "data": "data:application/zip;base64,iugdfibjsdfIBUSDCIBUSDAVIBUSADFIBHSDFAIBH",
                    },
                    {
                        "title": "itak.zip",
                        "filename": "FAKE_itak.zip",
                        "data": "data:application/zip;base64,UEsxcfbngghdmhgmfjmghmghmgmgmhghfngfsvfvf",
                    },
                    {
                        "title": "tak-tracker.zip",
                        "filename": "FAKE_tak-tracker.zip",
                        "data": "data:application/zip;base64,xbnbvnzdgdbfzdbfzdgbfdzbzdzdzggfnndgndgzdnggnzd",
                    },
                ]
            }
        }
    )


def main() -> int:
    """Main entrypoint, return exit code"""
    LOGGER.debug("Called")
    persistentdir = Path(environ.get("PERSISTENT_DATA_PATH", "/data/persistent"))
    extra_ca_certs_path = Path(environ.get("LOCAL_CA_CERTS_PATH", "/ca_public"))
    _hostname = environ.get("FPAPI_HOST_NAME", "fake.localmaeher.dev.pvarki.fi")
    bind_port = int(environ.get("FPAPI_BIND_PORT", 7788))
    bind_address = environ.get("FPAPI_BIND_ADDRESS", "0.0.0.0")  # nosec
    server_cert = (persistentdir / "public" / "server_chain.pem", persistentdir / "private" / "server.key")
    ssl_ctx = get_ssl_context(ssl.Purpose.CLIENT_AUTH, server_cert, extra_ca_certs_path)
    # Enable client cert as required
    ssl_ctx.verify_mode = ssl.CERT_REQUIRED

    app = web.Application()
    app.add_routes(
        [
            web.get("/", handle_get_hello),
            web.get("/{name}", handle_get_hello),
            web.post("/api/v1/interop/add", handle_interop_add),
            web.post("/api/v1/users/created", handle_user_crud),
            web.post("/api/v1/users/revoked", handle_user_crud),
            web.post("/api/v1/users/promoted", handle_user_crud),
            web.post("/api/v1/users/demoted", handle_user_crud),
            web.put("/api/v1/users/updated", handle_user_crud),
            web.post("/api/v1/clients/fragment", handle_fragment),
            web.get("/api/v1/admins/fragment", handle_admin_fragment),
            web.get("/api/v1/healthcheck", handle_health),
            web.post("/api/v1/healthcheck", handle_health),
            web.get("/api/v1/description/{language}", handle_description),
            web.post("/api/v1/instructions/{language}", handle_instructions),
            # v2 routes
            web.get("/api/v2/description/{language}", handle_description_v2),
            web.post("/api/v2/clients/data", handle_clients_data_v2),
            web.post("/api/v2/admin/clients/data", handle_admin_clients_data_v2),
        ]
    )

    LOGGER.info("Starting runner on port {}".format(bind_port))
    web.run_app(app, host=bind_address, port=bind_port, ssl_context=ssl_ctx)
    return 0


if __name__ == "__main__":
    loglevel = int(environ.get("LOG_LEVEL", "10"))
    init_logging(loglevel)
    LOGGER.setLevel(loglevel)
    sys.exit(main())
