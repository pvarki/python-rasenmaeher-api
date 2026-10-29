"""Test CLI scripts"""

import asyncio
import os

import pytest
from libadvian.binpackers import ensure_str

from rasenmaeher_api import __version__

# Each case boots the whole app in a subprocess, which on a loaded shared runner is nowhere near
# the ~2s it takes on a developer machine. Generous on purpose: the bound is here to stop a hung
# subprocess holding the suite, not to assert anything about startup time.
CLI_TIMEOUT = 60


@pytest.mark.asyncio(loop_scope="session")
async def test_version_cli() -> None:
    """Test the CLI parsing for default version dumping works"""
    cmd = "rasenmaeher_api --version"
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out = await asyncio.wait_for(process.communicate(), CLI_TIMEOUT)
    # Demand clean exit
    assert process.returncode == 0
    # Check output
    assert ensure_str(out[0]).strip().endswith(__version__)


@pytest.mark.asyncio(loop_scope="session")
async def test_addcode_cli() -> None:
    """Test we can add new admin code via CLI"""
    cmd = "rasenmaeher_api addcode"
    process = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=os.environ,
    )
    out = await asyncio.wait_for(process.communicate(), CLI_TIMEOUT)
    # Demand clean exit
    assert process.returncode == 0
    # Check output
    assert ensure_str(out[0]).strip()
