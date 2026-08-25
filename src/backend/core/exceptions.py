"""
Domain exception hierarchy for PEM Sports.

Every failure path inside the serving layer raises a subclass of
`PemSportsException`. A single FastAPI exception handler (registered in
`main.py`) maps the exception's `http_status` and `default_detail` into a
stable JSON envelope. This replaces the prior pattern of swallowing
errors and returning `[]`, which made empty results indistinguishable
from real data gaps.
"""
from __future__ import annotations

from typing import Optional


class PemSportsException(Exception):
    """Base class for all domain errors."""

    http_status: int = 500
    default_detail: str = "Internal engine error"

    def __init__(self, detail: Optional[str] = None) -> None:
        self.detail = detail or self.default_detail
        super().__init__(self.detail)


class TableMissingError(PemSportsException):
    """A required DuckDB table (e.g. `qb_weekly`) is not present."""

    http_status = 404
    default_detail = "Requested dataset has not been baked"


class NoDataForFilterError(PemSportsException):
    """Query succeeded but produced zero rows for the given filters."""

    http_status = 404
    default_detail = "No data for the requested filters"


class QueryEngineError(PemSportsException):
    """DuckDB raised a binder/parser/IO error that should surface as 500."""

    http_status = 500
    default_detail = "DuckDB query failure"


class DatabaseUnavailableError(PemSportsException):
    """Serving DuckDB file missing or the transactional pool is down."""

    http_status = 503
    default_detail = "Serving database not initialized"


class InvalidRequestError(PemSportsException):
    """Request failed validation after the FastAPI boundary (Draft Lab simulate)."""

    http_status = 422
    default_detail = "Invalid request"


# Backwards-compatibility alias (pre-PEM Sports brand). Prefer
# `PemSportsException` in new code; kept so any external/uncommitted
# consumers importing the old name continue to work.
NFLStatsException = PemSportsException
