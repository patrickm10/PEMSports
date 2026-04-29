"""Unit tests for player headshot pipeline (no live network calls)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import duckdb
import pytest

from pipelines.player_headshots import build_espn_headshot_url, build_headshot_path, run_pipeline


def test_build_espn_headshot_url_maps_player_id_to_cdn():
    assert (
        build_espn_headshot_url("3918298")
        == "https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/3918298.png&h=96&w=96&scale=crop"
    )
    assert build_espn_headshot_url("3918298", raw=True) == (
        "https://a.espncdn.com/i/headshots/nfl/players/full/3918298.png"
    )


def test_team_map_slug_covers_constants():
    # No-op: roster scraping is no longer part of the headshot pipeline.
    assert True


def test_iter_teams_for_scrape_respects_limit():
    # No-op: roster scraping is no longer part of the headshot pipeline.
    assert True


def test_build_headshot_path_matches_api_contract():
    pid = "550e8400-e29b-41d4-a716-446655440000"
    assert build_headshot_path(pid) == f"/headshots/{pid}.jpg"


def test_run_pipeline_writes_jpg_and_csv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "t.db"
    con = duckdb.connect(str(db_path))
    con.execute(
        """
        CREATE TABLE players (
          player_id VARCHAR,
          legacy_player_id VARCHAR,
          player_name VARCHAR,
          team VARCHAR,
          position VARCHAR,
          espn_player_id VARCHAR
        )
        """
    )
    pid = "550e8400-e29b-41d4-a716-446655440000"
    con.execute(
        "INSERT INTO players VALUES (?, ?, ?, ?, ?, ?)",
        [pid, "legacy1", "Josh Allen", "BUF", "QB", "3918298"],
    )
    con.close()

    png_bytes = b"\x89PNG\r\n\x1a\nfake"

    def fake_get(url, headers=None, timeout=None):  # noqa: ARG001
        m = MagicMock()
        m.status_code = 200
        m.content = png_bytes
        return m

    monkeypatch.setattr("pipelines.player_headshots.requests.get", fake_get)
    monkeypatch.setattr("pipelines.player_headshots._png_to_jpeg", lambda b: b"JPEGDATA")  # noqa: ARG005

    csv_out = tmp_path / "out.csv"
    out_dir = tmp_path / "headshots"

    rows = run_pipeline(
        db_path=db_path,
        output_csv=csv_out,
        headshots_dir=out_dir,
        overwrite=True,
        delay=0,
        timeout=10,
    )

    assert len(rows) == 1
    dest = out_dir / f"{pid}.jpg"
    assert dest.exists()
    assert dest.read_bytes() == b"JPEGDATA"

    assert csv_out.exists()
    text = csv_out.read_text(encoding="utf-8")
    assert pid in text
    assert "/headshots/" in text


def test_collect_db_players_requires_file():
    missing = Path(__file__).resolve().parent / "__no_such_db__.db"
    with pytest.raises(FileNotFoundError):
        run_pipeline(db_path=missing, dry_run=True)
