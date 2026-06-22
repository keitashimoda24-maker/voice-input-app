"""Recording indicator window. RT paste + Whisper finalization. Futuristic design."""

import subprocess
import threading

import pyperclip
from PyQt6.QtCore import QObject, QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QKeySequence,
    QPainter,
    QPen,
    QPixmap,
    QShortcut,
    QTextCursor,
)
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QTextEdit, QVBoxLayout, QWidget


class _RTSignals(QObject):
    text_updated = pyqtSignal(str, bool)
    start_dots = pyqtSignal()  # バックグラウンドスレッドからドットアニメを起動


# ── カラーパレット ─────────────────────────────────────────────────────────────
_CYAN = QColor(0, 229, 255)
_PURPLE = QColor(168, 85, 247)
_GREEN = QColor(0, 255, 136)
_ORANGE = QColor(255, 159, 10)
_DIM = QColor(255, 255, 255, 90)

CSS_CYAN = "#00e5ff"
CSS_PURPLE = "#a855f7"
CSS_GREEN = "#00ff88"

_CARD_STYLE = """
QWidget#card {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 rgba(8,10,26,252), stop:1 rgba(4,6,18,252));
    border-radius: 18px;
    border: 1px solid rgba(0,229,255,0.22);
}
"""


# ── アイコン描画 ──────────────────────────────────────────────────────────────
def _px(kind: str, size: int = 18, c: QColor = None) -> QPixmap:
    if c is None:
        c = _CYAN
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = float(size)
    lw = max(1.1, s * 0.08)

    if kind == "mic":
        pen = QPen(c, lw)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        bw, bh = s * 0.36, s * 0.44
        p.drawRoundedRect(QRectF((s - bw) / 2, s * 0.06, bw, bh), bw / 2, bw / 2)
        ar = s * 0.30
        p.drawArc(QRectF((s - ar * 2) / 2, s * 0.30, ar * 2, ar * 1.5), 0, -180 * 16)
        p.drawLine(QPointF(s / 2, s * 0.60), QPointF(s / 2, s * 0.82))
        p.drawLine(QPointF(s * 0.30, s * 0.82), QPointF(s * 0.70, s * 0.82))

    elif kind == "loading":
        r = s * 0.09
        p.setBrush(QBrush(c))
        p.setPen(Qt.PenStyle.NoPen)
        for ix in (0.25, 0.50, 0.75):
            p.drawEllipse(QRectF(s * ix - r, s * 0.5 - r, r * 2, r * 2))

    elif kind == "memo":
        # 近未来スタイラス: 太い対角バー + 鋭い先端
        pen_body = QPen(c, max(3.0, s * 0.22))
        pen_body.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(pen_body)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(s * 0.28, s * 0.72), QPointF(s * 0.78, s * 0.18))
        # 先端ダイヤモンド
        from PyQt6.QtGui import QPainterPath

        tip = QPainterPath()
        tip.moveTo(s * 0.14, s * 0.86)
        tip.lineTo(s * 0.28, s * 0.72)
        tip.lineTo(s * 0.36, s * 0.80)
        tip.closeSubpath()
        p.setBrush(QBrush(c))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(tip)
        # エネルギーライン（細い平行線）
        pen_e = QPen(c, max(1.0, s * 0.07))
        pen_e.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen_e)
        p.drawLine(QPointF(s * 0.60, s * 0.26), QPointF(s * 0.86, s * 0.12))
        p.drawLine(QPointF(s * 0.70, s * 0.36), QPointF(s * 0.90, s * 0.22))

    elif kind == "search":
        # 近未来サーチ: 六角形レンズ輪 + ハンドル
        import math

        pen = QPen(c, lw * 1.2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        r = s * 0.27
        cx, cy = s * 0.37, s * 0.35
        # 六角形レンズ
        from PyQt6.QtGui import QPainterPath

        hex_path = QPainterPath()
        for i in range(6):
            angle = math.radians(i * 60 - 30)
            px_ = cx + r * math.cos(angle)
            py_ = cy + r * math.sin(angle)
            if i == 0:
                hex_path.moveTo(px_, py_)
            else:
                hex_path.lineTo(px_, py_)
        hex_path.closeSubpath()
        p.drawPath(hex_path)
        # ハンドル
        pen2 = QPen(c, lw * 1.7)
        pen2.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen2)
        p.drawLine(QPointF(cx + r * 0.65, cy + r * 0.65), QPointF(s * 0.92, s * 0.92))

    elif kind == "cal":
        # 近未来カレンダー: グリッド点 + トップバー
        pen = QPen(c, lw * 1.1)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        # 外枠（角丸なし・シャープ）
        p.drawRect(QRectF(s * 0.08, s * 0.15, s * 0.78, s * 0.70))
        # 上部バー（塗りつぶし）
        p.setBrush(QBrush(c))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(QRectF(s * 0.08, s * 0.15, s * 0.78, s * 0.15))
        # グリッド点 2×3
        dot_r = max(1.5, s * 0.07)
        for xi, xf in enumerate((0.24, 0.46, 0.68)):
            for yi, yf in enumerate((0.43, 0.62)):
                alpha = 255 if (xi == 1 and yi == 0) else 140
                p.setBrush(QBrush(QColor(int(c.red()), int(c.green()), int(c.blue()), alpha)))
                p.drawEllipse(QRectF(s * xf - dot_r, s * yf - dot_r, dot_r * 2, dot_r * 2))

    elif kind == "cancel":
        pen = QPen(c, lw * 1.1)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        m = s * 0.22
        p.drawLine(QPointF(m, m), QPointF(s - m, s - m))
        p.drawLine(QPointF(s - m, m), QPointF(m, s - m))

    p.end()
    return px


def _get_frontmost_pid() -> int:
    """フォアグラウンドアプリのPIDを返す。"""
    try:
        from AppKit import NSWorkspace

        return NSWorkspace.sharedWorkspace().frontmostApplication().processIdentifier()
    except Exception:
        return 0


