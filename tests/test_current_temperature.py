from datetime import datetime
from zoneinfo import ZoneInfo

from src.aemet_cache import AemetCache
from src.aemet_client import AemetClientError
from src.config import Config
from src.main import (
    _apply_expected_current_temperature,
    _expected_temperature_for_now,
    _get_current_observation,
    normalize_current_observation,
    normalize_current_temperature,
)


def test_normalize_current_temperature_uses_matching_municipality_latest_value():
    observations = [
        {"ubi": "MADRID", "ta": 20.1, "fint": "2026-05-22T07:00:00"},
        {"ubi": "ALCALA DE HENARES", "ta": 18.4, "fint": "2026-05-22T07:00:00"},
        {"ubi": "ALCALA DE HENARES", "ta": 19.2, "fint": "2026-05-22T08:00:00"},
    ]

    assert normalize_current_temperature(observations, "Alcalá de Henares") == 19.2


def test_normalize_current_temperature_uses_station_data_without_name_filter():
    observations = [
        {"ubi": "MADRID", "ta": 20.1, "fint": "2026-05-22T07:00:00"},
        {"ubi": "MADRID", "ta": 21.8, "fint": "2026-05-22T08:00:00"},
    ]

    assert (
        normalize_current_temperature(
            observations, "Alcalá de Henares", station_id="3195"
        )
        == 21.8
    )


def test_normalize_current_temperature_returns_none_without_match():
    observations = [{"ubi": "MADRID", "ta": 20.1, "fint": "2026-05-22T07:00:00"}]

    assert normalize_current_temperature(observations, "Alcalá de Henares") is None


def test_normalize_current_observation_includes_time_and_station():
    observations = [
        {
            "ubi": "ALCALA DE HENARES",
            "ta": 19.2,
            "fint": "2026-05-22T08:10:00",
        },
    ]

    assert normalize_current_observation(observations, "Alcalá de Henares") == {
        "current_temp": 19.2,
        "current_temp_time": "10:10",
        "current_temp_station": "ALCALA DE HENARES",
        "current_temp_observed_at": "2026-05-22T10:10:00+02:00",
    }


def test_normalize_current_observation_converts_utc_time_to_configured_timezone():
    observations = [
        {
            "ubi": "ALCALA DE HENARES",
            "ta": 19.2,
            "fint": "2026-01-22T08:10:00Z",
        },
    ]

    assert (
        normalize_current_observation(
            observations, "Alcalá de Henares", timezone_name="Europe/Madrid"
        )["current_temp_time"]
        == "09:10"
    )


def test_normalize_current_observation_rejects_old_values():
    observations = [
        {
            "ubi": "ALCALA DE HENARES",
            "ta": 19.2,
            "fint": "2026-05-22T06:00:00Z",
        },
    ]

    result = normalize_current_observation(
        observations,
        "Alcalá de Henares",
        timezone_name="Europe/Madrid",
        now=datetime(2026, 5, 22, 11, 0, tzinfo=ZoneInfo("Europe/Madrid")),
        max_age_minutes=150,
    )

    assert result == {
        "current_temp": None,
        "current_temp_time": "08:00",
        "current_temp_station": "ALCALA DE HENARES",
        "current_temp_note": "AEMET no tiene una observacion reciente",
    }


def test_current_observation_refreshes_even_when_cache_exists(tmp_path):
    cache = AemetCache(tmp_path / "aemet_cache.json")
    cache.set(
        "current-observation:alcala de henares",
        {
            "current_temp": 10,
            "current_temp_time": "07:00",
            "current_temp_station": "ALCALA DE HENARES",
        },
    )
    aemet = FakeAemet(
        [
            {
                "ubi": "ALCALA DE HENARES",
                "ta": 22.4,
                "fint": "2026-05-22T12:50:00",
            }
        ]
    )

    result = _get_current_observation(
        cache,
        aemet,
        _config(),
        set(),
    )

    assert aemet.calls == 1
    assert result == {
        "current_temp": 22.4,
        "current_temp_time": "14:50",
        "current_temp_station": "ALCALA DE HENARES",
        "current_temp_observed_at": "2026-05-22T14:50:00+02:00",
    }
    assert cache.get_stale("current-observation:alcala de henares") == result


