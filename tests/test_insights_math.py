"""Unit tests for PEM Insights math (deterministic, no DuckDB)."""

import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from backend.analytics.insights_config import MIN_SAMPLE_SIZE
from backend.analytics.insights_math import (
    enrich_insight_row,
    insight_score,
    passes_min_sample,
    relative_delta_pct,
    sample_strength_label,
    sample_strength_weight,
)


class TestRelativeDeltaPct:
    def test_positive_delta(self):
        assert relative_delta_pct(2.0, 10.0) == 20.0

    def test_zero_baseline_returns_none(self):
        assert relative_delta_pct(2.0, 0.0) is None

    def test_none_inputs(self):
        assert relative_delta_pct(None, 10.0) is None


class TestSampleStrength:
    def test_labels(self):
        assert sample_strength_label(3) == "Low"
        assert sample_strength_label(5) == "Moderate"
        assert sample_strength_label(8) == "Strong"

    def test_weight_caps_at_one(self):
        assert sample_strength_weight(8) == 1.0
        assert sample_strength_weight(16) == 1.0
        assert sample_strength_weight(4) == 0.5


class TestInsightScore:
    def test_combines_relative_and_sample(self):
        # 20% relative * 0.5 weight (4 games) = 10.0
        assert insight_score(20.0, 4) == 10.0

    def test_none_relative_returns_none(self):
        assert insight_score(None, 5) is None


class TestMinSample:
    def test_threshold(self):
        assert passes_min_sample(MIN_SAMPLE_SIZE) is True
        assert passes_min_sample(MIN_SAMPLE_SIZE - 1) is False


class TestEnrichInsightRow:
    def test_derives_all_fields(self):
        row = enrich_insight_row(
            {
                "sample_size": 6,
                "context_average": 15.0,
                "baseline_value": 12.0,
                "absolute_delta": 3.0,
            }
        )
        assert row["relative_delta_pct"] == 25.0
        assert row["sample_strength"] == "Moderate"
        assert row["insight_score"] is not None
