"""Middleware stuff"""
from typing import Optional
from dataclasses import dataclass, field
import logging
import asyncio

from starlette.types import Receive, Scope, Send
from fastapi import FastAPI
from gino import Gino
from gino.exceptions import UninitializedError

from .config import DBConfig
from .base import init_db

LOGGER = logging.getLogger(__name__)

# FIXME: this should probably be in some common library of ours


@dataclass
class DBWrapper:  # pylint: disable=R0902
    """Handle app db connection stuff"""

    gino: Gino = field()
    config: DBConfig = field(default_factory=DBConfig)
    init_db: bool = field(default=True)

    async def bind_gino(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """Bind gino to db"""
        LOGGER.debug("Called")
        if self.gino._bind is not None:  # pylint: disable=W0212
            LOGGER.warning("Already bound")
            return
        LOGGER.debug("Setting Gino DB bind")
        await self.gino.set_bind(
            self.config.dsn,
            echo=self.config.echo,
            min_size=self.config.pool_min_size,
            max_size=self.config.pool_max_size,
            ssl=self.config.ssl,
            loop=loop,
        )
        if self.init_db:
            LOGGER.info("Calling init_db")
            await init_db()

    async def app_startup_event(self) -> None:
        """App startup callback, connect to db or die"""
        LOGGER.info("Connecting to the database: {!r}".format(self.config.dsn))
        retries = 0
        while True:
            retries += 1
            try:
                await self.bind_gino()
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
        msg = "Database connection pool created: {}"
        LOGGER.info(
            msg.format(repr(self.gino.bind)),
            extra={"color_message": msg.format(self.gino.bind.repr(color=True))},
        )

    async def app_shutdown_event(self) -> None:
        """On app shutdown close the db connection"""
        try:
            msg = "Closing database connection: {}"
            LOGGER.info(
                msg.format(repr(self.gino.bind)),
                extra={"color_message": msg.format(self.gino.bind.repr(color=True))},
            )
            ginobound = self.gino.pop_bind()
            await ginobound.close()
            msg = "Closed database connection: {}"
            LOGGER.info(
                msg.format(repr(ginobound)),
                extra={"color_message": msg.format(ginobound.repr(color=True))},
            )
        except (RuntimeError, UninitializedError) as exc:
            LOGGER.exception("Ignoring {} during close".format(exc))


class DBConnectionMiddleware:  # pylint: disable=R0903
    """Middleware that handles request connection pooling"""

    def __init__(self, app: FastAPI, gino: Gino, config: DBConfig) -> None:
        self.app = app
        self.gino = gino
        self._conn_for_req = config.use_connection_for_request

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Not going to handle this, pass onwards
        if scope["type"] != "http" or not self._conn_for_req:
            await self.app(scope, receive, send)
            return

        # Get and release connection
        scope["connection"] = await self.gino.acquire(lazy=True)
        try:
            await self.app(scope, receive, send)
        finally:
            conn = scope.pop("connection", None)
            if conn is not None:
                await conn.release()
