"""ブレインダンプ（思考の自動構造化）ウィンドウ。"""

import threading
from datetime import datetime

import pyperclip
from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

CATEGORY_COLORS = {
    "今日やること": "#00e5ff",
    "アイデア・事業構想": "#a855f7",
    "懸念事項・問題": "#ff6b6b",
    "要調査・要確認": "#ffd93d",
    "メモ・その他": "#aaaaaa",
}


class _Signals(QObject):
    done = pyqtSignal(dict, str)  # data, timestamp
    error = pyqtSignal(str)


class BraindumpWindow(QWidget):
    def __init__(self, raw_text: str):
        super().__init__()
        self._all_data = []  # 累積結果リスト
        self._signals = _Signals()
        self._signals.done.connect(self._append_result)
        self._signals.error.connect(self._show_error)

        self.setWindowTitle("音声メモ")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumWidth(520)
        self.setMinimumHeight(300)
        self.setStyleSheet(
            "QWidget { background: rgb(8,10,26); color: white; }"
            "QPushButton { background: rgba(0,229,255,0.12); color: #00e5ff;"
            "  border: 1px solid rgba(0,229,255,0.35); border-radius: 8px;"
            "  padding: 8px 18px; font-size: 13px; }"
            "QPushButton:hover { background: rgba(0,229,255,0.22); }"
            "QScrollBar:vertical { background: rgba(255,255,255,0.05); width: 6px; border-radius: 3px; }"
            "QScrollBar::handle:vertical { background: rgba(0,229,255,0.3); border-radius: 3px; }"
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 16)
        outer.setSpacing(10)

        # タイトル行
        title_row = QHBoxLayout()
        title_lbl = QLabel("🧠 音声メモ")
        ft = QFont("Hiragino Sans")
        ft.setPointSize(16)
        ft.setBold(True)
        title_lbl.setFont(ft)
        title_lbl.setStyleSheet("color: white;")
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        copy_btn = QPushButton("📋 全てコピー")
        copy_btn.clicked.connect(self._copy_all)
        title_row.addWidget(copy_btn)
        close_btn = QPushButton("閉じる")
        close_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.5);"
            "  border: 1px solid rgba(255,255,255,0.12); border-radius: 8px; padding: 8px 18px; }"
        )
        close_btn.clicked.connect(self.close)
        title_row.addWidget(close_btn)
        outer.addLayout(title_row)

        # スクロールエリア（メモを積み上げていく）
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._container = QWidget()
        self._items_layout = QVBoxLayout(self._container)
        self._items_layout.setContentsMargins(0, 0, 0, 0)
        self._items_layout.setSpacing(12)
        self._items_layout.addStretch()
        self._scroll.setWidget(self._container)
        outer.addWidget(self._scroll)

        self.resize(540, 480)
        self.show()
        self._start_processing(raw_text)

    def add_entry(self, raw_text: str):
        """既存ウィンドウに新しいメモを追記する。"""
        self.raise_()
        self.activateWindow()
        self._start_processing(raw_text)

    def _start_processing(self, raw_text: str):
        # 「整理中...」カードを先に追加
        ts = datetime.now().strftime("%H:%M")
        loading = self._make_card_frame()
        lbl = QLabel(f"🧠 整理中... ({ts})")
        f = QFont("Hiragino Sans")
        f.setPointSize(13)
        lbl.setFont(f)
        lbl.setStyleSheet("color: #a855f7; padding: 8px;")
        loading.layout().addWidget(lbl)
        # stretch の手前に挿入
        self._items_layout.insertWidget(self._items_layout.count() - 1, loading)
        self._scroll_to_bottom()

        def _run():
            try:
                from ai_actions import structure_braindump

                result = structure_braindump(raw_text)
                ts2 = datetime.now().strftime("%H:%M")
                self._signals.done.emit(result, ts2)
            except Exception as ex:
                from config import safe_error_message

                self._signals.error.emit(safe_error_message(ex))
            finally:
                # loading カードを削除
                from PyQt6.QtCore import QTimer

                QTimer.singleShot(0, loading.deleteLater)

        threading.Thread(target=_run, daemon=True).start()

    def _make_card_frame(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background: rgba(168,85,247,0.07); border: 1px solid rgba(168,85,247,0.25);"
            "  border-radius: 12px; }"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 12, 16, 12)
        cl.setSpacing(6)
        return card

    def _append_result(self, data: dict, ts: str):
        self._all_data.append(data)
        card = self._make_card_frame()

        # タイムスタンプ
        ts_lbl = QLabel(ts)
        fts = QFont("Hiragino Sans")
        fts.setPointSize(10)
        ts_lbl.setFont(fts)
        ts_lbl.setStyleSheet("color: rgba(255,255,255,0.3);")
        card.layout().addWidget(ts_lbl)

        for category, items in data.items():
            if not items:
                continue
            color = CATEGORY_COLORS.get(category, "#aaaaaa")
            cat_lbl = QLabel(f"● {category}")
            f2 = QFont("Hiragino Sans")
            f2.setPointSize(12)
            f2.setBold(True)
            cat_lbl.setFont(f2)
            cat_lbl.setStyleSheet(f"color: {color}; margin-top: 4px;")
            card.layout().addWidget(cat_lbl)
            for item in items:
                il = QLabel(f"  • {item}")
                f3 = QFont("Hiragino Sans")
                f3.setPointSize(11)
                il.setFont(f3)
                il.setStyleSheet("color: rgba(255,255,255,0.85); padding-left: 6px;")
                il.setWordWrap(True)
                card.layout().addWidget(il)

        # stretch の手前に挿入
        self._items_layout.insertWidget(self._items_layout.count() - 1, card)
        self._scroll_to_bottom()
        self.adjustSize()

    def _scroll_to_bottom(self):
        from PyQt6.QtCore import QTimer

        QTimer.singleShot(
            50, lambda: self._scroll.verticalScrollBar().setValue(self._scroll.verticalScrollBar().maximum())
        )

    def _copy_all(self):
        lines = []
        for data in self._all_data:
            for category, items in data.items():
                if items:
                    lines.append(f"【{category}】")
                    for item in items:
                        lines.append(f"・{item}")
            lines.append("")
        pyperclip.copy("\n".join(lines).strip())

    def _show_error(self, msg: str):
        card = self._make_card_frame()
        lbl = QLabel(f"❌ エラー: {msg}")
        lbl.setStyleSheet("color: #ff6b6b; padding: 8px;")
        card.layout().addWidget(lbl)
        self._items_layout.insertWidget(self._items_layout.count() - 1, card)
