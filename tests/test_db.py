"""DB specific tests"""
import logging
import uuid

import pytest

from rasenmaeher_api.db import DBConfig

LOGGER = logging.getLogger(__name__)


def test_dbconfig_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test the env loading works without import side effects"""
    host = str(uuid.uuid4())
    user = str(uuid.uuid4())
    passwd = str(uuid.uuid4())
    with monkeypatch.context() as mpatch:
        mpatch.setenv("RM_DATABASE_HOST", host)
        mpatch.setenv("RM_DATABASE_USER", user)
        mpatch.setenv("RM_DATABASE_PASSWORD", passwd)

        config = DBConfig()
        assert config.host == host
        assert config.user == user
        assert str(config.password) == passwd
        assert config.dsn
