import polars as pl
from pathlib import Path
import os
import sys

# Add 'src' to path for imports to use normalization logic if needed
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

try:
    from pipelines.enrichment import get_team_slug, TEAM_MAP
except ImportError:
    # Fallback if imports fail
    TEAM_MAP = {}
    def get_team_slug(x): return str(x).lower()

def audit():
    enriched_cols = ['opponent', 'stadium_name', 'city', 'state', 'temp', 'humidity', 'wind', 'game_result', 'season']
    positions = ['QB', 'RB', 'WR', 'TE', 'K', 'DST']
    results = []

    results.append("### Schema Audit")
    for p in positions:
        w_path = Path(f"data/rankings/{p}_weekly.parquet")
        s_path = Path(f"data/rankings/{p}_seasonal.parquet")
        
        if w_path.exists():
            w_cols = pl.read_parquet(w_path).columns
            found = [c for c in enriched_cols if c in w_cols]
            results.append(f"{p}_weekly: {found}")
        
        if s_path.exists():
            s_cols = pl.read_parquet(s_path).columns
            found = [c for c in enriched_cols if c in s_cols]
            results.append(f"{p}_seasonal (Should be empty): {found}")

    results.append("\n### Coverage Audit (Weekly)")
    coverage_cols = ['opponent', 'stadium_name', 'city', 'state', 'temp', 'humidity', 'wind', 'game_result']
    for p in positions:
        path = Path(f"data/rankings/{p}_weekly.parquet")
        if not path.exists():
            continue
            
        df = pl.read_parquet(path)
        if 'year' not in df.columns:
            results.append(f"{p}: No 'year' column found.")
            continue
            
        results.append(f"\n#### {p} Weekly Details")
        # Null counts by year
        agg_exprs = [pl.col(c).null_count().alias(f"{c}_nulls") for c in coverage_cols if c in df.columns]
        agg_exprs.append(pl.len().alias("total"))
        
        stats = df.group_by('year').agg(agg_exprs).sort('year')
        results.append(str(stats))

    results.append("\n### Join Diagnostic (Sample Misses)")
    matchups_path = Path("data/nfl_metadata/nfl_matchups_enriched.csv")
    if matchups_path.exists():
        matchups = pl.read_csv(matchups_path, infer_schema_length=0)
        # Check team names in matchups vs expected slugs
        m_teams = set(matchups["Winner"].unique()) | set(matchups["Loser"].unique())
        results.append(f"Unique teams in matchups file: {len(m_teams)}")
        # sample a few
        results.append(f"Sample matchup teams: {list(m_teams)[:5]}")

    # Use utf-8 encoding to avoid UnicodeEncodeError on Windows
    with open("audit_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(results))

if __name__ == "__main__":
    audit()
