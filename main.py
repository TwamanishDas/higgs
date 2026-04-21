import sys
import time
from concurrent.futures import ThreadPoolExecutor
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal, QTimer

import logger
import config
import notifier
from brain import azure_client, context as brain_context
from brain import memory, pattern_analyzer, soul_builder
from brain import api_server, scheduler
from awareness import windows as win_awareness
from awareness import context_detector
from awareness.window_monitor import WindowMonitor
from widget.overlay import DesktopWidget


# ── Qt signal bridges ────────────────────────────────────────────────────────

class ScanSignals(QObject):
    result     = pyqtSignal(dict)
    error      = pyqtSignal(str)


class ContextSignals(QObject):
    help_offer = pyqtSignal(str, str, list, str)


class ExcelSignals(QObject):
    context_received = pyqtSignal(dict)


class ChatSignals(QObject):
    response = pyqtSignal(str)          # plain-text chat reply


class SchedulerSignals(QObject):
    """Fired when a calendar event needs a notification."""
    warning_15 = pyqtSignal(dict)       # 15-minute warning
    starting   = pyqtSignal(dict)       # event starting now


# ── Per-app AI scan cooldown ─────────────────────────────────────────────────
_app_scan_times: dict[str, float] = {}
_APP_SCAN_COOLDOWN = 300   # seconds between per-app scans
_APP_SCAN_MAX_KEYS = 100


def _app_scan_due(process: str) -> bool:
    now  = time.monotonic()
    last = _app_scan_times.get(process, 0.0)
    return (now - last) >= _APP_SCAN_COOLDOWN


def _mark_app_scanned(process: str):
    if len(_app_scan_times) >= _APP_SCAN_MAX_KEYS:
        oldest = min(_app_scan_times, key=_app_scan_times.get)
        del _app_scan_times[oldest]
    _app_scan_times[process] = time.monotonic()


# ── Worker functions ──────────────────────────────────────────────────────────

def run_scan(signals: ScanSignals, cfg: dict, active_window: dict | None = None):
    """Full AI scan — collect context, call GPT-4o, record observation."""
    try:
        logger.log.info("AI scan started")
        ctx    = brain_context.build_context(cfg)
        result = azure_client.analyze(ctx)

        try:
            import psutil
            win  = active_window or win_awareness.get_active_window()
            cpu  = psutil.cpu_percent(interval=None)
            ram  = psutil.virtual_memory().percent
            memory.record_observation(
                active_app   = win.get("process", ""),
                active_title = win.get("title", ""),
                mood         = result.get("mood", "IDLE"),
                headline     = result.get("headline", ""),
                message      = result.get("message", ""),
                cpu          = cpu,
                ram          = ram,
                raw_context  = ctx[:2000],
            )
        except Exception as mem_err:
            logger.log.warning(f"Memory record skipped: {mem_err}")

        signals.result.emit(result)
    except Exception as e:
        logger.log.error(f"Scan failed: {e}")
        signals.error.emit(str(e))


def run_context_check(signals: ContextSignals, window: dict):
    """Immediate local context detection — no AI call."""
    try:
        offer = context_detector.detect_context(window)
        if offer:
            signals.help_offer.emit(
                offer["headline"],
                offer["message"],
                offer.get("suggestions", []),
                offer.get("level", "low"),
            )
    except Exception as e:
        logger.log.error(f"Context check error: {e}")


def run_pattern_analysis(cfg: dict):
    try:
        pattern_analyzer.analyze_patterns()
        auto_soul = pattern_analyzer.build_auto_soul(cfg)
        if auto_soul.get("_auto_trait"):
            azure_client.set_auto_trait(auto_soul["_auto_trait"])
        pattern_analyzer.generate_daily_summary(cfg)
        logger.log.info("Pattern analysis complete")
    except Exception as e:
        logger.log.error(f"Pattern analysis error: {e}")


# ── NLP scheduling workers ────────────────────────────────────────────────────

