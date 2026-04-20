"""
NLP Calendar Scheduler — Aria's intelligent event planner.

Conversation flow (two turns):
  Turn 1  User: "schedule a call Monday to brainstorm the app"
          Aria: asks 2 targeted probe questions (goal, duration/attendees)
  Turn 2  User: answers the probe questions
          Aria: confirms the event, stores it, generates an agenda + prep notes

Background timer (every 60 s in main.py):
  - 15-minute warning notification
  - At-start notification with agenda sent to chat panel
"""

import sqlite3
import os
import threading
from datetime import datetime, timedelta

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import log

# ── DB path (shared companion.db) ─────────────────────────────────────────────

_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "memory", "companion.db"
)
_local = threading.local()


def _conn() -> sqlite3.Connection:
    if not getattr(_local, "conn", None):
        os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
        _local.conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


# ── Schema init ───────────────────────────────────────────────────────────────

def init():
    """Create the calendar_events table if it does not exist."""
    with _conn() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS calendar_events (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            title         TEXT    NOT NULL,
            description   TEXT    DEFAULT '',
            scheduled_dt  TEXT    NOT NULL,
            duration_mins INTEGER DEFAULT 60,
            attendees     TEXT    DEFAULT 'Solo',
            agenda        TEXT    DEFAULT '',
            prep_notes    TEXT    DEFAULT '',
            created_ts    TEXT    NOT NULL,
            notified_15   INTEGER DEFAULT 0,
            notified_now  INTEGER DEFAULT 0,
            status        TEXT    DEFAULT 'scheduled'
        )
        """)
    log.info("Scheduler: calendar_events table ready")


# ── CRUD ──────────────────────────────────────────────────────────────────────

def save_event(title: str, description: str, scheduled_dt: str,
               duration_mins: int, attendees: str,
               agenda: str, prep_notes: str) -> int:
    """Persist an event. Returns its new row id."""
    now = datetime.now().isoformat()
    try:
        with _conn() as c:
            cur = c.execute(
                """INSERT INTO calendar_events
                   (title, description, scheduled_dt, duration_mins,
                    attendees, agenda, prep_notes, created_ts)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (title, description, scheduled_dt, duration_mins,
                 attendees, agenda, prep_notes, now)
            )
        log.info(f"Scheduler: event saved | id={cur.lastrowid} | dt={scheduled_dt} | title={title}")
        return cur.lastrowid
    except Exception as e:
        log.error(f"Scheduler save_event: {e}")
        return -1


