""" Application settings. """
import enum
import os
import logging
from pathlib import Path
from tempfile import gettempdir
from typing import Optional, Any, Tuple, List
import sqlite3
from pydantic import BaseSettings


TEMP_DIR = Path(gettempdir())
LOGGER = logging.getLogger(__name__)


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

    def run_command(self, sql_cmd: str = "NA") -> Tuple[bool, List[Any]]:
        """create a table from the create_table_sql statement
        :param sql_cmd: sql command statement
        """
        try:
            _c = self.sqlite_conn.cursor()
            _c.execute(sql_cmd)
            self.sqlite_conn.commit()

            _rows = []
            _rows = _c.fetchall()
            _c.close()
            if len(_rows) > 0:
                return True, _rows
            return True, []
        except Exception as _e:  # pylint: disable=broad-exception-caught
            LOGGER.error("SQLITE run command error : {}".format(_e))
            return False, []

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
            LOGGER.error("SQLITE check sqlite database connection error : {}".format(_e))
            return False

    def create_sqlitedatabase(self) -> None:
        """Check sqlite database connection"""
        # Wipe the database if it exists, this should happen only if there
        # is something fucky with the database file. see check_sqlitedatabase()
        if os.path.isfile(self.sqlite_filepath):
            os.remove(self.sqlite_filepath)

        self.sqlite_conn = sqlite3.connect(self.sqlite_filepath)

        # create tables and add management hash
        if self.sqlite_conn is not None:
            self.run_command(self.settings.sqlite_enrollement_table_schema)

            self.run_command(self.settings.sqlite_management_table_schema)
            _q = self.settings.sqlite_insert_into_management.format(
                management_hash=self.settings.sqlite_init_management_hash, special_rules="main"
            )
            self.run_command(_q)

            # Create development dummy roles
            if self.settings.environment.lower() == "dev":
                # Create kissa dummy role
                _q = self.settings.sqlite_insert_into_enrollment.format(
                    work_id="kissa",
                    work_id_hash="kissa123",
                    state="ReadyForDelivery",
                    accepted="somehashwhoaccepted_this",
                    dl_link="https://www.kuvaton.com/kuvei/asiakkaamme_kissa.jpg",
                )
                self.run_command(_q)
                # Create koira dummy role
                _q = self.settings.sqlite_insert_into_enrollment.format(
                    work_id="koira", work_id_hash="koira123", state="init", accepted="", dl_link=""
                )
                self.run_command(_q)
                _q = self.settings.sqlite_insert_into_enrollment.format(
                    work_id="porakoira", work_id_hash="porakoira123", state="init", accepted="", dl_link=""
                )
                self.run_command(_q)

        else:
            LOGGER.critical("Error! cannot create the database connection.")


