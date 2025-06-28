import logging
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import polars as pl
import re
from typing import List, Optional, Dict, Callable
from tqdm import tqdm

# === CONFIGURATION ===
DEFAULT_YEAR = 2020
DEFAULT_WEEK = 1

STADIUM_PATH = Path("data/nfl_metadata/nfl_stadiums.csv")
ROSTER_PATH = Path("data/nfl_metadata/nfl_roster.csv")

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# === UTILITY FUNCTIONS ===
def _handle_duplicate_headers(headers: List[str]) -> List[str]:
    seen = {}
    result = []
    for h in headers:
        seen[h] = seen.get(h, 0) + 1
        result.append(h if seen[h] == 1 else f"{h}.{seen[h]}")
    return result

def _convert_numeric(df: pl.DataFrame, cols: List[str]) -> pl.DataFrame:
    for col in cols:
        if col in df.columns:
            df = df.with_columns(
                pl.col(col)
                .str.replace_all(",", "")
                .str.replace_all("--", "")
                .cast(pl.Float64, strict=False)
                .fill_null(0)
                .alias(col)
            )
    return df

def _rename_duplicate_stats(df: pl.DataFrame, stat_map: Dict[str, str]) -> pl.DataFrame:
    for base_col, new_col in stat_map.items():
        matches = [col for col in df.columns if col == base_col or col.startswith(f"{base_col}.")]
        if len(matches) > 1 and new_col not in df.columns:
            df = df.rename({matches[1]: new_col})
    return df

def _clean_name(name: str) -> str:
    if not isinstance(name, str):
        return name
    # Remove parenthetical data and trim
    name = re.sub(r"\s*\(.*?\)", "", name).strip()
    # Convert to title case (e.g., "baker mayfield" → "Baker Mayfield")
    return name.title()

def _load_metadata() -> Optional[pl.DataFrame]:
    if not STADIUM_PATH.exists() or not ROSTER_PATH.exists():
        logging.warning("Missing stadium or roster CSV. Skipping enrichment.")
        return None

    roster = pl.read_csv(ROSTER_PATH).with_columns([
        pl.col("Player").map_elements(lambda x: x.strip().title() if isinstance(x, str) else x, return_dtype=pl.Utf8),
        pl.col("home_team_name").map_elements(lambda x: x.strip().lower() if isinstance(x, str) else x, return_dtype=pl.Utf8)
    ])

    stadiums = pl.read_csv(STADIUM_PATH).with_columns([
        pl.col("home_team_name").map_elements(lambda x: x.strip().lower() if isinstance(x, str) else x, return_dtype=pl.Utf8)
    ])

    return roster.join(stadiums, on="home_team_name", how="left")

# === POSITION CONFIG ===
POSITION_CONFIG: Dict[str, Dict] = {
    "qb": {
        "numeric_cols": ["CMP", "YDS", "TD", "Y/A", "INT", "FPTS/G", "FPTS", "R_YDS", "R_TD"],
        "score_func": lambda: (
            pl.col("YDS") * 0.4 + pl.col("R_YDS") * 0.1 + pl.col("TD") * 0.3 +
            pl.col("Y/A") * 0.2 - pl.col("INT") * 0.1 + pl.col("FPTS/G") * 0.4 +
            pl.col("FPTS") * 0.3 + pl.col("CMP") * 0.1 + pl.col("R_TD") * 0.2
        ),
        "top_n": 32,
        "handle_duplicates": True,
        "stat_renames": {"YDS": "R_YDS", "TD": "R_TD"}
    },
    "rb": {
        "numeric_cols": ["ATT", "YDS", "TD", "R_YDS", "R_TD", "Y/A", "FPTS/G", "FPTS", "FL", "REC"],
        "score_func": lambda: (
            pl.col("R_YDS") * 0.45 + pl.col("R_TD") * 0.4 + pl.col("Y/A") * 0.15 +
            pl.col("FPTS/G") * 0.3 + pl.col("FPTS") * 0.2 + pl.col("ATT") * 0.1 -
            pl.col("FL") * 0.1 + pl.col("REC") * 0.1 + pl.col("YDS") * 0.1 + pl.col("TD") * 0.1
        ),
        "top_n": 32,
        "handle_duplicates": True,
        "stat_renames": {"YDS": "R_YDS", "TD": "R_TD"}
    },
    "wr": {
        "numeric_cols": ["REC", "YDS", "TD", "R_YDS", "R_TD", "FPTS/G", "FPTS", "ATT"],
        "score_func": lambda: (
            pl.col("REC") * 0.35 + pl.col("YDS") * 0.25 + pl.col("TD") * 0.4 +
            pl.col("R_YDS").fill_null(0) * 0.1 +
            pl.col("R_TD").fill_null(0) * 0.1 +
            pl.col("ATT").fill_null(0) * 0.05 +
            pl.col("FPTS/G") * 0.4 + pl.col("FPTS") * 0.3
        ),
        "top_n": 50,
        "handle_duplicates": True,
        "stat_renames": {"YDS": "R_YDS", "TD": "R_TD"}
    },
    "te": {
        "numeric_cols": ["REC", "YDS", "TD", "Y/R", "LG", "20+", "FPTS/G", "FPTS"],
        "score_func": lambda: (
            pl.col("REC") * 0.35 + pl.col("YDS") * 0.25 + pl.col("TD") * 0.5 +
            pl.col("Y/R") * 0.15 + pl.col("LG") * 0.1 + pl.col("20+") * 0.1 +
            pl.col("FPTS/G") * 0.4 + pl.col("FPTS") * 0.3
        ),
        "top_n": 50,
        "handle_duplicates": False
    },
    "k": {
        "numeric_cols": ["FG", "FGA", "PCT", "1-19", "20-29", "30-39", "40-49", "50+", "FPTS/G", "FPTS"],
        "score_func": lambda: (
            pl.col("FG") * 0.4 + pl.col("FGA") * 0.2 + pl.col("PCT") * 0.2 + pl.col("1-19") * 0.1 +
            pl.col("20-29") * 0.2 + pl.col("30-39") * 0.1 + pl.col("40-49") * 0.1 + pl.col("50+") * 0.1 +
            pl.col("FPTS/G") * 0.4 + pl.col("FPTS") * 0.3
        ),
        "top_n": 32,
        "handle_duplicates": False
    },
}

