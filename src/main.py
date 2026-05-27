from __future__ import annotations

import argparse
import io
import logging
import sys
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any
from xml.etree import ElementTree
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from zipfile import BadZipFile, ZipFile

from src.aemet_client import AemetClient, AemetClientError
from src.aemet_cache import AemetCache
from src.config import Config, ConfigError
from src.message_builder import build_alert_message, build_daily_summary_message
from src.state_store import StateStore
from src.telegram_client import TelegramClient, TelegramClientError
from src.weather_rules import build_weather_alerts

LOGGER = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bot meteorologico AEMET + Telegram")
    parser.add_argument("mode", choices=["alerts", "daily"], help="Modo de ejecucion")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    try:
        config = Config.from_env()
        run_bot(args.mode, config)
        return 0
    except (ConfigError, AemetClientError, TelegramClientError) as exc:
        LOGGER.error("%s", exc)
        return 1


def run_bot(mode: str, config: Config) -> dict[str, int | str]:
    aemet = AemetClient(config.aemet_api_key)
    telegram = TelegramClient(config.telegram_bot_token, config.telegram_chat_id)
    cache = AemetCache()
    cache_notes: set[str] = set()

    if mode == "daily":
        today_key = _today_key(config.timezone)
        normalized = dict(
            _get_cached_aemet_data(
                cache,
                key=f"forecast-summary-v2:{config.municipio_id}",
                fetch=lambda: normalize_forecast(
                    aemet.get_municipality_forecast(config.municipio_id),
                    config.municipio_nombre,
                ),
                cache_date=today_key,
                cache_notes=cache_notes,
                required=True,
            )
        )
        normalized["official_alerts"] = _get_cached_aemet_data(
            cache,
            key=f"official-alerts:{config.aemet_alert_area}",
            fetch=lambda: normalize_official_alerts(
                aemet.get_weather_alerts(config.aemet_alert_area)
            ),
            cache_date=today_key,
            cache_notes=cache_notes,
            required=False,
            default=[],
        )
        normalized.update(
            _get_current_observation(
                cache,
                aemet,
                config,
                cache_notes,
                now=_now(config.timezone),
            )
        )
        message_time = _now(config.timezone)
        _apply_expected_current_temperature(
            normalized,
            config.timezone,
            now=message_time,
        )
        normalized["daily_alerts"] = build_weather_alerts(
            normalized,
            rain_prob_threshold=config.rain_prob_threshold,
            wind_kmh_threshold=config.wind_kmh_threshold,
            heat_temp_threshold=config.heat_temp_threshold,
            cold_temp_threshold=config.cold_temp_threshold,
        )
        normalized["cache_note"] = bool(cache_notes)
        message = build_daily_summary_message(
            normalized,
            config.municipio_nombre,
            current_time=message_time.strftime("%H:%M"),
        )
        telegram.send_message(message)
        LOGGER.info("Resumen diario enviado.")
        return {"mode": "daily", "sent": 1}

    if mode != "alerts":
        raise ValueError(f"Modo no soportado: {mode}")

    forecast = aemet.get_municipality_forecast(config.municipio_id)
    try:
        official_alerts = normalize_official_alerts(
            aemet.get_weather_alerts(config.aemet_alert_area)
        )
    except AemetClientError as exc:
        LOGGER.warning("No se pudieron obtener avisos oficiales AEMET: %s", exc)
        official_alerts = []
    normalized = normalize_forecast(forecast, config.municipio_nombre)
    normalized["official_alerts"] = official_alerts
    alerts = build_weather_alerts(
        normalized,
        rain_prob_threshold=config.rain_prob_threshold,
        wind_kmh_threshold=config.wind_kmh_threshold,
        heat_temp_threshold=config.heat_temp_threshold,
        cold_temp_threshold=config.cold_temp_threshold,
    )
    state = StateStore()
    state.cleanup_old_entries(days=3)

    sent = 0
    for alert in alerts:
        key = alert["dedupe_key"]
        if state.has_been_notified(key):
            LOGGER.info("Alerta ya notificada, se omite: %s", key)
            continue
        telegram.send_message(build_alert_message(alert, config.municipio_nombre))
        state.mark_notified(key)
        sent += 1
        LOGGER.info("Alerta enviada: %s", key)

    LOGGER.info("Alertas detectadas=%s, enviadas=%s", len(alerts), sent)
    return {"mode": "alerts", "detected": len(alerts), "sent": sent}


