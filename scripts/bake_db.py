"""
Bake Script: Compiles Parquet Data Lake into a Persistent DuckDB Serving Layer.
Solves PlainSkip errors and optimizes for cloud hosting.

Multi-year history: every `data/rankings/*.parquet` matching
`{POS}_{weekly|seasonal}.parquet` or `{POS}_{YYYY}_{weekly|seasonal}.parquet`
is merged into the serving table for that position (DuckDB unions files by name).

Column Strategy: Dynamic discovery with blacklist pruning.
Instead of a static whitelist (which silently drops performance metrics like
YDS, TD, CMP, ATT, etc.), we read ALL columns from the source Parquet and
exclude only known artifacts (_right join suffixes, raw scrape duplicates).
"""
import duckdb
import logging
import re
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bake_db")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "rankings"
DB_PATH = PROJECT_ROOT / "data" / "nfl_stats.db"

POSITIONS = ["QB", "RB", "WR", "TE", "K", "DST"]

# Files under data/rankings/: legacy combined `{POS}_weekly.parquet` or per-year
# `{POS}_{YYYY}_weekly.parquet` (same for seasonal).
_RANKING_PARQUET = re.compile(
    r"^(?P<pos>QB|RB|WR|TE|K|DST)_(?:(?P<year>\d{4})_)?(?P<kind>weekly|seasonal)\.parquet$",
    re.IGNORECASE,
)

# Columns excluded from all tables.
# Rank: computed dynamically via ROW_NUMBER() in query_engine.
# Player: raw scrape artifact, duplicate of player_name.
GLOBAL_BLACKLIST = {"Rank", "Player"}

# Columns known to be strings — preserved without numeric casting.
KNOWN_STRING = {
    "player_name", "player_id", "team", "position", "season",
    "opponent", "stadium_name", "city", "state", "indoor_outdoor",
    "surface_type", "game_result",
}

# Filter dimensions: INTEGER in DuckDB (not DOUBLE from TRY_CAST) for `year = ?` / indexes.
KNOWN_INT = {"year", "week"}

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
        "R_YDS": "rush_yds", "R_TD": "rush_td", "ATT": "att"
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


def _collect_ranking_parquet_groups() -> dict[tuple[str, str], list[Path]]:
    """
    Glob `data/rankings/*.parquet` and group paths by (UPPER position, weekly|seasonal).

    Unmatched files are logged and skipped (so stray parquet does not break the bake).
    """
    groups: dict[tuple[str, str], list[Path]] = {}
    for p in sorted(DATA_DIR.glob("*.parquet")):
        m = _RANKING_PARQUET.match(p.name)
        if not m:
            logger.warning("Skipping unrecognized parquet (expected *_{weekly,seasonal}.parquet): %s", p.name)
            continue
        pos = m.group("pos").upper()
        kind = m.group("kind").lower()
        groups.setdefault((pos, kind), []).append(p.resolve())

    # Stable merge order: optional year in filename, then path
    def sort_key(path: Path) -> tuple[int, str]:
        mm = _RANKING_PARQUET.match(path.name)
        y = int(mm.group("year")) if mm and mm.group("year") else 0
        return (y, str(path).lower())

    for key in groups:
        groups[key].sort(key=sort_key)
    return groups


def _sql_read_parquet_union(paths: list[Path]) -> str:
    """DuckDB read_parquet over one or more files, aligning columns across years."""
    parts: list[str] = []
    for p in paths:
        s = str(p).replace("\\", "/").replace("'", "''")
        parts.append(f"'{s}'")
    return f"read_parquet([{', '.join(parts)}], union_by_name=true)"


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
        if c == "player_name" and has_player_raw:
            # Prefer enriched player_name, fall back to raw Player column
            exprs.append(f'COALESCE("player_name", "Player") AS "{out_name}"')
        elif out_name in KNOWN_STRING:
            # Metadata strings
            exprs.append(f'"{c}" AS "{out_name}"')
        elif out_name in KNOWN_INT:
            exprs.append(f'TRY_CAST("{c}" AS INTEGER) AS "{out_name}"')
        else:
            # All performance metrics & numeric metadata (temp, wind, fpts)
            # TRY_CAST to DOUBLE ensures schema stability for the frontend
            exprs.append(f'TRY_CAST("{c}" AS DOUBLE) AS "{out_name}"')

    return final_cols, ", ".join(exprs)


