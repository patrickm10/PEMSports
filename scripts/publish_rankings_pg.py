"""Publish baked DuckDB rankings into Neon Postgres (schema stats).

Modes:
  full         — truncate+reload every rankings table from the local bake
  incremental  — replace one year/week (weekly) and one year (seasonal)

Requires DATABASE_URL or DATABASE_URL_UNPOOLED (prefer unpooled for COPY).
"""
from __future__ import annotations

import argparse
import logging
import math
import os
import sys
from pathlib import Path
from typing import Any, Iterable

import duckdb
import psycopg

PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SRC = PROJECT_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "nfl_stats.db"
KNOWN_STRING = {
    "player_name",
    "player_id",
    "team",
    "position",
    "season",
    "opponent",
    "stadium_name",
    "city",
    "state",
    "indoor_outdoor",
    "surface_type",
    "game_result",
    "weather_impact",
    "home_away",
    "legacy_player_id",
    "espn_player_id",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("publish_rankings_pg")


def _pg_ident(name: str) -> str:
    cleaned = name.lower().replace('"', "")
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_-+/%")
    if not cleaned or any(ch not in allowed for ch in cleaned):
        raise ValueError(f"Unsafe identifier: {name!r}")
    return cleaned


def _pg_type(col: str, duck_type: str) -> str:
    c = col.lower()
    dt = (duck_type or "").upper()
    if c in {"year", "week"}:
        return "INTEGER"
    if c in KNOWN_STRING or "CHAR" in dt or "TEXT" in dt or "VARCHAR" in dt:
        return "TEXT"
    if "INT" in dt and "INTERVAL" not in dt:
        return "BIGINT"
    return "DOUBLE PRECISION"


def _quote_ident(name: str) -> str:
    return '"' + _pg_ident(name) + '"'


def _ensure_schema(pg: psycopg.Connection) -> None:
    pg.execute("CREATE SCHEMA IF NOT EXISTS stats")
    pg.execute("CREATE SCHEMA IF NOT EXISTS app")
    pg.execute(
        """
        CREATE TABLE IF NOT EXISTS app.stats_generation (
            id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
            generation BIGINT NOT NULL DEFAULT 0,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    pg.execute(
        "INSERT INTO app.stats_generation (id, generation) VALUES (1, 0) "
        "ON CONFLICT (id) DO NOTHING"
    )
    pg.execute(
        """
        CREATE TABLE IF NOT EXISTS app.data_refresh_log (
            id SERIAL PRIMARY KEY,
            run_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            position VARCHAR(10) NOT NULL,
            year INTEGER,
            week INTEGER,
            rows_processed INTEGER NOT NULL,
            status VARCHAR(20) NOT NULL,
            error_message TEXT
        )
        """
    )


def _duck_tables(duck: duckdb.DuckDBPyConnection) -> list[str]:
    rows = duck.execute("SHOW TABLES").fetchall()
    return [r[0] for r in rows]


def _duck_schema(duck: duckdb.DuckDBPyConnection, table: str) -> list[tuple[str, str]]:
    rows = duck.execute(f"PRAGMA table_info('{table}')").fetchall()
    # cid, name, type, notnull, dflt_value, pk
    return [(r[1], r[2] or "") for r in rows]


def _ensure_table(
    pg: psycopg.Connection, table: str, columns: list[tuple[str, str]]
) -> None:
    ident = _pg_ident(table)
    col_sql = []
    for name, duck_type in columns:
        col_sql.append(f"{_quote_ident(name)} {_pg_type(name, duck_type)}")
    pg.execute(
        f"CREATE TABLE IF NOT EXISTS stats.{ident} ({', '.join(col_sql)})"
    )
    existing = {
        r[0]
        for r in pg.execute(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema = 'stats' AND table_name = %s
            """,
            (ident,),
        ).fetchall()
    }
    for name, duck_type in columns:
        n = _pg_ident(name)
        if n not in existing:
            pg.execute(
                f"ALTER TABLE stats.{ident} ADD COLUMN {_quote_ident(n)} {_pg_type(name, duck_type)}"
            )
    names = [_pg_ident(n) for n, _ in columns]
    if "year" in names and "week" in names:
        pg.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{ident}_yw ON stats.{ident} (year, week)"
        )
    elif "year" in names:
        pg.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{ident}_year ON stats.{ident} (year)"
        )
    if "player_id" in names:
        pg.execute(
            f"CREATE INDEX IF NOT EXISTS idx_{ident}_player ON stats.{ident} (player_id)"
        )


