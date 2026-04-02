import logging
import re
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm

# --- CONFIG --------------------------------------------------------

YEARS = range(2020, 2025)
POSITIONS = ["qb"]
BASE_URL = "https://www.fantasypros.com/nfl/stats/{pos}.php?year={year}"

OUTPUT_DIR = Path("backend/static/data/official_rankings/season_totals")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TEAM_ABBR_TO_NAME = {
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
    "FA":"free_agent"
}

POSITION_CONFIG = {
    "qb": {
        "numeric_cols": ["CMP", "YDS", "TD", "Y/A", "INT", "FPTS/G", "FPTS", "Rush_YDS", "Rush_TD", "Rush_ATT", "FL"],
        "stat_renames": {"YDS": "Pass Yds", "TD": "Pass TD", "ATT": "Pass Att"}
    },
    "rb": {
        "numeric_cols": ["ATT", "YDS", "TD", "REC_YDS", "REC_TD", "Y/A", "FPTS/G", "FPTS", "FL", "REC", "TGT", "Y/R"],
        "stat_renames": {"YDS": "Rush Yds", "TD": "Rush TD"}
    },
    "wr": {
        "numeric_cols": ["REC", "YDS", "TD", "Y/R", "LG", "20+", "FL"],
        "stat_renames": {"YDS": "Rec Yds", "TD": "Rec TD"}
    },
    "te": {
        "numeric_cols": ["REC", "YDS", "TD", "Y/R", "LG", "20+", "FPTS/G", "FPTS", "FL"],
        "stat_renames": {"YDS": "Rec Yds", "TD": "Rec TD"}
    },
    "k": {
        "numeric_cols": ["FG", "FGA", "PCT", "1-19", "20-29", "30-39", "40-49", "50+", "FPTS/G", "FPTS"],
        "stat_renames": {}
    },
}

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def _fetch_html(url: str) -> Optional[str]:
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logging.error(f"Failed to fetch {url} – {e}")
        return None


def _extract_table_data(soup: BeautifulSoup, pos: str, year: int) -> Optional[pd.DataFrame]:
    tbl = soup.find("table", class_="table")
    if tbl is None:
        return None

    raw = [th.get_text(strip=True) for th in tbl.thead.find_all("th")]
    seen, headers = {}, []
    for h in raw:
        cnt = seen.get(h, 0)
        headers.append(h if cnt == 0 else f"{h}_{cnt}")
        seen[h] = cnt + 1

    rows = [
        [td.get_text(strip=True) for td in tr.find_all("td")]
        for tr in tbl.tbody.find_all("tr")
    ]
    rows = [r for r in rows if len(r) == len(headers)]
    if not rows:
        return None

    df = pd.DataFrame(rows, columns=headers)

    df["team_abbr"] = df["Player"].str.extract(r"\((\w{2,3})\)", expand=False).str.upper()
    df["team_name"] = df["team_abbr"].map(TEAM_ABBR_TO_NAME).fillna("free_agent")
    df["Player"] = df["Player"].str.replace(r"\(.*\)", "", regex=True).str.strip().str.title()

    if pos == "qb":
        dup_map = {f"{stat}_1": f"Rush_{stat}" for stat in ("ATT", "YDS", "TD") if f"{stat}_1" in df.columns}
        df.rename(columns=dup_map, inplace=True)

    cfg = POSITION_CONFIG[pos]

    for col in cfg["numeric_cols"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .replace({",": "", "—": "", "-": ""}, regex=True)
                .pipe(pd.to_numeric, errors="coerce")
                .fillna(0)
            )


    for old, new in cfg["stat_renames"].items():
        if old in df.columns:
            df.rename(columns={old: new}, inplace=True)

    df["year"] = year

    if "G" in df.columns:
        df = df[df["G"] != "0"]

    print(df.head(10))

    return df


def main():
    for pos in POSITIONS:
        collected = []
        for year in tqdm(YEARS, desc=f"{pos.upper()} Season Stats"):
            url = BASE_URL.format(pos=pos, year=year)
            html = _fetch_html(url)
            if not html:
                continue

            df = _extract_table_data(BeautifulSoup(html, "html.parser"), pos, year)
            if df is not None:
                collected.append(df)

        if not collected:
            logging.warning(f"No data collected for {pos}")
            continue

        final = pd.concat(collected, ignore_index=True)
        final["year"] = final["year"].astype(int)
        final["team_abbr"] = final["team_abbr"].fillna("FA")
        final["played"] = ~final["team_abbr"].str.contains("fa", case=False)
        final.sort_values(["played", "year"], ascending=[False, True], inplace=True)
        final.drop(columns="played", inplace=True)
        final["Rank"] = final.groupby("year").cumcount() + 1

        out = OUTPUT_DIR / f"{pos}_season_totals_2020_2024.csv"
        final.to_csv(out, index=False)
        logging.info(f"[{pos.upper()}] wrote {out}")

if __name__ == "__main__":
    main()
