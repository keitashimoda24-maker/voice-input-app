"""System tray/menubar application."""

import os
import threading


# ── ウェイクワード（configから読み込み） ──────────────────────────────────────
def _load_wake_words(key: str, fallback: set) -> set:
    from config import load_config

    cfg = load_config()
    raw = cfg.get(key, "")
    if raw:
        return {w.strip() for w in raw.split(",") if w.strip()}
    return fallback


def _memo_wake_words() -> set:
    return _load_wake_words("memo_wake_words", {"メモ", "めも", "memo", "ボイスメモ", "音声メモ", "おんせいメモ"})


def _research_wake_words() -> set:
    return _load_wake_words(
        "research_wake_words",
        {
            "リサーチ",
            "りさーち",
            "research",
            "調べて",
            "しらべて",
            "調べてください",
            "調べておいて",
            "リサーチして",
            "リサーチしてください",
        },
    )


def _calendar_wake_words() -> set:
    return _load_wake_words(
        "calendar_wake_words", {"カレンダー", "かれんだー", "calendar", "予定追加", "スケジュール追加"}
    )


def _strip_wake_word(text: str, wake_words: set) -> str | None:
    """テキストがウェイクワードで始まる場合、ウェイクワードを除いたテキストを返す。
    ウェイクワードでない場合は None を返す。
    セパレータ（スペース・句読点）で区切られている場合のみ検出する。"""
    t = text.strip()
    if not t:
        return None
    # 長いウェイクワードを先に試す（部分マッチ優先防止）
    for word in sorted(wake_words, key=len, reverse=True):
        tl = t.lower()
        wl = word.lower()
        if tl == wl:
            return ""
        # セパレータあり（明確な区切りがある場合）
        for sep in (" ", "　", "、", "。", "，", "\n", "・", "：", ":"):
            if tl.startswith(wl + sep):
                return t[len(word) + len(sep) :].strip()
        # セパレータなし（日本語音声認識はスペースを入れないことが多い）
        if tl.startswith(wl) and len(tl) > len(wl):
            return t[len(word) :].strip()
    return None


def _strip_memo_wake_word(text: str) -> str | None:
    return _strip_wake_word(text, _memo_wake_words())


def _strip_research_wake_word(text: str) -> str | None:
    return _strip_wake_word(text, _research_wake_words())


def _strip_calendar_wake_word(text: str) -> str | None:
    return _strip_wake_word(text, _calendar_wake_words())


from PyQt6.QtCore import QObject, QPointF, QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPen, QPixmap, QTextCursor
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

import research_manager
from config import load_config
from recorder import AudioRecorder
from settings_dialog import SettingsDialog
from transcriber import transcribe
from voice_window import _CYAN, VoiceWindow, _px


