from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from google.oauth2.credentials import Credentials as UserCredentials
from google.oauth2 import service_account
from googleapiclient.discovery import build


class GoogleCalendarClientError(RuntimeError):
    """Raised when Google Calendar cannot be queried successfully."""


class GoogleCalendarClient:
    SCOPES = ("https://www.googleapis.com/auth/calendar.readonly",)

    def __init__(
        self,
        service_account_json: str | None = None,
        *,
        oauth_client_json: str | None = None,
        oauth_refresh_token: str | None = None,
    ) -> None:
        self.service = self._build_service(
            service_account_json,
            oauth_client_json=oauth_client_json,
            oauth_refresh_token=oauth_refresh_token,
        )

    @classmethod
    def from_service(cls, service: Any) -> "GoogleCalendarClient":
        client = cls.__new__(cls)
        client.service = service
        return client

    def get_events_remaining_today(
        self,
        calendar_ids: list[str] | tuple[str, ...],
        start: datetime,
        end: datetime,
        max_results: int = 10,
        calendar_names_by_id: dict[str, str] | None = None,
    ) -> list[dict[str, str]]:
        events: list[dict[str, str]] = []
        for calendar_id in calendar_ids:
            try:
                configured_name = (calendar_names_by_id or {}).get(calendar_id)
                calendar_name = self._get_calendar_name(calendar_id, configured_name)
                response = (
                    self.service.events()
                    .list(
                        calendarId=calendar_id,
                        timeMin=start.isoformat(),
                        timeMax=end.isoformat(),
                        singleEvents=True,
                        orderBy="startTime",
                        maxResults=max_results,
                    )
                    .execute()
                )
            except Exception as exc:  # noqa: BLE001 - Google client raises broad errors.
                raise GoogleCalendarClientError(
                    f"No se pudieron obtener eventos de Google Calendar: {exc}"
                ) from exc

            for item in response.get("items", []):
                event = normalize_calendar_event(item, calendar_name=calendar_name)
                if event:
                    events.append(event)

        return sorted(events, key=lambda event: event["sort_key"])[:max_results]

    def _get_calendar_name(self, calendar_id: str, configured_name: str | None = None) -> str:
        if configured_name and configured_name.strip():
            return configured_name.strip()

        summary = self._get_calendar_summary_from_resource("calendarList", calendar_id)
        if summary:
            return summary

        summary = self._get_calendar_summary_from_resource("calendars", calendar_id)
        if summary:
            return summary

        return ""

    def _get_calendar_summary_from_resource(self, resource_name: str, calendar_id: str) -> str:
        try:
            resource = getattr(self.service, resource_name)()
            calendar = resource.get(calendarId=calendar_id).execute()
        except Exception:  # noqa: BLE001 - fallback to ID if metadata cannot be read.
            return ""
        summary = calendar.get("summary") if isinstance(calendar, dict) else None
        return str(summary).strip() if summary else ""

    def _build_service(
        self,
        service_account_json: str | None,
        *,
        oauth_client_json: str | None = None,
        oauth_refresh_token: str | None = None,
    ) -> Any:
        try:
            if oauth_client_json and oauth_refresh_token:
                credentials = _build_user_credentials(
                    oauth_client_json, oauth_refresh_token, self.SCOPES
                )
                return build("calendar", "v3", credentials=credentials, cache_discovery=False)

            if not service_account_json:
                raise ValueError(
                    "configura GOOGLE_SERVICE_ACCOUNT_JSON o "
                    "GOOGLE_OAUTH_CLIENT_JSON y GOOGLE_OAUTH_REFRESH_TOKEN"
                )

            info = json.loads(service_account_json)
            credentials = service_account.Credentials.from_service_account_info(
                info, scopes=self.SCOPES
            )
            return build("calendar", "v3", credentials=credentials, cache_discovery=False)
        except Exception as exc:  # noqa: BLE001 - credential parsing/build can vary.
            raise GoogleCalendarClientError(
                f"No se pudo inicializar Google Calendar: {exc}"
            ) from exc


def _build_user_credentials(
    oauth_client_json: str, refresh_token: str, scopes: tuple[str, ...]
) -> UserCredentials:
    info = json.loads(oauth_client_json)
    client_info = info.get("installed") or info.get("web") or info
    client_id = client_info.get("client_id")
    client_secret = client_info.get("client_secret")
    token_uri = client_info.get("token_uri", "https://oauth2.googleapis.com/token")

    missing = [
        name
        for name, value in {
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
        }.items()
        if not value
    ]
    if missing:
        raise ValueError("faltan campos OAuth: " + ", ".join(missing))

    return UserCredentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=token_uri,
        client_id=client_id,
        client_secret=client_secret,
        scopes=scopes,
    )


def normalize_calendar_event(
    item: dict[str, Any], *, calendar_name: str | None = None
) -> dict[str, str] | None:
    if not isinstance(item, dict):
        return None
    start = item.get("start")
    if not isinstance(start, dict):
        return None

    title = str(item.get("summary") or "Sin titulo").strip() or "Sin titulo"
    if start.get("date"):
        date = str(start["date"])
        return {
            "time": "Todo el dia",
            "title": title,
            "calendar": calendar_name or "",
            "sort_key": f"{date}T00:00:00",
        }

    date_time = start.get("dateTime")
    if not date_time:
        return None
    text = str(date_time)
    return {
        "time": _format_event_time(text),
        "title": title,
        "calendar": calendar_name or "",
        "sort_key": text,
    }


def _format_event_time(value: str) -> str:
    if "T" not in value:
        return value[:5]
    return value.split("T", 1)[1][:5]
