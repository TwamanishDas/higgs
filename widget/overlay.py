import threading
from PyQt6.QtWidgets import QWidget, QApplication, QMenu, QPushButton
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QAction, QFont

from widget.animations import AnimationState, Mood, draw_widget
from widget.notifications import NotificationBubble
from widget.settings_panel import SettingsPanel
from widget.chat_panel import ChatPanel
from widget.characters.pokemon_list import POKEMON_BY_ID
from widget.characters.pokemon_character import PokemonCharacter
from widget.characters import sprite_manager

# Animation tick intervals per mood (ms) — saves CPU on slow/idle moods
_TICK_MS: dict[str, int] = {
    "SLEEPING": 100,   # 10 FPS
    "IDLE":      33,   # 30 FPS
    "HAPPY":     20,   # 50 FPS
    "INFO":      25,   # 40 FPS
}
_TICK_DEFAULT = 20     # 50 FPS for active/alert moods


class DesktopWidget(QWidget):
    scan_requested = pyqtSignal()

    def __init__(self, cfg: dict):
        super().__init__()
        self._cfg = cfg
        self._size = cfg["widget"]["size"]
        self._state = AnimationState()
        self._notification: NotificationBubble | None = None
        self._drag_pos: QPoint | None = None
        self._vault_path = cfg.get("vault", {}).get("path", "")
        self._name = cfg.get("identity", {}).get("name", "Aria")

        self._pokemon_char: PokemonCharacter | None = None
        self._apply_character(cfg)

        self.setFixedSize(self._size + 20, self._size + 20)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setWindowOpacity(cfg["widget"]["opacity"])
        self.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)

        screen = QApplication.primaryScreen().geometry()
        x = min(cfg["widget"]["start_x"], screen.width() - self.width())
        y = min(cfg["widget"]["start_y"], screen.height() - self.height())
        self.move(x, y)

        self._settings_panel = SettingsPanel()
        self._settings_panel.saved.connect(self._on_settings_saved)
        self._chat_panel = ChatPanel()

        # Chat button — floats at the bottom-centre of the widget
        self._chat_btn = self._make_chat_button()

        # Animation timer only — no scan timer here (main.py owns scanning)
        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._tick)
        self._anim_timer.start(_TICK_DEFAULT)

        self.show()
        self._chat_btn.show()

    # ── Chat button ───────────────────────────────────────────────────────────

    def _make_chat_button(self) -> QPushButton:
        btn = QPushButton("💬", self)
        btn.setFixedSize(26, 26)
        btn.setFont(QFont("Segoe UI Emoji", 11))
        btn.setToolTip("Chat with Aria")
        btn.setStyleSheet("""
            QPushButton {
                background: #161b22;
                border: 1px solid #30363d;
                border-radius: 13px;
                color: #8b949e;
            }
            QPushButton:hover  { background: #1c2128; border-color: #4a9eff; color: #4a9eff; }
            QPushButton:pressed { background: #0d1117; }
        """)
        # Position at bottom-centre of the widget window
        w = self._size + 20
        btn.move((w - 26) // 2, w - 28)
        btn.clicked.connect(self._toggle_chat)
        btn.raise_()
        return btn

    def _toggle_chat(self):
        if self._chat_panel.isVisible():
            self._chat_panel.hide()
        else:
            self._chat_panel.show_near(self.x(), self.y(), self.width(), self.height())

    def set_excel_context(self, ctx: dict):
        """Called from main.py when Excel sends a selection."""
        self._chat_panel.set_excel_context(ctx)
        # Glow the chat button to signal new Excel data
        self._chat_btn.setStyleSheet("""
            QPushButton {
                background: #0d2a1a;
                border: 1px solid #3fb950;
                border-radius: 13px;
                color: #3fb950;
            }
            QPushButton:hover  { background: #0d2a1a; border-color: #58d068; color: #58d068; }
        """)
        # Auto-open chat panel to show the welcome message
        if not self._chat_panel.isVisible():
            self._chat_panel.show_near(self.x(), self.y(), self.width(), self.height())

    def add_aria_chat_message(self, text: str):
        self._chat_panel.add_aria_message(text)

    # ── Character system ──────────────────────────────────────────────────────

    def _apply_character(self, cfg: dict):
        # Release old sprite memory before switching
        if self._pokemon_char:
            self._pokemon_char._pixmap = None
            self._pokemon_char = None

        char_cfg  = cfg.get("character", {})
        char_type = char_cfg.get("type", "orb")
        self._char_type = char_type

        if char_type == "pokemon":
            pokemon_id = char_cfg.get("pokemon_id", 25)
            shiny      = char_cfg.get("shiny", False)
            self._pokemon_char = PokemonCharacter(
                pokemon_id, shiny, repaint_callback=self.update
            )
            self._download_and_load(pokemon_id, shiny)

    def _download_and_load(self, pokemon_id: int, shiny: bool):
        def worker():
            sprite_manager.ensure_pokemon(pokemon_id, shiny)
            QTimer.singleShot(0, self._finish_load)
        threading.Thread(target=worker, daemon=True).start()

    def _finish_load(self):
        if self._pokemon_char:
            self._pokemon_char.load()
            self.update()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_mood(self, mood_str: str):
        try:
            mood = Mood[mood_str.upper()]
        except KeyError:
            mood = Mood.IDLE
        self._state.set_mood(mood)
        # Adjust tick rate to match mood activity level
        interval = _TICK_MS.get(mood_str.upper(), _TICK_DEFAULT)
        if self._anim_timer.interval() != interval:
            self._anim_timer.setInterval(interval)

    def show_notification(self, headline: str, message: str,
                          suggestions: list[str], alert_level: str,
                          duration_seconds: int = 8):
        if self._notification:
            self._notification.close()
        bubble = NotificationBubble(
            headline, message, suggestions, alert_level,
            duration_ms=duration_seconds * 1000
        )
        bubble.show()
        self._notification = bubble
        self._reposition_notification()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _reposition_notification(self):
        if not self._notification:
            return
        screen = QApplication.primaryScreen().geometry()
        bw = self._notification.width()
        bh = self._notification.height()
        bx = self.x() - bw - 12
        if bx < 0:
            bx = self.x() + self.width() + 12
        by = max(0, min(self.y(), screen.height() - bh))
        self._notification.move(bx, by)

    def _tick(self):
        self._state.step()
        if self._pokemon_char:
            self._pokemon_char.step()
        self.update()

    def _request_scan(self):
        self.set_mood("THINKING")
        self.scan_requested.emit()

    def _show_settings(self):
        screen = QApplication.primaryScreen().geometry()
        sw = self._settings_panel.width()
        sh = self._settings_panel.height()
        self._settings_panel.move(
            (screen.width() - sw) // 2,
            (screen.height() - sh) // 2
        )
        self._settings_panel.show()
        self._settings_panel.raise_()

    def _on_settings_saved(self, new_cfg: dict):
        self._cfg  = new_cfg
        self._name = new_cfg.get("identity", {}).get("name", "Aria")
        self._vault_path = new_cfg.get("vault", {}).get("path", "")
        self._apply_character(new_cfg)

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        size = self._size + 20
        if self._char_type == "pokemon" and self._pokemon_char:
            self._pokemon_char.render(painter, self._state.mood, size)
        else:
            draw_widget(painter, self._state, size)

    # ── Mouse ─────────────────────────────────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            self._reposition_notification()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        self._request_scan()

    def _show_context_menu(self, pos: QPoint):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #1a1a2e; color: #cce4ff; border: 1px solid #4a9eff;
                    border-radius: 6px; padding: 4px; font-size: 12px; }
            QMenu::item { padding: 7px 20px; border-radius: 4px; }
            QMenu::item:selected { background: #2a3a5a; }
            QMenu::separator { background: #2a3a5a; height: 1px; margin: 3px 8px; }
        """)

        header = QAction(f"◆  {self._name}", self)
        header.setEnabled(False)
        menu.addAction(header)
        menu.addSeparator()

        chat_action = QAction("💬  Open Chat / Schedule", self)
        chat_action.triggered.connect(self._toggle_chat)
        menu.addAction(chat_action)

        scan_action = QAction("⟳  Scan Now", self)
        scan_action.triggered.connect(self._request_scan)
        menu.addAction(scan_action)

        menu.addSeparator()

        settings_action = QAction("⚙  Settings", self)
        settings_action.triggered.connect(self._show_settings)
        menu.addAction(settings_action)

        menu.addSeparator()

        sleep_action = QAction("◌  Sleep Mode", self)
        sleep_action.triggered.connect(lambda: self.set_mood("SLEEPING"))
        menu.addAction(sleep_action)

        wake_action = QAction("◉  Wake Up", self)
        wake_action.triggered.connect(lambda: self.set_mood("IDLE"))
        menu.addAction(wake_action)

        menu.addSeparator()

        quit_action = QAction("✕  Quit", self)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

        menu.exec(pos)