def _get_current_observation(
    cache: AemetCache,
    aemet: AemetClient,
    config: Config,
    cache_notes: set[str],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    cache_key = (
        f"current-observation:{config.aemet_station_id}"
        if config.aemet_station_id
        else f"current-observation:{_normalize_text(config.municipio_nombre)}"
    )
    try:
        observations = aemet.get_current_observations(config.aemet_station_id)
        normalized = normalize_current_observation(
            observations,
            config.municipio_nombre,
            config.aemet_station_id,
            config.timezone,
            now=now,
            max_age_minutes=config.current_observation_max_age_minutes,
        )
        if normalized.get("current_temp") is not None:
            cache.set(cache_key, normalized)
        return normalized
    except AemetClientError as exc:
        stale = cache.get_stale(cache_key)
        if (
            _is_rate_limit_error(exc)
            and isinstance(stale, dict)
            and _is_recent_current_observation(
                stale,
                config.timezone,
                config.current_observation_max_age_minutes,
                now=now,
            )
        ):
            LOGGER.warning("AEMET limito la observacion actual; se usa cache.")
            cache_notes.add(cache_key)
            return stale
        LOGGER.warning("No se pudo obtener temperatura actual AEMET: %s", exc)
        return {}


def _get_cached_aemet_data(
    cache: AemetCache,
    *,
    key: str,
    fetch: Callable[[], Any],
    cache_notes: set[str],
    required: bool,
    max_age: timedelta | None = None,
    cache_date: str | None = None,
    default: Any | None = None,
) -> Any:
    cached = cache.get(key, max_age=max_age, cache_date=cache_date)
    if cached is not None:
        LOGGER.info("Usando cache AEMET valida: %s", key)
        return cached

    try:
        fresh = fetch()
        cache.set(key, fresh, cache_date=cache_date)
        return fresh
    except AemetClientError as exc:
        stale = cache.get_stale(key)
        if _is_rate_limit_error(exc) and stale is not None:
            LOGGER.warning("AEMET limito la API; se usa cache: %s", key)
            cache_notes.add(key)
            return stale
        if required:
            raise
        LOGGER.warning("No se pudo obtener %s: %s", key, exc)
        return default


def _is_rate_limit_error(exc: AemetClientError) -> bool:
    return "429" in str(exc) or "Too Many Requests" in str(exc)


def _current_time(timezone: str) -> str:
    return _now(timezone).strftime("%H:%M")


def _now(timezone_name: str) -> datetime:
    try:
        tz = ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        LOGGER.warning("Timezone no valido '%s'. Se usara UTC.", timezone_name)
        tz = ZoneInfo("UTC")
    return datetime.now(tz)


def _today_key(timezone: str) -> str:
    try:
        tz = ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")
    return datetime.now(tz).date().isoformat()


def normalize_current_temperature(
    observations: Any, municipio_nombre: str, station_id: str | None = None
) -> int | float | None:
    return normalize_current_observation(
        observations, municipio_nombre, station_id
    ).get("current_temp")


def normalize_current_observation(
    observations: Any,
    municipio_nombre: str,
    station_id: str | None = None,
    timezone_name: str = "Europe/Madrid",
    *,
    now: datetime | None = None,
    max_age_minutes: int | None = None,
) -> dict[str, Any]:
    if isinstance(observations, dict):
        candidates = [observations]
    elif isinstance(observations, list):
        candidates = observations
    else:
        return {}

    if not station_id:
        municipio_key = _normalize_text(municipio_nombre)
        candidates = [
            item
            for item in candidates
            if isinstance(item, dict)
            and municipio_key in _normalize_text(str(item.get("ubi", "")))
        ]

    candidates_with_temp = [
        item
        for item in candidates
        if isinstance(item, dict) and _to_number(item.get("ta")) is not None
    ]
    if not candidates_with_temp:
        return {}

    tz = _load_timezone(timezone_name)
    latest = max(
        candidates_with_temp,
        key=lambda item: _parse_observation_datetime(item.get("fint"))
        or datetime.min.replace(tzinfo=timezone.utc),
    )
    observed_at = _parse_observation_datetime(latest.get("fint"))
    observed_at_local = observed_at.astimezone(tz) if observed_at else None
    if (
        observed_at_local
        and max_age_minutes is not None
        and max_age_minutes > 0
        and _observation_age_minutes(observed_at_local, now, tz) > max_age_minutes
    ):
        return {
            "current_temp": None,
            "current_temp_time": observed_at_local.strftime("%H:%M"),
            "current_temp_station": latest.get("ubi") or latest.get("idema"),
            "current_temp_note": "AEMET no tiene una observacion reciente",
        }

    return {
        "current_temp": _to_number(latest.get("ta")),
        "current_temp_time": _format_observation_time(latest.get("fint"), tz),
        "current_temp_station": latest.get("ubi") or latest.get("idema"),
        "current_temp_observed_at": observed_at_local.isoformat()
        if observed_at_local
        else None,
    }


def _apply_expected_current_temperature(
    summary: dict[str, Any],
    timezone_name: str,
    *,
    now: datetime | None = None,
) -> None:
    if summary.get("current_temp") is not None:
        summary["current_temp_source"] = summary.get("current_temp_source") or "observed"
        return

    expected = _expected_temperature_for_now(
        summary.get("hourly_temperatures"),
        timezone_name,
        now=now,
    )
    if expected is None:
        return

    summary["current_temp"] = expected
    summary["current_temp_source"] = "forecast"
    summary.pop("current_temp_note", None)


def _expected_temperature_for_now(
    hourly_temperatures: Any,
    timezone_name: str,
    *,
    now: datetime | None = None,
) -> int | float | None:
    if not isinstance(hourly_temperatures, list):
        return None

    candidates = [
        item
        for item in hourly_temperatures
        if isinstance(item, dict)
        and _to_number(item.get("value")) is not None
        and _period_hour(item.get("periodo")) is not None
    ]
    if not candidates:
        return None

    tz = _load_timezone(timezone_name)
    current = now.astimezone(tz) if now else datetime.now(tz)
    current_minutes = current.hour * 60 + current.minute
    best = min(
        candidates,
        key=lambda item: abs((_period_hour(item.get("periodo")) or 0) * 60 - current_minutes),
    )
    return _to_number(best.get("value"))


def _is_recent_current_observation(
    observation: dict[str, Any],
    timezone_name: str,
    max_age_minutes: int | None,
    *,
    now: datetime | None = None,
) -> bool:
    if observation.get("current_temp") is None:
        return False
    if max_age_minutes is None or max_age_minutes <= 0:
        return True

    observed_at = _parse_observation_datetime(observation.get("current_temp_observed_at"))
    if observed_at is None:
        return False

    tz = _load_timezone(timezone_name)
    return _observation_age_minutes(observed_at.astimezone(tz), now, tz) <= max_age_minutes


def _format_observation_time(value: Any, tz: ZoneInfo) -> str | None:
    observed_at = _parse_observation_datetime(value)
    if observed_at:
        return observed_at.astimezone(tz).strftime("%H:%M")
    if not value:
        return None
    text = str(value)
    if "T" in text:
        return text.split("T", 1)[1][:5]
    return text[:5] if len(text) >= 5 else text


def _parse_observation_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        observed_at = datetime.fromisoformat(text)
    except ValueError:
        return None
    if observed_at.tzinfo is None:
        observed_at = observed_at.replace(tzinfo=timezone.utc)
    return observed_at


def _load_timezone(timezone_name: str) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        LOGGER.warning("Timezone no valido '%s'. Se usara UTC.", timezone_name)
        return ZoneInfo("UTC")


def _observation_age_minutes(
    observed_at_local: datetime, now: datetime | None, tz: ZoneInfo
) -> float:
    current = now.astimezone(tz) if now else datetime.now(tz)
    return (current - observed_at_local).total_seconds() / 60


def _normalize_text(value: str) -> str:
    replacements = str.maketrans("ÁÉÍÓÚÜÑáéíóúüñ", "AEIOUUNaeiouun")
    return value.translate(replacements).casefold()


def normalize_forecast(forecast: Any, municipio_nombre: str) -> dict[str, Any]:
    day = _first_forecast_day(forecast)
    return {
        "municipio_nombre": municipio_nombre,
        "date": day.get("fecha"),
        "max_temp": _to_number(_nested_get(day, ["temperatura", "maxima"])),
        "min_temp": _to_number(_nested_get(day, ["temperatura", "minima"])),
        "hourly_temperatures": _hourly_temperatures(
            _nested_get(day, ["temperatura", "dato"])
        ),
        "rain_probability": _max_period_value(day.get("probPrecipitacion", [])),
        "rain_period": _period_for_max_value(day.get("probPrecipitacion", [])),
        "wind_kmh": _max_wind(day.get("viento", [])),
        "wind_period": _period_for_max_wind(day.get("viento", [])),
        "sky_status": _first_sky_status(day.get("estadoCielo", [])),
    }


def normalize_official_alerts(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, bytes):
        return _normalize_cap_zip_alerts(raw)

    if isinstance(raw, str):
        return _normalize_cap_xml_alerts(raw)

    if isinstance(raw, dict):
        candidates = raw.get("features") or raw.get("alertas") or raw.get("avisos") or []
    else:
        candidates = raw
    if not isinstance(candidates, list):
        return []

    normalized = []
    for item in candidates:
        props = item.get("properties", item) if isinstance(item, dict) else {}
        if not isinstance(props, dict):
            continue
        normalized.append(
            {
                "level": props.get("nivel") or props.get("level") or props.get("severity"),
                "event": props.get("fenomeno") or props.get("event") or props.get("title"),
                "onset": props.get("inicio") or props.get("onset") or props.get("effective"),
                "dedupe_key": props.get("id") or props.get("identifier"),
            }
        )
    return normalized


def _normalize_cap_zip_alerts(raw_zip: bytes) -> list[dict[str, Any]]:
    try:
        with ZipFile(io.BytesIO(raw_zip)) as archive:
            alerts = []
            for name in archive.namelist():
                if not name.lower().endswith(".xml"):
                    continue
                with archive.open(name) as xml_file:
                    alerts.extend(
                        _normalize_cap_xml_alerts(
                            xml_file.read().decode("utf-8", errors="replace")
                        )
                    )
            return alerts
    except BadZipFile:
        LOGGER.info("Los avisos oficiales de AEMET no son un ZIP CAP parseable.")
        return []


def _normalize_cap_xml_alerts(raw_xml: str) -> list[dict[str, Any]]:
    if not raw_xml.strip():
        return []
    try:
        root = ElementTree.fromstring(raw_xml)
    except ElementTree.ParseError:
        LOGGER.info("Los avisos oficiales de AEMET no son JSON ni XML CAP parseable.")
        return []

    alerts = []
    for alert_node in _find_nodes_by_local_name(root, "alert"):
        identifier = _find_text_by_local_name(alert_node, "identifier")
        for info_node in _find_nodes_by_local_name(alert_node, "info"):
            level = _cap_level_from_info(info_node)
            event = _find_text_by_local_name(info_node, "event")
            onset = (
                _find_text_by_local_name(info_node, "onset")
                or _find_text_by_local_name(info_node, "effective")
            )
            alerts.append(
                {
                    "level": level,
                    "event": event,
                    "onset": onset,
                    "dedupe_key": "-".join(
                        part
                        for part in [identifier, level, event, onset]
                        if part
                    ),
                }
            )
    return alerts


def _cap_level_from_info(info_node: ElementTree.Element) -> str | None:
    # AEMET CAP suele publicar el color en parameters como "Nivel" o similar.
    for parameter in _find_nodes_by_local_name(info_node, "parameter"):
        name = _find_text_by_local_name(parameter, "valueName")
        value = _find_text_by_local_name(parameter, "value")
        if name and value and "nivel" in name.lower():
            return _normalize_alert_level(value)

    severity = _find_text_by_local_name(info_node, "severity")
    return _normalize_alert_level(severity)


def _normalize_alert_level(value: str | None) -> str | None:
    if not value:
        return None
    lower = value.lower()
    if "rojo" in lower or lower == "red" or lower == "extreme":
        return "rojo"
    if "naranja" in lower or lower == "orange" or lower == "severe":
        return "naranja"
    if "amarillo" in lower or lower == "yellow" or lower == "moderate":
        return "amarillo"
    return lower


def _find_nodes_by_local_name(
    node: ElementTree.Element, local_name: str
) -> list[ElementTree.Element]:
    return [child for child in node.iter() if _local_name(child.tag) == local_name]


def _find_text_by_local_name(node: ElementTree.Element, local_name: str) -> str | None:
    for child in node.iter():
        if _local_name(child.tag) == local_name and child.text:
            return child.text.strip()
    return None


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _first_forecast_day(forecast: Any) -> dict[str, Any]:
    if isinstance(forecast, list) and forecast:
        first = forecast[0]
    elif isinstance(forecast, dict):
        first = forecast
    else:
        raise AemetClientError("La prediccion de AEMET esta vacia")

    prediccion = first.get("prediccion", {}) if isinstance(first, dict) else {}
    days = prediccion.get("dia", []) if isinstance(prediccion, dict) else []
    if not days:
        raise AemetClientError("La prediccion de AEMET no contiene dias")
    return days[0]


def _nested_get(data: dict[str, Any], path: list[str]) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _max_period_value(items: Any) -> int | float | None:
    values = [_to_number(item.get("value")) for item in items if isinstance(item, dict)]
    values = [value for value in values if value is not None]
    return max(values) if values else None


def _period_for_max_value(items: Any) -> str:
    best_item = None
    best_value = None
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        value = _to_number(item.get("value"))
        if value is not None and (best_value is None or value > best_value):
            best_value = value
            best_item = item
    if not best_item:
        return "hoy"
    return _format_period(best_item.get("periodo"))


def _period_for_max_wind(items: Any) -> str:
    best_item = None
    best_value = None
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        value = _to_number(item.get("velocidad"))
        if value is not None and (best_value is None or value > best_value):
            best_value = value
            best_item = item
    if not best_item:
        return "hoy"
    return _format_period(best_item.get("periodo"))


def _format_period(period: Any) -> str:
    if not period:
        return "hoy"
    text = str(period)
    if len(text) == 4 and text.isdigit():
        return f"entre {text[:2]}:00 y {text[2:]}:00"
    return text


def _hourly_temperatures(items: Any) -> list[dict[str, int | float | str]]:
    normalized = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        value = _to_number(item.get("value"))
        hour = _period_hour(item.get("hora") or item.get("periodo"))
        if value is None or hour is None:
            continue
        normalized.append({"periodo": f"{hour:02d}", "value": value})
    return normalized


def _period_hour(period: Any) -> int | None:
    if period in (None, ""):
        return None
    text = str(period).strip()
    if text.isdigit():
        hour = int(text[:2] if len(text) >= 2 else text)
        return hour if 0 <= hour <= 23 else None
    return None


def _first_sky_status(items: Any) -> str | None:
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        description = item.get("descripcion")
        if description:
            return str(description)
    return None


def _max_wind(items: Any) -> int | float | None:
    values = []
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        values.append(_to_number(item.get("velocidad")))
    values = [value for value in values if value is not None]
    return max(values) if values else None


def _to_number(value: Any) -> int | float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return int(number) if number.is_integer() else number


if __name__ == "__main__":
    sys.exit(main())
