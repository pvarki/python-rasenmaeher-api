"""Main API entrypoint"""
from typing import AsyncGenerator
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from libpvarki.logging import init_logging

from rasenmaeher_api.settings import settings
from rasenmaeher_api.web.api.router import api_router
from rasenmaeher_api.mtlsinit import mtls_init


LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle lifespan management things, like mTLS client init"""
    # init
    _ = app
    # TODO: We need to init our JWT issuer too
    await mtls_init()
    # App runs
    yield
    # Cleanup


def get_app() -> FastAPI:
    """Returns the FastAPI application."""
    init_logging(settings.log_level_int)

    app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=app_lifespan)
    app.include_router(router=api_router, prefix="/api/v1")

    LOGGER.info("API init done, setting log verbosity to '{}'.".format(settings.log_level))

    return app
