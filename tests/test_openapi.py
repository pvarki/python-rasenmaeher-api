"""Get the openapi.json from the API container via NGinx proxy"""
import requests

def test_get_openapi_json(localmaeher_api, openapi_version):
    url = f"{localmaeher_api[0]}/openapi.json"
    response = requests.get(url, json=None, headers=None, verify=False)
    print(response.json())
    assert response.status_code == 200
    assert response.json()["openapi"] == f"{openapi_version[0]}"
    assert response.json()["info"] is not None
    assert response.json()["info"]["title"] == "FastAPI"
    assert response.json()["info"]["version"] == f"{openapi_version[1]}"
    assert response.json()["paths"] is not None
    assert response.json()["paths"][f"/api/{localmaeher_api[1]}/healthcheck"] is not None
    assert response.json()["components"] is not None
    assert response.json()["components"]["schemas"] is not None
    assert response.json()["components"]["schemas"]["CertificatesRequest"] is not None
    assert response.json()["components"]["securitySchemes"] is not None
    assert response.json()["components"]["securitySchemes"]["JWTBearer"] is not None
