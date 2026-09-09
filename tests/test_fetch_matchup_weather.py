"""Kickoff hour parsing for Open-Meteo join (no network)."""

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from pipelines.fetch_matchup_weather import iso_date, kickoff_et_hour


def test_iso_date_trims_to_yyyy_mm_dd():
    assert iso_date("2018-09-06") == "2018-09-06"
    assert iso_date("2018-09-06 00:00:00") == "2018-09-06"
    assert iso_date(None) is None


def test_kickoff_rounds_to_nearest_et_hour():
    assert kickoff_et_hour("2018-09-06", "8:20PM") == "2018-09-06T20:00"
    assert kickoff_et_hour("2024-09-08", "1:00PM") == "2024-09-08T13:00"
    assert kickoff_et_hour("2024-09-08", "4:25PM") == "2024-09-08T16:00"
    assert kickoff_et_hour("2024-09-08", "") == "2024-09-08T13:00"
