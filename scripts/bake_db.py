"""
Bake Script: Compiles Parquet Data Lake into a Persistent DuckDB Serving Layer.
Solves PlainSkip errors and optimizes for cloud hosting.

Column Strategy: Dynamic discovery with blacklist pruning.
Instead of a static whitelist (which silently drops performance metrics like
YDS, TD, CMP, ATT, etc.), we read ALL columns from the source Parquet and
exclude only known artifacts (_right join suffixes, raw scrape duplicates).
"""
import duckdb
from pathlib import Path
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bake_db")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC = PROJECT_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
DATA_DIR = PROJECT_ROOT / "data" / "rankings"
DB_PATH = PROJECT_ROOT / "data" / "nfl_stats.db"
PLAYERS_CSV = PROJECT_ROOT / "data" / "players.csv"

POSITIONS = ["QB", "RB", "WR", "TE", "K", "DST"]

# Columns excluded from all tables.
# Rank: computed dynamically via ROW_NUMBER() in query_engine.
# Player: raw scrape artifact, duplicate of player_name.
GLOBAL_BLACKLIST = {"Rank", "Player"}

# Columns known to be strings — preserved without numeric casting.
KNOWN_STRING = {
    "player_name", "player_id", "team", "position", "season",
    "opponent", "stadium_name", "city", "state", "indoor_outdoor",
    "surface_type", "game_result", "weather_impact", "home_away",
}

# Position-Specific Mapping Matrix: Unified names for the Serving Layer.
# Maps [Parquet Name] -> [Database Column Name]
MAPPING_MATRIX = {
    "QB": {
        "passing_yds": "yds", "passing_td": "td", "passing_att": "att",
        "passing_cmp": "cmp", "interceptions": "int", "passing_fumbles": "fumbles",
        "INT": "int", "SACKS": "sacks", "CMP": "cmp", "ATT": "att"
    },
    "RB": {
        "rushing_yds": "rush_yds", "rushing_td": "rush_td", "rushing_att": "att",
        "rushing_fumbles": "fumbles", "yds": "rush_yds", "td": "rush_td",
        # FantasyPros duplicate headers: first YDS/TD block = rushing, R_* = receiving.
        "R_YDS": "yds", "R_TD": "td", "ATT": "att"
    },
    "WR": {
        "receiving_yds": "yds", "receiving_td": "td", "receiving_rec": "rec",
        "targets": "tgt", "receiving_fumbles": "fumbles",
        "TGT %": "tgt_pct", "R_YDS": "rush_yds", "R_TD": "rush_td"
    },
    "TE": {
        "receiving_yds": "yds", "receiving_td": "td", "receiving_rec": "rec",
        "targets": "tgt", "receiving_fumbles": "fumbles",
        "TGT %": "tgt_pct", "R_YDS": "rush_yds", "R_TD": "rush_td"
    },
    "K": {
        "fg_made": "fgm", "fg_att": "fga", "xpt_made": "xpm",
        "XPT": "xpm", "XPA": "xpa", "PCT": "pct", "LG": "lg"
    },
    "DST": {
        "yds": "yds_allowed", "td": "td_allowed",
        "FR": "fum_rec", "FF": "fum_for", "DEF TD": "def_td",
        "SFTY": "safety", "SPC TD": "st_td"
    }
}


def _discover_and_build(conn: duckdb.DuckDBPyConnection, parquet_path: Path, pos: str) -> tuple[list[str], str]:
    """
    Discover columns from Parquet and build a SELECT expression list.

    Returns:
        (kept_columns, select_sql_fragment)
    """
    path_str = str(parquet_path).replace("\\", "/")
    raw_cols = [
        desc[0]
        for desc in conn.execute(
            f"SELECT * FROM read_parquet('{path_str}') LIMIT 0"
        ).description
    ]

    has_player_raw = "Player" in raw_cols
    pos_map = MAPPING_MATRIX.get(pos, {})

    # Prune blacklisted columns and _right join artifacts
    # NOTE: We preserve ALL other columns by default (column-agnostic)
    kept = [
        c for c in raw_cols
        if c not in GLOBAL_BLACKLIST and not c.endswith("_right")
    ]

    exprs: list[str] = []
    final_cols: list[str] = []
    seen_out_names = set()

    for c in kept:
        # 1. Determine Output Name (Mapping -> Lowercase)
        out_name = pos_map.get(c, c.lower())

        # 3. Deduplicate: Skip if we already have a column mapping to this out_name
        # (e.g. Parquet having both 'yds' and 'R_YDS')
        if out_name in seen_out_names:
            continue
        seen_out_names.add(out_name)

        final_cols.append(out_name)

        # 2. SELECT Expression with Casting
        # Qualify with `src.` so SELECTs stay unambiguous when joined with `players p`.
        if c == "player_name" and has_player_raw:
            exprs.append(f'COALESCE(src."player_name", src."Player") AS "{out_name}"')
        elif out_name in KNOWN_STRING:
            exprs.append(f'src."{c}" AS "{out_name}"')
        else:
            exprs.append(f'TRY_CAST(src."{c}" AS DOUBLE) AS "{out_name}"')

    return final_cols, ", ".join(exprs)


