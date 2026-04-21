"""
Environment configuration — strict, fail-fast settings loaded once at import time.

Contract:
- In `development` mode, sensible defaults are applied (local Postgres, mock
  JWT secret) to keep the DX smooth.
- In `staging` / `production` mode, missing or unsafe values raise
  `SystemExit(1)` immediately. There is no silent fallback to mock auth or
  in-memory state when the environment is intended to be real.

Access pattern:
    from backend.core.config import config
    if config.is_production:
        ...
"""
from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)

Environment = Literal["development", "staging", "production"]

_VALID_ENVS: tuple[str, ...] = ("development", "staging", "production")
_DEV_JWT_SECRET = "insecure-dev-secret-do-not-use-in-prod"


@dataclass(frozen=True)
class EnvironmentConfig:
    app_env: Environment
    jwt_secret: str
    jwt_algorithm: str
    database_url: str
    access_token_expire_minutes: int

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def allow_mock_auth(self) -> bool:
        return self.app_env == "development"


def _abort(reason: str) -> "EnvironmentConfig":
    logger.critical("Fatal config error: %s", reason)
    raise SystemExit(f"[config] {reason}")


def _load() -> EnvironmentConfig:
    raw_env = os.getenv("APP_ENV", "development").strip().lower()
    if raw_env not in _VALID_ENVS:
        _abort(f"APP_ENV must be one of {_VALID_ENVS}, got '{raw_env}'")
    app_env: Environment = raw_env  # type: ignore[assignment]

    jwt_secret = os.getenv("JWT_SECRET", "").strip()
    database_url = os.getenv("DATABASE_URL", "").strip()

    if app_env == "development":
        if not jwt_secret:
            jwt_secret = _DEV_JWT_SECRET
        if not database_url:
            database_url = "postgresql://postgres:postgres@localhost:5432/nflstats"
    else:
        if not jwt_secret or jwt_secret == _DEV_JWT_SECRET:
            _abort(
                f"JWT_SECRET must be set to a non-default value when APP_ENV={app_env}"
            )
        if len(jwt_secret) < 32:
            _abort(
                f"JWT_SECRET must be at least 32 characters when APP_ENV={app_env}"
            )
        if not database_url:
            _abort(f"DATABASE_URL must be set when APP_ENV={app_env}")

    return EnvironmentConfig(
        app_env=app_env,
        jwt_secret=jwt_secret,
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        database_url=database_url,
        access_token_expire_minutes=int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
        ),
    )


config: EnvironmentConfig = _load()
