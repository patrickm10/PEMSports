"""Write normalized Draft Lab parquet to the data lake."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Optional

import polars as pl

from pipelines.draft_lab.backtest import BacktestResult
from pipelines.draft_lab.manager_profiles import ManagerProfile
from pipelines.draft_lab.models import (
    MappedDraft,
    MappedLeague,
    MappedManager,
    MappedMarketRow,
    MappedPick,
)

PARQUET_NAMES = {
    "leagues": "leagues.parquet",
    "drafts": "drafts.parquet",
    "managers": "managers.parquet",
    "picks": "picks.parquet",
    "unresolved_players": "unresolved_players.parquet",
    "market": "market.parquet",
    "manager_profiles": "manager_profiles.parquet",
    "backtests": "backtests.parquet",
}


def _write(df: pl.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.write_parquet(path)


def _records(rows: Iterable[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        if hasattr(row, "__dataclass_fields__"):
            out.append(asdict(row))
        else:
            out.append(dict(row))
    return out


def write_table(name: str, rows: Iterable[Any], out_dir: Path, *, schema: Optional[dict] = None) -> Path:
    filename = PARQUET_NAMES[name]
    path = out_dir / filename
    records = _records(rows)
    if records:
        df = pl.DataFrame(records)
    elif schema:
        df = pl.DataFrame(schema=schema)
    else:
        df = pl.DataFrame()
    _write(df, path)
    return path


def write_lake(
    *,
    out_dir: Path,
    leagues: list[MappedLeague],
    drafts: list[MappedDraft],
    managers: list[MappedManager],
    picks: list[MappedPick],
    unresolved: list[dict[str, str]],
    market: list[MappedMarketRow],
    profiles: list[ManagerProfile],
    backtests: list[BacktestResult],
) -> dict[str, str]:
    paths = {
        "leagues": write_table("leagues", leagues, out_dir),
        "drafts": write_table("drafts", drafts, out_dir),
        "managers": write_table(
            "managers",
            [
                {
                    "manager_id": m.manager_id,
                    "league_id": m.league_id,
                    "espn_owner_id": m.espn_owner_id,
                    "display_name": m.display_name,
                    "team_abbrev": m.team_abbrev,
                }
                for m in managers
            ],
            out_dir,
        ),
        "picks": write_table("picks", picks, out_dir),
        "unresolved_players": write_table("unresolved_players", unresolved, out_dir),
        "market": write_table("market", market, out_dir),
        "manager_profiles": write_table("manager_profiles", profiles, out_dir),
        "backtests": write_table("backtests", backtests, out_dir),
    }
    return {k: str(v) for k, v in paths.items()}
