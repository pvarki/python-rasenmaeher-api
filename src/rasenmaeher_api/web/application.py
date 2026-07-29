"""Main API entrypoint"""

import asyncio
import datetime
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import aiohttp
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from libadvian.tasks import TaskMaster
from libpvarki.logging import add_trace_and_audit, init_logging

from .. import __version__
from ..db.config import DBConfig
from ..db.middleware import DBConnectionMiddleware, DBWrapper
from ..jwtinit import jwt_init
from ..mtlsinit import mtls_init
from ..rmsettings import RMSettings
from .api.router import api_router, api_router_v2

LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle lifespan management things, like mTLS client init"""
    # init
    LOGGER.debug("DB startup")
    dbwrapper = DBWrapper(config=DBConfig.singleton())
    await dbwrapper.app_startup_event()
    _ = app
    LOGGER.debug("JWT and mTLS inits")
    await jwt_init()
    await mtls_init()
    reporter = asyncio.get_running_loop().create_task(report_to_kraftwerk())
    # App runs
    LOGGER.debug("Yield")
    yield
    # Cleanup
    LOGGER.debug("Cleanup")
    await reporter  # Just to avoid warning about task that was not awaited
    await TaskMaster.singleton().stop_lingering_tasks()  # Make sure teasks get finished
    await dbwrapper.app_shutdown_event()


def get_app_no_init() -> FastAPI:
    """Return the app without logging etc inits"""
    app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=app_lifespan, version=__version__)
    app.include_router(router=api_router, prefix="/api/v1")
    app.include_router(router=api_router_v2, prefix="/api/v2")
    # FIXME: figure out WTF mypy wants here, or has FastAPI changed something ?
    app.add_middleware(DBConnectionMiddleware, config=DBConfig.singleton())  # type: ignore[arg-type]

    def custom_openapi() -> dict[str, Any]:
        """Return OpenAPI schema enriched with a generation timestamp."""
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )
        openapi_schema["x-generated-date"] = datetime.datetime.now(datetime.UTC).isoformat()
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    app.openapi = custom_openapi  # type: ignore[method-assign]
    return app


def get_app() -> FastAPI:
    """Returns the FastAPI application."""
    add_trace_and_audit()  # Register AUDIT and TRACE log levels
    init_logging(RMSettings.singleton().log_level_int)
    app = get_app_no_init()
    LOGGER.info(f"API init done, setting log verbosity to '{RMSettings.singleton().log_level}'.")
    return app


async def report_to_kraftwerk() -> None:
    """Call the KRAFTWERK announce URL if configured"""
    conf = RMSettings.singleton()
    url = conf.kraftwerk_announce
    if not url:
        LOGGER.info("KRAFTWERK announce url is empty")
        return
    data = {
        "dns": conf.kraftwerk_manifest_dict["dns"],
        "version": __version__,
    }
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=conf.kraftwerk_timeout)) as session:
            LOGGER.debug(f"POSTing to {url} data: {data}")
            async with session.post(url, json=data) as response:
                response.raise_for_status()
                payload = await response.json()
                LOGGER.debug(f"{url} responded with {payload}")
    except (aiohttp.ClientError, TimeoutError) as exc:
        LOGGER.warning(f"Failed to report to KRAFTWERK at {url}")
        LOGGER.info(exc)
    except Exception:
        LOGGER.exception("Unhandled exception while reporting to KRAFTWERK")
