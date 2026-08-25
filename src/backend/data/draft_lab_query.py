"""Draft Lab DuckDB queries. Ranking SQL stays in query_engine.py."""

from __future__ import annotations

import json
from typing import Any, Optional

from backend.core.exceptions import NoDataForFilterError, TableMissingError
from backend.data.query_engine import _execute, get_serving_conn


def _q(sql: str, params: list[Any] | None = None, *, context: str) -> list[dict[str, Any]]:
    get_serving_conn()
    return _execute(sql, params, context=context)


def _one_or_404(rows: list[dict[str, Any]], *, detail: str) -> dict[str, Any]:
    if not rows:
        raise NoDataForFilterError(detail)
    return rows[0]


def _parse_json_field(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    text = str(value).strip()
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def query_leagues() -> list[dict[str, Any]]:
    rows = _q(
        """
        SELECT
          league_id,
          espn_league_id,
          name,
          scoring,
          team_count,
          roster_slots_json,
          source
        FROM draft_lab_leagues
        ORDER BY name
        """,
        context="draft_lab_leagues",
    )
    return [_league_record(r) for r in rows]


def query_league(league_id: str) -> dict[str, Any]:
    rows = _q(
        """
        SELECT
          league_id,
          espn_league_id,
          name,
          scoring,
          team_count,
          roster_slots_json,
          source
        FROM draft_lab_leagues
        WHERE league_id = ?
        """,
        [league_id],
        context="draft_lab_leagues",
    )
    return _league_record(_one_or_404(rows, detail=f"No league {league_id}"))


def _league_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "league_id": row.get("league_id"),
        "espn_league_id": str(row.get("espn_league_id")) if row.get("espn_league_id") is not None else None,
        "name": row.get("name"),
        "scoring": row.get("scoring"),
        "team_count": int(row["team_count"]) if row.get("team_count") is not None else None,
        "roster_slots": _parse_json_field(row.get("roster_slots_json"), {}),
        "source": row.get("source"),
    }


def query_drafts(*, league_id: Optional[str] = None, season: Optional[int] = None) -> list[dict[str, Any]]:
    conditions: list[str] = []
    params: list[Any] = []
    if league_id:
        conditions.append("league_id = ?")
        params.append(league_id)
    if season is not None:
        conditions.append("season = ?")
        params.append(season)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = _q(
        f"""
        SELECT
          draft_id,
          league_id,
          season,
          draft_type,
          rounds,
          pick_count,
          pick_order_json
        FROM draft_lab_drafts
        {where}
        ORDER BY season DESC, draft_id
        """,
        params,
        context="draft_lab_drafts",
    )
    return [_draft_record(r) for r in rows]


def query_draft(draft_id: str) -> dict[str, Any]:
    rows = _q(
        """
        SELECT
          draft_id,
          league_id,
          season,
          draft_type,
          rounds,
          pick_count,
          pick_order_json
        FROM draft_lab_drafts
        WHERE draft_id = ?
        """,
        [draft_id],
        context="draft_lab_drafts",
    )
    return _draft_record(_one_or_404(rows, detail=f"No draft {draft_id}"))


def _draft_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "draft_id": row.get("draft_id"),
        "league_id": row.get("league_id"),
        "season": int(row["season"]) if row.get("season") is not None else None,
        "draft_type": row.get("draft_type"),
        "rounds": int(row["rounds"]) if row.get("rounds") is not None else None,
        "pick_count": int(row["pick_count"]) if row.get("pick_count") is not None else None,
        "pick_order": _parse_json_field(row.get("pick_order_json"), []),
    }


def query_picks(draft_id: str) -> list[dict[str, Any]]:
    rows = _q(
        """
        SELECT
          pick_id,
          draft_id,
          league_id,
          season,
          overall_pick,
          "round",
          round_pick,
          manager_id,
          player_id,
          espn_player_id,
          player_name,
          position,
          team,
          resolution_status,
          resolution_reason
        FROM draft_lab_picks
        WHERE draft_id = ?
        ORDER BY overall_pick
        """,
        [draft_id],
        context="draft_lab_picks",
    )
    return [_pick_record(r) for r in rows]


