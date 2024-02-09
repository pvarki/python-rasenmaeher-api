"""Main API entrypoint"""
from typing import AsyncGenerator
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from libpvarki.logging import init_logging
import aiohttp

from ..rmsettings import RMSettings
from .api.router import api_router
from ..mtlsinit import mtls_init
from ..jwtinit import jwt_init
from ..db import base as dbbase
from ..db.config import DBConfig
from ..db.middleware import DBConnectionMiddleware, DBWrapper
from .. import __version__

LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle lifespan management things, like mTLS client init"""
    # init
    dbwrapper = DBWrapper(gino=dbbase.db, config=DBConfig.singleton())
    await dbwrapper.app_startup_event()
    _ = app
    await jwt_init()
    await mtls_init()
    reporter = asyncio.get_running_loop().create_task(report_to_kraftwerk())
    # App runs
    yield
    # Cleanup
    await reporter  # Just to avoid warning about task that was not awaited
    await dbwrapper.app_shutdown_event()


def get_app_no_init() -> FastAPI:
    """Return the app without logging etc inits"""
    app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=app_lifespan, version=__version__)
    app.include_router(router=api_router, prefix="/api/v1")
    app.add_middleware(DBConnectionMiddleware, gino=dbbase.db, config=DBConfig.singleton())
    return app


def get_app() -> FastAPI:
    """Returns the FastAPI application."""
    init_logging(RMSettings.singleton().log_level_int)
    app = get_app_no_init()
    LOGGER.info("API init done, setting log verbosity to '{}'.".format(RMSettings.singleton().log_level))
    return app


async def report_to_kraftwerk() -> None:
    """Call the KRAFTWERK announce URL if configured"""
    url = RMSettings.singleton().kraftwerk_announce
    if not url:
        LOGGER.info("KRAFTWERK announce url is empty")
        return
    data = {
        "dns": RMSettings.singleton().kraftwerk_manifest_dict["dns"],
        "version": __version__,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                response.raise_for_status()
                payload = await response.json()
                LOGGER.debug("{} responded with {}".format(url, payload))
    except aiohttp.ClientError as exc:
        LOGGER.warning("Failed to report to KRAFTWERK at {}".format(url))
        LOGGER.info(exc)
    except Exception as exc:  # pylint: disable=W0718
        LOGGER.exception("Unhandled exception while reporting to KRAFTWERK: {}".format(exc))
