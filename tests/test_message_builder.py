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
            "max_temp": 31,
            "min_temp": 18,
            "rain_probability": 40,
            "wind_kmh": 22,
        },
        "Alcala de Henares",
    )

    assert "<b>Resumen meteorológico diario</b>" in message
    assert "Máxima: 31°C" in message
    assert "Mínima: 18°C" in message
    assert "Lluvia: 40%" in message
    assert "Viento: 22 km/h" in message
