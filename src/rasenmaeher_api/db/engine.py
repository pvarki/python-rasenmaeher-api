"""Engine stuff"""
from typing import ClassVar, Optional, Any
import logging
from dataclasses import dataclass, field

from sqlmodel import Session, create_engine

from .config import DBConfig


LOGGER = logging.getLogger(__name__)


@dataclass
class EngineWrapper:
    """Handle engine singletons"""

    config: DBConfig = field(default_factory=DBConfig.singleton)
    # FIXME: correct typing
    engine: Optional[Any] = field(default=None)

    _singleton: ClassVar[Optional["EngineWrapper"]] = None

    @classmethod
    def singleton(cls, **kwargs: Any) -> "EngineWrapper":
        """Get a singleton"""
        if EngineWrapper._singleton is None:
            EngineWrapper._singleton = EngineWrapper(**kwargs)
        assert EngineWrapper._singleton is not None
        return EngineWrapper._singleton

    def __post_init__(self) -> None:
        """create one engine"""
        assert self.config.dsn
        if self.config.pool_min_size and self.config.pool_max_size:
            self.engine = create_engine(
                self.config.dsn,
                pool_pre_ping=True,
                echo=self.config.echo,
                # Not valid for psycopg
                #                min_size=self.config.pool_min_size,
                #                max_size=self.config.pool_max_size,
                #                ssl=self.config.ssl,
            )
            return
        self.engine = create_engine(
            self.config.dsn,
            pool_pre_ping=True,
            echo=self.config.echo,
        )

    @classmethod
    def get_session(cls) -> Session:
        """Get a session from wrapper singleton"""
        return cls.singleton().session()

    def session(self) -> Session:
        """Get a session"""
        return Session(self.engine)
