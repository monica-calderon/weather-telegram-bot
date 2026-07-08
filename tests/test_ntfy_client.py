from src.ntfy_client import NtfyClient, _html_to_text


def test_ntfy_client_posts_plain_text_message_with_headers(monkeypatch):
    monkeypatch.setattr("src.ntfy_client.uuid.uuid4", lambda: FakeUuid("abc123"))
    client = NtfyClient(
        "weather-topic",
        server="https://ntfy.example.com",
        token="secret",
        priority="high",
        tags=("sun", "umbrella"),
    )
    session = FakeSession()
    client.session = session

    client.send_message("<b>Resumen diario</b>\nLluvia &amp; viento")

    assert session.posts == [
        {
            "url": "https://ntfy.example.com/weather-topic/weather-abc123",
            "data": "Resumen diario\nLluvia & viento".encode("utf-8"),
            "headers": {
                "Title": "Tiempo",
                "Actions": "http, Eliminar, "
                "https://ntfy.example.com/weather-topic/weather-abc123, "
                "method=DELETE, clear=true, "
                "headers.Authorization=Bearer secret",
                "Priority": "high",
                "Tags": "sun,umbrella",
                "Authorization": "Bearer secret",
            },
            "auth": None,
            "timeout": 20,
        }
    ]


def test_html_to_text_removes_telegram_markup():
    assert _html_to_text("Hola <b>mundo</b> &amp; cielo") == "Hola mundo & cielo"


def test_delete_action_uses_basic_auth_when_configured(monkeypatch):
    monkeypatch.setattr("src.ntfy_client.uuid.uuid4", lambda: FakeUuid("def456"))
    client = NtfyClient(
        "weather-topic",
        server="https://ntfy.example.com",
        username="user",
        password="pass",
    )
    session = FakeSession()
    client.session = session

    client.send_message("Hola")

    assert session.posts[0]["headers"]["Actions"] == (
        "http, Eliminar, "
        "https://ntfy.example.com/weather-topic/weather-def456, "
        "method=DELETE, clear=true, "
        "headers.Authorization=Basic dXNlcjpwYXNz"
    )


class FakeSession:
    def __init__(self):
        self.posts = []

    def post(self, url, data, headers, auth, timeout):
        self.posts.append(
            {
                "url": url,
                "data": data,
                "headers": headers,
                "auth": auth,
                "timeout": timeout,
            }
        )
        return FakeResponse()


class FakeResponse:
    def raise_for_status(self):
        return None


class FakeUuid:
    def __init__(self, value):
        self.hex = value
