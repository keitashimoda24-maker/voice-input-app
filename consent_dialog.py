"""初回起動時の同意画面。"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from privacy_policy import PRIVACY_POLICY, TERMS_OF_USE

_C_BG = "#0d0f14"
_C_CARD = "rgba(22, 26, 35, 0.95)"
_C_TEXT = "#e2e8f0"
_C_DIM = "rgba(180, 195, 220, 0.6)"
_C_ACCENT = "#6c8cff"
_C_BORDER = "rgba(90, 120, 200, 0.2)"


class ConsentDialog(QDialog):
    """プライバシーポリシー・利用規約への同意を取得するダイアログ。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("音声入力アプリ - ご利用にあたって")
        self.setFixedSize(560, 620)
        self.setStyleSheet(f"""
            QDialog {{
                background: {_C_BG};
            }}
        """)
        self._accepted = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 20)
        layout.setSpacing(12)

        # タイトル
        title = QLabel("音声入力アプリへようこそ")
        title.setFont(QFont(".AppleSystemUIFont", 18, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {_C_TEXT}; background: transparent;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("ご利用前に以下をご確認ください")
        subtitle.setFont(QFont(".AppleSystemUIFont", 12))
        subtitle.setStyleSheet(f"color: {_C_DIM}; background: transparent;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # プライバシーポリシー
        browser = QTextBrowser()
        browser.setPlainText(PRIVACY_POLICY + "\n\n" + "=" * 40 + "\n\n" + TERMS_OF_USE)
        browser.setFont(QFont(".AppleSystemUIFont", 11))
        browser.setStyleSheet(f"""
            QTextBrowser {{
                background: {_C_CARD};
                color: {_C_TEXT};
                border: 1px solid {_C_BORDER};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        layout.addWidget(browser, stretch=1)

        # 同意チェックボックス
        self._agree_check = QCheckBox("プライバシーポリシーおよび利用規約に同意します")
        self._agree_check.setFont(QFont(".AppleSystemUIFont", 12))
        self._agree_check.setStyleSheet(f"""
            QCheckBox {{
                color: {_C_TEXT};
                background: transparent;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {_C_ACCENT};
                border-radius: 4px;
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                background: {_C_ACCENT};
            }}
        """)
        self._agree_check.toggled.connect(self._on_check_changed)
        layout.addWidget(self._agree_check)

        # ボタン行
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self._decline_btn = QPushButton("同意しない")
        self._decline_btn.setFont(QFont(".AppleSystemUIFont", 13))
        self._decline_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {_C_DIM};
                border: 1px solid {_C_BORDER};
                border-radius: 8px;
                padding: 10px 24px;
            }}
            QPushButton:hover {{
                color: {_C_TEXT};
                border-color: {_C_TEXT};
            }}
        """)
        self._decline_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._decline_btn)

        self._accept_btn = QPushButton("同意して開始")
        self._accept_btn.setFont(QFont(".AppleSystemUIFont", 13, QFont.Weight.Bold))
        self._accept_btn.setEnabled(False)
        self._accept_btn.setStyleSheet(f"""
            QPushButton {{
                background: {_C_ACCENT};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 24px;
            }}
            QPushButton:disabled {{
                background: rgba(108, 140, 255, 0.3);
                color: rgba(255, 255, 255, 0.4);
            }}
            QPushButton:hover:!disabled {{
                background: #7d9aff;
            }}
        """)
        self._accept_btn.clicked.connect(self._on_accept)
        btn_row.addWidget(self._accept_btn)

        layout.addLayout(btn_row)

    def _on_check_changed(self, checked):
        self._accept_btn.setEnabled(checked)

    def _on_accept(self):
        self._accepted = True
        self.accept()

    @property
    def user_accepted(self) -> bool:
        return self._accepted
