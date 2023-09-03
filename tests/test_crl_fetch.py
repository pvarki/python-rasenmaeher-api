"""Test the CRL fetching via Nginx and API container"""
import requests

def test_localmaeher_fetch_crl(localmaeher_api):
    url = f"{localmaeher_api[0]}/{localmaeher_api[1]}/utils/crl"
    response = requests.get(url, json=None, headers=None, verify=False)
    assert response.status_code == 200

def test_localhost_fetch_crl(localhost_api):
    url = f"{localhost_api[0]}/{localhost_api[1]}/utils/crl"
    response = requests.get(url, json=None, headers=None, verify=False)
    assert response.status_code == 200
