"""
Holographic AI-core widget renderer.
Draws a hexagonal scanning avatar with circuit accents, sweep beam,
pulsing core, and mood-reactive colour + motion effects.
"""
import math
from enum import Enum
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush,
    QRadialGradient, QLinearGradient,
    QPainterPath, QFont
)


# ── Mood enum ────────────────────────────────────────────────────────────────

class Mood(Enum):
    IDLE      = "IDLE"
    THINKING  = "THINKING"
    ALERT     = "ALERT"
    INFO      = "INFO"
    WARNING   = "WARNING"
    HAPPY     = "HAPPY"
    ANALYZING = "ANALYZING"
    SLEEPING  = "SLEEPING"
    BUSY      = "BUSY"
    ERROR     = "ERROR"


# ── Per-mood colour palette ──────────────────────────────────────────────────

_PALETTE = {
    Mood.IDLE:      {"primary": QColor(0,   200, 255),  "secondary": QColor(0,   120, 200),  "accent": QColor(100, 230, 255)},
    Mood.THINKING:  {"primary": QColor(255, 210, 40),   "secondary": QColor(200, 140, 0),    "accent": QColor(255, 235, 120)},
    Mood.ALERT:     {"primary": QColor(255, 50,  50),   "secondary": QColor(180, 0,   0),    "accent": QColor(255, 130, 130)},
    Mood.INFO:      {"primary": QColor(0,   230, 200),  "secondary": QColor(0,   150, 140),  "accent": QColor(80,  255, 230)},
    Mood.WARNING:   {"primary": QColor(255, 160, 0),    "secondary": QColor(180, 90,  0),    "accent": QColor(255, 200, 80)},
    Mood.HAPPY:     {"primary": QColor(50,  220, 120),  "secondary": QColor(0,   150, 70),   "accent": QColor(120, 255, 170)},
    Mood.ANALYZING: {"primary": QColor(180, 80,  255),  "secondary": QColor(100, 0,   200),  "accent": QColor(210, 140, 255)},
    Mood.SLEEPING:  {"primary": QColor(80,  90,  120),  "secondary": QColor(50,  55,  80),   "accent": QColor(110, 120, 160)},
    Mood.BUSY:      {"primary": QColor(220, 220, 255),  "secondary": QColor(120, 120, 200),  "accent": QColor(255, 255, 255)},
    Mood.ERROR:     {"primary": QColor(220, 30,  30),   "secondary": QColor(140, 0,   0),    "accent": QColor(255, 80,  80)},
}


# ── Animation state ──────────────────────────────────────────────────────────

class AnimationState:
    def __init__(self):
        self.tick = 0
        self.mood = Mood.IDLE
        self._prev_mood = Mood.IDLE
        self._transition_ticks = 0
        self.transition_alpha = 1.0

    def set_mood(self, mood: Mood):
        if mood != self.mood:
            self._prev_mood = self.mood
            self.mood = mood
            self._transition_ticks = 20
            self.transition_alpha = 0.0

    def step(self):
        self.tick += 1
        if self._transition_ticks > 0:
            self._transition_ticks -= 1
            self.transition_alpha = 1.0 - self._transition_ticks / 20.0


# ── Helpers ──────────────────────────────────────────────────────────────────

