"""Tests in sequence to simulate an end-to-end scenario"""
import logging

import aiohttp
import pytest

from ..conftest import DEFAULT_TIMEOUT, API, VER

LOGGER = logging.getLogger(__name__)

# pylint: disable=too-few-public-methods
class ValueStorage:
    """Storage for values generated and used in this testsuite"""

    first_user_admin_call_sign = ""
    first_user_admin_jwt_exchange_code = ""
    invite_code = ""
    call_sign = ""
    call_sign_jwt = ""
    approve_code = ""


@pytest.mark.asyncio
async def test_1_firstuser_add_admin(
    session_with_tpjwt: aiohttp.ClientSession,
    call_sign_generator: str,
) -> None:
    """Tests that we can create new work_id"""
    client = session_with_tpjwt
    url = f"{API}/{VER}/firstuser/add-admin"
    data = {
        "callsign": f"{call_sign_generator}",
    }
    LOGGER.debug("Fetching {}".format(url))
    LOGGER.debug("Data: {}".format(data))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["admin_added"] is True
    assert payload["jwt_exchange_code"] != ""
    ValueStorage.first_user_admin_jwt_exchange_code = payload["jwt_exchange_code"]
    ValueStorage.first_user_admin_call_sign = call_sign_generator


@pytest.mark.asyncio
async def test_2_invite_code_create(
    session_with_tpjwt: aiohttp.ClientSession,
) -> None:
    """Tests that we can create a new invite code"""
    client = session_with_tpjwt
    url = f"{API}/{VER}/enrollment/invitecode/create"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.post(url, json=None, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["invite_code"] != ""
    ValueStorage.invite_code = payload["invite_code"]


@pytest.mark.asyncio
async def test_3_invite_code_is_ok(
    session_with_testcas: aiohttp.ClientSession,
) -> None:
    """Tests that we can verify that the given invite code is ok"""
    client = session_with_testcas
    url = f"{API}/{VER}/enrollment/invitecode?invitecode={ValueStorage.invite_code}"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["invitecode_is_active"] is True


@pytest.mark.asyncio
async def test_4_invite_code_enroll(
    session_with_testcas: aiohttp.ClientSession,
    call_sign_generator: str,
) -> None:
    """
    Tests that we can enroll using valid invite_code
    """
    client = session_with_testcas
    url = f"{API}/{VER}/enrollment/invitecode/enroll"
    data = {
        "invite_code": f"{ValueStorage.invite_code}",
        "callsign": f"{call_sign_generator}",
    }
    LOGGER.debug("Fetching {}".format(url))
    LOGGER.debug("Data: {}".format(data))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    ValueStorage.call_sign = payload["callsign"]
    ValueStorage.call_sign_jwt = payload["jwt"]
    ValueStorage.approve_code = payload["approvecode"]


@pytest.mark.asyncio
async def test_5_enrollment_list_for_available_call_sign(
    session_with_tpjwt: aiohttp.ClientSession,
) -> None:
    """Tests that we have call_sign available for enrollment"""
    client = session_with_tpjwt
    url = f"{API}/{VER}/enrollment/list"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    found_enroll_call_sign = False
    for item in payload["callsign_list"]:
        assert item["callsign"] != "" or item["callsign"] == ""
        assert item["approvecode"] != ""
        assert item["state"] == 0 or item["state"] == 1
        if item["callsign"] == ValueStorage.call_sign and item["state"] == 0:
            ValueStorage.approve_code = item["approvecode"]
            found_enroll_call_sign = True
    assert found_enroll_call_sign is True


@pytest.mark.asyncio
async def test_6_call_sign_not_accepted(
    session_with_testcas: aiohttp.ClientSession,
) -> None:
    """Tests that call_sign has not yet accepted"""
    client = session_with_testcas
    client.headers.update({"Authorization": f"Bearer {ValueStorage.call_sign_jwt}"})
    url = f"{API}/{VER}/enrollment/have-i-been-accepted"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["have_i_been_accepted"] is False


@pytest.mark.asyncio
async def test_7_enrollment_accept_call_sign(
    session_with_tpjwt: aiohttp.ClientSession,
) -> None:
    """
    Tests that we can accept call_sign
    """
    client = session_with_tpjwt
    url = f"{API}/{VER}/enrollment/accept"
    data = {
        "callsign": f"{ValueStorage.call_sign}",
        "approvecode": f"{ValueStorage.approve_code}",
    }
    LOGGER.debug("Fetching {}".format(url))
    LOGGER.debug("Data: {}".format(data))
    response = await client.post(url, json=data, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))


@pytest.mark.asyncio
async def test_8_call_sign_accepted(
    session_with_testcas: aiohttp.ClientSession,
) -> None:
    """Tests that call_sign has been accepted"""
    client = session_with_testcas
    client.headers.update({"Authorization": f"Bearer {ValueStorage.call_sign_jwt}"})
    url = f"{API}/{VER}/enrollment/have-i-been-accepted"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = await response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["have_i_been_accepted"] is True


@pytest.mark.asyncio
async def test_9_check_if_enduser_pfx_available(
    session_with_testcas: aiohttp.ClientSession,
) -> None:
    """Tests that we can check if the pfx bundle is available for the given callsign"""
    client = session_with_testcas
    client.headers.update({"Authorization": f"Bearer {ValueStorage.call_sign_jwt}"})
    url = f"{API}/{VER}/enduserpfx/{ValueStorage.call_sign}"
    LOGGER.debug("Fetching {}".format(url))
    response = await client.get(url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    assert response.content
