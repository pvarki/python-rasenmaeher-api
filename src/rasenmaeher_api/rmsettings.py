""" Application settings. """
from typing import Optional, Any, Dict, ClassVar
import enum
import os
import logging
import json

from pydantic import BaseSettings

LOGGER = logging.getLogger(__name__)


class LogLevel(str, enum.Enum):  # noqa: WPS600
    """Possible log levels."""

    NOTSET = "NOTSET"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    FATAL = "FATAL"


class RMSettings(BaseSettings):  # pylint: disable=too-few-public-methods
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
    test_api_client_cert_header_value: str = "CN=fake.localmaeher.pvarki.fi,O=N/A"
    api_healthcheck_proto: str = "http://"
    api_healthcheck_url: str = "/api/v1/healthcheck"
    api_healthcheck_headers: str = '{"propably":"not_needed"}'

    # Sentry's configuration.
    sentry_dsn: Optional[str] = None
    sentry_sample_rate: float = 1.0

    # Cfssl configuration
    cfssl_host: str = "http://127.0.0.1"
    cfssl_port: str = "8888"

    persistent_data_dir = "/data/persistent"

    # mtls
    mtls_client_cert_path: Optional[str] = None
    mtls_client_key_path: Optional[str] = None
    mtls_client_cert_cn = "rasenmaeher"

    # Keycloak configuration.
    keycloak_server_url: Optional[str] = None
    keycloak_client_id: Optional[str] = None
    keycloak_realm_name: Optional[str] = None
    keycloak_client_secret: Optional[str] = None

    # LDAP configuration
    ldap_conn_string: Optional[str] = None
    ldap_username: Optional[str] = None
    ldap_client_secret: Optional[str] = None

    _singleton: ClassVar[Optional["RMSettings"]] = None

    @classmethod
    def singleton(cls) -> "RMSettings":
        """Return singleton"""
        if not RMSettings._singleton:
            RMSettings._singleton = RMSettings()
        return RMSettings._singleton


switchme_to_singleton_call = RMSettings()
