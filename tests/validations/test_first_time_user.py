"""Tests the firstuser"""
from typing import Tuple, Dict
import logging

import requests

LOGGER = logging.getLogger(__name__)


def test_check_valid_code(
    localmaeher_api: Tuple[str, str], testdata: Dict[str, str]
) -> None:
    """Tests that we can check valid temp_admin_code"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/check-code?temp_admin_code={testdata['user_hash']}"
    response = requests.get(url, json=None, headers=None, verify=False, timeout=2.0)
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status_code == 200
    assert payload["code_ok"] is True


def test_check_invalid_code(localmaeher_api: Tuple[str, str]) -> None:
    """Tests that we can check invalid temp_admin_code"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/check-code?temp_admin_code=asdfökj34342242ääasdfa35r"
    response = requests.get(url, json=None, headers=None, verify=False, timeout=2.0)
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status_code == 200
    assert payload["code_ok"] is False


def test_empty_admin_list(
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
    error_messages: Dict[str, str],
) -> None:
    """Tests that we can have an empty list without any id's and hashes"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/list-admin?temp_admin_code={testdata['user_hash']}"
    response = requests.get(url, json=None, headers=None, verify=False, timeout=2.0)
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status_code == 404
    assert payload["detail"] == error_messages["NO_USERS_FOUND"]


def test_firstuser_add_admin(
    localmaeher_api: Tuple[str, str], testdata: Dict[str, str]
) -> None:
    """Tests that we can add firstuser admin"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/add-admin"
    data = {
        "temp_admin_code": f"{testdata['user_hash']}",
        "work_id": f"{testdata['first_time_user_work_id1']}",
    }
    response = requests.post(url, json=data, headers=None, verify=False, timeout=2.0)
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status_code == 200


def test_duplicate_firstuser_admin(
    localmaeher_api: Tuple[str, str], testdata: Dict[str, str]
) -> None:
    """Tests failure if firstuser admin already exists"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/add-admin"
    data = {
        "temp_admin_code": f"{testdata['user_hash']}",
        "work_id": f"{testdata['first_time_user_work_id1']}",
    }
    response = requests.post(url, json=data, headers=None, verify=False, timeout=2.0)
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status_code == 500


def test_one_item_admin_list(
    localmaeher_api: Tuple[str, str], testdata: Dict[str, str]
) -> None:
    """Tests that we can have one item in the admin list"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/list-admin?temp_admin_code={testdata['user_hash']}"
    response = requests.get(url, json=None, headers=None, verify=False, timeout=2.0)
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status_code == 200
    assert (
        payload["admin_list"][0]["work_id"] == f"{testdata['first_time_user_work_id1']}"
    )
    assert payload["admin_list"][0]["work_id_hash"] != ""


def test_firstuser_is_active(localmaeher_api: Tuple[str, str]) -> None:
    """Tests firstuser is active"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/is-active"
    response = requests.get(url, json=None, headers=None, verify=False, timeout=2.0)
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status_code == 200
    assert payload["api_is_active"] is True


def test_disable_firstuser(
    localmaeher_api: Tuple[str, str], testdata: Dict[str, str]
) -> None:
    """Tests that we can disable firstuser"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/disable"
    data = {"permit_str": f"{testdata['permit_str']}"}
    response = requests.post(url, json=data, headers=None, verify=False, timeout=2.0)
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status_code == 200
    assert payload["api_disabled"] is True


def test_firstuser_is_not_active(localmaeher_api: Tuple[str, str]) -> None:
    """Tests firstuser is not active"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/is-active"
    response = requests.get(url, json=None, headers=None, verify=False, timeout=2.0)
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status_code == 200
    assert payload["api_is_active"] is False


def test_delete_disabled_firstuser(
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
    error_messages: Dict[str, str],
) -> None:
    """Tests that we cannot delete disabled firstuser"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/delete-admin"
    data = {
        "temp_admin_code": f"{testdata['user_hash']}",
        "work_id": f"{testdata['first_time_user_work_id1']}",
    }
    response = requests.post(url, json=data, headers=None, verify=False, timeout=2.0)
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status_code == 410
    assert payload["detail"] == error_messages["FIRSTUSER_API_IS_DISABLED"]


