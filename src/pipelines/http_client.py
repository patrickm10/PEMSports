"""
Resilient HTTP client for scraping pipelines.
Wraps requests.Session with automatic retries and backoff.
"""

import logging
from typing import Any, Mapping, Optional, Sequence, Union

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 10  # seconds
_RETRY_STRATEGY = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)


def _build_session() -> requests.Session:
    session = requests.Session()
    adapter = HTTPAdapter(max_retries=_RETRY_STRATEGY)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# Module-level singleton — reused across calls within a pipeline run.
_session = _build_session()


def fetch_html(url: str, timeout: int = _DEFAULT_TIMEOUT) -> Optional[str]:
    """
    Fetch a page and return its HTML content as a string.
    Returns None on any failure (logs the error).
    """
    try:
        response = _session.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.RequestException as exc:
        logger.error("GET %s failed: %s", url, exc)
        return None


def fetch_json(
    url: str,
    timeout: int = _DEFAULT_TIMEOUT,
    *,
    cookies: Optional[Mapping[str, str]] = None,
    headers: Optional[Mapping[str, str]] = None,
    params: Optional[Union[Mapping[str, Any], Sequence[tuple[str, Any]]]] = None,
) -> Optional[Any]:
    """
    Fetch a URL and return parsed JSON.
    Returns None on any failure (logs the error).
    """
    try:
        response = _session.get(
            url,
            timeout=timeout,
            cookies=dict(cookies) if cookies else None,
            headers=dict(headers) if headers else None,
            params=params,
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as exc:
        logger.error("GET JSON %s failed: %s", url, exc)
        return None
