from src.web_app import create_app


def test_cron_endpoint_requires_token(monkeypatch):
    monkeypatch.setenv("AEMET_API_KEY", "aemet")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setenv("MUNICIPIO_ID", "28005")
    monkeypatch.setenv("MUNICIPIO_NOMBRE", "Alcala")
    monkeypatch.setenv("CRON_SECRET", "secret")
    app = create_app()

    response = app.test_client().get("/cron/daily")

    assert response.status_code == 401
    assert response.json == {"error": "No autorizado", "ok": False}


def test_cron_endpoint_runs_daily_with_valid_token(monkeypatch):
    monkeypatch.setenv("AEMET_API_KEY", "aemet")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "chat")
    monkeypatch.setenv("MUNICIPIO_ID", "28005")
    monkeypatch.setenv("MUNICIPIO_NOMBRE", "Alcala")
    monkeypatch.setenv("CRON_SECRET", "secret")

    def fake_run_bot(mode, config):
        assert mode == "daily"
        assert config.cron_secret == "secret"
        return {"mode": "daily", "sent": 1}

    monkeypatch.setattr("src.web_app.run_bot", fake_run_bot)
    app = create_app()

    response = app.test_client().get("/cron/daily?token=secret")

    assert response.status_code == 200
    assert response.json == {"mode": "daily", "ok": True, "sent": 1}


def test_cron_endpoint_rejects_unknown_mode():
    app = create_app()

    response = app.test_client().get("/cron/weekly?token=secret")

    assert response.status_code == 404
    assert response.json == {"error": "Modo no soportado", "ok": False}