def _save_focused_window(pid: int):
    """録音開始時にフォーカス中のウィンドウ（AXUIElement）を保存する。
    貼り付け時にこのウィンドウを正確に復元するために使用。"""
    if not pid:
        return None
    try:
        from ApplicationServices import (
            AXUIElementCopyAttributeValue,
            AXUIElementCreateApplication,
        )

        ax_app = AXUIElementCreateApplication(pid)
        err, focused_window = AXUIElementCopyAttributeValue(ax_app, "AXFocusedWindow", None)
        if err == 0 and focused_window:
            return focused_window
    except Exception:
        pass
    return None


def _restore_focused_window(pid: int, ax_window=None):
    """保存したウィンドウを強制的にフォーカスする。
    AXUIElementでウィンドウを正確に復元 → アプリをアクティブ化。"""
    if not pid:
        return
    try:
        from AppKit import NSApplicationActivateIgnoringOtherApps, NSRunningApplication

        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
        if app:
            app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
    except Exception:
        pass
    if ax_window:
        try:
            from ApplicationServices import (
                AXUIElementPerformAction,
                AXUIElementSetAttributeValue,
            )

            # ウィンドウをRaise → メインウィンドウに設定
            AXUIElementPerformAction(ax_window, "AXRaise")
            AXUIElementSetAttributeValue(ax_window, "AXMain", True)
        except Exception:
            pass


def _post(e, pid: int):
    """イベントをPID指定で送出。pidが0の場合はAnnotatedSessionEventTapを使用。
    CGEventPostToPidは別ディスプレイのアプリに届かないことがあるため、
    常にCGEventPost（フォーカス中のアプリに送出）も併用する。"""
    import Quartz

    # フォーカス中のアプリに送出（最も確実）
    Quartz.CGEventPost(Quartz.kCGAnnotatedSessionEventTap, e)


# クリップボード操作をシリアライズするロック（RT入力とWhisper貼り付けの競合防止）
_CLIPBOARD_LOCK = threading.Lock()


def _quartz_type(text: str, pid: int = 0):
    """クリップボード経由でテキストを貼り付け（unicode 2重送信を回避）。"""
    try:
        import time

        import pyperclip

        acquired = _CLIPBOARD_LOCK.acquire(timeout=2.0)
        if not acquired:
            return  # デッドロック防止
        try:
            pyperclip.copy(text)
            time.sleep(0.06)
            _quartz_cmd_v(pid)
        finally:
            _CLIPBOARD_LOCK.release()
    except Exception:
        pass


def _quartz_backspace(count: int, pid: int = 0):
    """Quartzイベントでバックスペースをcount回押す。"""
    try:
        import time

        import Quartz

        src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
        BS = 51
        for _ in range(count):
            for down in (True, False):
                e = Quartz.CGEventCreateKeyboardEvent(src, BS, down)
                _post(e, pid)
            time.sleep(0.002)
    except Exception:
        pass


def _quartz_enter(pid: int = 0):
    """QuartzイベントでEnterキーを送出。"""
    try:
        import Quartz

        # kCGEventSourceStatePrivate: 独立した状態テーブルを使用
        # （HIDSystemState だと直前の Cmd+V のモディファイヤが残る可能性がある）
        src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStatePrivate)
        RETURN = 36
        for down in (True, False):
            e = Quartz.CGEventCreateKeyboardEvent(src, RETURN, down)
            Quartz.CGEventSetFlags(e, 0)  # モディファイヤなしを明示
            _post(e, pid)
    except Exception:
        pass


def _quartz_cmd_v(pid: int = 0):
    """QuartzイベントでCmd+Vを送出。"""
    try:
        import Quartz

        src = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
        V = 9
        CMD = Quartz.kCGEventFlagMaskCommand
        for down in (True, False):
            e = Quartz.CGEventCreateKeyboardEvent(src, V, down)
            Quartz.CGEventSetFlags(e, CMD)
            _post(e, pid)
    except Exception:
        pass


def _play(kind: str):
    import sounds

    sounds.play(kind)


def _restore_target_focus(pid: int):
    """録音ウィンドウ表示後、元のアプリにフォーカスを戻す。
    これをしないとCmd+VやBackspaceイベントが未フォーカスのテキストフィールドに届き
    macOSがアラート音（ポロン音）を連続再生してしまう。"""
    if not pid:
        return

    def _do():
        import time

        time.sleep(0.12)
        try:
            from AppKit import NSApplicationActivateIgnoringOtherApps, NSRunningApplication

            app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
            if app:
                app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
        except Exception:
            pass

    threading.Thread(target=_do, daemon=True).start()


# ── レベルバー ────────────────────────────────────────────────────────────────
class LevelBars(QWidget):
    """AquaVoice style dot visualization."""

    N = 10

    def __init__(self):
        super().__init__()
        self._dots = [0.0] * self.N
        self._level = 0.0
        self.setFixedSize(self.N * 10 + (self.N - 1) * 3, 28)
        self._timer = QTimer(self)
        self._timer.setInterval(35)
        self._timer.timeout.connect(self._tick)

    def showEvent(self, e):
        super().showEvent(e)
        self._timer.start()

    def hideEvent(self, e):
        self._timer.stop()
        super().hideEvent(e)

    def set_level(self, v: float):
        self._level = min(v, 1.0)

    def _tick(self):
        if not self.isVisible():
            return
        import math
        import random

        for i in range(self.N):
            cf = math.exp(-((i - self.N / 2) ** 2) / (self.N**2 / 6))
            amplified = min(self._level * 2.2, 1.0)
            target = min(amplified * cf * (0.55 + random.random() * 1.1), 1.0)
            self._dots[i] += (
                (target - self._dots[i]) * 0.70 if target > self._dots[i] else (target - self._dots[i]) * 0.08
            )
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        h = self.height()
        cy = h / 2.0
        p.setPen(Qt.PenStyle.NoPen)
        for i, v in enumerate(self._dots):
            x = i * 13 + 5
            r = 2.5 + v * 2.5
            alpha = int(100 + v * 155)
            p.setBrush(QBrush(QColor(0, 229, 255, alpha)))
            p.drawEllipse(QPointF(x, cy), r, r)
        p.end()


