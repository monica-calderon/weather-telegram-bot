from __future__ import annotations

import requests


class TelegramClientError(RuntimeError):
    """Raised when Telegram rejects or cannot receive a message."""


class TelegramClient:
    def __init__(self, bot_token: str, chat_id: str, timeout: int = 20) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.timeout = timeout
        self.session = requests.Session()

    def send_message(self, text: str) -> None:
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            raise TelegramClientError(f"Error enviando mensaje a Telegram: {exc}") from exc
        except ValueError as exc:
            raise TelegramClientError("Telegram no devolvio JSON valido") from exc

        if not data.get("ok"):
            description = data.get("description", "sin detalle")
            raise TelegramClientError(f"Telegram rechazo el mensaje: {description}")