def run_chat_probe(signals: ChatSignals, raw_request: str, state_box: list):
    """
    Turn 1 — user just sent a scheduling request.
    Calls AI for probe questions; stores partial state in state_box[0].
    """
    try:
        result = azure_client.schedule_probe_chat(raw_request)
        # Update shared state (list-as-mutable-box pattern)
        state_box[0] = {
            "active":        True,
            "turn":          1,
            "raw_request":   raw_request,
            "hint_title":    result.get("title", ""),
            "hint_dt":       result.get("parsed_dt", ""),
        }
        signals.response.emit(result.get("reply", "Let me ask a couple of quick questions!"))
    except Exception as e:
        logger.log.error(f"Schedule probe error: {e}")
        signals.response.emit(f"Sorry, something went wrong: {e}")
        state_box[0] = {}


def run_chat_finalize(signals: ChatSignals, probe_answers: str,
                      state_box: list, sched_signals: SchedulerSignals):
    """
    Turn 2 — user answered the probe questions.
    Finalises the event, saves it, emits confirmation reply.
    """
    state = state_box[0]
    try:
        result = azure_client.finalize_schedule_chat(
            raw_request  = state.get("raw_request", ""),
            probe_answers= probe_answers,
            hint_title   = state.get("hint_title", ""),
            hint_dt      = state.get("hint_dt", ""),
        )
        # Save to DB
        event_id = scheduler.save_event(
            title         = result.get("title", "Event"),
            description   = result.get("description", ""),
            scheduled_dt  = result.get("scheduled_dt", ""),
            duration_mins = result.get("duration_mins", 60),
            attendees     = result.get("attendees", "Solo"),
            agenda        = result.get("agenda", ""),
            prep_notes    = result.get("prep_notes", ""),
        )
        logger.log.info(f"Event scheduled | id={event_id} | title={result.get('title')}")
        state_box[0] = {}   # clear state — conversation over
        signals.response.emit(result.get("reply", "All set! I'll remind you before it starts."))
    except Exception as e:
        logger.log.error(f"Schedule finalize error: {e}")
        signals.response.emit(f"Sorry, I couldn't save the event: {e}")
        state_box[0] = {}


def run_chat(signals: ChatSignals, user_message: str, excel_ctx: dict):
    """Normal (non-scheduling) chat."""
    try:
        reply = azure_client.chat(user_message, excel_ctx)
        signals.response.emit(reply)
    except Exception as e:
        logger.log.error(f"Chat error: {e}")
        signals.response.emit(f"Sorry, something went wrong: {e}")


def run_scheduler_check(sched_signals: SchedulerSignals):
    """Check for events that need a 15-min warning or start notification."""
    try:
        due = scheduler.get_due_events()
        for ev in due.get("warning_15", []):
            scheduler.mark_notified_15(ev["id"])
            sched_signals.warning_15.emit(ev)
        for ev in due.get("starting", []):
            scheduler.mark_notified_now(ev["id"])
            sched_signals.starting.emit(ev)
    except Exception as e:
        logger.log.error(f"Scheduler check error: {e}")


# ── Azure init ────────────────────────────────────────────────────────────────

