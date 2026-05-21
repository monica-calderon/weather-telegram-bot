from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


class StateStore:
    def __init__(self, path: str | Path = ".state/notified_alerts.json") -> None:
        self.path = Path(path)
        self._data = self._load()

    def has_been_notified(self, key: str) -> bool:
        return key in self._data

    def mark_notified(self, key: str) -> None:
        self._data[key] = datetime.now(timezone.utc).isoformat()
        self._save()

    def cleanup_old_entries(self, days: int = 3) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cleaned = {}
        for key, value in self._data.items():
            try:
                saved_at = datetime.fromisoformat(value)
            except ValueError:
                continue
            if saved_at >= cutoff:
                cleaned[key] = value
        self._data = cleaned
        self._save()

    def _load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
