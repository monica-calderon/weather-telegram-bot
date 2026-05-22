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
    rain_notice = _build_rain_notice(summary)
    wind_notice = _build_wind_notice(summary)
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
    if rain_notice or wind_notice:
        lines.append("")
        if rain_notice:
            lines.append(rain_notice)
        if wind_notice:
            lines.append(wind_notice)
    lines.extend(["", "Fuente: AEMET"])
    return "\n".join(lines)


def _format_value(value: Any, suffix: str) -> str:
    if value is None:
        return "No disponible"
    return f"{value}{suffix}"


def _build_rain_notice(summary: dict[str, Any]) -> str | None:
    probability = _to_number(summary.get("rain_probability"))
    if probability is None or probability <= 50:
        return None
    period = summary.get("rain_period") or "hoy"
    return (
        f"☔ Aviso lluvia: {html.escape(_format_value(probability, '%'))} "
        f"{html.escape(str(period))}"
    )


def _build_wind_notice(summary: dict[str, Any]) -> str | None:
    wind = _to_number(summary.get("wind_kmh"))
    threshold = _to_number(summary.get("wind_notice_threshold")) or 45
    if wind is None or wind < threshold:
        return None
    period = summary.get("wind_period") or "hoy"
    return (
        f"💨 Aviso viento: {html.escape(_format_value(wind, ' km/h'))} "
        f"{html.escape(str(period))}"
    )


def _to_number(value: Any) -> int | float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number
