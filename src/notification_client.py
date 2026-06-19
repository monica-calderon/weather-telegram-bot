from __future__ import annotations

import logging

from src.config import Config
from src.ntfy_client import NtfyClient
from src.telegram_client import TelegramClient

LOGGER = logging.getLogger(__name__)


class NotificationClientError(RuntimeError):
    """Raised when a configured notification channel fails."""


class NotificationClient:
    def __init__(self, config: Config) -> None:
        self.channels = []
        if "telegram" in config.notification_methods:
            self.channels.append(
                (
                    "Telegram",
                    TelegramClient(
                        config.telegram_bot_token or "",
                        config.telegram_chat_id or "",
                    ),
                )
            )
        if "ntfy" in config.notification_methods:
            self.channels.append(
                (
                    "Ntfy",
                    NtfyClient(
                        config.ntfy_topic or "",
                        server=config.ntfy_server,
                        token=config.ntfy_token,
                        username=config.ntfy_username,
                        password=config.ntfy_password,
                        priority=config.ntfy_priority,
                        tags=config.ntfy_tags,
                    ),
                )
            )
        LOGGER.info(
            "Canales de notificacion configurados: %s",
            ", ".join(channel_name for channel_name, _ in self.channels) or "ninguno",
        )

    def send_message(self, text: str) -> None:
        errors = []
        for channel_name, client in self.channels:
            try:
                client.send_message(text)
                LOGGER.info("Notificacion enviada por %s.", channel_name)
            except Exception as exc:  # noqa: BLE001 - try every configured channel.
                LOGGER.warning("No se pudo enviar por %s: %s", channel_name, exc)
                errors.append(f"{channel_name}: {exc}")

        if errors:
            raise NotificationClientError(
                "Fallaron uno o mas canales de notificacion: " + "; ".join(errors)
            )
