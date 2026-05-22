from src.aemet_client import AemetClient


class FakeResponse:
    status_code = 200
    content = b"{}"

    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeSession:
    def __init__(self):
        self.calls = []

    def get(self, url, headers=None, params=None, timeout=None):
        self.calls.append(
            {"url": url, "headers": headers, "params": params, "timeout": timeout}
        )
        if len(self.calls) == 1:
            return FakeResponse({"datos": "https://example.test/data.json"})
        return FakeResponse([{"ok": True}])


def test_aemet_metadata_request_sends_api_key_as_header_and_query_param():
    client = AemetClient("secret-key")
    fake_session = FakeSession()
    client.session = fake_session

    result = client.get_municipality_forecast("28005")

    assert result == [{"ok": True}]
    assert fake_session.calls[0]["headers"] == {"api_key": "secret-key"}
    assert fake_session.calls[0]["params"] == {"api_key": "secret-key"}


def test_current_observations_can_use_specific_station():
    client = AemetClient("secret-key")
    fake_session = FakeSession()
    client.session = fake_session

    client.get_current_observations("3195")

    assert (
        fake_session.calls[0]["url"]
        == "https://opendata.aemet.es/opendata/api/observacion/convencional/datos/estacion/3195"
    )
