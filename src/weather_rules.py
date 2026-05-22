from __future__ import annotations

from datetime import date
from typing import Any

Alert = dict[str, str]


def build_weather_alerts(
    normalized: dict[str, Any],
    *,
    rain_prob_threshold: int,
    wind_kmh_threshold: int,
    heat_temp_threshold: int,
    cold_temp_threshold: int,
) -> list[Alert]:
    alerts: list[Alert] = []
    day = normalized.get("date") or date.today().isoformat()
    place = normalized.get("municipio_nombre", "tu zona")

    rain_probability = normalized.get("rain_probability")
    if rain_probability is not None and rain_probability >= rain_prob_threshold:
        period = normalized.get("rain_period", "hoy")
        alerts.append(
            {
                "type": "rain",
                "severity": "medium",
                "title": "Posible lluvia",
                "description": (
                    f"Probabilidad de lluvia del {rain_probability}% {period} en {place}."
                ),
                "dedupe_key": f"rain-{day}-{period}",
            }
        )

    wind_kmh = normalized.get("wind_kmh")
    if wind_kmh is not None and wind_kmh >= wind_kmh_threshold:
        period = normalized.get("wind_period", "hoy")
        alerts.append(
            {
                "type": "wind",
                "severity": "medium",
                "title": "Viento fuerte",
                "description": (
                    f"Viento previsto de hasta {wind_kmh} km/h {period} en {place}."
                ),
                "dedupe_key": f"wind-{day}-{period}",
            }
        )

    max_temp = normalized.get("max_temp")
    if max_temp is not None and max_temp >= heat_temp_threshold:
        alerts.append(
            {
                "type": "heat",
                "severity": "high" if max_temp >= heat_temp_threshold + 5 else "medium",
                "title": "Calor",
                "description": f"Temperatura maxima prevista de {max_temp} C en {place}.",
                "dedupe_key": f"heat-{day}",
            }
        )

    min_temp = normalized.get("min_temp")
    if min_temp is not None and min_temp <= cold_temp_threshold:
        alerts.append(
            {
                "type": "cold",
                "severity": "medium",
                "title": "Frio o helada",
                "description": f"Temperatura minima prevista de {min_temp} C en {place}.",
                "dedupe_key": f"cold-{day}",
            }
        )

    alerts.extend(build_official_alerts(normalized.get("official_alerts", []), place))
    return alerts


def build_official_alerts(raw_alerts: list[dict[str, Any]], place: str) -> list[Alert]:
    alerts: list[Alert] = []
    for idx, item in enumerate(raw_alerts):
        level = str(item.get("level", "")).lower()
        if level not in {"amarillo", "naranja", "rojo", "yellow", "orange", "red"}:
            continue
        event = str(item.get("event") or item.get("title") or "Aviso meteorologico")
        onset = str(item.get("onset") or item.get("effective") or "actual")
        severity = {
            "amarillo": "medium",
            "yellow": "medium",
            "naranja": "high",
            "orange": "high",
            "rojo": "critical",
            "red": "critical",
        }.get(level, "medium")
        alerts.append(
            {
                "type": "official",
                "severity": severity,
                "title": f"Aviso oficial AEMET: {event}",
                "description": (
                    f"AEMET mantiene aviso {level} por {event} en {place}. "
                    f"Inicio/periodo: {onset}."
                ),
                "dedupe_key": str(item.get("dedupe_key") or f"official-{level}-{event}-{onset}-{idx}"),
            }
        )
    return alerts
