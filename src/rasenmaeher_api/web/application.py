"""Main API entrypoint"""
from typing import AsyncGenerator
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from libpvarki.logging import init_logging

from ..settings import settings
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
    # App runs
    yield
    # Cleanup
    await dbwrapper.app_shutdown_event()


def get_app_no_init() -> FastAPI:
    """Retunr the app without logging etc inits"""
    app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=app_lifespan, version=__version__)
    app.include_router(router=api_router, prefix="/api/v1")
    app.add_middleware(DBConnectionMiddleware, gino=dbbase.db, config=DBConfig.singleton())
    return app


def get_app() -> FastAPI:
    """Returns the FastAPI application."""
    init_logging(settings.log_level_int)
    app = get_app_no_init()
    LOGGER.info("API init done, setting log verbosity to '{}'.".format(settings.log_level))
    return app
