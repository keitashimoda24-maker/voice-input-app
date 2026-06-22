"""ペースト直後に表示する「ビジネス文に変換」フローティングボタン。"""

import threading

from PyQt6.QtCore import QObject, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QWidget


class _Signals(QObject):
    done = pyqtSignal(str)
    error = pyqtSignal(str)


class ToneWidget(QWidget):
    """ペースト後5秒間表示される「ビジネス文に変換」ピル。"""

    def __init__(self, original_text: str, on_replace):
        super().__init__()
        self._original = original_text
        self._on_replace = on_replace
        self._signals = _Signals()
        self._signals.done.connect(self._on_done)
        self._signals.error.connect(self._on_error)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        row = QHBoxLayout(self)
        row.setContentsMargins(16, 9, 16, 9)
        self._lbl = QLabel("🔁 ビジネス文に変換")
        f = QFont("Hiragino Sans")
        f.setPointSize(12)
        self._lbl.setFont(f)
        self._lbl.setStyleSheet("color: rgba(255, 200, 80, 0.92);")
        row.addWidget(self._lbl)
        self.adjustSize()
        self._position()
        self.show()

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(5000)
        self._timer.timeout.connect(self.hide)
        self._timer.start()

    def _position(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        self.adjustSize()
        self.move(geo.center().x() - self.width() // 2, geo.bottom() - self.height() - 80)

    def mousePressEvent(self, e):
        self._timer.stop()
        self._lbl.setText("⏳ 変換中...")
        threading.Thread(target=self._convert, daemon=True).start()

    def _convert(self):
        try:
            from ai_actions import tone_convert

            result = tone_convert(self._original)
            self._signals.done.emit(result)
        except Exception as ex:
            self._signals.error.emit(str(ex))

    def _on_done(self, text: str):
        self._on_replace(text)
        self.hide()

    def _on_error(self, _msg: str):
        self._lbl.setText("❌ 変換失敗")
        QTimer.singleShot(2000, self.hide)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor(8, 10, 26, 215)))
        p.setPen(QPen(QColor(255, 200, 80, 110), 1.0))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 20, 20)
        p.end()