# ── 自動リサイズテキスト表示 ──────────────────────────────────────────────────
class _AutoResizeTextEdit(QTextEdit):
    """テキスト量に応じて高さが自動拡大する読み取り専用テキスト表示。"""

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setFont(QFont("Hiragino Sans", 12))
        self.setStyleSheet(
            "QTextEdit { color: rgba(255,255,255,0.65); font-size: 12px;"
            " background: rgba(0,229,255,0.04); border-radius: 8px;"
            " padding: 4px 6px; border: none; }"
        )
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(32)
        self.document().contentsChanged.connect(self._adjust_height)

    def _adjust_height(self):
        doc_h = int(self.document().size().height())
        new_h = max(32, min(doc_h + 12, 280))
        if self.height() != new_h:
            self.setFixedHeight(new_h)


class _EditTextBox(QTextEdit):
    """Returnキーで送信/貼り付け、Shift+Returnで改行する編集用テキストボックス。"""

    return_pressed = pyqtSignal()  # Return が押された（送信）
    shift_return_pressed = pyqtSignal()  # Shift+Return が押された（貼り付けのみ）

    def __init__(self):
        super().__init__()
        self._ime_composing = False
        self._ime_commit_time = 0.0  # IME確定時のタイムスタンプ

    def inputMethodEvent(self, e):
        """IMEの変換中かどうかを追跡する。"""
        import time
        has_preedit = bool(e.preeditString())
        has_commit = bool(e.commitString())
        if has_commit:
            self._ime_commit_time = time.monotonic()
        self._ime_composing = has_preedit
        super().inputMethodEvent(e)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            # IME変換中のReturnは確定操作なのでスキップ
            if self._ime_composing:
                super().keyPressEvent(e)
                return
            # IME確定直後（50ms以内）のReturnはIME確定操作の残りなので無視
            import time
            if time.monotonic() - self._ime_commit_time < 0.05:
                return
            if e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.shift_return_pressed.emit()
                return
            else:
                self.return_pressed.emit()
                return
        super().keyPressEvent(e)