def test_current_observation_uses_normalized_cache_on_rate_limit(tmp_path):
    cache = AemetCache(tmp_path / "aemet_cache.json")
    cached = {
        "current_temp": 21.5,
        "current_temp_time": "11:50",
        "current_temp_station": "ALCALA DE HENARES",
    }
    cache.set("current-observation:alcala de henares", cached)
    cache_notes: set[str] = set()

    result = _get_current_observation(
        cache,
        FakeAemet(AemetClientError("429 Client Error: Too Many Requests")),
        _config(),
        cache_notes,
    )

    assert result == cached
    assert cache_notes == {"current-observation:alcala de henares"}


def test_current_observation_ignores_old_cache_on_rate_limit(tmp_path):
    cache = AemetCache(tmp_path / "aemet_cache.json")
    cache.set(
        "current-observation:alcala de henares",
        {
            "current_temp": 21.5,
            "current_temp_time": "08:00",
            "current_temp_station": "ALCALA DE HENARES",
            "current_temp_observed_at": "2026-05-22T08:00:00+02:00",
        },
    )
    cache_notes: set[str] = set()

    result = _get_current_observation(
        cache,
        FakeAemet(AemetClientError("429 Client Error: Too Many Requests")),
        Config(
            aemet_api_key="aemet",
            telegram_bot_token="telegram",
            telegram_chat_id="chat",
            municipio_id="28005",
            municipio_nombre="Alcalá de Henares",
            current_observation_max_age_minutes=150,
        ),
        cache_notes,
        now=datetime(2026, 5, 22, 12, 0, tzinfo=ZoneInfo("Europe/Madrid")),
    )

    assert result == {}
    assert cache_notes == set()


def test_current_observation_uses_recent_cache_on_rate_limit(tmp_path):
    cache = AemetCache(tmp_path / "aemet_cache.json")
    cached = {
        "current_temp": 21.5,
        "current_temp_time": "11:00",
        "current_temp_station": "ALCALA DE HENARES",
        "current_temp_observed_at": "2026-05-22T11:00:00+02:00",
    }
    cache.set("current-observation:alcala de henares", cached)
    cache_notes: set[str] = set()

    result = _get_current_observation(
        cache,
        FakeAemet(AemetClientError("429 Client Error: Too Many Requests")),
        Config(
            aemet_api_key="aemet",
            telegram_bot_token="telegram",
            telegram_chat_id="chat",
            municipio_id="28005",
            municipio_nombre="Alcalá de Henares",
            current_observation_max_age_minutes=150,
        ),
        cache_notes,
        now=datetime(2026, 5, 22, 12, 0, tzinfo=ZoneInfo("Europe/Madrid")),
    )

    assert result == cached
    assert cache_notes == {"current-observation:alcala de henares"}


def test_expected_temperature_for_now_uses_nearest_forecast_hour():
    result = _expected_temperature_for_now(
        [
            {"periodo": "06", "value": 14},
            {"periodo": "12", "value": 22},
            {"periodo": "18", "value": 25},
        ],
        "Europe/Madrid",
        now=datetime(2026, 5, 22, 14, 30, tzinfo=ZoneInfo("Europe/Madrid")),
    )

    assert result == 22


def test_expected_current_temperature_keeps_observed_value():
    summary = {
        "current_temp": 21,
        "hourly_temperatures": [{"periodo": "12", "value": 25}],
    }

    _apply_expected_current_temperature(
        summary,
        "Europe/Madrid",
        now=datetime(2026, 5, 22, 12, 0, tzinfo=ZoneInfo("Europe/Madrid")),
    )

    assert summary["current_temp"] == 21
    assert summary["current_temp_source"] == "observed"


def test_expected_current_temperature_falls_back_to_forecast():
    summary = {
        "current_temp": None,
        "current_temp_note": "AEMET no tiene una observacion reciente",
        "hourly_temperatures": [
            {"periodo": "06", "value": 14},
            {"periodo": "12", "value": 22},
            {"periodo": "18", "value": 25},
        ],
    }

    _apply_expected_current_temperature(
        summary,
        "Europe/Madrid",
        now=datetime(2026, 5, 22, 11, 20, tzinfo=ZoneInfo("Europe/Madrid")),
    )

    assert summary["current_temp"] == 22
    assert summary["current_temp_source"] == "forecast"
    assert "current_temp_note" not in summary


class FakeAemet:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def get_current_observations(self, station_id=None):
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def _config() -> Config:
    return Config(
        aemet_api_key="aemet",
        telegram_bot_token="telegram",
        telegram_chat_id="chat",
        municipio_id="28005",
        municipio_nombre="Alcalá de Henares",
        current_observation_max_age_minutes=0,
    )
