"""
Unit tests for the offensive rankings pipeline modules.
Run: python -m pytest pipelines/tests/test_offensive_pipeline.py -v
"""

import polars as pl
import pytest

from pipelines.constants import SCORING_RULES, TEAM_MAP
from pipelines.features.scoring import apply_scoring_features
from pipelines.scrapers.fantasypros import _rename_duplicate_headers
from pipelines.transforms.player_stats import (
    clean_player_data,
    clean_player_name,
)
from pipelines.transforms.team_stats import extract_dst_team_abbr as extract_team


# ── extract_team ──────────────────────────────────────────────────────

class TestExtractTeam:
    def test_standard(self):
        assert extract_team("Josh Allen (BUF)") == "buffalo_bills"

    def test_newline_in_name(self):
        assert extract_team("Josh Allen\n(BUF)") == "buffalo_bills"

    def test_no_team(self):
        assert extract_team("Josh Allen") is None

    def test_non_string(self):
        assert extract_team(123) is None

    def test_unknown_abbr_passthrough(self):
        # Abbreviation not in TEAM_MAP should be returned as-is
        assert extract_team("Player (XYZ)") == "XYZ"


# ── clean_player_name ────────────────────────────────────────────────

class TestCleanPlayerName:
    def test_strips_team(self):
        assert clean_player_name("Lamar Jackson (BAL)") == "Lamar Jackson"

    def test_no_team(self):
        assert clean_player_name("Lamar Jackson") == "Lamar Jackson"

    def test_non_string(self):
        result = clean_player_name(42)
        assert result == 42  # returned as-is with a warning


# ── _rename_duplicate_headers ────────────────────────────────────────

class TestRenameDuplicateHeaders:
    def test_no_dupes(self):
        assert _rename_duplicate_headers(["A", "B", "C"]) == ["A", "B", "C"]

    def test_with_dupes(self):
        result = _rename_duplicate_headers(["PLAYER", "ATT", "YDS", "ATT", "YDS"])
        assert result == ["PLAYER", "ATT", "YDS", "R_ATT", "R_YDS"]


# ── calculate_ppr_points ─────────────────────────────────────────────

class TestCalculatePPRPoints:
    def test_qb_scoring(self):
        df = pl.DataFrame({
            "YDS": ["300"],
            "TD": ["3"],
            "INT": ["1"],
        })
        result = apply_scoring_features(df, "QB")
        assert "fpts_ppr" in result.columns
        # 300*0.05 + 3*4 + 1*(-2) = 15 + 12 - 2 = 25
        assert result["fpts_ppr"][0] == 25.0

    def test_wr_scoring(self):
        df = pl.DataFrame({
            "REC": ["8"],
            "YDS": ["120"],
            "TD": ["1"],
        })
        result = apply_scoring_features(df, "WR")
        # 8*1 + 120*0.1 + 1*6 = 8 + 12 + 6 = 26
        assert result["fpts_ppr"][0] == 26.0

    def test_unknown_position(self):
        df = pl.DataFrame({"YDS": ["100"]})
        result = apply_scoring_features(df, "PUNTER")
        # Unknown position defaults to 0 score but still creates the columns
        assert "fpts_ppr" in result.columns
        assert result["fpts_ppr"][0] == 0.0

    def test_empty_dataframe(self):
        df = pl.DataFrame()
        result = apply_scoring_features(df, "QB")
        assert result.is_empty()


# ── clean_player_data ─────────────────────────────────────────────────

class TestCleanPlayerData:
    def test_full_pipeline(self):
        df = pl.DataFrame({
            "PLAYER": ["Josh Allen (BUF)", "Lamar Jackson (BAL)"],
            "G": ["17", "16"],
            "YDS": ["4000", "3500"],
        })
        result = clean_player_data(df)

        assert "Team" in result.columns
        assert result["PLAYER"].to_list() == ["Josh Allen", "Lamar Jackson"]
        assert result["Team"].to_list() == ["buffalo_bills", "baltimore_ravens"]
        # Team should come right after PLAYER
        assert result.columns.index("Team") == result.columns.index("PLAYER") + 1

    def test_filters_zero_games(self):
        df = pl.DataFrame({
            "PLAYER": ["A (BUF)", "B (NYG)"],
            "G": ["0", "10"],
        })
        result = clean_player_data(df)
        assert len(result) == 1

    def test_empty_df(self):
        result = clean_player_data(pl.DataFrame())
        assert result.is_empty()


# ── constants sanity ──────────────────────────────────────────────────

class TestConstants:
    def test_team_map_no_empty_values(self):
        for abbr, name in TEAM_MAP.items():
            assert abbr, "Empty abbreviation key"
            assert name, f"Empty team name for {abbr}"

    def test_scoring_rules_all_positions(self):
        for pos in ["QB", "RB", "WR", "TE", "K"]:
            assert pos in SCORING_RULES, f"Missing scoring rules for {pos}"
