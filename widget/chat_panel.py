"""
Floating chat panel — docks beside the widget.
Shows conversation bubbles, Excel context badge, and a text input.
All AI interaction happens here; no Office task pane needed.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QLineEdit, QPushButton, QFrame,
    QSizePolicy, QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QKeyEvent

# ── Theme ─────────────────────────────────────────────────────────────────────
_DARK    = "#0d1117"
_SURFACE = "#161b22"
_RAISED  = "#1c2128"
_BORDER  = "#30363d"
_ACCENT  = "#4a9eff"
_TEXT    = "#e6edf3"
_MUTED   = "#8b949e"
_GREEN   = "#3fb950"
_USER_BG = "#1a3050"
_ARIA_BG = "#1c2128"

_PANEL_W = 340


# ── Individual message bubble ─────────────────────────────────────────────────

class _Bubble(QFrame):
    def __init__(self, text: str, is_user: bool, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 2, 6, 2)
        lay.setSpacing(0)

        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setFont(QFont("Segoe UI", 11))
        lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        lbl.setMaximumWidth(260)
        lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        if is_user:
            lbl.setStyleSheet(f"""
                QLabel {{
                    background: {_USER_BG};
                    color: {_TEXT};
                    border: 1px solid {_ACCENT};
                    border-radius: 14px;
                    border-bottom-right-radius: 3px;
                    padding: 8px 13px;
                }}
            """)
            lay.addStretch()
            lay.addWidget(lbl)
        else:
            lbl.setStyleSheet(f"""
                QLabel {{
                    background: {_ARIA_BG};
                    color: {_TEXT};
                    border: 1px solid {_BORDER};
                    border-radius: 14px;
                    border-bottom-left-radius: 3px;
                    padding: 8px 13px;
                }}
            """)
            lay.addWidget(lbl)
            lay.addStretch()

        self.setStyleSheet("QFrame { background: transparent; border: none; }")


# ── Typing indicator ──────────────────────────────────────────────────────────

class _TypingIndicator(QLabel):
    def __init__(self, parent=None):
        super().__init__("  Aria is thinking", parent)
        self.setFont(QFont("Segoe UI", 10))
        self.setStyleSheet(f"color: {_MUTED}; background: transparent; padding: 0 16px;")
        self._dots = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def start(self):
        self._dots = 0
        self._timer.start(400)
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _tick(self):
        self._dots = (self._dots + 1) % 4
        self.setText("  Aria is thinking" + "." * self._dots)


# ── Main chat panel ───────────────────────────────────────────────────────────

class ChatPanel(QWidget):
    """
    Floating frameless panel that docks next to the main widget.
    Emits `message_sent(str)` when the user submits a message.
    """
    message_sent = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.Tool |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(_PANEL_W)
        self._excel_context: dict = {}
        self._setup_ui()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Card container
        card = QFrame()
        card.setObjectName("card")
        card.setStyleSheet(f"""
            QFrame#card {{
                background: {_DARK};
                border: 1px solid {_BORDER};
                border-radius: 16px;
            }}
        """)
        outer.addWidget(card)

        lay = QVBoxLayout(card)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        lay.addWidget(self._make_header())
        lay.addWidget(self._make_scroll())
        lay.addWidget(self._make_typing())
        lay.addWidget(self._make_input())

    def _make_header(self) -> QFrame:
        hdr = QFrame()
        hdr.setStyleSheet(f"""
            QFrame {{
                background: {_SURFACE};
                border-bottom: 1px solid {_BORDER};
                border-top-left-radius: 16px;
                border-top-right-radius: 16px;
            }}
        """)
        row = QHBoxLayout(hdr)
        row.setContentsMargins(14, 10, 14, 10)

        title = QLabel("◆  Aria")
        title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {_ACCENT}; background: transparent; border: none;")
        row.addWidget(title)
        row.addStretch()

        # Excel context badge
        self._badge = QLabel()
        self._badge.setFont(QFont("Segoe UI", 9))
        self._badge.setStyleSheet(f"""
            QLabel {{
                color: {_GREEN};
                background: transparent;
                border: 1px solid {_GREEN};
                border-radius: 8px;
                padding: 2px 8px;
            }}
        """)
        self._badge.hide()
        row.addWidget(self._badge)

        # Close button
        close = QPushButton("✕")
        close.setFixedSize(26, 26)
        close.setFont(QFont("Segoe UI", 10))
        close.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {_MUTED};
                border: none; border-radius: 13px;
            }}
            QPushButton:hover {{ color: {_TEXT}; background: {_RAISED}; }}
        """)
        close.clicked.connect(self.hide)
        row.addWidget(close)
        return hdr

    def _make_scroll(self) -> QScrollArea:
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll.setFixedHeight(360)
        self._scroll.setStyleSheet(f"""
            QScrollArea {{ background: {_DARK}; border: none; }}
            QScrollBar:vertical {{
                background: {_DARK}; width: 4px; border-radius: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {_BORDER}; border-radius: 2px; min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        self._msg_widget = QWidget()
        self._msg_widget.setStyleSheet(f"background: {_DARK};")
        self._msg_layout = QVBoxLayout(self._msg_widget)
        self._msg_layout.setContentsMargins(8, 14, 8, 10)
        self._msg_layout.setSpacing(6)
        self._msg_layout.addStretch()

        self._scroll.setWidget(self._msg_widget)
        return self._scroll

    def _make_typing(self) -> _TypingIndicator:
        self._typing = _TypingIndicator()
        self._typing.hide()
        return self._typing

    def _make_input(self) -> QFrame:
        bar = QFrame()
        bar.setStyleSheet(f"""
            QFrame {{
                background: {_SURFACE};
                border-top: 1px solid {_BORDER};
                border-bottom-left-radius: 16px;
                border-bottom-right-radius: 16px;
            }}
        """)
        row = QHBoxLayout(bar)
        row.setContentsMargins(12, 10, 12, 10)
        row.setSpacing(8)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Ask Aria anything…")
        self._input.setFont(QFont("Segoe UI", 11))
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: {_RAISED}; color: {_TEXT};
                border: 1px solid {_BORDER}; border-radius: 10px;
                padding: 8px 12px;
            }}
            QLineEdit:focus {{ border-color: {_ACCENT}; }}
        """)
        self._input.returnPressed.connect(self._on_send)
        row.addWidget(self._input)

        send = QPushButton("↑")
        send.setFixedSize(36, 36)
        send.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        send.setStyleSheet(f"""
            QPushButton {{
                background: {_ACCENT}; color: white;
                border: none; border-radius: 18px;
            }}
            QPushButton:hover  {{ background: #6ab0ff; }}
            QPushButton:pressed {{ background: #3a8eef; }}
            QPushButton:disabled {{ background: {_RAISED}; color: {_MUTED}; }}
        """)
        send.clicked.connect(self._on_send)
        self._send_btn = send
        row.addWidget(send)
        return bar

    # ── Public API ────────────────────────────────────────────────────────────

    def add_user_message(self, text: str):
        self._push_bubble(text, is_user=True)

    def add_aria_message(self, text: str):
        self._typing.stop()
        self._send_btn.setEnabled(True)
        self._push_bubble(text, is_user=False)

    def set_thinking(self, on: bool):
        if on:
            self._typing.start()
            self._send_btn.setEnabled(False)
        else:
            self._typing.stop()
            self._send_btn.setEnabled(True)

    def set_excel_context(self, ctx: dict):
        self._excel_context = ctx
        if ctx:
            sheet = ctx.get("sheet", "")
            addr  = ctx.get("address", "").split("!")[-1]  # strip sheet prefix
            self._badge.setText(f"📊 {sheet}  {addr}")
            self._badge.show()
            # Welcome message on first connection
            if not self._has_shown_excel_welcome:
                self._has_shown_excel_welcome = True
                rows = len(ctx.get("values", []))
                cols = len(ctx.get("values", [[]])[0]) if ctx.get("values") else 0
                self.add_aria_message(
                    f"I can see your Excel selection — "
                    f"**{sheet}!{addr}** ({rows}×{cols} cells). "
                    f"Ask me anything about it."
                )
        else:
            self._badge.hide()

    def get_excel_context(self) -> dict:
        return self._excel_context

    def show_near(self, widget_x: int, widget_y: int, widget_w: int, widget_h: int):
        """Position the panel beside the main widget and show it."""
        screen = QApplication.primaryScreen().geometry()
        panel_h = self.sizeHint().height()
        px = widget_x - _PANEL_W - 12
        if px < 0:
            px = widget_x + widget_w + 12
        py = max(0, min(widget_y, screen.height() - panel_h))
        self.move(px, py)
        self.show()
        self.raise_()
        self._input.setFocus()

    # ── Internal ──────────────────────────────────────────────────────────────

    _has_shown_excel_welcome = False

    def _push_bubble(self, text: str, is_user: bool):
        # Remove trailing stretch, insert bubble, re-add stretch
        count = self._msg_layout.count()
        item  = self._msg_layout.takeAt(count - 1)
        bubble = _Bubble(text, is_user)
        self._msg_layout.addWidget(bubble)
        if item:
            self._msg_layout.addItem(item)
        # Scroll to bottom after layout settles
        QTimer.singleShot(
            60,
            lambda: self._scroll.verticalScrollBar().setValue(
                self._scroll.verticalScrollBar().maximum()
            ),
        )

    def _on_send(self):
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self.add_user_message(text)
        self.set_thinking(True)
        self.message_sent.emit(text)
