"""
Pokemon character renderer using HD HOME sprites (PNG).
Animates via smooth floating, breathing and mood-based overlay effects.
"""
import math
import os
from PyQt6.QtCore import Qt, QRectF, QPointF
from PyQt6.QtGui import (
    QPainter, QColor, QPixmap, QPainterPath,
    QRadialGradient, QBrush, QPen, QFont, QTransform
)

from widget.animations import Mood
from widget.characters import sprite_manager

_MOOD_OVERLAY = {
    Mood.ALERT:     QColor(255, 40,  40,  90),
    Mood.ERROR:     QColor(180, 0,   0,   110),
    Mood.WARNING:   QColor(255, 140, 0,   80),
    Mood.HAPPY:     QColor(60,  210, 100, 50),
    Mood.INFO:      QColor(0,   200, 220, 50),
    Mood.ANALYZING: QColor(160, 80,  255, 60),
    Mood.THINKING:  QColor(80,  140, 255, 55),
    Mood.SLEEPING:  QColor(30,  30,  60,  130),
    Mood.BUSY:      None,
    Mood.IDLE:      None,
}

_MOOD_GLOW = {
    Mood.ALERT:     QColor(255, 40,  40,  130),
    Mood.ERROR:     QColor(180, 0,   0,   150),
    Mood.WARNING:   QColor(255, 140, 0,   110),
    Mood.HAPPY:     QColor(60,  210, 100, 110),
    Mood.INFO:      QColor(0,   200, 220, 110),
    Mood.ANALYZING: QColor(160, 80,  255, 110),
    Mood.THINKING:  QColor(80,  140, 255, 110),
    Mood.SLEEPING:  QColor(70,  70,  120, 70),
    Mood.BUSY:      QColor(200, 200, 255, 90),
    Mood.IDLE:      QColor(80,  140, 255, 70),
}


class PokemonCharacter:
    def __init__(self, pokemon_id: int, shiny: bool = False, repaint_callback=None):
        self.pokemon_id = pokemon_id
        self.shiny = shiny
        self._repaint = repaint_callback or (lambda: None)
        self._pixmap: QPixmap | None = None
        self._tick = 0
        self._loaded = False

    def load(self):
        """Call from main thread after sprites are downloaded."""
        variant = "front_shiny" if self.shiny else "front"
        path = sprite_manager.sprite_path(self.pokemon_id, variant)
        if path and os.path.exists(path):
            px = QPixmap(path)
            if not px.isNull():
                self._pixmap = px
                self._loaded = True
                self._repaint()
                return
        self._loaded = False

    def step(self):
        self._tick += 1

    def render(self, painter: QPainter, mood: Mood, size: int):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        t = self._tick
        cx, cy = size / 2.0, size / 2.0

        # ── Glow ─────────────────────────────────────────────────
        glow_col = _MOOD_GLOW.get(mood, QColor(80, 140, 255, 70))
        pulse = 1.0 + 0.1 * math.sin(t * 0.06)
        if mood == Mood.ALERT:
            pulse = 1.0 + 0.35 * abs(math.sin(t * 0.18))
        glow_r = size * 0.46 * pulse
        grad = QRadialGradient(QPointF(cx, cy), glow_r)
        glow_col.setAlpha(int(glow_col.alpha() * pulse))
        grad.setColorAt(0, glow_col)
        grad.setColorAt(1, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), glow_r, glow_r)

        if not self._loaded or not self._pixmap:
            # Placeholder while loading
            painter.setBrush(QBrush(QColor(40, 40, 60, 160)))
            painter.drawEllipse(QPointF(cx, cy), size * 0.32, size * 0.32)
            painter.setPen(QPen(QColor(180, 180, 255), 1))
            painter.setFont(QFont("Segoe UI", 9))
            painter.drawText(QRectF(0, cy - 12, size, 24),
                             Qt.AlignmentFlag.AlignCenter, "Loading...")
            return

        # ── Float + breathe animation ─────────────────────────────
        float_y  = math.sin(t * 0.045) * 4.5          # gentle bob
        breathe  = 1.0 + math.sin(t * 0.055) * 0.025  # subtle scale pulse

        if mood == Mood.SLEEPING:
            float_y  = math.sin(t * 0.025) * 2.5
            breathe  = 1.0 + math.sin(t * 0.03) * 0.015
        elif mood == Mood.HAPPY:
            float_y  = math.sin(t * 0.1) * 6.0
            breathe  = 1.0 + abs(math.sin(t * 0.08)) * 0.04
        elif mood == Mood.ALERT:
            float_y  = math.sin(t * 0.22) * 3.0       # jittery
            breathe  = 1.0 + abs(math.sin(t * 0.2)) * 0.05

        # Scale sprite to widget with padding
        pad = int(size * 0.10)
        max_dim = int((size - pad * 2) * breathe)

        scaled = self._pixmap.scaled(
            max_dim, max_dim,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        px = int(cx - scaled.width()  / 2)
        py = int(cy - scaled.height() / 2 + float_y)

        # ── Draw sprite ───────────────────────────────────────────
        painter.drawPixmap(px, py, scaled)

        # ── Colour overlay ────────────────────────────────────────
        overlay = _MOOD_OVERLAY.get(mood)
        if overlay:
            alpha = overlay.alpha()
            if mood == Mood.ALERT:
                alpha = int(alpha * (0.5 + 0.5 * abs(math.sin(t * 0.18))))
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceAtop)
            ov = QColor(overlay)
            ov.setAlpha(alpha)
            painter.fillRect(px, py, scaled.width(), scaled.height(), ov)
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver)

        # ── Sleeping Z's ──────────────────────────────────────────
        if mood == Mood.SLEEPING:
            for i, (zx, zy) in enumerate([
                (cx + size * 0.30, cy - size * 0.20),
                (cx + size * 0.40, cy - size * 0.34),
            ]):
                a = int(200 * abs(math.sin(t * 0.05 + i * 1.6)))
                zc = QColor(180, 180, 255, a)
                painter.setPen(QPen(zc, 1.2))
                painter.setFont(QFont("Segoe UI", 8 + i * 2, QFont.Weight.Bold))
                painter.drawText(QPointF(zx, zy), "z")

        # ── Busy spinner ──────────────────────────────────────────
        if mood == Mood.BUSY:
            angle = (t * 4) % 360
            ring = QColor(255, 255, 255, 160)
            painter.setPen(QPen(ring, 2.5))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            r = size * 0.44
            painter.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2),
                            int(angle * 16), int(110 * 16))

        # ── Sparkle dots for HAPPY ────────────────────────────────
        if mood == Mood.HAPPY:
            painter.setPen(Qt.PenStyle.NoPen)
            for i in range(5):
                a = math.radians(i * 72 + t * 3)
                sx = cx + math.cos(a) * size * 0.42
                sy = cy + math.sin(a) * size * 0.42
                alpha = int(200 * abs(math.sin(t * 0.1 + i)))
                sc = QColor(60, 220, 120, alpha)
                painter.setBrush(QBrush(sc))
                painter.drawEllipse(QPointF(sx, sy), 3, 3)
