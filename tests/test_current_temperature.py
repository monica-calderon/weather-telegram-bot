from src.main import normalize_current_temperature


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
