"""
Pull historical kickoff weather from Open-Meteo and write
data/nfl_metadata/nfl_matchups_with_weather.csv.

PFR game times are Eastern. Archive timestamps use America/New_York so the
hourly join matches kickoff, not stadium-local clock labels.

Does not register Insights weather. Keeps Open-Meteo metric defaults (temp_C).
"""

from __future__ import annotations

import logging
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import polars as pl

_SRC = Path(__file__).resolve().parent.parent
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import requests

from pipelines.http_client import fetch_json

logger = logging.getLogger(__name__)

BASE_DATA_DIR = Path("data/nfl_metadata")
MATCHUPS_PATH = BASE_DATA_DIR / "nfl_matchups_enriched.csv"
OUTPUT_PATH = BASE_DATA_DIR / "nfl_matchups_with_weather.csv"
COORDS_PATH = BASE_DATA_DIR / "stadium_coords.csv"
HOURLY_CACHE_DIR = Path("data_local/weather_hourly")

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
ARCHIVE_HOURLY = (
    "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,surface_pressure"
)
ARCHIVE_TZ = "America/New_York"
REQUEST_PAUSE_S = 0.8
ARCHIVE_429_SLEEP_S = 15.0
ARCHIVE_MAX_TRIES = 6

# Approximate stadium coordinates if geocoding misses (city/state collisions).
_STADIUM_COORDS_FALLBACK: dict[str, tuple[float, float]] = {
    "State Farm Stadium": (33.5276, -112.2626),
    "Mercedes-Benz Stadium": (33.7553, -84.4006),
    "M&T Bank Stadium": (39.2780, -76.6227),
    "Highmark Stadium": (42.7738, -78.7870),
    "Bank of America Stadium": (35.2258, -80.8528),
    "Soldier Field": (41.8623, -87.6167),
    "Paycor Stadium": (39.0954, -84.5160),
    "FirstEnergy Stadium": (41.5061, -81.6995),
    "AT&T Stadium": (32.7473, -97.0945),
    "Empower Field at Mile High": (39.7439, -105.0201),
    "Ford Field": (42.3400, -83.0456),
    "Lambeau Field": (44.5013, -88.0622),
    "NRG Stadium": (29.6847, -95.4107),
    "Lucas Oil Stadium": (39.7601, -86.1639),
    "TIAA Bank Field": (30.3239, -81.6373),
    "GEHA Field at Arrowhead Stadium": (39.0489, -94.4839),
    "Allegiant Stadium": (36.0909, -115.1833),
    "SoFi Stadium": (33.9535, -118.3390),
    "Hard Rock Stadium": (25.9580, -80.2389),
    "U.S. Bank Stadium": (44.9738, -93.2575),
    "Gillette Stadium": (42.0909, -71.2643),
    "Caesars Superdome": (29.9509, -90.0814),
    "MetLife Stadium": (40.8128, -74.0742),
    "Lincoln Financial Field": (39.9008, -75.1675),
    "Acrisure Stadium": (40.4468, -80.0158),
    "Levi's Stadium": (37.4032, -121.9698),
    "Lumen Field": (47.5952, -122.3316),
    "Raymond James Stadium": (27.9759, -82.5033),
    "Nissan Stadium": (36.1665, -86.7713),
    "FedExField": (38.9076, -76.8645),
}


def iso_date(value: Any) -> str | None:
    """Return YYYY-MM-DD from a matchup Date cell."""
    if value is None:
        return None
    text = str(value).strip()
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    return None


def kickoff_et_hour(date_iso: str, time_raw: Any) -> str | None:
    """Nearest America/New_York hour for a PFR Date + Time (e.g. 8:20PM)."""
    if not date_iso:
        return None
    raw = str(time_raw or "").strip().replace(" ", "")
    if not raw:
        raw = "1:00PM"
    match = re.match(r"^(\d{1,2}):(\d{2})(AM|PM)$", raw, re.IGNORECASE)
    if not match:
        logger.warning("Unparsed kickoff time %r on %s; default 1:00PM ET", time_raw, date_iso)
        raw = "1:00PM"
        match = re.match(r"^(\d{1,2}):(\d{2})(AM|PM)$", raw, re.IGNORECASE)
        if not match:
            return None
    try:
        dt = datetime.strptime(f"{date_iso} {raw.upper()}", "%Y-%m-%d %I:%M%p")
    except ValueError:
        return None
    if dt.minute >= 30:
        dt = dt.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        dt = dt.replace(minute=0, second=0, microsecond=0)
    return dt.strftime("%Y-%m-%dT%H:00")


