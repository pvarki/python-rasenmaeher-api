"""Test API get status and set-state (set status)"""
import logging

import requests

LOGGER = logging.getLogger(__name__)


def test_get_init_status(localmaeher_api, testdata):
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/enrollment/status/{testdata['work_id1']}"
    response = requests.get(url, json=None, headers=None, verify=False)
    assert response.status_code == 200
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["status"] == "init"


def test_set_new_state(localmaeher_api, testdata):
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/enrollment/config/set-state"
    data = {
        "state": "new",
        "work_id": f"{testdata['work_id1']}",
        "work_id_hash": "work_id_hash",
        "permit_str": f"{testdata['permit_str']}",
    }
    response = requests.post(url, json=data, headers=None, verify=False)
    assert response.status_code == 200
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["success"] is True


def test_get_new_status(localmaeher_api, testdata):
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/enrollment/status/{testdata['work_id1']}"
    response = requests.get(url, json=None, headers=None, verify=False)
    assert response.status_code == 200
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["status"] == "new"


def test_set_init_state(localmaeher_api, testdata):
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/enrollment/config/set-state"
    data = {
        "state": "init",
        "work_id": f"{testdata['work_id1']}",
        "work_id_hash": "work_id_hash",
        "permit_str": f"{testdata['permit_str']}",
    }
    response = requests.post(url, json=data, headers=None, verify=False)
    assert response.status_code == 200
    payload = response.json()
    LOGGER.debug("payload={}".format(payload))
    assert payload["success"] is True
