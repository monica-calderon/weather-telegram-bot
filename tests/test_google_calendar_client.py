from datetime import datetime
from zoneinfo import ZoneInfo

from src.google_calendar_client import GoogleCalendarClient, normalize_calendar_event


def test_normalize_calendar_event_with_time():
    event = normalize_calendar_event(
        {
            "summary": "Dentista",
            "start": {"dateTime": "2026-05-27T18:30:00+02:00"},
        },
        calendar_name="Bubu",
    )

    assert event == {
        "time": "18:30",
        "title": "Dentista",
        "calendar": "Bubu",
        "sort_key": "2026-05-27T18:30:00+02:00",
    }


def test_normalize_calendar_event_all_day_and_missing_title():
    event = normalize_calendar_event({"start": {"date": "2026-05-27"}})

    assert event == {
        "time": "Todo el dia",
        "title": "Sin titulo",
        "calendar": "",
        "sort_key": "2026-05-27T00:00:00",
    }


def test_google_calendar_client_combines_and_sorts_multiple_calendars():
    service = FakeCalendarService(
        {
            "calendar-1": [
                {"summary": "Tarde", "start": {"dateTime": "2026-05-27T19:00:00+02:00"}},
            ],
            "calendar-2": [
                {"summary": "Antes", "start": {"dateTime": "2026-05-27T16:00:00+02:00"}},
            ],
        }
    )
    client = GoogleCalendarClient.from_service(service)

    events = client.get_events_remaining_today(
        ("calendar-1", "calendar-2"),
        datetime(2026, 5, 27, 15, 0, tzinfo=ZoneInfo("Europe/Madrid")),
        datetime(2026, 5, 27, 23, 59, tzinfo=ZoneInfo("Europe/Madrid")),
        max_results=10,
    )

    assert [event["title"] for event in events] == ["Antes", "Tarde"]
    assert [event["calendar"] for event in events] == ["Bubu", "Trabajo"]


class FakeCalendarService:
    def __init__(self, events_by_calendar):
        self.events_by_calendar = events_by_calendar
        self.requested_calendar_id = None

    def events(self):
        return self

    def calendarList(self):
        return self

    def get(self, **kwargs):
        self.requested_calendar_id = kwargs["calendarId"]
        return self

    def list(self, **kwargs):
        self.requested_calendar_id = kwargs["calendarId"]
        return self

    def execute(self):
        if self.requested_calendar_id == "calendar-1":
            return {"summary": "Trabajo", "items": self.events_by_calendar[self.requested_calendar_id]}
        if self.requested_calendar_id == "calendar-2":
            return {"summary": "Bubu", "items": self.events_by_calendar[self.requested_calendar_id]}
        return {"items": self.events_by_calendar[self.requested_calendar_id]}
