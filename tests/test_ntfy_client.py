from src.ntfy_client import NtfyClient, _html_to_text


def test_ntfy_client_posts_plain_text_message_with_headers():
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
            "url": "https://ntfy.example.com/weather-topic",
            "data": "Resumen diario\nLluvia & viento".encode("utf-8"),
            "headers": {
                "Title": "Tiempo",
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
