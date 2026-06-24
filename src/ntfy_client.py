from __future__ import annotations

import re
import uuid
from html import unescape

import requests


class NtfyClientError(RuntimeError):
    """Raised when Ntfy rejects or cannot receive a message."""


class NtfyClient:
    def __init__(
        self,
        topic: str,
        *,
        server: str = "https://ntfy.sh",
        token: str | None = None,
        username: str | None = None,
        password: str | None = None,
        priority: str | None = None,
        tags: tuple[str, ...] = (),
        timeout: int = 20,
    ) -> None:
        self.topic = topic
        self.server = server
        self.token = token
        self.username = username
        self.password = password
        self.priority = priority
        self.tags = tags
        self.timeout = timeout
        self.session = requests.Session()

    def send_message(self, text: str, *, title: str = "Tiempo") -> None:
        sequence_id = f"weather-{uuid.uuid4().hex}"
        headers = {
            "Title": title,
            "X-Sequence-ID": sequence_id,
            "Actions": self._delete_action(sequence_id),
        }
        if self.priority:
            headers["Priority"] = self.priority
        if self.tags:
            headers["Tags"] = ",".join(self.tags)
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        auth = None
        if not self.token and self.username and self.password:
            auth = (self.username, self.password)

        try:
            response = self.session.post(
                self._topic_url(),
                data=_html_to_text(text).encode("utf-8"),
                headers=headers,
                auth=auth,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise NtfyClientError(f"Error enviando mensaje a Ntfy: {exc}") from exc

    def _topic_url(self) -> str:
        if self.topic.startswith(("http://", "https://")):
            return self.topic
        return f"{self.server.rstrip('/')}/{self.topic.lstrip('/')}"

    def _delete_action(self, sequence_id: str) -> str:
        delete_url = f"{self._topic_url().rstrip('/')}/{sequence_id}/delete"
        return f"http, Eliminar, {delete_url}, method=GET, clear=true"


def _html_to_text(text: str) -> str:
    without_tags = re.sub(r"<[^>]+>", "", text)
    return unescape(without_tags)
