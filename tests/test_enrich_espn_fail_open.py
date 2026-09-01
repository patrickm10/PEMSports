"""Fail-open contract for ESPN id enrichment (never blocks bake/deploy)."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

import requests


def _load_enrich_module():
    path = Path(__file__).resolve().parent.parent / "scripts" / "enrich_espn_player_ids.py"
    spec = importlib.util.spec_from_file_location("enrich_espn_player_ids", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_main_fail_open_on_request_exception(tmp_path: Path):
    mod = _load_enrich_module()
    csv_path = tmp_path / "players.csv"
    csv_path.write_text(
        "player_id,legacy_player_id,player_name,team,position,espn_player_id\n"
        "a,legacy,Test Player,KC,QB,\n",
        encoding="utf-8",
    )

    with patch.object(
        mod,
        "enrich_players_csv",
        side_effect=requests.RequestException("simulated nflverse down"),
    ):
        with patch("sys.argv", ["enrich_espn_player_ids.py", "--players-csv", str(csv_path)]):
            assert mod.main() == 0


def test_main_fail_open_on_runtime_error(tmp_path: Path):
    mod = _load_enrich_module()
    csv_path = tmp_path / "players.csv"
    csv_path.write_text(
        "player_id,legacy_player_id,player_name,team,position,espn_player_id\n"
        "a,legacy,Test Player,KC,QB,\n",
        encoding="utf-8",
    )

    with patch.object(
        mod,
        "enrich_players_csv",
        side_effect=RuntimeError("simulated nflverse payload error"),
    ):
        with patch("sys.argv", ["enrich_espn_player_ids.py", "--players-csv", str(csv_path)]):
            assert mod.main() == 0
