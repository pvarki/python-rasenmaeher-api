"""Middleware stuff"""
from typing import Optional
from dataclasses import dataclass, field
import logging
import asyncio

from starlette.types import Receive, Scope, Send
from fastapi import FastAPI


from .config import DBConfig
from .dbinit import init_db
from .engine import EngineWrapper

LOGGER = logging.getLogger(__name__)

# FIXME: this should probably be in some common library of ours


@dataclass
class DBWrapper:  # pylint: disable=R0902
    """Handle app db connection stuff"""

    config: DBConfig = field(default_factory=DBConfig)
    init_db: bool = field(default=True)

    async def create_engine(self) -> None:
        """Make sure we have engine"""
        EngineWrapper.singleton()
        if self.init_db:
            await init_db()

    async def app_startup_event(self) -> None:
        """App startup callback, connect to db or die"""
        LOGGER.info("Connecting to the database: {!r}".format(self.config.dsn))
        retries = 0
        while True:
            retries += 1
            try:
                await self.create_engine()
                break
            except Exception as exc:  # pylint: disable=W0703
                LOGGER.error("database connection failed {}".format(exc))
                # TODO: Check that it's a connection error, otherwise just raise immediately
                if retries < self.config.retry_limit:
                    LOGGER.info("Waiting for the database to start...")
                    await asyncio.sleep(self.config.retry_interval)
                else:
                    LOGGER.error("Cannot connect to the database; max retries reached.")
                    raise

    async def app_shutdown_event(self) -> None:
        """On app shutdown close the db connection"""
        # we no longer need to manage connections like this


class DBConnectionMiddleware:  # pylint: disable=R0903
    """Middleware that handles request connection pooling"""

    def __init__(self, app: FastAPI, config: DBConfig) -> None:
        self.app = app
        self._conn_for_req = config.use_connection_for_request

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Not going to handle this, pass onwards
        if scope["type"] != "http" or not self._conn_for_req:
            await self.app(scope, receive, send)
            return

        # We no longer need to handle connection per request
        await self.app(scope, receive, send)
