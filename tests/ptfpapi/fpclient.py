"""Quick client to test the fprun server"""
import logging
from os import environ
import sys
from pathlib import Path
import asyncio


from libadvian.logging import init_logging
from libpvarki.mtlshelp import get_session

LOGGER = logging.getLogger(__name__)


async def main() -> int:
    """Main entrypoint"""
    proc = await asyncio.create_subprocess_exec(
        "/app/muck_magic_hosts.sh", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()
    LOGGER.debug("muck out={!r} err={!r}".format(stdout, stderr))
    if proc.returncode != 0:
        LOGGER.warning("Mucking /etc/hosts failed, this might cause issues")

    hostname = environ.get("FPAPI_HOST_NAME", "fake.localmaeher.pvarki.fi")
    api_port = int(environ.get("FPAPI_PORT", 7788))
    url_base = f"https://{hostname}:{api_port}/"

    persistentdir = Path(environ.get("PERSISTENT_DATA_PATH", "/data/persistent"))
    extra_ca_certs_path = Path(environ.get("LOCAL_CA_CERTS_PATH", "/ca_public"))
    client_cert = (persistentdir / "public" / "client.pem", persistentdir / "private" / "client.key")
    session = get_session(client_cert, extra_ca_certs_path)

    async with session as client:
        resp = await client.get(url_base)
        resp.raise_for_status()
        body = await resp.text()
        LOGGER.info("got {}".format(body))

    return 0


if __name__ == "__main__":
    loglevel = int(environ.get("LOG_LEVEL", "10"))
    init_logging(loglevel)
    LOGGER.setLevel(loglevel)
    sys.exit(asyncio.get_event_loop().run_until_complete(main()))
