"""Tests enrollment invitecode validations"""
from typing import Tuple, Dict
import logging

import requests

LOGGER = logging.getLogger(__name__)


# FIXME: openapi.json 2023-09-10: invalid doc: '.../invitecode?code=xxx...': '?code' -> '?invitecode'
def test_not_used_invite_code(
    localmaeher_api: Tuple[str, str, float], testdata: Dict[str, str]
) -> None:
    """Tests that we can check invite_code is usable"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/enrollment/invitecode?invitecode={testdata['invite_code']}"
    response = requests.get(
        url, json=None, headers=None, verify=False, timeout=localmaeher_api[2]
    )
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status_code == 200
    assert payload["invitecode_is_active"] is False


def test_invalid_invite_code_enroll(
    localmaeher_api: Tuple[str, str, float],
    testdata: Dict[str, str],
    error_messages: Dict[str, str],
) -> None:
    """Tests that we cannot enroll non-existent work_id and invite_code"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/enrollment/invitecode/enroll"
    data = {
        "invitecode": f"{testdata['invite_code']}",
        "work_id": f"{testdata['invite_code_work_id1']}",
    }
    response = requests.post(
        url, json=data, headers=None, verify=False, timeout=localmaeher_api[2]
    )
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status_code == 400
    assert payload["detail"] == error_messages["INVITECODE_NOT_VALID"]


def test_invalid_user_hash_invite_code_create(
    localmaeher_api: Tuple[str, str, float],
    testdata: Dict[str, str],
    error_messages: Dict[str, str],
) -> None:
    """Tests that we cannot create a new invite code using invalid user management hash"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/enrollment/invitecode/create"
    data = {
        "user_management_hash": f"{testdata['invite_code_invalid_user_hash']}",
    }
    response = requests.post(
        url, json=data, headers=None, verify=False, timeout=localmaeher_api[2]
    )
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status_code == 403
    assert payload["detail"] == error_messages["NO_ENROLLMENT_PERMISSIONS"]
