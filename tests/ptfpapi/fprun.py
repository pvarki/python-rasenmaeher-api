"""The quickest and dirtiest way to respond something to rasenmaehers product integration requests"""
import logging
from os import environ
import sys
import ssl
from pathlib import Path


from aiohttp import web
from libadvian.logging import init_logging
from libpvarki.mtlshelp import get_ssl_context
from libpvarki.schemas.generic import OperationResultResponse
from libpvarki.schemas.product import (
    UserInstructionFragment,
    UserCRUDRequest,
)

LOGGER = logging.getLogger(__name__)


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
    """Respond with success to all CRUD operations"""
    check_peer_cert(request)
    # Just to make sure the request itself uses valid schema
    _req = UserCRUDRequest.parse_raw(await request.text())
    resp = UserInstructionFragment(html="<p>Hello world!</p>")
    return web.json_response(resp.dict())


def main() -> int:
    """Main entrypoint, return exit code"""
    LOGGER.debug("Called")
    persistentdir = Path(environ.get("PERSISTENT_DATA_PATH", "/data/persistent"))
    extra_ca_certs_path = Path(environ.get("LOCAL_CA_CERTS_PATH", "/ca_public"))
    _hostname = environ.get("FPAPI_HOST_NAME", "fake.localmaeher.pvarki.fi")
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
            web.post("/api/v1/users/created", handle_user_crud),
            web.post("/api/v1/users/revoked", handle_user_crud),
            web.post("/api/v1/users/promoted", handle_user_crud),
            web.post("/api/v1/users/demoted", handle_user_crud),
            web.put("/api/v1/users/updated", handle_user_crud),
            web.post("/api/v1/clients/fragment", handle_fragment),
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
