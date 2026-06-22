"""Bottom overlay bar shown during recording – AquaVoice-inspired design."""

import random
import subprocess

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QHBoxLayout, QWidget


class AudioDotsWidget(QWidget):
    """Animated dot visualization of audio level (AquaVoice style)."""

    DOT_COUNT = 10

    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = 0.0
        self._dot_sizes = [0.0] * self.DOT_COUNT
        dot_diameter = 7
        gap = 6
        self.setFixedSize(self.DOT_COUNT * dot_diameter + (self.DOT_COUNT - 1) * gap, 36)

    def set_level(self, level: float):
        self._level = level
        for i in range(self.DOT_COUNT):
            center_factor = 1.0 - abs(i - self.DOT_COUNT / 2) / (self.DOT_COUNT / 2) * 0.3
            target = level * center_factor * (0.6 + random.random() * 0.8)
            target = min(target, 1.0)
            if target > self._dot_sizes[i]:
                self._dot_sizes[i] += (target - self._dot_sizes[i]) * 0.5
            else:
                self._dot_sizes[i] += (target - self._dot_sizes[i]) * 0.12
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        dot_d = 7
        gap = 6
        total = self.DOT_COUNT * dot_d + (self.DOT_COUNT - 1) * gap
        x_start = (w - total) // 2
        cy = h / 2

        for i, size_ratio in enumerate(self._dot_sizes):
            x = x_start + i * (dot_d + gap) + dot_d / 2
            # Base size 4, max 8 based on level
            r = 2.0 + size_ratio * 2.0
            alpha = int(120 + size_ratio * 135)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(0, 229, 255, alpha)))
            painter.drawEllipse(QPointF(x, cy), r, r)
        painter.end()


class MicIconWidget(QWidget):
    """Custom-drawn cyan microphone icon (no emoji)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(28, 36)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = float(self.width())
        h = float(self.height())
        cx = w / 2
        cy = h / 2

        cyan = QColor(0, 229, 255)
        pen = QPen(cyan, 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)

        # Mic body
        bw, bh = w * 0.36, h * 0.38
        mic_top = cy - bh * 0.6
        mic_rect = QRectF(cx - bw / 2, mic_top, bw, bh)
        p.setBrush(QBrush(QColor(0, 229, 255, 50)))
        p.drawRoundedRect(mic_rect, bw / 2, bw / 2)

        # Arc
        p.setBrush(Qt.BrushStyle.NoBrush)
        ar = w * 0.28
        arc_top = cy + bh * 0.05
        p.drawArc(QRectF(cx - ar, arc_top - ar * 0.3, ar * 2, ar * 1.4), 0, -180 * 16)

        # Stand
        stand_top = arc_top + ar * 0.4
        stand_bottom = stand_top + ar * 0.5
        p.drawLine(QPointF(cx, stand_top), QPointF(cx, stand_bottom))
        p.drawLine(QPointF(cx - ar * 0.5, stand_bottom), QPointF(cx + ar * 0.5, stand_bottom))

        p.end()


class RecordingOverlay(QWidget):
    """Pill-shaped floating bar at the bottom of the screen – AquaVoice style."""

    def __init__(self, recorder, parent=None):
        super().__init__(parent)
        self._recorder = recorder
        self._setup_window()
        self._setup_ui()
        self._timer = QTimer()
        self._timer.setInterval(50)  # 20fps
        self._timer.timeout.connect(self._update_level)
        self._rec_blink = True
        self._blink_timer = QTimer()
        self._blink_timer.setInterval(600)
        self._blink_timer.timeout.connect(self._toggle_blink)

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedHeight(56)
        self.setFixedWidth(340)

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(10)

        # Mic icon (custom drawn)
        self._mic_icon = MicIconWidget()
        layout.addWidget(self._mic_icon)

        # Red dot + REC label (custom painted in _setup as widget)
        self._rec_dot_widget = _RecDotLabel()
        layout.addWidget(self._rec_dot_widget)

        # Status label (for "変換中..." fallback)
        from PyQt6.QtWidgets import QLabel

        self._status_label = QLabel("")
        font = QFont("SF Pro Text", 13)
        font.setBold(True)
        self._status_label.setFont(font)
        self._status_label.setStyleSheet("color: white;")
        self._status_label.hide()
        layout.addWidget(self._status_label)

        # Audio level dots
        self._level_widget = AudioDotsWidget()
        layout.addWidget(self._level_widget)

        layout.addStretch()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -2)
        # Dark background
        painter.setBrush(QBrush(QColor(18, 18, 30, 235)))
        # Cyan border
        painter.setPen(QPen(QColor(0, 180, 210, 120), 1.5))
        painter.drawRoundedRect(rect, 26, 26)
        painter.end()

    def _position_bottom_center(self):
        screen = self.screen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.center().x() - self.width() // 2
            y = geo.bottom() - self.height() - 20
            self.move(x, y)

    def show_recording(self):
        self._rec_dot_widget.show()
        self._status_label.hide()
        self._position_bottom_center()
        self.show()
        self._timer.start()
        self._blink_timer.start()
        _play_sound("start")

    def hide_recording(self, transcribing=False):
        self._timer.stop()
        self._blink_timer.stop()
        if transcribing:
            self._rec_dot_widget.hide()
            self._status_label.setText("変換中...")
            self._status_label.show()
            self._level_widget.set_level(0.0)
        else:
            self.hide()
            _play_sound("stop")

    def hide_overlay(self):
        self._blink_timer.stop()
        self.hide()
        _play_sound("stop")

    def _update_level(self):
        self._level_widget.set_level(self._recorder.current_level)

    def _toggle_blink(self):
        self._rec_blink = not self._rec_blink
        self._rec_dot_widget.set_dot_visible(self._rec_blink)


class _RecDotLabel(QWidget):
    """Red dot + 'REC' text widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._dot_visible = True
        self.setFixedSize(65, 36)

    def set_dot_visible(self, visible: bool):
        self._dot_visible = visible
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        h = self.height()
        cy = h / 2

        # Red dot
        if self._dot_visible:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(255, 59, 48)))
            p.drawEllipse(QPointF(8, cy), 5, 5)

        # "REC" text
        font = QFont("SF Pro Text", 14)
        font.setBold(True)
        p.setFont(font)
        p.setPen(QPen(QColor(255, 255, 255)))
        p.drawText(QRectF(22, 0, 43, h), Qt.AlignmentFlag.AlignVCenter, "REC")
        p.end()


def _play_sound(kind: str):
    sounds = {
        "start": "/System/Library/Sounds/Tink.aiff",
        "stop": "/System/Library/Sounds/Pop.aiff",
    }
    path = sounds.get(kind)
    if path:
        subprocess.Popen(["afplay", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
