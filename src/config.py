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
    rain_prob_threshold: int = 70
    wind_kmh_threshold: int = 45
    heat_temp_threshold: int = 35
    cold_temp_threshold: int = 0
    aemet_alert_area: str = "esp"

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
            rain_prob_threshold=_int_env("RAIN_PROB_THRESHOLD", 70),
            wind_kmh_threshold=_int_env("WIND_KMH_THRESHOLD", 45),
            heat_temp_threshold=_int_env("HEAT_TEMP_THRESHOLD", 35),
            cold_temp_threshold=_int_env("COLD_TEMP_THRESHOLD", 0),
            aemet_alert_area=os.getenv("AEMET_ALERT_AREA", "esp"),
        )


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ConfigError(f"{name} debe ser un numero entero, recibido: {value}") from exc
