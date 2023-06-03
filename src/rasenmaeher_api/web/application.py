"""Main API entrypoint"""

from fastapi import FastAPI
from rasenmaeher_api.web.api.router import api_router


def get_app() -> FastAPI:
    """Returns the FastAPI application."""

    app = FastAPI(docs_url="/api/docs", openapi_url="/api/openapi.json")
    app.include_router(router=api_router, prefix="/api/v1")

    return app
