"""Main API entrypoint"""
import logging
from fastapi import FastAPI
from libpvarki.logging import init_logging
from rasenmaeher_api.settings import settings
from rasenmaeher_api.web.api.router import api_router


LOGGER = logging.getLogger(__name__)


def get_app() -> FastAPI:
    """Returns the FastAPI application."""

    init_logging(settings.log_level_int)
    app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.include_router(router=api_router, prefix="/api/v1")

    LOGGER.info("API init done, setting log verbosity to '{}'.".format(settings.log_level))

    return app
