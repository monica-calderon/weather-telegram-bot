from datetime import datetime, timedelta, timezone

from src.state_store import StateStore


def test_state_store_marks_and_reads_notified_key(tmp_path):
    state_path = tmp_path / "notified_alerts.json"
    store = StateStore(state_path)

    assert not store.has_been_notified("rain-2026-05-21")

    store.mark_notified("rain-2026-05-21")
    reloaded = StateStore(state_path)

    assert reloaded.has_been_notified("rain-2026-05-21")


def test_state_store_cleanup_removes_old_entries(tmp_path):
    state_path = tmp_path / "notified_alerts.json"
    old_date = datetime.now(timezone.utc) - timedelta(days=10)
    recent_date = datetime.now(timezone.utc)
    state_path.write_text(
        (
            "{"
            f'"old-alert": "{old_date.isoformat()}",'
            f'"recent-alert": "{recent_date.isoformat()}"'
            "}"
        ),
        encoding="utf-8",
    )

    store = StateStore(state_path)
    store.cleanup_old_entries(days=3)

    assert not store.has_been_notified("old-alert")
    assert store.has_been_notified("recent-alert")
