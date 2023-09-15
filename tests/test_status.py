"""Test API get status and set-state (set status)"""
from typing import Tuple, Dict
import logging

import pytest
import requests

LOGGER = logging.getLogger(__name__)


@pytest.mark.skip(reason="Fails due to not checking correct things")
def test_get_init_status(
    localmaeher_api: Tuple[str, str, float], testdata: Dict[str, str]
) -> None:
    """Initialize enrollment"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/enrollment/status/{testdata['work_id1']}"
    response = requests.get(
        url, json=None, headers=None, verify=False, timeout=localmaeher_api[2]
    )
    assert response.status_code == 200
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["status"] == "init"


@pytest.mark.skip(reason="Fails due to not checking correct things")
def test_set_new_state(
    localmaeher_api: Tuple[str, str, float], testdata: Dict[str, str]
) -> None:
    """Start new enrollment"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/enrollment/config/set-state"
    data = {
        "state": "new",
        "work_id": f"{testdata['work_id1']}",
        "work_id_hash": "work_id_hash",
        "permit_str": f"{testdata['permit_str']}",
    }
    response = requests.post(
        url, json=data, headers=None, verify=False, timeout=localmaeher_api[2]
    )
    assert response.status_code == 200
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["success"] is True


@pytest.mark.skip(reason="Fails due to not checking correct things")
def test_get_new_status(
    localmaeher_api: Tuple[str, str, float], testdata: Dict[str, str]
) -> None:
    """Check status of new enrollment"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/enrollment/status/{testdata['work_id1']}"
    response = requests.get(
        url, json=None, headers=None, verify=False, timeout=localmaeher_api[2]
    )
    assert response.status_code == 200
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["status"] == "new"


@pytest.mark.skip(reason="Fails due to not checking correct things")
def test_set_init_state(
    localmaeher_api: Tuple[str, str, float], testdata: Dict[str, str]
) -> None:
    """FIXME: Check enrollment state??"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/enrollment/config/set-state"
    data = {
        "state": "init",
        "work_id": f"{testdata['work_id1']}",
        "work_id_hash": "work_id_hash",
        "permit_str": f"{testdata['permit_str']}",
    }
    response = requests.post(
        url, json=data, headers=None, verify=False, timeout=localmaeher_api[2]
    )
    assert response.status_code == 200
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["success"] is True
