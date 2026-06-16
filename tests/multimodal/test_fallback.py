from __future__ import annotations

import time

import httpx
import pytest

from examsolver.multimodal import fallback


def test_check_cloud_reachable_returns_true_and_caches_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    class FakeClient:
        def __init__(self, *, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def head(self, url: str) -> httpx.Response:
            calls.append(url)
            return httpx.Response(401)

    fallback.reset_cache_for_tests()
    monkeypatch.setattr(httpx, "Client", FakeClient)
    monkeypatch.setattr(time, "monotonic", lambda: 100.0)

    assert fallback.check_cloud_reachable() is True
    assert fallback.check_cloud_reachable() is True
    assert calls == [fallback.CLOUD_PROBE_URL]


def test_check_cloud_reachable_returns_false_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class TimeoutClient:
        def __init__(self, *, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self) -> "TimeoutClient":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def head(self, url: str) -> httpx.Response:
            raise httpx.TimeoutException("too slow")

    fallback.reset_cache_for_tests()
    monkeypatch.setattr(httpx, "Client", TimeoutClient)

    assert fallback.check_cloud_reachable() is False


def test_check_cloud_reachable_refreshes_after_cache_ttl(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    clock = {"now": 0.0}

    class FakeClient:
        def __init__(self, *, timeout: float) -> None:
            self.timeout = timeout

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def head(self, url: str) -> httpx.Response:
            calls.append(url)
            return httpx.Response(401)

    fallback.reset_cache_for_tests()
    monkeypatch.setattr(httpx, "Client", FakeClient)
    monkeypatch.setattr(time, "monotonic", lambda: clock["now"])

    assert fallback.check_cloud_reachable() is True
    clock["now"] = fallback.CACHE_TTL_SECONDS + 0.1
    assert fallback.check_cloud_reachable() is True

    assert calls == [fallback.CLOUD_PROBE_URL, fallback.CLOUD_PROBE_URL]
