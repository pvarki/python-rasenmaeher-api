"""Test product API/mTLS client things"""
import logging

import pytest
import aiohttp


from rasenmaeher_api.settings import settings

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
