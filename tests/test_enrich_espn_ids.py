"""ESPN id enrichment from nflverse (no live network)."""
from __future__ import annotations

import csv
from pathlib import Path

from tests.test_enrich_espn_fail_open import _load_enrich_module


def _write_players(path: Path, rows: list[dict[str, str]]) -> None:
    fieldnames = [
        "player_id",
        "legacy_player_id",
        "player_name",
        "team",
        "position",
        "espn_player_id",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fieldnames})


def test_null_espn_id_is_not_a_match(tmp_path: Path):
    """Sleeper-shaped records with espn_id=null must not fill espn_player_id."""
    mod = _load_enrich_module()
    csv_path = tmp_path / "players.csv"
    _write_players(
        csv_path,
        [
            {
                "player_id": "chase-uuid",
                "legacy_player_id": "legacy-chase",
                "player_name": "Ja'Marr Chase",
                "team": "CIN",
                "position": "WR",
                "espn_player_id": "",
            }
        ],
    )
    report = mod.enrich_players_csv(
        players_csv=csv_path,
        nflverse_players=[
            {
                "full_name": "Ja'Marr Chase",
                "position": "WR",
                "espn_id": None,
            }
        ],
    )
    assert report["matched"] == 0
    assert report["missing"] == 1
    with csv_path.open(encoding="utf-8") as f:
        out = list(csv.DictReader(f))
    assert out[0]["espn_player_id"] == ""


def test_nflverse_unique_match_fills_espn_player_id(tmp_path: Path):
    mod = _load_enrich_module()
    csv_path = tmp_path / "players.csv"
    _write_players(
        csv_path,
        [
            {
                "player_id": "chase-uuid",
                "legacy_player_id": "l1",
                "player_name": "Ja'Marr Chase",
                "team": "CIN",
                "position": "WR",
                "espn_player_id": "",
            },
            {
                "player_id": "nacua-uuid",
                "legacy_player_id": "l2",
                "player_name": "Puka Nacua",
                "team": "LAR",
                "position": "WR",
                "espn_player_id": "",
            },
            {
                "player_id": "maye-uuid",
                "legacy_player_id": "l3",
                "player_name": "Drake Maye",
                "team": "NE",
                "position": "QB",
                "espn_player_id": "",
            },
        ],
    )
    report = mod.enrich_players_csv(
        players_csv=csv_path,
        nflverse_players=[
            {"display_name": "Ja'Marr Chase", "position": "WR", "espn_id": "4360310"},
            {"display_name": "Puka Nacua", "position": "WR", "espn_id": 4432773},
            {"display_name": "Drake Maye", "position": "QB", "espn_id": "4431611.0"},
        ],
    )
    assert report["matched"] == 3
    assert report["missing"] == 0
    by_name = {
        r["player_name"]: r["espn_player_id"]
        for r in csv.DictReader(csv_path.open(encoding="utf-8"))
    }
    assert by_name["Ja'Marr Chase"] == "4360310"
    assert by_name["Puka Nacua"] == "4432773"
    assert by_name["Drake Maye"] == "4431611"


def test_ambiguous_name_position_is_skipped(tmp_path: Path):
    mod = _load_enrich_module()
    csv_path = tmp_path / "players.csv"
    _write_players(
        csv_path,
        [
            {
                "player_id": "mw-uuid",
                "legacy_player_id": "l1",
                "player_name": "Mike Williams",
                "team": "LAC",
                "position": "WR",
                "espn_player_id": "",
            }
        ],
    )
    report = mod.enrich_players_csv(
        players_csv=csv_path,
        nflverse_players=[
            {"display_name": "Mike Williams", "position": "WR", "espn_id": "3045138"},
            {"display_name": "Mike Williams", "position": "WR", "espn_id": "13489"},
        ],
    )
    assert report["matched"] == 0
    assert report["ambiguous"] == 1
    with csv_path.open(encoding="utf-8") as f:
        out = list(csv.DictReader(f))
    assert out[0]["espn_player_id"] == ""


def test_preserves_existing_espn_id_without_overwrite(tmp_path: Path):
    mod = _load_enrich_module()
    csv_path = tmp_path / "players.csv"
    _write_players(
        csv_path,
        [
            {
                "player_id": "allen-uuid",
                "legacy_player_id": "l1",
                "player_name": "Josh Allen",
                "team": "BUF",
                "position": "QB",
                "espn_player_id": "3918298",
            }
        ],
    )
    report = mod.enrich_players_csv(
        players_csv=csv_path,
        nflverse_players=[
            {"display_name": "Josh Allen", "position": "QB", "espn_id": "999999"},
        ],
    )
    assert report["preserved"] == 1
    assert report["matched"] == 0
    with csv_path.open(encoding="utf-8") as f:
        out = list(csv.DictReader(f))
    assert out[0]["espn_player_id"] == "3918298"


def test_build_indexes_skips_null_sleeper_espn_id():
    mod = _load_enrich_module()
    by_name_pos, by_name = mod._build_indexes(
        [
            {"full_name": "Ja'Marr Chase", "position": "WR", "espn_id": None},
            {"full_name": "Josh Allen", "position": "QB", "espn_id": "3918298"},
        ]
    )
    assert by_name_pos.get(("ja marr chase", "WR"), []) == []
    assert "ja marr chase" not in by_name
    assert by_name_pos[("josh allen", "QB")] == ["3918298"]
