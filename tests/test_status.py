"""Test API get status and set-state (set status)"""
from typing import Dict
import logging

import pytest
import requests

from .conftest import DEFAULT_TIMEOUT, API, VER

LOGGER = logging.getLogger(__name__)


@pytest.mark.skip(reason="Fails due to not checking correct things")
def test_get_init_status(testdata: Dict[str, str]) -> None:
    """Initialize enrollment"""
    url = f"{API}/{VER}/enrollment/status/{testdata['work_id1']}"
    response = requests.get(url, json=None, headers=None, verify=False, timeout=DEFAULT_TIMEOUT)
    assert response.status_code == 200
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["status"] == "init"


@pytest.mark.skip(reason="Fails due to not checking correct things")
def test_set_new_state(testdata: Dict[str, str]) -> None:
    """Start new enrollment"""
    url = f"{API}/{VER}/enrollment/config/set-state"
    data = {
        "state": "new",
        "work_id": f"{testdata['work_id1']}",
        "work_id_hash": "work_id_hash",
        "permit_str": f"{testdata['permit_str']}",
    }
    response = requests.post(url, json=data, headers=None, verify=False, timeout=DEFAULT_TIMEOUT)
    assert response.status_code == 200
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["success"] is True


@pytest.mark.skip(reason="Fails due to not checking correct things")
def test_get_new_status(testdata: Dict[str, str]) -> None:
    """Check status of new enrollment"""
    url = f"{API}/{VER}/enrollment/status/{testdata['work_id1']}"
    response = requests.get(url, json=None, headers=None, verify=False, timeout=DEFAULT_TIMEOUT)
    assert response.status_code == 200
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["status"] == "new"


@pytest.mark.skip(reason="Fails due to not checking correct things")
def test_set_init_state(testdata: Dict[str, str]) -> None:
    """FIXME: Check enrollment state??"""
    url = f"{API}/{VER}/enrollment/config/set-state"
    data = {
        "state": "init",
        "work_id": f"{testdata['work_id1']}",
        "work_id_hash": "work_id_hash",
        "permit_str": f"{testdata['permit_str']}",
    }
    response = requests.post(url, json=data, headers=None, verify=False, timeout=DEFAULT_TIMEOUT)
    assert response.status_code == 200
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["success"] is True
