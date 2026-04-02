"""
Scoring features module.
Calculates cumulative and per-game fantasy scoring from cleaned data.
"""

import logging
import polars as pl
from pipelines.constants import SCORING_RULES

logger = logging.getLogger(__name__)

def apply_scoring_features(df: pl.DataFrame, position: str) -> pl.DataFrame:
    """
    Apply standard scoring features to a normalized dataframe.
    
    Ensures `fpts` and `fpts_ppr` exist (either fetched from source or calculated via rules),
    and computes per-game derivations if `games_played` is available.
    """
    if df.is_empty():
        return df

    # Calculate point formulas dynamically if raw columns don't exist
    position = position.upper()
    rules = SCORING_RULES.get(position)
    
    # Pre-downcase the rules since DataFrame columns are now strictly lowercase
    lower_rules = {k.lower(): v for k, v in rules.items()} if rules else {}
    
    exprs = []

    # Calculate FPTS (Raw/Standard) if missing
    if "fpts" not in df.columns:
        if lower_rules:
            # Drop PPR specific 'rec' for standard FPTS
            std_rules = {k: v for k, v in lower_rules.items() if k != "rec"}
            applicable = {col: wt for col, wt in std_rules.items() if col in df.columns}
            if applicable:
                terms = [pl.col(c).cast(pl.Float64, strict=False).fill_null(0.0) * w for c, w in applicable.items()]
                pts_expr = terms[0]
                for term in terms[1:]:
                    pts_expr = pts_expr + term
                exprs.append(pts_expr.round(2).alias("fpts"))
            else:
                exprs.append(pl.lit(0.0).alias("fpts"))
        else:
            exprs.append(pl.lit(0.0).alias("fpts"))
    else:
        # Cast existing to Float64 explicitly
        exprs.append(pl.col("fpts").cast(pl.Float64, strict=False).fill_null(0.0).alias("fpts"))

    # Calculate FPTS_PPR if missing
    if "fpts_ppr" not in df.columns:
        if lower_rules:
            applicable = {col: w for col, w in lower_rules.items() if col in df.columns}
            if applicable:
                terms = [pl.col(c).cast(pl.Float64, strict=False).fill_null(0.0) * w for c, w in applicable.items()]
                pts_expr = terms[0]
                for term in terms[1:]:
                    pts_expr = pts_expr + term
                exprs.append(pts_expr.round(2).alias("fpts_ppr"))
            else:
                exprs.append(pl.lit(0.0).alias("fpts_ppr"))
        else:
            exprs.append(pl.lit(0.0).alias("fpts_ppr"))
    else:
        exprs.append(pl.col("fpts_ppr").cast(pl.Float64, strict=False).fill_null(0.0).alias("fpts_ppr"))

    # Append core scoring
    df = df.with_columns(exprs)

    # Calculate Per-Game Metrics if games_played is present
    pg_exprs = []
    if "games_played" in df.columns:
        games_col = pl.col("games_played").cast(pl.Int64, strict=False).fill_null(0)
        # Avoid division by zero
        condition = games_col > 0
        pg_exprs.extend([
            pl.when(condition).then((pl.col("fpts") / games_col).round(2)).otherwise(0.0).alias("fpts_per_game"),
            pl.when(condition).then((pl.col("fpts_ppr") / games_col).round(2)).otherwise(0.0).alias("fpts_ppr_per_game")
        ])
    else:
        # If no games played, populate with 0
        pg_exprs.extend([
            pl.lit(0.0).alias("fpts_per_game"),
            pl.lit(0.0).alias("fpts_ppr_per_game")
        ])
        # Also ensure games_played column exists as part of the schema contract
        pg_exprs.append(pl.lit(None).cast(pl.Int64).alias("games_played"))
        
    df = df.with_columns(pg_exprs)
    
    return df