# ── メインウィンドウ（録音インジケーターのみ）─────────────────────────────────
class VoiceWindow(QWidget):
    STATE_RECORDING = "recording"
    STATE_TRANSCRIBING = "transcribing"

    def __init__(self, recorder):
        self._in_edit_mode = False  # hide()オーバーライドより前に初期化
        self._hide_allowed = True
        super().__init__()
        self._recorder = recorder
        self._state = self.STATE_RECORDING
        self._stop_cb = None
        # 状態の初期化
        self._reset_state()
        # UI構築（一回のみ）
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build_ui()

        self._level_timer = QTimer(self)
        self._level_timer.setInterval(40)
        self._level_timer.timeout.connect(self._update_level)

        self._rt_debounce = QTimer(self)
        self._rt_debounce.setSingleShot(True)
        self._rt_debounce.setInterval(150)
        self._rt_debounce.timeout.connect(self._apply_pending_rt)

        self._dot_timer = QTimer(self)
        self._dot_timer.setInterval(750)
        self._dot_timer.timeout.connect(self._animate_dots)

        sc = QShortcut(QKeySequence("Meta+Alt+R"), self)
        sc.setContext(Qt.ShortcutContext.ApplicationShortcut)
        sc.activated.connect(self._on_stop_shortcut)
        sc2 = QShortcut(QKeySequence("Escape"), self)
        sc2.activated.connect(self._on_cancel)

    def _reset_state(self):
        """状態をリセットする（__init__とhide()から呼ばれる）。"""
        self._cancel_cb = None
        self._pasted_text = ""
        self._rt = None
        self._rt_signals = _RTSignals()
        self._rt_signals.text_updated.connect(self._on_rt_update)
        self._rt_signals.start_dots.connect(self._start_dot_timer)
        self._rt_pasted = ""
        self._rt_field_text = ""
        self._rt_pending_text = ""
        self._rt_type_lock = threading.Lock()
        self._target_pid = 0
        self._target_ax_window = None
        self._saved_cursor_pos = None
        self._wake_word_detector = None
        self._rt_mode = "normal"
        self._dot_phase = 0

        from cursor_indicator import CursorMicIndicator
        from cursor_indicator import _get_text_cursor_screen_pos as _get_text_cursor_screen_pos_fn

        # 古いインジケータをクリーンアップ（リソースリーク防止）
        old = getattr(self, '_cursor_indicator', None)
        if old is not None:
            old.hide_indicator()
            old.deleteLater()
        self._cursor_indicator = CursorMicIndicator()
        self._get_cursor_pos = _get_text_cursor_screen_pos_fn

    def hide(self):
        if not getattr(self, '_hide_allowed', True):
            return
        super().hide()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(10, 5, 10, 5)
        main.setSpacing(4)

        # 上段: AquaVoice風 [X] [●] [ドット...] [■]
        row = QHBoxLayout()
        row.setSpacing(8)

        # キャンセルボタン (X)
        self._cancel_btn = QPushButton()
        self._cancel_btn.setFixedSize(28, 28)
        self._cancel_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.12); border-radius: 14px;"
            " border: none; color: rgba(255,255,255,0.6); font-size: 14px; font-weight: bold; }"
            "QPushButton:hover { background: rgba(255,255,255,0.22); }"
        )
        self._cancel_btn.setText("X")
        self._cancel_btn.clicked.connect(self._on_cancel)
        row.addWidget(self._cancel_btn)

        # 青い録音インジケーター丸
        self._rec_lbl = QLabel()
        self._rec_lbl.setFixedSize(22, 22)
        self._rec_lbl.setStyleSheet(
            "background: #007aff; border-radius: 11px; border: none;"
        )
        row.addWidget(self._rec_lbl)

        # アイコンラベル（非表示・モード切替用に保持）
        self._icon_lbl = QLabel()
        self._icon_lbl.setPixmap(_px("mic", 18, _CYAN))
        self._icon_lbl.setFixedSize(18, 18)
        self._icon_lbl.hide()
        row.addWidget(self._icon_lbl)

        self._level_bars = LevelBars()
        row.addWidget(self._level_bars)

        # 停止ボタン (■)
        self._stop_btn = QPushButton()
        self._stop_btn.setFixedSize(28, 28)
        self._stop_btn.setStyleSheet(
            "QPushButton { background: rgba(255,59,48,0.18); border-radius: 6px;"
            " border: 1px solid rgba(255,59,48,0.4); color: #ff3b30; font-size: 12px; }"
            "QPushButton:hover { background: rgba(255,59,48,0.35); }"
        )
        self._stop_btn.setText("■")
        self._stop_btn.clicked.connect(self._on_stop_shortcut)
        row.addWidget(self._stop_btn)

        self._status_lbl = QLabel("")
        f = QFont("Hiragino Sans")
        f.setPointSize(11)
        self._status_lbl.setFont(f)
        self._status_lbl.setStyleSheet(f"color: {CSS_PURPLE};")
        self._status_lbl.hide()
        row.addWidget(self._status_lbl)

        main.addLayout(row)

        # 下段: リアルタイムテキスト表示（録音中は読み取り専用ラベル）
        self._rt_label = QLabel("")
        self._rt_label.setFont(QFont("Hiragino Sans", 12))
        self._rt_label.setStyleSheet("color: rgba(255,255,255,0.80); padding: 3px 6px;")
        self._rt_label.setWordWrap(True)
        self._rt_label.setMinimumWidth(300)
        self._rt_label.setMaximumWidth(560)
        self._rt_label.hide()
        main.addWidget(self._rt_label)

        # 修正ヒント（Whisper結果表示時のみ）
        self._edit_hint = QLabel("テキストボックス内の修正は学習されます")
        self._edit_hint.setFont(QFont("Hiragino Sans", 10))
        self._edit_hint.setStyleSheet("color: rgba(0,229,255,0.65); padding: 1px 6px;")
        self._edit_hint.hide()
        main.addWidget(self._edit_hint)

        # 編集可能テキストボックス（Whisper結果の修正用）
        self._result_edit = _EditTextBox()
        # Returnキーの動作を設定から読み込み
        from config import load_config as _load_cfg

        self._return_action = "send"  # Cmd+Return=送信, Shift+Return=貼り付けのみ
        self._result_edit.return_pressed.connect(self._on_send_result)
        self._result_edit.shift_return_pressed.connect(self._on_paste_result)
        self._result_edit.setFont(QFont("Hiragino Sans", 12))
        self._result_edit.setStyleSheet(
            "QTextEdit { color: white; background: rgba(255,255,255,0.08);"
            " border: 1px solid rgba(0,229,255,0.3); border-radius: 8px;"
            " padding: 4px 6px; }"
        )
        self._result_edit.setMinimumWidth(340)
        self._result_edit.setMaximumWidth(560)
        self._result_edit.setMaximumHeight(160)
        self._result_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._result_edit.hide()
        main.addWidget(self._result_edit)

        # 貼り付けボタン行
        self._btn_row = QWidget()
        btn_layout = QHBoxLayout(self._btn_row)
        btn_layout.setContentsMargins(0, 2, 0, 0)
        btn_layout.setSpacing(6)

        send_label = "送信 (Return)"
        paste_label = "貼り付けのみ (⇧Return)"

        self._send_btn = QPushButton(send_label)
        self._send_btn.setStyleSheet(
            "QPushButton { background: rgba(0,122,255,0.85); color: white;"
            " border-radius: 6px; padding: 5px 14px; font-size: 12px; }"
            "QPushButton:hover { background: rgba(0,100,220,0.95); }"
        )
        self._send_btn.clicked.connect(self._on_send_result)

        self._paste_btn = QPushButton(paste_label)
        self._paste_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.15); color: rgba(255,255,255,0.8);"
            " border-radius: 6px; padding: 5px 14px; font-size: 12px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.25); }"
        )
        self._paste_btn.clicked.connect(self._on_paste_result)

        self._cancel_result_btn = QPushButton("キャンセル")
        self._cancel_result_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.10); color: rgba(255,255,255,0.7);"
            " border-radius: 6px; padding: 5px 14px; font-size: 12px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.18); }"
        )
        self._cancel_result_btn.clicked.connect(self._on_cancel_result)

        # 整形ボタン（サイクル: off → clean → bullets → paragraph → auto → off）
        self._format_btn = QPushButton("整形")
        self._format_btn.setStyleSheet(
            "QPushButton { background: rgba(168,85,247,0.20); color: rgba(168,85,247,0.9);"
            " border-radius: 6px; padding: 5px 10px; font-size: 11px;"
            " border: 1px solid rgba(168,85,247,0.3); }"
            "QPushButton:hover { background: rgba(168,85,247,0.35); }"
        )
        self._format_btn.clicked.connect(self._on_format_cycle)
        self._format_modes = ["off", "clean", "bullets", "paragraph", "auto"]
        self._format_labels = {"off": "整形", "clean": "整形:読みやすく", "bullets": "整形:箇条書き", "paragraph": "整形:段落", "auto": "整形:自動"}
        self._update_format_btn_label()

        btn_layout.addWidget(self._cancel_result_btn)
        btn_layout.addWidget(self._format_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self._paste_btn)
        btn_layout.addWidget(self._send_btn)
        self._btn_row.hide()
        main.addWidget(self._btn_row)

        self._whisper_original = ""  # Whisperの元テキスト（学習比較用）
        self._in_edit_mode = False

        # REC ラベルの点滅タイマー
        self._rec_blink = QTimer(self)
        self._rec_blink.setInterval(600)
        self._rec_blink_state = True
        self._rec_blink.timeout.connect(self._blink_rec)
        self._rec_blink.start()

        self.adjustSize()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor(8, 10, 26, 210)))
        p.setPen(QPen(QColor(0, 229, 255, 55), 1.0))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 20, 20)
        p.end()

    def mousePressEvent(self, e):
        # 編集モード中はクリックでウィンドウを閉じない
        if self._in_edit_mode:
            super().mousePressEvent(e)
            return
        if self._state == self.STATE_RECORDING and self._stop_cb:
            self._stop_cb()

    # ── 状態遷移 ──────────────────────────────────────────────────────────────
    def set_stop_callback(self, cb):
        self._stop_cb = cb

    def set_cancel_callback(self, cb):
        self._cancel_cb = cb

    def _on_stop_shortcut(self):
        if self._state == self.STATE_RECORDING and self._stop_cb:
            self._stop_cb()

    def set_wake_word_detector(self, fn):
        """fn(text) -> 'memo' | 'research' | None を設定。RTテキストからモードを検出する。"""
        self._wake_word_detector = fn

    def _apply_rt_mode(self, mode: str):
        """RTウェイクワード検出時にバナー表示を切り替える。"""
        try:
            if mode == self._rt_mode:
                return
            self._rt_mode = mode
            if mode == "memo":
                self._icon_lbl.setPixmap(_px("memo", 18, _ORANGE))
                self._status_lbl.setText("MEMO REC")
                self._status_lbl.setStyleSheet(f"color: {CSS_GREEN}; letter-spacing: 1px;")
                self._status_lbl.show()
            elif mode == "research":
                self._icon_lbl.setPixmap(_px("search", 18, QColor(200, 150, 255)))
                self._status_lbl.setText("RESEARCH")
                self._status_lbl.setStyleSheet("color: rgba(200,160,255,0.95); letter-spacing: 1px;")
                self._status_lbl.show()
            elif mode == "calendar":
                self._icon_lbl.setPixmap(_px("cal", 18, QColor(0, 220, 110)))
                self._status_lbl.setText("CALENDAR")
                self._status_lbl.setStyleSheet("color: rgba(0,230,120,0.95); letter-spacing: 1px;")
                self._status_lbl.show()
            self.adjustSize()
            self._position_bottom()
        except Exception:
            pass

    def _blink_rec(self):
        self._rec_blink_state = not self._rec_blink_state
        if self._rec_blink_state:
            self._rec_lbl.setStyleSheet(
                "background: #007aff; border-radius: 11px; border: none;"
            )
        else:
            self._rec_lbl.setStyleSheet(
                "background: rgba(0,122,255,0.3); border-radius: 11px; border: none;"
            )

    def _position_near_cursor(self):
        """Position the window near the saved cursor position."""
        try:
            pos = self._saved_cursor_pos
            if not pos:
                self._position_bottom()
                return
            # カーソル位置を含むスクリーンを検索（マルチモニター対応）
            from PyQt6.QtCore import QPoint
            screen = QApplication.screenAt(QPoint(int(pos[0]), int(pos[1])))
            if not screen:
                screen = QApplication.primaryScreen()
            if not screen:
                self._position_bottom()
                return
            geo = screen.availableGeometry()
            self.adjustSize()
            w = self.width()
            h = self.height()
            # Position slightly below and to the right of cursor
            x = pos[0] + 8
            y = pos[1] + 20
            # Ensure window stays within screen bounds
            if x + w > geo.right() - 8:
                x = pos[0] - w - 8
            if x < geo.left() + 8:
                x = geo.left() + 8
            if y + h > geo.bottom() - 8:
                y = pos[1] - h - 8
            if y < geo.top() + 8:
                y = geo.top() + 8
            self.move(x, y)
        except Exception:
            self._position_bottom()

    def start_recording(self, memo_mode: bool = False, target_pid: int = 0):
        # 編集UI表示中の場合、target_pidは変更しない（元のアプリに貼り付けるため）
        if not self._in_edit_mode:
            self._target_pid = target_pid if target_pid else _get_frontmost_pid()
            # 録音開始時のウィンドウを保存（貼り付け先を正確に復元するため）
            self._target_ax_window = _save_focused_window(self._target_pid)
        # カーソル位置はウィンドウ表示前（ターゲットアプリがフォーカス中）に取得する
        cursor_pos = self._get_cursor_pos()
        # Save cursor position for later use by show_result
        self._saved_cursor_pos = cursor_pos
        # 録音中はターゲットアプリからフォーカスを奪わない
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self._state = self.STATE_RECORDING
        self._rt_pasted = ""
        self._rt_field_text = ""
        self._rt_pending_text = ""
        self._dot_phase = 0
        self._rt_label.setText("")
        self._rt_label.hide()
        self._rt_mode = "memo" if memo_mode else "normal"
        if memo_mode:
            self._icon_lbl.setPixmap(_px("memo", 18, _ORANGE))
            self._status_lbl.setText("MEMO REC")
            self._status_lbl.setStyleSheet(f"color: {CSS_GREEN}; letter-spacing: 1px;")
            self._status_lbl.show()
        else:
            self._icon_lbl.setPixmap(_px("mic", 18, _CYAN))
            self._status_lbl.hide()
        # 編集UI表示中: テキストボックスは表示したまま録音UIを追加
        if self._in_edit_mode:
            self._btn_row.hide()  # ボタンだけ隠す（録音中は操作不要）
        self._rec_lbl.show()
        self._cancel_btn.show()
        self._stop_btn.show()
        self._rec_blink_state = True
        self._rec_lbl.setStyleSheet(
            "background: #007aff; border-radius: 11px; border: none;"
        )
        self._rec_blink.start()
        self._level_bars.show()
        self._position_bottom()
        self.show()
        self._level_timer.start()
        _play("start")
        self._cursor_indicator.show_at_cursor(cursor_pos)
        if not self._in_edit_mode:
            _restore_target_focus(self._target_pid)
        self._start_realtime()

    def _start_dot_timer(self):
        pass  # プレースホルダー入力廃止のため無効化

    def _animate_dots(self):
        pass  # プレースホルダー入力廃止のため無効化

    def _start_realtime(self):
        def _run():
            try:
                from realtime_transcriber import RealtimeTranscriber

                self._rt = RealtimeTranscriber(on_update=lambda t, f: self._rt_signals.text_updated.emit(t, f))
                self._rt.start()
            except Exception:
                pass

        threading.Thread(target=_run, daemon=True).start()

    def _on_rt_update(self, text: str, is_final: bool):
        """RTテキストを受け取り、デバウンス後に入力欄へ反映。"""
        try:
            if self._state != self.STATE_RECORDING:
                return
            # ウェイクワードをリアルタイムで検出してバナーを切り替える
            if self._wake_word_detector and self._rt_mode == "normal" and text.strip():
                mode = self._wake_word_detector(text.strip())
                if mode:
                    self._apply_rt_mode(mode)
            self._rt_pending_text = text
            self._rt_debounce.start()  # 150ms リセット
        except Exception:
            pass

    def _apply_pending_rt(self):
        """RTテキストを録音バー内に表示する。
        クリップボードやQuartzイベントは一切使わない（フリーズ防止）。"""
        if self._state != self.STATE_RECORDING:
            return
        new_text = self._rt_pending_text.strip()
        if new_text:
            self._rt_label.setText(new_text)
            if not self._rt_label.isVisible():
                self._rt_label.show()
            # テキスト量が変わるたびにサイズと位置を再計算
            self.adjustSize()
            self._position_bottom()
        else:
            if self._rt_label.isVisible():
                self._rt_label.hide()
                self.adjustSize()
                self._position_bottom()

    def show_transcribing(self):
        self._state = self.STATE_TRANSCRIBING
        self._cursor_indicator.hide_indicator()
        self._rt_debounce.stop()
        self._dot_timer.stop()
        self._rec_blink.stop()
        self._rec_lbl.hide()
        self._cancel_btn.hide()
        self._stop_btn.hide()
        rt = self._rt
        self._rt = None
        if rt:
            threading.Thread(target=rt.stop, daemon=True).start()
        self._level_bars.set_level(0.0)
        self._level_timer.stop()
        self._level_bars.hide()
        self._icon_lbl.show()
        self._icon_lbl.setPixmap(_px("loading", 18, _PURPLE))
        self._status_lbl.setText("追加の文字起こし中..." if self._in_edit_mode else "文字起こしを修正中...")
        self._status_lbl.setStyleSheet(f"color: {CSS_PURPLE};")
        self._status_lbl.show()
        # 編集モード中: テキストボックスは表示したまま
        if self._in_edit_mode:
            self._edit_hint.show()
            self._result_edit.show()
        self.adjustSize()
        self._position_bottom()
        self.show()
        self._dot_phase = 0
        self._rt_field_text = ""
        self._rt_label.setText("")
        self._rt_label.hide()

    def show_result(self, text: str):
        """Whisper結果を編集UIに表示。ユーザーが修正→貼り付け。"""
        self._cursor_indicator.hide_indicator()
        self._rt_label.setText("")
        self._rt_label.hide()

        if not text.strip():
            # 空テキスト: RTプレースホルダーを消して閉じる
            rt_len = len(self._rt_field_text)
            pid = self._target_pid
            ax_window = self._target_ax_window
            self._rt_field_text = ""
            self.hide()
            if rt_len > 0:

                def _backspace_with_activate(n, p, axw):
                    import time

                    time.sleep(0.1)
                    _restore_focused_window(p, axw)
                    time.sleep(0.1)
                    _quartz_backspace(n, p)

                threading.Thread(target=_backspace_with_activate, args=(rt_len, pid, ax_window), daemon=True).start()
            return

        # 録音UI要素をすべて隠す
        self._rec_lbl.hide()
        self._cancel_btn.hide()
        self._stop_btn.hide()
        self._rec_blink.stop()
        self._level_bars.hide()
        self._level_timer.stop()
        self._status_lbl.hide()

        # 編集UIを表示
        self._icon_lbl.setPixmap(_px("mic", 18, _CYAN))
        if self._in_edit_mode:
            # 追加録音: カーソル位置にテキストを挿入
            cursor = self._result_edit.textCursor()
            cursor.insertText(text.strip())
            self._result_edit.setTextCursor(cursor)
        else:
            # 初回: テキストを設定
            self._whisper_original = text.strip()
            self._result_edit.setPlainText(text.strip())
        self._edit_hint.show()
        self._result_edit.show()
        self._btn_row.show()
        self._in_edit_mode = True

        # 録音中の WA_ShowWithoutActivating を解除してフォーカス可能にする
        # hide → 属性変更 → show の順でないと反映されない
        self._in_edit_mode = False  # hide中の副作用を防ぐ
        self.hide()
        self._in_edit_mode = True
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        # hide()でWindowFlagsがリセットされる場合があるので再適用
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # Accessoryポリシーのみ設定（activateIgnoringOtherAppsはSpace切替を誘発するので使わない）
        try:
            from AppKit import NSApp, NSApplicationActivationPolicyAccessory
            NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
        except Exception:
            pass
        self.adjustSize()
        # カーソル位置が保存されていればその近くに表示、なければ画面下部
        if getattr(self, "_saved_cursor_pos", None):
            self._position_near_cursor()
        else:
            self._position_bottom()
        self.show()
        self.raise_()
        # NSWindowでSpace切り替えなしに最前面+キーボード入力可能にする
        self._make_key_without_activating_app()
        QTimer.singleShot(150, self._force_activate_edit)

    def paste_direct(self, text: str):
        """RTテキストを削除してWhisper最終結果を入力欄に貼り付け（学習なし直接貼り付け）。"""
        self._cursor_indicator.hide_indicator()
        self._rt_label.setText("")
        self._rt_label.hide()
        if not text.strip():
            rt_len = len(self._rt_field_text)
            pid = self._target_pid
            ax_window = self._target_ax_window
            self._rt_field_text = ""
            self.hide()
            if rt_len > 0:

                def _backspace_with_activate(n, p, axw):
                    import time

                    time.sleep(0.1)
                    _restore_focused_window(p, axw)
                    time.sleep(0.1)
                    _quartz_backspace(n, p)

                threading.Thread(target=_backspace_with_activate, args=(rt_len, pid, ax_window), daemon=True).start()
            return
        self._pasted_text = text
        rt_len = len(self._rt_field_text)
        self._rt_field_text = ""
        self.hide()
        threading.Thread(target=self._replace_rt_and_paste, args=(rt_len, text), daemon=True).start()

    def _learn_if_modified(self, final_text: str):
        """修正があれば学習する（貼り付け/送信の成否に関係なく）。"""
        if final_text and final_text != self._whisper_original and self._whisper_original:

            def _learn_bg(original, corrected):
                try:
                    from learning import force_regenerate, learn_correction

                    learn_correction(original, corrected)
                    force_regenerate()
                except Exception:
                    pass

            threading.Thread(target=_learn_bg, args=(self._whisper_original, final_text), daemon=True).start()

    def _do_paste_or_send(self, send_enter: bool):
        """貼り付け/送信の共通処理。send_enter=True で貼り付け後にEnterも送信。"""
        if not self._in_edit_mode:
            return
        final_text = ""
        try:
            final_text = self._result_edit.toPlainText().strip()
        except Exception:
            pass
        self._learn_if_modified(final_text)
        try:
            if not final_text:
                self._on_cancel_result()
                return
            self._close_edit_ui()
            self._pasted_text = final_text
            rt_len = len(self._rt_field_text)
            self._rt_field_text = ""
            self.hide()
            threading.Thread(
                target=self._replace_rt_and_paste, args=(rt_len, final_text, send_enter), daemon=True
            ).start()
        except Exception:
            self._in_edit_mode = False
            self._close_edit_ui()
            self.hide()

    def _on_send_result(self):
        """送信ボタン: 貼り付け + Enter送信。"""
        self._do_paste_or_send(send_enter=True)

    def _on_paste_result(self):
        """貼り付けのみボタン。"""
        self._do_paste_or_send(send_enter=False)

    def _on_cancel_result(self):
        """編集UIのキャンセル。RTプレースホルダーを消して閉じる。"""
        self._close_edit_ui()
        rt_len = len(self._rt_field_text)
        pid = self._target_pid
        self._rt_field_text = ""
        self.hide()
        if rt_len > 0:

            def _remove():
                import time

                time.sleep(0.15)
                _quartz_backspace(rt_len, pid)

            threading.Thread(target=_remove, daemon=True).start()

    def _update_format_btn_label(self):
        """整形ボタンのラベルを現在のモードに合わせて更新。"""
        from config import load_config
        mode = load_config().get("auto_format_mode", "off")
        label = self._format_labels.get(mode, "整形")
        self._format_btn.setText(label)
        if mode == "off":
            self._format_btn.setStyleSheet(
                "QPushButton { background: rgba(168,85,247,0.20); color: rgba(168,85,247,0.9);"
                " border-radius: 6px; padding: 5px 10px; font-size: 11px;"
                " border: 1px solid rgba(168,85,247,0.3); }"
                "QPushButton:hover { background: rgba(168,85,247,0.35); }"
            )
        else:
            self._format_btn.setStyleSheet(
                "QPushButton { background: rgba(168,85,247,0.45); color: white;"
                " border-radius: 6px; padding: 5px 10px; font-size: 11px;"
                " border: 1px solid rgba(168,85,247,0.6); }"
                "QPushButton:hover { background: rgba(168,85,247,0.55); }"
            )

    def _on_format_cycle(self):
        """整形モードをサイクルし、現在のテキストに適用。"""
        from config import load_config, save_config
        config = load_config()
        current = config.get("auto_format_mode", "off")
        idx = self._format_modes.index(current) if current in self._format_modes else 0
        next_mode = self._format_modes[(idx + 1) % len(self._format_modes)]
        config["auto_format_mode"] = next_mode
        save_config(config)
        self._update_format_btn_label()

        # offに戻った場合は元テキストに復元
        if next_mode == "off":
            if hasattr(self, "_whisper_original") and self._whisper_original:
                self._result_edit.setPlainText(self._whisper_original)
            return

        # 現在のテキストに整形を適用
        text = self._whisper_original if hasattr(self, "_whisper_original") and self._whisper_original else self._result_edit.toPlainText().strip()
        if not text:
            return

        self._format_btn.setText("整形中...")
        self._format_btn.setEnabled(False)

        def _apply():
            try:
                from ai_actions import auto_format
                result = auto_format(text, next_mode)
                QTimer.singleShot(0, lambda: self._on_format_done(result))
            except Exception:
                QTimer.singleShot(0, lambda: self._on_format_done(text))

        import threading
        threading.Thread(target=_apply, daemon=True).start()

    def _on_format_done(self, text: str):
        """整形完了後にテキストを更新。"""
        self._format_btn.setEnabled(True)
        self._update_format_btn_label()
        if text.strip():
            self._result_edit.setPlainText(text.strip())
            self._result_edit.moveCursor(QTextCursor.MoveOperation.End)
        self.adjustSize()
        if getattr(self, "_saved_cursor_pos", None):
            self._position_near_cursor()
        else:
            self._position_bottom()

    def _make_key_without_activating_app(self):
        """NSWindowを直接操作して、アプリのアクティブ化（Space切替）なしに
        ウィンドウを最前面+キーボード入力可能にする。"""
        try:
            from AppKit import NSApplication
            for win in NSApplication.sharedApplication().windows():
                if win.isVisible():
                    # 全Spaceに表示 + アクティブSpaceに移動
                    win.setCollectionBehavior_((1 << 0) | (1 << 1))
                    # ステータスバー級の高レベル（全アプリの上）
                    win.setLevel_(25)
                    # Space切替なしで最前面に表示
                    win.orderFrontRegardless()
                    # キーボード入力を受け付ける（アプリactivateなし）
                    win.makeKeyWindow()
        except Exception as ex:
            print(f"[voice_window] _make_key_without_activating_app error: {ex}")

    def _force_activate_edit(self):
        """編集モードのウィンドウをアクティブ化してフォーカスを取る。
        Space切替を起こさないようNSWindow単体で操作する。"""
        if not self._in_edit_mode:
            return
        # NSWindow経由で最前面+キー入力（アプリactivateしない）
        self._make_key_without_activating_app()
        self.activateWindow()
        self.raise_()
        self._result_edit.setFocus(Qt.FocusReason.OtherFocusReason)
        # カーソル位置が既に設定済みの場合は末尾移動しない（追加録音時の挿入位置を保持）
        if not self._result_edit.textCursor().hasSelection() and self._result_edit.textCursor().position() == 0:
            self._result_edit.moveCursor(QTextCursor.MoveOperation.End)
        # 遅延で再度フォーカスを確認
        QTimer.singleShot(300, self._ensure_edit_focus)

    def _restore_to_prohibited(self):
        """Accessory → Prohibited に戻してメニューバー重複を防ぐ。"""
        try:
            from AppKit import NSApp, NSApplicationActivationPolicyProhibited

            NSApp.setActivationPolicy_(NSApplicationActivationPolicyProhibited)
        except Exception:
            pass

    def _ensure_edit_focus(self):
        """フォーカスが _result_edit に入っていなければ再設定する。"""
        if not self._in_edit_mode:
            return
        if not self._result_edit.hasFocus():
            # Space切替を起こさないようNSWindow単体で操作
            self._make_key_without_activating_app()
            self.activateWindow()
            self._result_edit.setFocus(Qt.FocusReason.OtherFocusReason)

    def _restore_accessory_policy(self):
        """編集モード終了後にProhibitedに戻す。"""
        try:
            from AppKit import NSApp, NSApplicationActivationPolicyProhibited

            NSApp.setActivationPolicy_(NSApplicationActivationPolicyProhibited)
        except Exception:
            pass

    def _close_edit_ui(self):
        """編集UIを閉じる。_in_edit_mode は最初にFalseにする（フリーズ防止最優先）。"""
        self._in_edit_mode = False  # 最優先で解除
        try:
            self._edit_hint.hide()
            self._result_edit.hide()
            self._btn_row.hide()
        except Exception:
            pass
        self._restore_accessory_policy()

    def _replace_rt_and_paste(self, rt_len: int, text: str, send_enter: bool = False):
        # 最終防衛ガード：空文字列は絶対にペーストしない
        if not text or not text.strip():
            return
        import time

        import sounds

        pid = self._target_pid
        ax_window = self._target_ax_window
        # 編集ウィンドウが閉じるのを待つ
        time.sleep(0.15)
        # クリップボードにテキストを先にセット（アクティブ化前に準備）
        acquired = _CLIPBOARD_LOCK.acquire(timeout=3.0)
        if not acquired:
            return
        try:
            pyperclip.copy(text)
        finally:
            _CLIPBOARD_LOCK.release()
        # 録音開始時のウィンドウを正確に復元（アプリ + ウィンドウ単位）
        # 別ディスプレイへのフォーカス切り替えは時間がかかるためリトライ付き
        _restore_focused_window(pid, ax_window)
        time.sleep(0.2)
        # 2回目のアクティブ化（別モニターの場合、1回では切り替わらないことがある）
        _restore_focused_window(pid, ax_window)
        time.sleep(0.15)
        # フォーカスが正しく復元されたか確認し、ずれていたら再試行
        current_pid = _get_frontmost_pid()
        if current_pid != pid:
            print(f"[voice_window] フォーカスずれ検出: 期待={pid}, 実際={current_pid}. 再復元...")
            _restore_focused_window(pid, ax_window)
            time.sleep(0.3)
            # 3回目でもずれている場合はAppleScript経由で強制アクティブ化
            current_pid = _get_frontmost_pid()
            if current_pid != pid:
                try:
                    from AppKit import NSRunningApplication
                    app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
                    if app:
                        bundle_id = app.bundleIdentifier()
                        if bundle_id:
                            subprocess.run(
                                ["osascript", "-e", f'tell application id "{bundle_id}" to activate'],
                                timeout=3, capture_output=True,
                            )
                            time.sleep(0.3)
                            print(f"[voice_window] AppleScript強制アクティブ化: {bundle_id}")
                except Exception as ex:
                    print(f"[voice_window] 強制アクティブ化失敗: {ex}")
        acquired = _CLIPBOARD_LOCK.acquire(timeout=3.0)
        if not acquired:
            return
        try:
            if rt_len > 0:
                _quartz_backspace(rt_len, pid)
                time.sleep(0.05)
            _quartz_cmd_v(pid)
            # 送信モード: ペースト後にEnterキーを送信
            # ターミナルアプリ等はペースト処理に時間がかかるため十分な待機が必要
            if send_enter:
                time.sleep(0.25)
                _quartz_enter(pid)
        finally:
            _CLIPBOARD_LOCK.release()
        time.sleep(0.05)
        sounds.play("paste")
        # セキュリティ: 5秒後にクリップボードを消去（監視アプリへの漏洩防止）
        time.sleep(5.0)
        try:
            subprocess.run(["pbcopy"], input=b"", timeout=2)
        except Exception:
            pass

    def _on_cancel(self):
        # 編集UIが表示中ならそちらのキャンセル処理
        if self._result_edit.isVisible():
            self._on_cancel_result()
            return
        # 先に状態を変えてデバウンスコールバック・RT更新を無効化
        self._state = self.STATE_TRANSCRIBING
        self._rt_debounce.stop()
        self._dot_timer.stop()
        self._rec_blink.stop()
        self._rec_lbl.hide()
        self._cancel_btn.hide()
        self._stop_btn.hide()
        self._level_timer.stop()
        self._rt_label.setText("")
        self._rt_label.hide()
        self._edit_hint.hide()
        self._result_edit.hide()
        self._btn_row.hide()
        placeholder_len = len(self._rt_field_text)
        pid = self._target_pid
        self._rt_field_text = ""
        # RT認識を停止（投げっぱなしではなく rt を None にしてから停止）
        rt = self._rt
        self._rt = None
        if rt:
            threading.Thread(target=rt.stop, daemon=True).start()
        self._cursor_indicator.hide_indicator()
        self.hide()
        if self._cancel_cb:
            self._cancel_cb()
        _play("stop")
        # プレースホルダーをフィールドから削除
        if placeholder_len > 0:

            def _remove():
                import time

                time.sleep(0.15)
                _quartz_backspace(placeholder_len, pid)

            threading.Thread(target=_remove, daemon=True).start()

    def _update_level(self):
        self._level_bars.set_level(self._recorder.current_level)

    def _position_bottom(self):
        # ターゲットアプリがあるスクリーンの下部に配置（マルチモニター対応）
        screen = None
        try:
            # マウスカーソルがあるスクリーンを使用
            from PyQt6.QtGui import QCursor
            screen = QApplication.screenAt(QCursor.pos())
        except Exception:
            pass
        if not screen:
            screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        self.adjustSize()
        w = self.width()
        h = self.height()
        x = geo.center().x() - w // 2
        x = max(geo.left() + 8, min(x, geo.right() - w - 8))
        y = geo.bottom() - h - 28
        self.move(x, y)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            # 編集モード中のESCは無視（IME変換キャンセルと競合するため）
            if not self._in_edit_mode:
                self._on_cancel()
        elif e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self._result_edit.isVisible():
                if self._result_edit._ime_composing:
                    return
                if self._result_edit._ignore_next_return:
                    self._result_edit._ignore_next_return = False
                    return
                has_shift = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                if has_shift:
                    self._on_paste_result()
                else:
                    self._on_send_result()
            else:
                super().keyPressEvent(e)
        else:
            super().keyPressEvent(e)