def _merge_home_away_schedule(
    conn: duckdb.DuckDBPyConnection,
    table: str,
    schedule,
    *,
    source: str,
) -> None:
    """Replace `table` with a copy that includes home_away from schedule rows."""
    schedule_path = str(PROJECT_ROOT / "data" / "_tmp_home_away_schedule.parquet").replace("\\", "/")
    schedule.write_parquet(schedule_path)

    conn.execute(
        f"""
        CREATE TABLE {table}_with_ha AS
        SELECT w.*, s.home_away
        FROM {table} w
        LEFT JOIN read_parquet('{schedule_path}') s
          ON CAST(w.year AS INTEGER) = s.year
         AND CAST(w.week AS INTEGER) = s.week
         AND w.team = s.team
        """
    )
    conn.execute(f"DROP TABLE {table}")
    conn.execute(f"ALTER TABLE {table}_with_ha RENAME TO {table}")
    logger.info("  -> %s: attached home_away via %s", table.replace("_weekly", "").upper(), source)


def _attach_home_away(conn: duckdb.DuckDBPyConnection, pos: str) -> None:
    """Join home_away when parquet lacks the column."""
    import polars as pl

    from pipelines.schedule_lookup import build_home_away_from_stadium, build_home_away_schedule

    table = f"{pos.lower()}_weekly"
    cols = {d[0].lower() for d in conn.execute(f"SELECT * FROM {table} LIMIT 0").description}
    if "home_away" in cols:
        return

    try:
        schedule = build_home_away_schedule()
        if not schedule.is_empty():
            _merge_home_away_schedule(conn, table, schedule, source="schedule lookup")
            return

        logger.warning(
            "  -> %s: enriched matchups missing; deriving home_away from stadium.csv",
            pos,
        )
        weekly_path = str(PROJECT_ROOT / "data" / "rankings" / f"{pos}_weekly.parquet").replace("\\", "/")
        weekly = pl.read_parquet(weekly_path)
        schedule = build_home_away_from_stadium(weekly)
        if schedule.is_empty():
            logger.warning("  -> %s: stadium fallback produced no home_away rows", pos)
            return

        _merge_home_away_schedule(conn, table, schedule, source="stadium fallback")
    except Exception as exc:  # noqa: BLE001
        logger.warning("  -> %s: failed to attach home_away: %s", pos, exc)


