"""Unit tests for insights_service cache key correctness."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from backend.core.cache import cache
from backend.services.insights_service import get_insights_leaderboard


@pytest.fixture(autouse=True)
def clear_cache():
    cache._store.clear()
    yield
    cache._store.clear()


class TestInsightsCacheGeneration:
    def test_cache_key_includes_stats_generation(self):
        first_payload = {"position": "rb", "insights": [{"player_id": "a"}]}
        second_payload = {"position": "rb", "insights": [{"player_id": "b"}]}

        with patch(
            "backend.services.insights_service.stats_generation",
            side_effect=[1, 2],
        ):
            with patch(
                "backend.services.insights_service.query_insights_leaderboard",
                side_effect=[first_payload, second_payload],
            ) as mock_query:
                first = get_insights_leaderboard(
                    position="rb",
                    context="surface",
                    context_value="Grass",
                )
                second = get_insights_leaderboard(
                    position="rb",
                    context="surface",
                    context_value="Grass",
                )

        assert first == first_payload
        assert second == second_payload
        assert mock_query.call_count == 2
