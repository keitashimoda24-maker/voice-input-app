"""Floating mic indicator shown near the text cursor during recording.
Apple純正ディクテーション風のデザイン。"""

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPen,
    QRadialGradient,
)
from PyQt6.QtWidgets import QApplication, QWidget


class CursorMicIndicator(QWidget):
    """Apple風マイクバッジ - テキストカーソル付近に表示。"""

    SIZE = 42

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow)
        self.setFixedSize(self.SIZE, self.SIZE)

        self._pulse = 0.0
        self._pulse_dir = 1
        self._anim_timer = QTimer(self)
        self._anim_timer.setInterval(40)
        self._anim_timer.timeout.connect(self._tick)

    # ── 表示 / 非表示 ──────────────────────────────────────────────────────
    def show_at_cursor(self, pos=None):
        if pos is None:
            pos = _get_text_cursor_screen_pos()
        s = self.SIZE
        screen = QApplication.primaryScreen()

        if pos:
            wx, wy = pos[0] + 6, pos[1] + 4
        elif screen:
            geo = screen.availableGeometry()
            wx = geo.center().x() - s // 2
            wy = geo.bottom() - s - 140
        else:
            wx, wy = 200, 200

        if screen:
            geo = screen.geometry()
            wx = max(geo.left(), min(wx, geo.right() - s))
            wy = max(geo.top(), min(wy, geo.bottom() - s))

        self.move(wx, wy)
        self.show()
        self.raise_()
        self._anim_timer.start()

    def hide_indicator(self):
        self._anim_timer.stop()
        self.hide()

    # ── アニメーション ──────────────────────────────────────────────────────
    def _tick(self):
        self._pulse += self._pulse_dir * 0.035
        if self._pulse >= 1.0:
            self._pulse = 1.0
            self._pulse_dir = -1
        elif self._pulse <= 0.0:
            self._pulse = 0.0
            self._pulse_dir = 1
        self.update()

    # ── 描画（未来的デザイン） ──────────────────────────────────────────────
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = float(self.SIZE)
        cx = cy = s / 2

        # ── 外側パルスリング（呼吸するグロー）
        glow_r = cx - 1 + self._pulse * 4
        glow_alpha = int(40 + self._pulse * 60)
        p.setPen(QPen(QColor(0, 229, 255, glow_alpha), 2.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(cx - glow_r, cy - glow_r, glow_r * 2, glow_r * 2))

        # ── 背景円（ダーク半透明 + シアングロー、枠線なし）
        bg_r = cx - 5
        grad = QRadialGradient(cx, cy, bg_r * 1.2)
        grad.setColorAt(0.0, QColor(10, 20, 40, 230))
        grad.setColorAt(0.7, QColor(5, 15, 35, 240))
        grad.setColorAt(1.0, QColor(0, 10, 30, 220))
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)  # 枠線なし
        p.drawEllipse(QRectF(cx - bg_r, cy - bg_r, bg_r * 2, bg_r * 2))

        # ── 内側リングアクセント
        inner_r = bg_r - 1.5
        ring_alpha = int(100 + self._pulse * 80)
        p.setPen(QPen(QColor(0, 229, 255, ring_alpha), 1.2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2))

        # ── マイクアイコン（シアン発光）
        cyan = QColor(0, 229, 255)
        lw = max(1.3, s * 0.035)
        pen = QPen(cyan, lw)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)

        # マイク本体（太め＋塗りつぶし）
        bw, bh = s * 0.24, s * 0.30
        mic_top = cy - bh * 0.55
        mic_rect = QRectF(cx - bw / 2, mic_top, bw, bh)
        p.setBrush(QBrush(QColor(0, 229, 255, 60)))
        p.drawRoundedRect(mic_rect, bw / 2, bw / 2)

        # マイクの弧（大きめ）
        p.setBrush(Qt.BrushStyle.NoBrush)
        ar = s * 0.18
        arc_top = cy - bh * 0.02
        p.drawArc(QRectF(cx - ar, arc_top, ar * 2, ar * 1.2), 0, -180 * 16)

        # マイクスタンド（しっかり見える）
        stand_top = arc_top + ar * 0.6
        stand_bottom = stand_top + ar * 0.6
        p.drawLine(QPointF(cx, stand_top), QPointF(cx, stand_bottom))
        p.drawLine(QPointF(cx - ar * 0.6, stand_bottom), QPointF(cx + ar * 0.6, stand_bottom))

        p.end()


# ── テキストカーソル座標を取得（フォールバックチェーン） ──────────────────────


def _get_mouse_pos():
    """マウスカーソルの現在位置を返す (x, y)。"""
    try:
        from AppKit import NSEvent

        loc = NSEvent.mouseLocation()
        # AppKit座標系（左下原点）→ Qt座標系（左上原点）に変換
        from PyQt6.QtWidgets import QApplication

        screen = QApplication.primaryScreen()
        if screen:
            screen_h = screen.geometry().height()
            return (int(loc.x), int(screen_h - loc.y))
        return (int(loc.x), int(loc.y))
    except Exception:
        return None


def _get_ax_cursor_pos():
    """Accessibility API でテキストカーソル座標を取得。"""
    try:
        from ApplicationServices import (
            AXUIElementCopyAttributeValue,
            AXUIElementCopyParameterizedAttributeValue,
            AXUIElementCreateSystemWide,
        )

        system = AXUIElementCreateSystemWide()

        err, focused = AXUIElementCopyAttributeValue(system, "AXFocusedUIElement", None)
        if err != 0 or not focused:
            return None

        err, sel_range = AXUIElementCopyAttributeValue(focused, "AXSelectedTextRange", None)
        if err != 0 or sel_range is None:
            return None

        err, bounds = AXUIElementCopyParameterizedAttributeValue(focused, "AXBoundsForRange", sel_range, None)
        if err != 0 or bounds is None:
            return None

        rect = bounds.rectValue()
        x = int(rect.origin.x)
        y = int(rect.origin.y + rect.size.height)
        return (x, y)
    except Exception:
        return None


def _get_text_cursor_screen_pos():
    """テキストカーソル位置を返す。
    優先順位:
      1. Accessibility API（テキストカーソル）
      2. マウスカーソル位置（ユーザーは大抵入力欄の近くにいる）
    """
    pos = _get_ax_cursor_pos()
    if pos:
        return pos
    return _get_mouse_pos()
