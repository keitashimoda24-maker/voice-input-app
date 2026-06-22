"""辞書管理ウィンドウ — カスタム単語の追加・削除UI。"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from dictionary import add_word, load_dictionary, remove_word

_MAX_ENTRIES = 800


class DictionaryWindow(QWidget):
    """非モーダル辞書ウィンドウ。exec() は使わない。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(420, 520)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # カードコンテナ
        card = QWidget()
        card.setObjectName("dictCard")
        card.setStyleSheet("""
            QWidget#dictCard {
                background-color: rgba(28, 28, 30, 245);
                border-radius: 18px;
                border: 1px solid rgba(0,229,255,0.25);
            }
        """)
        outer.addWidget(card)

        layout = QVBoxLayout(card)
        layout.setSpacing(8)
        layout.setContentsMargins(18, 14, 18, 14)

        # ── ヘッダー ──
        title = QLabel("辞書")
        f_title = QFont("Hiragino Sans", 15)
        f_title.setBold(True)
        title.setFont(f_title)
        title.setStyleSheet("color: white;")
        layout.addWidget(title)

        subtitle = QLabel("カスタム単語でAI精度を向上")
        subtitle.setFont(QFont("Hiragino Sans", 11))
        subtitle.setStyleSheet("color: rgba(255,255,255,0.5);")
        layout.addWidget(subtitle)

        # ── カウンター + 追加ボタン行 ──
        top_row = QHBoxLayout()
        self._count_label = QLabel()
        self._count_label.setFont(QFont("Hiragino Sans", 11))
        self._count_label.setStyleSheet("color: rgba(0,229,255,0.8);")
        top_row.addWidget(self._count_label)
        top_row.addStretch()

        add_btn = QPushButton("+ 追加")
        add_btn.setStyleSheet(
            "QPushButton { background-color: rgba(0,229,255,0.15); color: #00e5ff; "
            "border: 1px solid rgba(0,229,255,0.4); border-radius: 8px; "
            "padding: 5px 14px; font-size: 12px; font-weight: bold; }"
            "QPushButton:hover { background-color: rgba(0,229,255,0.25); }"
        )
        add_btn.clicked.connect(self._show_add_input)
        top_row.addWidget(add_btn)
        layout.addLayout(top_row)

        # ── 追加入力エリア（通常は非表示） ──
        self._input_row = QWidget()
        self._input_row.hide()
        ir_layout = QHBoxLayout(self._input_row)
        ir_layout.setContentsMargins(0, 0, 0, 0)
        ir_layout.setSpacing(6)

        self._input_edit = QLineEdit()
        self._input_edit.setPlaceholderText("単語を入力...")
        self._input_edit.setFont(QFont("Hiragino Sans", 12))
        self._input_edit.setStyleSheet(
            "QLineEdit { color: white; background: rgba(50,50,55,190); "
            "border: 1px solid rgba(0,229,255,0.5); border-radius: 8px; "
            "padding: 6px 10px; }"
        )
        self._input_edit.returnPressed.connect(self._do_add)
        ir_layout.addWidget(self._input_edit)

        ok_btn = QPushButton("OK")
        ok_btn.setStyleSheet(
            "QPushButton { background-color: #007AFF; color: white; "
            "border-radius: 8px; padding: 6px 12px; font-size: 12px; }"
            "QPushButton:hover { background-color: #0056CC; }"
        )
        ok_btn.clicked.connect(self._do_add)
        ir_layout.addWidget(ok_btn)

        cancel_input_btn = QPushButton("x")
        cancel_input_btn.setFixedSize(28, 28)
        cancel_input_btn.setStyleSheet(
            "QPushButton { background: #3a3a3c; color: white; border-radius: 14px; font-size: 12px; }"
        )
        cancel_input_btn.clicked.connect(self._hide_add_input)
        ir_layout.addWidget(cancel_input_btn)

        layout.addWidget(self._input_row)

        # ── セパレーター ──
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(255,255,255,0.1);")
        layout.addWidget(sep)

        # ── スクロールエリア ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { background: rgba(255,255,255,0.05); width: 6px; border-radius: 3px; }"
            "QScrollBar::handle:vertical { background: rgba(0,229,255,0.3); border-radius: 3px; min-height: 20px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )
        self._list_container = QWidget()
        self._list_container.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(2)
        self._list_layout.addStretch()
        scroll.setWidget(self._list_container)
        layout.addWidget(scroll, 1)

        # ── 閉じるボタン ──
        close_btn = QPushButton("閉じる")
        close_btn.setStyleSheet(
            "QPushButton { background: #3a3a3c; color: white; "
            "border-radius: 8px; padding: 7px 14px; font-size: 12px; }"
            "QPushButton:hover { background: #4a4a4c; }"
        )
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # Escキーで閉じる
        esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        esc.activated.connect(self.close)

        self._reload_list()

    def _reload_list(self):
        """リスト表示を更新。"""
        # 既存行を削除（stretchは残す）
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        words = load_dictionary()
        self._count_label.setText(f"{len(words)}/{_MAX_ENTRIES} entries")

        for word in words:
            row = self._make_row(word)
            self._list_layout.insertWidget(self._list_layout.count() - 1, row)

    def _make_row(self, word: str) -> QWidget:
        """単語行ウィジェットを作成。"""
        row = QWidget()
        row.setStyleSheet("QWidget { background: rgba(255,255,255,0.04); border-radius: 8px; }")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(12, 6, 8, 6)
        rl.setSpacing(8)

        lbl = QLabel(word)
        lbl.setFont(QFont("Hiragino Sans", 12))
        lbl.setStyleSheet("color: white; background: transparent;")
        rl.addWidget(lbl, 1)

        del_btn = QPushButton("削除")
        del_btn.setStyleSheet(
            "QPushButton { background: rgba(255,69,58,0.15); color: #ff453a; "
            "border: 1px solid rgba(255,69,58,0.3); border-radius: 6px; "
            "padding: 3px 10px; font-size: 11px; }"
            "QPushButton:hover { background: rgba(255,69,58,0.3); }"
        )
        del_btn.clicked.connect(lambda _, w=word: self._do_remove(w))
        rl.addWidget(del_btn)

        return row

    def _show_add_input(self):
        self._input_row.show()
        self._input_edit.clear()
        self._input_edit.setFocus()

    def _hide_add_input(self):
        self._input_row.hide()

    def _do_add(self):
        word = self._input_edit.text().strip()
        if not word:
            return
        add_word(word)
        self._input_edit.clear()
        self._reload_list()

    def _do_remove(self, word: str):
        remove_word(word)
        self._reload_list()

    def paintEvent(self, e):
        pass  # 透過背景のためデフォルトを無効化

    def showEvent(self, event):
        super().showEvent(event)
        # 画面中央に配置
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.center().x() - self.width() // 2
            y = geo.center().y() - self.height() // 2
            self.move(x, y)
        self._reload_list()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(e)
