"""Settings dialog for configuring the app."""

import json
import os
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QKeySequence
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config import load_config, load_vocabulary, save_config, save_vocabulary
from learning import force_regenerate, get_vocabulary_stats

# ── Qt modifier → Quartz flags / 表示名 マッピング ───────────────────────────
_MOD_MAP = [
    (Qt.KeyboardModifier.ControlModifier, 1048576, "Cmd"),
    (Qt.KeyboardModifier.AltModifier, 524288, "Option"),
    (Qt.KeyboardModifier.MetaModifier, 262144, "Ctrl"),
    (Qt.KeyboardModifier.ShiftModifier, 131072, "Shift"),
]

_QT_TO_VK = {
    Qt.Key.Key_A: 0,
    Qt.Key.Key_S: 1,
    Qt.Key.Key_D: 2,
    Qt.Key.Key_F: 3,
    Qt.Key.Key_H: 4,
    Qt.Key.Key_G: 5,
    Qt.Key.Key_Z: 6,
    Qt.Key.Key_X: 7,
    Qt.Key.Key_C: 8,
    Qt.Key.Key_V: 9,
    Qt.Key.Key_B: 11,
    Qt.Key.Key_Q: 12,
    Qt.Key.Key_W: 13,
    Qt.Key.Key_E: 14,
    Qt.Key.Key_R: 15,
    Qt.Key.Key_Y: 16,
    Qt.Key.Key_T: 17,
    Qt.Key.Key_1: 18,
    Qt.Key.Key_2: 19,
    Qt.Key.Key_3: 20,
    Qt.Key.Key_4: 21,
    Qt.Key.Key_6: 22,
    Qt.Key.Key_5: 23,
    Qt.Key.Key_9: 25,
    Qt.Key.Key_7: 26,
    Qt.Key.Key_8: 28,
    Qt.Key.Key_0: 29,
    Qt.Key.Key_O: 31,
    Qt.Key.Key_U: 32,
    Qt.Key.Key_I: 34,
    Qt.Key.Key_P: 35,
    Qt.Key.Key_L: 37,
    Qt.Key.Key_J: 38,
    Qt.Key.Key_K: 40,
    Qt.Key.Key_N: 45,
    Qt.Key.Key_M: 46,
    Qt.Key.Key_Space: 49,
    Qt.Key.Key_Return: 36,
    Qt.Key.Key_Tab: 48,
    Qt.Key.Key_F1: 122,
    Qt.Key.Key_F2: 120,
    Qt.Key.Key_F3: 99,
    Qt.Key.Key_F4: 118,
    Qt.Key.Key_F5: 96,
    Qt.Key.Key_F6: 97,
    Qt.Key.Key_F7: 98,
    Qt.Key.Key_F8: 100,
    Qt.Key.Key_F9: 101,
    Qt.Key.Key_F10: 109,
    Qt.Key.Key_F11: 103,
    Qt.Key.Key_F12: 111,
}

_QT_KEY_NAME = {
    Qt.Key.Key_A: "A",
    Qt.Key.Key_B: "B",
    Qt.Key.Key_C: "C",
    Qt.Key.Key_D: "D",
    Qt.Key.Key_E: "E",
    Qt.Key.Key_F: "F",
    Qt.Key.Key_G: "G",
    Qt.Key.Key_H: "H",
    Qt.Key.Key_I: "I",
    Qt.Key.Key_J: "J",
    Qt.Key.Key_K: "K",
    Qt.Key.Key_L: "L",
    Qt.Key.Key_M: "M",
    Qt.Key.Key_N: "N",
    Qt.Key.Key_O: "O",
    Qt.Key.Key_P: "P",
    Qt.Key.Key_Q: "Q",
    Qt.Key.Key_R: "R",
    Qt.Key.Key_S: "S",
    Qt.Key.Key_T: "T",
    Qt.Key.Key_U: "U",
    Qt.Key.Key_V: "V",
    Qt.Key.Key_W: "W",
    Qt.Key.Key_X: "X",
    Qt.Key.Key_Y: "Y",
    Qt.Key.Key_Z: "Z",
    Qt.Key.Key_0: "0",
    Qt.Key.Key_1: "1",
    Qt.Key.Key_2: "2",
    Qt.Key.Key_3: "3",
    Qt.Key.Key_4: "4",
    Qt.Key.Key_5: "5",
    Qt.Key.Key_6: "6",
    Qt.Key.Key_7: "7",
    Qt.Key.Key_8: "8",
    Qt.Key.Key_9: "9",
    Qt.Key.Key_Space: "Space",
    Qt.Key.Key_Return: "Return",
    Qt.Key.Key_Tab: "Tab",
    Qt.Key.Key_F1: "F1",
    Qt.Key.Key_F2: "F2",
    Qt.Key.Key_F3: "F3",
    Qt.Key.Key_F4: "F4",
    Qt.Key.Key_F5: "F5",
    Qt.Key.Key_F6: "F6",
    Qt.Key.Key_F7: "F7",
    Qt.Key.Key_F8: "F8",
    Qt.Key.Key_F9: "F9",
    Qt.Key.Key_F10: "F10",
    Qt.Key.Key_F11: "F11",
    Qt.Key.Key_F12: "F12",
}

_INSTRUCTIONS_DIR = os.path.expanduser("~/.voice_input_app")
_INSTRUCTIONS_PATH = os.path.join(_INSTRUCTIONS_DIR, "custom_instructions.txt")


