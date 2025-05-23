"""Application settings."""

from typing import Optional, Any, Dict, ClassVar, List
import enum
from pathlib import Path
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
    integration_api_timeout: float = 3.0

    # Api access management
    api_client_cert_header: str = "X-ClientCert-DN"
    test_api_client_cert_header_value: str = "CN=fake.localmaeher.dev.pvarki.fi,O=N/A"
    api_healthcheck_proto: str = "http://"
    api_healthcheck_url: str = "/api/v1/healthcheck"
    api_healthcheck_headers: str = '{"probably":"not_needed"}'

    # Sentry's configuration.
    sentry_dsn: Optional[str] = None
    sentry_sample_rate: float = 1.0

    # Cfssl configuration
    cfssl_host: str = "http://127.0.0.1"
    cfssl_port: str = "8888"
    ocsprest_host: str = "http://127.0.0.1"
    ocsprest_port: str = "8887"
    cfssl_timeout: float = 2.5

    persistent_data_dir = "/data/persistent"

    # mtls
    mtls_client_cert_path: Optional[str] = None
    mtls_client_key_path: Optional[str] = None
    mtls_client_cert_cn = "rasenmaeher"

    # LDAP configuration
    ldap_conn_string: Optional[str] = None
    ldap_username: Optional[str] = None
    ldap_client_secret: Optional[str] = None

    # Tilauspalvelu integration
    tilauspalvelu_jwt: str = "https://tilaa.pvarki.fi/api/v1/config/jwtPublicKey.pem"
    kraftwerk_announce: Optional[str] = None  # When KRAFTWERK actually exists
    kraftwerk_timeout: float = 2.0

    # keycloak integration
    kc_url: str = "http://keycloak:8080"
    kc_username: str = "admin"
    kc_password: Optional[str] = None
    kc_user_realm: str = "master"  # Which realm to use to auth the user
    kc_realm: str = "RASENMAEHER"  # In which realm the real users are
    kc_enabled: bool = True  # Whether to use KC or not (mainly so that unit tests have less dependencies for now)

    # Enrollment code generation related
    code_size: int = 8
    code_avoid_confusion: bool = True  # Replace 1 and 0 with O and I to avoid confusion

    _singleton: ClassVar[Optional["RMSettings"]] = None

    @classmethod
    def singleton(cls) -> "RMSettings":
        """Return singleton"""
        if not RMSettings._singleton:
            RMSettings._singleton = RMSettings()
        return RMSettings._singleton

    def __init__(self, *args: List[Any], **kwargs: Dict[str, Any]) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        # FIXME: When the switchme_to_singleton_call has been removed call load_manifest here

    def load_manifest(self) -> None:
        """Load the kraftwerk manifest file"""
        if self.kraftwerk_manifest_bool:
            return
        pth = Path(self.kraftwerk_manifest_path)
        if not pth.exists():
            raise ValueError(f"{self.kraftwerk_manifest_path} does not exist")
        self.kraftwerk_manifest_dict = json.loads(pth.read_text(encoding="utf-8"))
        self.kraftwerk_manifest_bool = True

    @property
    def deployment_name(self) -> str:
        """Resolve the deployment name"""
        if not self.kraftwerk_manifest_bool:
            self.load_manifest()
        if "dns" in self.kraftwerk_manifest_dict:
            my_dn = str(self.kraftwerk_manifest_dict["dns"])
            return my_dn.split(".", maxsplit=1)[0]
        LOGGER.warning("DNS name not defined")
        return "undefined"

    @property
    def valid_product_cns(self) -> List[str]:
        """Get valid CNs for productapi certs"""
        self.load_manifest()
        return [product["certcn"] for product in self.kraftwerk_manifest_dict["products"].values()]


switchme_to_singleton_call = RMSettings.singleton()  # pylint: disable=C0103
