"""Tests the firstuser"""
from typing import Tuple, Dict
import logging

import aiohttp
import pytest

from ..conftest import DEFAULT_TIMEOUT

LOGGER = logging.getLogger(__name__)

# pylint: disable=too-few-public-methods
class ValueStorage:
    """Storage for values generated and used in this testsuite"""

    work_id = ""
    jwt = ""
    work_id_should_not_exist = "fasaani123"
    max_work_ids_to_create = 1000


@pytest.mark.asyncio
async def test_firstuser_add_admin(
    session_with_tpjwt: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    work_id_generator: str,
) -> None:
    """Tests that we can add firstuser admin"""
    client = session_with_tpjwt
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/add-admin"
    data = {
        "work_id": f"{work_id_generator}",
    }
    LOGGER.debug("Fetching {}".format(url))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["admin_added"] is True
    assert payload["jwt_exchange_code"] != ""
    ValueStorage.jwt = payload["jwt_exchange_code"]
    ValueStorage.work_id = work_id_generator


@pytest.mark.asyncio
async def test_duplicate_firstuser_admin(
    session_with_tpjwt: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
) -> None:
    """Tests failure if firstuser admin already exists"""
    client = session_with_tpjwt
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/add-admin"
    data = {
        "work_id": f"{ValueStorage.work_id}",
    }
    LOGGER.debug("Fetching {}".format(url))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status == 500


@pytest.mark.asyncio
async def test_firstuser_is_active(
    session_with_tpjwt: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
) -> None:
    """Tests firstuser is active"""
    client = session_with_tpjwt
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/is-active"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["api_is_active"] is True


@pytest.mark.asyncio
async def test_disable_firstuser(
    session_with_tpjwt: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
) -> None:
    """Tests that we can disable firstuser"""
    client = session_with_tpjwt
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
    session_with_tpjwt: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
) -> None:
    """Tests firstuser is not active"""
    client = session_with_tpjwt
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/is-active"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["api_is_active"] is False


@pytest.mark.asyncio
async def test_delete_disabled_firstuser(
    session_with_tpjwt: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
    error_messages: Dict[str, str],
) -> None:
    """Tests that we cannot delete disabled firstuser"""
    client = session_with_tpjwt
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/delete-admin"
    data = {
        "temp_admin_code": f"{testdata['user_hash']}",
        "work_id": f"{ValueStorage.work_id}",
    }
    LOGGER.debug("Fetching {}".format(url))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status == 410
    assert payload["detail"] == error_messages["FIRSTUSER_API_IS_DISABLED"]


@pytest.mark.asyncio
async def test_disabled_admin_list(
    session_with_tpjwt: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
    error_messages: Dict[str, str],
) -> None:
    """Tests that we cannot list disabled admin"""
    client = session_with_tpjwt
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/list-admin?temp_admin_code={testdata['user_hash']}"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status == 410
    assert payload["detail"] == error_messages["FIRSTUSER_API_IS_DISABLED"]


@pytest.mark.asyncio
async def test_disabled_add_admin(
    session_with_tpjwt: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    error_messages: Dict[str, str],
) -> None:
    """Tests that we cannot add firstuser if admin is disabled"""
    client = session_with_tpjwt
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/add-admin"
    data = {
        "work_id": f"{ValueStorage.work_id_should_not_exist}",
    }
    LOGGER.debug("Fetching {}".format(url))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status == 410
    assert payload["detail"] == error_messages["FIRSTUSER_API_IS_DISABLED"]


@pytest.mark.asyncio
async def test_enable_firstuser(
    session_with_tpjwt: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
) -> None:
    """Tests that we can enable disabled firstuser"""
    client = session_with_tpjwt
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/enable"
    data = {"permit_str": f"{testdata['permit_str']}"}
    LOGGER.debug("Fetching {}".format(url))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["api_enabled"] is True