def _pick_record(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "pick_id": row.get("pick_id"),
        "draft_id": row.get("draft_id"),
        "league_id": row.get("league_id"),
        "season": int(row["season"]) if row.get("season") is not None else None,
        "overall_pick": int(row["overall_pick"]) if row.get("overall_pick") is not None else None,
        "round": int(row["round"]) if row.get("round") is not None else None,
        "round_pick": int(row["round_pick"]) if row.get("round_pick") is not None else None,
        "manager_id": row.get("manager_id"),
        "player_id": row.get("player_id"),
        "espn_player_id": str(row.get("espn_player_id")) if row.get("espn_player_id") is not None else None,
        "player_name": row.get("player_name"),
        "position": row.get("position"),
        "team": row.get("team"),
        "resolution_status": row.get("resolution_status"),
        "resolution_reason": row.get("resolution_reason"),
    }


def query_manager(manager_id: str) -> dict[str, Any]:
    rows = _q(
        """
        SELECT
          manager_id,
          league_id,
          espn_owner_id,
          display_name,
          team_abbrev
        FROM draft_lab_managers
        WHERE manager_id = ?
        """,
        [manager_id],
        context="draft_lab_managers",
    )
    manager = _one_or_404(rows, detail=f"No manager {manager_id}")
    try:
        profiles = _q(
            """
            SELECT
              manager_id,
              league_id,
              season_from,
              season_to,
              n_picks,
              n_drafts,
              mean_reach,
              median_reach,
              early_position_share_json,
              position_share_json,
              sample_size_ok
            FROM draft_lab_manager_profiles
            WHERE manager_id = ?
            """,
            [manager_id],
            context="draft_lab_manager_profiles",
        )
    except TableMissingError:
        profiles = []
    profile = _profile_record(profiles[0]) if profiles else None
    return {
        "manager_id": manager.get("manager_id"),
        "league_id": manager.get("league_id"),
        "espn_owner_id": manager.get("espn_owner_id"),
        "display_name": manager.get("display_name"),
        "team_abbrev": manager.get("team_abbrev"),
        "profile": profile,
    }


def _profile_record(row: dict[str, Any]) -> dict[str, Any]:
    sample = row.get("sample_size_ok")
    if isinstance(sample, str):
        sample_ok = sample.strip().lower() in {"true", "1", "t"}
    else:
        sample_ok = bool(sample)
    return {
        "season_from": int(row["season_from"]) if row.get("season_from") is not None else None,
        "season_to": int(row["season_to"]) if row.get("season_to") is not None else None,
        "n_picks": int(row["n_picks"]) if row.get("n_picks") is not None else None,
        "n_drafts": int(row["n_drafts"]) if row.get("n_drafts") is not None else None,
        "mean_reach": float(row["mean_reach"]) if row.get("mean_reach") is not None else None,
        "median_reach": float(row["median_reach"]) if row.get("median_reach") is not None else None,
        "early_position_share": _parse_json_field(row.get("early_position_share_json"), {}),
        "position_share": _parse_json_field(row.get("position_share_json"), {}),
        "sample_size_ok": sample_ok,
    }


def query_market(
    *,
    season: Optional[int] = None,
    scoring: Optional[str] = None,
    provider: Optional[str] = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    conditions: list[str] = []
    params: list[Any] = []
    if season is not None:
        conditions.append("season = ?")
        params.append(season)
    if scoring:
        conditions.append("scoring = ?")
        params.append(scoring)
    if provider:
        conditions.append("provider = ?")
        params.append(provider)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)
    rows = _q(
        f"""
        SELECT
          provider,
          season,
          scoring,
          as_of,
          player_id,
          espn_player_id,
          player_name,
          position,
          team,
          market_rank,
          adp,
          auction_value
        FROM draft_lab_market
        {where}
        ORDER BY market_rank, espn_player_id
        LIMIT ?
        """,
        params,
        context="draft_lab_market",
    )
    return [_market_record(r) for r in rows]


