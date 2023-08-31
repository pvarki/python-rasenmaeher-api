"""Test product API/mTLS client things"""
import logging

import pytest
import aiohttp
from pytest_httpserver import HTTPServer

LOGGER = logging.getLogger(__name__)


@pytest.mark.skip(reason="Something is fucky-wucky with pytest-httpserver and tls")
@pytest.mark.asyncio
async def test_hello(httpserver: HTTPServer, mtlsclient: aiohttp.ClientSession) -> None:
    """Quick and dirty test of the mTLS client and server"""
    httpserver.expect_request("/").respond_with_data("hello world!")
    url = httpserver.url_for("/")
    LOGGER.debug("url={}".format(url))
    async with mtlsclient.get(url) as result:
        assert (await result.text()) == "hello world!"
        assert result.connection
        assert result.connection.transport
        cert = result.connection.transport.get_extra_info("peercert")
        assert cert
