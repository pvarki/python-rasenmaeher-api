"""Gino based database abstraction"""
from .config import DBConfig
from .base import db

__all__ = [
    "DBConfig",
    "db",
]
