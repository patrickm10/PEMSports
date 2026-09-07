"""Unit tests for ranking_service cache key correctness."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from backend.core.cache import cache
from backend.services.ranking_service import get_player_impact


@pytest.fixture(autouse=True)
def clear_cache():
    cache._store.clear()
    yield
    cache._store.clear()


class TestPlayerImpactCache:
    def test_cache_key_includes_position(self):
        qb_rows = [{"metric_label": "KC", "avg_fpts": 20.0, "avg_fpts_ppr": 22.0, "games_played": 3}]
        wr_rows = [{"metric_label": "KC", "avg_fpts": 10.0, "avg_fpts_ppr": 12.0, "games_played": 2}]
        player_id = "test-player-uuid"

        with patch(
            "backend.services.ranking_service.query_player_impact_metrics",
            side_effect=[qb_rows, wr_rows],
        ) as mock_query:
            first = get_player_impact("qb", player_id, "opponent")
            second = get_player_impact("wr", player_id, "opponent")

        assert first == qb_rows
        assert second == wr_rows
        assert first != second
        assert mock_query.call_count == 2
        mock_query.assert_any_call("qb", player_id, "opponent")
        mock_query.assert_any_call("wr", player_id, "opponent")
