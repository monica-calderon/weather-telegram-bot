from src.config import Config


def test_config_defaults_to_madrid_alert_area(monkeypatch):
    monkeypatch.setenv("AEMET_API_KEY", "aemet")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setenv("MUNICIPIO_ID", "28005")
    monkeypatch.setenv("MUNICIPIO_NOMBRE", "Alcala")
    monkeypatch.setenv("RAIN_PROB_THRESHOLD", "")
    monkeypatch.delenv("AEMET_ALERT_AREA", raising=False)
    monkeypatch.delenv("AEMET_STATION_ID", raising=False)

    config = Config.from_env()

    assert config.rain_prob_threshold == 50
    assert config.aemet_alert_area == "72"
    assert config.aemet_station_id == "3170Y"
    assert config.current_observation_max_age_minutes == 150
    assert config.open_meteo_latitude == 40.4818
    assert config.open_meteo_longitude == -3.3643


def test_config_keeps_station_empty_for_unknown_municipality(monkeypatch):
    monkeypatch.setenv("AEMET_API_KEY", "aemet")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setenv("MUNICIPIO_ID", "99999")
    monkeypatch.setenv("MUNICIPIO_NOMBRE", "Otro")
    monkeypatch.delenv("AEMET_STATION_ID", raising=False)

    config = Config.from_env()

    assert config.aemet_station_id is None
    assert config.open_meteo_latitude is None
    assert config.open_meteo_longitude is None
