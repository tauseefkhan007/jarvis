"""Tests for local reminders."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from jarvis.memory.db import Database
from jarvis.tools.builtin.reminders import RemindersTool
from jarvis.tools.registry import BUILTIN_TOOLS

pytestmark = pytest.mark.unit


@pytest.fixture
def reminder_context():
    db = Database(":memory:", sqlite_vss_path=None)
    context = SimpleNamespace(db=db, redacted_text="", user_print=lambda *_: None)
    yield context
    db.close()


def test_reminder_tool_is_registered():
    assert "reminders" in BUILTIN_TOOLS
    assert isinstance(BUILTIN_TOOLS["reminders"], RemindersTool)


def test_create_list_complete_and_delete_reminders(reminder_context):
    tool = RemindersTool()
    due_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    created = tool.run({"action": "create", "text": "Call Sam", "due_at": due_at}, reminder_context)
    assert created.success
    reminder_id = created.resource_references[0]["id"]

    listed = tool.run({"action": "list"}, reminder_context)
    assert listed.success and "Call Sam" in listed.reply_text
    assert reminder_id in listed.reply_text

    completed = tool.run({"action": "complete", "id": reminder_id}, reminder_context)
    assert completed.success
    assert not reminder_context.db.list_reminders()
    assert reminder_context.db.list_reminders(include_completed=True)[0]["status"] == "completed"

    second = tool.run(
        {"action": "create", "text": "Send report", "due_at": due_at},
        reminder_context,
    )
    second_id = second.resource_references[0]["id"]
    deleted = tool.run({"action": "delete", "id": second_id}, reminder_context)
    assert deleted.success
    remaining = reminder_context.db.list_reminders(include_completed=True)
    assert len(remaining) == 1 and remaining[0]["id"] == reminder_id


def test_create_rejects_naive_and_past_timestamps(reminder_context):
    tool = RemindersTool()
    naive = (datetime.now() + timedelta(hours=1)).isoformat()
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

    assert not tool.run({"action": "create", "text": "A", "due_at": naive}, reminder_context).success
    assert not tool.run({"action": "create", "text": "A", "due_at": past}, reminder_context).success
    assert reminder_context.db.list_reminders(include_completed=True) == []


def test_reminder_text_is_redacted_before_persistence(reminder_context, monkeypatch):
    from jarvis.tools.builtin import reminders

    monkeypatch.setattr(reminders, "redact", lambda text: "[redacted]")
    due_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    result = RemindersTool().run(
        {"action": "create", "text": "Sensitive detail", "due_at": due_at},
        reminder_context,
    )
    assert result.success
    assert reminder_context.db.list_reminders()[0]["text"] == "[redacted]"