def test_disabled_admin_list(
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
    error_messages: Dict[str, str],
) -> None:
    """Tests that we cannot list disabled admin"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/list-admin?temp_admin_code={testdata['user_hash']}"
    response = requests.get(url, json=None, headers=None, verify=False, timeout=2.0)
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status_code == 410
    assert payload["detail"] == error_messages["FIRSTUSER_API_IS_DISABLED"]


def test_disabled_add_admin(
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
    error_messages: Dict[str, str],
) -> None:
    """Tests that we cannot add firstuser if admin is disabled"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/add-admin"
    data = {
        "temp_admin_code": f"{testdata['user_hash']}",
        "work_id": f"{testdata['first_time_user_work_id2']}",
    }
    response = requests.post(url, json=data, headers=None, verify=False, timeout=2.0)
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status_code == 410
    assert payload["detail"] == error_messages["FIRSTUSER_API_IS_DISABLED"]


def test_enable_firstuser(
    localmaeher_api: Tuple[str, str], testdata: Dict[str, str]
) -> None:
    """Tests that we can enable disabled firstuser"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/enable"
    data = {"permit_str": f"{testdata['permit_str']}"}
    response = requests.post(url, json=data, headers=None, verify=False, timeout=2.0)
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status_code == 200
    assert payload["api_enabled"] is True


def test_enabled_admin_list(
    localmaeher_api: Tuple[str, str], testdata: Dict[str, str]
) -> None:
    """Tests that we can have admin list after firstuser activation"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/list-admin?temp_admin_code={testdata['user_hash']}"
    response = requests.get(url, json=None, headers=None, verify=False, timeout=2.0)
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status_code == 200
    assert (
        payload["admin_list"][0]["work_id"] == f"{testdata['first_time_user_work_id1']}"
    )
    assert payload["admin_list"][0]["work_id_hash"] != ""


def test_another_firstuser_add_admin(
    localmaeher_api: Tuple[str, str], testdata: Dict[str, str]
) -> None:
    """Tests that we can add firstuser admin"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/add-admin"
    data = {
        "temp_admin_code": f"{testdata['user_hash']}",
        "work_id": f"{testdata['first_time_user_work_id2']}",
    }
    response = requests.post(url, json=data, headers=None, verify=False, timeout=2.0)
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status_code == 200


def test_two_firstusers_admin_list(
    localmaeher_api: Tuple[str, str], testdata: Dict[str, str]
) -> None:
    """Tests that we can have admin list after firstuser activation"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/list-admin?temp_admin_code={testdata['user_hash']}"
    response = requests.get(url, json=None, headers=None, verify=False, timeout=2.0)
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status_code == 200
    assert (
        payload["admin_list"][0]["work_id"] == f"{testdata['first_time_user_work_id1']}"
    )
    assert payload["admin_list"][0]["work_id_hash"] != ""
    assert (
        payload["admin_list"][1]["work_id"] == f"{testdata['first_time_user_work_id2']}"
    )
    assert payload["admin_list"][1]["work_id_hash"] != ""


def test_delete_enabled_firstuser(
    localmaeher_api: Tuple[str, str], testdata: Dict[str, str]
) -> None:
    """Tests that we delete enabled firstuser"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/delete-admin"
    data = {
        "temp_admin_code": f"{testdata['user_hash']}",
        "work_id": f"{testdata['first_time_user_work_id1']}",
    }
    response = requests.post(url, json=data, headers=None, verify=False, timeout=2.0)
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status_code == 200
    assert payload["admin_removed"] is True


def test_delete_another_enabled_firstuser(
    localmaeher_api: Tuple[str, str], testdata: Dict[str, str]
) -> None:
    """Tests that we delete another enabled firstuser"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/delete-admin"
    data = {
        "temp_admin_code": f"{testdata['user_hash']}",
        "work_id": f"{testdata['first_time_user_work_id2']}",
    }
    response = requests.post(url, json=data, headers=None, verify=False, timeout=2.0)
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status_code == 200
    assert payload["admin_removed"] is True
