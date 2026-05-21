import io
from zipfile import ZIP_DEFLATED, ZipFile

from src.main import normalize_official_alerts


def test_normalize_official_alerts_from_cap_xml():
    cap_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
      <identifier>aemet-123</identifier>
      <info>
        <event>Tormentas</event>
        <onset>2026-05-21T19:00:00+02:00</onset>
        <parameter>
          <valueName>Nivel</valueName>
          <value>naranja</value>
        </parameter>
      </info>
    </alert>
    """

    alerts = normalize_official_alerts(cap_xml)

    assert alerts == [
        {
            "level": "naranja",
            "event": "Tormentas",
            "onset": "2026-05-21T19:00:00+02:00",
            "dedupe_key": "aemet-123-naranja-Tormentas-2026-05-21T19:00:00+02:00",
        }
    ]


def test_normalize_official_alerts_ignores_unparseable_text():
    assert normalize_official_alerts("Sin avisos disponibles") == []


def test_normalize_official_alerts_from_cap_zip():
    cap_xml = """<?xml version="1.0" encoding="UTF-8"?>
    <alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
      <identifier>aemet-456</identifier>
      <info>
        <event>Viento</event>
        <onset>2026-05-21T21:00:00+02:00</onset>
        <severity>Moderate</severity>
      </info>
    </alert>
    """
    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("avisos/aemet.xml", cap_xml)

    alerts = normalize_official_alerts(buffer.getvalue())

    assert alerts == [
        {
            "level": "amarillo",
            "event": "Viento",
            "onset": "2026-05-21T21:00:00+02:00",
            "dedupe_key": "aemet-456-amarillo-Viento-2026-05-21T21:00:00+02:00",
        }
    ]
