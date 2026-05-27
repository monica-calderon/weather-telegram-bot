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
    ) -> int | float:
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

        temperature = _current_temperature_from_payload(data)
        if temperature is None:
            raise OpenMeteoClientError("Open-Meteo no devolvio temperatura actual")
        return temperature


def _current_temperature_from_payload(data: Any) -> int | float | None:
    if not isinstance(data, dict):
        return None
    current = data.get("current")
    if not isinstance(current, dict):
        return None
    value = current.get("temperature_2m")
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number
