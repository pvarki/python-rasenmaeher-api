""" Application settings. """
import enum
import os
from pathlib import Path
from tempfile import gettempdir
from typing import Optional, Any
import sqlite3
from pydantic import BaseSettings


TEMP_DIR = Path(gettempdir())


class LogLevel(str, enum.Enum):  # noqa: WPS600
    """Possible log levels."""

    NOTSET = "NOTSET"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class SqliteDB:  # pylint: disable=too-few-public-methods
    """
    Application SqliteDB settings/connection

    """

    def __init__(self) -> None:
        self.settings = Settings()

        self.db_ok: bool = False

        if self.settings.environment.lower() == "dev":
            self.sqlite_filepath = self.settings.sqlite_filepath_dev
        else:
            self.sqlite_filepath = self.settings.sqlite_filepath_prod

        # sqlite_enrollement_table_name: str = "enrollment"
        # sqlite_enrollement_table_schema: str = "TODO_SCHEMA"

        # Check sqlite database file
        self.db_ok = self.check_sqlitedatabase()

        if self.db_ok is False:
            self.create_sqlitedatabase()

    def run_command(self, conn: Any, sql_cmd: str = "NA") -> list[Any]:
        """create a table from the create_table_sql statement
        :param conn: Connection object
        :param sql_cmd: sql command statement
        """
        try:
            _c = conn.cursor()
            _c.execute(sql_cmd)
            _c.commit()

            _rows = []
            _rows = _c.fetchall()
            _c.close()
            if len(_rows) > 0:
                return _rows
            return [True]
        except Exception as _e:  # pylint: disable=broad-exception-caught
            print(_e)
            return [False]

    def check_sqlitedatabase(self) -> bool:
        """Check if the sqlite database has been initialized"""
        if not os.path.isfile(self.sqlite_filepath):
            return False
        try:
            self.sqlite_conn = sqlite3.connect(self.sqlite_filepath)
            return True
        except Exception as _e:  # pylint: disable=broad-exception-caught
            # TODO Figure out should we actually do something about this or not.
            # Now it will most likely end up being wiped.
            print(_e)
            return False

    def create_sqlitedatabase(self) -> None:
        """Check sqlite database connection"""
        # Wipe the database if it exists, this should happen only if there
        # is something fucky with the database file. see check_sqlitedatabase()
        if os.path.isfile(self.sqlite_filepath):
            os.remove(self.sqlite_filepath)

        self.sqlite_conn = sqlite3.connect(self.sqlite_filepath)

        # create tables
        if self.sqlite_conn is not None:
            self.run_command(self.sqlite_conn, self.settings.sqlite_enrollement_table_schema)

            self.run_command(self.sqlite_conn, self.settings.sqlite_management_table_schema)
        else:
            print("Error! cannot create the database connection.")


class Settings(BaseSettings):  # pylint: disable=too-few-public-methods
    """
    Application settings.

    These parameters can be configured
    with environment variables.
    """

    host: str = "127.0.0.1"
    port: int = 8000
    # quantity of workers for uvicorn
    workers_count: int = 1
    # Enable uvicorn reloading
    reload: bool = False

    # Current environment
    environment: str = "dev"

    log_level: LogLevel = LogLevel.DEBUG

    # Sentry's configuration.
    sentry_dsn: Optional[str] = None
    sentry_sample_rate: float = 1.0

    # Cfssl configuration
    cfssl_host: str = "http://127.0.0.1"
    cfssl_port: str = "8888"

    # Keycloak configuration.
    keycloak_server_url: Optional[str] = None
    keycloak_client_id: Optional[str] = None
    keycloak_realm_name: Optional[str] = None
    keycloak_client_secret: Optional[str] = None

    # LDAP configuration
    ldap_conn_string: Optional[str] = None
    ldap_username: Optional[str] = None
    ldap_client_secret: Optional[str] = None

    # Sqlite configurations
    sqlite_filepath_prod: str = "/data/persistent/sqlite/rm_db.sql"  # nosec B108 - "hardcoded_tmp_directory"
    sqlite_filepath_dev: str = "/tmp/rm_db.sql"  # nosec B108 - "hardcoded_tmp_directory"
    sqlite_enrollement_table_name: str = "enrollment"

    sqlite_enrollement_table_schema = """ CREATE TABLE IF NOT EXISTS enrollment (
                                        id integer PRIMARY KEY,
                                        work_id text NOT NULL,
                                        work_id_hash text NOT NULL,
                                        state text NOT NULL
                                    ); """

    sqlite_management_table_name: str = "management"
    sqlite_management_table_schema = """ CREATE TABLE IF NOT EXISTS management (
                                        id integer PRIMARY KEY,
                                        management_hash text NOT NULL,
                                        special_rules text NOT NULL
                                    ); """

    class Config:  # pylint: disable=too-few-public-methods
        """Configuration of settings."""

        env_file = ".env"
        env_prefix = "RM_"
        env_file_encoding = "utf-8"


settings = Settings()
sqlite = SqliteDB()
