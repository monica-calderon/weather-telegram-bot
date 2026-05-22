from src.message_builder import build_alert_message, build_daily_summary_message


def test_build_alert_message_contains_expected_fields():
    message = build_alert_message(
        {
            "type": "rain",
            "severity": "medium",
            "title": "Posible lluvia",
            "description": "Probabilidad de lluvia del 80%.",
            "dedupe_key": "rain-2026-05-21-hoy",
        },
        "Alcala de Henares",
    )

    assert "<b>Alerta meteorológica</b>" in message
    assert "Zona: Alcala de Henares" in message
    assert "Tipo: Lluvia" in message
    assert "Fuente: AEMET" in message


def test_build_daily_summary_message_contains_expected_values():
    message = build_daily_summary_message(
        {
            "sky_status": "Poco nuboso",
            "current_temp": 21,
            "max_temp": 31,
            "min_temp": 18,
            "rain_probability": 60,
            "rain_period": "entre 12:00 y 18:00",
            "wind_kmh": 48,
            "wind_period": "entre 18:00 y 24:00",
            "wind_notice_threshold": 45,
        },
        "Alcala de Henares",
        current_time="09:00",
    )

    assert "☀️ <b>Resumen diario</b> 09:00" in message
    assert "Cielo: Poco nuboso" in message
    assert "Actual: 21°C" in message
    assert "Máxima: 31°C" in message
    assert "Mínima: 18°C" in message
    assert "Lluvia máx.: 60%" in message
    assert "Viento máx.: 48 km/h" in message
    assert "Aviso lluvia: 60% entre 12:00 y 18:00" in message
    assert "Aviso viento: 48 km/h entre 18:00 y 24:00" in message
