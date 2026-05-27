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
            "current_temp_time": "12:50",
            "current_temp_station": "Alcala de Henares",
            "max_temp": 31,
            "min_temp": 18,
            "rain_probability": 60,
            "rain_period": "entre 12:00 y 18:00",
            "wind_kmh": 48,
            "wind_period": "entre 18:00 y 24:00",
            "cache_note": True,
            "daily_alerts": [
                {
                    "type": "rain",
                    "severity": "medium",
                    "title": "Posible lluvia",
                    "description": "Probabilidad de lluvia del 60% entre 12:00 y 18:00 en Alcala.",
                    "dedupe_key": "rain-2026-05-22-1218",
                },
                {
                    "type": "wind",
                    "severity": "medium",
                    "title": "Viento fuerte",
                    "description": "Viento previsto de hasta 48 km/h entre 18:00 y 24:00 en Alcala.",
                    "dedupe_key": "wind-2026-05-22-1824",
                },
                {
                    "type": "heat",
                    "severity": "medium",
                    "title": "Calor",
                    "description": "Temperatura maxima prevista de 31 C en Alcala.",
                    "dedupe_key": "heat-2026-05-22",
                },
                {
                    "type": "official",
                    "severity": "high",
                    "title": "Aviso oficial AEMET: Tormentas",
                    "description": "AEMET mantiene aviso naranja por Tormentas en Alcala.",
                    "dedupe_key": "official-tormentas",
                },
            ],
        },
        "Alcala de Henares",
        current_time="09:00",
    )

    assert "☀️ <b>Resumen diario</b> 09:00" in message
    assert "Cielo: Poco nuboso" in message
    assert "Actual: 21°C" in message
    assert "12:50" not in message
    assert "Máxima: 31°C" in message
    assert "Mínima: 18°C" in message
    assert "Lluvia máx.: 60%" in message
    assert "Viento máx.: 48 km/h" in message
    assert "<b>Avisos del día</b>" in message
    assert "Posible lluvia: Probabilidad de lluvia del 60% entre 12:00 y 18:00" in message
    assert "Viento fuerte: Viento previsto de hasta 48 km/h entre 18:00 y 24:00" in message
    assert "Calor: Temperatura maxima prevista de 31 C" in message
    assert "Aviso oficial AEMET: Tormentas" in message
    assert "Nota: datos cacheados por límite temporal de AEMET." in message


def test_build_daily_summary_message_marks_forecast_current_temperature():
    message = build_daily_summary_message(
        {
            "current_temp": 22,
            "current_temp_source": "forecast",
        },
        "Alcala de Henares",
    )

    assert "Actual: 22°C prev." in message


def test_build_daily_summary_message_keeps_unavailable_current_temperature_short():
    message = build_daily_summary_message(
        {
            "current_temp": None,
            "current_temp_time": "08:00",
            "current_temp_station": "Alcala de Henares",
            "current_temp_note": "AEMET no tiene una observacion reciente",
        },
        "Alcala de Henares",
    )

    assert "Actual: No disponible" in message
    assert "AEMET no tiene una observacion reciente" not in message
