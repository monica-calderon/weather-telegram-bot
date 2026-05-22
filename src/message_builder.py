from __future__ import annotations

import html
from typing import Any


TYPE_LABELS = {
    "rain": "Lluvia",
    "wind": "Viento",
    "heat": "Calor",
    "cold": "Frio/helada",
    "official": "Aviso oficial",
}


def build_alert_message(alert: dict[str, str], municipio_nombre: str) -> str:
    alert_type = TYPE_LABELS.get(alert.get("type", ""), alert.get("type", "Alerta"))
    return "\n".join(
        [
            "🌦️ <b>Alerta meteorológica</b>",
            "",
            f"📍 Zona: {html.escape(municipio_nombre)}",
            f"⚠️ Tipo: {html.escape(alert_type)}",
            f"📌 Detalle: {html.escape(alert.get('description', ''))}",
            "",
            "Fuente: AEMET",
        ]
    )


def build_daily_summary_message(
    summary: dict[str, Any], municipio_nombre: str, current_time: str | None = None
) -> str:
    max_temp = _format_value(summary.get("max_temp"), "°C")
    min_temp = _format_value(summary.get("min_temp"), "°C")
    current_temp = _format_value(summary.get("current_temp"), "°C")
    rain_probability = _format_value(summary.get("rain_probability"), "%")
    wind_kmh = _format_value(summary.get("wind_kmh"), " km/h")
    title = "☀️ <b>Resumen diario</b>"
    if current_time:
        title = f"{title} {html.escape(current_time)}"
    return "\n".join(
        [
            title,
            "",
            f"📍 {html.escape(municipio_nombre)}",
            f"🌡️ Actual: {html.escape(current_temp)}",
            f"🌡️ Máxima: {html.escape(max_temp)}",
            f"🌡️ Mínima: {html.escape(min_temp)}",
            f"🌧️ Lluvia: {html.escape(rain_probability)}",
            f"💨 Viento: {html.escape(wind_kmh)}",
            "",
            "Fuente: AEMET",
        ]
    )


def _format_value(value: Any, suffix: str) -> str:
    if value is None:
        return "No disponible"
    return f"{value}{suffix}"
