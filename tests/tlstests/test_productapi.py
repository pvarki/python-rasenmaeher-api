"""Test product API/mTLS client things"""
import logging
import uuid

import pytest
import aiohttp
from libpvarki.schemas.generic import OperationResultResponse
from libpvarki.schemas.product import UserCRUDRequest


from rasenmaeher_api.settings import settings
from rasenmaeher_api.prodcutapihelpers import post_to_all_products, put_to_all_products
from rasenmaeher_api.web.api.instructions.schema import (
    ProductFileList,
)


LOGGER = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_hello(mtlsclient: aiohttp.ClientSession) -> None:
    """Quick and dirty test of the mTLS client and server"""
    url = settings.kraftwerk_manifest_dict["products"]["fake"]["api"]
    async with mtlsclient as client:
        LOGGER.debug("GETting {}".format(url))
        resp = await client.get(url)
        resp.raise_for_status()
        body = await resp.text()
        assert "Hello" in body


# NOTE: update is missing on purpose since it uses PUT not POST
@pytest.mark.parametrize("endpoint_suffix", ["created", "revoked", "promoted", "demoted"])
@pytest.mark.asyncio
async def test_user_crud(endpoint_suffix: str) -> None:
    """Test calling the user POST endpoints"""
    endpoint = f"api/v1/users/{endpoint_suffix}"

    responses = await post_to_all_products(
        endpoint,
        UserCRUDRequest(
            uuid=str(uuid.uuid4()),
            callsign="TEST22a",
            x509cert="FIXME: needs cert",
        ).dict(),
        OperationResultResponse,
    )

    assert responses
    assert "fake" in responses
    assert isinstance(responses["fake"], OperationResultResponse)
    assert responses["fake"].success


@pytest.mark.asyncio
async def test_user_update() -> None:
    """Test calling the user  (PUT)"""
    responses = await put_to_all_products(
        "api/v1/users/updated",
        UserCRUDRequest(
            uuid=str(uuid.uuid4()),
            callsign="TEST22b",
            x509cert="FIXME: needs cert",
        ).dict(),
        OperationResultResponse,
    )

    assert responses
    assert "fake" in responses
    assert isinstance(responses["fake"], OperationResultResponse)
    assert responses["fake"].success


@pytest.mark.asyncio
async def test_user_fragment() -> None:
    """Test calling the user-created endpoint"""
    responses = await post_to_all_products(
        "api/v1/clients/fragment",
        UserCRUDRequest(
            uuid=str(uuid.uuid4()),
            callsign="TEST22b",
            x509cert="FIXME: needs cert",
        ).dict(),
        ProductFileList,
    )
    assert responses
    assert "fake" in responses
    assert isinstance(responses["fake"], ProductFileList)


@pytest.mark.parametrize("endpoint", ["no-such-url", "api/v1/clients/fragment"])
@pytest.mark.asyncio
async def test_failure_is_none(endpoint: str) -> None:
    """Test calling the user-created endpoint"""
    responses = await post_to_all_products(
        endpoint,
        {},  # Invalid data for fragment
        ProductFileList,
    )
    assert responses
    assert "fake" in responses
    assert responses["fake"] is None
