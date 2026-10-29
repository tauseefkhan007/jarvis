"""Reminder delivery is persisted exactly once across daemon polling."""

from datetime import datetime, timedelta, timezone

import pytest

from jarvis.memory.db import Database
from jarvis.reminder_service import deliver_due_reminders

pytestmark = pytest.mark.unit


def test_due_reminders_are_emitted_once_and_marked_delivered():
    db = Database(":memory:", sqlite_vss_path=None)
    try:
        reminder_id = db.create_reminder(
            "Review the draft",
            (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
        )

        emitted = []
        assert deliver_due_reminders(db, emitted.append) == 1
        assert emitted == [{"id": reminder_id, "text": "Review the draft", "due_at": db.list_reminders()[0]["due_at"]}]

        assert deliver_due_reminders(db, emitted.append) == 0
        assert len(emitted) == 1
    finally:
        db.close()


def test_future_reminder_is_not_emitted():
    db = Database(":memory:", sqlite_vss_path=None)
    try:
        db.create_reminder(
            "Not yet",
            (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        )
        emitted = []
        assert deliver_due_reminders(db, emitted.append) == 0
        assert emitted == []
    finally:
        db.close()


def test_due_reminder_survives_a_restart_until_it_is_delivered(tmp_path):
    path = str(tmp_path / "jarvis.db")
    first = Database(path, sqlite_vss_path=None)
    reminder_id = first.create_reminder(
        "Restart-safe reminder",
        (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
    )
    first.close()

    restarted = Database(path, sqlite_vss_path=None)
    try:
        emitted = []
        assert deliver_due_reminders(restarted, emitted.append) == 1
        assert emitted[0]["id"] == reminder_id
        assert emitted[0]["text"] == "Restart-safe reminder"
    finally:
        restarted.close()
