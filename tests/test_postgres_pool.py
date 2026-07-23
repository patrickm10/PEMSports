"""Postgres pool configuration tests (no live database required)."""

from backend.data import postgres as postgres_module


def test_pool_open_timeout_allows_neon_cold_start():
    """Pool open timeout must exceed Neon's typical wake-from-suspend latency."""
    assert postgres_module.POOL_OPEN_TIMEOUT >= 30.0
