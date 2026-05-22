from __future__ import annotations

from datetime import timedelta

import pytest

from src.aemet_cache import AemetCache
from src.aemet_client import AemetClientError
from src.main import _get_cached_aemet_data


def test_valid_cache_avoids_fetch(tmp_path):
    cache = AemetCache(tmp_path / "aemet_cache.json")
    cache.set("forecast:28005", {"ok": True})
    calls = 0

    def fetch():
        nonlocal calls
        calls += 1
        return {"ok": False}

    result = _get_cached_aemet_data(
        cache,
        key="forecast:28005",
        fetch=fetch,
        cache_date=None,
        cache_notes=set(),
        required=True,
    )

    assert result == {"ok": True}
    assert calls == 0


def test_expired_cache_refreshes_value(tmp_path):
    cache = AemetCache(tmp_path / "aemet_cache.json")
    cache.set("forecast", {"old": True})

    result = _get_cached_aemet_data(
        cache,
        key="forecast",
        fetch=lambda: {"fresh": True},
        max_age=timedelta(seconds=-1),
        cache_notes=set(),
        required=True,
    )

    assert result == {"fresh": True}
    assert cache.get_stale("forecast") == {"fresh": True}


def test_different_cache_date_refreshes_but_remains_available_as_stale(tmp_path):
    cache = AemetCache(tmp_path / "aemet_cache.json")
    cache.set("forecast", {"old": True}, cache_date="2026-05-21")

    result = _get_cached_aemet_data(
        cache,
        key="forecast",
        fetch=lambda: {"fresh": True},
        cache_date="2026-05-22",
        cache_notes=set(),
        required=True,
    )

    assert result == {"fresh": True}
    assert cache.get("forecast", cache_date="2026-05-22") == {"fresh": True}


def test_rate_limit_uses_stale_cache(tmp_path):
    cache = AemetCache(tmp_path / "aemet_cache.json")
    cache.set("forecast", {"old": True})
    cache_notes: set[str] = set()

    result = _get_cached_aemet_data(
        cache,
        key="forecast",
        fetch=lambda: (_ for _ in ()).throw(
            AemetClientError("429 Client Error: Too Many Requests")
        ),
        max_age=timedelta(seconds=-1),
        cache_notes=cache_notes,
        required=True,
    )

    assert result == {"old": True}
    assert cache_notes == {"forecast"}


def test_rate_limit_uses_previous_day_cache(tmp_path):
    cache = AemetCache(tmp_path / "aemet_cache.json")
    cache.set("forecast", {"yesterday": True}, cache_date="2026-05-21")
    cache_notes: set[str] = set()

    result = _get_cached_aemet_data(
        cache,
        key="forecast",
        fetch=lambda: (_ for _ in ()).throw(
            AemetClientError("429 Client Error: Too Many Requests")
        ),
        cache_date="2026-05-22",
        cache_notes=cache_notes,
        required=True,
    )

    assert result == {"yesterday": True}
    assert cache_notes == {"forecast"}


def test_rate_limit_without_cache_keeps_error(tmp_path):
    cache = AemetCache(tmp_path / "aemet_cache.json")

    with pytest.raises(AemetClientError):
        _get_cached_aemet_data(
            cache,
            key="forecast",
            fetch=lambda: (_ for _ in ()).throw(
                AemetClientError("429 Client Error: Too Many Requests")
            ),
            max_age=timedelta(days=1),
            cache_notes=set(),
            required=True,
        )
