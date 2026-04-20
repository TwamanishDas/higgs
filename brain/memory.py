"""
Active + archive memory system. Stores observations, daily summaries,
and detected patterns in SQLite. Enables cross-session learning.
"""
import sqlite3
import json
import os
import threading
from datetime import datetime, timedelta
from collections import Counter

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from logger import log

_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "memory", "companion.db"
)

# One persistent connection per thread — avoids opening/closing on every call
_local = threading.local()


def _conn() -> sqlite3.Connection:
    if not getattr(_local, "conn", None):
        os.makedirs(os.path.dirname(_DB_PATH), exist_ok=True)
        _local.conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


def init():
    with _conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS observations (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            ts            TEXT    NOT NULL,
            date          TEXT    NOT NULL,
            active_app    TEXT,
            active_title  TEXT,
            mood          TEXT,
            headline      TEXT,
            message       TEXT,
            cpu_percent   REAL,
            ram_percent   REAL,
            raw_context   TEXT
        );

        CREATE TABLE IF NOT EXISTS daily_summaries (
            date          TEXT PRIMARY KEY,
            summary       TEXT,
            key_apps      TEXT,
            total_scans   INTEGER,
            dominant_mood TEXT,
            created_ts    TEXT
        );

        CREATE TABLE IF NOT EXISTS patterns (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_type  TEXT    NOT NULL,
            pattern_key   TEXT    NOT NULL,
            pattern_value TEXT    NOT NULL,
            confidence    REAL    DEFAULT 0.5,
            last_seen     TEXT,
            UNIQUE(pattern_type, pattern_key)
        );

        CREATE TABLE IF NOT EXISTS soul_traits (
            trait         TEXT PRIMARY KEY,
            value         TEXT,
            reason        TEXT,
            updated_ts    TEXT
        );

        CREATE TABLE IF NOT EXISTS recommendations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ts          TEXT NOT NULL,
            date        TEXT NOT NULL,
            headline    TEXT,
            message     TEXT,
            category    TEXT,
            context_app TEXT
        );
        """)
    log.info("Memory DB initialized")


def record_observation(active_app: str, active_title: str, mood: str,
                       headline: str, message: str,
                       cpu: float = 0.0, ram: float = 0.0,
                       raw_context: str = ""):
    now = datetime.now()
    try:
        with _conn() as c:
            c.execute(
                """INSERT INTO observations
                   (ts, date, active_app, active_title, mood, headline,
                    message, cpu_percent, ram_percent, raw_context)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (now.isoformat(), now.strftime("%Y-%m-%d"),
                 active_app, active_title, mood, headline,
                 message, cpu, ram, raw_context[:2000])
            )
    except Exception as e:
        log.error(f"Memory record_observation failed: {e}")


