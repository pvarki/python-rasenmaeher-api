"""A unique-key race must have the same result as a previously used nonce."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import IntegrityError

from rasenmaeher_api.db.engine import EngineWrapper
from rasenmaeher_api.db.errors import NotFound, TokenReuse
from rasenmaeher_api.db.nonces import SeenToken


@pytest.mark.asyncio
@pytest.mark.parametrize("concurrent_insert", [True, False])
async def test_nonce_insert_race(monkeypatch: pytest.MonkeyPatch, concurrent_insert: bool) -> None:
    error = IntegrityError("insert", {}, Exception("constraint failed"))
    session = MagicMock()
    session.__enter__.return_value.commit.side_effect = error
    monkeypatch.setattr(EngineWrapper, "get_session", lambda: session)
    lookup = AsyncMock(side_effect=[NotFound(), SeenToken(token="nonce") if concurrent_insert else NotFound()])
    monkeypatch.setattr(SeenToken, "by_token", lookup)
    with pytest.raises(TokenReuse if concurrent_insert else IntegrityError):
        await SeenToken.use_token("nonce")
    assert lookup.await_count == 2
    session.__exit__.assert_called_once()
