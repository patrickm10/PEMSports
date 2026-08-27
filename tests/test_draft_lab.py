"""Draft Lab mapper, ingest, resolution, simulate, bake, and route contracts."""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from pipelines.draft_lab.espn_mapper import map_espn_payload, scoring_from_settings
from pipelines.draft_lab.ids import draft_id_for, league_id_for
from pipelines.draft_lab.ingest import ingest_payloads, load_fixture_payloads
from pipelines.draft_lab.manager_profiles import build_manager_profiles
from pipelines.draft_lab.player_resolution import (
    PlayerResolver,
    ResolutionReport,
    load_players_dimension,
    resolve_picks,
    unresolved_rows,
)
from pipelines.draft_lab.simulate import SimPlayer, recommend, roster_counts_from_picks
from pipelines.draft_lab.backtest import run_backtests_for_draft

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "draft_lab"
LEAGUE_JSON = FIXTURES / "league_2024.json"
PLAYERS_CSV = FIXTURES / "players.csv"


@pytest.fixture(scope="module")
def espn_payload() -> dict:
    return json.loads(LEAGUE_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def mapped_bundle(espn_payload):
    return map_espn_payload(espn_payload, source="fixture", as_of="fixture", provider="fixture")


def test_mapper_snake_ppr_and_ids(mapped_bundle, espn_payload):
    assert mapped_bundle.league.scoring == "ppr"
    assert mapped_bundle.draft.draft_type == "SNAKE"
    assert mapped_bundle.draft.pick_count == 30
    assert mapped_bundle.league.team_count == 10
    assert mapped_bundle.league.league_id == league_id_for(espn_payload["id"])
    assert mapped_bundle.draft.draft_id == draft_id_for(espn_payload["id"], 2024)
    assert len(mapped_bundle.managers) == 10
    assert len(mapped_bundle.picks) == 30
    assert mapped_bundle.picks[0].overall_pick == 1
    assert any(row.market_rank == 1 for row in mapped_bundle.market)


def test_scoring_from_reception_points():
    assert scoring_from_settings({"scoringSettings": {"scoringItems": [{"statId": 53, "points": 1}]}}) == "ppr"
    assert scoring_from_settings({"scoringSettings": {"scoringItems": [{"statId": 53, "points": 0.5}]}}) == "half"
    assert scoring_from_settings({"scoringSettings": {"scoringItems": [{"statId": 53, "points": 0}]}}) == "std"


def test_mapper_rejects_auction():
    with pytest.raises(ValueError, match="snake only"):
        map_espn_payload(
            {
                "id": 1,
                "seasonId": 2024,
                "settings": {"size": 2, "draftSettings": {"type": "AUCTION", "rounds": 1}},
                "teams": [{"id": 1}, {"id": 2}],
                "draftDetail": {"picks": []},
            },
            source="fixture",
        )


def test_resolution_never_drops_unresolved(mapped_bundle):
    resolver = PlayerResolver(load_players_dimension(PLAYERS_CSV))
    report = ResolutionReport()
    resolve_picks(mapped_bundle.picks, resolver, report)
    leftover = unresolved_rows(mapped_bundle.picks)
    assert report.resolved + report.unresolved + report.ambiguous == 30
    assert report.unresolved >= 1
    assert leftover
    assert all(row["espn_player_id"] for row in leftover)
    assert all(p.resolution_status in {"resolved", "unresolved", "ambiguous"} for p in mapped_bundle.picks)
    unknown = [p for p in mapped_bundle.picks if p.espn_player_id == "1036"]
    assert len(unknown) == 1
    assert unknown[0].resolution_status == "unresolved"
    assert unknown[0].player_id is None


def test_simulate_is_deterministic():
    remaining = [
        SimPlayer("2", "B", "WR", "MIA", 2, "bbb"),
        SimPlayer("1", "A", "RB", "SF", 1, "aaa"),
        SimPlayer("3", "C", "WR", "MIN", 3, "ccc"),
    ]
    a = recommend(
        remaining=remaining,
        roster_counts={},
        roster_slots={"RB": 2, "WR": 2, "FLEX": 1, "BENCH": 6},
        overall_pick=1,
        team_count=10,
        model="market_only",
        seed=0,
        limit=3,
    )
    b = recommend(
        remaining=remaining,
        roster_counts={},
        roster_slots={"RB": 2, "WR": 2, "FLEX": 1, "BENCH": 6},
        overall_pick=1,
        team_count=10,
        model="market_only",
        seed=0,
        limit=3,
    )
    assert [r.espn_player_id for r in a.recommendations] == ["1", "2", "3"]
    assert a.as_dict() == b.as_dict()
    rec = a.recommendations[0]
    assert rec.explanation["components"]["market_component"] is not None
    assert rec.explanation["components"]["roster_need_component"] == 0.0
    assert rec.explanation["components"]["manager_position_component"] == 0.0


def test_roster_counts_skips_null_overall_pick():
    from types import SimpleNamespace

    pick = SimpleNamespace(manager_id="m1", overall_pick=None, position="RB")
    assert roster_counts_from_picks([pick], manager_id="m1", before_overall=5) == {}


def test_simulate_manager_model_exposes_components():
    remaining = [
        SimPlayer("1", "RB One", "RB", "SF", 1, "aaa"),
        SimPlayer("2", "WR One", "WR", "MIA", 2, "bbb"),
    ]
    result = recommend(
        remaining=remaining,
        roster_counts={"RB": 0},
        roster_slots={"RB": 2, "WR": 2, "FLEX": 1},
        overall_pick=1,
        team_count=10,
        model="market_plus_manager",
        seed=0,
        limit=2,
        early_share={"WR": 0.9, "RB": 0.1},
        position_share={"WR": 0.9, "RB": 0.1},
        sample_size_ok=True,
    )
    keys = result.recommendations[0].explanation["components"]
    assert set(keys) == {
        "market_component",
        "roster_need_component",
        "manager_position_component",
    }
    assert all(isinstance(v, float) for v in keys.values())


def test_ingest_and_backtest_shape(tmp_path, mapped_bundle):
    payloads = load_fixture_payloads(FIXTURES)
    summary = ingest_payloads(
        payloads,
        source="fixture",
        provider="fixture",
        as_of="fixture",
        players_csv=PLAYERS_CSV,
        out_dir=tmp_path,
        seed=0,
    )
    assert summary["picks"] == 30
    assert summary["unresolved"] >= 1
    assert summary["backtests"] == 2
    assert (tmp_path / "picks.parquet").exists()
    assert (tmp_path / "unresolved_players.parquet").exists()
    assert (tmp_path / "backtests.parquet").exists()

    resolver = PlayerResolver(load_players_dimension(PLAYERS_CSV))
    resolve_picks(mapped_bundle.picks, resolver)
    from pipelines.draft_lab.player_resolution import resolve_market

    resolve_market(mapped_bundle.market, resolver)
    profiles = build_manager_profiles(mapped_bundle.picks, mapped_bundle.market)
    results = run_backtests_for_draft(
        draft=mapped_bundle.draft,
        picks=mapped_bundle.picks,
        market=mapped_bundle.market,
        profiles=profiles,
        roster_slots_json=mapped_bundle.league.roster_slots_json,
        seed=0,
    )
    assert {r.model for r in results} == {"market_only", "market_plus_manager"}
    for row in results:
        assert row.n_picks > 0
        assert row.exact_hit_rate is not None
        assert 0.0 <= row.exact_hit_rate <= 1.0
        assert row.top3_hit_rate is not None
        assert row.mean_abs_rank_error is not None
        assert row.position_hit_rate is not None
        again = run_backtests_for_draft(
            draft=mapped_bundle.draft,
            picks=mapped_bundle.picks,
            market=mapped_bundle.market,
            profiles=profiles,
            roster_slots_json=mapped_bundle.league.roster_slots_json,
            seed=0,
        )
        match = next(x for x in again if x.model == row.model)
        assert match.exact_hit_rate == row.exact_hit_rate


def test_bake_draft_lab_from_parquet(tmp_path):
    ingest_payloads(
        load_fixture_payloads(FIXTURES),
        source="fixture",
        provider="fixture",
        as_of="fixture",
        players_csv=PLAYERS_CSV,
        out_dir=tmp_path,
        seed=0,
    )
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "bake_draft_lab",
        Path(__file__).resolve().parent.parent / "scripts" / "bake_draft_lab.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkey_dir = tmp_path
    mod.DRAFT_LAB_DIR = monkey_dir
    conn = duckdb.connect(str(tmp_path / "test.db"))
    created = mod.bake_draft_lab_tables(conn)
    assert created == 8
    n_picks = conn.execute("SELECT COUNT(*) FROM draft_lab_picks").fetchone()[0]
    n_unresolved = conn.execute(
        "SELECT COUNT(*) FROM draft_lab_picks WHERE resolution_status = 'unresolved'"
    ).fetchone()[0]
    assert n_picks == 30
    assert n_unresolved >= 1
    conn.close()


def test_bake_fail_open_without_parquet(tmp_path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "bake_draft_lab",
        Path(__file__).resolve().parent.parent / "scripts" / "bake_draft_lab.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    empty = tmp_path / "empty_lake"
    empty.mkdir()
    mod.DRAFT_LAB_DIR = empty
    conn = duckdb.connect(str(tmp_path / "empty.db"))
    assert mod.bake_draft_lab_tables(conn) == 0
    tables = {r[0] for r in conn.execute("SHOW TABLES").fetchall()}
    assert not any(name.startswith("draft_lab_") for name in tables)
    conn.close()


def test_bake_draft_lab_preserves_table_on_corrupt_rebake(tmp_path):
    import importlib.util
    import polars as pl

    spec = importlib.util.spec_from_file_location(
        "bake_draft_lab",
        Path(__file__).resolve().parent.parent / "scripts" / "bake_draft_lab.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.DRAFT_LAB_DIR = tmp_path
    mod.TABLES = (("draft_lab_picks", "picks.parquet", ("draft_id",)),)

    pl.DataFrame(
        {
            "draft_id": ["d1"],
            "player_id": ["p1"],
            "manager_id": ["m1"],
            "overall_pick": [1],
            "position": ["RB"],
        }
    ).write_parquet(tmp_path / "picks.parquet")

    conn = duckdb.connect(str(tmp_path / "rebake.db"))
    mod.bake_draft_lab_tables(conn)
    assert conn.execute("SELECT COUNT(*) FROM draft_lab_picks").fetchone()[0] == 1

    (tmp_path / "picks.parquet").write_text("bad")
    mod.bake_draft_lab_tables(conn)
    assert conn.execute("SELECT COUNT(*) FROM draft_lab_picks").fetchone()[0] == 1
    conn.close()


def test_draft_lab_routes_missing_tables_or_contract(client: TestClient):
    response = client.get("/api/v1/draft-lab/leagues")
    assert response.status_code in (200, 404)
    if response.status_code == 200:
        body = response.json()
        assert "leagues" in body
        assert isinstance(body["leagues"], list)
        if body["leagues"]:
            row = body["leagues"][0]
            for key in (
                "league_id",
                "espn_league_id",
                "name",
                "scoring",
                "team_count",
                "roster_slots",
                "source",
            ):
                assert key in row


def test_simulate_invalid_model_is_422(client: TestClient):
    response = client.post(
        "/api/v1/draft-lab/simulate",
        json={
            "draft_id": "x",
            "overall_pick": 1,
            "model": "magic",
            "seed": 0,
        },
    )
    assert response.status_code == 422


def test_http_client_fetch_json_returns_none_on_error(monkeypatch):
    from pipelines import http_client
    import requests

    def boom(*_args, **_kwargs):
        raise requests.RequestException("nope")

    monkeypatch.setattr(http_client._session, "get", boom)
    assert http_client.fetch_json("https://example.invalid/x") is None
