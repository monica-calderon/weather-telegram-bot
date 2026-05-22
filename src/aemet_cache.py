from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class AemetCache:
    def __init__(self, path: str | Path = ".state/aemet_cache.json") -> None:
        self.path = Path(path)
        self._data = self._load()

    def get(
        self,
        key: str,
        *,
        max_age: timedelta | None = None,
        cache_date: str | None = None,
    ) -> Any | None:
        entry = self._data.get(key)
        if not isinstance(entry, dict) or "value" not in entry:
            return None
        if cache_date is not None and entry.get("cache_date") != cache_date:
            return None
        if max_age is not None and self._is_expired(entry, max_age):
            return None
        return entry["value"]

    def get_stale(self, key: str) -> Any | None:
        entry = self._data.get(key)
        if not isinstance(entry, dict):
            return None
        return entry.get("value")

    def set(self, key: str, value: Any, *, cache_date: str | None = None) -> None:
        self._data[key] = {
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "value": value,
        }
        if cache_date is not None:
            self._data[key]["cache_date"] = cache_date
        self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _is_expired(self, entry: dict[str, Any], max_age: timedelta) -> bool:
        fetched_at = entry.get("fetched_at")
        if not isinstance(fetched_at, str):
            return True
        try:
            fetched_datetime = datetime.fromisoformat(fetched_at)
        except ValueError:
            return True
        if fetched_datetime.tzinfo is None:
            fetched_datetime = fetched_datetime.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) - fetched_datetime > max_age