def _load_coord_cache() -> dict[str, tuple[float, float]]:
    if not COORDS_PATH.exists():
        return {}
    df = pl.read_csv(COORDS_PATH)
    if not {"stadium_name", "latitude", "longitude"}.issubset(df.columns):
        return {}
    out: dict[str, tuple[float, float]] = {}
    for row in df.iter_rows(named=True):
        name = row.get("stadium_name")
        try:
            lat = float(row["latitude"])
            lon = float(row["longitude"])
        except (TypeError, ValueError):
            continue
        if name:
            out[str(name)] = (lat, lon)
    return out


def _save_coord_cache(coords: dict[str, tuple[float, float]], venues: pl.DataFrame) -> None:
    rows = []
    for row in venues.iter_rows(named=True):
        name = row["stadium_name"]
        pair = coords.get(name)
        if not pair:
            continue
        rows.append(
            {
                "stadium_name": name,
                "city": row.get("city"),
                "state": row.get("state"),
                "latitude": pair[0],
                "longitude": pair[1],
            }
        )
    if rows:
        BASE_DATA_DIR.mkdir(parents=True, exist_ok=True)
        pl.DataFrame(rows).write_csv(COORDS_PATH)


def geocode_city(city: str, state: str) -> tuple[float, float] | None:
    name = f"{city}, {state}".strip().strip(",")
    payload = fetch_json(
        GEOCODE_URL,
        timeout=20,
        params={"name": name, "count": 1, "language": "en", "countryCode": "US"},
    )
    if not payload or payload.get("error"):
        payload = fetch_json(
            GEOCODE_URL,
            timeout=20,
            params={"name": city, "count": 1, "language": "en", "countryCode": "US"},
        )
    results = (payload or {}).get("results") or []
    if not results:
        return None
    lat = results[0].get("latitude")
    lon = results[0].get("longitude")
    if lat is None or lon is None:
        return None
    return float(lat), float(lon)


def resolve_coords(venues: pl.DataFrame) -> dict[str, tuple[float, float]]:
    cached = _load_coord_cache()
    resolved: dict[str, tuple[float, float]] = {}
    missing = 0
    for row in venues.iter_rows(named=True):
        name = str(row["stadium_name"])
        if name in cached:
            resolved[name] = cached[name]
            continue
        pair = geocode_city(str(row.get("city") or ""), str(row.get("state") or ""))
        time.sleep(REQUEST_PAUSE_S)
        if pair is None:
            pair = _STADIUM_COORDS_FALLBACK.get(name)
            if pair:
                logger.info("Geocode miss for %s; using stadium fallback coords", name)
        if pair is None:
            logger.warning("No coordinates for stadium %s (%s, %s)", name, row.get("city"), row.get("state"))
            missing += 1
            continue
        resolved[name] = pair
    _save_coord_cache(resolved, venues)
    logger.info("Stadiums with coords: %d (missing %d)", len(resolved), missing)
    return resolved


def _get_archive_json(params: dict[str, Any]) -> dict[str, Any] | None:
    """Archive GET with long 429 backoff (scraper client retries too fast)."""
    last_reason = None
    for attempt in range(1, ARCHIVE_MAX_TRIES + 1):
        try:
            response = requests.get(ARCHIVE_URL, params=params, timeout=60)
            if response.status_code == 429:
                wait = ARCHIVE_429_SLEEP_S * attempt
                logger.warning("Archive 429 (try %d/%d); sleep %.0fs", attempt, ARCHIVE_MAX_TRIES, wait)
                time.sleep(wait)
                continue
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            last_reason = str(exc)
            wait = ARCHIVE_429_SLEEP_S * attempt
            logger.warning("Archive error %s; sleep %.0fs", last_reason, wait)
            time.sleep(wait)
            continue
        if payload.get("error"):
            last_reason = payload.get("reason")
            logger.error("Archive API error: %s", last_reason)
            return None
        return payload
    logger.error("Archive miss after retries: %s", last_reason)
    return None


def fetch_archive_hourly(
    lat: float, lon: float, start_date: str, end_date: str
) -> list[dict[str, Any]]:
    payload = _get_archive_json(
        {
            "latitude": lat,
            "longitude": lon,
            "start_date": start_date,
            "end_date": end_date,
            "hourly": ARCHIVE_HOURLY,
            "timezone": ARCHIVE_TZ,
        }
    )
    if not payload:
        return []
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    temps = hourly.get("temperature_2m") or []
    hums = hourly.get("relative_humidity_2m") or []
    precips = hourly.get("precipitation") or []
    winds = hourly.get("wind_speed_10m") or []
    pressures = hourly.get("surface_pressure") or []
    rows = []
    for i, ts in enumerate(times):
        rows.append(
            {
                "hourly_time": ts,
                "temp_C": temps[i] if i < len(temps) else None,
                "rel_humidity": hums[i] if i < len(hums) else None,
                "precip_mm": precips[i] if i < len(precips) else None,
                "wind_kph": winds[i] if i < len(winds) else None,
                "pressure_hpa": pressures[i] if i < len(pressures) else None,
            }
        )
    return rows


