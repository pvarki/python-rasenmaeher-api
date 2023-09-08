"""Test the CRL fetching via Nginx and API container"""
from typing import Tuple
import logging

import requests

LOGGER = logging.getLogger(__name__)


def test_localmaeher_fetch_crl(localmaeher_api: Tuple[str, str]) -> None:
    """Test that we can get CRL via https api dns name"""
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/utils/crl"
    response = requests.get(url, json=None, headers=None, verify=False, timeout=2.0)
    assert response.status_code == 200


def test_localhost_fetch_crl(localhost_api: Tuple[str, str]) -> None:
    """Test that we can get CRL via the direct localhost access to rasenmaeher"""
    url = f"{localhost_api[0]}/{localhost_api[1]}/utils/crl"
    response = requests.get(url, json=None, headers=None, verify=False, timeout=2.0)
    assert response.status_code == 200
