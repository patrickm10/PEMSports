"""Kickoff hour parsing and incremental weather cache behavior (no network)."""

import sys
from pathlib import Path

import polars as pl
import pytest

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from pipelines import fetch_matchup_weather as weather


def test_iso_date_trims_to_yyyy_mm_dd():
    assert weather.iso_date("2018-09-06") == "2018-09-06"
    assert weather.iso_date("2018-09-06 00:00:00") == "2018-09-06"
    assert weather.iso_date(None) is None


def test_kickoff_rounds_to_nearest_et_hour():
    assert weather.kickoff_et_hour("2018-09-06", "8:20PM") == "2018-09-06T20:00"
    assert weather.kickoff_et_hour("2024-09-08", "1:00PM") == "2024-09-08T13:00"
    assert weather.kickoff_et_hour("2024-09-08", "4:25PM") == "2024-09-08T16:00"
    assert weather.kickoff_et_hour("2024-09-08", "") == "2024-09-08T13:00"


def test_cache_covers_range():
    cached = pl.DataFrame({"hourly_time": ["2023-09-01T12:00", "2024-02-20T12:00"]})
    assert weather._cache_covers_range(cached, "2023-09-01", "2024-02-20")
    assert not weather._cache_covers_range(cached, "2023-09-01", "2025-02-20")


def test_extend_hourly_cache_fetches_missing_tail(monkeypatch, tmp_path):
    stadium = "Lambeau Field"
    cache_dir = tmp_path / "weather_hourly"
    monkeypatch.setattr(weather, "HOURLY_CACHE_DIR", cache_dir)

    cached = pl.DataFrame(
        {
            "hourly_time": ["2024-09-01T12:00", "2024-09-08T13:00"],
            "temp_C": [17.0, 18.0],
            "stadium_name": [stadium, stadium],
        }
    )
    weather._save_hourly_cache(stadium, cached)

    fetched: list[tuple[str, str]] = []

    def fake_fetch(_lat, _lon, start_date, end_date):
        fetched.append((start_date, end_date))
        return [{"hourly_time": "2025-09-07T13:00", "temp_C": 20.0}]

    monkeypatch.setattr(weather, "fetch_archive_hourly", fake_fetch)
    monkeypatch.setattr(weather, "time", type("T", (), {"sleep": staticmethod(lambda *_: None)})())

    extended = weather._extend_hourly_cache(
        stadium,
        weather._load_hourly_cache(stadium),
        "2024-09-01",
        "2025-02-20",
        44.5,
        -88.0,
    )

    assert fetched == [("2024-09-09", "2025-02-20")]
    assert extended.height == 3
    assert "2025-09-07T13:00" in extended.get_column("hourly_time").to_list()


def test_build_hourly_index_uses_all_venues_not_stadium_skip(monkeypatch, tmp_path):
    cache_dir = tmp_path / "weather_hourly"
    monkeypatch.setattr(weather, "HOURLY_CACHE_DIR", cache_dir)

    stadium = "Lambeau Field"
    weather._save_hourly_cache(
        stadium,
        pl.DataFrame(
            {
                "hourly_time": ["2024-09-08T13:00"],
                "temp_C": [18.0],
                "stadium_name": [stadium],
            }
        ),
    )

    calls: list[str] = []

    def fake_extend(name, cached, start, end, lat, lon):
        calls.append(name)
        return cached.with_columns(pl.lit(name).alias("stadium_name"))

    monkeypatch.setattr(weather, "_extend_hourly_cache", fake_extend)

    venues = pl.DataFrame({"stadium_name": [stadium], "city": ["Green Bay"], "state": ["WI"]})
    coords = {stadium: (44.5, -88.0)}
    hourly = weather.build_hourly_index(venues, [2024, 2025], coords)

    assert calls == [stadium]
    assert hourly.height == 1


def test_main_joins_new_stadium_dates_from_hourly(monkeypatch, tmp_path):
    base = tmp_path / "data" / "nfl_metadata"
    base.mkdir(parents=True)
    cache_dir = tmp_path / "weather_hourly"
    monkeypatch.setattr(weather, "BASE_DATA_DIR", base)
    monkeypatch.setattr(weather, "MATCHUPS_PATH", base / "nfl_matchups_enriched.csv")
    monkeypatch.setattr(weather, "OUTPUT_PATH", base / "nfl_matchups_with_weather.csv")
    monkeypatch.setattr(weather, "COORDS_PATH", base / "stadium_coords.csv")
    monkeypatch.setattr(weather, "HOURLY_CACHE_DIR", cache_dir)

    stadium = "Lambeau Field"
    prev = pl.DataFrame(
        {
            "Date": ["2024-09-08"],
            "stadium_name": [stadium],
            "city": ["Green Bay"],
            "temp_C": ["10.0"],
            "rel_humidity": ["50"],
            "wind_kph": ["5"],
            "precip_mm": ["0"],
            "pressure_hpa": ["1010"],
        }
    )
    prev.write_csv(weather.OUTPUT_PATH)

    matchups = pl.DataFrame(
        {
            "Date": ["2024-09-08", "2025-09-07"],
            "Time": ["1:00PM", "1:00PM"],
            "Year": [2024, 2025],
            "stadium_name": [stadium, stadium],
            "city": ["Green Bay", "Green Bay"],
            "state": ["WI", "WI"],
        }
    )
    matchups.write_csv(weather.MATCHUPS_PATH)

    def fake_resolve(_venues):
        return {stadium: (44.5, -88.0)}

    def fake_build(_venues, years, coords):
        return pl.DataFrame(
            {
                "stadium_name": [stadium, stadium],
                "hourly_time": ["2024-09-08T13:00", "2025-09-07T13:00"],
                "temp_C": [10.0, 22.0],
                "rel_humidity": [50.0, 55.0],
                "wind_kph": [5.0, 6.0],
                "precip_mm": [0.0, 0.0],
                "pressure_hpa": [1010.0, 1011.0],
            }
        )

    monkeypatch.setattr(weather, "resolve_coords", fake_resolve)
    monkeypatch.setattr(weather, "build_hourly_index", fake_build)

    weather.main()

    out = pl.read_csv(weather.OUTPUT_PATH, infer_schema_length=0)
    row_2025 = out.filter(pl.col("Date") == "2025-09-07")
    assert row_2025.height == 1
    assert row_2025.get_column("temp_C")[0] not in (None, "")
