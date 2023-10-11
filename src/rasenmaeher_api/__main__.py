"""Entrypoint module  `python -m rasenmaeher_api`."""

import uvicorn

from rasenmaeher_api.rmsettings import switchme_to_singleton_call


def main() -> None:
    """Entrypoint of the application."""
    uvicorn.run(
        "rasenmaeher_api.web.application:get_app",
        workers=switchme_to_singleton_call.workers_count,
        host=switchme_to_singleton_call.host,
        port=switchme_to_singleton_call.port,
        reload=switchme_to_singleton_call.reload,
        log_level=switchme_to_singleton_call.log_level.value.lower(),
        factory=True,
    )


if __name__ == "__main__":
    main()