# === SCRAPING FUNCTION ===
def find_best_players(position: str, year: int, weeks: Optional[List[int]]) -> Optional[pl.DataFrame]:
    config = POSITION_CONFIG.get(position)
    if not config:
        logging.warning(f"Unsupported position: {position}")
        return None

    metadata = _load_metadata()
    folder = "career" if weeks is None else "weekly"
    data_dir = Path("data/official_rankings") / folder
    data_dir.mkdir(parents=True, exist_ok=True)
    weeks = weeks or [None]
    all_dfs = []

    for week in tqdm(weeks, desc=f"{position.upper()} {year}"):
        base_url = f"https://www.fantasypros.com/nfl/stats/{position}.php?scoring=PPR"
        base_url += f"&range={'week&week=' + str(week) if week else 'full'}"

        try:
            res = requests.get(base_url, timeout=10)
            res.raise_for_status()
            soup = BeautifulSoup(res.content, "html.parser")
            table = soup.find("table", class_="table")
            if not table:
                continue

            headers = [th.text.strip() for th in table.find("thead").find_all("th")]
            if config.get("handle_duplicates"):
                headers = _handle_duplicate_headers(headers)

            rows = [
                [td.text.strip() for td in tr.find_all("td")]
                for tr in table.find("tbody").find_all("tr")
            ]
            if not rows:
                continue

            df = pl.DataFrame({h: [row[i] for row in rows] for i, h in enumerate(headers)})
            if "Player" in df.columns:
                df = df.with_columns([
                    pl.col("Player").map_elements(_clean_name, return_dtype=pl.Utf8)
                ])

            df = _rename_duplicate_stats(df, config.get("stat_renames", {}))
            df = _convert_numeric(df, config["numeric_cols"])
            df = df.with_columns([
                config["score_func"]().round(2).alias("Score"),
                pl.lit(week or DEFAULT_WEEK).alias("week"),
                pl.lit(year or DEFAULT_YEAR).alias("year")
            ])
            df = df.sort("Score", descending=True).head(config["top_n"])

            if metadata is not None:
                df = df.join(metadata, on="Player", how="left")


            all_dfs.append(df)

        except Exception as e:
            logging.error(f"Error for {position} year {year} week {week}: {e}")

    if all_dfs:
        final = pl.concat(all_dfs, how="vertical")
        suffix = f"{position}_{year}_weeks.csv" if weeks != [None] else f"{position}_{year}.csv"
        final.write_csv(data_dir / f"official_{suffix}")
        return final
    return None

# === MAIN EXECUTION ===
def main():
    positions = ["rb", "wr", "te", "k"]
    start_year, end_year = 2020, 2025
    output_dir = Path("data/official_rankings/historical")
    output_dir.mkdir(parents=True, exist_ok=True)

    for pos in positions:
        results = []
        for year in tqdm(range(start_year, end_year), desc=f"Position: {pos.upper()}"):
            df = find_best_players(pos, year, list(range(1, 18)))
            if df is not None:
                results.append(df)

        if results:
            full_df = pl.concat(results, how="vertical")
            filename = output_dir / f"{pos}_{start_year}_{end_year}_historical.csv"
            full_df.write_csv(filename)
            logging.info(f"[{pos.upper()}] Historical data saved to: {filename.resolve()}")

            # Identify and report players missing stadium metadata
            if "stadium_name" in full_df.columns:
                missing_meta = full_df.filter(pl.col("stadium_name").is_null())
                if missing_meta.height > 0:
                    missing_players = missing_meta.select("Player").unique().sort("Player")
                    logging.warning(f"[{pos.upper()}] {len(missing_players)} players missing stadium metadata:\n{missing_players}")


if __name__ == "__main__":
    main()
