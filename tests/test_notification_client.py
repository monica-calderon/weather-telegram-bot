from src.config import Config
from src.notification_client import NotificationClient


def test_notification_client_sends_to_telegram_and_ntfy(monkeypatch):
    sent_messages = []

    class FakeTelegramClient:
        def __init__(self, bot_token, chat_id):
            self.bot_token = bot_token
            self.chat_id = chat_id

        def send_message(self, text):
            sent_messages.append(("telegram", text))

    class FakeNtfyClient:
        def __init__(self, topic, **kwargs):
            self.topic = topic
            self.kwargs = kwargs

        def send_message(self, text):
            sent_messages.append(("ntfy", text))

    monkeypatch.setattr("src.notification_client.TelegramClient", FakeTelegramClient)
    monkeypatch.setattr("src.notification_client.NtfyClient", FakeNtfyClient)

    client = NotificationClient(
        Config(
            aemet_api_key="aemet",
            municipio_id="28005",
            municipio_nombre="Alcala",
            telegram_bot_token="telegram",
            telegram_chat_id="chat",
            notification_methods=("telegram", "ntfy"),
            ntfy_topic="weather-topic",
        )
    )

    client.send_message("Hola")

    assert sent_messages == [("telegram", "Hola"), ("ntfy", "Hola")]
