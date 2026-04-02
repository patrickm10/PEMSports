import os
import requests
from bs4 import BeautifulSoup
import polars as pl
import re

def _clean_name(name):
    if not isinstance(name, str):
        return name
    name = re.sub(r"\s*\(.*?\)", "", name)
    return name.strip()

def _make_unique_headers(headers: list[str]) -> list[str]:
    seen = {}
    unique = []
    for h in headers:
        if h not in seen:
            seen[h] = 0
            unique.append(h)
        else:
            seen[h] += 1
            unique.append(f"{h}.{seen[h]}")
    return unique

def _rename_duplicate_stats(df: pl.DataFrame, stat_renames: dict) -> pl.DataFrame:
    for base_col, new_col in stat_renames.items():
        matches = [col for col in df.columns if col == base_col or col.startswith(f"{base_col}.")]
        for i, dup_col in enumerate(matches[1:], start=1):
            suffix = f".{i}" if i > 1 else ""
            df = df.rename({dup_col: f"{new_col}{suffix}"})
    return df

POSITION_CONFIG = {
    "qb": {
        "numeric_cols": ["CMP", "YDS", "TD", "Y/A", "INT", "FPTS/G", "FPTS", "R_YDS", "R_TD", "R_ATT"],
        "score_func": lambda df: (
            df["YDS"] * 0.4 + df["R_YDS"] * 0.1 + df["TD"] * 0.6 +
            df["Y/A"] * 0.2 - df["INT"] * 0.1 + df["FPTS/G"] * 0.4 +
            df["FPTS"] * 0.3 + df["CMP"] * 0.1 + df["R_TD"] * 0.2
        ),
        "top_n": 32,
        "handle_duplicates": True,
        "stat_renames": {"YDS": "R_YDS", "TD": "R_TD", "ATT": "R_ATT"}
    },
    "rb": {
        "numeric_cols": ["ATT", "YDS", "TD", "REC_YDS", "REC_TD", "Y/A", "FPTS/G", "FPTS", "FL", "REC"],
        "score_func": lambda df: (
            df["YDS"] * 0.45 + df["TD"] * 0.4 + df["Y/A"] * 0.15 +
            df["FPTS/G"] * 0.3 + df["FPTS"] * 0.2 + df["ATT"] * 0.1 -
            df["FL"] * 0.1 + df["REC"] * 0.1 +
            df["REC_YDS"] * 0.1 +
            df["REC_TD"] * 0.1
        ),
        "top_n": 32,
        "handle_duplicates": True,
        "stat_renames": {"YDS": "REC_YDS", "TD": "REC_TD"}
    },
    "wr": {
        "numeric_cols": ["REC", "YDS", "TD", "Y/R", "LG", "20+"],
        "score_func": lambda df: (
            df["REC"] * 0.35 + df["YDS"] * 0.25 + df["TD"] * 0.5 +
            df["Y/R"] * 0.15 + df["LG"] * 0.1 + df["20+"] * 0.1
        ),
        "top_n": 50,
        "handle_duplicates": False
    },
    "te": {
        "numeric_cols": ["REC", "YDS", "TD", "Y/R", "LG", "20+", "FPTS/G", "FPTS"],
        "score_func": lambda df: (
            df["REC"] * 0.35 + df["YDS"] * 0.25 + df["TD"] * 0.5 +
            df["Y/R"] * 0.15 + df["LG"] * 0.1 + df["20+"] * 0.1 +
            df["FPTS/G"] * 0.4 + df["FPTS"] * 0.3
        ),
        "top_n": 50,
        "handle_duplicates": False
    },
    "k": {
        "numeric_cols": ["FG", "FGA", "PCT", "1-19", "20-29", "30-39", "40-49", "50+", "FPTS/G", "FPTS"],
        "score_func": lambda df: (
            df["FG"] * 0.4 + df["FGA"] * 0.2 + df["PCT"] * 0.2 + df["1-19"] * 0.1 +
            df["20-29"] * 0.2 + df["30-39"] * 0.1 + df["40-49"] * 0.1 + df["50+"] * 0.1 +
            df["FPTS/G"] * 0.4 + df["FPTS"] * 0.3
        ),
        "top_n": 32,
        "handle_duplicates": False
    },
}

def find_best_players(position, year=None, week=None):
    if position not in POSITION_CONFIG:
        print(f"Position '{position}' not supported.")
        return None

    c = POSITION_CONFIG[position]
    folder = "career" if week is None else "weekly"
    os.makedirs(f"data/official_rankings/{folder}", exist_ok=True)

    base_url = f"https://www.fantasypros.com/nfl/stats/{position}.php?scoring=PPR"
    if year:
        base_url += f"&year={year}"
    else:
        base_url += f"&range=full"

    try:
        response = requests.get(base_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        table = soup.find("table", {"class": "table"})
        if not table:
            print(f"No table found for {position} year {year} week {week}.")
            return None

        headers = [th.text.strip() for th in table.find("thead").find_all("th")]
        rows = [[td.text.strip() for td in tr.find_all("td")] for tr in table.find("tbody").find_all("tr")]

        if not rows:
            print(f"No player data found for {position} year {year} week {week}.")
            return None

        unique_headers = _make_unique_headers(headers)
        df = pl.DataFrame(rows, orient="row", schema=unique_headers)

        if "Player" in df.columns:
            df = df.with_columns(
                pl.col("Player").map_elements(_clean_name, return_dtype=pl.String).alias("Player")
            )

        if c.get("handle_duplicates") and "stat_renames" in c:
            df = _rename_duplicate_stats(df, c["stat_renames"])

        # Cast numeric columns properly
        for col in c["numeric_cols"]:
            if col in df.columns:
                df = df.with_columns(pl.col(col).str.replace_all(",", "").cast(pl.Float64))

        # For RB scoring, ensure REC_YDS and REC_TD exist, else add zero columns
        if position == "rb":
            length = df.height
            if "REC_YDS" not in df.columns:
                df = df.with_columns(pl.lit(0.0).repeat(length).alias("REC_YDS"))
            if "REC_TD" not in df.columns:
                df = df.with_columns(pl.lit(0.0).repeat(length).alias("REC_TD"))

        # Calculate score (now safe to use all columns)
        df = df.with_columns([
            pl.Series("Score", c["score_func"](df))
        ])

        df = df.with_columns([
            pl.col("Score").rank("min").cast(pl.Int64).alias("Rank")
        ])

        df = df.sort("Score", descending=True).head(c["top_n"])

        suffix = f"{position}_{year}_week{week}.csv" if week else f"{position}_{year}.csv"
        filename = f"data/official_rankings/{folder}/official_{suffix}"
        df.write_csv(filename)
        print(filename)
        print(f"Saved {position.upper()} rankings to {filename}")

        return df

    except Exception as e:
        print(f"Error processing {position} year {year} week {week}: {e}")
        return None

if __name__ == "__main__":
    positions = ["qb", "rb", "wr", "te", "k"]
    for year in range(2020, 2025):
        for pos in positions:
            best_players = find_best_players(pos, year)
            print(f"Processed {pos.upper()} for year {year}")
            print(best_players.head(5) if best_players is not None else "No data found.")
