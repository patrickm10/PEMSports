#!/usr/bin/env python3
"""
FantasyPros + Pro-Football-Reference ETL  (2020-2024)

• Outputs:
    feature_store/{pos}_2020_2024_enriched.parquet
    feature_store/all_positions_2020_2024.parquet

Dependencies:  polars>=0.20, requests, beautifulsoup4, tqdm
"""

from __future__ import annotations
import io, logging, re
from pathlib import Path
from typing import Dict, List, Optional

import requests, polars as pl
from bs4 import BeautifulSoup
from tqdm import tqdm

# ─── Config ──────────────────────────────────────────────────────────────

YEARS      = range(2020, 2025)
WEEKS      = range(1, 18)
POSITIONS  = ["qb", "rb", "wr", "te", "k"]

BASE_FP  = "https://www.fantasypros.com/nfl/stats/{pos}.php?year={year}&week={week}&range=week"
BASE_PFR = "https://www.pro-football-reference.com/years/{year}/games.csv"

OUT_DIR = Path("feature_store")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Team slug map
TEAM_ABBR: Dict[str, str] = {
    "ARI":"arizona_cardinals","ATL":"atlanta_falcons","BAL":"baltimore_ravens",
    "BUF":"buffalo_bills","CAR":"carolina_panthers","CHI":"chicago_bears",
    "CIN":"cincinnati_bengals","CLE":"cleveland_browns","DAL":"dallas_cowboys",
    "DEN":"denver_broncos","DET":"detroit_lions","GB":"green_bay_packers",
    "HOU":"houston_texans","IND":"indianapolis_colts","JAX":"jacksonville_jaguars",
    "JAC":"jacksonville_jaguars","KC":"kansas_city_chiefs","LV":"las_vegas_raiders",
    "LAC":"los_angeles_chargers","LAR":"los_angeles_rams","MIA":"miami_dolphins",
    "MIN":"minnesota_vikings","NE":"new_england_patriots","NO":"new_orleans_saints",
    "NYG":"new_york_giants","NYJ":"new_york_jets","PHI":"philadelphia_eagles",
    "PIT":"pittsburgh_steelers","SEA":"seattle_seahawks","SF":"san_francisco_49ers",
    "TB":"tampa_bay_buccaneers","TEN":"tennessee_titans","WAS":"washington_commanders",
    "FA":"free_agent",
}

# Score formulas – numeric cols stay in result; nothing is dropped
POS_SCORE = {
    "qb": lambda d: (
        d.get("YDS",0)*0.4  + d.get("Rush_YDS",0)*0.1 + d.get("TD",0)*0.3
        + d.get("Y/A",0)*0.2 - d.get("INT",0)*0.1     - d.get("FL",0)*0.1
        + d.get("FPTS/G",0)*0.4 + d.get("FPTS",0)*0.3 + d.get("CMP",0)*0.1
        + d.get("Rush_TD",0)*0.2
    ),
    "rb": lambda d: (
        d.get("YDS",0)*0.45 + d.get("TD",0)*0.4 + d.get("Y/A",0)*0.15
        + d.get("FPTS/G",0)*0.3 + d.get("FPTS",0)*0.2 + d.get("ATT",0)*0.1
        - d.get("FL",0)*0.1   + d.get("REC",0)*0.1  + d.get("REC_YDS",0)*0.1
        + d.get("REC_TD",0)*0.1
    ),
    "wr": lambda d: (
        d.get("REC",0)*0.35 + d.get("YDS",0)*0.25 + d.get("TD",0)*0.5
        + d.get("Y/R",0)*0.15 + d.get("LG",0)*0.1 + d.get("20+",0)*0.1
        - d.get("FL",0)*0.1
    ),
    "te": lambda d: (
        d.get("REC",0)*0.35 + d.get("YDS",0)*0.25 + d.get("TD",0)*0.5
        + d.get("Y/R",0)*0.15 + d.get("LG",0)*0.1 + d.get("20+",0)*0.1
        + d.get("FPTS/G",0)*0.4 + d.get("FPTS",0)*0.3 - d.get("FL",0)*0.1
    ),
    "k": lambda d: (
        d.get("FG",0)*0.4  + d.get("FGA",0)*0.2 + d.get("PCT",0)*0.2
        + d.get("1-19",0)*0.1 + d.get("20-29",0)*0.2 + d.get("30-39",0)*0.1
        + d.get("40-49",0)*0.1 + d.get("50+",0)*0.1 + d.get("FPTS/G",0)*0.4
        + d.get("FPTS",0)*0.3
    ),
}

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# ─── Helpers ────────────────────────────────────────────────────────────

def fetch_html(url: str) -> Optional[str]:
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.text
    except Exception as exc:
        logging.warning(f"Fetch {url} failed – {exc}")
        return None