def _load_custom_instructions() -> str:
    try:
        with open(_INSTRUCTIONS_PATH, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def _save_custom_instructions(text: str):
    os.makedirs(_INSTRUCTIONS_DIR, exist_ok=True)
    with open(_INSTRUCTIONS_PATH, "w", encoding="utf-8") as f:
        f.write(text.strip())


# ══════════════════════════════════════════════════════════════════════════════
#  カラーパレット
# ══════════════════════════════════════════════════════════════════════════════
_C = {
    "bg": "#0d0f14",
    "bg_card": "rgba(22, 26, 35, 0.92)",
    "bg_input": "rgba(30, 35, 48, 0.95)",
    "bg_row": "rgba(35, 42, 58, 0.7)",
    "bg_row_hover": "rgba(45, 55, 75, 0.85)",
    "border": "rgba(90, 120, 200, 0.2)",
    "border_focus": "rgba(120, 160, 255, 0.5)",
    "accent": "#6c8cff",  # 青紫アクセント
    "accent_glow": "rgba(108,140,255,0.3)",
    "accent2": "#a78bfa",  # ラベンダー
    "accent3": "#38bdf8",  # スカイブルー
    "text": "#e2e8f0",
    "text_dim": "rgba(180, 195, 220, 0.6)",
    "text_bright": "#f8fafc",
    "danger": "#f87171",
    "danger_bg": "rgba(248, 113, 113, 0.12)",
    "danger_border": "rgba(248, 113, 113, 0.3)",
    "success": "#34d399",
    "save_bg": "linear-gradient(135deg, #6c8cff, #a78bfa)",
}

# ダイアログ全体のダークテーマスタイル
_DIALOG_STYLE = f"""
    QDialog {{
        background-color: {_C["bg"]};
        color: {_C["text"]};
    }}
    QLabel {{
        color: {_C["text"]};
        background: transparent;
    }}
    QGroupBox {{
        color: {_C["accent2"]};
        border: 1px solid {_C["border"]};
        border-radius: 10px;
        margin-top: 14px;
        padding-top: 18px;
        font-weight: bold;
        background: {_C["bg_card"]};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 8px;
        color: {_C["accent2"]};
    }}
    QLineEdit {{
        color: {_C["text"]};
        background: {_C["bg_input"]};
        border: 1px solid {_C["border"]};
        border-radius: 8px;
        padding: 7px 12px;
        font-size: 13px;
        selection-background-color: {_C["accent"]};
    }}
    QLineEdit:focus {{
        border: 1px solid {_C["border_focus"]};
    }}
    QLineEdit::placeholder {{
        color: {_C["text_dim"]};
    }}
    QComboBox {{
        color: {_C["text"]};
        background: {_C["bg_input"]};
        border: 1px solid {_C["border"]};
        border-radius: 8px;
        padding: 6px 12px;
        font-size: 13px;
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background: #1a1f2e;
        color: {_C["text"]};
        border: 1px solid {_C["border"]};
        selection-background-color: {_C["accent"]};
    }}
    QRadioButton {{
        color: {_C["text"]};
        spacing: 8px;
        background: transparent;
    }}
    QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border: 2px solid {_C["border"]};
        border-radius: 9px;
        background: {_C["bg_input"]};
    }}
    QRadioButton::indicator:checked {{
        border: 2px solid {_C["accent"]};
        background: {_C["accent"]};
    }}
    QCheckBox {{
        color: {_C["text"]};
        spacing: 8px;
        background: transparent;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 2px solid {_C["border"]};
        border-radius: 4px;
        background: {_C["bg_input"]};
    }}
    QCheckBox::indicator:checked {{
        border: 2px solid {_C["accent"]};
        background: {_C["accent"]};
    }}
    QScrollArea {{
        background: transparent;
        border: none;
    }}
    QScrollBar:vertical {{
        background: rgba(255,255,255,0.03);
        width: 6px;
        border-radius: 3px;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(108,140,255,0.3);
        border-radius: 3px;
        min-height: 24px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QTextEdit {{
        color: {_C["text"]};
        background: {_C["bg_input"]};
        border: 1px solid {_C["border"]};
        border-radius: 10px;
        padding: 10px;
        font-size: 13px;
        selection-background-color: {_C["accent"]};
    }}
    QTextEdit:focus {{
        border: 1px solid {_C["border_focus"]};
    }}
"""

# タブバーのスタイル
_TAB_STYLE = f"""
    QTabWidget::pane {{
        border: 1px solid {_C["border"]};
        border-radius: 12px;
        background: {_C["bg_card"]};
        top: -1px;
    }}
    QTabBar::tab {{
        color: {_C["text_dim"]};
        background: transparent;
        padding: 10px 22px;
        font-size: 13px;
        border: none;
        border-bottom: 2px solid transparent;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        color: {_C["accent"]};
        font-weight: bold;
        border-bottom: 2px solid {_C["accent"]};
    }}
    QTabBar::tab:hover:!selected {{
        color: {_C["text"]};
        border-bottom: 2px solid rgba(108,140,255,0.3);
    }}
"""


class _HotkeyCapture(QWidget):
    def __init__(self, current_display: str, parent=None):
        super().__init__(parent)
        self._listening = False
        self._keycode = None
        self._quartz_flags = None
        self._display = current_display
        self.setFixedHeight(42)
        self.setMinimumWidth(200)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 4, 14, 4)
        layout.setSpacing(10)

        self._key_lbl = QLabel(current_display)
        self._key_lbl.setStyleSheet(f"color: {_C['accent']}; font-size: 14px; font-weight: bold;")
        layout.addWidget(self._key_lbl)
        layout.addStretch()

        self._hint_lbl = QLabel("クリックして変更")
        self._hint_lbl.setStyleSheet(f"color: {_C['text_dim']}; font-size: 11px;")
        layout.addWidget(self._hint_lbl)

        self.setStyleSheet(
            f"QWidget {{ background: {_C['bg_input']}; border: 1px solid {_C['border']};border-radius: 10px; }}"
        )
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def hotkey_data(self):
        if self._keycode is None:
            return None
        return {
            "keycode": self._keycode,
            "quartz_flags": self._quartz_flags,
            "display": self._display,
        }

    def mousePressEvent(self, e):
        self._start_listen()

    def keyPressEvent(self, e):
        if not self._listening:
            return
        key = e.key()
        mods = e.modifiers()
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Alt, Qt.Key.Key_Meta, Qt.Key.Key_Shift, Qt.Key.Key_CapsLock):
            return
        if key == Qt.Key.Key_Escape:
            self._cancel_listen()
            return
        vk = _QT_TO_VK.get(key)
        if vk is None:
            self._hint_lbl.setText("このキーは未対応です")
            return
        quartz_flags = 0
        parts = []
        for qt_mod, qz_flag, name in _MOD_MAP:
            if mods & qt_mod:
                quartz_flags |= qz_flag
                parts.append(name)
        parts.append(_QT_KEY_NAME.get(key) or QKeySequence(key).toString() or "?")
        display = "+".join(parts)
        self._keycode = vk
        self._quartz_flags = quartz_flags
        self._display = display
        self._key_lbl.setText(display)
        self._stop_listen()

    def focusOutEvent(self, e):
        if self._listening:
            self._cancel_listen()
        super().focusOutEvent(e)

    def _start_listen(self):
        self._listening = True
        self._key_lbl.setText("キーを押してください...")
        self._key_lbl.setStyleSheet("color: #fbbf24; font-size: 13px; font-weight: bold;")
        self._hint_lbl.setText("Escでキャンセル")
        self.setStyleSheet(
            "QWidget { background: rgba(251,191,36,0.08); border: 1.5px solid rgba(251,191,36,0.5);"
            "border-radius: 10px; }"
        )
        self.setFocus()

    def _stop_listen(self):
        self._listening = False
        self._key_lbl.setStyleSheet(f"color: {_C['accent']}; font-size: 14px; font-weight: bold;")
        self._hint_lbl.setText("クリックして変更")
        self.setStyleSheet(
            f"QWidget {{ background: {_C['bg_input']}; border: 1px solid {_C['border']};border-radius: 10px; }}"
        )

    def _cancel_listen(self):
        self._listening = False
        self._key_lbl.setText(self._display)
        self._stop_listen()


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._config = load_config()
        self._setup_ui()

    # ── Activation Policy 切り替え ──
    def showEvent(self, event):
        super().showEvent(event)
        try:
            from AppKit import NSApp, NSApplicationActivationPolicyAccessory
            NSApp.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
            NSApp.activateIgnoringOtherApps_(True)
        except Exception:
            pass
        self.activateWindow()
        self.raise_()

    def closeEvent(self, event):
        try:
            from AppKit import NSApp, NSApplicationActivationPolicyProhibited
            NSApp.setActivationPolicy_(NSApplicationActivationPolicyProhibited)
        except Exception:
            pass
        super().closeEvent(event)

    def _setup_ui(self):
        self.setWindowTitle("設定 - 音声入力")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumWidth(600)
        self.setMinimumHeight(640)
        self.setStyleSheet(_DIALOG_STYLE)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # ── ヘッダー ──
        header = QHBoxLayout()
        title = QLabel("SETTINGS")
        title.setFont(QFont("SF Pro Display", 20, QFont.Weight.Bold))
        title.setStyleSheet(f"""
            color: {_C["text_bright"]};
            letter-spacing: 4px;
        """)
        header.addWidget(title)
        header.addStretch()
        # バージョンバッジ
        ver_badge = QLabel("v2.0")
        ver_badge.setStyleSheet(f"""
            color: {_C["accent"]};
            background: {_C["accent_glow"]};
            border: 1px solid {_C["accent"]};
            border-radius: 10px;
            padding: 3px 10px;
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 1px;
        """)
        header.addWidget(ver_badge)
        main_layout.addLayout(header)

        # 薄いライン
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(
            f"background: qlineargradient(x1:0, x2:1, stop:0 transparent, stop:0.5 {_C['accent']}, stop:1 transparent);"
        )
        main_layout.addWidget(line)

        # ── タブウィジェット ──
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(_TAB_STYLE)
        main_layout.addWidget(self._tabs, 1)

        self._tabs.addTab(self._build_general_tab(), "基本設定")
        self._tabs.addTab(self._build_shortcuts_tab(), "ショートカット")
        self._tabs.addTab(self._build_dictionary_tab(), "辞書")
        self._tabs.addTab(self._build_instructions_tab(), "カスタム指示")
        self._tabs.addTab(self._build_replacements_tab(), "自動置換")
        self._tabs.addTab(self._build_data_tab(), "データ管理")

        # ── フッターボタン ──
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        cancel_btn = QPushButton("キャンセル")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                color: {_C["text_dim"]};
                background: transparent;
                border: 1px solid {_C["border"]};
                border-radius: 10px;
                padding: 10px 24px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                color: {_C["text"]};
                border-color: {_C["text_dim"]};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("保存")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                color: white;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {_C["accent"]}, stop:1 {_C["accent2"]});
                border: none;
                border-radius: 10px;
                padding: 10px 32px;
                font-size: 13px;
                font-weight: bold;
                letter-spacing: 1px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #7d9bff, stop:1 #b89cff);
            }}
        """)
        save_btn.clicked.connect(self._save)
        # グロー効果
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(20)
        glow.setColor(QColor(108, 140, 255, 80))
        glow.setOffset(0, 2)
        save_btn.setGraphicsEffect(glow)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        main_layout.addLayout(btn_layout)

    # ══════════════════════════════════════════════════════════════════════════
    #  タブ1: 基本設定
    # ══════════════════════════════════════════════════════════════════════════
    def _build_general_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # ── API / 言語 ──
        form = QFormLayout()
        form.setSpacing(12)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self._api_key_edit = QLineEdit()
        self._api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        # Keychainから読み込み（設定されていれば伏せ字表示）
        from config import get_api_key

        existing_key = get_api_key()
        if existing_key:
            self._api_key_edit.setPlaceholderText("Keychainに保存済み（変更する場合のみ入力）")
        else:
            self._api_key_edit.setPlaceholderText("sk-ant-...")
        api_label = QLabel("Anthropic APIキー")
        api_label.setStyleSheet(f"color: {_C['text_dim']}; font-size: 12px;")
        form.addRow(api_label, self._api_key_edit)

        self._lang_combo = QComboBox()
        self._lang_combo.addItems(["ja (日本語)", "en (English)", "zh (中文)", "自動検出"])
        lang = self._config.get("language", "ja")
        self._lang_combo.setCurrentIndex({"ja": 0, "en": 1, "zh": 2, "auto": 3}.get(lang, 0))
        lang_label = QLabel("認識言語")
        lang_label.setStyleSheet(f"color: {_C['text_dim']}; font-size: 12px;")
        form.addRow(lang_label, self._lang_combo)

        layout.addLayout(form)

        # ── 起動音ジャンル ──
        sound_group = QGroupBox("起動音ジャンル")
        sound_layout = QVBoxLayout(sound_group)
        sound_layout.setSpacing(4)
        _GENRES = [
            ("coin", "Coin     -- コイン弾き（明るい金属音）"),
            ("ping", "Ping     -- ソナーピン（純音・余韻あり）"),
            ("strum", "Strum    -- ギターCコードストラム"),
            ("knock", "Knock    -- コツンという打撃音"),
            ("flutter", "Flutter  -- トレモロ振動音"),
            ("glass", "Glass    -- クリスタルグラスを叩く"),
            ("synth", "Synth    -- 温かいシンセパッド"),
            ("wood", "Wood     -- 木琴単音"),
        ]
        self._genre_keys = [k for k, _ in _GENRES]
        self._sound_radio_group = QButtonGroup(self)
        current_genre = self._config.get("sound_genre", "crystal")
        for i, (key, label) in enumerate(_GENRES):
            row_widget = QWidget()
            row_widget.setStyleSheet("background: transparent;")
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)
            rb = QRadioButton(label)
            if key == current_genre:
                rb.setChecked(True)
            self._sound_radio_group.addButton(rb, i)
            preview_btn = QPushButton("試聴")
            preview_btn.setFixedSize(64, 26)
            preview_btn.setStyleSheet(f"""
                QPushButton {{
                    font-size: 11px; padding: 0 6px;
                    background: {_C["bg_input"]};
                    border: 1px solid {_C["border"]};
                    border-radius: 6px;
                    color: {_C["accent3"]};
                }}
                QPushButton:hover {{
                    background: rgba(56, 189, 248, 0.12);
                    border-color: {_C["accent3"]};
                }}
            """)
            preview_btn.clicked.connect(lambda checked, k=key: self._preview_sound(k))
            row_layout.addWidget(rb)
            row_layout.addStretch()
            row_layout.addWidget(preview_btn)
            sound_layout.addWidget(row_widget)
        layout.addWidget(sound_group)

        # AI機能は常にオン（UIには表示しない）

        # ── チーム語彙 ──
        team_group = QGroupBox("チーム語彙")
        team_layout = QVBoxLayout(team_group)
        team_layout.setSpacing(6)
        path_row = QHBoxLayout()
        self._team_vocab_edit = QLineEdit()
        self._team_vocab_edit.setText(self._config.get("team_vocab_path", ""))
        self._team_vocab_edit.setPlaceholderText("チーム語彙JSONファイルのパス（任意）")
        path_row.addWidget(self._team_vocab_edit)
        browse_btn = QPushButton("参照...")
        browse_btn.setFixedWidth(70)
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                color: {_C["text"]};
                background: {_C["bg_input"]};
                border: 1px solid {_C["border"]};
                border-radius: 8px;
                padding: 6px;
                font-size: 12px;
            }}
            QPushButton:hover {{ border-color: {_C["accent"]}; }}
        """)
        browse_btn.clicked.connect(self._browse_team_vocab)
        path_row.addWidget(browse_btn)
        team_layout.addLayout(path_row)
        vocab_btn_row = QHBoxLayout()
        for label, slot in [("エクスポート", self._export_vocab), ("インポート", self._import_vocab)]:
            btn = QPushButton(label)
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: {_C["accent3"]};
                    background: transparent;
                    border: 1px solid rgba(56,189,248,0.3);
                    border-radius: 8px;
                    padding: 6px 16px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background: rgba(56,189,248,0.08);
                    border-color: {_C["accent3"]};
                }}
            """)
            btn.clicked.connect(slot)
            vocab_btn_row.addWidget(btn)
        vocab_btn_row.addStretch()
        team_layout.addLayout(vocab_btn_row)
        layout.addWidget(team_group)

        # ── アプリ別カスタムルール ──
        rules_group = QGroupBox("アプリ別カスタムルール")
        rules_layout = QVBoxLayout(rules_group)
        rules_layout.setSpacing(6)
        rules_desc = QLabel("アプリ名（部分一致）と指示を設定すると、そのアプリ使用時に自動適用されます。")
        rules_desc.setStyleSheet(f"color: {_C['text_dim']}; font-size: 11px;")
        rules_desc.setWordWrap(True)
        rules_layout.addWidget(rules_desc)
        self._rules_rows: list[tuple[QLineEdit, QLineEdit]] = []
        self._rules_container = QWidget()
        self._rules_container.setStyleSheet("background: transparent;")
        self._rules_container_layout = QVBoxLayout(self._rules_container)
        self._rules_container_layout.setContentsMargins(0, 0, 0, 0)
        self._rules_container_layout.setSpacing(4)
        rules_layout.addWidget(self._rules_container)
        existing_rules: dict = self._config.get("app_rules", {})
        for app_n, rule_t in existing_rules.items():
            self._add_rule_row(app_n, rule_t)
        if not existing_rules:
            self._add_rule_row("", "")
        add_rule_btn = QPushButton("+ ルールを追加")
        add_rule_btn.setFixedWidth(130)
        add_rule_btn.setStyleSheet(f"""
            QPushButton {{
                color: {_C["accent"]};
                background: transparent;
                border: 1px dashed {_C["border"]};
                border-radius: 8px;
                padding: 6px;
                font-size: 12px;
            }}
            QPushButton:hover {{ border-color: {_C["accent"]}; background: {_C["accent_glow"]}; }}
        """)
        add_rule_btn.clicked.connect(lambda: self._add_rule_row("", ""))
        rules_layout.addWidget(add_rule_btn)
        layout.addWidget(rules_group)

        # ── AI学習セクション ──
        ai_section = QGroupBox("AI学習ステータス")
        ai_sec_layout = QVBoxLayout(ai_section)
        ai_sec_layout.setSpacing(8)
        stats = get_vocabulary_stats()
        self._stats_lbl = QLabel(self._stats_text(stats))
        self._stats_lbl.setStyleSheet(f"color: {_C['text_dim']}; font-size: 11px;")
        self._stats_lbl.setWordWrap(True)
        ai_sec_layout.addWidget(self._stats_lbl)
        prompt = stats.get("whisper_prompt", "")
        prompt_box = QLabel(f"Whisperプロンプト:\n{prompt if prompt else '（まだ生成されていません）'}")
        prompt_box.setStyleSheet(f"""
            background: {_C["bg_input"]};
            color: {_C["text_dim"]};
            border-radius: 8px;
            padding: 10px;
            font-size: 11px;
            border: 1px solid {_C["border"]};
        """)
        prompt_box.setWordWrap(True)
        self._prompt_box = prompt_box
        ai_sec_layout.addWidget(prompt_box)
        # 学習は自動実行されるためボタンは不要
        layout.addWidget(ai_section)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ══════════════════════════════════════════════════════════════════════════
    #  タブ2: ショートカット & ウェイクワード
    # ══════════════════════════════════════════════════════════════════════════
    def _build_shortcuts_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(content)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        # ヘッダー
        t = QLabel("SHORTCUTS & WAKE WORDS")
        t.setFont(QFont("SF Pro Display", 16, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {_C['text_bright']}; letter-spacing: 3px;")
        layout.addWidget(t)
        sub = QLabel("キーボードショートカットとウェイクアップワードを設定")
        sub.setStyleSheet(f"color: {_C['text_dim']}; font-size: 12px;")
        layout.addWidget(sub)

        # ── 録音開始/停止 ──
        rec_group = QGroupBox("録音開始 / 停止")
        rec_layout = QVBoxLayout(rec_group)
        rec_layout.setSpacing(8)
        rec_desc = QLabel("録音のオン/オフを切り替えるショートカット")
        rec_desc.setStyleSheet(f"color: {_C['text_dim']}; font-size: 11px;")
        rec_layout.addWidget(rec_desc)
        current_display = self._config.get("hotkey", {}).get("display", "Cmd+Option+R")
        self._hotkey_btn = _HotkeyCapture(current_display)
        rec_layout.addWidget(self._hotkey_btn)
        layout.addWidget(rec_group)

        # ── 前回の文字起こしを貼り付け ──
        paste_group = QGroupBox("前回の文字起こしを貼り付け")
        paste_layout = QVBoxLayout(paste_group)
        paste_layout.setSpacing(8)
        paste_desc = QLabel("直前の文字起こし結果を再度貼り付けるショートカット")
        paste_desc.setStyleSheet(f"color: {_C['text_dim']}; font-size: 11px;")
        paste_layout.addWidget(paste_desc)
        paste_display = self._config.get("paste_last_hotkey", {}).get("display", "Cmd+Ctrl+V")
        self._paste_hotkey_btn = _HotkeyCapture(paste_display)
        paste_layout.addWidget(self._paste_hotkey_btn)
        layout.addWidget(paste_group)

        # ── 文字起こしモード ──
        mode_group = QGroupBox("文字起こし後の表示方法")
        mode_layout = QVBoxLayout(mode_group)
        mode_layout.setSpacing(8)
        mode_desc = QLabel("文字起こし完了後にテキストをどう表示するか選択します")
        mode_desc.setStyleSheet(f"color: {_C['text_dim']}; font-size: 11px;")
        mode_layout.addWidget(mode_desc)

        self._transcription_mode_group = QButtonGroup(self)
        current_mode = self._config.get("transcription_mode", "edit")

        rb_edit = QRadioButton("編集ウィンドウで表示（修正してから貼り付け）")
        rb_edit.setStyleSheet(f"color: {_C['text']}; font-size: 12px;")
        rb_direct = QRadioButton("入力欄に直接貼り付け（編集ウィンドウなし）")
        rb_direct.setStyleSheet(f"color: {_C['text']}; font-size: 12px;")

        self._transcription_mode_group.addButton(rb_edit, 0)
        self._transcription_mode_group.addButton(rb_direct, 1)
        if current_mode == "direct":
            rb_direct.setChecked(True)
        else:
            rb_edit.setChecked(True)

        mode_layout.addWidget(rb_edit)
        mode_layout.addWidget(rb_direct)
        layout.addWidget(mode_group)

        # ── 高速モード ──
        self._fast_mode_cb = QCheckBox("高速モード（Apple音声認識を使用・API不要）")
        self._fast_mode_cb.setStyleSheet(f"color: {_C['text']}; font-size: 12px;")
        self._fast_mode_cb.setChecked(self._config.get("fast_mode", False))
        fast_desc = QLabel(
            "録音中のリアルタイム認識結果をそのまま使用します。\nWhisper APIを呼ばないため高速ですが、精度は下がります。"
        )
        fast_desc.setStyleSheet(f"color: {_C['text_dim']}; font-size: 11px;")
        fast_desc.setWordWrap(True)
        layout.addWidget(self._fast_mode_cb)
        layout.addWidget(fast_desc)

        # ── テキスト自動整形 ──
        format_group = QGroupBox("テキスト自動整形")
        format_layout = QVBoxLayout(format_group)
        format_layout.setSpacing(8)
        format_desc = QLabel(
            "音声入力後のテキストを自動で読みやすい形に整形します。\n"
            "編集ウィンドウの「整形」ボタンからもモード切替できます。"
        )
        format_desc.setStyleSheet(f"color: {_C['text_dim']}; font-size: 11px;")
        format_desc.setWordWrap(True)
        format_layout.addWidget(format_desc)

        fmt_row = QHBoxLayout()
        fmt_label = QLabel("整形モード:")
        fmt_label.setStyleSheet(f"color: {_C['text']}; font-size: 12px;")
        self._format_combo = QComboBox()
        self._format_combo.addItems(["OFF（そのまま）", "読みやすく整形", "箇条書き", "段落構成", "自動判定"])
        fmt_map = {"off": 0, "clean": 1, "bullets": 2, "paragraph": 3, "auto": 4}
        self._format_combo.setCurrentIndex(fmt_map.get(self._config.get("auto_format_mode", "off"), 0))
        self._format_combo.setStyleSheet(
            f"QComboBox {{ color: {_C['text']}; background: {_C['bg_input']};"
            f" border: 1px solid {_C['border']}; border-radius: 6px; padding: 4px 8px; font-size: 12px; }}"
        )
        fmt_row.addWidget(fmt_label)
        fmt_row.addWidget(self._format_combo, 1)
        format_layout.addLayout(fmt_row)

        format_group.setStyleSheet(
            f"QGroupBox {{ color: {_C['text']}; font-weight: bold; font-size: 12px;"
            f" border: 1px solid {_C['border']}; border-radius: 8px; padding: 16px 12px; margin-top: 12px; }}"
            f" QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 4px; }}"
        )
        layout.addWidget(format_group)

        # ── Returnキーの動作 ──
        return_group = QGroupBox("Returnキーの動作（編集ウィンドウ）")
        return_layout = QVBoxLayout(return_group)
        return_layout.setSpacing(8)
        return_desc = QLabel("文字起こし結果の編集ウィンドウでReturnキーを押したときの動作")
        return_desc.setStyleSheet(f"color: {_C['text_dim']}; font-size: 11px;")
        return_layout.addWidget(return_desc)

        self._return_action_group = QButtonGroup(self)
        current_action = self._config.get("return_key_action", "send")

        rb_send = QRadioButton("Return = 送信（貼り付け + Enter）、Shift+Return = 貼り付けのみ")
        rb_send.setStyleSheet(f"color: {_C['text']}; font-size: 12px;")
        rb_paste = QRadioButton("Return = 貼り付けのみ、Shift+Return = 送信（貼り付け + Enter）")
        rb_paste.setStyleSheet(f"color: {_C['text']}; font-size: 12px;")

        self._return_action_group.addButton(rb_send, 0)
        self._return_action_group.addButton(rb_paste, 1)
        if current_action == "paste":
            rb_paste.setChecked(True)
        else:
            rb_send.setChecked(True)

        return_layout.addWidget(rb_send)
        return_layout.addWidget(rb_paste)
        layout.addWidget(return_group)

        # ── 再起動の注意 ──
        note = QLabel("※ ショートカットの変更後はアプリを再起動してください")
        note.setStyleSheet(f"color: {_C['text_dim']}; font-size: 10px;")
        layout.addWidget(note)

        # ── セパレーター ──
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {_C['border']};")
        layout.addWidget(sep)

        # ── ウェイクワード見出し ──
        ww_title = QLabel("WAKE WORDS")
        ww_title.setFont(QFont("SF Pro Display", 14, QFont.Weight.Bold))
        ww_title.setStyleSheet(f"color: {_C['text_bright']}; letter-spacing: 2px;")
        layout.addWidget(ww_title)
        ww_desc = QLabel("録音中にこれらの言葉で始めると、対応する機能が自動起動します。\nカンマ区切りで複数設定可能。")
        ww_desc.setStyleSheet(f"color: {_C['text_dim']}; font-size: 11px;")
        ww_desc.setWordWrap(True)
        layout.addWidget(ww_desc)

        _input_style = f"""
            QLineEdit {{
                color: {_C["text"]};
                background: {_C["bg_input"]};
                border: 1px solid {_C["border"]};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {_C["border_focus"]};
            }}
        """

        # 音声メモ
        memo_group = QGroupBox("音声メモ")
        memo_layout = QVBoxLayout(memo_group)
        memo_layout.setSpacing(6)
        memo_hint = QLabel("例: 「メモ 今日のタスク...」で音声メモモードに切り替え")
        memo_hint.setStyleSheet(f"color: {_C['text_dim']}; font-size: 10px;")
        memo_layout.addWidget(memo_hint)
        self._memo_ww_edit = QLineEdit()
        self._memo_ww_edit.setStyleSheet(_input_style)
        self._memo_ww_edit.setPlaceholderText("メモ,めも,memo,ボイスメモ,...")
        self._memo_ww_edit.setText(
            self._config.get("memo_wake_words", "メモ,めも,memo,ボイスメモ,音声メモ,おんせいメモ")
        )
        memo_layout.addWidget(self._memo_ww_edit)
        layout.addWidget(memo_group)

        # リサーチ
        research_group = QGroupBox("リサーチ")
        research_layout = QVBoxLayout(research_group)
        research_layout.setSpacing(6)
        research_hint = QLabel("例: 「リサーチ Pythonの非同期処理」でリサーチモードに切り替え")
        research_hint.setStyleSheet(f"color: {_C['text_dim']}; font-size: 10px;")
        research_layout.addWidget(research_hint)
        self._research_ww_edit = QLineEdit()
        self._research_ww_edit.setStyleSheet(_input_style)
        self._research_ww_edit.setPlaceholderText("リサーチ,research,調べて,...")
        self._research_ww_edit.setText(
            self._config.get(
                "research_wake_words",
                "リサーチ,りさーち,research,調べて,しらべて,調べてください,調べておいて,リサーチして,リサーチしてください",
            )
        )
        research_layout.addWidget(self._research_ww_edit)
        layout.addWidget(research_group)

        # カレンダー
        cal_group = QGroupBox("カレンダー")
        cal_layout = QVBoxLayout(cal_group)
        cal_layout.setSpacing(6)
        cal_hint = QLabel("例: 「カレンダー 明日14時に会議」で予定を自動登録")
        cal_hint.setStyleSheet(f"color: {_C['text_dim']}; font-size: 10px;")
        cal_layout.addWidget(cal_hint)
        self._cal_ww_edit = QLineEdit()
        self._cal_ww_edit.setStyleSheet(_input_style)
        self._cal_ww_edit.setPlaceholderText("カレンダー,calendar,予定追加,...")
        self._cal_ww_edit.setText(
            self._config.get("calendar_wake_words", "カレンダー,かれんだー,calendar,予定追加,スケジュール追加")
        )
        cal_layout.addWidget(self._cal_ww_edit)
        layout.addWidget(cal_group)

        layout.addStretch()
        scroll.setWidget(content)
        return scroll

    # ══════════════════════════════════════════════════════════════════════════
    #  タブ3: 辞書
    # ══════════════════════════════════════════════════════════════════════════
    def _build_dictionary_tab(self) -> QWidget:
        from dictionary import add_word, load_dictionary, remove_word

        self._dict_load = load_dictionary
        self._dict_add = add_word
        self._dict_remove = remove_word

        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        # ヘッダー
        header = QHBoxLayout()
        title_col = QVBoxLayout()
        t = QLabel("DICTIONARY")
        t.setFont(QFont("SF Pro Display", 16, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {_C['text_bright']}; letter-spacing: 3px;")
        title_col.addWidget(t)
        sub = QLabel("カスタム単語を登録してAI精度を向上")
        sub.setStyleSheet(f"color: {_C['text_dim']}; font-size: 12px;")
        title_col.addWidget(sub)
        header.addLayout(title_col)
        header.addStretch()

        # カウンターバッジ
        self._dict_count_label = QLabel()
        self._dict_count_label.setStyleSheet(f"""
            color: {_C["accent3"]};
            background: rgba(56, 189, 248, 0.1);
            border: 1px solid rgba(56, 189, 248, 0.25);
            border-radius: 12px;
            padding: 4px 14px;
            font-size: 11px;
            font-weight: bold;
        """)
        header.addWidget(self._dict_count_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(header)

        # 追加ボタン
        add_btn = QPushButton("+ 新しい単語を追加")
        add_btn.setStyleSheet(f"""
            QPushButton {{
                color: {_C["accent"]};
                background: {_C["accent_glow"]};
                border: 1px dashed rgba(108,140,255,0.4);
                border-radius: 10px;
                padding: 10px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(108,140,255,0.2);
                border: 1px solid {_C["accent"]};
            }}
        """)
        add_btn.clicked.connect(self._dict_show_add)
        layout.addWidget(add_btn)

        # 追加入力行
        self._dict_input_row = QWidget()
        self._dict_input_row.hide()
        self._dict_input_row.setStyleSheet(f"""
            QWidget {{
                background: {_C["bg_input"]};
                border: 1px solid {_C["border_focus"]};
                border-radius: 12px;
            }}
        """)
        ir = QHBoxLayout(self._dict_input_row)
        ir.setContentsMargins(12, 8, 12, 8)
        ir.setSpacing(8)
        self._dict_input_edit = QLineEdit()
        self._dict_input_edit.setPlaceholderText("単語を入力...")
        self._dict_input_edit.setStyleSheet(f"""
            QLineEdit {{
                color: {_C["text"]};
                background: transparent;
                border: none;
                font-size: 14px;
                padding: 4px;
            }}
        """)
        self._dict_input_edit.returnPressed.connect(self._dict_do_add)
        ir.addWidget(self._dict_input_edit)
        ok_btn = QPushButton("追加")
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                color: white;
                background: {_C["accent"]};
                border: none;
                border-radius: 8px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: #7d9bff; }}
        """)
        ok_btn.clicked.connect(self._dict_do_add)
        ir.addWidget(ok_btn)
        cancel_btn = QPushButton("x")
        cancel_btn.setFixedSize(30, 30)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                color: {_C["text_dim"]};
                background: transparent;
                border: 1px solid {_C["border"]};
                border-radius: 15px;
                font-size: 13px;
            }}
            QPushButton:hover {{ color: {_C["danger"]}; border-color: {_C["danger"]}; }}
        """)
        cancel_btn.clicked.connect(lambda: self._dict_input_row.hide())
        ir.addWidget(cancel_btn)
        layout.addWidget(self._dict_input_row)

        # リスト
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._dict_list_container = QWidget()
        self._dict_list_container.setStyleSheet("background: transparent;")
        self._dict_list_layout = QVBoxLayout(self._dict_list_container)
        self._dict_list_layout.setContentsMargins(0, 0, 0, 0)
        self._dict_list_layout.setSpacing(4)
        self._dict_list_layout.addStretch()
        scroll.setWidget(self._dict_list_container)
        layout.addWidget(scroll, 1)

        self._dict_reload()
        return widget

    def _dict_show_add(self):
        self._dict_input_row.show()
        self._dict_input_edit.clear()
        self._dict_input_edit.setFocus()

    def _dict_do_add(self):
        word = self._dict_input_edit.text().strip()
        if not word:
            return
        self._dict_add(word)
        self._dict_input_edit.clear()
        self._dict_reload()

    def _dict_reload(self):
        while self._dict_list_layout.count() > 1:
            item = self._dict_list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        words = self._dict_load()
        self._dict_count_label.setText(f"{len(words)} / 800")
        for word in words:
            row = QWidget()
            row.setStyleSheet(f"""
                QWidget {{
                    background: {_C["bg_row"]};
                    border-radius: 10px;
                    border: 1px solid transparent;
                }}
                QWidget:hover {{
                    background: {_C["bg_row_hover"]};
                    border: 1px solid {_C["border"]};
                }}
            """)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(16, 10, 12, 10)
            rl.setSpacing(10)
            # 小さいドットインジケーター
            dot = QLabel()
            dot.setFixedSize(6, 6)
            dot.setStyleSheet(f"background: {_C['accent']}; border-radius: 3px;")
            rl.addWidget(dot)
            lbl = QLabel(word)
            lbl.setFont(QFont("", 13))
            lbl.setStyleSheet(f"color: {_C['text']}; background: transparent;")
            rl.addWidget(lbl, 1)
            del_btn = QPushButton("x")
            del_btn.setFixedSize(28, 28)
            del_btn.setStyleSheet(f"""
                QPushButton {{
                    color: {_C["text_dim"]};
                    background: transparent;
                    border: 1px solid transparent;
                    border-radius: 14px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    color: {_C["danger"]};
                    background: {_C["danger_bg"]};
                    border: 1px solid {_C["danger_border"]};
                }}
            """)
            del_btn.clicked.connect(lambda _, w=word: self._dict_do_remove(w))
            rl.addWidget(del_btn)
            self._dict_list_layout.insertWidget(self._dict_list_layout.count() - 1, row)

    def _dict_do_remove(self, word: str):
        self._dict_remove(word)
        self._dict_reload()

    # ══════════════════════════════════════════════════════════════════════════
    #  タブ3: カスタム指示
    # ══════════════════════════════════════════════════════════════════════════
    def _build_instructions_tab(self) -> QWidget:
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(widget)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        # ヘッダー
        t = QLabel("CUSTOM INSTRUCTIONS")
        t.setFont(QFont("SF Pro Display", 16, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {_C['text_bright']}; letter-spacing: 3px;")
        layout.addWidget(t)

        sub = QLabel("文字起こしの変換スタイルを自由にカスタマイズできます。")
        sub.setStyleSheet(f"color: {_C['text_dim']}; font-size: 12px;")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        # ヒントカード
        hint_card = QWidget()
        hint_card.setStyleSheet("""
            QWidget {
                background: rgba(167, 139, 250, 0.08);
                border: 1px solid rgba(167, 139, 250, 0.2);
                border-radius: 10px;
            }
        """)
        hint_layout = QVBoxLayout(hint_card)
        hint_layout.setContentsMargins(14, 10, 14, 10)
        hint_layout.setSpacing(4)
        hint_title = QLabel("EXAMPLES")
        hint_title.setStyleSheet(f"color: {_C['accent2']}; font-size: 10px; font-weight: bold; letter-spacing: 2px;")
        hint_layout.addWidget(hint_title)
        for example in ["Slackではカジュアルな口調で", "句読点を使わない", "ですます調に統一"]:
            ex = QLabel(f"  {example}")
            ex.setStyleSheet(f"color: {_C['text_dim']}; font-size: 11px;")
            hint_layout.addWidget(ex)
        layout.addWidget(hint_card)

        # エディタ
        self._instructions_edit = QTextEdit()
        self._instructions_edit.setPlaceholderText("ここにカスタム指示を入力...")
        self._instructions_edit.setFont(QFont("", 13))
        self._instructions_edit.setMinimumHeight(200)
        self._instructions_edit.setStyleSheet(f"""
            QTextEdit {{
                color: {_C["text"]};
                background: {_C["bg_input"]};
                border: 1px solid {_C["border"]};
                border-radius: 12px;
                padding: 14px;
                font-size: 13px;
                line-height: 1.6;
            }}
            QTextEdit:focus {{
                border: 1px solid {_C["accent2"]};
            }}
        """)
        self._instructions_edit.setPlainText(_load_custom_instructions())
        layout.addWidget(self._instructions_edit, 1)

        return widget

    # ══════════════════════════════════════════════════════════════════════════
    #  タブ4: 自動置換
    # ══════════════════════════════════════════════════════════════════════════
    def _build_replacements_tab(self) -> QWidget:
        from replacements import add_replacement, load_replacements, remove_replacement

        self._repl_load = load_replacements
        self._repl_add = add_replacement
        self._repl_remove = remove_replacement

        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        # ヘッダー
        header = QHBoxLayout()
        title_col = QVBoxLayout()
        t = QLabel("AUTO REPLACE")
        t.setFont(QFont("SF Pro Display", 16, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {_C['text_bright']}; letter-spacing: 3px;")
        title_col.addWidget(t)
        sub = QLabel("音声認識後に自動で置換されるルール")
        sub.setStyleSheet(f"color: {_C['text_dim']}; font-size: 12px;")
        title_col.addWidget(sub)
        header.addLayout(title_col)
        header.addStretch()

        self._repl_count_label = QLabel()
        self._repl_count_label.setStyleSheet(f"""
            color: {_C["success"]};
            background: rgba(52, 211, 153, 0.1);
            border: 1px solid rgba(52, 211, 153, 0.25);
            border-radius: 12px;
            padding: 4px 14px;
            font-size: 11px;
            font-weight: bold;
        """)
        header.addWidget(self._repl_count_label, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(header)

        # 追加ボタン
        add_btn = QPushButton("+ 新しい置換ルールを追加")
        add_btn.setStyleSheet(f"""
            QPushButton {{
                color: {_C["success"]};
                background: rgba(52, 211, 153, 0.08);
                border: 1px dashed rgba(52, 211, 153, 0.3);
                border-radius: 10px;
                padding: 10px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(52, 211, 153, 0.15);
                border: 1px solid {_C["success"]};
            }}
        """)
        add_btn.clicked.connect(self._repl_show_add)
        layout.addWidget(add_btn)

        # 追加入力行
        self._repl_input_row = QWidget()
        self._repl_input_row.hide()
        self._repl_input_row.setStyleSheet(f"""
            QWidget {{
                background: {_C["bg_input"]};
                border: 1px solid rgba(52, 211, 153, 0.4);
                border-radius: 12px;
            }}
        """)
        ir = QHBoxLayout(self._repl_input_row)
        ir.setContentsMargins(12, 10, 12, 10)
        ir.setSpacing(8)
        self._repl_from_edit = QLineEdit()
        self._repl_from_edit.setPlaceholderText("変換前")
        self._repl_from_edit.setStyleSheet(f"""
            QLineEdit {{
                color: {_C["text"]};
                background: transparent;
                border: none;
                border-bottom: 1px solid {_C["border"]};
                border-radius: 0;
                font-size: 13px;
                padding: 4px 2px;
            }}
            QLineEdit:focus {{ border-bottom-color: {_C["accent"]}; }}
        """)
        ir.addWidget(self._repl_from_edit)
        arrow = QLabel("-->")
        arrow.setStyleSheet(f"color: {_C['success']}; font-size: 16px; font-weight: bold; font-family: monospace;")
        ir.addWidget(arrow)
        self._repl_to_edit = QLineEdit()
        self._repl_to_edit.setPlaceholderText("変換後")
        self._repl_to_edit.setStyleSheet(f"""
            QLineEdit {{
                color: {_C["success"]};
                background: transparent;
                border: none;
                border-bottom: 1px solid {_C["border"]};
                border-radius: 0;
                font-size: 13px;
                padding: 4px 2px;
            }}
            QLineEdit:focus {{ border-bottom-color: {_C["success"]}; }}
        """)
        self._repl_to_edit.returnPressed.connect(self._repl_do_add)
        ir.addWidget(self._repl_to_edit)
        ok_btn = QPushButton("追加")
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                color: white;
                background: {_C["success"]};
                border: none;
                border-radius: 8px;
                padding: 6px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{ background: #4ade80; }}
        """)
        ok_btn.clicked.connect(self._repl_do_add)
        ir.addWidget(ok_btn)
        cancel_btn = QPushButton("x")
        cancel_btn.setFixedSize(30, 30)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                color: {_C["text_dim"]};
                background: transparent;
                border: 1px solid {_C["border"]};
                border-radius: 15px;
                font-size: 13px;
            }}
            QPushButton:hover {{ color: {_C["danger"]}; border-color: {_C["danger"]}; }}
        """)
        cancel_btn.clicked.connect(lambda: self._repl_input_row.hide())
        ir.addWidget(cancel_btn)
        layout.addWidget(self._repl_input_row)

        # リスト
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._repl_list_container = QWidget()
        self._repl_list_container.setStyleSheet("background: transparent;")
        self._repl_list_layout = QVBoxLayout(self._repl_list_container)
        self._repl_list_layout.setContentsMargins(0, 0, 0, 0)
        self._repl_list_layout.setSpacing(4)
        self._repl_list_layout.addStretch()
        scroll.setWidget(self._repl_list_container)
        layout.addWidget(scroll, 1)

        self._repl_reload()
        return widget

    def _repl_show_add(self):
        self._repl_input_row.show()
        self._repl_from_edit.clear()
        self._repl_to_edit.clear()
        self._repl_from_edit.setFocus()

    def _repl_do_add(self):
        from_text = self._repl_from_edit.text().strip()
        to_text = self._repl_to_edit.text()
        if not from_text:
            return
        self._repl_add(from_text, to_text)
        self._repl_from_edit.clear()
        self._repl_to_edit.clear()
        self._repl_reload()

    def _repl_reload(self):
        while self._repl_list_layout.count() > 1:
            item = self._repl_list_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        rules = self._repl_load()
        self._repl_count_label.setText(f"{len(rules)} / 800")
        _edit_style = f"""
            QLineEdit {{
                color: {_C["text"]};
                background: {_C["bg_input"]};
                border: 1px solid {_C["accent"]};
                border-radius: 6px;
                font-size: 13px;
                padding: 4px 8px;
            }}
        """
        _edit_style_to = f"""
            QLineEdit {{
                color: {_C["success"]};
                background: {_C["bg_input"]};
                border: 1px solid {_C["accent"]};
                border-radius: 6px;
                font-size: 13px;
                padding: 4px 8px;
            }}
        """
        for rule in rules:
            from_text = rule.get("from", "")
            to_text = rule.get("to", "")
            row = QWidget()
            row.setStyleSheet(f"""
                QWidget {{
                    background: {_C["bg_row"]};
                    border-radius: 10px;
                    border: 1px solid transparent;
                }}
                QWidget:hover {{
                    background: {_C["bg_row_hover"]};
                    border: 1px solid {_C["border"]};
                }}
            """)
            rl = QHBoxLayout(row)
            rl.setContentsMargins(16, 10, 12, 10)
            rl.setSpacing(10)

            # ── 表示モード ──
            from_lbl = QLabel(from_text)
            from_lbl.setFont(QFont("", 13))
            from_lbl.setStyleSheet(f"color: {_C['text']}; background: transparent;")
            rl.addWidget(from_lbl)
            arrow = QLabel("-->")
            arrow.setStyleSheet(
                f"color: {_C['success']}; font-weight: bold; font-family: monospace; font-size: 12px; background: transparent;"
            )
            rl.addWidget(arrow)
            to_lbl = QLabel(to_text)
            to_lbl.setFont(QFont("", 13))
            to_lbl.setStyleSheet(f"color: {_C['success']}; background: transparent;")
            rl.addWidget(to_lbl, 1)

            # ── 編集モード（初期非表示） ──
            from_edit = QLineEdit(from_text)
            from_edit.setFont(QFont("", 13))
            from_edit.setStyleSheet(_edit_style)
            from_edit.hide()
            rl.addWidget(from_edit)

            arrow2 = QLabel("-->")
            arrow2.setStyleSheet(
                f"color: {_C['success']}; font-weight: bold; font-family: monospace; font-size: 12px; background: transparent;"
            )
            arrow2.hide()
            rl.addWidget(arrow2)

            to_edit = QLineEdit(to_text)
            to_edit.setFont(QFont("", 13))
            to_edit.setStyleSheet(_edit_style_to)
            to_edit.hide()
            rl.addWidget(to_edit, 1)

            save_btn = QPushButton("保存")
            save_btn.setStyleSheet(f"""
                QPushButton {{
                    color: white; background: {_C["success"]};
                    border: none; border-radius: 6px;
                    padding: 4px 12px; font-size: 11px; font-weight: bold;
                }}
                QPushButton:hover {{ background: #4ade80; }}
            """)
            save_btn.hide()
            rl.addWidget(save_btn)

            cancel_edit_btn = QPushButton("戻す")
            cancel_edit_btn.setStyleSheet(f"""
                QPushButton {{
                    color: {_C["text_dim"]}; background: transparent;
                    border: 1px solid {_C["border"]}; border-radius: 6px;
                    padding: 4px 12px; font-size: 11px;
                }}
                QPushButton:hover {{ color: {_C["text"]}; }}
            """)
            cancel_edit_btn.hide()
            rl.addWidget(cancel_edit_btn)

            # ── 編集ボタン ──
            edit_btn = QPushButton("編集")
            edit_btn.setStyleSheet(f"""
                QPushButton {{
                    color: {_C["accent"]}; background: transparent;
                    border: 1px solid {_C["border"]}; border-radius: 6px;
                    padding: 3px 10px; font-size: 11px;
                }}
                QPushButton:hover {{ border-color: {_C["accent"]}; background: rgba(99,102,241,0.1); }}
            """)
            rl.addWidget(edit_btn)

            # ── 削除ボタン ──
            del_btn = QPushButton("x")
            del_btn.setFixedSize(28, 28)
            del_btn.setStyleSheet(f"""
                QPushButton {{
                    color: {_C["text_dim"]};
                    background: transparent;
                    border: 1px solid transparent;
                    border-radius: 14px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    color: {_C["danger"]};
                    background: {_C["danger_bg"]};
                    border: 1px solid {_C["danger_border"]};
                }}
            """)
            del_btn.clicked.connect(lambda _, ft=from_text: self._repl_do_remove(ft))
            rl.addWidget(del_btn)

            # ── 表示/編集モード切替 ──
            display_widgets = [from_lbl, arrow, to_lbl, edit_btn]
            edit_widgets = [from_edit, arrow2, to_edit, save_btn, cancel_edit_btn]

            def enter_edit(_=None, dw=display_widgets, ew=edit_widgets, fe=from_edit):
                for w in dw:
                    w.hide()
                for w in ew:
                    w.show()
                fe.setFocus()

            def exit_edit(_=None, dw=display_widgets, ew=edit_widgets):
                for w in ew:
                    w.hide()
                for w in dw:
                    w.show()

            def do_save(_=None, ft=from_text, fe=from_edit, te=to_edit):
                new_from = fe.text().strip()
                new_to = te.text()
                if not new_from:
                    return
                self._repl_remove(ft)
                self._repl_add(new_from, new_to)
                self._repl_reload()

            edit_btn.clicked.connect(enter_edit)
            save_btn.clicked.connect(do_save)
            to_edit.returnPressed.connect(do_save)
            cancel_edit_btn.clicked.connect(exit_edit)

            self._repl_list_layout.insertWidget(self._repl_list_layout.count() - 1, row)

    def _repl_do_remove(self, from_text: str):
        self._repl_remove(from_text)
        self._repl_reload()

    # ══════════════════════════════════════════════════════════════════════════
    #  タブ5: データ管理
    # ══════════════════════════════════════════════════════════════════════════
    def _build_data_tab(self) -> QWidget:
        widget = QWidget()
        widget.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(widget)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 24, 24, 24)

        # ヘッダー
        t = QLabel("DATA MANAGEMENT")
        t.setFont(QFont("SF Pro Display", 16, QFont.Weight.Bold))
        t.setStyleSheet(f"color: {_C['text_bright']}; letter-spacing: 3px;")
        layout.addWidget(t)

        sub = QLabel("保存されているデータの確認・エクスポート・削除ができます。")
        sub.setStyleSheet(f"color: {_C['text_dim']}; font-size: 12px;")
        sub.setWordWrap(True)
        layout.addWidget(sub)

        # データ概要カード
        summary_card = QWidget()
        summary_card.setStyleSheet(f"""
            QWidget {{
                background: {_C["bg_row"]};
                border: 1px solid {_C["border"]};
                border-radius: 10px;
            }}
        """)
        sc_layout = QVBoxLayout(summary_card)
        sc_layout.setContentsMargins(16, 12, 16, 12)
        sc_layout.setSpacing(6)
        sc_title = QLabel("STORED DATA")
        sc_title.setStyleSheet(
            f"color: {_C['accent2']}; font-size: 10px; font-weight: bold; letter-spacing: 2px; background: transparent;"
        )
        sc_layout.addWidget(sc_title)
        self._data_summary_label = QLabel()
        self._data_summary_label.setStyleSheet(f"color: {_C['text']}; font-size: 12px; background: transparent;")
        self._data_summary_label.setWordWrap(True)
        sc_layout.addWidget(self._data_summary_label)
        layout.addWidget(summary_card)
        self._refresh_data_summary()

        # プライバシーポリシー表示ボタン
        privacy_btn = QPushButton("プライバシーポリシーを表示")
        privacy_btn.setStyleSheet(f"""
            QPushButton {{
                color: {_C["accent"]};
                background: rgba(108, 140, 255, 0.08);
                border: 1px solid rgba(108, 140, 255, 0.25);
                border-radius: 10px;
                padding: 12px;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background: rgba(108, 140, 255, 0.15);
                border: 1px solid {_C["accent"]};
            }}
        """)
        privacy_btn.clicked.connect(self._show_privacy_policy)
        layout.addWidget(privacy_btn)

        # エクスポートボタン
        export_btn = QPushButton("全データをエクスポート (JSON)")
        export_btn.setStyleSheet(f"""
            QPushButton {{
                color: {_C["success"]};
                background: rgba(52, 211, 153, 0.08);
                border: 1px solid rgba(52, 211, 153, 0.25);
                border-radius: 10px;
                padding: 12px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(52, 211, 153, 0.15);
                border: 1px solid {_C["success"]};
            }}
        """)
        export_btn.clicked.connect(self._export_data)
        layout.addWidget(export_btn)

        # 削除ボタン
        delete_btn = QPushButton("全データを削除")
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                color: {_C["danger"]};
                background: {_C["danger_bg"]};
                border: 1px solid {_C["danger_border"]};
                border-radius: 10px;
                padding: 12px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(248, 113, 113, 0.2);
                border: 1px solid {_C["danger"]};
            }}
        """)
        delete_btn.clicked.connect(self._delete_all_data)
        layout.addWidget(delete_btn)

        layout.addStretch()
        return widget

    def _refresh_data_summary(self):
        from data_manager import get_data_summary

        summary = get_data_summary()
        if not summary:
            self._data_summary_label.setText("保存されたデータはありません。")
        else:
            lines = [f"  {k}: {v}" for k, v in summary.items()]
            self._data_summary_label.setText("\n".join(lines))

    def _show_privacy_policy(self):
        from privacy_policy import PRIVACY_POLICY, TERMS_OF_USE

        dlg = QDialog(self)
        dlg.setWindowTitle("プライバシーポリシー")
        dlg.setFixedSize(500, 500)
        dlg.setStyleSheet(f"QDialog {{ background: {_C['bg']}; }}")
        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(16, 16, 16, 16)
        from PyQt6.QtWidgets import QTextBrowser

        browser = QTextBrowser()
        browser.setPlainText(PRIVACY_POLICY + "\n\n" + "=" * 40 + "\n\n" + TERMS_OF_USE)
        browser.setFont(QFont(".AppleSystemUIFont", 11))
        browser.setStyleSheet(f"""
            QTextBrowser {{
                background: {_C["bg_card"]};
                color: {_C["text"]};
                border: 1px solid {_C["border"]};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        lay.addWidget(browser)
        close_btn = QPushButton("閉じる")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                color: {_C["text"]};
                background: {_C["bg_input"]};
                border: 1px solid {_C["border"]};
                border-radius: 8px;
                padding: 8px 20px;
            }}
            QPushButton:hover {{ border-color: {_C["accent"]}; }}
        """)
        close_btn.clicked.connect(dlg.accept)
        lay.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        dlg.exec()

    def _export_data(self):
        from datetime import datetime

        from data_manager import export_all_data

        default_name = f"voice_input_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path, _ = QFileDialog.getSaveFileName(
            self, "データエクスポート", str(Path.home() / "Desktop" / default_name), "JSON Files (*.json)"
        )
        if path:
            try:
                export_all_data(path)
                QMessageBox.information(self, "エクスポート完了", f"データをエクスポートしました:\n{path}")
            except Exception as e:
                QMessageBox.warning(self, "エラー", f"エクスポートに失敗しました:\n{e}")

    def _delete_all_data(self):
        reply = QMessageBox.warning(
            self,
            "全データ削除の確認",
            "すべてのユーザーデータ（修正履歴・語彙辞書・APIキー等）を削除します。\n"
            "この操作は取り消せません。\n\n本当に削除しますか？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            # 二重確認
            reply2 = QMessageBox.critical(
                self,
                "最終確認",
                "本当にすべてのデータを削除しますか？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply2 == QMessageBox.StandardButton.Yes:
                from data_manager import delete_all_data

                deleted = delete_all_data()
                self._refresh_data_summary()
                QMessageBox.information(
                    self, "削除完了", "以下のデータを削除しました:\n" + "\n".join(f"  {d}" for d in deleted)
                )

    # ══════════════════════════════════════════════════════════════════════════
    #  共通ヘルパー
    # ══════════════════════════════════════════════════════════════════════════
    @staticmethod
    def _sep():
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {_C['border']};")
        return sep

    @staticmethod
    def _stats_text(stats: dict) -> str:
        return (
            f"修正履歴: {stats['correction_history']} 件  /  "
            f"単語辞書: {stats['word_substitutions']} 件  /  "
            f"フレーズ辞書: {stats['phrase_substitutions']} 件"
        )

    def _add_rule_row(self, app_name: str = "", rule_text: str = ""):
        row_widget = QWidget()
        row_widget.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(6)

        app_edit = QLineEdit()
        app_edit.setPlaceholderText("アプリ名")
        app_edit.setText(app_name)
        app_edit.setFixedWidth(120)

        rule_edit = QLineEdit()
        rule_edit.setPlaceholderText("指示（例: 句点を使わず「!」で終わらせる）")
        rule_edit.setText(rule_text)

        del_btn = QPushButton("x")
        del_btn.setFixedSize(28, 28)
        del_btn.setStyleSheet(f"""
            QPushButton {{
                color: {_C["text_dim"]};
                background: transparent;
                border: none;
                border-radius: 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                color: {_C["danger"]};
                background: {_C["danger_bg"]};
            }}
        """)

        row_layout.addWidget(app_edit)
        row_layout.addWidget(rule_edit)
        row_layout.addWidget(del_btn)

        pair = (app_edit, rule_edit)
        self._rules_rows.append(pair)
        self._rules_container_layout.addWidget(row_widget)

        def _remove():
            row_widget.setParent(None)
            row_widget.deleteLater()
            if pair in self._rules_rows:
                self._rules_rows.remove(pair)

        del_btn.clicked.connect(_remove)

    def _browse_team_vocab(self):
        path, _ = QFileDialog.getOpenFileName(self, "チーム語彙ファイルを選択", "", "JSON Files (*.json)")
        if path:
            self._team_vocab_edit.setText(path)

    def _export_vocab(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "語彙をエクスポート", "vocabulary_export.json", "JSON Files (*.json)"
        )
        if not path:
            return
        try:
            vocab = load_vocabulary()
            with open(path, "w", encoding="utf-8") as f:
                json.dump(vocab, f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "エクスポート完了", f"語彙をエクスポートしました:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"エクスポート失敗:\n{e}")

    def _import_vocab(self):
        path, _ = QFileDialog.getOpenFileName(self, "語彙をインポート", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                imported = json.load(f)
            vocab = load_vocabulary()
            vocab.update(imported)
            save_vocabulary(vocab)
            QMessageBox.information(self, "インポート完了", f"語彙をインポートしました:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "エラー", f"インポート失敗:\n{e}")

    def _on_regen(self):
        history = get_vocabulary_stats()["correction_history"]
        if history == 0:
            QMessageBox.information(
                self, "AI学習", "まだ修正履歴がありません。\n音声入力を使って修正を行うと学習が始まります。"
            )
            return
        self._regen_btn.setText("学習中...")
        self._regen_btn.setEnabled(False)
        force_regenerate()
        QTimer.singleShot(4000, self._refresh_prompt)

    def _refresh_prompt(self):
        from config import load_whisper_prompt

        prompt = load_whisper_prompt()
        self._prompt_box.setText(
            f"Whisperプロンプト:\n{prompt if prompt else '（生成失敗 — 修正履歴が少ない可能性があります）'}"
        )
        self._regen_btn.setText("AI学習を実行")
        self._regen_btn.setEnabled(True)
        stats = get_vocabulary_stats()
        self._stats_lbl.setText(self._stats_text(stats))

    def _preview_sound(self, genre_key: str):
        try:
            import sounds

            sounds.play("start", genre=genre_key)
        except Exception:
            pass

    def _save(self):
        # APIキーはKeychainに保存（config.jsonには保存しない）
        from config import save_api_key

        api_key_input = self._api_key_edit.text().strip()
        if api_key_input:
            save_api_key(api_key_input)
        self._config["openai_api_key"] = ""   # レガシー消去
        self._config["anthropic_api_key"] = ""  # config.jsonからは常に消去
        self._config["language"] = {0: "ja", 1: "en", 2: "zh", 3: "auto"}[self._lang_combo.currentIndex()]
        self._config["sound_genre"] = self._genre_keys[self._sound_radio_group.checkedId()]
        import sounds

        sounds.clear_cache()

        self._config["app_format_enabled"] = True
        self._config["style_learn_enabled"] = True
        self._config["deep_context_enabled"] = self._config.get("deep_context_enabled", False)
        self._config["team_vocab_path"] = self._team_vocab_edit.text().strip()
        app_rules = {}
        for app_edit, rule_edit in self._rules_rows:
            app_n = app_edit.text().strip()
            rule_t = rule_edit.text().strip()
            if app_n and rule_t:
                app_rules[app_n] = rule_t
        self._config["app_rules"] = app_rules
        # ショートカット
        hk = self._hotkey_btn.hotkey_data()
        if hk:
            self._config["hotkey"] = hk
        paste_hk = self._paste_hotkey_btn.hotkey_data()
        if paste_hk:
            self._config["paste_last_hotkey"] = paste_hk
        # 文字起こしモード
        self._config["transcription_mode"] = "direct" if self._transcription_mode_group.checkedId() == 1 else "edit"
        # 高速モード
        self._config["fast_mode"] = self._fast_mode_cb.isChecked()
        # テキスト自動整形
        fmt_idx = self._format_combo.currentIndex()
        self._config["auto_format_mode"] = ["off", "clean", "bullets", "paragraph", "auto"][fmt_idx]
        # Returnキーの動作
        self._config["return_key_action"] = "paste" if self._return_action_group.checkedId() == 1 else "send"
        # ウェイクワード
        self._config["memo_wake_words"] = self._memo_ww_edit.text().strip()
        self._config["research_wake_words"] = self._research_ww_edit.text().strip()
        self._config["calendar_wake_words"] = self._cal_ww_edit.text().strip()
        save_config(self._config)
        _save_custom_instructions(self._instructions_edit.toPlainText())
        self.accept()
