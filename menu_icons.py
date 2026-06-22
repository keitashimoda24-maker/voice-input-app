"""Menu icons drawn with QPainter -- no external SVG files needed."""

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

_SZ = 16
_CLR = QColor(180, 195, 220)  # light steel-blue for dark menu background


def _make(draw_fn) -> QIcon:
    px = QPixmap(_SZ, _SZ)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    draw_fn(p, float(_SZ))
    p.end()
    return QIcon(px)


def _pen(p: QPainter, width: float = 1.5):
    pen = QPen(_CLR, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)


def _brush(p: QPainter):
    p.setBrush(QBrush(_CLR))


# ── 1. Microphone ────────────────────────────────────────────────
def icon_mic() -> QIcon:
    def draw(p: QPainter, s: float):
        _pen(p, 1.5)
        # mic head (rounded rect)
        cx, top, w, h = s * 0.5, s * 0.15, s * 0.30, s * 0.42
        path = QPainterPath()
        path.addRoundedRect(QRectF(cx - w / 2, top, w, h), w / 2, w / 2)
        p.drawPath(path)
        # arc beneath
        arc_y = top + h - s * 0.08
        arc_w, arc_h = s * 0.50, s * 0.36
        p.drawArc(QRectF(cx - arc_w / 2, arc_y, arc_w, arc_h), 0 * 16, -180 * 16)
        # stem
        stem_top = arc_y + arc_h / 2
        stem_bot = s * 0.88
        p.drawLine(QPointF(cx, stem_top), QPointF(cx, stem_bot))
        # base
        p.drawLine(QPointF(cx - s * 0.15, stem_bot), QPointF(cx + s * 0.15, stem_bot))

    return _make(draw)


# ── 2. Note / Stylus (voice memo) ───────────────────────────────
def icon_memo() -> QIcon:
    def draw(p: QPainter, s: float):
        _pen(p, 1.5)
        # notepad body
        p.drawRoundedRect(QRectF(s * 0.18, s * 0.10, s * 0.50, s * 0.75), 1.5, 1.5)
        # lines on notepad
        for y_frac in (0.32, 0.47, 0.62):
            y = s * y_frac
            p.drawLine(QPointF(s * 0.28, y), QPointF(s * 0.58, y))
        # pencil overlay (small diagonal)
        pen_bx, pen_by = s * 0.82, s * 0.82
        pen_tx, pen_ty = s * 0.58, s * 0.58
        p.drawLine(QPointF(pen_tx, pen_ty), QPointF(pen_bx, pen_by))
        # pencil tip
        p.drawLine(QPointF(pen_bx, pen_by), QPointF(pen_bx + s * 0.02, pen_by + s * 0.06))
        # small angle lines for pencil body
        off = s * 0.04
        p.drawLine(QPointF(pen_tx - off, pen_ty + off), QPointF(pen_bx - off, pen_by + off))

    return _make(draw)


# ── 3. Clipboard ─────────────────────────────────────────────────
def icon_clipboard() -> QIcon:
    def draw(p: QPainter, s: float):
        _pen(p, 1.5)
        # board
        p.drawRoundedRect(QRectF(s * 0.15, s * 0.18, s * 0.70, s * 0.72), 2.0, 2.0)
        # clip at top
        clip_w = s * 0.28
        clip_h = s * 0.16
        cx = s * 0.5
        p.drawRoundedRect(QRectF(cx - clip_w / 2, s * 0.08, clip_w, clip_h), 2.0, 2.0)
        # lines on board
        for y_frac in (0.45, 0.58, 0.71):
            y = s * y_frac
            p.drawLine(QPointF(s * 0.30, y), QPointF(s * 0.70, y))

    return _make(draw)


# ── 4. Clock / History ───────────────────────────────────────────
def icon_history() -> QIcon:
    def draw(p: QPainter, s: float):
        _pen(p, 1.5)
        cx, cy, r = s * 0.52, s * 0.52, s * 0.36
        # clock circle
        p.drawEllipse(QPointF(cx, cy), r, r)
        # hour hand (pointing to ~10 o'clock)
        p.drawLine(QPointF(cx, cy), QPointF(cx - s * 0.12, cy - s * 0.18))
        # minute hand (pointing to 12)
        p.drawLine(QPointF(cx, cy), QPointF(cx + s * 0.18, cy + s * 0.04))
        # CCW arrow at 9-o'clock position
        ax, ay = cx - r - s * 0.02, cy
        _pen(p, 1.3)
        p.drawLine(QPointF(ax, ay), QPointF(ax + s * 0.08, ay - s * 0.08))
        p.drawLine(QPointF(ax, ay), QPointF(ax + s * 0.08, ay + s * 0.06))

    return _make(draw)