def bake():
    if DB_PATH.exists():
        logger.info(f"Removing existing database at {DB_PATH}")
        DB_PATH.unlink()

    conn = duckdb.connect(str(DB_PATH))

    # Optional canonical Players dimension:
    # If present, this table upgrades legacy parquet `player_id` values to internal UUIDs.
    # Downstream (API + headshots) should treat the UUID as the canonical key.
    players_table_loaded = False
    if PLAYERS_CSV.exists():
        try:
            players_csv_path = str(PLAYERS_CSV).replace("\\", "/")
            # ALL_VARCHAR avoids DuckDB inferring espn_player_id as numeric when
            # the column mixes ESPN ids with empty strings — that inference made
            # NULLIF(..., '') fail and skipped the players table entirely.
            conn.execute(
                f"""
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
            )
            conn.execute("CREATE UNIQUE INDEX idx_players_player_id ON players(player_id)")
            conn.execute("CREATE UNIQUE INDEX idx_players_legacy_player_id ON players(legacy_player_id)")
            players_table_loaded = True
            logger.info("Loaded players dimension from %s", PLAYERS_CSV)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load players dimension from %s: %s", PLAYERS_CSV, exc)

    for pos in POSITIONS:
        # 1. Weekly Data
        weekly_parquet = DATA_DIR / f"{pos}_weekly.parquet"
        if weekly_parquet.exists():
            logger.info(f"Baking {pos} Weekly...")
            path_str = str(weekly_parquet).replace("\\", "/")

            columns, select_stmt = _discover_and_build(conn, weekly_parquet, pos)

            from_clause = f"read_parquet('{path_str}') src"
            if players_table_loaded and "player_id" in {c.lower() for c in columns}:
                # Upgrade to canonical UUID when mapped; keep legacy id when join misses.
                select_stmt = select_stmt.replace(
                    'src."player_id" AS "player_id"',
                    'COALESCE(p.player_id, CAST(src.player_id AS VARCHAR)) AS "player_id"',
                )
                from_clause = (
                    f"read_parquet('{path_str}') src "
                    f"LEFT JOIN players p ON CAST(src.player_id AS VARCHAR) = p.legacy_player_id"
                )

            conn.execute(f"CREATE TABLE {pos.lower()}_weekly AS SELECT {select_stmt} FROM {from_clause}")
            conn.execute(f"CREATE INDEX idx_{pos.lower()}_weekly_lookup ON {pos.lower()}_weekly (year, week)")
            conn.execute(f"CREATE INDEX idx_{pos.lower()}_weekly_player ON {pos.lower()}_weekly (player_id)")

            if pos in ("QB", "RB", "WR", "TE"):
                _attach_home_away(conn, pos)

            row_count = conn.execute(f"SELECT COUNT(*) FROM {pos.lower()}_weekly").fetchone()[0]
            logger.info(f"  -> {pos} Weekly: {row_count} rows, {len(columns)} columns")

        # 2. Seasonal Data
        seasonal_parquet = DATA_DIR / f"{pos}_seasonal.parquet"
        if seasonal_parquet.exists():
            logger.info(f"Baking {pos} Seasonal...")
            path_str = str(seasonal_parquet).replace("\\", "/")

            columns, select_stmt = _discover_and_build(conn, seasonal_parquet, pos)

            from_clause = f"read_parquet('{path_str}') src"
            if players_table_loaded and "player_id" in {c.lower() for c in columns}:
                select_stmt = select_stmt.replace(
                    'src."player_id" AS "player_id"',
                    'COALESCE(p.player_id, CAST(src.player_id AS VARCHAR)) AS "player_id"',
                )
                from_clause = (
                    f"read_parquet('{path_str}') src "
                    f"LEFT JOIN players p ON CAST(src.player_id AS VARCHAR) = p.legacy_player_id"
                )

            conn.execute(f"CREATE TABLE {pos.lower()}_seasonal AS SELECT {select_stmt} FROM {from_clause}")
            conn.execute(f"CREATE INDEX idx_{pos.lower()}_seasonal_lookup ON {pos.lower()}_seasonal (year)")
            conn.execute(f"CREATE INDEX idx_{pos.lower()}_seasonal_player ON {pos.lower()}_seasonal (player_id)")

            row_count = conn.execute(f"SELECT COUNT(*) FROM {pos.lower()}_seasonal").fetchone()[0]
            logger.info(f"  -> {pos} Seasonal: {row_count} rows, {len(columns)} columns")

    try:
        from bake_draft_lab import bake_draft_lab_tables

        bake_draft_lab_tables(conn)
    except Exception as exc:  # noqa: BLE001 - rankings bake must not fail
        logger.warning("Draft Lab bake skipped (fail-open): %s", exc)

    # Final schema audit
    logger.info("--- Bake Audit ---")
    tables = conn.execute("SHOW TABLES").fetchall()
    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
        cols = [d[0] for d in conn.execute(f"SELECT * FROM {t[0]} LIMIT 0").description]
        logger.info(
            f"Table {t[0]:<20}: {count:>6} rows | {len(cols):>2} cols -> "
            f"{', '.join(cols[:10])}{'...' if len(cols) > 10 else ''}"
        )

    conn.close()
    logger.info(
        f"Successfully baked persistent database: {DB_PATH} "
        f"({DB_PATH.stat().st_size / 1024 / 1024:.2f} MB)"
    )


if __name__ == "__main__":
    bake()

