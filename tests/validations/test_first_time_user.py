"""Tests the firstuser"""
from typing import Tuple, Dict
import logging

import aiohttp
import pytest

from ..conftest import DEFAULT_TIMEOUT

LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_check_valid_code(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
) -> None:
    """Tests that we can check valid temp_admin_code"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/check-code?temp_admin_code={testdata['user_hash']}"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status == 200
    assert payload["code_ok"] is True


@pytest.mark.asyncio
async def test_check_invalid_code(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
) -> None:
    """Tests that we can check invalid temp_admin_code"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/check-code?temp_admin_code=asdfökj34342242ääasdfa35r"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status == 200
    assert payload["code_ok"] is False


@pytest.mark.asyncio
async def test_empty_admin_list(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
    error_messages: Dict[str, str],
) -> None:
    """Tests that we can have an empty list without any id's and hashes"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/list-admin?temp_admin_code={testdata['user_hash']}"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status == 404
    assert payload["detail"] == error_messages["NO_USERS_FOUND"]


@pytest.mark.asyncio
async def test_firstuser_add_admin(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
) -> None:
    """Tests that we can add firstuser admin"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/add-admin"
    data = {
        "temp_admin_code": f"{testdata['user_hash']}",
        "work_id": f"{testdata['first_time_user_work_id1']}",
    }
    LOGGER.debug("Fetching {}".format(url))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))


@pytest.mark.asyncio
async def test_duplicate_firstuser_admin(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
) -> None:
    """Tests failure if firstuser admin already exists"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/add-admin"
    data = {
        "temp_admin_code": f"{testdata['user_hash']}",
        "work_id": f"{testdata['first_time_user_work_id1']}",
    }
    LOGGER.debug("Fetching {}".format(url))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status == 500


@pytest.mark.asyncio
async def test_one_item_admin_list(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
) -> None:
    """Tests that we can have one item in the admin list"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/list-admin?temp_admin_code={testdata['user_hash']}"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert (
        payload["admin_list"][0]["work_id"] == f"{testdata['first_time_user_work_id1']}"
    )
    assert payload["admin_list"][0]["work_id_hash"] != ""


@pytest.mark.asyncio
async def test_firstuser_is_active(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
) -> None:
    """Tests firstuser is active"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/is-active"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["api_is_active"] is True


@pytest.mark.asyncio
async def test_disable_firstuser(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
) -> None:
    """Tests that we can disable firstuser"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/disable"
    data = {"permit_str": f"{testdata['permit_str']}"}
    LOGGER.debug("Fetching {}".format(url))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["api_disabled"] is True


@pytest.mark.asyncio
async def test_firstuser_is_not_active(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
) -> None:
    """Tests firstuser is not active"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/is-active"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["api_is_active"] is False


@pytest.mark.asyncio
async def test_delete_disabled_firstuser(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
    error_messages: Dict[str, str],
) -> None:
    """Tests that we cannot delete disabled firstuser"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/delete-admin"
    data = {
        "temp_admin_code": f"{testdata['user_hash']}",
        "work_id": f"{testdata['first_time_user_work_id1']}",
    }
    LOGGER.debug("Fetching {}".format(url))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status == 410
    assert payload["detail"] == error_messages["FIRSTUSER_API_IS_DISABLED"]


@pytest.mark.asyncio
async def test_disabled_admin_list(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
    error_messages: Dict[str, str],
) -> None:
    """Tests that we cannot list disabled admin"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/list-admin?temp_admin_code={testdata['user_hash']}"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status == 410
    assert payload["detail"] == error_messages["FIRSTUSER_API_IS_DISABLED"]


@pytest.mark.asyncio
async def test_disabled_add_admin(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
    error_messages: Dict[str, str],
) -> None:
    """Tests that we cannot add firstuser if admin is disabled"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/add-admin"
    data = {
        "temp_admin_code": f"{testdata['user_hash']}",
        "work_id": f"{testdata['first_time_user_work_id2']}",
    }
    LOGGER.debug("Fetching {}".format(url))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status == 410
    assert payload["detail"] == error_messages["FIRSTUSER_API_IS_DISABLED"]


@pytest.mark.asyncio
async def test_enable_firstuser(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
) -> None:
    """Tests that we can enable disabled firstuser"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/enable"
    data = {"permit_str": f"{testdata['permit_str']}"}
    LOGGER.debug("Fetching {}".format(url))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["api_enabled"] is True


@pytest.mark.asyncio
async def test_enabled_admin_list(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
) -> None:
    """Tests that we can have admin list after firstuser activation"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/list-admin?temp_admin_code={testdata['user_hash']}"
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert (
        payload["admin_list"][0]["work_id"] == f"{testdata['first_time_user_work_id1']}"
    )
    assert payload["admin_list"][0]["work_id_hash"] != ""


@pytest.mark.asyncio
async def test_another_firstuser_add_admin(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
) -> None:
    """Tests that we can add firstuser admin"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/add-admin"
    data = {
        "temp_admin_code": f"{testdata['user_hash']}",
        "work_id": f"{testdata['first_time_user_work_id2']}",
    }
    LOGGER.debug("Fetching {}".format(url))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))


@pytest.mark.asyncio
async def test_two_firstusers_admin_list(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
) -> None:
    """Tests that we can have admin list after firstuser activation"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/list-admin?temp_admin_code={testdata['user_hash']}"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert (
        payload["admin_list"][0]["work_id"] == f"{testdata['first_time_user_work_id1']}"
    )
    assert payload["admin_list"][0]["work_id_hash"] != ""
    assert (
        payload["admin_list"][1]["work_id"] == f"{testdata['first_time_user_work_id2']}"
    )
    assert payload["admin_list"][1]["work_id_hash"] != ""


@pytest.mark.asyncio
async def test_delete_enabled_firstuser(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
) -> None:
    """Tests that we delete enabled firstuser"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/delete-admin"
    data = {
        "temp_admin_code": f"{testdata['user_hash']}",
        "work_id": f"{testdata['first_time_user_work_id1']}",
    }
    LOGGER.debug("Fetching {}".format(url))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["admin_removed"] is True


@pytest.mark.asyncio
async def test_delete_another_enabled_firstuser(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
) -> None:
    """Tests that we delete another enabled firstuser"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/delete-admin"
    data = {
        "temp_admin_code": f"{testdata['user_hash']}",
        "work_id": f"{testdata['first_time_user_work_id2']}",
    }
    LOGGER.debug("Fetching {}".format(url))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["admin_removed"] is True
