"""Overpass API client with caching and polite retry behaviour."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Delhi administrative bounding box: south, west, north, east
DELHI_BBOX = (28.404, 76.838, 28.883, 77.347)

_USER_AGENT = (
    "TreeMap-Ingest/0.1 (citizen-science tree mapping; "
    "https://github.com/treemap/treemap; contact: ingest@treemap.example)"
)
_OVERPASS_ENDPOINT = "https://overpass-api.de/api/interpreter"


def build_delhi_query(bbox: tuple[float, float, float, float] = DELHI_BBOX) -> str:
    """Return an Overpass QL query for natural=tree nodes inside *bbox*.

    bbox is (south, west, north, east) as expected by Overpass.
    """
    s, w, n, e = bbox
    return (
        "[out:json][timeout:180];\n"
        f"node[natural=tree]({s},{w},{n},{e});\n"
        "out body;"
    )


def fetch_overpass(
    query: str,
    cache_path: Path,
    *,
    endpoint: str = _OVERPASS_ENDPOINT,
    max_retries: int = 5,
    initial_backoff_s: float = 5.0,
) -> dict[str, Any]:
    """Fetch *query* from the Overpass API, writing the result to *cache_path*.

    If *cache_path* already contains a valid JSON response the file is returned
    immediately without making a network request (one query per run).

    Retry with exponential back-off on 429 / 5xx responses.
    """
    cache_path = Path(cache_path)

    # Return cached result if it exists and is valid JSON
    if cache_path.is_file() and cache_path.stat().st_size > 0:
        try:
            data = json.loads(cache_path.read_bytes())
            if "elements" in data:
                logger.info("Using cached Overpass response: %s", cache_path)
                return data
        except (json.JSONDecodeError, OSError):
            logger.warning("Cached file is corrupt; re-fetching: %s", cache_path)

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = cache_path.with_suffix(cache_path.suffix + ".part")

    session = requests.Session()
    session.headers["User-Agent"] = _USER_AGENT

    backoff = initial_backoff_s
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                "Overpass query attempt %d/%d …", attempt, max_retries
            )
            response = session.post(
                endpoint,
                data={"data": query},
                timeout=(15, 300),
            )
            if response.status_code == 429 or response.status_code >= 500:
                logger.warning(
                    "HTTP %s; retrying in %.0f s …",
                    response.status_code,
                    backoff,
                )
                time.sleep(backoff)
                backoff = min(backoff * 2, 120.0)
                continue
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            # Persist to cache atomically
            tmp_path.write_bytes(response.content)
            tmp_path.replace(cache_path)
            logger.info(
                "Overpass response cached (%d elements): %s",
                len(data.get("elements", [])),
                cache_path,
            )
            return data
        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(
                "Request error on attempt %d: %s; retrying in %.0f s …",
                attempt,
                exc,
                backoff,
            )
            time.sleep(backoff)
            backoff = min(backoff * 2, 120.0)
        finally:
            tmp_path.unlink(missing_ok=True)

    raise RuntimeError(
        f"Overpass query failed after {max_retries} attempts"
    ) from last_exc