def _init_azure(cfg: dict):
    az = cfg["azure"]
    azure_client.init(
        endpoint    = az["endpoint"],
        api_key     = az["api_key"],
        deployment  = az["deployment"],
        api_version = az.get("api_version", "2024-12-01-preview"),
        identity    = cfg.get("identity", {}),
        soul        = cfg.get("soul", {}),
        tone        = cfg.get("tone", {}),
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    logger.setup()
    cfg = config.load()
    logger.log.info("Config loaded")

    az = cfg["azure"]
    if not az["endpoint"] or not az["api_key"]:
        logger.log.critical("Azure endpoint or API key missing in config.json")
        sys.exit(1)

    _init_azure(cfg)
    memory.init()
    logger.log.info("Memory system ready")

    # ── Soul seed (OpenClaw read-into-being) ─────────────────────────────────
    soul_builder.seed(
        name        = cfg.get("identity", {}).get("name", "Aria"),
        personality = cfg.get("soul", {}).get("personality", "professional"),
        tagline     = cfg.get("identity", {}).get("tagline", "Your ambient second brain"),
    )
    logger.log.info("Soul context ready")

    # ── Scheduler DB init ─────────────────────────────────────────────────────
    scheduler.init()
    logger.log.info("Scheduler ready")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # ── Shared thread pool ────────────────────────────────────────────────────
    executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="companion")

    widget           = DesktopWidget(cfg)
    scan_signals     = ScanSignals()
    context_signals  = ContextSignals()
    excel_signals    = ExcelSignals()
    chat_signals     = ChatSignals()
    sched_signals    = SchedulerSignals()

    # Mutable scheduling-conversation state (list-as-box so closures can mutate it)
    _schedule_state: list[dict] = [{}]

    def _notif_duration() -> int:
        return cfg.get("notifications", {}).get("display_duration_seconds", 8)

    def _scan_cooldown() -> int:
        return cfg.get("notifications", {}).get("scan_cooldown_seconds", 300)

    # ── Signal handlers ───────────────────────────────────────────────────────

    def on_scan_result(result: dict):
        mood        = result.get("mood", "IDLE")
        message     = result.get("message", "")
        headline    = result.get("headline", "Update")
        suggestions = result.get("suggestions", [])
        level       = result.get("alert_level", "low")
        logger.log.info(f"Scan result | mood={mood} | level={level}")
        widget.set_mood(mood)
        if message and notifier.should_notify("scan", headline, 60):
            widget.show_notification(headline, message, suggestions, level, _notif_duration())

    def on_scan_error(err: str):
        logger.log.error(f"Scan error: {err}")
        widget.set_mood("ERROR")
        if notifier.should_notify("scan_error", err, 120):
            widget.show_notification("Scan failed", err,
                                     ["Check Azure AI config"], "medium", _notif_duration())

    def on_context_help(headline, message, suggestions, level):
        if notifier.should_notify("context_help", headline + message, 1800):
            widget.show_notification(headline, message, suggestions, level, _notif_duration())

    def on_settings_saved(new_cfg: dict):
        nonlocal cfg
        cfg = new_cfg
        _init_azure(cfg)
        logger.log.info("Settings saved and applied")

    def on_excel_context(ctx: dict):
        """Fired by Flask thread → relay to Qt main thread via signal."""
        excel_signals.context_received.emit(ctx)

    def on_excel_context_received(ctx: dict):
        """Runs on main thread — update widget."""
        widget.set_excel_context(ctx)

    def on_user_chat_message(message: str, excel_ctx: dict):
        """Called by API server (Flask thread) — dispatch to executor."""
        executor.submit(run_chat, chat_signals, message, excel_ctx)

    def on_chat_response(reply: str):
        widget.add_aria_chat_message(reply)

    # ── NLP Calendar: detect intent and route ─────────────────────────────────

    def on_widget_chat_message(message: str):
        """
        Fired by the chat panel's send button.
        Routes to scheduling probe/finalize or normal chat.
        """
        state = _schedule_state[0]

        if state.get("active") and state.get("turn") == 1:
            # Turn 2 — user answered the probe questions
            executor.submit(
                run_chat_finalize,
                chat_signals, message, _schedule_state, sched_signals,
            )
            return

        # Check keyword pre-filter first (free), then submit probe
        excel_ctx = (widget._chat_panel.get_excel_context()
                     if hasattr(widget._chat_panel, "get_excel_context") else {})

        if scheduler.looks_like_schedule_request(message):
            executor.submit(run_chat_probe, chat_signals, message, _schedule_state)
        else:
            executor.submit(run_chat, chat_signals, message, excel_ctx)

    # ── Scheduler notification handlers ──────────────────────────────────────

    def on_sched_warning_15(event: dict):
        headline, message, suggestions = scheduler.build_15min_notification(event)
        widget.show_notification(headline, message, suggestions, "medium", _notif_duration())
        widget.set_mood("ALERT")
        logger.log.info(f"15-min warning fired for event id={event['id']}")

    def on_sched_starting(event: dict):
        # Desktop notification bubble
        headline, message, suggestions = scheduler.build_start_notification(event)
        widget.show_notification(headline, message, suggestions, "high", _notif_duration() + 5)
        widget.set_mood("HAPPY")
        # Rich chat message with full agenda
        chat_msg = scheduler.build_start_chat_message(event)
        widget.add_aria_chat_message(chat_msg)
        # Auto-open chat so the user sees the agenda
        if not widget._chat_panel.isVisible():
            widget._chat_panel.show_near(
                widget.x(), widget.y(), widget.width(), widget.height()
            )
        logger.log.info(f"Start notification fired for event id={event['id']}")

    # ── Window change ─────────────────────────────────────────────────────────

    def on_window_changed(window: dict):
        process = (window.get("process") or "").lower().replace(".exe", "")
        title   = window.get("title", "")
        logger.log.info(f"Window changed → {process} | {title[:50]}")

        if cfg.get("skills", {}).get("context_help", True):
            executor.submit(run_context_check, context_signals, window)

        if cfg.get("skills", {}).get("ai_brain", True) and _app_scan_due(process):
            _mark_app_scanned(process)
            widget.set_mood("THINKING")
            executor.submit(run_scan, scan_signals, cfg, window)

    # ── Periodic fallback scan ────────────────────────────────────────────────

    def on_periodic_scan():
        if cfg.get("skills", {}).get("ai_brain", True):
            widget.set_mood("THINKING")
            executor.submit(run_scan, scan_signals, cfg)

    def on_pattern_analysis():
        if cfg.get("skills", {}).get("memory", True):
            executor.submit(run_pattern_analysis, cfg)

    def on_scheduler_tick():
        executor.submit(run_scheduler_check, sched_signals)

    # ── Connect signals ───────────────────────────────────────────────────────

    scan_signals.result.connect(on_scan_result)
    scan_signals.error.connect(on_scan_error)
    context_signals.help_offer.connect(on_context_help)
    excel_signals.context_received.connect(on_excel_context_received)
    chat_signals.response.connect(on_chat_response)
    sched_signals.warning_15.connect(on_sched_warning_15)
    sched_signals.starting.connect(on_sched_starting)
    widget._settings_panel.saved.connect(on_settings_saved)
    widget.scan_requested.connect(on_periodic_scan)
    widget._chat_panel.message_sent.connect(on_widget_chat_message)

    # ── API server (Excel add-in bridge) ─────────────────────────────────────
    api_server.init(
        on_excel_context = on_excel_context,
        on_chat_message  = on_user_chat_message,
    )
    api_server.start(port=5050)

    # ── Window monitor ────────────────────────────────────────────────────────
    win_monitor = WindowMonitor(poll_interval=1.5)
    win_monitor.signals.changed.connect(on_window_changed)
    win_monitor.start()

    # ── Periodic timers ───────────────────────────────────────────────────────

    scan_interval_ms = cfg.get("awareness", {}).get("scan_interval_seconds", 30) * 1000
    scan_timer = QTimer()
    scan_timer.timeout.connect(on_periodic_scan)
    scan_timer.start(scan_interval_ms)

    # Calendar event check — every 60 s
    sched_timer = QTimer()
    sched_timer.timeout.connect(on_scheduler_tick)
    sched_timer.start(60_000)

    pattern_timer = QTimer()
    pattern_timer.timeout.connect(on_pattern_analysis)
    pattern_timer.start(30 * 60 * 1000)

    # ── Clean shutdown ────────────────────────────────────────────────────────

    def on_quit():
        logger.log.info("Shutting down...")
        win_monitor.stop()
        executor.shutdown(wait=False)

    app.aboutToQuit.connect(on_quit)

    # ── Startup sequence ──────────────────────────────────────────────────────

    QTimer.singleShot(3_000,  on_periodic_scan)
    QTimer.singleShot(15_000, on_pattern_analysis)
    QTimer.singleShot(5_000,  on_scheduler_tick)   # check events shortly after start

    name = cfg.get('identity', {}).get('name', 'Aria')
    logger.log.info(f"Widget '{name}' running — NLP calendar active")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
