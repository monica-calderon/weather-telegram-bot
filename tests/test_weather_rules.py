from src.weather_rules import build_weather_alerts


def base_weather(**overrides):
    data = {
        "municipio_nombre": "Alcala de Henares",
        "date": "2026-05-21",
        "rain_probability": 10,
        "rain_period": "hoy",
        "wind_kmh": 10,
        "max_temp": 20,
        "min_temp": 8,
        "official_alerts": [],
    }
    data.update(overrides)
    return data


def test_rain_alert_when_probability_reaches_threshold():
    alerts = build_weather_alerts(
        base_weather(rain_probability=80),
        rain_prob_threshold=70,
        wind_kmh_threshold=45,
        heat_temp_threshold=35,
        cold_temp_threshold=0,
    )

    assert alerts[0]["type"] == "rain"
    assert alerts[0]["dedupe_key"] == "rain-2026-05-21-hoy"


def test_wind_alert_when_speed_reaches_threshold():
    alerts = build_weather_alerts(
        base_weather(wind_kmh=50, wind_period="entre 18:00 y 24:00"),
        rain_prob_threshold=70,
        wind_kmh_threshold=45,
        heat_temp_threshold=35,
        cold_temp_threshold=0,
    )

    wind_alert = next(alert for alert in alerts if alert["type"] == "wind")
    assert "entre 18:00 y 24:00" in wind_alert["description"]
    assert wind_alert["dedupe_key"] == "wind-2026-05-21-entre 18:00 y 24:00"


def test_heat_alert_when_max_temperature_reaches_threshold():
    alerts = build_weather_alerts(
        base_weather(max_temp=36),
        rain_prob_threshold=70,
        wind_kmh_threshold=45,
        heat_temp_threshold=35,
        cold_temp_threshold=0,
    )

    assert any(alert["type"] == "heat" for alert in alerts)


def test_cold_alert_when_min_temperature_reaches_threshold():
    alerts = build_weather_alerts(
        base_weather(min_temp=-1),
        rain_prob_threshold=70,
        wind_kmh_threshold=45,
        heat_temp_threshold=35,
        cold_temp_threshold=0,
    )

    assert any(alert["type"] == "cold" for alert in alerts)


def test_official_alert_for_known_aemet_levels():
    alerts = build_weather_alerts(
        base_weather(official_alerts=[{"level": "naranja", "event": "tormentas"}]),
        rain_prob_threshold=70,
        wind_kmh_threshold=45,
        heat_temp_threshold=35,
        cold_temp_threshold=0,
    )

    assert any(alert["type"] == "official" and alert["severity"] == "high" for alert in alerts)
