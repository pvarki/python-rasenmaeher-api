""" Application database. """
import os
import logging
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Tuple, List
import sqlite3
from .settings import settings

TEMP_DIR = Path(gettempdir())
LOGGER = logging.getLogger(__name__)


class SqliteDB:  # pylint: disable=too-few-public-methods
    """
    Application SqliteDB settings/connection

    """

    def __init__(self) -> None:
        self.settings = settings

        self.db_ok: bool = False

        if self.settings.environment.lower() == "dev":
            self.sqlite_filepath = self.settings.sqlite_filepath_dev
        else:
            self.sqlite_filepath = self.settings.sqlite_filepath_prod

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
            LOGGER.exception("SQLITE run command error : {}".format(_e))
            LOGGER.error("SQLITE QUERY : {}".format(sql_cmd))
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
            # Create tables using schema in config
            self.run_command(self.settings.sqlite_enrollement_table_schema)
            self.run_command(self.settings.sqlite_management_table_schema)
            self.run_command(self.settings.sqlite_services_table_schema)
            self.run_command(self.settings.sqlite_jwt_table_schema)

            # Add self to known services list
            _e = f"{self.settings.api_healthcheck_proto}{self.settings.host}:{self.settings.port}"
            _q = self.settings.sqlite_insert_into_services.format(
                service_name="rasenmaeher",
                init_state="init",
                endpoint_proto_host_port=_e,
                healthcheck_url=self.settings.api_healthcheck_url,
                healthcheck_headers=self.settings.api_healthcheck_headers,
            )
            self.run_command(_q)

            # Add services from manifest to known services list
            if settings.kraftwerk_manifest_bool is True:
                for name, conf in self.settings.kraftwerk_manifest_dict["products"].items():
                    _q = self.settings.sqlite_insert_into_services.format(
                        service_name=name,
                        init_state="init",
                        endpoint_proto_host_port=conf["api"],
                        healthcheck_url="/healthcheck",
                        healthcheck_headers='{"propably":"not_needed"}',
                    )
                    self.run_command(_q)

            # Add initial management hash that has permissions to enroll users etc
            _q = self.settings.sqlite_insert_into_management.format(
                management_hash=self.settings.sqlite_init_management_hash, special_rules="main", active=1
            )
            self.run_command(_q)

            # Add initial 'first time user' hash that has permission to create admin users
            _q = self.settings.sqlite_insert_into_management.format(
                management_hash=self.settings.sqlite_first_time_user_hash, special_rules="first-user", active=1
            )
            self.run_command(_q)

            # Add the 'first time user' code to jwt table if not there already
            _q = self.settings.sqlite_jwt_sel_from_jwt_where_exchange.format(
                exchange_code=self.settings.one_time_admin_code
            )
            _success, _result = self.run_command(_q)

            if _success is False:
                _reason = "Error in init! Database query failed. Undefined backend error q_init123"
                LOGGER.error("{}".format(_reason))
                raise RuntimeError(_reason)

            if len(_result) == 0:
                _q = self.settings.sqlite_insert_into_jwt.format(
                    claims='{"anon_admin_session":true}',
                    consumed="no",
                    work_id_hash="NA",
                    work_id="NA",
                    exchange_code=self.settings.one_time_admin_code,
                )
                _success, _result = self.run_command(_q)
                if _success is False:
                    _reason = "Error in init! Database query failed. Undefined backend error q_init223"
                    LOGGER.error("{}".format(_reason))
                    raise RuntimeError(_reason)

            # Create development dummy roles
            if self.settings.environment.lower() == "dev":
                # Create test admin credentials
                _q = self.settings.sqlite_insert_into_enrollment.format(
                    work_id=settings.sqlite_init_testing_management_username,
                    work_id_hash=settings.sqlite_init_testing_management_hash,
                    state="ReadyForDelivery",
                    accepted="somehashwhoaccepted_this",
                    cert_dl_link="https://www.kuvaton.com/kuvei/asiakkaamme_kissa.jpg",
                    cert_howto_dl_link="https://www.kuvaton.com/kuvei/asiakkaamme_kissa.jpg",
                    mtls_test_link="https://www.kuvaton.com/kuvei/asiakkaamme_kissa.jpg",
                    verification_code="",
                    locked="",
                )
                self.run_command(_q)
                _q = self.settings.sqlite_insert_into_management.format(
                    management_hash=self.settings.sqlite_init_testing_management_hash,
                    special_rules="enrollment",
                    active=1,
                )
                self.run_command(_q)

                # Create kissa dummy role
                _q = self.settings.sqlite_insert_into_enrollment.format(
                    work_id="kissa",
                    work_id_hash="kissa123",
                    state="ReadyForDelivery",
                    accepted="somehashwhoaccepted_this",
                    cert_dl_link="https://www.kuvaton.com/kuvei/asiakkaamme_kissa.jpg",
                    cert_howto_dl_link="https://www.kuvaton.com/kuvei/asiakkaamme_kissa.jpg",
                    mtls_test_link="https://www.kuvaton.com/kuvei/asiakkaamme_kissa.jpg",
                    verification_code="",
                    locked="",
                )
                self.run_command(_q)
                # Create koira dummy role
                _q = self.settings.sqlite_insert_into_enrollment.format(
                    work_id="koira",
                    work_id_hash="koira123",
                    state="init",
                    accepted="",
                    cert_dl_link="",
                    cert_howto_dl_link="",
                    mtls_test_link="",
                    verification_code="",
                    locked="",
                )
                self.run_command(_q)
                _q = self.settings.sqlite_insert_into_enrollment.format(
                    work_id="porakoira",
                    work_id_hash="porakoira123",
                    state="init",
                    accepted="",
                    cert_dl_link="",
                    cert_howto_dl_link="",
                    mtls_test_link="",
                    verification_code="",
                    locked="",
                )
                self.run_command(_q)

        else:
            LOGGER.critical("Error! cannot create the database connection.")


sqlite = SqliteDB()