def bake():
    if DB_PATH.exists():
        logger.info(f"Removing existing database at {DB_PATH}")
        DB_PATH.unlink()

    conn = duckdb.connect(str(DB_PATH))

    groups = _collect_ranking_parquet_groups()

    for pos in POSITIONS:
        # 1. Weekly Data
        weekly_paths = groups.get((pos, "weekly"), [])
        if weekly_paths:
            logger.info("Baking %s Weekly from %d parquet file(s): %s", pos, len(weekly_paths), weekly_paths)
            columns, select_stmt = _discover_and_build(conn, weekly_paths[0], pos)
            from_src = _sql_read_parquet_union(weekly_paths)

            conn.execute(
                f"CREATE TABLE {pos.lower()}_weekly AS "
                f"SELECT {select_stmt} FROM {from_src}"
            )
            conn.execute(f"CREATE INDEX idx_{pos.lower()}_weekly_lookup ON {pos.lower()}_weekly (year, week)")
            conn.execute(f"CREATE INDEX idx_{pos.lower()}_weekly_player ON {pos.lower()}_weekly (player_id)")

            row_count = conn.execute(f"SELECT COUNT(*) FROM {pos.lower()}_weekly").fetchone()[0]
            logger.info(f"  -> {pos} Weekly: {row_count} rows, {len(columns)} columns")

        # 2. Seasonal Data
        seasonal_paths = groups.get((pos, "seasonal"), [])
        if seasonal_paths:
            logger.info("Baking %s Seasonal from %d parquet file(s): %s", pos, len(seasonal_paths), seasonal_paths)
            columns, select_stmt = _discover_and_build(conn, seasonal_paths[0], pos)
            from_src = _sql_read_parquet_union(seasonal_paths)

            conn.execute(
                f"CREATE TABLE {pos.lower()}_seasonal AS "
                f"SELECT {select_stmt} FROM {from_src}"
            )
            conn.execute(f"CREATE INDEX idx_{pos.lower()}_seasonal_lookup ON {pos.lower()}_seasonal (year)")
            conn.execute(f"CREATE INDEX idx_{pos.lower()}_seasonal_player ON {pos.lower()}_seasonal (player_id)")

            row_count = conn.execute(f"SELECT COUNT(*) FROM {pos.lower()}_seasonal").fetchone()[0]
            logger.info(f"  -> {pos} Seasonal: {row_count} rows, {len(columns)} columns")

    # Final schema audit
    logger.info("--- Bake Audit ---")
    tables = conn.execute("SHOW TABLES").fetchall()
    table_names = {t[0] for t in tables}
    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {t[0]}").fetchone()[0]
        cols = [d[0] for d in conn.execute(f"SELECT * FROM {t[0]} LIMIT 0").description]
        logger.info(
            f"Table {t[0]:<20}: {count:>6} rows | {len(cols):>2} cols -> "
            f"{', '.join(cols[:10])}{'...' if len(cols) > 10 else ''}"
        )

    for sample in ("qb_weekly", "qb_seasonal"):
        if sample in table_names:
            types = conn.execute(
                "SELECT column_name, data_type FROM information_schema.columns "
                f"WHERE table_name = '{sample}' AND column_name IN ('year', 'week') "
                "ORDER BY column_name"
            ).fetchall()
            logger.info("Filter columns (%s): %s", sample, types)

    conn.close()
    logger.info(
        f"Successfully baked persistent database: {DB_PATH} "
        f"({DB_PATH.stat().st_size / 1024 / 1024:.2f} MB)"
    )


if __name__ == "__main__":
    bake()

