"""Draft Lab ingest CLI: ESPN JSON fixtures or live API → parquet lake."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipelines.draft_lab.backtest import run_backtests_for_draft
from pipelines.draft_lab.espn_client import fetch_live_payloads
from pipelines.draft_lab.espn_mapper import map_espn_payloads
from pipelines.draft_lab.manager_profiles import build_manager_profiles
from pipelines.draft_lab.models import MappedEspnBundle
from pipelines.draft_lab.player_resolution import (
    PlayerResolver,
    ResolutionReport,
    load_players_dimension,
    resolve_market,
    resolve_picks,
    unresolved_rows,
)
from pipelines.draft_lab.storage import write_lake
from pipelines.logger import get_pipeline_logger

logger = get_pipeline_logger("draft_lab")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_fixture_payloads(fixtures_dir: Path) -> list[Any]:
    if not fixtures_dir.exists():
        raise FileNotFoundError(f"Fixtures directory not found: {fixtures_dir}")
    payloads: list[Any] = []
    for path in sorted(fixtures_dir.glob("*.json")):
        with path.open(encoding="utf-8") as fh:
            raw = json.load(fh)
        if isinstance(raw, list):
            payloads.extend(raw)
        else:
            payloads.append(raw)
        logger.info("Loaded fixture %s", path.name)
    if not payloads:
        raise ValueError(f"No JSON fixtures in {fixtures_dir}")
    return payloads


def _dedupe_managers(bundles: list[MappedEspnBundle]) -> list:
    seen: set[str] = set()
    out = []
    for bundle in bundles:
        for manager in bundle.managers:
            if manager.manager_id in seen:
                continue
            seen.add(manager.manager_id)
            out.append(manager)
    return out


def ingest_payloads(
    payloads: list[Any],
    *,
    source: str,
    provider: str,
    as_of: str,
    players_csv: Path,
    out_dir: Path,
    seed: int = 0,
) -> dict[str, Any]:
    bundles = map_espn_payloads(payloads, source=source, as_of=as_of, provider=provider)
    resolver = PlayerResolver(load_players_dimension(players_csv))
    report = ResolutionReport()

    leagues = []
    drafts = []
    picks = []
    market = []
    for bundle in bundles:
        resolve_picks(bundle.picks, resolver, report)
        resolve_market(bundle.market, resolver)
        leagues.append(bundle.league)
        drafts.append(bundle.draft)
        picks.extend(bundle.picks)
        market.extend(bundle.market)

    managers = _dedupe_managers(bundles)
    unresolved = unresolved_rows(picks)
    profiles = build_manager_profiles(picks, market)

    backtests = []
    for bundle in bundles:
        backtests.extend(
            run_backtests_for_draft(
                draft=bundle.draft,
                picks=bundle.picks,
                market=bundle.market,
                profiles=profiles,
                roster_slots_json=bundle.league.roster_slots_json,
                seed=seed,
            )
        )

    paths = write_lake(
        out_dir=out_dir,
        leagues=leagues,
        drafts=drafts,
        managers=managers,
        picks=picks,
        unresolved=unresolved,
        market=market,
        profiles=profiles,
        backtests=backtests,
    )
    summary = {
        "leagues": len(leagues),
        "drafts": len(drafts),
        "managers": len(managers),
        "picks": len(picks),
        "market_rows": len(market),
        "unresolved": report.unresolved,
        "ambiguous": report.ambiguous,
        "resolved": report.resolved,
        "profiles": len(profiles),
        "backtests": len(backtests),
        "paths": paths,
    }
    logger.info("Draft Lab ingest complete: %s", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    root = _repo_root()
    parser = argparse.ArgumentParser(description="Ingest ESPN snake drafts into Draft Lab parquet.")
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=None,
        help="Directory of ESPN-shaped JSON fixtures (default: tests/fixtures/draft_lab).",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Fetch ESPN JSON using ESPN_S2 / ESPN_SWID / ESPN_LEAGUE_IDS.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=root / "data" / "draft_lab",
        help="Parquet lake directory.",
    )
    parser.add_argument(
        "--players-csv",
        type=Path,
        default=root / "data" / "players.csv",
        help="Canonical players dimension CSV.",
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--provider", default=None, help="Market provider label.")
    args = parser.parse_args(argv)

    as_of = datetime.now(timezone.utc).date().isoformat()
    try:
        if args.live:
            payloads = fetch_live_payloads()
            if not payloads:
                logger.error("Live ESPN fetch returned no payloads")
                return 1
            provider = args.provider or "espn_draft_ranks"
            source_label = "espn_live"
        else:
            fixtures_dir = args.fixtures or (root / "tests" / "fixtures" / "draft_lab")
            payloads = load_fixture_payloads(fixtures_dir)
            provider = args.provider or "fixture"
            source_label = "fixture"
            as_of = "fixture"
        ingest_payloads(
            payloads,
            source=source_label,
            provider=provider,
            as_of=as_of,
            players_csv=args.players_csv,
            out_dir=args.out,
            seed=args.seed,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        logger.error("Draft Lab ingest failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
