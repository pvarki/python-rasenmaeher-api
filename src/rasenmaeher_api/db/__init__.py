"""Gino based database abstraction"""
from .config import DBConfig
from .base import db, bind_config
from .people import Person

__all__ = [
    "DBConfig",
    "db",
    "Person",
    "bind_config",
]
