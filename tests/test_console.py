"""Test CLI scripts"""

import asyncio

import pytest
from libadvian.binpackers import ensure_str

from rasenmaeher_api import __version__


@pytest.mark.asyncio(loop_scope="session")
async def test_version_cli():  # type: ignore
    """Test the CLI parsing for default version dumping works"""
    cmd = "rasenmaeher_api --version"
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out = await asyncio.wait_for(process.communicate(), 15)
    # Demand clean exit
    assert process.returncode == 0
    # Check output
    assert ensure_str(out[0]).strip().endswith(__version__)