def _make_icon(state: str = "idle", size: int = 64) -> QIcon:
    """近未来デザインのトレイアイコン。state: 'idle' | 'recording' | 'memo' | 'research'"""
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = float(size)

    if state == "recording":
        # 録音中: 明るいシアン塗りつぶし円
        p.setBrush(QBrush(QColor(0, 229, 255, 255)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(2, 2, s - 4, s - 4))
        # 中央に白い停止四角
        sq = s * 0.36
        p.setBrush(QBrush(QColor(10, 12, 28)))
        p.drawRoundedRect(QRectF((s - sq) / 2, (s - sq) / 2, sq, sq), s * 0.05, s * 0.05)

    elif state == "memo":
        # グロー外輪
        p.setBrush(QBrush(QColor(255, 160, 30, 55)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(0, 0, s, s))
        # メイン円（オレンジ）
        p.setBrush(QBrush(QColor(255, 145, 15, 255)))
        p.drawEllipse(QRectF(4, 4, s - 8, s - 8))
        lw = max(2.0, s * 0.085)
        # 白いスタイラス本体（太い対角バー）
        from PyQt6.QtGui import QPainterPath as _PP

        pen_s = QPen(QColor(255, 255, 255), lw * 2.2)
        pen_s.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(pen_s)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(s * 0.30, s * 0.72), QPointF(s * 0.74, s * 0.22))
        # 先端ダイヤモンド（白）
        tip = _PP()
        tip.moveTo(s * 0.18, s * 0.84)
        tip.lineTo(s * 0.30, s * 0.72)
        tip.lineTo(s * 0.38, s * 0.80)
        tip.closeSubpath()
        p.setBrush(QBrush(QColor(255, 255, 255)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(tip)
        # エネルギーライン2本（薄い白）
        pen_e = QPen(QColor(255, 255, 255, 160), lw * 0.8)
        pen_e.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen_e)
        p.drawLine(QPointF(s * 0.62, s * 0.24), QPointF(s * 0.82, s * 0.12))
        p.drawLine(QPointF(s * 0.70, s * 0.33), QPointF(s * 0.84, s * 0.22))

    elif state == "research":
        # グロー効果（淡い紫外輪）
        p.setBrush(QBrush(QColor(160, 80, 255, 55)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(0, 0, s, s))
        # メイン円
        p.setBrush(QBrush(QColor(140, 60, 240, 255)))
        p.drawEllipse(QRectF(4, 4, s - 8, s - 8))
        lw = max(2.0, s * 0.085)
        # 白い虫眼鏡レンズ（塗りつぶし円 + 内側を空洞にして輪に）
        r_outer = s * 0.23
        r_inner = s * 0.14
        cx, cy = s * 0.37, s * 0.35
        p.setBrush(QBrush(QColor(255, 255, 255, 240)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(cx - r_outer, cy - r_outer, r_outer * 2, r_outer * 2))
        # 内側をくり抜いて輪にする
        p.setBrush(QBrush(QColor(140, 60, 240, 255)))
        p.drawEllipse(QRectF(cx - r_inner, cy - r_inner, r_inner * 2, r_inner * 2))
        # ハンドル（白、太い斜め線）
        pen_h = QPen(QColor(255, 255, 255), lw * 1.9)
        pen_h.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen_h)
        p.drawLine(QPointF(cx + r_outer * 0.70, cy + r_outer * 0.70), QPointF(s * 0.76, s * 0.76))

    elif state == "calendar":
        # グロー外輪
        p.setBrush(QBrush(QColor(0, 230, 120, 55)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QRectF(0, 0, s, s))
        # メイン円（エメラルド）
        p.setBrush(QBrush(QColor(0, 195, 95, 255)))
        p.drawEllipse(QRectF(4, 4, s - 8, s - 8))
        lw = max(2.0, s * 0.085)
        w = QColor(255, 255, 255)
        # シャープな外枠
        pen_f = QPen(w, lw * 1.1)
        pen_f.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(pen_f)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(s * 0.16, s * 0.18, s * 0.52, s * 0.50))
        # トップバー（白塗り）
        p.setBrush(QBrush(w))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(QRectF(s * 0.16, s * 0.18, s * 0.52, s * 0.13))
        # リング（垂直ライン）
        pen_r = QPen(QColor(0, 195, 95), lw * 1.0)
        p.setPen(pen_r)
        for xf in (0.30, 0.52):
            p.drawLine(QPointF(s * xf, s * 0.12), QPointF(s * xf, s * 0.24))
        # グリッド点 2×3（白/半透明）
        dot_r = max(2.5, s * 0.058)
        p.setPen(Qt.PenStyle.NoPen)
        for xi, xf in enumerate((0.27, 0.41, 0.55)):
            for yi, yf in enumerate((0.40, 0.54)):
                clr = QColor(255, 255, 255, 255 if (xi == 0 and yi == 0) else 130)
                p.setBrush(QBrush(clr))
                p.drawRect(QRectF(s * xf - dot_r * 0.7, s * yf - dot_r * 0.7, dot_r * 1.4, dot_r * 1.4))

    else:
        # 待機中: 白マイク + KOE AI テキスト（メニューバー統一デザイン）
        c = QColor(255, 255, 255)
        lw = max(2.0, s * 0.09)
        pen = QPen(c, lw)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        # マイクを上寄せ（テキスト分のスペース確保）
        bw, bh = s * 0.24, s * 0.30
        p.drawRoundedRect(QRectF((s - bw) / 2, s * 0.02, bw, bh), bw / 2, bw / 2)
        ar = s * 0.22
        p.drawArc(QRectF((s - ar * 2) / 2, s * 0.16, ar * 2, ar * 1.1), 0, -180 * 16)
        p.drawLine(QPointF(s / 2, s * 0.42), QPointF(s / 2, s * 0.52))
        p.drawLine(QPointF(s * 0.36, s * 0.52), QPointF(s * 0.64, s * 0.52))
        # KOE AI テキスト（大）
        font = QFont("Helvetica Neue", max(1, int(s * 0.45)))
        font.setBold(True)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, s * 0.01)
        p.setFont(font)
        p.setPen(QColor(255, 255, 255))
        p.drawText(QRectF(0, s * 0.54, s, s * 0.46), Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, "KOE")

    p.end()
    return QIcon(px)


class WorkerSignals(QObject):
    transcription_done = pyqtSignal(str)
    transcription_error = pyqtSignal(str)
    research_done = pyqtSignal(str, str)  # query, answer
    research_error = pyqtSignal(str)
    calendar_done = pyqtSignal(str)  # label
    calendar_error = pyqtSignal(str)
    # ホットキー用（バックグラウンドスレッドからスレッドセーフにメインスレッドへ通知）
    hotkey_toggle = pyqtSignal()
    hotkey_paste = pyqtSignal()
    hotkey_cancel = pyqtSignal()
    hotkey_force_restart = pyqtSignal()


class VoiceInputTrayApp(QObject):
    def __init__(self, app: QApplication):
        super().__init__()
        self._app = app
        self._recorder = AudioRecorder()
        self._last_hotkey_time = 0.0
        self._signals = WorkerSignals()
        self._signals.transcription_done.connect(self._on_transcription_done)
        self._signals.transcription_error.connect(self._on_transcription_error)
        self._signals.research_done.connect(self._on_research_done_main)
        self._signals.research_error.connect(self._on_research_error_main)
        self._signals.calendar_done.connect(self._on_calendar_done_main)
        self._signals.calendar_error.connect(self._on_calendar_error_main)
        self._signals.hotkey_toggle.connect(self.toggle_recording)
        self._signals.hotkey_paste.connect(self._paste_last_transcript)
        self._signals.hotkey_cancel.connect(self._on_hotkey_cancel)
        self._signals.hotkey_force_restart.connect(lambda: __import__('main')._force_restart())
        self._settings_dialog = None
        self._dictionary_win = None
        self._instructions_win = None
        self._replacements_win = None
        self._history_win = None

        self._last_pasted_text = ""
        self._braindump_mode = False
        self._screen_context = ""  # Deep Context: 画面キーワード
        self._tone_widget = None
        self._research_target_pid = 0
        self._icon_idle = _make_icon("idle", 64)
        self._icon_recording = _make_icon("recording", 64)
        self._icon_memo = _make_icon("memo", 64)
        self._icon_research = _make_icon("research", 64)
        self._icon_calendar = _make_icon("calendar", 64)

        self._tray = QSystemTrayIcon(self._icon_idle, parent=self)
        _hk = load_config().get("hotkey", {}).get("display", "Cmd+Option+R")
        self._tray.setToolTip(f"音声入力 - 待機中\n{_hk} で録音開始 / ダブルクリックで再起動")
        self._build_menu()
        self._tray.show()

        self._blink_timer = QTimer()
        self._blink_timer.setInterval(500)
        self._blink_state = False
        self._blink_timer.timeout.connect(self._blink)

        self._research_blink_timer = QTimer()
        self._research_blink_timer.setInterval(600)
        self._research_blink_state = False
        self._research_blink_timer.timeout.connect(self._blink_research)

        self._voice_win = VoiceWindow(self._recorder)
        self._voice_win.set_stop_callback(self._stop_recording)
        self._voice_win.set_cancel_callback(self._cancel_recording)
        self._voice_win.set_wake_word_detector(self._rt_wake_word_detector)

        app.aboutToQuit.connect(self._on_quit)
        self._start_hotkey_listener()

    def _build_menu(self):
        from menu_icons import (
            icon_clipboard,
            icon_history,
            icon_learn,
            icon_memo,
            icon_mic,
            icon_quit,
            icon_research,
            icon_restart,
            icon_settings,
        )

        menu = QMenu()
        cfg = load_config()
        hk = cfg.get("hotkey", {}).get("display", "Cmd+Option+R")
        paste_hk = cfg.get("paste_last_hotkey", {}).get("display", "Cmd+Ctrl+V")
        self._record_action = menu.addAction(icon_mic(), f"録音開始 ({hk})")
        self._record_action.triggered.connect(self.toggle_recording)
        self._braindump_action = menu.addAction(icon_memo(), "音声メモ（メニューから起動）")
        self._braindump_action.triggered.connect(self._start_braindump)
        menu.addSeparator()
        self._paste_last_action = menu.addAction(icon_clipboard(), f"前回の文字起こしを貼り付け ({paste_hk})")
        self._paste_last_action.triggered.connect(self._paste_last_transcript)
        self._paste_last_action.setEnabled(False)
        self._history_action = menu.addAction(icon_history(), "文字起こし履歴")
        self._history_action.triggered.connect(self._open_history)
        self._learn_action = menu.addAction(icon_learn(), "最後の入力を修正して学習")
        self._learn_action.triggered.connect(self._open_learner)
        self._learn_action.setEnabled(False)
        self._research_action = menu.addAction(icon_research(), "リサーチ結果")
        self._research_action.triggered.connect(self._open_research)
        # unread_count() はファイルI/Oなのでメインスレッドをブロックしないよう遅延実行
        QTimer.singleShot(500, self._update_research_label)
        menu.addSeparator()
        settings_action = menu.addAction(icon_settings(), "設定")
        settings_action.triggered.connect(self._open_settings)
        restart_action = menu.addAction(icon_restart(), "再起動")
        restart_action.triggered.connect(self._restart)
        menu.addSeparator()
        quit_action = menu.addAction(icon_quit(), "終了")
        quit_action.triggered.connect(self._app.quit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_activated)

    def _update_research_label(self):
        """リサーチ未読数をバックグラウンドで取得してメニューラベルを更新。"""

        def _check():
            try:
                unread = research_manager.unread_count()
                if unread and hasattr(self, "_research_action"):
                    QTimer.singleShot(0, lambda: self._research_action.setText("リサーチ結果  ●"))
            except Exception:
                pass

        threading.Thread(target=_check, daemon=True).start()

    def _restart(self):
        import os
        import subprocess
        import sys

        # venv の Python を明示指定（sys.executable はシステムPythonを指す場合があるため）
        app_dir = os.path.dirname(os.path.abspath(__file__))
        venv_python = os.path.join(app_dir, "venv", "bin", "python3")
        python_exe = venv_python if os.path.exists(venv_python) else sys.executable
        subprocess.Popen([python_exe, "main.py"], cwd=app_dir)
        self._app.quit()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_recording()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # ダブルクリックで強制再起動（フリーズ時の救済措置）
            self._restart()

    def _on_hotkey_cancel(self):
        """ホットキー（ESC）によるキャンセル。メインスレッドで実行。"""
        win = self._voice_win
        if win.isVisible() and not win._in_edit_mode:
            win._on_cancel()

    def toggle_recording(self):
        import time

        now = time.time()
        if now - self._last_hotkey_time < 0.5:
            return
        self._last_hotkey_time = now
        # 編集モード中（録音していない状態）: 追加録音を開始する
        # start_recording() は _in_edit_mode 中の追加録音をサポート済み
        if self._recorder.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _toggle_deep_context(self, checked: bool):
        """Deep Contextのオン/オフを切り替えてconfig.jsonに保存。"""
        from config import save_config

        config = load_config()
        config["deep_context_enabled"] = checked
        save_config(config)

    def _start_recording(self, memo_mode: bool = False):
        # 最初にフォアグラウンドアプリのPIDを取得（他の処理より前に）
        from voice_window import _get_frontmost_pid

        target_pid = _get_frontmost_pid()
        # Deep Context: 録音ウィンドウ表示前にスクリーンショットを撮影
        self._screen_context = ""
        if load_config().get("deep_context_enabled", False):

            def _capture():
                try:
                    from deep_context import capture_screen_context

                    self._screen_context = capture_screen_context()
                except Exception:
                    self._screen_context = ""

            threading.Thread(target=_capture, daemon=True).start()
        self._recorder.start()
        self._tray.setToolTip("音声入力 - 録音中...")
        self._record_action.setText("⏹ 録音停止 (Cmd+Option+R)")
        self._blink_timer.start()
        self._voice_win.start_recording(memo_mode=memo_mode, target_pid=target_pid)

    def _cancel_recording(self):
        """録音をキャンセル — 文字起こしせずに停止する。"""
        self._blink_timer.stop()
        self._tray.setIcon(self._icon_idle)
        self._recorder.stop()  # 音声データは破棄
        self._reset_record_action()
        self._voice_win.hide()

    def _stop_recording(self):
        self._blink_timer.stop()
        self._tray.setIcon(self._icon_idle)

        # 高速モード: RTテキストをそのまま使い、Whisper APIをスキップ
        if load_config().get("fast_mode", False):
            rt_text = self._voice_win._rt_pending_text.strip()
            # RT表示中のテキストも取得（デバウンス前の最新テキスト）
            if not rt_text:
                rt_label_text = self._voice_win._rt_label.text().strip()
                if rt_label_text:
                    rt_text = rt_label_text
            self._recorder.stop()  # 音声データは破棄
            if not rt_text:
                self._reset_record_action()
                self._voice_win.show_transcribing()
                self._voice_win.hide()
                return
            import sounds

            sounds.play("stop")
            # 後処理（学習済み修正 + アプリ別ルール + 置換）をローカルで適用
            from app_formatter import format_for_app
            from learning import apply_corrections
            from replacements import apply_replacements

            target_pid = self._voice_win._target_pid
            corrected = apply_corrections(rt_text)
            corrected = format_for_app(corrected, target_pid=target_pid)
            corrected = apply_replacements(corrected)
            self._voice_win.show_transcribing()
            self._signals.transcription_done.emit(corrected)
            self._reset_record_action()
            return

        audio_path = self._recorder.stop()
        if not audio_path:
            self._reset_record_action()
            self._voice_win.show_transcribing()  # タイマーを確実に停止
            self._voice_win.hide()
            return
        import sounds

        sounds.play("stop")
        self._voice_win.show_transcribing()  # 「文字起こしを修正中...」表示
        self._record_action.setText("変換中...")
        self._record_action.setEnabled(False)
        target_pid = self._voice_win._target_pid  # 貼り付け先アプリのPID
        threading.Thread(target=self._transcribe_async, args=(audio_path, target_pid), daemon=True).start()

    def _transcribe_async(self, audio_path: str, target_pid: int = 0):
        try:
            text = transcribe(audio_path, target_pid=target_pid, screen_context=self._screen_context)
            self._signals.transcription_done.emit(text)
        except Exception as e:
            from config import safe_error_message

            self._signals.transcription_error.emit(safe_error_message(e))
        finally:
            try:
                os.unlink(audio_path)
            except Exception:
                pass

    def _on_transcription_done(self, text: str):
        try:
            self._on_transcription_done_impl(text)
        except Exception:
            self._reset_record_action()
            self._voice_win.paste_direct("")

    def _on_transcription_done_impl(self, text: str):
        from main import _log
        _log(f"文字起こし完了: text={text[:100] if text else '(empty)'}")
        self._reset_record_action()

        # 編集UI追記モード: テキストボックスが既に表示中なら追記
        if self._voice_win._in_edit_mode and self._voice_win.isVisible():
            win = self._voice_win
            # 録音UI要素をクリーンアップ
            win._rec_lbl.hide()
            win._rec_blink.stop()
            win._level_bars.hide()
            win._level_timer.stop()
            win._status_lbl.hide()
            win._icon_lbl.setPixmap(_px("mic", 18, _CYAN))
            if text.strip():
                existing = win._result_edit.toPlainText()
                separator = "\n" if existing.strip() else ""
                win._result_edit.setPlainText(existing + separator + text.strip())
                win._result_edit.moveCursor(QTextCursor.MoveOperation.End)
            # 編集UIを復元（ボタン含む）
            win._edit_hint.show()
            win._result_edit.show()
            win._btn_row.show()
            win.adjustSize()
            win._position_bottom()
            QTimer.singleShot(150, win._force_activate_edit)
            return

        # 履歴に保存（ウェイクワード処理より前に保存）
        if text.strip():
            try:
                from transcript_history import add_transcript

                add_transcript(text.strip())
            except Exception:
                pass

        # RT検出モードを取得（SFSpeechRecognizerが先にウェイクワードを検出している場合）
        rt_mode = getattr(self._voice_win, "_rt_mode", "normal")

        # ウェイクワード検出: テキストからウェイクワードを除去
        # テキストベース検出 + RT検出のフォールバック
        memo_stripped = _strip_memo_wake_word(text) if text.strip() else None
        research_stripped = _strip_research_wake_word(text) if text.strip() else None
        calendar_stripped = _strip_calendar_wake_word(text) if text.strip() else None

        # モード判定: テキストベースのウェイクワード検出 or RT検出 or メニューからの起動
        detected_mode = "normal"
        _log(f"モード判定: rt_mode={rt_mode}, research_stripped={research_stripped!r}, memo_stripped={memo_stripped!r}")
        if self._braindump_mode or memo_stripped is not None or rt_mode == "memo":
            detected_mode = "memo"
        elif (research_stripped is not None and research_stripped.strip()) or rt_mode == "research":
            detected_mode = "research"
        elif (calendar_stripped is not None and calendar_stripped.strip()) or rt_mode == "calendar":
            detected_mode = "calendar"

        # コンテンツテキストを抽出（ウェイクワードを除去した残り）
        if detected_mode == "memo":
            content = memo_stripped if memo_stripped is not None else text.strip()
        elif detected_mode == "research":
            content = research_stripped if research_stripped is not None and research_stripped.strip() else text.strip()
        elif detected_mode == "calendar":
            content = calendar_stripped if calendar_stripped is not None and calendar_stripped.strip() else text.strip()
        else:
            content = text.strip()

        # --- メモモード ---
        if detected_mode == "memo":
            self._braindump_mode = False
            self._braindump_action.setText("🧠 音声メモ")
            self._tray.setIcon(self._icon_memo)
            self._tray.setToolTip("📝 音声メモ - 保存中...")
            self._voice_win.paste_direct("")  # RT入力済みテキストを消去
            self._show_mode_toast("📝 音声メモモード")
            if content.strip():
                from braindump_window import BraindumpWindow

                if hasattr(self, "_braindump_win") and self._braindump_win and self._braindump_win.isVisible():
                    self._braindump_win.add_entry(content)  # 既存ウィンドウに追記
                else:
                    self._braindump_win = BraindumpWindow(content)  # 新規作成
            QTimer.singleShot(3000, self._reset_tray_icon)
            return

        if not text.strip():
            self._voice_win.paste_direct("")
            self._show_not_recognized()
            return

        # --- リサーチモード ---
        if detected_mode == "research" and content.strip():
            from main import _log
            _log(f"リサーチモード開始: query={content}")
            self._tray.setIcon(self._icon_research)
            self._tray.setToolTip("リサーチ中...")
            self._research_target_pid = self._voice_win._target_pid
            self._voice_win.paste_direct("")
            # ローディング状態のポップアップを即座に表示
            from research_popup import ResearchPopup
            if hasattr(self, "_research_popup") and self._research_popup:
                self._research_popup.close()
            self._research_popup = ResearchPopup(content, loading=True)
            self._research_popup.show()
            self._research_blink_timer.start()
            research_manager.process_direct(
                content,
                on_new_result=self._on_research_found,
                on_error=self._on_research_error,
            )
            QTimer.singleShot(60000, self._stop_research_blink)
            return

        # --- カレンダーモード ---
        if detected_mode == "calendar" and content.strip():
            self._tray.setIcon(self._icon_calendar)
            self._tray.setToolTip("📅 予定を追加中...")
            self._voice_win.paste_direct("")
            self._show_mode_toast("📅 予定を登録中...")
            import calendar_manager

            calendar_manager.process_async(
                content,
                on_done=self._on_calendar_done,
                on_error=self._on_calendar_error,
            )
            QTimer.singleShot(8000, self._reset_tray_icon)
            return

        self._last_pasted_text = text
        self._learn_action.setEnabled(True)
        self._paste_last_action.setEnabled(True)

        # 文字起こしモード: edit=編集ウィンドウ表示, direct=入力欄に直接貼り付け
        cfg = load_config()
        if cfg.get("transcription_mode", "edit") == "direct":
            self._voice_win.paste_direct(text)
        else:
            # テキストボックス内で修正可能。修正があれば自動で学習される
            self._voice_win.show_result(text)

    def _show_not_recognized(self):
        from PyQt6.QtCore import Qt, QTimer
        from PyQt6.QtGui import QBrush, QColor, QPainter, QPen
        from PyQt6.QtWidgets import QLabel

        class _Toast(QLabel):
            def paintEvent(self, e):
                p = QPainter(self)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                p.setBrush(QBrush(QColor(8, 10, 26, 210)))
                p.setPen(QPen(QColor(255, 100, 100, 120), 1))
                p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 16, 16)
                p.end()
                super().paintEvent(e)

        toast = _Toast("聞き取れませんでした")
        toast.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        )
        toast.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        toast.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        f = QFont("Hiragino Sans")
        f.setPointSize(12)
        toast.setFont(f)
        toast.setStyleSheet("color: rgba(255,140,140,0.9); padding: 8px 18px;")
        toast.adjustSize()

        screen = self._app.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            toast.move(geo.center().x() - toast.width() // 2, geo.bottom() - toast.height() - 40)
        toast.show()
        self._toast = toast  # GCされないよう保持
        QTimer.singleShot(2500, toast.hide)

    def _on_quit(self):
        """アプリ終了前にトレイアイコンとCore Audioエンジンを確実に停止する。"""
        try:
            self._tray.hide()  # ステータスバーアイテムを確実に削除
        except Exception:
            pass
        try:
            self._voice_win._on_cancel()
        except Exception:
            pass

    def _start_braindump(self):
        """ブレインダンプモードで録音開始。"""
        if self._recorder.is_recording:
            return
        self._braindump_mode = True
        self._braindump_action.setText("🧠 音声メモ録音中... (停止で保存)")
        self._tray.setToolTip("📝 音声メモモード - 録音中...")
        self._start_recording(memo_mode=True)

    def _show_tone_widget(self, text: str):
        """ビジネス文変換ボタンを表示。"""
        if self._tone_widget:
            self._tone_widget.hide()
        from tone_widget import ToneWidget

        self._tone_widget = ToneWidget(
            original_text=text,
            on_replace=self._replace_last_paste,
        )

    def _replace_last_paste(self, new_text: str):
        """ペースト済みテキストを新テキストで置換。"""
        import pyperclip

        from voice_window import _quartz_backspace, _quartz_cmd_v

        old_text = self._last_pasted_text
        pid = self._voice_win._target_pid
        self._last_pasted_text = new_text

        def _do():
            import time

            if pid:
                try:
                    from AppKit import NSApplicationActivateIgnoringOtherApps, NSRunningApplication

                    app_obj = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
                    if app_obj:
                        app_obj.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
                        time.sleep(0.1)
                except Exception:
                    pass
            _quartz_backspace(len(old_text), pid)
            time.sleep(0.05)
            pyperclip.copy(new_text)
            time.sleep(0.05)
            _quartz_cmd_v(pid)

        threading.Thread(target=_do, daemon=True).start()

    def _rt_wake_word_detector(self, text: str):
        """RTテキストからウェイクワードを検出してモードを返す（バックグラウンドスレッドから呼ばれる）。
        セパレータ付きのウェイクワードが先頭にある場合のみ検出する。"""
        stripped = _strip_memo_wake_word(text)
        if stripped is not None:

            def _set_memo():
                try:
                    self._tray.setIcon(self._icon_memo)
                    self._tray.setToolTip("📝 音声メモモード - 録音中...")
                except Exception:
                    pass

            QTimer.singleShot(0, _set_memo)
            return "memo"
        r_stripped = _strip_research_wake_word(text)
        if r_stripped is not None:

            def _set_research():
                try:
                    self._tray.setIcon(self._icon_research)
                    self._tray.setToolTip("リサーチモード - 録音中...")
                except Exception:
                    pass

            QTimer.singleShot(0, _set_research)
            return "research"
        c_stripped = _strip_calendar_wake_word(text)
        if c_stripped is not None:

            def _set_calendar():
                try:
                    self._tray.setIcon(self._icon_calendar)
                    self._tray.setToolTip("📅 カレンダーモード - 録音中...")
                except Exception:
                    pass

            QTimer.singleShot(0, _set_calendar)
            return "calendar"
        return None

    def _reset_tray_icon(self):
        """トレイアイコンとツールチップをidle状態に戻す。"""
        self._tray.setIcon(self._icon_idle)
        hk = self._hotkey_display()
        self._tray.setToolTip(f"音声入力 - 待機中\n{hk} で録音開始 / ダブルクリックで再起動")

    def _show_mode_toast(self, message: str):
        """モード切り替えトースト通知を表示。"""
        try:
            from PyQt6.QtCore import Qt, QTimer
            from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
            from PyQt6.QtWidgets import QLabel

            class _ModeToast(QLabel):
                def paintEvent(self, e):
                    try:
                        p = QPainter(self)
                        p.setRenderHint(QPainter.RenderHint.Antialiasing)
                        p.setBrush(QBrush(QColor(8, 10, 26, 220)))
                        p.setPen(QPen(QColor(160, 80, 255, 160), 1))
                        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 16, 16)
                        p.end()
                        super().paintEvent(e)
                    except Exception:
                        pass

            toast = _ModeToast(message)
            toast.setWindowFlags(
                Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
            )
            toast.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            toast.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
            f = QFont("Hiragino Sans")
            f.setPointSize(13)
            f.setBold(True)
            toast.setFont(f)
            toast.setStyleSheet("color: rgba(220,180,255,0.95); padding: 10px 22px;")
            toast.adjustSize()

            screen = self._app.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                toast.move(geo.center().x() - toast.width() // 2, geo.bottom() - toast.height() - 40)
            toast.show()
            self._mode_toast = toast  # GCされないよう保持
            QTimer.singleShot(2500, toast.hide)
        except Exception:
            pass

    def _on_calendar_done(self, label: str):
        """バックグラウンドスレッドから呼ばれる — シグナル経由でメインスレッドへ渡す。"""
        try:
            import sounds

            sounds.play("calendar")
        except Exception:
            pass
        self._signals.calendar_done.emit(label)

    def _on_calendar_error(self, msg: str):
        """バックグラウンドスレッドから呼ばれる — シグナル経由でメインスレッドへ渡す。"""
        self._signals.calendar_error.emit(msg)

    def _on_calendar_done_main(self, label: str):
        """メインスレッドで実行: トースト表示とアイコン更新。"""
        try:
            self._tray.setIcon(self._icon_calendar)
            self._tray.setToolTip(f"📅 追加しました: {label}")
            self._show_mode_toast(f"📅 追加しました\n{label}")
            QTimer.singleShot(4000, self._reset_tray_icon)
        except Exception:
            pass

    def _on_calendar_error_main(self, msg: str):
        """メインスレッドで実行: エラートースト。"""
        try:
            self._reset_tray_icon()
            self._show_mode_toast(f"❌ 予定追加に失敗: {msg[:40]}")
        except Exception:
            pass

    def _on_research_found(self, item: str, answer: str):
        """バックグラウンドスレッドから呼ばれる — シグナル経由でメインスレッドへ渡す。"""
        from main import _log
        _log(f"リサーチ結果受信: item={item}, answer_len={len(answer)}")
        self._signals.research_done.emit(item, answer)

    def _on_research_error(self, msg: str):
        """バックグラウンドスレッドから呼ばれる — シグナル経由でメインスレッドへ渡す。"""
        from main import _log
        _log(f"リサーチエラー: {msg}")
        self._signals.research_error.emit(msg)

    def _stop_research_blink(self):
        self._research_blink_timer.stop()
        self._reset_tray_icon()

    def _on_research_done_main(self, item: str, answer: str):
        """メインスレッドで実行: ローディング中のポップアップに回答を表示。"""
        from main import _log
        _log(f"リサーチ結果表示: item={item}")
        try:
            self._research_blink_timer.stop()
            self._update_research_badge()
            self._tray.setIcon(self._icon_research)
            self._tray.setToolTip(f"リサーチ完了: {item}")

            # 既存ポップアップを更新（ローディング→回答）
            if hasattr(self, "_research_popup") and self._research_popup:
                self._research_popup.set_answer(answer.strip())
            else:
                # フォールバック: ポップアップがなければ新規作成
                from research_popup import ResearchPopup
                self._research_popup = ResearchPopup(item, answer.strip())
                self._research_popup.show()

            import sounds
            sounds.play("paste")
            QTimer.singleShot(3000, self._reset_tray_icon)
        except Exception as e:
            _log(f"ポップアップ表示エラー: {e}")
            import traceback
            _log(traceback.format_exc())

    def _paste_research_result(self, text: str, pid: int):
        """バックグラウンドスレッドでリサーチ結果を元アプリへ貼り付け。"""
        import time

        import pyperclip

        from voice_window import _CLIPBOARD_LOCK, _quartz_cmd_v

        try:
            if pid:
                from AppKit import NSApplicationActivateIgnoringOtherApps, NSRunningApplication

                app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
                if app:
                    app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
                    time.sleep(0.15)
            with _CLIPBOARD_LOCK:
                pyperclip.copy(text)
                time.sleep(0.05)
                _quartz_cmd_v(pid)
            import sounds

            sounds.play("paste")
        except Exception:
            pass

    def _on_research_error_main(self, msg: str):
        """メインスレッドで実行: エラー通知。"""
        try:
            self._research_blink_timer.stop()
            self._reset_tray_icon()
            self._tray.showMessage(
                "❌ リサーチ失敗",
                msg[:120],
                QSystemTrayIcon.MessageIcon.Warning,
                6000,
            )
        except Exception:
            pass

    def _show_research_toast(self, query: str, preview: str):
        """リサーチ結果トースト（クエリ＋回答冒頭）。"""
        try:
            from PyQt6.QtCore import Qt, QTimer
            from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
            from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

            class _Toast(QWidget):
                def paintEvent(self, e):
                    try:
                        p = QPainter(self)
                        p.setRenderHint(QPainter.RenderHint.Antialiasing)
                        p.setBrush(QBrush(QColor(8, 10, 26, 230)))
                        p.setPen(QPen(QColor(168, 85, 247, 160), 1))
                        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 16, 16)
                        p.end()
                        super().paintEvent(e)
                    except Exception:
                        pass

            toast = _Toast()
            toast.setWindowFlags(
                Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
            )
            toast.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            toast.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

            layout = QVBoxLayout(toast)
            layout.setContentsMargins(16, 12, 16, 12)
            layout.setSpacing(4)

            f_title = QFont("Hiragino Sans")
            f_title.setPointSize(11)
            f_title.setBold(True)
            f_body = QFont("Hiragino Sans")
            f_body.setPointSize(10)

            lbl_q = QLabel(f"🔍 {query}")
            lbl_q.setFont(f_title)
            lbl_q.setStyleSheet("color: rgba(200,160,255,0.95);")
            layout.addWidget(lbl_q)

            lbl_a = QLabel(preview)
            lbl_a.setFont(f_body)
            lbl_a.setStyleSheet("color: rgba(220,220,220,0.85);")
            lbl_a.setWordWrap(True)
            lbl_a.setMaximumWidth(400)
            layout.addWidget(lbl_a)

            toast.adjustSize()
            screen = self._app.primaryScreen()
            if screen:
                geo = screen.availableGeometry()
                toast.move(geo.center().x() - toast.width() // 2, geo.bottom() - toast.height() - 40)
            toast.show()
            self._research_toast = toast
            QTimer.singleShot(12000, toast.hide)
        except Exception:
            pass

    def _update_research_badge(self):
        unread = research_manager.unread_count()
        self._research_action.setText(f"🔍 リサーチ結果{'  ●' if unread else ''}")

    def _open_research(self):
        from research_window import ResearchWindow

        self._research_win = ResearchWindow()
        self._research_win.show()
        QTimer.singleShot(100, self._update_research_badge)

    def _show_correction_window(self, text: str):
        """非モーダル確認ウィンドウを表示。修正があった時のみ学習ボタンを出す。"""
        try:
            from correction_window import CorrectionWindow

            pid = self._voice_win._target_pid
            self._correction_win = CorrectionWindow(text, target_pid=pid)
            self._correction_win.finished.connect(lambda final, action: self._on_correction_done(final, action, pid))
            self._correction_win.show()
        except Exception:
            self._voice_win.paste_direct(text)

    def _on_correction_done(self, text: str, action: str, pid: int):
        """修正ウィンドウからのコールバック。"""
        if action == "paste" and text.strip():
            self._voice_win._target_pid = pid
            import threading

            threading.Thread(target=self._voice_win._replace_rt_and_paste, args=(0, text), daemon=True).start()
            self._show_tone_widget(text)

    def _paste_last_transcript(self):
        """前回の文字起こしテキストを編集ウィンドウで再表示する。"""
        text = self._last_pasted_text
        if not text:
            return

        from voice_window import _get_frontmost_pid, _save_focused_window

        win = self._voice_win
        pid = _get_frontmost_pid()
        win._target_pid = pid
        win._target_ax_window = _save_focused_window(pid)

        # 録音UI要素を確実に隠す
        win._rec_lbl.hide()
        win._cancel_btn.hide()
        win._stop_btn.hide()
        win._rec_blink.stop()
        win._level_bars.hide()
        win._level_timer.stop()
        win._status_lbl.hide()
        win._rt_label.setText("")
        win._rt_label.hide()
        win._cursor_indicator.hide_indicator()

        # 編集UIを設定
        win._whisper_original = text.strip()
        win._result_edit.setPlainText(text.strip())
        win._edit_hint.show()
        win._result_edit.show()
        win._btn_row.show()
        win._in_edit_mode = True
        win._rt_field_text = ""

        # ウィンドウをアクティブ化可能にして表示
        win.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, False)
        win.adjustSize()
        win._position_bottom()
        win.show()
        win.raise_()
        QTimer.singleShot(150, win._force_activate_edit)

    def _open_learner(self):
        if self._last_pasted_text:
            from post_paste_learner import PostPasteLearnerWindow

            self._learner_win = PostPasteLearnerWindow(self._last_pasted_text)
            self._learner_win.show()

    def _on_transcription_error(self, error_msg: str):
        self._reset_record_action()
        self._voice_win.hide()
        if "インターネット接続がありません" in error_msg:
            self._show_mode_toast("🌐 インターネット接続がありません")
        else:
            QMessageBox.critical(None, "エラー", f"音声認識エラー:\n{error_msg}")

    def _reset_record_action(self):
        hk = self._hotkey_display()
        self._record_action.setText(f"録音開始 ({hk})")
        self._record_action.setEnabled(True)
        self._tray.setToolTip(f"音声入力 - 待機中\n{hk} で録音開始 / ダブルクリックで再起動")

    def _blink(self):
        self._blink_state = not self._blink_state
        if self._blink_state:
            icon = self._icon_memo if self._braindump_mode else self._icon_recording
        else:
            icon = self._icon_idle
        self._tray.setIcon(icon)

    def _blink_research(self):
        self._research_blink_state = not self._research_blink_state
        self._tray.setIcon(self._icon_research if self._research_blink_state else self._icon_idle)

    def _open_dictionary(self):
        if self._dictionary_win and self._dictionary_win.isVisible():
            self._dictionary_win.raise_()
            self._dictionary_win.activateWindow()
            return
        from dictionary_window import DictionaryWindow

        self._dictionary_win = DictionaryWindow()
        self._dictionary_win.show()

    def _open_replacements(self):
        if self._replacements_win and self._replacements_win.isVisible():
            self._replacements_win.raise_()
            self._replacements_win.activateWindow()
            return
        from replacements_window import ReplacementsWindow

        self._replacements_win = ReplacementsWindow()
        self._replacements_win.show()

    def _open_instructions(self):
        if self._instructions_win and self._instructions_win.isVisible():
            self._instructions_win.raise_()
            self._instructions_win.activateWindow()
            return
        from instructions_window import InstructionsWindow

        self._instructions_win = InstructionsWindow()
        self._instructions_win.show()

    def _open_history(self):
        if self._history_win and self._history_win.isVisible():
            self._history_win.raise_()
            self._history_win.activateWindow()
            return
        from transcript_history_window import TranscriptHistoryWindow

        self._history_win = TranscriptHistoryWindow()
        self._history_win.show()

    def _open_settings(self):
        if self._settings_dialog and self._settings_dialog.isVisible():
            self._settings_dialog.raise_()
            self._settings_dialog.activateWindow()
            return
        self._settings_dialog = SettingsDialog()
        self._settings_dialog.show()

    def _hotkey_display(self) -> str:
        return load_config().get("hotkey", {}).get("display", "Cmd+Option+R")

    def _start_hotkey_listener(self):
        def listen():
            import Quartz

            ESC_KEYCODE = 53
            MODIFIER_MASK = (
                Quartz.kCGEventFlagMaskCommand
                | Quartz.kCGEventFlagMaskShift
                | Quartz.kCGEventFlagMaskAlternate
                | Quartz.kCGEventFlagMaskControl
            )

            # ホットキー設定をキャッシュ（イベントタップ内でファイルI/Oしない）
            import time as _time

            _cached_config = [None, 0.0]  # [config_dict, timestamp]
            _CACHE_TTL = 5.0  # 5秒キャッシュ

            def _get_cached_config():
                now = _time.monotonic()
                if _cached_config[0] is None or now - _cached_config[1] > _CACHE_TTL:
                    try:
                        _cached_config[0] = load_config()
                        _cached_config[1] = now
                    except Exception:
                        if _cached_config[0] is None:
                            _cached_config[0] = {}
                return _cached_config[0]

            def _load_hotkey():
                cfg = _get_cached_config().get("hotkey", {})
                return cfg.get("keycode", 15), cfg.get("quartz_flags", 1572864)

            # 前回の文字起こしを貼り付け（設定から読み込み）
            def _load_paste_hotkey():
                cfg = _get_cached_config().get("paste_last_hotkey", {})
                return cfg.get("keycode", 9), cfg.get(
                    "quartz_flags", Quartz.kCGEventFlagMaskCommand | Quartz.kCGEventFlagMaskControl
                )

            # Return/Enter キー（編集UI表示中に貼り付け実行）
            RETURN_KEYCODE = 36
            ENTER_KEYCODE = 76  # テンキーEnter

            # 緊急再起動用: ホットキー連続押下を追跡
            _rapid_press_times = []

            def callback(proxy, event_type, event, refcon):
                try:
                    keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
                    flags = Quartz.CGEventGetFlags(event) & MODIFIER_MASK

                    target_kc, target_flags = _load_hotkey()
                    if keycode == target_kc and flags == target_flags:
                        import time as _t

                        now = _t.time()
                        _rapid_press_times.append(now)
                        # 直近2秒以内の押下だけ残す
                        while _rapid_press_times and now - _rapid_press_times[0] > 2.0:
                            _rapid_press_times.pop(0)
                        if len(_rapid_press_times) >= 4:
                            # 4連打 = 緊急強制再起動（Qtイベントループに依存しない）
                            _rapid_press_times.clear()
                            from main import _force_restart

                            _force_restart()
                            return None
                        self._signals.hotkey_toggle.emit()
                        return None

                    paste_kc, paste_flags = _load_paste_hotkey()
                    if keycode == paste_kc and flags == paste_flags:
                        self._signals.hotkey_paste.emit()
                        return None

                    if keycode == ESC_KEYCODE and flags == 0:
                        # スレッドセーフ: Qtウィジェットに直接アクセスせず、
                        # シグナル経由でメインスレッドに判定を任せる
                        # イベントは消費しない（メインスレッドで条件チェック後にキャンセル）
                        self._signals.hotkey_cancel.emit()

                    # Return/Enter: Qt側（_EditTextBox.keyPressEvent / VoiceWindow.keyPressEvent）で処理。
                    # CGEventTapでは消費しない（バックグラウンドスレッドからのQt widget
                    # アクセスはスレッドセーフでなく、イベント漏れの原因になるため）。

                except Exception:
                    pass
                return event

            mask = Quartz.CGEventMaskBit(Quartz.kCGEventKeyDown)
            for _attempt in range(3):
                tap = Quartz.CGEventTapCreate(
                    Quartz.kCGSessionEventTap,
                    Quartz.kCGHeadInsertEventTap,
                    Quartz.kCGEventTapOptionDefault,
                    mask,
                    callback,
                    None,
                )
                if tap:
                    break
                import time

                time.sleep(1)
            if not tap:
                return
            src = Quartz.CFMachPortCreateRunLoopSource(None, tap, 0)
            loop = Quartz.CFRunLoopGetCurrent()
            Quartz.CFRunLoopAddSource(loop, src, Quartz.kCFRunLoopCommonModes)
            Quartz.CGEventTapEnable(tap, True)

            # macOS がイベントタップを無効化した場合に再有効化するタイマー
            def _re_enable_tap(timer, info):
                if not Quartz.CGEventTapIsEnabled(tap):
                    Quartz.CGEventTapEnable(tap, True)

            timer = Quartz.CFRunLoopTimerCreate(
                None, Quartz.CFAbsoluteTimeGetCurrent() + 5.0, 5.0, 0, 0, _re_enable_tap, None
            )
            Quartz.CFRunLoopAddTimer(loop, timer, Quartz.kCFRunLoopCommonModes)
            Quartz.CFRunLoopRun()

        threading.Thread(target=listen, daemon=True).start()
