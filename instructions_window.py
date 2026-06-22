"""カスタム指示ウィンドウ — 文字起こしの変換スタイルを指定する。"""

import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

# 保存先パス
_INSTRUCTIONS_DIR = os.path.expanduser("~/.voice_input_app")
_INSTRUCTIONS_PATH = os.path.join(_INSTRUCTIONS_DIR, "custom_instructions.txt")


def load_custom_instructions() -> str:
    """カスタム指示テキストを読み込む。ファイルがなければ空文字を返す。"""
    try:
        with open(_INSTRUCTIONS_PATH, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def _save_custom_instructions(text: str):
    """カスタム指示テキストをファイルに保存する。"""
    os.makedirs(_INSTRUCTIONS_DIR, exist_ok=True)
    with open(_INSTRUCTIONS_PATH, "w", encoding="utf-8") as f:
        f.write(text.strip())


class InstructionsWindow(QWidget):
    """カスタム指示を編集する非モーダルウィンドウ。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
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

        # タイトル
        title = QLabel("📝 カスタム指示")
        f_title = QFont("Hiragino Sans", 13)
        f_title.setBold(True)
        title.setFont(f_title)
        title.setStyleSheet("color: white;")
        layout.addWidget(title)

        # サブタイトル
        subtitle = QLabel(
            "文字起こしの変換スタイルを指示できます。\n例: 「Slackではカジュアルな口調で」「句読点を使わない」"
        )
        subtitle.setFont(QFont("Hiragino Sans", 10))
        subtitle.setStyleSheet("color: rgba(180,180,180,0.9);")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # テキストエディタ
        self._text_edit = QTextEdit()
        self._text_edit.setPlaceholderText("ここにカスタム指示を入力...")
        self._text_edit.setFont(QFont("Hiragino Sans", 13))
        self._text_edit.setMinimumHeight(120)
        self._text_edit.setMaximumHeight(240)
        self._text_edit.setStyleSheet(
            "QTextEdit { color: white; background: rgba(50,50,55,190);"
            " border: 1px solid rgba(0,122,255,0.5); border-radius: 10px;"
            " padding: 8px; }"
        )
        # 既存の指示を読み込み
        self._text_edit.setPlainText(load_custom_instructions())
        layout.addWidget(self._text_edit)

        # 保存ボタン
        save_btn = QPushButton("保存")
        save_btn.setStyleSheet(
            "QPushButton { background-color: #007AFF; color: white; "
            "border-radius: 8px; padding: 7px 14px; font-size: 12px; }"
            "QPushButton:hover { background-color: #0056CC; }"
        )
        save_btn.clicked.connect(self._on_save)
        layout.addWidget(save_btn)

        # Escapeで閉じる
        esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc.activated.connect(self.close)

        self.adjustSize()

    def paintEvent(self, e):
        pass  # 透過背景

    def showEvent(self, event):
        super().showEvent(event)
        # 画面中央に配置
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.adjustSize()
            x = geo.center().x() - self.width() // 2
            y = geo.center().y() - self.height() // 2
            self.move(x, y)
        self._text_edit.setFocus()

    def _on_save(self):
        text = self._text_edit.toPlainText()
        _save_custom_instructions(text)
        self.close()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(e)
