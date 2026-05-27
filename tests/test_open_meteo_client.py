from src.open_meteo_client import _current_temperature_from_payload


def test_current_temperature_from_payload_reads_open_meteo_current_value():
    assert _current_temperature_from_payload({"current": {"temperature_2m": 21.7}}) == 21.7


def test_current_temperature_from_payload_returns_none_without_value():
    assert _current_temperature_from_payload({"current": {}}) is None
