"""自動置換ルール管理ウィンドウ。"""

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

from replacements import add_replacement, load_replacements, remove_replacement

_MAX_ENTRIES = 800


class ReplacementsWindow(QWidget):
    """非モーダル自動置換ウィンドウ。exec() は使わない。"""

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
        card.setObjectName("replCard")
        card.setStyleSheet("""
            QWidget#replCard {
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
        title = QLabel("自動置換")
        f_title = QFont("Hiragino Sans", 15)
        f_title.setBold(True)
        title.setFont(f_title)
        title.setStyleSheet("color: white;")
        layout.addWidget(title)

        subtitle = QLabel("音声認識後に自動で置換されるルール")
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

        self._from_edit = QLineEdit()
        self._from_edit.setPlaceholderText("変換前")
        self._from_edit.setFont(QFont("Hiragino Sans", 12))
        self._from_edit.setStyleSheet(
            "QLineEdit { color: white; background: rgba(50,50,55,190); "
            "border: 1px solid rgba(0,229,255,0.5); border-radius: 8px; "
            "padding: 6px 10px; }"
        )
        ir_layout.addWidget(self._from_edit)

        arrow_lbl = QLabel("\u2192")
        arrow_lbl.setFont(QFont("Hiragino Sans", 14))
        arrow_lbl.setStyleSheet("color: rgba(0,229,255,0.7);")
        ir_layout.addWidget(arrow_lbl)

        self._to_edit = QLineEdit()
        self._to_edit.setPlaceholderText("変換後")
        self._to_edit.setFont(QFont("Hiragino Sans", 12))
        self._to_edit.setStyleSheet(
            "QLineEdit { color: white; background: rgba(50,50,55,190); "
            "border: 1px solid rgba(0,229,255,0.5); border-radius: 8px; "
            "padding: 6px 10px; }"
        )
        self._to_edit.returnPressed.connect(self._do_add)
        ir_layout.addWidget(self._to_edit)

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
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        rules = load_replacements()
        self._count_label.setText(f"{len(rules)}/{_MAX_ENTRIES} entries")

        for rule in rules:
            row = self._make_row(rule)
            self._list_layout.insertWidget(self._list_layout.count() - 1, row)

    def _make_row(self, rule: dict) -> QWidget:
        """置換ルール行ウィジェットを作成。クリックで編集モードに切り替え。"""
        from_text = rule.get("from", "")
        to_text = rule.get("to", "")

        row = QWidget()
        row.setStyleSheet("QWidget { background: rgba(255,255,255,0.04); border-radius: 8px; }")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(12, 6, 8, 6)
        rl.setSpacing(8)

        # ── 表示モード用ウィジェット ──
        display = QWidget()
        display.setStyleSheet("background: transparent;")
        dl = QHBoxLayout(display)
        dl.setContentsMargins(0, 0, 0, 0)
        dl.setSpacing(8)

        from_lbl = QLabel(from_text)
        from_lbl.setFont(QFont("Hiragino Sans", 12))
        from_lbl.setStyleSheet("color: white; background: transparent;")
        dl.addWidget(from_lbl)

        arrow = QLabel("\u2192")
        arrow.setFont(QFont("Hiragino Sans", 12))
        arrow.setStyleSheet("color: rgba(0,229,255,0.7); background: transparent;")
        dl.addWidget(arrow)

        to_lbl = QLabel(to_text)
        to_lbl.setFont(QFont("Hiragino Sans", 12))
        to_lbl.setStyleSheet("color: rgba(0,229,255,0.9); background: transparent;")
        dl.addWidget(to_lbl, 1)

        edit_btn = QPushButton("編集")
        edit_btn.setStyleSheet(
            "QPushButton { background: rgba(0,229,255,0.12); color: #00e5ff; "
            "border: 1px solid rgba(0,229,255,0.3); border-radius: 6px; "
            "padding: 3px 10px; font-size: 11px; }"
            "QPushButton:hover { background: rgba(0,229,255,0.25); }"
        )
        dl.addWidget(edit_btn)

        rl.addWidget(display, 1)

        # ── 編集モード用ウィジェット（初期非表示） ──
        edit_w = QWidget()
        edit_w.setStyleSheet("background: transparent;")
        edit_w.hide()
        el = QHBoxLayout(edit_w)
        el.setContentsMargins(0, 0, 0, 0)
        el.setSpacing(6)

        edit_style = (
            "QLineEdit { color: white; background: rgba(50,50,55,190); "
            "border: 1px solid rgba(0,229,255,0.5); border-radius: 6px; "
            "padding: 4px 8px; }"
        )
        from_edit = QLineEdit(from_text)
        from_edit.setFont(QFont("Hiragino Sans", 12))
        from_edit.setStyleSheet(edit_style)
        el.addWidget(from_edit)

        arrow2 = QLabel("\u2192")
        arrow2.setFont(QFont("Hiragino Sans", 12))
        arrow2.setStyleSheet("color: rgba(0,229,255,0.7); background: transparent;")
        el.addWidget(arrow2)

        to_edit = QLineEdit(to_text)
        to_edit.setFont(QFont("Hiragino Sans", 12))
        to_edit.setStyleSheet(edit_style)
        el.addWidget(to_edit, 1)

        save_btn = QPushButton("保存")
        save_btn.setStyleSheet(
            "QPushButton { background-color: #007AFF; color: white; "
            "border-radius: 6px; padding: 4px 10px; font-size: 11px; }"
            "QPushButton:hover { background-color: #0056CC; }"
        )
        el.addWidget(save_btn)

        cancel_btn = QPushButton("戻す")
        cancel_btn.setStyleSheet(
            "QPushButton { background: #3a3a3c; color: white; "
            "border-radius: 6px; padding: 4px 10px; font-size: 11px; }"
            "QPushButton:hover { background: #4a4a4c; }"
        )
        el.addWidget(cancel_btn)

        rl.addWidget(edit_w, 1)

        # ── 削除ボタン ──
        del_btn = QPushButton("x")
        del_btn.setFixedSize(28, 28)
        del_btn.setStyleSheet(
            "QPushButton { background: rgba(255,69,58,0.15); color: #ff453a; "
            "border: 1px solid rgba(255,69,58,0.3); border-radius: 14px; "
            "font-size: 13px; font-weight: bold; }"
            "QPushButton:hover { background: rgba(255,69,58,0.3); }"
        )
        del_btn.clicked.connect(lambda _, ft=from_text: self._do_remove(ft))
        rl.addWidget(del_btn)

        # ── クリックで編集モード切替 ──
        def enter_edit(_=None):
            display.hide()
            edit_w.show()
            from_edit.setFocus()

        def exit_edit(_=None):
            edit_w.hide()
            display.show()

        def do_save(_=None):
            new_from = from_edit.text().strip()
            new_to = to_edit.text()
            if not new_from:
                return
            # 元のルールを削除して新しいルールを追加
            remove_replacement(from_text)
            add_replacement(new_from, new_to)
            self._reload_list()

        edit_btn.clicked.connect(enter_edit)
        save_btn.clicked.connect(do_save)
        to_edit.returnPressed.connect(do_save)
        cancel_btn.clicked.connect(exit_edit)

        return row

    def _show_add_input(self):
        self._input_row.show()
        self._from_edit.clear()
        self._to_edit.clear()
        self._from_edit.setFocus()

    def _hide_add_input(self):
        self._input_row.hide()

    def _do_add(self):
        from_text = self._from_edit.text().strip()
        to_text = self._to_edit.text()  # 空文字も許可（削除用途）
        if not from_text:
            return
        add_replacement(from_text, to_text)
        self._from_edit.clear()
        self._to_edit.clear()
        self._reload_list()

    def _do_remove(self, from_text: str):
        remove_replacement(from_text)
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
