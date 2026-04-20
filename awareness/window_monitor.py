"""
Real-time active-window change detector.
Runs a background thread that polls every 1.5 s.
Emits WindowChangeSignals.changed whenever the foreground window switches
to a different process or a meaningfully different document title.
"""
import threading
import time
import os
import sys

from PyQt6.QtCore import QObject, pyqtSignal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from awareness import windows as win_awareness
from logger import log


def _title_key(window: dict) -> str:
    """
    Stable key for a window.
    Uses the process name + first 60 chars of title so minor
    title changes (e.g. unsaved-indicator '*') don't re-trigger.
    """
    process = (window.get("process") or "").lower().replace(".exe", "")
    title   = (window.get("title")   or "")[:60].strip()
    return f"{process}||{title}"


class WindowChangeSignals(QObject):
    # Emitted with the new active window dict
    changed = pyqtSignal(dict)


class WindowMonitor:
    """
    Lightweight poller. Call start() once; it spawns a daemon thread.
    The `signals.changed` Qt signal fires on the emitting thread —
    connect it to a slot in your main thread as usual.
    """

    def __init__(self, poll_interval: float = 1.5):
        self.signals       = WindowChangeSignals()
        self._interval     = poll_interval
        self._last_key     = ""
        self._running      = False
        self._thread: threading.Thread | None = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, daemon=True, name="window-monitor"
        )
        self._thread.start()
        log.info("Window monitor started (poll interval %.1fs)" % self._interval)

    def stop(self):
        self._running = False

    def _loop(self):
        while self._running:
            try:
                win = win_awareness.get_active_window()
                key = _title_key(win)
                if key and key != self._last_key:
                    self._last_key = key
                    log.info(
                        f"Window changed | process={win.get('process')} "
                        f"| title={win.get('title','')[:50]}"
                    )
                    self.signals.changed.emit(win)
            except Exception as e:
                log.error(f"Window monitor error: {e}")
            time.sleep(self._interval)
