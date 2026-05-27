from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    aemet_api_key: str
    telegram_bot_token: str
    telegram_chat_id: str
    municipio_id: str
    municipio_nombre: str
    timezone: str = "Europe/Madrid"
    rain_prob_threshold: int = 50
    wind_kmh_threshold: int = 45
    heat_temp_threshold: int = 35
    cold_temp_threshold: int = 0
    aemet_alert_area: str = "72"
    aemet_station_id: str | None = None
    current_observation_max_age_minutes: int = 150
    open_meteo_latitude: float | None = None
    open_meteo_longitude: float | None = None
    google_service_account_json: str | None = None
    google_calendar_ids: tuple[str, ...] = ()
    calendar_events_max: int = 10

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()

        required = {
            "AEMET_API_KEY": os.getenv("AEMET_API_KEY"),
            "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
            "TELEGRAM_CHAT_ID": os.getenv("TELEGRAM_CHAT_ID"),
            "MUNICIPIO_ID": os.getenv("MUNICIPIO_ID"),
            "MUNICIPIO_NOMBRE": os.getenv("MUNICIPIO_NOMBRE"),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ConfigError(
                "Faltan variables de entorno obligatorias: " + ", ".join(missing)
            )

        return cls(
            aemet_api_key=required["AEMET_API_KEY"] or "",
            telegram_bot_token=required["TELEGRAM_BOT_TOKEN"] or "",
            telegram_chat_id=required["TELEGRAM_CHAT_ID"] or "",
            municipio_id=required["MUNICIPIO_ID"] or "",
            municipio_nombre=required["MUNICIPIO_NOMBRE"] or "",
            timezone=os.getenv("TIMEZONE", "Europe/Madrid"),
            rain_prob_threshold=_int_env("RAIN_PROB_THRESHOLD", 50),
            wind_kmh_threshold=_int_env("WIND_KMH_THRESHOLD", 45),
            heat_temp_threshold=_int_env("HEAT_TEMP_THRESHOLD", 35),
            cold_temp_threshold=_int_env("COLD_TEMP_THRESHOLD", 0),
            aemet_alert_area=os.getenv("AEMET_ALERT_AREA", "72"),
            aemet_station_id=_station_id_from_env(required["MUNICIPIO_ID"] or ""),
            current_observation_max_age_minutes=_int_env(
                "CURRENT_OBSERVATION_MAX_AGE_MINUTES", 150
            ),
            open_meteo_latitude=_coordinate_from_env(
                "OPEN_METEO_LATITUDE", required["MUNICIPIO_ID"] or "", "latitude"
            ),
            open_meteo_longitude=_coordinate_from_env(
                "OPEN_METEO_LONGITUDE", required["MUNICIPIO_ID"] or "", "longitude"
            ),
            google_service_account_json=_optional_env("GOOGLE_SERVICE_ACCOUNT_JSON"),
            google_calendar_ids=_csv_env("GOOGLE_CALENDAR_IDS"),
            calendar_events_max=_int_env("CALENDAR_EVENTS_MAX", 10),
        )


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigError(f"{name} debe ser un numero entero, recibido: {value}") from exc


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    return value.strip()


def _csv_env(name: str) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None or not value.strip():
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _station_id_from_env(municipio_id: str) -> str | None:
    configured = os.getenv("AEMET_STATION_ID")
    if configured and configured.strip():
        return configured.strip()

    known_station_by_municipality = {
        "28005": "3170Y",  # Alcala de Henares
    }
    return known_station_by_municipality.get(municipio_id)


def _coordinate_from_env(name: str, municipio_id: str, coordinate: str) -> float | None:
    configured = os.getenv(name)
    if configured and configured.strip():
        try:
            return float(configured.strip())
        except ValueError as exc:
            raise ConfigError(f"{name} debe ser un numero decimal") from exc

    known_coordinates_by_municipality = {
        "28005": {"latitude": 40.4818, "longitude": -3.3643},
    }
    defaults = known_coordinates_by_municipality.get(municipio_id)
    if not defaults:
        return None
    return defaults[coordinate]
