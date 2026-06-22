"""Transcript history window with dark theme."""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget

from transcript_history import clear_history, load_history, search_history


class TranscriptHistoryWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("文字起こし履歴")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumSize(480, 400)
        self.resize(520, 560)
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        self.setStyleSheet("""
            QWidget {
                background: rgba(8, 10, 26, 252);
                color: white;
                font-family: "Hiragino Sans";
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                background: rgba(255,255,255,0.05);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: rgba(0,229,255,0.3);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Title
        title = QLabel("文字起こし履歴")
        title.setFont(QFont("Hiragino Sans", 16, QFont.Weight.Bold))
        title.setStyleSheet("color: #00e5ff; padding-bottom: 4px;")
        layout.addWidget(title)

        # Search bar
        search_row = QHBoxLayout()
        search_row.setSpacing(8)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("キーワードで検索...")
        self._search_edit.setFont(QFont("Hiragino Sans", 12))
        self._search_edit.setStyleSheet(
            "QLineEdit { color: white; background: rgba(255,255,255,0.08);"
            " border: 1px solid rgba(0,229,255,0.3); border-radius: 8px;"
            " padding: 6px 10px; }"
            "QLineEdit:focus { border: 1px solid rgba(0,229,255,0.6); }"
        )
        self._search_edit.textChanged.connect(self._on_search)
        search_row.addWidget(self._search_edit)

        clear_btn = QPushButton("全削除")
        clear_btn.setFont(QFont("Hiragino Sans", 11))
        clear_btn.setStyleSheet(
            "QPushButton { background: rgba(255,60,60,0.2); color: rgba(255,100,100,0.9);"
            " border: 1px solid rgba(255,60,60,0.3); border-radius: 6px;"
            " padding: 6px 12px; }"
            "QPushButton:hover { background: rgba(255,60,60,0.35); }"
        )
        clear_btn.clicked.connect(self._on_clear)
        search_row.addWidget(clear_btn)
        layout.addLayout(search_row)

        # Scroll area for entries
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._list_widget = QWidget()
        self._list_widget.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(6)
        self._list_layout.addStretch()

        self._scroll.setWidget(self._list_widget)
        layout.addWidget(self._scroll)

        # Status bar
        self._status_lbl = QLabel("")
        self._status_lbl.setFont(QFont("Hiragino Sans", 10))
        self._status_lbl.setStyleSheet("color: rgba(255,255,255,0.4);")
        layout.addWidget(self._status_lbl)

    def _refresh(self, entries=None):
        """Rebuild the list of transcript entries."""
        # Clear existing items
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if entries is None:
            entries = load_history()

        # Show in reverse chronological order
        for entry in reversed(entries):
            card = self._make_card(entry)
            self._list_layout.insertWidget(self._list_layout.count() - 1, card)

        self._status_lbl.setText(f"{len(entries)} 件の履歴")

    def _make_card(self, entry: dict) -> QWidget:
        """Create a card widget for a transcript entry."""
        card = QWidget()
        card.setStyleSheet(
            "QWidget { background: rgba(255,255,255,0.04);"
            " border: 1px solid rgba(0,229,255,0.12);"
            " border-radius: 10px; }"
        )
        card.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        # Timestamp
        ts_str = ""
        try:
            from datetime import datetime

            dt = datetime.fromisoformat(entry.get("timestamp", ""))
            ts_str = dt.strftime("%Y/%m/%d %H:%M:%S")
        except Exception:
            ts_str = entry.get("timestamp", "")

        ts_lbl = QLabel(ts_str)
        ts_lbl.setFont(QFont("Hiragino Sans", 9))
        ts_lbl.setStyleSheet("color: rgba(0,229,255,0.6); border: none;")
        layout.addWidget(ts_lbl)

        # Text (truncated for display)
        text = entry.get("text", "")
        display_text = text[:200] + "..." if len(text) > 200 else text
        text_lbl = QLabel(display_text)
        text_lbl.setFont(QFont("Hiragino Sans", 11))
        text_lbl.setStyleSheet("color: rgba(255,255,255,0.85); border: none;")
        text_lbl.setWordWrap(True)
        layout.addWidget(text_lbl)

        # Click to copy
        def _copy(t=text):
            try:
                clipboard = QApplication.clipboard()
                if clipboard:
                    clipboard.setText(t)
                # Flash feedback
                text_lbl.setStyleSheet("color: #00e5ff; border: none;")
                QTimer.singleShot(800, lambda: text_lbl.setStyleSheet("color: rgba(255,255,255,0.85); border: none;"))
            except Exception:
                pass

        card.mousePressEvent = lambda e: _copy()
        return card

    def _on_search(self, text: str):
        try:
            if text.strip():
                results = search_history(text)
            else:
                results = load_history()
            self._refresh(results)
        except Exception:
            pass

    def _on_clear(self):
        try:
            clear_history()
            self._refresh([])
        except Exception:
            pass

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setBrush(QBrush(QColor(8, 10, 26, 252)))
        p.setPen(QPen(QColor(0, 229, 255, 40), 1.0))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 12, 12)
        p.end()
