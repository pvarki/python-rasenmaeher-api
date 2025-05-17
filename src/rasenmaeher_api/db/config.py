"""Read database configuration from ENV or .env -file"""

from typing import Optional, cast, Callable, ClassVar, Any
import logging
import functools
from dataclasses import dataclass, field


from sqlalchemy.engine.url import URL, make_url
from sqlalchemy import util
from starlette.config import Config
from starlette.datastructures import Secret

LOGGER = logging.getLogger(__name__)
config = cast(
    Callable[..., Any], Config()
)  # not supporting .env files anymore because https://github.com/encode/starlette/discussions/2446

# FIXME: this should probably be in some common library of ours


@dataclass
class DBConfig:  # pylint: disable=R0902
    """DB config dataclass, functools etc used to avoid import-time side-effects"""

    driver: str = field(
        default_factory=cast(Callable[..., str], functools.partial(config, "RM_DATABASE_DRIVER", default="postgresql"))
    )
    host: Optional[str] = field(default_factory=functools.partial(config, "RM_DATABASE_HOST", default=None))
    port: int = field(
        default_factory=cast(Callable[..., int], functools.partial(config, "RM_DATABASE_PORT", cast=int, default=None))
    )
    user: Optional[str] = field(
        default_factory=cast(Callable[..., str], functools.partial(config, "RM_DATABASE_USER", default="raesenmaeher"))
    )
    password: Secret = field(
        default_factory=cast(
            Callable[..., Secret], functools.partial(config, "RM_DATABASE_PASSWORD", cast=Secret, default=None)
        )
    )
    database: str = field(
        default_factory=cast(Callable[..., str], functools.partial(config, "RM_DATABASE_NAME", default="raesenmaeher"))
    )
    dsn: Optional[URL] = field(
        default_factory=cast(
            Callable[..., Optional[URL]],
            functools.partial(
                config,
                "RM_DB_DSN",
                cast=make_url,
                default=None,
            ),
        )
    )
    pool_min_size: int = field(
        default_factory=cast(Callable[..., int], functools.partial(config, "DB_POOL_MIN_SIZE", cast=int, default=1))
    )
    pool_max_size: int = field(
        default_factory=cast(Callable[..., int], functools.partial(config, "DB_POOL_MAX_SIZE", cast=int, default=16))
    )
    echo: bool = field(
        default_factory=cast(Callable[..., bool], functools.partial(config, "DB_ECHO", cast=bool, default=False))
    )
    ssl: str = field(
        default_factory=cast(Callable[..., str], functools.partial(config, "DB_SSL", cast=str, default="prefer"))
    )  # see asyncpg.connect()
    use_connection_for_request: bool = field(
        default_factory=cast(
            Callable[..., bool], functools.partial(config, "DB_USE_CONNECTION_FOR_REQUEST", cast=bool, default=True)
        )
    )
    retry_limit: int = field(
        default_factory=cast(Callable[..., int], functools.partial(config, "DB_RETRY_LIMIT", cast=int, default=1))
    )
    retry_interval: int = field(
        default_factory=cast(Callable[..., int], functools.partial(config, "DB_RETRY_INTERVAL", cast=int, default=1))
    )

    # private
    _singleton: ClassVar[Optional["DBConfig"]] = None

    @classmethod
    def singleton(cls, **kwargs: Any) -> "DBConfig":
        """Get a singleton"""
        if DBConfig._singleton is None:
            DBConfig._singleton = DBConfig(**kwargs)
        assert DBConfig._singleton is not None
        return DBConfig._singleton

    def __post_init__(self) -> None:
        """Post init stuff"""
        if self.dsn is None:
            self.dsn = URL(
                drivername=self.driver,
                username=self.user,
                password=self.password,  # type: ignore[arg-type]
                host=self.host,
                port=self.port,
                database=self.database,
                query=util.EMPTY_DICT,
            )

        LOGGER.debug("DSN={}".format(self.dsn))
        LOGGER.debug("HOST={}".format(self.host))
        LOGGER.debug("DATABASE={}".format(self.database))
