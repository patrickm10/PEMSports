"""
Pure, deterministic PEM Insights formulas.

All relative performance and ranking math lives here so tests can validate
behavior without DuckDB. SQL aggregation returns raw aggregates; this module
derives insight_score and sample_strength labels.
"""

from __future__ import annotations

from backend.analytics.insights_config import (
    FULL_WEIGHT_SAMPLE,
    MIN_SAMPLE_SIZE,
    MODERATE_SAMPLE_SIZE,
    STRONG_SAMPLE_SIZE,
)


def passes_min_sample(sample_size: int) -> bool:
    """Return True when a player has enough context games for the leaderboard."""
    return sample_size >= MIN_SAMPLE_SIZE


def relative_delta_pct(
    absolute_delta: float | None, baseline_value: float | None
) -> float | None:
    """
    Percent change vs season-adjusted leave-one-out baseline.

    relative_delta_pct = 100 * absolute_delta / baseline_value
    """
    if absolute_delta is None or baseline_value is None:
        return None
    if baseline_value == 0:
        return None
    return round(100.0 * absolute_delta / baseline_value, 2)


def sample_strength_weight(sample_size: int) -> float:
    """Linear sample weight capped at 1.0 — not a statistical confidence interval."""
    if sample_size <= 0:
        return 0.0
    return min(1.0, sample_size / FULL_WEIGHT_SAMPLE)


def sample_strength_label(sample_size: int) -> str:
    """Interpretable sample count tier (Low / Moderate / Strong)."""
    if sample_size >= STRONG_SAMPLE_SIZE:
        return "Strong"
    if sample_size >= MODERATE_SAMPLE_SIZE:
        return "Moderate"
    return "Low"


def insight_score(relative_delta_pct_value: float | None, sample_size: int) -> float | None:
    """
    v1 ranking score: relative performance magnitude scaled by sample strength.

    insight_score = relative_delta_pct * sample_strength_weight(sample_size)
    """
    if relative_delta_pct_value is None:
        return None
    weight = sample_strength_weight(sample_size)
    return round(relative_delta_pct_value * weight, 4)


def enrich_insight_row(row: dict) -> dict:
    """Apply derived fields to a SQL aggregate row (mutates and returns row)."""
    sample_size = int(row.get("sample_size") or 0)
    absolute_delta = row.get("absolute_delta")
    baseline_value = row.get("baseline_value")

    if absolute_delta is not None and baseline_value is None:
        context_avg = row.get("context_average")
        if context_avg is not None:
            baseline_value = round(float(context_avg) - float(absolute_delta), 2)
            row["baseline_value"] = baseline_value

    rel = relative_delta_pct(
        float(absolute_delta) if absolute_delta is not None else None,
        float(baseline_value) if baseline_value is not None else None,
    )
    row["relative_delta_pct"] = rel
    row["sample_strength"] = sample_strength_label(sample_size)
    row["insight_score"] = insight_score(rel, sample_size)
    return row
