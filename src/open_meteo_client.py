from __future__ import annotations

from typing import Any

import requests


class OpenMeteoClientError(RuntimeError):
    """Raised when Open-Meteo cannot be queried successfully."""


class OpenMeteoClient:
    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, timeout: int = 15) -> None:
        self.timeout = timeout
        self.session = requests.Session()

    def get_current_temperature(
        self, latitude: float, longitude: float, timezone_name: str
    ) -> dict[str, int | float | str | None]:
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "current": "temperature_2m",
            "timezone": timezone_name,
        }
        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            raise OpenMeteoClientError(f"Error consultando Open-Meteo: {exc}") from exc
        except ValueError as exc:
            raise OpenMeteoClientError("Open-Meteo no devolvio JSON valido") from exc

        current = _current_temperature_from_payload(data)
        if current["temperature"] is None:
            raise OpenMeteoClientError("Open-Meteo no devolvio temperatura actual")
        return current


def _current_temperature_from_payload(data: Any) -> dict[str, int | float | str | None]:
    empty = {"temperature": None, "time": None}
    if not isinstance(data, dict):
        return empty
    current = data.get("current")
    if not isinstance(current, dict):
        return empty
    value = current.get("temperature_2m")
    if value in (None, ""):
        return empty
    try:
        number = float(value)
    except (TypeError, ValueError):
        return empty
    return {
        "temperature": int(number) if number.is_integer() else number,
        "time": _format_open_meteo_time(current.get("time")),
    }


def _format_open_meteo_time(value: Any) -> str | None:
    if not value:
        return None
    text = str(value)
    if "T" in text:
        return text.split("T", 1)[1][:5]
    return text[:5] if len(text) >= 5 else text
