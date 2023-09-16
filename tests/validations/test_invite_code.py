"""Tests enrollment invitecode validations"""
from typing import Tuple, Dict
import logging

import aiohttp
import pytest

from ..conftest import DEFAULT_TIMEOUT

LOGGER = logging.getLogger(__name__)


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
