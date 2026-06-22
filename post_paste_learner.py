"""貼り付け後の修正を学習するためのフォローアップUI。"""

import subprocess

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget


class PostPasteBadge(QWidget):
    """貼り付け後に数秒だけ表示される「後から学習」バッジ。"""

    def __init__(self, pasted_text: str):
        super().__init__()
        self._pasted_text = pasted_text
        self._learner_window = None
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.hide)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedHeight(42)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 14, 6)
        layout.setSpacing(8)

        btn = QPushButton("🧠 修正履歴を学習")
        btn.setFixedHeight(30)
        btn.setStyleSheet(
            "QPushButton { background: rgba(0,229,255,0.08); color: #00e5ff; "
            "border: 1px solid rgba(0,229,255,0.45); "
            "border-radius: 8px; padding: 0 16px; font-size: 12px; font-weight: 500; }"
            "QPushButton:hover { background: rgba(0,229,255,0.18); border-color: rgba(0,229,255,0.8); }"
        )
        btn.clicked.connect(self._open_learner)
        layout.addWidget(btn)

        self.adjustSize()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor(6, 8, 22, 230)))
        from PyQt6.QtGui import QPen

        p.setPen(QPen(QColor(0, 229, 255, 80), 1))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 14, 14)
        p.end()

    def show_near_bottom(self, offset_x: int = 0):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        x = geo.center().x() - self.width() // 2 + offset_x
        y = geo.bottom() - self.height() - 16
        self.move(x, y)
        self.show()
        self.raise_()
        self._auto_hide_timer.start(8000)  # 8秒で自動非表示

    def _open_learner(self):
        self._auto_hide_timer.stop()
        self.hide()
        self._learner_window = PostPasteLearnerWindow(self._pasted_text)
        self._learner_window.show()


class PostPasteLearnerWindow(QWidget):
    """貼り付け後の修正テキストを入力して学習させるウィンドウ。"""

    def __init__(self, original_pasted: str):
        super().__init__()
        self._original = original_pasted
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(500)
        self._build_ui()
        self._position()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QWidget()
        card.setObjectName("card")
        card.setStyleSheet("""
            QWidget#card {
                background-color: rgba(28, 28, 30, 240);
                border-radius: 20px;
                border: 1px solid rgba(255,255,255,0.13);
            }
        """)
        outer.addWidget(card)

        main = QVBoxLayout(card)
        main.setContentsMargins(20, 16, 20, 16)
        main.setSpacing(10)

        # タイトル
        title_row = QHBoxLayout()
        title = QLabel("🧠 貼り付け後の修正を学習")
        f = QFont()
        f.setPointSize(13)
        f.setBold(True)
        title.setFont(f)
        title.setStyleSheet("color: white;")
        title_row.addWidget(title)
        title_row.addStretch()
        main.addLayout(title_row)

        # 元の文章（読み取り専用）
        orig_lbl = QLabel("貼り付けた文章（元）:")
        orig_lbl.setStyleSheet("color: rgba(255,255,255,0.5); font-size: 11px;")
        main.addWidget(orig_lbl)

        orig_box = QLabel(self._original)
        orig_box.setWordWrap(True)
        orig_box.setFont(QFont("Hiragino Sans", 12))
        orig_box.setStyleSheet(
            "color: rgba(255,255,255,0.55); background: rgba(50,50,55,120); "
            "border-radius: 8px; padding: 8px; font-style: italic;"
        )
        main.addWidget(orig_box)

        # 修正後テキスト
        corr_lbl = QLabel("修正後のテキスト（編集してください）:")
        corr_lbl.setStyleSheet("color: rgba(255,255,255,0.7); font-size: 11px;")
        main.addWidget(corr_lbl)

        self._corrected_edit = QTextEdit()
        self._corrected_edit.setFont(QFont("Hiragino Sans", 13))
        self._corrected_edit.setPlainText(self._original)
        self._corrected_edit.setMinimumHeight(80)
        self._corrected_edit.setMaximumHeight(140)
        self._corrected_edit.setStyleSheet("""
            QTextEdit {
                color: white;
                background-color: rgba(50,50,55,190);
                border: 1px solid rgba(0,122,255,0.6);
                border-radius: 10px;
                padding: 8px;
            }
        """)
        main.addWidget(self._corrected_edit)

        hint = QLabel("💡 修正内容はWhisperの変換精度向上に使われます")
        hint.setStyleSheet("color: rgba(255,255,255,0.35); font-size: 10px;")
        main.addWidget(hint)

        # ボタン
        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("キャンセル (Esc)")
        cancel_btn.setStyleSheet(
            "QPushButton { background:#3a3a3c; color:white; border-radius:8px; padding:7px 14px; font-size:12px; }"
        )
        cancel_btn.clicked.connect(self.close)

        learn_btn = QPushButton("✅ 学習して閉じる")
        learn_btn.setStyleSheet(
            "QPushButton { background:#30d158; color:white; border-radius:8px; padding:7px 14px; font-size:12px; }"
        )
        learn_btn.clicked.connect(self._on_learn)

        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        btn_row.addWidget(learn_btn)
        main.addLayout(btn_row)

        self.adjustSize()

        # テキスト全選択
        self._corrected_edit.setFocus()
        self._corrected_edit.selectAll()

    def _position(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.adjustSize()
            x = geo.center().x() - self.width() // 2
            y = geo.bottom() - self.height() - 28
            self.move(x, y)

    def _on_learn(self):
        corrected = self._corrected_edit.toPlainText().strip()
        if corrected and corrected != self._original:
            from learning import force_regenerate, learn_correction

            learn_correction(self._original, corrected)
            force_regenerate()
            subprocess.Popen(
                ["afplay", "/System/Library/Sounds/Glass.aiff"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        self.close()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(e)
