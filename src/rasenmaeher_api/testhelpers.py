"""Helpers for testing, unit and manual"""
from typing import Tuple, List
import logging

from .db import Person, Enrollment, LoginCode

LOGGER = logging.getLogger(__name__)


async def create_test_users() -> Tuple[List[str], List[str]]:
    """Create a few test users and work ids returns
    list of work-ids and their corresponding jwt tokens
    """
    work_ids: List[str] = []
    jwt_tokens: List[str] = []

    # Create "anon_admin", this is also done in /firstuser/add-admin if one not exists yet
    # anon_admin is only used to "approve" the newly created admin users. Aka user for "anon_admin_session".
    _anon_admin_added = await Person.is_callsign_available(callsign="anon_admin")
    if _anon_admin_added is False:
        _anon_user = await Person.create_with_cert(callsign="anon_admin", extra={})
        _ = await _anon_user.assign_role(role="anon_admin")

    _anon_admin_user = await Person.by_callsign(callsign="anon_admin")

    # CREATE USER secondadmin
    # approved, admin role, approved by anon_admin
    _enrollment_pyteststuff = await Enrollment.create_for_callsign(callsign="pyteststuff", pool=None, extra={})
    _user_pyteststuff = await _enrollment_pyteststuff.approve(approver=_anon_admin_user)
    _ = await _user_pyteststuff.assign_role(role="admin")
    _jwt_pyteststuff = await LoginCode.create_for_claims(claims={"sub": "pyteststuff"})
    work_ids.append("pyteststuff")
    jwt_tokens.append(_jwt_pyteststuff)

    # CREATE USER secondadmin
    # approved, admin role, approved by pyteststuff
    _enrollment_secondadmin = await Enrollment.create_for_callsign(callsign="secondadmin", pool=None, extra={})
    _user_secondadmin = await _enrollment_secondadmin.approve(approver=_user_pyteststuff)
    _ = await _user_secondadmin.assign_role(role="admin")
    _jwt_secondadmin = await LoginCode.create_for_claims(claims={"sub": "secondadmin"})
    work_ids.append("secondadmin")
    jwt_tokens.append(_jwt_secondadmin)

    # CREATE USER kissa
    # approved, approved by secondadmin
    _enrollment_kissa = await Enrollment.create_for_callsign(callsign="kissa", pool=None, extra={})
    _ = await _enrollment_kissa.approve(approver=_user_secondadmin)
    _jwt_kissa = await LoginCode.create_for_claims(claims={"sub": "kissa"})
    work_ids.append("kissa")
    jwt_tokens.append(_jwt_kissa)

    # CREATE USER koira
    # not approved
    _ = await Enrollment.create_for_callsign(callsign="koira", pool=None, extra={})
    _jwt_koira = await LoginCode.create_for_claims(claims={"sub": "koira"})
    work_ids.append("koira")
    jwt_tokens.append(_jwt_koira)

    # TODO CREATE POOL FOR secondadmin

    return work_ids, jwt_tokens
