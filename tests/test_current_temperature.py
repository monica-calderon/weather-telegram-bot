from src.aemet_cache import AemetCache
from src.aemet_client import AemetClientError
from src.config import Config
from src.main import (
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
        "current_temp_time": "08:10",
        "current_temp_station": "ALCALA DE HENARES",
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
        "current_temp_time": "12:50",
        "current_temp_station": "ALCALA DE HENARES",
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
    )
