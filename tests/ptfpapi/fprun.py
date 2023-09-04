"""The quickest and dirtiest way to respond something to rasenmaehers product integration requests"""
import logging
from os import environ
import sys
import ssl
from pathlib import Path


from aiohttp import web
from libadvian.logging import init_logging
from libpvarki.mtlshelp import get_ssl_context

LOGGER = logging.getLogger(__name__)


async def handle_get_hello(request: web.Request) -> web.Response:
    """Hello world but check mTLS"""
    LOGGER.debug("request={}".format(request))
    LOGGER.debug("transport={}".format(request.transport))
    if not request.transport:
        raise web.HTTPError(reason="No transport")
    peer_cert = request.transport.get_extra_info("peercert")
    LOGGER.debug("peer_cert={}".format(peer_cert))
    if not peer_cert:
        raise web.HTTPError(reason="No peer cert")
    name = request.match_info.get("name", "Anonymous")
    text = "Hello, " + name
    return web.Response(text=text)


def main() -> int:
    """Main entrypoint, return exit code"""
    LOGGER.debug("Called")
    persistentdir = Path(environ.get("PERSISTENT_DATA_PATH", "/data/persistent"))
    extra_ca_certs_path = Path(environ.get("LOCAL_CA_CERTS_PATH", "/ca_public"))
    hostname = environ.get("FPAPI_HOST_NAME", "fake.localmaeher.pvarki.fi")
    bind_port = int(environ.get("FPAPI_BIND_PORT", 7788))
    _bind_address = environ.get("FPAPI_BIND_ADDRESS", "0.0.0.0")  # nosec
    server_cert = (persistentdir / "public" / "server_chain.pem", persistentdir / "private" / "server.key")
    ssl_ctx = get_ssl_context(ssl.Purpose.CLIENT_AUTH, server_cert, extra_ca_certs_path)
    # Enable client cert as required
    ssl_ctx.verify_mode = ssl.CERT_REQUIRED

    app = web.Application()
    app.add_routes([web.get("/", handle_get_hello), web.get("/{name}", handle_get_hello)])

    LOGGER.info("Starting runner on port {}".format(bind_port))
    web.run_app(app, host=hostname, port=bind_port, ssl_context=ssl_ctx)
    return 0


if __name__ == "__main__":
    loglevel = int(environ.get("LOG_LEVEL", "10"))
    init_logging(loglevel)
    LOGGER.setLevel(loglevel)
    sys.exit(main())
