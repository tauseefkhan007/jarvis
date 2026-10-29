"""Local reminder management for Jarvis."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from ...debug import debug_log
from ...utils.redact import redact
from ..base import Tool, ToolContext
from ..types import ToolExecutionResult


class RemindersTool(Tool):
    """Create, list, complete, or delete a local reminder."""

    @property
    def name(self) -> str:
        return "reminders"

    @property
    def description(self) -> str:
        return (
            "Create a local reminder for a specific future date and time, list pending reminders, "
            "mark a reminder complete, or delete one. Use for requests such as 'remind me to call "
            "Sam tomorrow at three' or 'what reminders do I have?'. Convert the requested time "
            "to an ISO 8601 date-time with an explicit timezone offset using the user's local-time "
            "context. Reminders are stored on this device and trigger a desktop notification while "
            "Jarvis is running."
        )

    @property
    def inputSchema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "list", "complete", "delete"],
                    "description": "The reminder operation to perform.",
                },
                "text": {
                    "type": "string",
                    "description": "The short reminder content, required for create.",
                },
                "due_at": {
                    "type": "string",
                    "format": "date-time",
                    "description": (
                        "Future ISO 8601 date-time with an explicit timezone offset, "
                        "required for create."
                    ),
                },
                "id": {
                    "type": "string",
                    "description": "The reminder ID, required for complete or delete.",
                },
            },
            "required": ["action"],
        }

    def run(self, args: Optional[Dict[str, Any]], context: ToolContext) -> ToolExecutionResult:
        context.user_print("⏰ Managing reminders...")
        if not isinstance(args, dict):
            return self._invalid("Reminder arguments must be an object.")
        action = args.get("action")
        try:
            if action == "create":
                return self._create(args, context)
            if action == "list":
                return self._list(context)
            if action == "complete":
                return self._complete(args, context)
            if action == "delete":
                return self._delete(args, context)
            return self._invalid("Choose create, list, complete, or delete for reminders.")
        except Exception as error:
            debug_log(f"reminders: operation failed ({type(error).__name__})", "reminders")
            context.user_print("⚠️ The reminder could not be saved.")
            return ToolExecutionResult(success=False, reply_text="The reminder could not be saved.")

    def _create(self, args: dict, context: ToolContext) -> ToolExecutionResult:
        text = args.get("text")
        due_at = args.get("due_at")
        if not isinstance(text, str) or not text.strip():
            return self._invalid("A reminder needs some text.")
        if not isinstance(due_at, str):
            return self._invalid("A reminder needs a date and time with a timezone.")
        try:
            due = datetime.fromisoformat(due_at.replace("Z", "+00:00"))
            if due.tzinfo is None or due.utcoffset() is None:
                raise ValueError("timezone required")
            due = due.astimezone(timezone.utc)
        except (ValueError, OverflowError):
            return self._invalid("Use a valid ISO date-time with an explicit timezone offset.")
        if due <= datetime.now(timezone.utc):
            return self._invalid("The reminder time must be in the future.")

        safe_text = redact(text.strip())[:500]
        if not safe_text.strip():
            return self._invalid("A reminder needs some text.")
        stored_due = due.isoformat(timespec="microseconds")
        reminder_id = context.db.create_reminder(safe_text, stored_due)
        debug_log(f"reminder created: {reminder_id}", "reminders")
        context.user_print("✅ Reminder saved.")
        return ToolExecutionResult(
            success=True,
            reply_text=f"Reminder saved for {due.isoformat(timespec='minutes')}: {safe_text}",
            resource_references=({"type": "reminder", "id": reminder_id, "label": safe_text},),
        )

    def _list(self, context: ToolContext) -> ToolExecutionResult:
        reminders = context.db.list_reminders()
        if not reminders:
            context.user_print("✅ No pending reminders.")
            return ToolExecutionResult(success=True, reply_text="You have no pending reminders.")
        lines = []
        references = []
        for item in reminders:
            due = datetime.fromisoformat(item["due_at"].replace("Z", "+00:00"))
            local_due = due.astimezone().isoformat(timespec="minutes")
            lines.append(f"- {item['id']}: {item['text']} (due {local_due})")
            references.append({"type": "reminder", "id": item["id"], "label": item["text"]})
        context.user_print(f"✅ Found {len(reminders)} pending reminder(s).")
        return ToolExecutionResult(
            success=True,
            reply_text="Pending reminders:\n" + "\n".join(lines),
            resource_references=tuple(references),
        )

    def _complete(self, args: dict, context: ToolContext) -> ToolExecutionResult:
        reminder_id = args.get("id")
        if not isinstance(reminder_id, str) or not reminder_id.strip():
            return self._invalid("Choose a reminder ID to complete.")
        if not context.db.complete_reminder(reminder_id.strip()):
            return self._invalid("That pending reminder could not be found.")
        debug_log(f"reminder completed: {reminder_id.strip()}", "reminders")
        context.user_print("✅ Reminder completed.")
        return ToolExecutionResult(
            success=True,
            reply_text=f"Reminder {reminder_id.strip()} completed.",
        )

    def _delete(self, args: dict, context: ToolContext) -> ToolExecutionResult:
        reminder_id = args.get("id")
        if not isinstance(reminder_id, str) or not reminder_id.strip():
            return self._invalid("Choose a reminder ID to delete.")
        if not context.db.delete_reminder(reminder_id.strip()):
            return self._invalid("That reminder could not be found.")
        debug_log(f"reminder deleted: {reminder_id.strip()}", "reminders")
        context.user_print("✅ Reminder deleted.")
        return ToolExecutionResult(
            success=True,
            reply_text=f"Reminder {reminder_id.strip()} deleted.",
        )

    @staticmethod
    def _invalid(message: str) -> ToolExecutionResult:
        return ToolExecutionResult(success=False, reply_text=message, error_message=message)
