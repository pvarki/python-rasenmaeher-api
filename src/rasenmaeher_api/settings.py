""" Application settings. """
import enum
import os
import logging
import json
from pathlib import Path
from tempfile import gettempdir
from typing import Optional, Any, Dict
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
    reload: bool = True

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

    # Manifest file from kraftwerk
    integration_api_port: int = 4625
    kraftwerk_manifest_path: str = "/pvarki/kraftwerk-rasenmaeher-init.json"
    kraftwerk_manifest_bool: bool = False
    kraftwerk_manifest_dict: Dict[Any, Any] = {}
    if os.path.exists(kraftwerk_manifest_path):
        with open(kraftwerk_manifest_path, encoding="utf8") as _f:
            try:
                kraftwerk_manifest_dict = json.load(_f)
                kraftwerk_manifest_bool = True
            except ValueError as _e:
                LOGGER.fatal("JSON malformed in kraftwerk_manifest_path {} : {}".format(kraftwerk_manifest_path, _e))

    # Api access management
    api_client_cert_header: str = "X-ClientCert-DN"
    test_api_client_cert_header_value: str = "TODO_CREATE_PKI_THAT_CAN_BE_PARSED_WITH__from_rfc4514_string"
    api_healthcheck_proto: str = "http://"
    api_healthcheck_url: str = "/api/v1/healthcheck"
    api_healthcheck_headers: str = '{"propably":"not_needed"}'

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

    # Initial shared secret between services (provided by kraftwerk)
    sqlite_init_management_hash: str = "PaulinTaikaKaulinOnKaunis_PaulisMagicPinIsBuuutiful!11!1"
    # Initial 'One time' code used to create first admin accounts (provided by kraftwerk)
    sqlite_first_time_user_hash: str = "PerPerPerjantaiPulloParisee"

    # Sqlite configurations
    sqlite_filepath_prod: str = "/data/persistent/sqlite/rm_db.sql"  # nosec B108 - "hardcoded_tmp_directory"
    sqlite_filepath_dev: str = "/tmp/rm_db.sql"  # nosec B108 - "hardcoded_tmp_directory"

    sqlite_enrollement_table_schema = """ CREATE TABLE IF NOT EXISTS enrollment (
                                        id integer PRIMARY KEY AUTOINCREMENT,
                                        work_id text NOT NULL,
                                        work_id_hash text NOT NULL,
                                        state text NOT NULL,
                                        accepted text NOT NULL,
                                        cert_dl_link text NOT NULL,
                                        cert_howto_dl_link text NOT NULL,
                                        mtls_test_link text NOT NULL,
                                        verification_code text NOT NULL,
                                        UNIQUE(work_id)
                                    ); """

    sqlite_management_table_schema = """ CREATE TABLE IF NOT EXISTS management (
                                        id integer PRIMARY KEY AUTOINCREMENT,
                                        management_hash text NOT NULL,
                                        special_rules text NOT NULL,
                                        UNIQUE(management_hash)
                                    ); """

    sqlite_services_table_schema = """ CREATE TABLE IF NOT EXISTS services (
                                        id integer PRIMARY KEY AUTOINCREMENT,
                                        service_name text NOT NULL,
                                        init_state text NOT NULL,
                                        endpoint_proto_host_port text NOT NULL,
                                        healthcheck_url text NOT NULL,
                                        healthcheck_headers text NOT NULL,
                                        UNIQUE(service_name)
                                    ); """

    sqlite_insert_into_services = """ INSERT OR REPLACE INTO services
                                        (service_name,
                                        init_state,
                                        endpoint_proto_host_port,
                                        healthcheck_url,
                                        healthcheck_headers
                                        )
                                        VALUES(
                                            '{service_name}',
                                            '{init_state}',
                                            '{endpoint_proto_host_port}',
                                            '{healthcheck_url}',
                                            '{healthcheck_headers}'
                                        )
                                    ;"""

    sqlite_sel_from_services = """SELECT service_name, init_state, endpoint_proto_host_port,
                                         healthcheck_url, healthcheck_headers
                                    FROM services
                                ;"""

    sqlite_insert_into_enrollment = """ INSERT INTO enrollment
                                        (work_id, work_id_hash, state, accepted, cert_dl_link, cert_howto_dl_link, mtls_test_link, verification_code)
                                        VALUES('{work_id}','{work_id_hash}','{state}', '{accepted}', '{cert_dl_link}', '{cert_howto_dl_link}', '{mtls_test_link}', '{verification_code}')
                                    ;"""

    sqlite_insert_into_management = """ INSERT OR REPLACE INTO management
                                        (management_hash, special_rules)
                                        VALUES('{management_hash}','{special_rules}')
                                    ;"""

    sqlite_sel_from_enrollment = """SELECT
    work_id, work_id_hash, state, accepted, cert_dl_link, cert_howto_dl_link, mtls_test_link, verification_code
                                        FROM enrollment
                                        WHERE work_id='{work_id}'
                                    ;"""

    sqlite_sel_from_enrollment_all = """SELECT
    work_id, work_id_hash, state, accepted, cert_dl_link, cert_howto_dl_link, mtls_test_link, verification_code
                                        FROM enrollment
                                    ;"""

    sqlite_sel_from_enrollment_where_hash = """SELECT
    work_id, work_id_hash, state, accepted, cert_dl_link, cert_howto_dl_link, mtls_test_link, verification_code
                                        FROM enrollment
                                        WHERE work_id_hash='{work_id_hash}'
                                    ;"""

    sqlite_sel_from_management = """SELECT management_hash, special_rules FROM management
                                        WHERE management_hash='{management_hash}'
                                    ;"""

    sqlite_sel_from_management_where_special_rule_like = """
                                        SELECT management_hash, special_rules FROM management
                                        WHERE special_rules LIKE '%{special_rules}%'
                                    ;"""

    sqlite_del_from_management_where_special_rule_like = """
                                        DELETE FROM management
                                        WHERE special_rules LIKE '%{special_rules}%'
                                    ;"""

    sqlite_update_from_management_where_special_rule_like = """
                                        UPDATE management
                                        SET special_rules='{new_special_rules}'
                                        WHERE special_rules LIKE '{special_rules}'
                                    ;"""

    sqlite_del_from_management_where_hash = """
                                        DELETE FROM management
                                        WHERE management_hash='{management_hash}'
                                    ;"""

    sqlite_del_from_enrollment_where_hash = """DELETE FROM enrollment
                                        WHERE work_id_hash='{work_id_hash}'
                                    ;"""

    sqlite_update_accept_enrollment = """UPDATE enrollment
                                        SET accepted='{management_hash}'
                                        WHERE work_id_hash='{work_id_hash}'
                                    ;"""

    sqlite_update_enrollment_cert_dl_link = """UPDATE enrollment
                                        SET cert_dl_link='{cert_download_link}'
                                        WHERE work_id_hash='{work_id_hash}' OR work_id='{work_id}'
                                    ;"""
    sqlite_update_enrollment_cert_howto_dl_link = """UPDATE enrollment
                                        SET cert_howto_dl_link='{howto_download_link}'
                                        WHERE work_id_hash='{work_id_hash}' OR work_id='{work_id}'
                                    ;"""
    sqlite_update_enrollment_mtls_test_link = """UPDATE enrollment
                                        SET mtls_test_link='{mtls_test_link}'
                                        WHERE work_id_hash='{work_id_hash}' OR work_id='{work_id}'
                                    ;"""
    sqlite_update_enrollment_mtls_test_link_all = """UPDATE enrollment
                                        SET mtls_test_link='{mtls_test_link}'
                                        WHERE work_id_hash IS NOT NULL
                                    ;"""

    sqlite_update_enrollment_state = """UPDATE enrollment
                                        SET state='{state}'
                                        WHERE work_id_hash='{work_id_hash}' OR work_id='{work_id}'
                                    ;"""

    sqlite_update_enrollment_verification_code = """UPDATE enrollment
                                        SET verification_code='{verification_code}'
                                        WHERE work_id_hash='{work_id_hash}' OR work_id='{work_id}'
                                    ;"""

    sqlite_healtcheck_query = """SELECT id
                                        FROM management
                                        LIMIT 2
                                    ;"""


settings = Settings()
