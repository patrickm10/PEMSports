"""Bake players.csv load must succeed with mixed numeric ESPN ids and empties."""
from __future__ import annotations

import csv
from pathlib import Path

import duckdb


def _load_players_sql(csv_path: Path) -> str:
    """Mirror scripts/bake_db.py players CREATE TABLE SQL."""
    players_csv_path = str(csv_path).replace("\\", "/")
    return f"""
    CREATE TABLE players AS
    SELECT
      CAST(player_id AS VARCHAR) AS player_id,
      CAST(legacy_player_id AS VARCHAR) AS legacy_player_id,
      CAST(player_name AS VARCHAR) AS player_name,
      CAST(team AS VARCHAR) AS team,
      CAST(position AS VARCHAR) AS position,
      CAST(NULLIF(CAST(espn_player_id AS VARCHAR), '') AS VARCHAR) AS espn_player_id
    FROM read_csv_auto(
      '{players_csv_path}',
      HEADER=TRUE,
      ALL_VARCHAR=TRUE
    )
    """


def test_players_csv_loads_with_numeric_espn_ids_and_empty_strings(tmp_path: Path):
    csv_path = tmp_path / "players.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "player_id",
                "legacy_player_id",
                "player_name",
                "team",
                "position",
                "espn_player_id",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "player_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
                "legacy_player_id": "legacy-1",
                "player_name": "Test One",
                "team": "KC",
                "position": "QB",
                "espn_player_id": "3918298",
            }
        )
        writer.writerow(
            {
                "player_id": "ffffffff-1111-2222-3333-444444444444",
                "legacy_player_id": "legacy-2",
                "player_name": "Test Two",
                "team": "BUF",
                "position": "WR",
                "espn_player_id": "",
            }
        )
        writer.writerow(
            {
                "player_id": "99999999-aaaa-bbbb-cccc-dddddddddddd",
                "legacy_player_id": "legacy-3",
                "player_name": "Test Three",
                "team": "SF",
                "position": "RB",
                "espn_player_id": "3043078",
            }
        )

    conn = duckdb.connect(":memory:")
    conn.execute(_load_players_sql(csv_path))
    count = conn.execute("SELECT COUNT(*) FROM players").fetchone()[0]
    assert count == 3

    espn_rows = conn.execute(
        """
        SELECT player_name, espn_player_id
        FROM players
        ORDER BY player_name
        """
    ).fetchall()
    assert espn_rows[0] == ("Test One", "3918298")
    assert espn_rows[1] == ("Test Three", "3043078")
    assert espn_rows[2] == ("Test Two", None)
