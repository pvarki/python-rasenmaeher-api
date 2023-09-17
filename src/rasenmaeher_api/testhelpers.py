"""Helpers for testing, unit and manual"""
from typing import Tuple, List
import logging

from .sqlitedatabase import sqlite as sqlitewrapper


LOGGER = logging.getLogger(__name__)


def create_test_users() -> Tuple[List[str], List[str]]:
    """Create a few test users and work ids returns
    list of work-ids and their corresponding "hashes"

    First one has "enrollment" special role
    """
    # copied from the sqlitedb dev init so blame karppo :D
    work_ids: List[str] = []
    work_hashes: List[str] = []

    # PONDER: create random ones ?
    work_ids.append("pyteststuff")
    work_hashes.append("TestikalukalukalukaulinJotainAsdJotainJotainJotain")
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
        management_hash=work_hashes[-1],
        special_rules="enrollment",
        active=1,
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

    # Add initial 'first time user' hash that has permission to create admin users
    _q = sqlitewrapper.settings.sqlite_insert_into_management.format(
        management_hash=sqlitewrapper.settings.sqlite_first_time_user_hash, special_rules="first-user", active=1
    )
    sqlitewrapper.run_command(_q)

    # Add the 'first time user' code to jwt table if not there already
    _exchange_code = "HackHackHacatoneillaOnPorakoiraNukkumassa"
    _q = sqlitewrapper.settings.sqlite_jwt_sel_from_jwt_where_exchange.format(exchange_code=_exchange_code)
    _, _result = sqlitewrapper.run_command(_q)

    if len(_result) == 0:
        _q = sqlitewrapper.settings.sqlite_insert_into_jwt.format(
            claims='{"anon_admin_session":true}',
            consumed="no",
            work_id_hash="NA",
            work_id="NA",
            exchange_code=_exchange_code,
        )
    else:
        _q = sqlitewrapper.settings.sqlite_jwt_update_consumed_where_exchange.format(
            new_consumed_state="no", exchange_code=_exchange_code
        )
    sqlitewrapper.run_command(_q)

    return work_ids, work_hashes