def _coerce_copy_value(col: str, duck_type: str, value: Any) -> Any:
    """DuckDB often emits year/week as 2025.0; Postgres INTEGER rejects that text."""
    if value is None:
        return None
    target = _pg_type(col, duck_type)
    if target not in {"INTEGER", "BIGINT"}:
        return value
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return int(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        return int(float(s)) if "." in s else int(s)
    return int(value)


def _copy_rows(
    pg: psycopg.Connection,
    table: str,
    columns: list[str],
    rows: Iterable[tuple[Any, ...]],
    duck_types: list[str],
) -> int:
    ident = _pg_ident(table)
    col_list = ", ".join(_quote_ident(c) for c in columns)
    count = 0
    with pg.cursor() as cur:
        with cur.copy(f"COPY stats.{ident} ({col_list}) FROM STDIN") as copy:
            for row in rows:
                copy.write_row(
                    tuple(
                        _coerce_copy_value(col, dtype, val)
                        for col, dtype, val in zip(columns, duck_types, row)
                    )
                )
                count += 1
    return count


def _log_refresh(
    pg: psycopg.Connection,
    *,
    position: str,
    year: int | None,
    week: int | None,
    rows: int,
    status: str,
    error: str | None = None,
) -> None:
    pg.execute(
        """
        INSERT INTO app.data_refresh_log
            (position, year, week, rows_processed, status, error_message)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (position, year, week, rows, status, error),
    )


def publish(
    *,
    duck_path: Path,
    dsn: str,
    mode: str,
    year: int | None,
    week: int | None,
) -> None:
    if not duck_path.exists():
        raise SystemExit(f"DuckDB bake not found at {duck_path}. Run scripts/bake_db.py.")
    duck = duckdb.connect(str(duck_path), read_only=True)
    pg = psycopg.connect(dsn, autocommit=False)
    try:
        _ensure_schema(pg)
        tables = _duck_tables(duck)
        ranking_tables = [
            t
            for t in tables
            if t.endswith("_weekly") or t.endswith("_seasonal") or t == "players"
            or t.startswith("draft_lab_")
        ]
        for table in ranking_tables:
            schema = _duck_schema(duck, table)
            cols = [c[0] for c in schema]
            _ensure_table(pg, table, schema)
            ident = _pg_ident(table)
            is_weekly = table.endswith("_weekly")
            is_seasonal = table.endswith("_seasonal")
            pos = table.split("_")[0]

            if mode == "full":
                pg.execute(f"TRUNCATE stats.{ident}")
                source_sql = f"SELECT * FROM {table}"
            elif is_weekly and year is not None and week is not None:
                pg.execute(
                    f"DELETE FROM stats.{ident} WHERE year = %s AND week = %s",
                    (year, week),
                )
                source_sql = (
                    f"SELECT * FROM {table} WHERE CAST(year AS INTEGER) = {int(year)} "
                    f"AND CAST(week AS INTEGER) = {int(week)}"
                )
            elif is_seasonal and year is not None:
                pg.execute(
                    f"DELETE FROM stats.{ident} WHERE year = %s",
                    (year,),
                )
                source_sql = (
                    f"SELECT * FROM {table} WHERE CAST(year AS INTEGER) = {int(year)}"
                )
            elif table == "players" or table.startswith("draft_lab_"):
                if mode == "incremental" and year is not None:
                    # Refresh dimension/lab on full or when explicitly full-loading those tables
                    if table == "players":
                        pg.execute(f"TRUNCATE stats.{ident}")
                        source_sql = f"SELECT * FROM {table}"
                    else:
                        continue
                else:
                    pg.execute(f"TRUNCATE stats.{ident}")
                    source_sql = f"SELECT * FROM {table}"
            else:
                continue

            result = duck.execute(source_sql)
            raw_rows = result.fetchall()
            duck_types = [c[1] for c in schema]
            n = (
                _copy_rows(pg, table, cols, raw_rows, duck_types)
                if raw_rows
                else 0
            )
            logger.info("Published %s (%s) → %d rows", table, mode, n)
            _log_refresh(
                pg,
                position=pos[:10],
                year=year,
                week=week if is_weekly else None,
                rows=n,
                status="ok",
            )

        pg.execute(
            "UPDATE app.stats_generation SET generation = generation + 1, "
            "updated_at = NOW() WHERE id = 1"
        )
        pg.commit()
        logger.info("Publish complete; stats_generation bumped.")
    except Exception:
        pg.rollback()
        raise
    finally:
        pg.close()
        duck.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish DuckDB bake to Neon Postgres.")
    parser.add_argument("--mode", choices=["full", "incremental"], default="full")
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--week", type=int, default=None)
    parser.add_argument(
        "--db-path",
        default=os.environ.get("NFL_STATS_DB_PATH", str(DEFAULT_DB_PATH)),
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL_UNPOOLED") or os.environ.get("DATABASE_URL"),
    )
    args = parser.parse_args()
    if not args.database_url:
        print("DATABASE_URL or DATABASE_URL_UNPOOLED is required.", file=sys.stderr)
        return 2
    if args.mode == "incremental" and args.year is None:
        print("incremental mode requires --year (and --week for weekly tables).", file=sys.stderr)
        return 2
    publish(
        duck_path=Path(args.db_path).resolve(),
        dsn=args.database_url,
        mode=args.mode,
        year=args.year,
        week=args.week,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