class Settings(BaseSettings):  # pylint: disable=too-few-public-methods
    """
    Application settings.

    These parameters can be configured
    with environment variables.
    """

    class Config:  # pylint: disable=too-few-public-methods
        """Configuration of settings."""

        env_file = ".env"
        env_prefix = "RM_"
        env_file_encoding = "utf-8"

    host: str = "127.0.0.1"
    port: int = 8000
    # quantity of workers for uvicorn
    workers_count: int = 1
    # Enable uvicorn reloading
    reload: bool = False

    # Current environment
    environment: str = "dev"

    # Set log_level (str) and log_level_int (int) for later use
    # if log_level is not set, then log level will be DEBUG
    log_level: LogLevel = LogLevel.DEBUG
    log_level_int: int = logging.DEBUG
    if log_level == "INFO":
        log_level_int = logging.INFO
    elif log_level == "WARNING":
        log_level_int = logging.WARNING
    elif log_level == "ERROR":
        log_level_int = logging.ERROR
    elif log_level == "FATAL":
        log_level_int = logging.FATAL

    # Api access management
    api_client_cert_header: str = "X-ClientCert-DN"
    test_api_client_cert_header_value: str = "TODO_CREATE_PKI_THAT_CAN_BE_PARSED_WITH__from_rfc4514_string"

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
    sqlite_init_management_hash: str = "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1"

    sqlite_enrollement_table_schema = """ CREATE TABLE IF NOT EXISTS enrollment (
                                        id integer PRIMARY KEY AUTOINCREMENT,
                                        work_id text NOT NULL,
                                        work_id_hash text NOT NULL,
                                        state text NOT NULL,
                                        accepted text NOT NULL,
                                        dl_link text NOT NULL
                                    ); """

    sqlite_management_table_schema = """ CREATE TABLE IF NOT EXISTS management (
                                        id integer PRIMARY KEY AUTOINCREMENT,
                                        management_hash text NOT NULL,
                                        special_rules text NOT NULL
                                    ); """

    sqlite_insert_into_enrollment = """ INSERT INTO enrollment
                                        (work_id, work_id_hash, state, accepted, dl_link)
                                        VALUES('{work_id}','{work_id_hash}','{state}', '{accepted}', '{dl_link}')
                                    ;"""
    sqlite_insert_into_management = """ INSERT INTO management
                                        (management_hash, special_rules)
                                        VALUES('{management_hash}','{special_rules}')
                                    ;"""
    sqlite_sel_from_enrollment = """SELECT work_id, work_id_hash, state, accepted, dl_link
                                        FROM enrollment
                                        WHERE work_id='{work_id}'
                                    ;"""

    sqlite_sel_from_enrollment_where_hash = """SELECT work_id, work_id_hash, state, accepted, dl_link
                                        FROM enrollment
                                        WHERE work_id_hash='{work_id_hash}'
                                    ;"""

    sqlite_sel_from_management = """SELECT management_hash, special_rules FROM management
                                        WHERE management_hash='{management_hash}'
                                    ;"""

    sqlite_update_accept_enrollment = """UPDATE enrollment
                                        SET accepted='{enroll_str}'
                                        WHERE work_id_hash='{work_id_hash}'
                                    ;"""
    sqlite_update_enrollment_dl_link = """UPDATE enrollment
                                        SET dl_link='{download_link}'
                                        WHERE work_id_hash='{work_id_hash}' OR work_id='{work_id}'
                                    ;"""

    sqlite_update_enrollment_state = """UPDATE enrollment
                                        SET state='{state}'
                                        WHERE work_id_hash='{work_id_hash}' OR work_id='{work_id}'
                                    ;"""

    # https://github.com/SAML-Toolkits/python3-saml/tree/master
    saml_settings = {
        "strict": False,  # can set to True to see problems such as Time skew/drift
        "debug": True,
        "idp": {
            "entityId": "test-saml-client",
            "singleSignOnService": {
                "url": "http://127.0.0.1:8080/auth/realms/test/protocol/saml",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect",
            },
            "x509cert": "MIIClzCCAX8CBgF6A0sAhDANBgkqhkiG9w0BAQsFADAPMQ0wCwYDVQQDDAR0ZXN0MB4XDTIxMDYxMzAyNTMwNFo\
XDTMxMDYxMzAyNTQ0NFowDzENMAsGA1UEAwwEdGVzdDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAK97NlCcNOhtH0a0wz5bo\
YKb7TaxogxnlyysOWUre1uI8SC6EBV3G5DHMdg4aWXwuXwy61+JJu70xNzJj155MJ+atGS7eLrxxGl0DNoLu/LU7Vhht+j09MZt5J60DnS7\
6H3pkvzAtRfd1P/d5JEFzWYkI4drBJccYX/nrrx2KZBkXOjwjVcEhsyK5ykA0LX+M+yFDy2w8qEWhxHuSL6enzw8IZ7qdtsF8SHqw7cdCgCJU6\
+0dxaRAAqmzMkO7BDEkwCJl0M8VaOPGo/SnZIAMYHLIUg1x0h/ecST4NPdqAwgDGtWAcD+Gp7Lr7xfBbKKqnLfg2PJdjs7Z0+NFOeVTvcC\
AwEAATANBgkqhkiG9w0BAQsFAAOCAQEAeJ2r2yoaQAo6v8MC6iAobOeJoBoezQg/OSQqeA9lygMWmGHpDIjSV7m3PCXwf5H9/NpHgBLt8y5\
PcjEs99uPfPeUBV/qitTFMuznMyr35e60iaHSdhZVjyCmrKgnIuGa07lng2wFabtpijqzbQJ99kYsWxbBDgbdVnt3jxohG1KKaXkGMyy7suwP\
gwrbwXfDrpyyj33NT/Dk/2W4Fjrjg8rIkuQypwB0SQLG1cZL9Z2AgW39JeVnP/sOH1gNpCCQwbpgE9hEed80jsYWlvucnFm2aHBtGV+/7/7N3q\
    RRpIvzrNVJoznqDDWU41RxS0NphAwX2ZqprWvN+SCEEhPGGQ==",
        },
        "sp": {
            "entityId": "test-saml-client",
            "assertionConsumerService": {
                "url": "http://127.0.0.1:3000/api/saml/callback",
                "binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST",
            },
            "x509cert": "MIIClzCCAX8CBgF6A0sAhDANBgkqhkiG9w0BAQsFADAPMQ0wCwYDVQQDDAR0ZXN0MB4XDTIxMDYxMzAyNTMwNFoXDTMxM\
DYxMzAyNTQ0NFowDzENMAsGA1UEAwwEdGVzdDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAK97NlCcNOhtH0a0wz5boYKb7TaxogxnlyysOW\
Ure1uI8SC6EBV3G5DHMdg4aWXwuXwy61+JJu70xNzJj155MJ+atGS7eLrxxGl0DNoLu/LU7Vhht+j09MZt5J60DnS76H3pkvzAtRfd1P/d5JEFzWYkI4d\
rBJccYX/nrrx2KZBkXOjwjVcEhsyK5ykA0LX+M+yFDy2w8qEWhxHuSL6enzw8IZ7qdtsF8SHqw7cdCgCJU6+0dxaRAAqmzMkO7BDEkwCJl0M8VaOPGo/S\
nZIAMYHLIUg1x0h/ecST4NPdqAwgDGtWAcD+Gp7Lr7xfBbKKqnLfg2PJdjs7Z0+NFOeVTvcCAwEAATANBgkqhkiG9w0BAQsFAAOCAQEAeJ2r2yoaQA\
o6v8MC6iAobOeJoBoezQg/OSQqeA9lygMWmGHpDIjSV7m3PCXwf5H9/NpHgBLt8y5PcjEs99uPfPeUBV/qitTFMuznMyr35e60iaHSdhZVjyCmrK\
gnIuGa07lng2wFabtpijqzbQJ99kYsWxbBDgbdVnt3jxohG1KKaXkGMyy7suwPgwrbwXfDrpyyj33NT/Dk/2W4Fjrjg8rIkuQypwB0SQLG1cZL\
9Z2AgW39JeVnP/sOH1gNpCCQwbpgE9hEed80jsYWlvucnFm2aHBtGV+/7/7N3qRRpIvzrNVJoznqDDWU41RxS0NphAwX2ZqprWvN+SCEEhPGGQ==",
        },
    }


settings = Settings()
sqlite = SqliteDB()
