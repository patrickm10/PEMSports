"""Postgres pool configuration tests (no live database required)."""

import asyncio
import inspect
from types import SimpleNamespace

import pytest

from backend.data import postgres as postgres_module


def test_pool_open_timeout_allows_neon_cold_start():
    """Pool open timeout must exceed Neon's typical wake-from-suspend latency."""
    assert postgres_module.POOL_OPEN_TIMEOUT >= 30.0


class _FakeConn:
    def __init__(self) -> None:
        self.executed: list[str] = []
        self.commits = 0

    async def execute(self, sql: str) -> None:
        self.executed.append(sql)

    async def commit(self) -> None:
        self.commits += 1


def test_configure_connection_commits_search_path():
    """psycopg_pool discards connections left INTRANS after configure."""
    src = inspect.getsource(postgres_module._configure_connection)
    assert "SET search_path TO app, stats, public" in src
    assert "await conn.commit()" in src
    assert "SET LOCAL" not in src

    conn = _FakeConn()
    asyncio.run(postgres_module._configure_connection(conn))
    assert conn.executed == ["SET search_path TO app, stats, public"]
    assert conn.commits == 1


class _FailingCheckout:
    async def __aenter__(self):
        raise TimeoutError("couldn't get a connection after 30.00 sec")

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


def test_init_db_production_raises_database_unavailable(monkeypatch):
    """Production must not swallow pool failures or boot without Postgres."""
    monkeypatch.setattr(
        postgres_module,
        "config",
        SimpleNamespace(is_development=False, app_env="production"),
    )
    monkeypatch.setattr(
        postgres_module, "get_db_connection", lambda: _FailingCheckout()
    )
    postgres_module._db_connected = True

    with pytest.raises(postgres_module.DatabaseUnavailable) as excinfo:
        asyncio.run(postgres_module.init_db())

    assert postgres_module.is_db_connected() is False
    assert "production" in str(excinfo.value)
    assert "couldn't get a connection after 30.00 sec" in str(excinfo.value)
