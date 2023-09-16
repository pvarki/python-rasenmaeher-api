"""Tests enrollment invitecode validations"""
from typing import Tuple, Dict
import logging

import aiohttp
import pytest

from ..conftest import DEFAULT_TIMEOUT

LOGGER = logging.getLogger(__name__)

# pylint: disable=too-few-public-methods
class ValueStorage:
    """Storage for invite_code generated in this testsuite"""

    invite_code = None


# FIXME: openapi.json 2023-09-10: invalid doc: '.../invitecode?code=xxx...': '?code' -> '?invitecode'
@pytest.mark.asyncio
async def test_not_used_invite_code(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
) -> None:
    """Tests that we can check invite_code is usable"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/enrollment/invitecode?invitecode={testdata['invite_code']}"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["invitecode_is_active"] is False


@pytest.mark.asyncio
async def test_invalid_invite_code_enroll(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
    error_messages: Dict[str, str],
) -> None:
    """Tests that we cannot enroll non-existent work_id and invite_code"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/enrollment/invitecode/enroll"
    data = {
        "invitecode": f"{testdata['invite_code']}",
        "work_id": f"{testdata['invite_code_work_id1']}",
    }
    LOGGER.debug("Fetching {}".format(url))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status == 400
    assert payload["detail"] == error_messages["INVITECODE_NOT_VALID"]


@pytest.mark.asyncio
async def test_invalid_user_hash_invite_code_create(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
    error_messages: Dict[str, str],
) -> None:
    """Tests that we cannot create a new invite code using invalid user management hash"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/enrollment/invitecode/create"
    data = {
        "user_management_hash": f"{testdata['invite_code_invalid_user_hash']}",
    }
    LOGGER.debug("Fetching {}".format(url))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert response.status == 403
    assert payload["detail"] == error_messages["NO_ENROLLMENT_PERMISSIONS"]


@pytest.mark.asyncio
async def test_valid_user_hash_invite_code_create(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
    testdata: Dict[str, str],
) -> None:
    """Tests that we can create a new invite code using valid user management hash"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/enrollment/invitecode/create"
    data = {
        "user_management_hash": f"{testdata['testing_management_hash']}",
    }
    LOGGER.debug("Fetching {}".format(url))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["invite_code"] != ""
    ValueStorage.invite_code = payload["invite_code"]


@pytest.mark.asyncio
@pytest.mark.xfail
async def test_validity_of_invalid_special_char_invite_code(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
) -> None:
    """Tests that we can verify invalid invite code containing special characters"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/enrollment/invitecode?invitecode=älåpåp234a'ät4grfdpgo"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["invitecode_is_active"] is False


@pytest.mark.asyncio
async def test_validity_of_invalid_invite_code(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
) -> None:
    """Tests that we can verify invalid invite code"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/enrollment/invitecode?invitecode=aerersd3434"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["invitecode_is_active"] is False


@pytest.mark.asyncio
async def test_validity_of_valid_invite_code(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
) -> None:
    """Tests that we can verify valid invite code"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/enrollment/invitecode?invitecode={ValueStorage.invite_code}"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["invitecode_is_active"] is True


@pytest.mark.asyncio
@pytest.mark.xfail
async def test_deactivate_valid_invite_code(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
) -> None:
    """Tests that we can deactivate valid invite code"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/enrollment/invitecode/deactivate"
    data = {
        "invite_code": f"{ValueStorage.invite_code}",
    }
    LOGGER.debug("Fetching {}".format(url))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["invite_code"] == f"{ValueStorage.invite_code}"


@pytest.mark.asyncio
@pytest.mark.xfail
async def test_valid_invite_code_is_not_active(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
) -> None:
    """Tests that we can verify valid invite code"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/enrollment/invitecode?invitecode={ValueStorage.invite_code}"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["invitecode_is_active"] is False


@pytest.mark.asyncio
@pytest.mark.xfail
async def test_activate_valid_invite_code(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
) -> None:
    """Tests that we can activate valid invite code"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/enrollment/invitecode/activate"
    data = {
        "invite_code": f"{ValueStorage.invite_code}",
    }
    LOGGER.debug("Fetching {}".format(url))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["invite_code"] == f"{ValueStorage.invite_code}"


@pytest.mark.asyncio
@pytest.mark.xfail
async def test_valid_invite_code_is_active(
    session_with_testcas: aiohttp.ClientSession,
    localmaeher_api: Tuple[str, str],
) -> None:
    """Tests that we can verify valid invite code"""
    client = session_with_testcas
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/enrollment/invitecode?invitecode={ValueStorage.invite_code}"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["invitecode_is_active"] is True
