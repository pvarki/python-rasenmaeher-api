"""Prove replay protection holds across workers using the real database constraint."""

import asyncio
import threading
from uuid import uuid4

import pytest

from rasenmaeher_api.db.errors import NotFound, TokenReuse
from rasenmaeher_api.db.nonces import SeenToken


@pytest.mark.asyncio(loop_scope="session")
async def test_concurrent_nonce_insert(dbinit_sess: None, monkeypatch: pytest.MonkeyPatch) -> None:
    nonce = str(uuid4())
    lookup = SeenToken.by_token
    first_reads = threading.Barrier(2)
    worker = threading.local()

    async def racing_lookup(token: str) -> SeenToken:
        if not getattr(worker, "checked", False):
            worker.checked = True
            try:
                return await lookup(token)
            except NotFound:
                first_reads.wait(timeout=10)
                raise
        return await lookup(token)

    monkeypatch.setattr(SeenToken, "by_token", racing_lookup)

    async def consume() -> str:
        try:
            await SeenToken.use_token(nonce)
            return "accepted"
        except TokenReuse:
            return "replayed"

    results = await asyncio.gather(
        asyncio.to_thread(lambda: asyncio.run(consume())), asyncio.to_thread(lambda: asyncio.run(consume()))
    )
    assert sorted(results) == ["accepted", "replayed"]
    assert (await lookup(nonce)).token == nonce
