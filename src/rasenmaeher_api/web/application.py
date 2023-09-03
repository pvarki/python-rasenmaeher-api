"""Main API entrypoint"""
import logging
import asyncio

from fastapi import FastAPI
from libpvarki.logging import init_logging

from rasenmaeher_api.settings import settings
from rasenmaeher_api.web.api.router import api_router
from rasenmaeher_api.mtlsinit import mtls_init


LOGGER = logging.getLogger(__name__)


def get_app() -> FastAPI:
    """Returns the FastAPI application."""
    init_logging(settings.log_level_int)
    asyncio.run_coroutine_threadsafe(mtls_init(), asyncio.get_event_loop())
    app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.include_router(router=api_router, prefix="/api/v1")

    LOGGER.info("API init done, setting log verbosity to '{}'.".format(settings.log_level))

    return app
