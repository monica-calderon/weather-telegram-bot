from src.config import Config


def test_config_defaults_to_madrid_alert_area(monkeypatch):
    monkeypatch.setenv("AEMET_API_KEY", "aemet")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setenv("MUNICIPIO_ID", "28005")
    monkeypatch.setenv("MUNICIPIO_NOMBRE", "Alcala")
    monkeypatch.delenv("AEMET_ALERT_AREA", raising=False)
    monkeypatch.delenv("AEMET_STATION_ID", raising=False)

    config = Config.from_env()

    assert config.aemet_alert_area == "72"
    assert config.aemet_station_id is None
