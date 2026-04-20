from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QFont


ALERT_COLORS = {
    "low":    ("#1a2a3a", "#4a9eff", "#cce4ff"),
    "medium": ("#2a1a0a", "#ff9a00", "#ffe0b0"),
    "high":   ("#2a0a0a", "#ff3a3a", "#ffc0c0"),
}


class NotificationBubble(QWidget):
    def __init__(self, headline: str, message: str, suggestions: list[str],
                 alert_level: str = "low", duration_ms: int = 8000, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        bg, border, text = ALERT_COLORS.get(alert_level, ALERT_COLORS["low"])
        self._border_color = border

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(6)

        hl = QLabel(headline)
        hl.setStyleSheet(f"color: {border}; font-weight: bold; font-size: 12px;")
        hl.setWordWrap(True)
        root.addWidget(hl)

        msg = QLabel(message)
        msg.setStyleSheet(f"color: {text}; font-size: 11px;")
        msg.setWordWrap(True)
        msg.setMaximumWidth(280)
        root.addWidget(msg)

        for tip in suggestions[:2]:
            t = QLabel(f"• {tip}")
            t.setStyleSheet(f"color: {text}; font-size: 10px; opacity: 0.8;")
            t.setWordWrap(True)
            t.setMaximumWidth(280)
            root.addWidget(t)

        self._bg_color = bg
        self.setFixedWidth(320)
        self.adjustSize()

        self._opacity_value = 0.0
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(300)
        anim.setStartValue(0.0)
        anim.setEndValue(0.95)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._anim = anim

        QTimer.singleShot(duration_ms, self._fade_out)

    def _fade_out(self):
        anim = QPropertyAnimation(self, b"windowOpacity")
        anim.setDuration(400)
        anim.setStartValue(self.windowOpacity())
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        anim.finished.connect(self.close)
        anim.start()
        self._fade_anim = anim

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 12, 12)

        painter.setPen(Qt.PenStyle.NoPen)
        bg = QColor(self._bg_color)
        bg.setAlpha(230)
        painter.setBrush(bg)
        painter.drawPath(path)

        border = QColor(self._border_color)
        border.setAlpha(180)
        from PyQt6.QtGui import QPen
        painter.setPen(QPen(border, 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
