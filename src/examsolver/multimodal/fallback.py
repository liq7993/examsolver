"""Cloud reachability probe for honest VLM degradation."""

from __future__ import annotations

import logging
import time

import httpx

logger = logging.getLogger(__name__)

CLOUD_PROBE_URL = "https://api.anthropic.com/v1/messages"
CACHE_TTL_SECONDS = 10.0
PROBE_TIMEOUT_SECONDS = 2.0

_cached_value: bool | None = None
_cached_at: float = 0.0


def check_cloud_reachable() -> bool:
    """Return whether the cloud VLM endpoint is reachable, cached for 10 seconds."""

    global _cached_at, _cached_value

    now = time.monotonic()
    if _cached_value is not None and now - _cached_at < CACHE_TTL_SECONDS:
        return _cached_value

    reachable = _probe_cloud()
    _cached_value = reachable
    _cached_at = now
    return reachable


def reset_cache_for_tests() -> None:
    """Clear cached probe state for deterministic tests."""

    global _cached_at, _cached_value

    _cached_value = None
    _cached_at = 0.0


def _probe_cloud() -> bool:
    try:
        with httpx.Client(timeout=PROBE_TIMEOUT_SECONDS) as client:
            client.head(CLOUD_PROBE_URL)
    except httpx.TimeoutException:
        logger.warning("multimodal.fallback: cloud probe timed out")
        return False
    except httpx.RequestError as exc:
        logger.warning("multimodal.fallback: cloud probe failed: %s", exc)
        return False
    return True