def get_recent_observations(days: int = 7) -> list[dict]:
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        with _conn() as c:
            rows = c.execute(
                "SELECT * FROM observations WHERE date >= ? ORDER BY ts DESC LIMIT 300",
                (cutoff,)
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        log.error(f"Memory get_recent_observations failed: {e}")
        return []


def get_today_observations() -> list[dict]:
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        with _conn() as c:
            rows = c.execute(
                "SELECT * FROM observations WHERE date = ? ORDER BY ts DESC",
                (today,)
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        log.error(f"Memory get_today_observations failed: {e}")
        return []


def save_daily_summary(date: str, summary: str, key_apps: list,
                       total_scans: int, dominant_mood: str):
    try:
        with _conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO daily_summaries
                   (date, summary, key_apps, total_scans, dominant_mood, created_ts)
                   VALUES (?,?,?,?,?,?)""",
                (date, summary, json.dumps(key_apps),
                 total_scans, dominant_mood, datetime.now().isoformat())
            )
    except Exception as e:
        log.error(f"Memory save_daily_summary failed: {e}")


def get_daily_summaries(days: int = 14) -> list[dict]:
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    try:
        with _conn() as c:
            rows = c.execute(
                "SELECT * FROM daily_summaries WHERE date >= ? ORDER BY date DESC",
                (cutoff,)
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        log.error(f"Memory get_daily_summaries failed: {e}")
        return []


def upsert_pattern(pattern_type: str, pattern_key: str,
                   pattern_value: str, confidence: float = 0.5):
    try:
        with _conn() as c:
            c.execute(
                """INSERT INTO patterns
                   (pattern_type, pattern_key, pattern_value, confidence, last_seen)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(pattern_type, pattern_key) DO UPDATE SET
                       pattern_value = excluded.pattern_value,
                       confidence    = MIN(1.0, patterns.confidence + 0.1),
                       last_seen     = excluded.last_seen""",
                (pattern_type, pattern_key, pattern_value,
                 confidence, datetime.now().isoformat())
            )
    except Exception as e:
        log.error(f"Memory upsert_pattern failed: {e}")


def get_patterns(pattern_type: str = None) -> list[dict]:
    try:
        with _conn() as c:
            if pattern_type:
                rows = c.execute(
                    "SELECT * FROM patterns WHERE pattern_type=? ORDER BY confidence DESC",
                    (pattern_type,)
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT * FROM patterns ORDER BY confidence DESC"
                ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        log.error(f"Memory get_patterns failed: {e}")
        return []


def save_soul_trait(trait: str, value: str, reason: str):
    try:
        with _conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO soul_traits (trait, value, reason, updated_ts)
                   VALUES (?,?,?,?)""",
                (trait, value, reason, datetime.now().isoformat())
            )
    except Exception as e:
        log.error(f"Memory save_soul_trait failed: {e}")


def get_soul_traits() -> dict:
    try:
        with _conn() as c:
            rows = c.execute(
                "SELECT trait, value, reason FROM soul_traits"
            ).fetchall()
        return {r["trait"]: {"value": r["value"], "reason": r["reason"]} for r in rows}
    except Exception as e:
        log.error(f"Memory get_soul_traits failed: {e}")
        return {}


def save_recommendation(headline: str, message: str, category: str, context_app: str = ""):
    """Persist every notification shown so the AI never repeats itself."""
    from datetime import datetime
    now = datetime.now()
    try:
        with _conn() as c:
            # Ensure table exists (idempotent)
            c.execute("""
                CREATE TABLE IF NOT EXISTS recommendations (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts          TEXT NOT NULL,
                    date        TEXT NOT NULL,
                    headline    TEXT,
                    message     TEXT,
                    category    TEXT,
                    context_app TEXT
                )
            """)
            c.execute(
                """INSERT INTO recommendations
                   (ts, date, headline, message, category, context_app)
                   VALUES (?,?,?,?,?,?)""",
                (now.isoformat(), now.strftime("%Y-%m-%d"),
                 headline, message, category, context_app)
            )
    except Exception as e:
        log.error(f"Memory save_recommendation failed: {e}")


def get_recent_recommendations(limit: int = 20) -> list[dict]:
    """Return the last N recommendations shown to the user."""
    try:
        with _conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL, date TEXT NOT NULL,
                    headline TEXT, message TEXT,
                    category TEXT, context_app TEXT
                )
            """)
            rows = c.execute(
                "SELECT headline, message, category, ts FROM recommendations "
                "ORDER BY ts DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        log.error(f"Memory get_recent_recommendations failed: {e}")
        return []


def archive_old_observations(keep_days: int = 30):
    cutoff = (datetime.now() - timedelta(days=keep_days)).strftime("%Y-%m-%d")
    try:
        with _conn() as c:
            deleted = c.execute(
                "DELETE FROM observations WHERE date < ?", (cutoff,)
            ).rowcount
        if deleted:
            log.info(f"Archived {deleted} old raw observations (daily summaries preserved)")
    except Exception as e:
        log.error(f"Memory archive failed: {e}")


def build_memory_context(days: int = 7) -> str:
    """Build a memory context string to include in AI prompts."""
    parts = []

    summaries = get_daily_summaries(days)
    if summaries:
        parts.append("## Memory: Recent Daily Activity")
        for s in summaries[:5]:
            apps = json.loads(s.get("key_apps", "[]"))
            apps_str = ", ".join(apps[:4]) if apps else "unknown"
            parts.append(
                f"- {s['date']}: {s['summary']} "
                f"[mood: {s['dominant_mood']}, apps: {apps_str}]"
            )

    patterns = get_patterns()
    if patterns:
        parts.append("\n## Memory: Detected Patterns")
        for p in patterns[:8]:
            parts.append(
                f"- {p['pattern_type']}/{p['pattern_key']}: {p['pattern_value']} "
                f"(confidence {p['confidence']:.1f})"
            )

    soul_traits = get_soul_traits()
    if soul_traits:
        parts.append("\n## Memory: Auto-Learned Character Traits")
        for trait, data in soul_traits.items():
            parts.append(f"- {trait}: {data['value']}")

    return "\n".join(parts)