# ── 5. Pencil + Brain (learn / correction) ──────────────────────
def icon_learn() -> QIcon:
    def draw(p: QPainter, s: float):
        _pen(p, 1.4)
        # lightbulb shape (knowledge symbol) -- top half
        cx, cy = s * 0.5, s * 0.38
        r = s * 0.24
        p.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2), 40 * 16, 280 * 16)
        # two short lines going down from bulb
        p.drawLine(QPointF(cx - s * 0.10, cy + r * 0.92), QPointF(cx - s * 0.10, cy + r + s * 0.12))
        p.drawLine(QPointF(cx + s * 0.10, cy + r * 0.92), QPointF(cx + s * 0.10, cy + r + s * 0.12))
        # base lines
        by = cy + r + s * 0.12
        p.drawLine(QPointF(cx - s * 0.12, by), QPointF(cx + s * 0.12, by))
        p.drawLine(QPointF(cx - s * 0.08, by + s * 0.07), QPointF(cx + s * 0.08, by + s * 0.07))
        # filament inside bulb
        _pen(p, 1.0)
        p.drawLine(QPointF(cx, cy - s * 0.04), QPointF(cx - s * 0.06, cy + s * 0.08))
        p.drawLine(QPointF(cx, cy - s * 0.04), QPointF(cx + s * 0.06, cy + s * 0.08))

    return _make(draw)


# ── 6. Magnifying glass (research) ──────────────────────────────
def icon_research() -> QIcon:
    def draw(p: QPainter, s: float):
        _pen(p, 1.5)
        cx, cy, r = s * 0.42, s * 0.42, s * 0.26
        p.drawEllipse(QPointF(cx, cy), r, r)
        # handle
        import math

        hx = cx + r * math.cos(math.radians(315))
        hy = cy - r * math.sin(math.radians(315))
        _pen(p, 2.0)
        p.drawLine(QPointF(hx, hy), QPointF(s * 0.85, s * 0.85))

    return _make(draw)


# ── 7. Gear (settings) ──────────────────────────────────────────
def icon_settings() -> QIcon:
    def draw(p: QPainter, s: float):
        import math

        cx, cy = s * 0.5, s * 0.5
        r_out, r_in = s * 0.40, s * 0.28
        teeth = 8
        # build gear path
        path = QPainterPath()
        for i in range(teeth):
            a1 = math.radians(i * 360 / teeth - 12)
            a2 = math.radians(i * 360 / teeth + 12)
            a3 = math.radians(i * 360 / teeth + 360 / teeth / 2 - 10)
            a4 = math.radians(i * 360 / teeth + 360 / teeth / 2 + 10)
            pts = [
                QPointF(cx + r_out * math.cos(a1), cy + r_out * math.sin(a1)),
                QPointF(cx + r_out * math.cos(a2), cy + r_out * math.sin(a2)),
                QPointF(cx + r_in * math.cos(a3), cy + r_in * math.sin(a3)),
                QPointF(cx + r_in * math.cos(a4), cy + r_in * math.sin(a4)),
            ]
            if i == 0:
                path.moveTo(pts[0])
            else:
                path.lineTo(pts[0])
            path.lineTo(pts[1])
            path.lineTo(pts[2])
            path.lineTo(pts[3])
        path.closeSubpath()
        _pen(p, 1.3)
        p.drawPath(path)
        # center circle
        p.drawEllipse(QPointF(cx, cy), s * 0.10, s * 0.10)

    return _make(draw)


# ── 8. Circular arrow (restart) ─────────────────────────────────
def icon_restart() -> QIcon:
    def draw(p: QPainter, s: float):
        _pen(p, 1.5)
        cx, cy, r = s * 0.5, s * 0.5, s * 0.32
        # arc ~300 degrees
        rect = QRectF(cx - r, cy - r, r * 2, r * 2)
        p.drawArc(rect, 60 * 16, 300 * 16)
        # arrowhead at the end of the arc (top-right area)
        import math

        end_angle = math.radians(60)
        ax = cx + r * math.cos(end_angle)
        ay = cy - r * math.sin(end_angle)
        # two arrow lines
        p.drawLine(QPointF(ax, ay), QPointF(ax + s * 0.10, ay + s * 0.02))
        p.drawLine(QPointF(ax, ay), QPointF(ax - s * 0.01, ay + s * 0.11))

    return _make(draw)


# ── 9. Power / X (quit) ─────────────────────────────────────────
def icon_quit() -> QIcon:
    def draw(p: QPainter, s: float):
        _pen(p, 1.5)
        cx, cy, r = s * 0.5, s * 0.52, s * 0.32
        # power arc (open at top)
        rect = QRectF(cx - r, cy - r, r * 2, r * 2)
        p.drawArc(rect, 50 * 16, 260 * 16)
        # vertical line at top (power symbol stem)
        p.drawLine(QPointF(cx, cy - r - s * 0.06), QPointF(cx, cy))

    return _make(draw)
