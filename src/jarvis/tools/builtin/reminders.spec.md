# Local reminders tool

The `reminders` builtin creates and manages reminders in the local Jarvis
SQLite database. It supports `create`, `list`, `complete`, and `delete`.
Creating a reminder requires non-empty text and a future ISO 8601 timestamp
with an explicit timezone offset. The tool converts the timestamp to UTC and
redacts and bounds reminder text before persistence. Ambiguous or past times
are rejected instead of guessed.

Pending reminders are ordered by their due instant. Completing a reminder
keeps its record as completed; deleting removes it. A reminder is private to
the configured local database and is not sent to an external service.

The daemon checks for due, unnotified reminders once per second. The database
claims due records atomically by setting `notified_at`, so concurrent pollers
and later polling do not emit a reminder twice. If Jarvis was stopped when a
reminder became due, the next daemon run delivers it. The daemon publishes a
redacted reminder event through its existing stdout transport. The desktop app
shows a native system-tray notification in bundled and subprocess modes. A
standalone daemon emits the event on stdout without importing desktop code.
Notifications require Jarvis to be running; there is no background OS service.
