from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Config:
    aemet_api_key: str
    municipio_id: str
    municipio_nombre: str
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    ntfy_method: str = "auto"
    notification_methods: tuple[str, ...] = ("telegram",)
    ntfy_topic: str | None = None
    ntfy_server: str = "https://ntfy.sh"
    ntfy_token: str | None = None
    ntfy_username: str | None = None
    ntfy_password: str | None = None
    ntfy_priority: str | None = None
    ntfy_tags: tuple[str, ...] = ()
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
    google_calendar_names: tuple[str, ...] = ()
    calendar_events_max: int = 10

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()

        required = {
            "AEMET_API_KEY": os.getenv("AEMET_API_KEY"),
            "MUNICIPIO_ID": os.getenv("MUNICIPIO_ID"),
            "MUNICIPIO_NOMBRE": os.getenv("MUNICIPIO_NOMBRE"),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ConfigError(
                "Faltan variables de entorno obligatorias: " + ", ".join(missing)
            )

        telegram_bot_token = _optional_env("TELEGRAM_BOT_TOKEN")
        telegram_chat_id = _optional_env("TELEGRAM_CHAT_ID")
        ntfy_topic = _optional_env("NTFY_TOPIC")
        ntfy_method = (os.getenv("NTFY_METHOD") or "auto").strip().lower()
        notification_methods = _notification_methods_from_env(
            ntfy_method,
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=telegram_chat_id,
            ntfy_topic=ntfy_topic,
        )

        return cls(
            aemet_api_key=required["AEMET_API_KEY"] or "",
            municipio_id=required["MUNICIPIO_ID"] or "",
            municipio_nombre=required["MUNICIPIO_NOMBRE"] or "",
            telegram_bot_token=telegram_bot_token,
            telegram_chat_id=telegram_chat_id,
            ntfy_method=ntfy_method,
            notification_methods=notification_methods,
            ntfy_topic=ntfy_topic,
            ntfy_server=os.getenv("NTFY_SERVER", "https://ntfy.sh").strip()
            or "https://ntfy.sh",
            ntfy_token=_optional_env("NTFY_TOKEN"),
            ntfy_username=_optional_env("NTFY_USERNAME"),
            ntfy_password=_optional_env("NTFY_PASSWORD"),
            ntfy_priority=_optional_env("NTFY_PRIORITY"),
            ntfy_tags=_csv_env("NTFY_TAGS"),
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
            google_calendar_names=_csv_env("GOOGLE_CALENDAR_NAMES"),
            calendar_events_max=_int_env("CALENDAR_EVENTS_MAX", 10),
        )


def _notification_methods_from_env(
    method: str,
    *,
    telegram_bot_token: str | None,
    telegram_chat_id: str | None,
    ntfy_topic: str | None,
) -> tuple[str, ...]:
    valid_methods = {"auto", "telegram", "ntfy", "both"}
    if method not in valid_methods:
        raise ConfigError(
            "NTFY_METHOD debe ser uno de estos valores: auto, telegram, ntfy, both"
        )

    telegram_configured = bool(telegram_bot_token and telegram_chat_id)
    ntfy_configured = bool(ntfy_topic)

    if method == "auto":
        methods = []
        if telegram_configured:
            methods.append("telegram")
        if ntfy_configured:
            methods.append("ntfy")
        if methods:
            return tuple(methods)
        raise ConfigError(
            "No hay ningun canal de notificacion configurado. Configura "
            "TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID, NTFY_TOPIC, o NTFY_METHOD."
        )

    if method in {"telegram", "both"} and not telegram_configured:
        raise ConfigError(
            "NTFY_METHOD requiere Telegram, pero faltan TELEGRAM_BOT_TOKEN "
            "o TELEGRAM_CHAT_ID."
        )
    if method in {"ntfy", "both"} and not ntfy_configured:
        raise ConfigError("NTFY_METHOD requiere Ntfy, pero falta NTFY_TOPIC.")
    if method == "both":
        return ("telegram", "ntfy")
    return (method,)


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