def _hex_points(cx: float, cy: float, r: float, rotation: float = 0.0) -> list[QPointF]:
    """Return 6 vertices of a regular hexagon."""
    pts = []
    for i in range(6):
        angle = math.radians(60 * i + rotation)
        pts.append(QPointF(cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return pts


def _hex_path(cx: float, cy: float, r: float, rotation: float = 0.0) -> QPainterPath:
    pts = _hex_points(cx, cy, r, rotation)
    path = QPainterPath()
    path.moveTo(pts[0])
    for p in pts[1:]:
        path.lineTo(p)
    path.closeSubpath()
    return path


def _col(base: QColor, alpha: int) -> QColor:
    c = QColor(base)
    c.setAlpha(alpha)
    return c


# ── Main draw entry point ────────────────────────────────────────────────────

def draw_widget(painter: QPainter, state: AnimationState, size: int):
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

    cx  = size / 2.0
    cy  = size / 2.0
    r   = size / 2.0 - 6          # outer hex radius
    t   = state.tick
    mood = state.mood
    pal  = _PALETTE[mood]

    _draw_outer_glow(painter, cx, cy, r, t, mood, pal)
    _draw_hex_frame(painter, cx, cy, r, t, mood, pal)
    _draw_circuit_corners(painter, cx, cy, r, t, pal)
    _draw_scan_beam(painter, cx, cy, r, t, mood, pal)
    _draw_core(painter, cx, cy, r, t, mood, pal)
    _draw_data_particles(painter, cx, cy, r, t, mood, pal)
    _draw_mood_overlay(painter, cx, cy, r, t, mood, pal)
    _draw_hud_label(painter, cx, cy, r, t, mood, pal)


# ── Outer ambient glow ───────────────────────────────────────────────────────

def _draw_outer_glow(painter, cx, cy, r, t, mood, pal):
    pulse = 1.0 + 0.12 * math.sin(t * 0.06)
    if mood == Mood.ALERT:
        pulse = 1.0 + 0.4 * abs(math.sin(t * 0.22))
    elif mood == Mood.BUSY:
        pulse = 1.0 + 0.18 * abs(math.sin(t * 0.18))

    glow_r = r * 1.45 * pulse
    grad = QRadialGradient(QPointF(cx, cy), glow_r)
    g0 = _col(pal["primary"], int(55 * pulse))
    grad.setColorAt(0.0, g0)
    grad.setColorAt(0.55, _col(pal["primary"], int(18 * pulse)))
    grad.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setBrush(QBrush(grad))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(QPointF(cx, cy), glow_r, glow_r)


# ── Hexagonal frame ──────────────────────────────────────────────────────────

def _draw_hex_frame(painter, cx, cy, r, t, mood, pal):
    rot_speed = {
        Mood.IDLE:      0.3,
        Mood.THINKING:  1.2,
        Mood.ANALYZING: 2.0,
        Mood.BUSY:      3.5,
        Mood.ALERT:     2.5,
        Mood.SLEEPING:  0.08,
        Mood.HAPPY:     0.7,
        Mood.INFO:      0.5,
        Mood.WARNING:   1.0,
        Mood.ERROR:     2.8,
    }.get(mood, 0.3)

    rotation = (t * rot_speed) % 360

    # Outer hex — faint fill + bright border
    outer_path = _hex_path(cx, cy, r * 0.92, rotation)
    fill_grad = QRadialGradient(QPointF(cx, cy), r)
    fill_grad.setColorAt(0.0, _col(pal["secondary"], 35))
    fill_grad.setColorAt(1.0, _col(pal["secondary"], 8))
    painter.setBrush(QBrush(fill_grad))

    border_alpha = 200
    if mood == Mood.ALERT:
        border_alpha = int(200 * abs(math.sin(t * 0.22))) + 55
    elif mood == Mood.SLEEPING:
        border_alpha = 80
    pen_w = 1.8 if mood != Mood.ALERT else 2.5
    painter.setPen(QPen(_col(pal["primary"], border_alpha), pen_w))
    painter.drawPath(outer_path)

    # Inner hex — counter-rotating, thinner
    inner_path = _hex_path(cx, cy, r * 0.70, -rotation * 0.6)
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(QPen(_col(pal["accent"], 80), 0.9))
    painter.drawPath(inner_path)

    # Vertex dots on outer hex
    pts = _hex_points(cx, cy, r * 0.92, rotation)
    painter.setBrush(QBrush(_col(pal["accent"], 200)))
    painter.setPen(Qt.PenStyle.NoPen)
    dot_r = 2.2
    for p in pts:
        painter.drawEllipse(p, dot_r, dot_r)


# ── Circuit-style corner brackets ────────────────────────────────────────────

def _draw_circuit_corners(painter, cx, cy, r, t, pal):
    """Four L-shaped bracket accents at cardinal points just outside the hex."""
    arm   = r * 0.22      # bracket arm length
    gap   = r * 1.05      # distance from centre
    alpha = 140
    pen   = QPen(_col(pal["accent"], alpha), 1.2)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    offsets = [
        ( gap,    0,    1,  0,  0,  1),   # right  → arms go left + down
        (-gap,    0,   -1,  0,  0,  1),   # left   → arms go right + down
        ( 0,    -gap,   0,  1,  1,  0),   # top    → arms go down + right
        ( 0,     gap,   0, -1,  1,  0),   # bottom → arms go up + right
    ]
    for ox, oy, dx1, dy1, dx2, dy2 in offsets:
        bx, by = cx + ox, cy + oy
        painter.drawLine(QPointF(bx, by), QPointF(bx + dx1 * arm, by + dy1 * arm))
        painter.drawLine(QPointF(bx, by), QPointF(bx + dx2 * arm, by + dy2 * arm))


# ── Scan beam ────────────────────────────────────────────────────────────────

def _draw_scan_beam(painter, cx, cy, r, t, mood, pal):
    if mood == Mood.SLEEPING:
        return

    speed = {
        Mood.IDLE:      1.2,
        Mood.THINKING:  2.0,
        Mood.ANALYZING: 2.8,
        Mood.BUSY:      4.0,
        Mood.ALERT:     3.5,
        Mood.HAPPY:     1.5,
        Mood.INFO:      1.8,
        Mood.WARNING:   2.2,
        Mood.ERROR:     4.5,
    }.get(mood, 1.2)

    # Beam sweeps top-to-bottom inside hex bounding box
    cycle = (t * speed) % 200      # 0..200
    frac  = cycle / 200.0          # 0..1
    beam_y = (cy - r * 0.82) + frac * r * 1.64

    # Clip to hex shape
    hex_clip = _hex_path(cx, cy, r * 0.90, 0)
    painter.save()
    painter.setClipPath(hex_clip)

    beam_alpha = int(120 * (1.0 - abs(frac - 0.5) * 2))   # fade at edges
    beam_col   = _col(pal["accent"], beam_alpha)

    # Beam line
    half_w = r * 0.88
    painter.setPen(QPen(beam_col, 1.2))
    painter.drawLine(QPointF(cx - half_w, beam_y), QPointF(cx + half_w, beam_y))

    # Glow strip above beam
    strip_h = r * 0.18
    grad = QLinearGradient(QPointF(cx, beam_y - strip_h), QPointF(cx, beam_y))
    grad.setColorAt(0.0, QColor(0, 0, 0, 0))
    g1 = _col(pal["primary"], int(40 * (beam_alpha / 120)))
    grad.setColorAt(1.0, g1)
    painter.fillRect(
        QRectF(cx - half_w, beam_y - strip_h, half_w * 2, strip_h),
        QBrush(grad)
    )

    painter.restore()


# ── Central core ─────────────────────────────────────────────────────────────

def _draw_core(painter, cx, cy, r, t, mood, pal):
    # Core radius breathes
    breathe = 1.0 + 0.08 * math.sin(t * 0.07)
    if mood == Mood.ALERT:
        breathe = 1.0 + 0.22 * abs(math.sin(t * 0.25))
    elif mood == Mood.SLEEPING:
        breathe = 1.0 + 0.03 * math.sin(t * 0.03)
    elif mood == Mood.HAPPY:
        breathe = 1.0 + 0.13 * abs(math.sin(t * 0.12))

    core_r = r * 0.30 * breathe

    # Deep glow behind core
    deep = QRadialGradient(QPointF(cx, cy), core_r * 2.2)
    deep.setColorAt(0.0, _col(pal["primary"], 80))
    deep.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setBrush(QBrush(deep))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(QPointF(cx, cy), core_r * 2.2, core_r * 2.2)

    # Core orb — radial gradient, off-centre highlight
    grad = QRadialGradient(
        QPointF(cx - core_r * 0.3, cy - core_r * 0.3), core_r * 1.1
    )
    grad.setColorAt(0.0, _col(pal["accent"], 255))
    grad.setColorAt(0.45, _col(pal["primary"], 220))
    grad.setColorAt(1.0,  _col(pal["secondary"], 180))
    painter.setBrush(QBrush(grad))
    painter.setPen(QPen(_col(pal["accent"], 160), 1.0))
    painter.drawEllipse(QPointF(cx, cy), core_r, core_r)

    # Specular highlight — small white blip top-left
    spec_r = core_r * 0.28
    spec_grad = QRadialGradient(
        QPointF(cx - core_r * 0.32, cy - core_r * 0.32), spec_r
    )
    spec_grad.setColorAt(0.0, QColor(255, 255, 255, 210))
    spec_grad.setColorAt(1.0, QColor(255, 255, 255, 0))
    painter.setBrush(QBrush(spec_grad))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(
        QPointF(cx - core_r * 0.32, cy - core_r * 0.32), spec_r, spec_r
    )


# ── Floating data particles ───────────────────────────────────────────────────

def _draw_data_particles(painter, cx, cy, r, t, mood, pal):
    if mood == Mood.SLEEPING:
        _draw_zzz(painter, cx, cy, r, t, pal)
        return

    count = {
        Mood.IDLE:      5,
        Mood.THINKING:  7,
        Mood.ANALYZING: 10,
        Mood.BUSY:      12,
        Mood.ALERT:     6,
        Mood.HAPPY:     8,
        Mood.INFO:      6,
        Mood.WARNING:   6,
        Mood.ERROR:     8,
    }.get(mood, 5)

    orbit_r = r * 0.72
    speed   = {
        Mood.BUSY:      5.5,
        Mood.ANALYZING: 4.0,
        Mood.ALERT:     4.5,
        Mood.ERROR:     5.0,
        Mood.THINKING:  3.0,
        Mood.HAPPY:     2.5,
    }.get(mood, 1.8)

    painter.setPen(Qt.PenStyle.NoPen)
    for i in range(count):
        phase  = (2 * math.pi * i / count)
        angle  = math.radians(t * speed + math.degrees(phase))
        # Each particle has a slight radial oscillation
        osc    = orbit_r * (0.85 + 0.15 * math.sin(t * 0.07 + i))
        px     = cx + math.cos(angle) * osc
        py     = cy + math.sin(angle) * osc
        alpha  = int(200 * (0.5 + 0.5 * math.sin(t * 0.09 + i * 1.1)))
        dot_r  = 1.8 + 0.8 * math.sin(t * 0.05 + i)
        painter.setBrush(QBrush(_col(pal["accent"], alpha)))
        painter.drawEllipse(QPointF(px, py), dot_r, dot_r)


def _draw_zzz(painter, cx, cy, r, t, pal):
    positions = [
        (cx + r * 0.55, cy - r * 0.25, 8),
        (cx + r * 0.70, cy - r * 0.48, 10),
    ]
    for i, (zx, zy, fsize) in enumerate(positions):
        alpha = int(200 * abs(math.sin(t * 0.04 + i * 1.8)))
        painter.setPen(QPen(_col(pal["accent"], alpha), 1.2))
        painter.setFont(QFont("Segoe UI", fsize, QFont.Weight.Bold))
        painter.drawText(QPointF(zx, zy), "z")


# ── Mood-specific overlays ────────────────────────────────────────────────────

def _draw_mood_overlay(painter, cx, cy, r, t, mood, pal):

    if mood in (Mood.THINKING, Mood.ANALYZING, Mood.BUSY):
        _draw_spinner_rings(painter, cx, cy, r, t, mood, pal)

    elif mood == Mood.ALERT:
        _draw_alert_pulse(painter, cx, cy, r, t, pal)

    elif mood == Mood.WARNING:
        _draw_warning_ring(painter, cx, cy, r, t, pal)

    elif mood == Mood.HAPPY:
        _draw_happy_sparks(painter, cx, cy, r, t, pal)

    elif mood == Mood.ERROR:
        _draw_error_glitch(painter, cx, cy, r, t, pal)


def _draw_spinner_rings(painter, cx, cy, r, t, mood, pal):
    configs = {
        Mood.THINKING:  [(r * 1.1, 2,   90,  1.5), (r * 0.85, -3,  60, 1.0)],
        Mood.ANALYZING: [(r * 1.1, 3,  240,  1.8), (r * 0.88, -4, 120, 1.1), (r * 1.25, 1.5, 60, 0.8)],
        Mood.BUSY:      [(r * 1.1, 6,   90,  2.2), (r * 0.82, -8, 120, 1.4)],
    }
    for ring_r, spd, span, width in configs.get(mood, []):
        angle = (t * spd) % 360
        painter.setPen(QPen(_col(pal["accent"], 160), width))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawArc(
            QRectF(cx - ring_r, cy - ring_r, ring_r * 2, ring_r * 2),
            int(angle * 16), int(span * 16)
        )


def _draw_alert_pulse(painter, cx, cy, r, t, pal):
    alpha = int(255 * abs(math.sin(t * 0.28)))
    for scale in (1.05, 1.22):
        painter.setPen(QPen(_col(pal["primary"], int(alpha * 0.8)), 2.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        rr = r * scale
        painter.drawEllipse(QPointF(cx, cy), rr, rr)


def _draw_warning_ring(painter, cx, cy, r, t, pal):
    scale = 1.0 + 0.12 * abs(math.sin(t * 0.10))
    painter.setPen(QPen(_col(pal["primary"], 200), 2.0))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    rr = r * scale * 1.1
    painter.drawEllipse(QPointF(cx, cy), rr, rr)


def _draw_happy_sparks(painter, cx, cy, r, t, pal):
    painter.setPen(Qt.PenStyle.NoPen)
    for i in range(6):
        angle  = math.radians(i * 60 + t * 2.5)
        dist   = r * (1.15 + 0.08 * math.sin(t * 0.09 + i))
        px     = cx + math.cos(angle) * dist
        py     = cy + math.sin(angle) * dist
        alpha  = int(210 * abs(math.sin(t * 0.12 + i)))
        spark_r = 2.5 + 1.0 * math.sin(t * 0.08 + i)
        painter.setBrush(QBrush(_col(pal["accent"], alpha)))
        painter.drawEllipse(QPointF(px, py), spark_r, spark_r)


def _draw_error_glitch(painter, cx, cy, r, t, pal):
    """Horizontal glitch bars inside the hex."""
    if t % 18 < 3:          # glitch fires occasionally
        import random
        rng = random.Random(t // 6)   # deterministic per glitch cycle
        painter.setPen(Qt.PenStyle.NoPen)
        hex_clip = _hex_path(cx, cy, r * 0.88, 0)
        painter.save()
        painter.setClipPath(hex_clip)
        for _ in range(3):
            gy    = cy + rng.uniform(-r * 0.6, r * 0.6)
            gw    = rng.uniform(r * 0.3, r * 0.8)
            gh    = rng.uniform(2, 5)
            galpha= rng.randint(60, 140)
            painter.fillRect(
                QRectF(cx - gw / 2, gy, gw, gh),
                _col(pal["accent"], galpha)
            )
        painter.restore()


# ── HUD label (mood name + tiny status dot) ──────────────────────────────────

def _draw_hud_label(painter, cx, cy, r, t, mood, pal):
    if mood == Mood.SLEEPING:
        return

    label = {
        Mood.IDLE:      "IDLE",
        Mood.THINKING:  "THINKING",
        Mood.ALERT:     "ALERT",
        Mood.INFO:      "INFO",
        Mood.WARNING:   "WARN",
        Mood.HAPPY:     "OK",
        Mood.ANALYZING: "SCANNING",
        Mood.BUSY:      "BUSY",
        Mood.ERROR:     "ERROR",
    }.get(mood, "")

    if not label:
        return

    # Tiny label at bottom of hex
    label_y = cy + r * 0.78
    alpha    = int(160 * (0.7 + 0.3 * math.sin(t * 0.05)))
    painter.setPen(QPen(_col(pal["primary"], alpha), 1))
    f = QFont("Consolas", 6, QFont.Weight.Bold)
    f.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 1.5)
    painter.setFont(f)

    fm_rect = QRectF(cx - r, label_y - 8, r * 2, 14)
    painter.drawText(fm_rect, Qt.AlignmentFlag.AlignHCenter, label)

    # Status dot left of label
    dot_alpha = int(255 * abs(math.sin(t * 0.08)))
    painter.setBrush(QBrush(_col(pal["accent"], dot_alpha)))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(QPointF(cx - r * 0.38, label_y - 1.5), 2.0, 2.0)