def _season_window(year: int) -> tuple[str, str]:
    return f"{year}-09-01", f"{year + 1}-02-20"


def _hourly_cache_path(stadium_name: str) -> Path:
    slug = re.sub(r"[^a-z0-9]+", "_", stadium_name.lower()).strip("_")
    return HOURLY_CACHE_DIR / f"{slug}.parquet"


def _load_hourly_cache(stadium_name: str) -> pl.DataFrame | None:
    path = _hourly_cache_path(stadium_name)
    if not path.exists():
        return None
    df = pl.read_parquet(path)
    if df.is_empty() or "hourly_time" not in df.columns:
        return None
    return df


def _save_hourly_cache(stadium_name: str, df: pl.DataFrame) -> None:
    HOURLY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    df.write_parquet(_hourly_cache_path(stadium_name))


def _hourly_date_bounds(df: pl.DataFrame) -> tuple[str | None, str | None]:
    if df.is_empty():
        return None, None
    times = df.get_column("hourly_time").cast(pl.String)
    return times.min()[:10], times.max()[:10]


def _cache_covers_range(cached: pl.DataFrame, start: str, end: str) -> bool:
    min_d, max_d = _hourly_date_bounds(cached)
    if min_d is None or max_d is None:
        return False
    return min_d <= start and max_d >= end


