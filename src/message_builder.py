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
    sky_status = summary.get("sky_status") or "No disponible"
    daily_alerts = summary.get("daily_alerts") or []
    title = "☀️ <b>Resumen diario</b>"
    if current_time:
        title = f"{title} {html.escape(current_time)}"
    lines = [
        title,
        "",
        f"📍 {html.escape(municipio_nombre)}",
        f"☁️ Cielo: {html.escape(str(sky_status))}",
        f"🌡️ Actual: {html.escape(current_temp)}",
        f"🌡️ Máxima: {html.escape(max_temp)}",
        f"🌡️ Mínima: {html.escape(min_temp)}",
        f"🌧️ Lluvia máx.: {html.escape(rain_probability)}",
        f"💨 Viento máx.: {html.escape(wind_kmh)}",
    ]
    if daily_alerts:
        lines.append("")
        lines.append("⚠️ <b>Avisos del día</b>")
        for alert in daily_alerts:
            title_text = alert.get("title") or TYPE_LABELS.get(alert.get("type", ""), "Aviso")
            description = alert.get("description") or ""
            lines.append(
                f"• {html.escape(str(title_text))}: {html.escape(str(description))}"
            )
    if summary.get("cache_note"):
        lines.extend(["", "Nota: datos cacheados por límite temporal de AEMET."])
    lines.extend(["", "Fuente: AEMET"])
    return "\n".join(lines)


def _format_value(value: Any, suffix: str) -> str:
    if value is None:
        return "No disponible"
    return f"{value}{suffix}"