def get_upcoming_events(days: int = 7) -> list[dict]:
    """Return scheduled events in the next N days."""
    cutoff = (datetime.now() + timedelta(days=days)).isoformat()
    now    = datetime.now().isoformat()
    try:
        with _conn() as c:
            rows = c.execute(
                """SELECT * FROM calendar_events
                   WHERE scheduled_dt >= ? AND scheduled_dt <= ?
                   AND status = 'scheduled'
                   ORDER BY scheduled_dt""",
                (now, cutoff)
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        log.error(f"Scheduler get_upcoming_events: {e}")
        return []


def get_due_events() -> dict:
    """
    Return two lists:
      warning_15 — events starting in 0–15 minutes, not yet 15-min-notified
      starting   — events starting in 0–1 minute,  not yet start-notified
    Called every 60 s by the main timer.
    """
    now      = datetime.now()
    in_15    = (now + timedelta(minutes=15)).isoformat()
    in_1     = (now + timedelta(minutes=1)).isoformat()
    now_iso  = now.isoformat()
    result   = {"warning_15": [], "starting": []}
    try:
        with _conn() as c:
            rows = c.execute(
                """SELECT * FROM calendar_events
                   WHERE scheduled_dt BETWEEN ? AND ?
                   AND notified_15 = 0 AND status = 'scheduled'""",
                (now_iso, in_15)
            ).fetchall()
            result["warning_15"] = [dict(r) for r in rows]

            rows = c.execute(
                """SELECT * FROM calendar_events
                   WHERE scheduled_dt <= ? AND notified_now = 0
                   AND status = 'scheduled'""",
                (in_1,)
            ).fetchall()
            result["starting"] = [dict(r) for r in rows]
    except Exception as e:
        log.error(f"Scheduler get_due_events: {e}")
    return result


def mark_notified_15(event_id: int):
    try:
        with _conn() as c:
            c.execute("UPDATE calendar_events SET notified_15=1 WHERE id=?", (event_id,))
    except Exception as e:
        log.error(f"Scheduler mark_notified_15: {e}")


def mark_notified_now(event_id: int):
    try:
        with _conn() as c:
            c.execute(
                "UPDATE calendar_events SET notified_now=1, status='notified' WHERE id=?",
                (event_id,)
            )
    except Exception as e:
        log.error(f"Scheduler mark_notified_now: {e}")


def delete_event(event_id: int):
    try:
        with _conn() as c:
            c.execute("DELETE FROM calendar_events WHERE id=?", (event_id,))
        log.info(f"Scheduler: event {event_id} deleted")
    except Exception as e:
        log.error(f"Scheduler delete_event: {e}")


def get_all_events() -> list[dict]:
    try:
        with _conn() as c:
            rows = c.execute(
                "SELECT * FROM calendar_events ORDER BY scheduled_dt DESC LIMIT 100"
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        log.error(f"Scheduler get_all_events: {e}")
        return []


# ── Schedule-intent keyword check (fast, no AI cost) ─────────────────────────

_SCHEDULE_KEYWORDS = [
    "schedule", "set a reminder", "remind me", "book a", "plan a",
    "add to calendar", "calendar event", "meeting at", "call at",
    "appointment", "set up a call", "block time", "block out",
    "put on calendar", "arrange a", "fix a time", "fix time",
]


def looks_like_schedule_request(message: str) -> bool:
    """
    Cheap keyword pre-filter before spending an AI call.
    Returns True if the message looks like a scheduling request.
    """
    low = message.lower()
    return any(kw in low for kw in _SCHEDULE_KEYWORDS)


# ── Build notification text ───────────────────────────────────────────────────

def build_15min_notification(event: dict) -> tuple[str, str, list[str]]:
    """Return (headline, message, suggestions) for the 15-minute warning."""
    dt = _fmt_dt(event["scheduled_dt"])
    headline = f"🗓 Starting in 15 min: {event['title']}"
    message  = f"{event['title']} begins at {dt}."
    if event.get("prep_notes"):
        message += f"\n\nPrep: {event['prep_notes']}"
    suggestions = [
        "Open notes",
        f"Duration: {event.get('duration_mins', 60)} min",
    ]
    return headline, message, suggestions


def build_start_notification(event: dict) -> tuple[str, str, list[str]]:
    """Return (headline, message, suggestions) for the start-time chat message."""
    dt = _fmt_dt(event["scheduled_dt"])
    headline = f"🗓 Starting now: {event['title']}"
    parts = [f"**{event['title']}** is starting now ({dt})."]
    if event.get("agenda"):
        parts.append(f"\n**Agenda:**\n{event['agenda']}")
    if event.get("attendees") and event["attendees"] != "Solo":
        parts.append(f"\n**Attendees:** {event['attendees']}")
    message = "\n".join(parts)
    suggestions = ["Mark done", "Postpone 15 min"]
    return headline, message, suggestions


def build_start_chat_message(event: dict) -> str:
    """
    The detailed Aria chat message sent at event start.
    Contains the AI-generated agenda so it appears in the chat bubble.
    """
    dt    = _fmt_dt(event["scheduled_dt"])
    lines = [f"🗓 **{event['title']}** is starting now ({dt})."]

    if event.get("agenda"):
        lines.append(f"\n**Suggested agenda:**\n{event['agenda']}")

    if event.get("prep_notes"):
        lines.append(f"\n**Prep checklist:**\n{event['prep_notes']}")

    if event.get("attendees") and event["attendees"].lower() != "solo":
        lines.append(f"\n**Attendees:** {event['attendees']}")

    lines.append("\nGood luck! 💪")
    return "\n".join(lines)


def _fmt_dt(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%A, %d %b at %I:%M %p")
    except Exception:
        return iso
