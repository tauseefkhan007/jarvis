"""Delivery helpers for locally stored reminders."""

from .debug import debug_log


def deliver_due_reminders(db, emit) -> int:
    """Claim due reminders, emit each one once, and return the number delivered."""
    try:
        due = db.claim_due_reminders()
    except Exception as exc:
        debug_log(f"reminder due check failed ({type(exc).__name__})", "reminders")
        return 0
    for reminder in due:
        emit({"id": reminder["id"], "text": reminder["text"], "due_at": reminder["due_at"]})
    if due:
        debug_log(f"delivered {len(due)} due reminder(s)", "reminders")
    return len(due)
