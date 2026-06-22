"""Floating correction window for editing transcribed text before pasting."""

import threading

import pyperclip
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from learning import force_regenerate, learn_correction


class CorrectionWindow(QWidget):
    """非モーダル修正ウィンドウ。exec() は使わない。"""

    # シグナル: (final_text, action)  action = "paste" | "copy" | "cancel"
    finished = pyqtSignal(str, str)

    def __init__(self, transcribed_text: str, target_pid: int = 0, parent=None):
        super().__init__(parent)
        self._original_text = transcribed_text
        self._target_pid = target_pid
        self._already_learned = False
        self._setup_ui(transcribed_text)

    def _setup_ui(self, text: str):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(520)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # カードコンテナ
        card = QWidget()
        card.setObjectName("card")
        card.setStyleSheet("""
            QWidget#card {
                background-color: rgba(28, 28, 30, 245);
                border-radius: 18px;
                border: 1px solid rgba(0,229,255,0.25);
            }
        """)
        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setSpacing(10)
        layout.setContentsMargins(18, 14, 18, 14)

        # Header
        header = QLabel("🎙 認識結果を確認・修正")
        f = QFont("Hiragino Sans", 13)
        f.setBold(True)
        header.setFont(f)
        header.setStyleSheet("color: white;")
        layout.addWidget(header)

        # Text editor
        self._text_edit = QTextEdit()
        self._text_edit.setPlainText(text)
        self._text_edit.setFont(QFont("Hiragino Sans", 13))
        self._text_edit.setMinimumHeight(80)
        self._text_edit.setMaximumHeight(180)
        self._text_edit.setStyleSheet(
            "QTextEdit { color: white; background: rgba(50,50,55,190);"
            " border: 1px solid rgba(0,122,255,0.5); border-radius: 10px;"
            " padding: 8px; }"
        )
        layout.addWidget(self._text_edit)

        # 修正履歴を学習ボタン（修正時のみ表示）
        self._learn_btn = QPushButton("🧠 修正履歴を学習")
        self._learn_btn.setStyleSheet(
            "QPushButton { background-color: #30d158; color: white; "
            "border-radius: 6px; padding: 6px 14px; font-size: 12px; }"
            "QPushButton:hover { background-color: #25a244; }"
            "QPushButton:disabled { background-color: #555; color: #aaa; }"
        )
        self._learn_btn.clicked.connect(self._on_learn_now)
        self._learn_btn.hide()
        layout.addWidget(self._learn_btn)

        # テキスト変更を監視
        self._text_edit.textChanged.connect(self._on_text_changed)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        cancel_btn = QPushButton("キャンセル")
        cancel_btn.setStyleSheet(
            "QPushButton { background:#3a3a3c; color:white; border-radius:8px; padding:7px 14px; font-size:12px; }"
        )
        cancel_btn.clicked.connect(self._on_cancel)

        copy_btn = QPushButton("コピーのみ")
        copy_btn.setStyleSheet(
            "QPushButton { background:#3a3a3c; color:white; border-radius:8px; padding:7px 14px; font-size:12px; }"
        )
        copy_btn.clicked.connect(self._on_copy_only)

        paste_btn = QPushButton("貼り付け (Return)")
        paste_btn.setStyleSheet(
            "QPushButton { background-color: #007AFF; color: white; "
            "border-radius: 8px; padding: 7px 14px; font-size: 12px; }"
            "QPushButton:hover { background-color: #0056CC; }"
        )
        paste_btn.clicked.connect(self._on_paste)
        paste_btn.setDefault(True)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(copy_btn)
        btn_layout.addWidget(paste_btn)
        layout.addLayout(btn_layout)

        # Shortcut
        esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc.activated.connect(self._on_cancel)

        self.adjustSize()

    def paintEvent(self, e):
        pass  # 透過背景のためデフォルトを無効化

    def showEvent(self, event):
        super().showEvent(event)
        # 画面中央下部に配置
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.adjustSize()
            x = geo.center().x() - self.width() // 2
            y = geo.bottom() - self.height() - 40
            self.move(x, y)
        self._text_edit.setFocus()
        self._text_edit.selectAll()

    def _get_current_text(self) -> str:
        return self._text_edit.toPlainText().strip()

    def _on_text_changed(self):
        current = self._text_edit.toPlainText().strip()
        if current != self._original_text and not self._already_learned:
            self._learn_btn.show()
        else:
            self._learn_btn.hide()

    def _on_learn_now(self):
        current = self._get_current_text()
        if not current or current == self._original_text:
            return
        self._already_learned = True
        self._learn_btn.setEnabled(False)
        self._learn_btn.setText("学習中...")
        # バックグラウンドで学習実行（メインスレッドをブロックしない）
        threading.Thread(target=self._do_learn, args=(self._original_text, current), daemon=True).start()
        QTimer.singleShot(1500, self._on_learn_done)

    @staticmethod
    def _do_learn(original: str, corrected: str):
        try:
            learn_correction(original, corrected)
            force_regenerate()
        except Exception:
            pass

    def _on_learn_done(self):
        self._learn_btn.setText("✓ 学習しました")

    def _on_paste(self):
        text = self._get_current_text()
        if not text:
            return
        if not self._already_learned and text != self._original_text:
            threading.Thread(target=self._do_learn, args=(self._original_text, text), daemon=True).start()
        self.finished.emit(text, "paste")
        self.close()

    def _on_copy_only(self):
        text = self._get_current_text()
        if not text:
            return
        pyperclip.copy(text)
        if not self._already_learned and text != self._original_text:
            threading.Thread(target=self._do_learn, args=(self._original_text, text), daemon=True).start()
        self.finished.emit(text, "copy")
        self.close()

    def _on_cancel(self):
        self.finished.emit("", "cancel")
        self.close()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self._on_cancel()
        elif e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if not e.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self._on_paste()
            else:
                super().keyPressEvent(e)
        else:
            super().keyPressEvent(e)
