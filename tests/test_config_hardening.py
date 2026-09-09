"""
Production startup hardening tests.

`backend.core.config._load()` reads the environment at call time, so we can
drive it directly with monkeypatched env vars and assert that production
boots only when JWT_SECRET (>=32 chars, non-default), DATABASE_URL, and
ALLOWED_ORIGINS are all present and safe.
"""
import pytest

from backend.core import config as config_module

_GOOD_SECRET = "x" * 32
_GOOD_DB = "postgresql://user:pass@host:5432/db"
_GOOD_ORIGINS = "https://pemsports.com,https://www.pemsports.com"


def _set_prod_env(monkeypatch, **overrides):
    """Populate a fully-valid production env, then apply overrides."""
    env = {
        "APP_ENV": "production",
        "JWT_SECRET": _GOOD_SECRET,
        "DATABASE_URL": _GOOD_DB,
        "ALLOWED_ORIGINS": _GOOD_ORIGINS,
    }
    env.update(overrides)
    for key in ("APP_ENV", "JWT_SECRET", "DATABASE_URL", "ALLOWED_ORIGINS", "RANKINGS_STORE"):
        value = env.get(key)
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)


def test_production_loads_with_complete_env(monkeypatch):
    _set_prod_env(monkeypatch)
    cfg = config_module._load()
    assert cfg.is_production
    assert cfg.allow_mock_auth is False
    assert cfg.allowed_origins == (
        "https://pemsports.com",
        "https://www.pemsports.com",
    )


@pytest.mark.parametrize("missing", ["JWT_SECRET", "DATABASE_URL", "ALLOWED_ORIGINS"])
def test_production_aborts_when_var_missing(monkeypatch, missing):
    _set_prod_env(monkeypatch, **{missing: None})
    with pytest.raises(SystemExit):
        config_module._load()


def test_production_rejects_short_jwt_secret(monkeypatch):
    _set_prod_env(monkeypatch, JWT_SECRET="too-short")
    with pytest.raises(SystemExit):
        config_module._load()


def test_production_rejects_dev_jwt_secret(monkeypatch):
    _set_prod_env(monkeypatch, JWT_SECRET=config_module._DEV_JWT_SECRET)
    with pytest.raises(SystemExit):
        config_module._load()


def test_production_defaults_rankings_store_to_postgres(monkeypatch):
    _set_prod_env(monkeypatch)
    cfg = config_module._load()
    assert cfg.rankings_store == "postgres"


def test_rankings_store_override(monkeypatch):
    _set_prod_env(monkeypatch)
    monkeypatch.setenv("RANKINGS_STORE", "duckdb")
    cfg = config_module._load()
    assert cfg.rankings_store == "duckdb"


def test_development_allows_mock_auth_and_defaults(monkeypatch):
    for key in ("JWT_SECRET", "DATABASE_URL", "ALLOWED_ORIGINS"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("APP_ENV", "development")
    cfg = config_module._load()
    assert cfg.is_development
    assert cfg.allow_mock_auth is True
    assert cfg.jwt_secret == config_module._DEV_JWT_SECRET
    assert "http://localhost:5174" in cfg.allowed_origins
    assert "http://127.0.0.1:5174" in cfg.allowed_origins
