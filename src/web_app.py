from __future__ import annotations

import hmac
import logging
import os

from flask import Flask, jsonify, request

from src.config import Config, ConfigError
from src.main import run_bot

LOGGER = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def health():
        return jsonify({"ok": True, "service": "weather-telegram-bot"})

    @app.get("/cron/<mode>")
    def cron(mode: str):
        if mode not in {"alerts", "daily"}:
            return jsonify({"ok": False, "error": "Modo no soportado"}), 404

        try:
            config = Config.from_env()
            if not _is_authorized(config.cron_secret):
                return jsonify({"ok": False, "error": "No autorizado"}), 401

            result = run_bot(mode, config)
            return jsonify({"ok": True, **result})
        except (ConfigError, RuntimeError, ValueError) as exc:
            LOGGER.exception("Error ejecutando endpoint cron")
            return jsonify({"ok": False, "error": str(exc)}), 500

    return app


def _is_authorized(expected_secret: str | None) -> bool:
    if not expected_secret:
        LOGGER.error("CRON_SECRET no esta configurado")
        return False

    provided_secret = request.args.get("token") or request.headers.get("X-Cron-Secret")
    if not provided_secret:
        return False

    return hmac.compare_digest(provided_secret, expected_secret)


app = create_app()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