def _day_before(iso: str) -> str:
    return (datetime.strptime(iso, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")


def _day_after(iso: str) -> str:
    return (datetime.strptime(iso, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")


def _ensure_stadium_name(df: pl.DataFrame, name: str) -> pl.DataFrame:
    if "stadium_name" in df.columns:
        return df
    return df.with_columns(pl.lit(name).alias("stadium_name"))


def _extend_hourly_cache(
    name: str,
    cached: pl.DataFrame,
    start: str,
    end: str,
    lat: float,
    lon: float,
) -> pl.DataFrame:
    """Merge cached hourly rows with any missing archive slices for [start, end]."""
    cached = _ensure_stadium_name(cached, name)
    if _cache_covers_range(cached, start, end):
        return cached

    min_d, max_d = _hourly_date_bounds(cached)
    frames: list[pl.DataFrame] = [cached.drop("stadium_name") if "stadium_name" in cached.columns else cached]

    if min_d and min_d > start:
        gap_rows = fetch_archive_hourly(lat, lon, start, _day_before(min_d))
        time.sleep(REQUEST_PAUSE_S)
        if gap_rows:
            frames.insert(0, pl.DataFrame(gap_rows))

    if max_d and max_d < end:
        gap_rows = fetch_archive_hourly(lat, lon, _day_after(max_d), end)
        time.sleep(REQUEST_PAUSE_S)
        if gap_rows:
            frames.append(pl.DataFrame(gap_rows))

    merged = pl.concat(frames, how="diagonal").unique(subset=["hourly_time"], keep="first")
    merged = merged.with_columns(pl.lit(name).alias("stadium_name"))
    _save_hourly_cache(name, merged)
    logger.info(
        "%s: extended cache to %d hourly rows (%s..%s)",
        name,
        len(merged),
        start,
        end,
    )
    return merged


def build_hourly_index(
    venues: pl.DataFrame, years: list[int], coords: dict[str, tuple[float, float]]
) -> pl.DataFrame:
    if not years:
        return pl.DataFrame()
    start, _ = _season_window(min(years))
    _, end = _season_window(max(years))
    frames: list[pl.DataFrame] = []
    for row in venues.iter_rows(named=True):
        name = str(row["stadium_name"])
        cached = _load_hourly_cache(name)
        if cached is not None:
            pair = coords.get(name)
            if pair:
                cached = _extend_hourly_cache(name, cached, start, end, pair[0], pair[1])
            else:
                cached = _ensure_stadium_name(cached, name)
            logger.info("%s: using %d hourly rows (cache)", name, len(cached))
            frames.append(cached)
            continue
        pair = coords.get(name)
        if not pair:
            continue
        lat, lon = pair
        hourly_rows = fetch_archive_hourly(lat, lon, start, end)
        time.sleep(REQUEST_PAUSE_S)
        if not hourly_rows:
            year_frames: list[pl.DataFrame] = []
            time.sleep(ARCHIVE_429_SLEEP_S)
            for year in years:
                y_start, y_end = _season_window(int(year))
                hourly_rows = fetch_archive_hourly(lat, lon, y_start, y_end)
                time.sleep(REQUEST_PAUSE_S)
                if not hourly_rows:
                    continue
                year_frames.append(
                    pl.DataFrame(hourly_rows).with_columns(pl.lit(name).alias("stadium_name"))
                )
                logger.info("%s %s: %d hourly rows", name, year, len(hourly_rows))
            if not year_frames:
                continue
            hdf = pl.concat(year_frames, how="diagonal")
            _save_hourly_cache(name, hdf)
            frames.append(hdf)
            continue
        hdf = pl.DataFrame(hourly_rows).with_columns(pl.lit(name).alias("stadium_name"))
        _save_hourly_cache(name, hdf)
        frames.append(hdf)
        logger.info("%s %s..%s: %d hourly rows", name, start, end, len(hourly_rows))
    if not frames:
        return pl.DataFrame()
    return pl.concat(frames, how="diagonal")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if not MATCHUPS_PATH.exists():
        logger.error("Missing matchups file: %s", MATCHUPS_PATH)
        sys.exit(1)

    matchups = pl.read_csv(MATCHUPS_PATH, infer_schema_length=0)
    required = {"Date", "stadium_name", "Year"}
    missing_cols = required - set(matchups.columns)
    if missing_cols:
        logger.error("Matchups missing columns: %s", sorted(missing_cols))
        sys.exit(1)

    matchups = matchups.with_columns(
        [
            pl.col("Date").map_elements(iso_date, return_dtype=pl.String).alias("Date"),
            pl.col("Year").cast(pl.Int64, strict=False),
        ]
    ).filter(pl.col("Date").is_not_null() & pl.col("stadium_name").is_not_null())

    if "Time" in matchups.columns:
        matchups = matchups.with_columns(
            pl.struct(["Date", "Time"]).map_elements(
                lambda s: kickoff_et_hour(s["Date"], s["Time"]),
                return_dtype=pl.String,
            ).alias("hourly_time")
        )
    else:
        matchups = matchups.with_columns(
            pl.col("Date")
            .map_elements(lambda d: kickoff_et_hour(d, None), return_dtype=pl.String)
            .alias("hourly_time")
        )

    venues = (
        matchups.select(["stadium_name", "city", "state"])
        .unique(subset=["stadium_name"])
        .sort("stadium_name")
    )
    years = sorted(
        y for y in matchups.get_column("Year").drop_nulls().unique().to_list() if y is not None
    )
    logger.info("Matchups: %d rows, %d stadiums, years %s", len(matchups), len(venues), years)

    prev: pl.DataFrame | None = None
    if OUTPUT_PATH.exists():
        prev = pl.read_csv(OUTPUT_PATH, infer_schema_length=0)

    coords = resolve_coords(venues)
    hourly = build_hourly_index(venues, years, coords)
    wx_cols = ["temp_C", "rel_humidity", "wind_kph", "precip_mm", "pressure_hpa"]
    if hourly.is_empty() and prev is None:
        logger.error("No hourly weather rows fetched")
        sys.exit(1)

    if hourly.is_empty():
        weather = matchups
        for col in wx_cols:
            weather = weather.with_columns(pl.lit(None).alias(col))
    else:
        weather = matchups.join(hourly, on=["stadium_name", "hourly_time"], how="left")

    if prev is not None:
        prev_keep = [c for c in ["Date", "stadium_name"] + wx_cols if c in prev.columns]
        prev_join = prev.select(prev_keep).rename(
            {c: f"{c}_prev" for c in prev_keep if c not in ("Date", "stadium_name")}
        )
        weather = weather.join(prev_join, on=["Date", "stadium_name"], how="left")
        for col in wx_cols:
            prev_c = f"{col}_prev"
            if col in weather.columns and prev_c in weather.columns:
                weather = weather.with_columns(
                    pl.coalesce([pl.col(col), pl.col(prev_c)]).alias(col)
                ).drop(prev_c)
            elif prev_c in weather.columns:
                weather = weather.rename({prev_c: col})

    keep = [
        c
        for c in [
            "Date",
            "stadium_name",
            "city",
            "temp_C",
            "rel_humidity",
            "wind_kph",
            "precip_mm",
            "pressure_hpa",
        ]
        if c in weather.columns
    ]
    out = weather.select(keep).unique(subset=["Date", "stadium_name"], keep="first")
    BASE_DATA_DIR.mkdir(parents=True, exist_ok=True)
    out.write_csv(OUTPUT_PATH)

    n = len(out)
    n_temp = int(out.select(pl.col("temp_C").is_not_null().sum()).item()) if "temp_C" in out.columns else 0
    n_stad = out.get_column("stadium_name").n_unique() if "stadium_name" in out.columns else 0
    n_stad_temp = (
        int(
            out.group_by("stadium_name")
            .agg(pl.col("temp_C").is_not_null().sum().alias("n"))
            .filter(pl.col("n") > 0)
            .height
        )
        if "temp_C" in out.columns
        else 0
    )
    print(f"[OK] {OUTPUT_PATH}")
    print(f"  rows={n} temp_C_non_null={n_temp} stadiums={n_stad} stadiums_with_temp={n_stad_temp}")


if __name__ == "__main__":
    main()