@pytest.mark.asyncio
async def test_firstuser_is_again_active(
    session_with_tpjwt: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
) -> None:
    """Tests firstuser is active"""
    client = session_with_tpjwt
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/is-active"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["api_is_active"] is True


@pytest.mark.asyncio
async def test_check_valid_code(
    session_with_tpjwt: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
) -> None:
    """Tests that we can check valid temp_admin_code"""
    client = session_with_tpjwt
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/check-code?temp_admin_code={ValueStorage.jwt}"
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
async def test_admin_list(
    session_with_tpjwt: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
) -> None:
    """Tests that we can have a list with id's and hashes"""
    client = session_with_tpjwt
    # chas no permission to add new admins.
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/list-admin?temp_admin_code={testdata['user_hash']}"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    work_id_list = []
    for item in payload["admin_list"]:
        assert item["work_id"] != ""
        assert item["work_id_hash"] != ""
        work_id_list.append(item["work_id"])
    assert f"{ValueStorage.work_id}" in work_id_list
    assert f"{ValueStorage.work_id_should_not_exist}" not in work_id_list


@pytest.mark.asyncio
async def test_delete_firstuser_temp_admin_code_missing(
    session_with_tpjwt: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    error_messages: Dict[str, str],
) -> None:
    """Tests that we delete enabled firstuser"""
    client = session_with_tpjwt
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/delete-admin"
    data = {
        "work_id": f"{ValueStorage.work_id}",
    }
    LOGGER.debug("Fetching {}".format(url))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert (
        " ".join(payload["detail"][0]["loc"]) == error_messages["BODY_TEMP_ADMIN_CODE"]
    )
    assert payload["detail"][0]["msg"] == error_messages["FIELD_REQUIRED"]
    assert payload["detail"][0]["type"] == error_messages["VALUE_MISSING"]


@pytest.mark.asyncio
async def test_delete_firstuser(
    session_with_tpjwt: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
) -> None:
    """Tests that we delete enabled firstuser"""
    client = session_with_tpjwt
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/delete-admin"
    data = {
        "temp_admin_code": f"{testdata['user_hash']}",
        "work_id": f"{ValueStorage.work_id}",
    }
    LOGGER.debug("Fetching {}".format(url))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["admin_removed"] is True


@pytest.mark.asyncio
async def test_multiple_firstuser_add_admin(
    session_with_tpjwt: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
) -> None:
    """Tests that we can add multiple firstuser admins"""
    client = session_with_tpjwt
    i = 1
    max_ids = ValueStorage.max_work_ids_to_create
    while i <= max_ids:
        url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/add-admin"
        data = {
            "work_id": f"{ValueStorage.work_id}-{i}",
        }
        LOGGER.debug("Fetching {}".format(url))
        response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        payload = await response.json()
        LOGGER.debug("payload={}".format(payload))
        i += 1


@pytest.mark.asyncio
async def test_delete_all_firstuser_admins(
    session_with_tpjwt: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
) -> None:
    """Tests that we can delete all of the firstuser admins and then get an empty admin list"""
    client = session_with_tpjwt
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/list-admin?temp_admin_code={testdata['user_hash']}"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    for item in payload["admin_list"]:
        url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/delete-admin"
        data = {
            "temp_admin_code": f"{testdata['user_hash']}",
            "work_id": f"{item['work_id']}",
        }
        LOGGER.debug("Fetching {}".format(url))
        response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        payload = await response.json()
        LOGGER.debug("payload={}".format(payload))
        assert payload["admin_removed"] is True


@pytest.mark.asyncio
async def test_empty_admin_list(
    session_with_tpjwt: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
    error_messages: Dict[str, str],
) -> None:
    """Tests that we can have an empty admin list"""
    client = session_with_tpjwt
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/firstuser/list-admin?temp_admin_code={testdata['user_hash']}"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status == 404
    assert payload["detail"] == error_messages["NO_USERS_FOUND"]
