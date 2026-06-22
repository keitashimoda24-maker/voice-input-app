"""リサーチ結果を表示するウィンドウ。"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget

import research_manager


class ResearchWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("リサーチ結果")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumSize(520, 400)
        self.setStyleSheet(
            "QWidget { background: rgb(8,10,26); color: white; }"
            "QPushButton { background: rgba(0,229,255,0.12); color: #00e5ff;"
            "  border: 1px solid rgba(0,229,255,0.35); border-radius: 8px;"
            "  padding: 6px 14px; font-size: 12px; }"
            "QPushButton:hover { background: rgba(0,229,255,0.22); }"
            "QScrollBar:vertical { background: rgba(255,255,255,0.05); width: 6px; border-radius: 3px; }"
            "QScrollBar::handle:vertical { background: rgba(0,229,255,0.3); border-radius: 3px; }"
        )
        self._build_ui()
        research_manager.mark_all_read()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setContentsMargins(20, 20, 20, 20)
        main.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("🔍 リサーチ結果")
        f = QFont("Hiragino Sans")
        f.setPointSize(16)
        f.setBold(True)
        title.setFont(f)
        header.addWidget(title)
        header.addStretch()
        clear_btn = QPushButton("全て削除")
        clear_btn.setStyleSheet(
            "QPushButton { color: rgba(255,100,100,0.7); border-color: rgba(255,100,100,0.3);"
            "  background: rgba(255,100,100,0.08); border-radius: 8px; padding: 6px 14px; }"
        )
        clear_btn.clicked.connect(self._clear_all)
        header.addWidget(clear_btn)
        main.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        self._items_layout = QVBoxLayout(container)
        self._items_layout.setContentsMargins(0, 0, 0, 0)
        self._items_layout.setSpacing(12)
        scroll.setWidget(container)
        main.addWidget(scroll)

        results = research_manager.load_results()
        if not results:
            empty = QLabel(
                "リサーチ結果はまだありません。\n録音を開始して「リサーチ ○○」または「調べて ○○」と話しかけてください。"
            )
            f2 = QFont("Hiragino Sans")
            f2.setPointSize(13)
            empty.setFont(f2)
            empty.setStyleSheet("color: rgba(255,255,255,0.4); padding: 40px;")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setWordWrap(True)
            self._items_layout.addWidget(empty)
        else:
            for r in reversed(results):
                self._add_result_card(r)

        self._items_layout.addStretch()

    def _add_result_card(self, r: dict):
        card = QFrame()
        card.setStyleSheet(
            "QFrame { background: rgba(0,229,255,0.04); border: 1px solid rgba(0,229,255,0.15);"
            "  border-radius: 12px; padding: 4px; }"
        )
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 12, 16, 12)
        cl.setSpacing(8)

        q_lbl = QLabel(f"🔍 {r['item']}")
        fq = QFont("Hiragino Sans")
        fq.setPointSize(13)
        fq.setBold(True)
        q_lbl.setFont(fq)
        q_lbl.setStyleSheet("color: #ffd93d;")
        q_lbl.setWordWrap(True)
        cl.addWidget(q_lbl)

        a_lbl = QLabel(r["answer"])
        fa = QFont("Hiragino Sans")
        fa.setPointSize(12)
        a_lbl.setFont(fa)
        a_lbl.setStyleSheet("color: rgba(255,255,255,0.82); line-height: 1.5;")
        a_lbl.setWordWrap(True)
        cl.addWidget(a_lbl)

        ts = r.get("timestamp", "")[:16].replace("T", " ")
        ts_lbl = QLabel(ts)
        fts = QFont("Hiragino Sans")
        fts.setPointSize(10)
        ts_lbl.setFont(fts)
        ts_lbl.setStyleSheet("color: rgba(255,255,255,0.25);")
        cl.addWidget(ts_lbl)

        self._items_layout.addWidget(card)

    def _clear_all(self):
        research_manager.save_results([])
        self.close()
        ResearchWindow().show()
