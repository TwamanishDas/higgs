"""
Notification gate — prevents spam and deduplication.
Prunes stale entries older than 24 hours to stay memory-lean.
"""
from datetime import datetime, timedelta

_last_time:    dict[str, datetime] = {}
_last_content: dict[str, int]      = {}
_PRUNE_AFTER   = timedelta(hours=24)
_prune_counter = 0
_PRUNE_EVERY   = 50   # prune on every Nth call


def _prune():
    """Remove entries not touched in the last 24 hours."""
    cutoff = datetime.now() - _PRUNE_AFTER
    stale  = [k for k, t in _last_time.items() if t < cutoff]
    for k in stale:
        _last_time.pop(k, None)
        _last_content.pop(k, None)


def should_notify(category: str, content: str, cooldown_seconds: int = 300) -> bool:
    global _prune_counter
    _prune_counter += 1
    if _prune_counter >= _PRUNE_EVERY:
        _prune_counter = 0
        _prune()

    now  = datetime.now()
    last = _last_time.get(category)
    if last and (now - last).total_seconds() < cooldown_seconds:
        return False
    h = hash(content)
    if _last_content.get(category) == h:
        return False
    _last_time[category]    = now
    _last_content[category] = h
    return True


def force_notify(category: str, content: str):
    """Mark as notified without checking cooldown — for high-priority alerts."""
    _last_time[category]    = datetime.now()
    _last_content[category] = hash(content)


def reset(category: str):
    _last_time.pop(category, None)
    _last_content.pop(category, None)
