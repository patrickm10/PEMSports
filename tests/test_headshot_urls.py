"""Unit tests for Python headshot_url post-attach (no rankings SQL JOIN)."""
from __future__ import annotations

from backend.data.headshot_urls import (
    attach_headshot_urls,
    build_espn_headshot_url,
    build_headshot_path,
    clear_espn_map_cache,
    headshot_url_for,
)


def test_headshot_url_prefers_cdn_when_espn_id_present():
    url = headshot_url_for("uuid-1", "3918298")
    assert url.startswith("https://a.espncdn.com/combiner/i")
    assert "3918298" in url
    assert url == build_espn_headshot_url("3918298")


def test_headshot_url_falls_back_to_path_without_espn_id():
    assert headshot_url_for("uuid-1", None) == build_headshot_path("uuid-1")
    assert headshot_url_for("uuid-1", "") == build_headshot_path("uuid-1")


def test_attach_headshot_urls_uses_injected_map():
    clear_espn_map_cache()
    rows = [
        {"player_id": "aaa", "player_name": "A"},
        {"player_id": "bbb", "player_name": "B"},
    ]
    out = attach_headshot_urls(
        rows,
        get_conn=lambda: (_ for _ in ()).throw(RuntimeError("should not connect")),
        espn_map={"aaa": "111"},
    )
    assert out[0]["headshot_url"] == build_espn_headshot_url("111")
    assert out[1]["headshot_url"] == build_headshot_path("bbb")


def test_attach_headshot_urls_empty_map_is_path_only():
    rows = [{"player_id": "zzz"}]
    out = attach_headshot_urls(rows, get_conn=lambda: None, espn_map={})
    assert out[0]["headshot_url"] == "/headshots/zzz.jpg"