def _market_record(row: dict[str, Any]) -> dict[str, Any]:
    adp = row.get("adp")
    av = row.get("auction_value")
    return {
        "provider": row.get("provider"),
        "season": int(row["season"]) if row.get("season") is not None else None,
        "scoring": row.get("scoring"),
        "as_of": row.get("as_of"),
        "player_id": row.get("player_id"),
        "espn_player_id": str(row.get("espn_player_id")) if row.get("espn_player_id") is not None else None,
        "player_name": row.get("player_name"),
        "position": row.get("position"),
        "team": row.get("team"),
        "market_rank": int(row["market_rank"]) if row.get("market_rank") is not None else None,
        "adp": float(adp) if adp is not None else None,
        "auction_value": float(av) if av is not None else None,
    }


def query_backtests(*, draft_id: Optional[str] = None) -> list[dict[str, Any]]:
    conditions: list[str] = []
    params: list[Any] = []
    if draft_id:
        conditions.append("draft_id = ?")
        params.append(draft_id)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = _q(
        f"""
        SELECT
          backtest_id,
          draft_id,
          model,
          exact_hit_rate,
          top3_hit_rate,
          mean_abs_rank_error,
          position_hit_rate,
          n_picks,
          n_skipped,
          seed
        FROM draft_lab_backtests
        {where}
        ORDER BY draft_id, model
        """,
        params,
        context="draft_lab_backtests",
    )
    return [_backtest_record(r) for r in rows]


def _backtest_record(row: dict[str, Any]) -> dict[str, Any]:
    def _f(key: str) -> Optional[float]:
        val = row.get(key)
        return float(val) if val is not None else None

    return {
        "backtest_id": row.get("backtest_id"),
        "draft_id": row.get("draft_id"),
        "model": row.get("model"),
        "exact_hit_rate": _f("exact_hit_rate"),
        "top3_hit_rate": _f("top3_hit_rate"),
        "mean_abs_rank_error": _f("mean_abs_rank_error"),
        "position_hit_rate": _f("position_hit_rate"),
        "n_picks": int(row["n_picks"]) if row.get("n_picks") is not None else None,
        "n_skipped": int(row["n_skipped"]) if row.get("n_skipped") is not None else None,
        "seed": int(row["seed"]) if row.get("seed") is not None else None,
    }


def query_simulation_context(draft_id: str) -> dict[str, Any]:
    draft = query_draft(draft_id)
    league = query_league(draft["league_id"])
    picks = query_picks(draft_id)
    market = query_market(season=draft["season"], scoring=league["scoring"], limit=1000)
    managers = _q(
        """
        SELECT manager_id, league_id, espn_owner_id, display_name, team_abbrev
        FROM draft_lab_managers
        WHERE league_id = ?
        """,
        [draft["league_id"]],
        context="draft_lab_managers",
    )
    try:
        profiles = _q(
            """
            SELECT
              manager_id,
              league_id,
              season_from,
              season_to,
              n_picks,
              n_drafts,
              mean_reach,
              median_reach,
              early_position_share_json,
              position_share_json,
              sample_size_ok
            FROM draft_lab_manager_profiles
            WHERE league_id = ?
            """,
            [draft["league_id"]],
            context="draft_lab_manager_profiles",
        )
    except TableMissingError:
        profiles = []
    return {
        "draft": draft,
        "league": league,
        "picks": picks,
        "market": market,
        "managers": managers,
        "profiles": [_profile_record(p) | {"manager_id": p.get("manager_id")} for p in profiles],
    }