def parse_fantasypros(html: str, pos: str) -> pl.DataFrame | None:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", class_="table")
    if table is None:
        return None

    headers = [th.get_text(strip=True) for th in table.thead.find_all("th")]
    # unique headers
    seen: Dict[str,int] = {}
    cols = [h if (cnt:=seen.get(h,0))==0 else f"{h}_{cnt}" for h in headers for _ in [seen.__setitem__(h,cnt+1)]]

    rows = [[td.get_text(strip=True) for td in tr.find_all("td")]
            for tr in table.tbody.find_all("tr")]
    rows = [r for r in rows if len(r)==len(cols)]
    df   = pl.DataFrame(rows, columns=cols)

    # team + player parsing
    df = df.with_columns([
        pl.col("Player").str.extract(r"\((\w{2,3})\)$").str.upper().alias("team_abbr")
    ])
    df = df.with_columns([
        pl.col("team_abbr").map_dict(TEAM_ABBR).fill_null("free_agent").alias("team_name"),
        pl.col("Player").str.replace(r"\(.*\)$","").str.strip().str.title().alias("Player")
    ])

    if pos=="qb":
        dup = {f"{s}_1":f"Rush_{s}" for s in ("ATT","YDS","TD") if f"{s}_1" in df.columns}
        df  = df.rename(dup)

    return df

def fetch_week_table(pos:str, year:int, week:int) -> Optional[pl.DataFrame]:
    html = fetch_html(BASE_FP.format(pos=pos, year=year, week=week))
    if not html:
        return None
    tbl = parse_fantasypros(html, pos)
    if tbl is None:                       # week with no data
        return None

    # numeric cast – keep strings if cast fails
    numeric_cols = [c for c in tbl.columns if re.fullmatch(r"[\d\+\-\.%,]+", str(tbl[c][0]))]
    tbl = tbl.with_columns([
        pl.col(c).str.replace(",","").cast(pl.Float64, strict=False).fill_null(0)
        for c in numeric_cols
    ])

    tbl = tbl.with_columns([
        pl.lit(year).cast(pl.Int16).alias("year"),
        pl.lit(week).cast(pl.Int8).alias("week"),
        pl.struct(tbl.columns).apply(lambda s: POS_SCORE[pos](s)).alias("Score"),
    ])
    return tbl

def build_matchups() -> pl.DataFrame:
    frames: List[pl.DataFrame] = []
    for yr in YEARS:
        raw = requests.get(BASE_PFR.format(year=yr), timeout=10).content
        df  = pl.read_csv(io.BytesIO(raw), truncate_ragged_lines=True)

        df = (
            df.filter(pl.col("Week").cast(str).str.contains(r"^\d+$"))
              .with_columns([
                  pl.col("Week").cast(pl.Int8).alias("week"),
                  pl.lit(yr).cast(pl.Int16).alias("year"),
                  pl.col("Winner/tie").str.replace(" ","_").str.to_lowercase().alias("winner"),
                  pl.col("Loser/tie" ).str.replace(" ","_").str.to_lowercase().alias("loser"),
              ])
        )

        long = (
            df.melt(
                id_vars=df.columns,          # keep ALL original matchup columns
                value_vars=["winner","loser"],
                variable_name="result_col",
                value_name="team_name",
            )
            .with_columns((pl.col("result_col")=="winner").cast(pl.Int8).alias("is_winner"))
            .drop("result_col")
        )
        frames.append(long)
    return pl.concat(frames, rechunk=True)

# ─── Pipeline ───────────────────────────────────────────────────────────

def main() -> None:
    logging.info("Building matchup table …")
    matchups = build_matchups()
    matchups.write_parquet(OUT_DIR / "matchups_2020_2024.parquet", compression="zstd")

    consolidated: List[pl.DataFrame] = []

    for pos in POSITIONS:
        wk_frames: List[pl.DataFrame] = []
        for yr in tqdm(YEARS, desc=f"{pos.upper()} seasons"):
            for wk in WEEKS:
                tbl = fetch_week_table(pos, yr, wk)
                if tbl is not None:
                    wk_frames.append(tbl)

        if not wk_frames:
            logging.warning(f"No data scraped for {pos}")
            continue

        stats = (
            pl.concat(wk_frames, rechunk=True)
              .with_columns(pl.col("team_name").str.replace(" ","_").str.to_lowercase())
        )

        joined = stats.join(matchups, on=["year","week","team_name"], how="left")
        out_pq = OUT_DIR / f"{pos}_2020_2024_enriched.parquet"
        joined.write_parquet(out_pq, compression="zstd")
        logging.info(f"{pos.upper()} → {out_pq}  rows={joined.height:,}")

        consolidated.append(joined)

    if consolidated:
        pl.concat(consolidated, rechunk=True).write_parquet(
            OUT_DIR / "all_positions_2020_2024.parquet",
            compression="zstd",
        )
        logging.info("Consolidated Parquet written")


if __name__ == "__main__":
    main()
