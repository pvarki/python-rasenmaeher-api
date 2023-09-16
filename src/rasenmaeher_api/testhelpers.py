"""Helpers for testing, unit and manual"""
from typing import Tuple, List
import logging

from .sqlitedatabase import sqlite as sqlitewrapper
from .settings import settings


LOGGER = logging.getLogger(__name__)


def create_test_users() -> Tuple[List[str], List[str]]:
    """Create a few test users and work ids returns
    list of work-ids and their corresponding "hashes"

    First one has "enrollment" special role
    """
    # copied from the sqlitedb dev init so blame karppo :D
    work_ids: List[str] = []
    work_hashes: List[str] = []

    # FIXME: do not put these to settings
    work_ids.append(settings.sqlite_init_testing_management_username)
    work_hashes.append(settings.sqlite_init_testing_management_hash)
    # Create test admin credentials
    _q = sqlitewrapper.settings.sqlite_insert_into_enrollment.format(
        work_id=work_ids[-1],
        work_id_hash=work_hashes[-1],
        state="ReadyForDelivery",
        accepted="somehashwhoaccepted_this",
        cert_dl_link="https://www.kuvaton.com/kuvei/asiakkaamme_kissa.jpg",
        cert_howto_dl_link="https://www.kuvaton.com/kuvei/asiakkaamme_kissa.jpg",
        mtls_test_link="https://www.kuvaton.com/kuvei/asiakkaamme_kissa.jpg",
        verification_code="",
        locked="",
    )
    sqlitewrapper.run_command(_q)
    _q = sqlitewrapper.settings.sqlite_insert_into_management.format(
        management_hash=sqlitewrapper.settings.sqlite_init_testing_management_hash, special_rules="enrollment"
    )
    sqlitewrapper.run_command(_q)

    work_ids.append("kissa")
    work_hashes.append("kissa123")
    # Create kissa dummy role
    _q = sqlitewrapper.settings.sqlite_insert_into_enrollment.format(
        work_id=work_ids[-1],
        work_id_hash=work_hashes[-1],
        state="ReadyForDelivery",
        accepted="somehashwhoaccepted_this",
        cert_dl_link="https://www.kuvaton.com/kuvei/asiakkaamme_kissa.jpg",
        cert_howto_dl_link="https://www.kuvaton.com/kuvei/asiakkaamme_kissa.jpg",
        mtls_test_link="https://www.kuvaton.com/kuvei/asiakkaamme_kissa.jpg",
        verification_code="",
        locked="",
    )
    sqlitewrapper.run_command(_q)

    work_ids.append("koira")
    work_hashes.append("koira123")
    # Create koira dummy role
    _q = sqlitewrapper.settings.sqlite_insert_into_enrollment.format(
        work_id=work_ids[-1],
        work_id_hash=work_hashes[-1],
        state="init",
        accepted="",
        cert_dl_link="",
        cert_howto_dl_link="",
        mtls_test_link="",
        verification_code="",
        locked="",
    )
    sqlitewrapper.run_command(_q)
    work_ids.append("koira")
    work_hashes.append("koira123")
    _q = sqlitewrapper.settings.sqlite_insert_into_enrollment.format(
        work_id=work_ids[-1],
        work_id_hash=work_hashes[-1],
        state="init",
        accepted="",
        cert_dl_link="",
        cert_howto_dl_link="",
        mtls_test_link="",
        verification_code="",
        locked="",
    )
    sqlitewrapper.run_command(_q)
    return work_ids, work_hashes
