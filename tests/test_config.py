import pytest

from src.config import Config, ConfigError


OPTIONAL_ENV_VARS = [
    "AEMET_ALERT_AREA",
    "AEMET_STATION_ID",
    "CURRENT_OBSERVATION_MAX_AGE_MINUTES",
    "OPEN_METEO_LATITUDE",
    "OPEN_METEO_LONGITUDE",
    "GOOGLE_SERVICE_ACCOUNT_JSON",
    "GOOGLE_OAUTH_CLIENT_JSON",
    "GOOGLE_OAUTH_REFRESH_TOKEN",
    "GOOGLE_CALENDAR_IDS",
    "GOOGLE_CALENDAR_NAMES",
    "CALENDAR_EVENTS_MAX",
    "NTFY_METHOD",
    "NTFY_TOPIC",
    "NTFY_SERVER",
    "NTFY_TOKEN",
    "NTFY_USERNAME",
    "NTFY_PASSWORD",
    "NTFY_PRIORITY",
    "NTFY_TAGS",
]


def _clear_optional_env(monkeypatch):
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    for name in OPTIONAL_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def test_config_defaults_to_madrid_alert_area(monkeypatch):
    _clear_optional_env(monkeypatch)
    monkeypatch.setenv("AEMET_API_KEY", "aemet")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setenv("MUNICIPIO_ID", "28005")
    monkeypatch.setenv("MUNICIPIO_NOMBRE", "Alcala")
    monkeypatch.setenv("RAIN_PROB_THRESHOLD", "")

    config = Config.from_env()

    assert config.rain_prob_threshold == 50
    assert config.aemet_alert_area == "72"
    assert config.aemet_station_id == "3170Y"
    assert config.current_observation_max_age_minutes == 150
    assert config.open_meteo_latitude == 40.4818
    assert config.open_meteo_longitude == -3.3643
    assert config.google_service_account_json is None
    assert config.google_oauth_client_json is None
    assert config.google_oauth_refresh_token is None
    assert config.google_calendar_ids == ()
    assert config.google_calendar_names == ()
    assert config.calendar_events_max == 10
    assert config.notification_methods == ("telegram",)


def test_config_keeps_station_empty_for_unknown_municipality(monkeypatch):
    _clear_optional_env(monkeypatch)
    monkeypatch.setenv("AEMET_API_KEY", "aemet")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setenv("MUNICIPIO_ID", "99999")
    monkeypatch.setenv("MUNICIPIO_NOMBRE", "Otro")

    config = Config.from_env()

    assert config.aemet_station_id is None
    assert config.open_meteo_latitude is None
    assert config.open_meteo_longitude is None


def test_config_reads_google_calendar_settings(monkeypatch):
    _clear_optional_env(monkeypatch)
    monkeypatch.setenv("AEMET_API_KEY", "aemet")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setenv("MUNICIPIO_ID", "28005")
    monkeypatch.setenv("MUNICIPIO_NOMBRE", "Alcala")
    monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", '{"type":"service_account"}')
    monkeypatch.setenv(
        "GOOGLE_CALENDAR_IDS",
        "calendar-one@example.com, calendar-two@example.com",
    )
    monkeypatch.setenv("GOOGLE_CALENDAR_NAMES", "Personal, Bubu")
    monkeypatch.setenv("CALENDAR_EVENTS_MAX", "3")

    config = Config.from_env()

    assert config.google_service_account_json == '{"type":"service_account"}'
    assert config.google_calendar_ids == (
        "calendar-one@example.com",
        "calendar-two@example.com",
    )
    assert config.google_calendar_names == ("Personal", "Bubu")
    assert config.calendar_events_max == 3


def test_config_reads_google_calendar_oauth_settings(monkeypatch):
    _clear_optional_env(monkeypatch)
    monkeypatch.setenv("AEMET_API_KEY", "aemet")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setenv("MUNICIPIO_ID", "28005")
    monkeypatch.setenv("MUNICIPIO_NOMBRE", "Alcala")
    monkeypatch.setenv("GOOGLE_OAUTH_CLIENT_JSON", '{"installed":{"client_id":"id"}}')
    monkeypatch.setenv("GOOGLE_OAUTH_REFRESH_TOKEN", "refresh-token")

    config = Config.from_env()

    assert config.google_oauth_client_json == '{"installed":{"client_id":"id"}}'
    assert config.google_oauth_refresh_token == "refresh-token"


def test_config_auto_uses_ntfy_when_only_ntfy_is_configured(monkeypatch):
    _clear_optional_env(monkeypatch)
    monkeypatch.setenv("AEMET_API_KEY", "aemet")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setenv("NTFY_TOPIC", "weather-topic")
    monkeypatch.setenv("NTFY_SERVER", "https://ntfy.example.com")
    monkeypatch.setenv("NTFY_TOKEN", "secret")
    monkeypatch.setenv("NTFY_PRIORITY", "high")
    monkeypatch.setenv("NTFY_TAGS", "sun,umbrella")
    monkeypatch.setenv("MUNICIPIO_ID", "28005")
    monkeypatch.setenv("MUNICIPIO_NOMBRE", "Alcala")

    config = Config.from_env()

    assert config.notification_methods == ("ntfy",)
    assert config.ntfy_topic == "weather-topic"
    assert config.ntfy_server == "https://ntfy.example.com"
    assert config.ntfy_token == "secret"
    assert config.ntfy_priority == "high"
    assert config.ntfy_tags == ("sun", "umbrella")


def test_config_both_requires_both_notification_configs(monkeypatch):
    _clear_optional_env(monkeypatch)
    monkeypatch.setenv("AEMET_API_KEY", "aemet")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setenv("NTFY_TOPIC", "weather-topic")
    monkeypatch.setenv("NTFY_METHOD", "both")
    monkeypatch.setenv("MUNICIPIO_ID", "28005")
    monkeypatch.setenv("MUNICIPIO_NOMBRE", "Alcala")

    config = Config.from_env()

    assert config.notification_methods == ("telegram", "ntfy")


def test_config_auto_uses_all_configured_notification_channels(monkeypatch):
    _clear_optional_env(monkeypatch)
    monkeypatch.setenv("AEMET_API_KEY", "aemet")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setenv("NTFY_TOPIC", "weather-topic")
    monkeypatch.setenv("NTFY_METHOD", "auto")
    monkeypatch.setenv("MUNICIPIO_ID", "28005")
    monkeypatch.setenv("MUNICIPIO_NOMBRE", "Alcala")

    config = Config.from_env()

    assert config.notification_methods == ("telegram", "ntfy")


def test_config_rejects_invalid_ntfy_method(monkeypatch):
    _clear_optional_env(monkeypatch)
    monkeypatch.setenv("AEMET_API_KEY", "aemet")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setenv("NTFY_METHOD", "email")
    monkeypatch.setenv("MUNICIPIO_ID", "28005")
    monkeypatch.setenv("MUNICIPIO_NOMBRE", "Alcala")

    with pytest.raises(ConfigError, match="NTFY_METHOD debe ser"):
        Config.from_env()


def test_config_fails_without_any_notification_channel(monkeypatch):
    _clear_optional_env(monkeypatch)
    monkeypatch.setenv("AEMET_API_KEY", "aemet")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.setenv("MUNICIPIO_ID", "28005")
    monkeypatch.setenv("MUNICIPIO_NOMBRE", "Alcala")

    with pytest.raises(ConfigError, match="No hay ningun canal"):
        Config.from_env()
