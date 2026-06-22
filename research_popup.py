"""Typeless風リサーチ結果ポップアップ。"""

import re

import pyperclip
from PyQt6.QtCore import QPointF, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)


def _md_to_html(md: str) -> str:
    """簡易Markdown→HTML変換。"""
    lines = md.split("\n")
    html_lines = []
    in_ul = False
    in_sub_ul = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if in_sub_ul:
                html_lines.append("</ul>")
                in_sub_ul = False
            if in_ul:
                html_lines.append("</ul>")
                in_ul = False
            html_lines.append("<br>")
            continue

        # サブリスト
        if re.match(r"^(\s{2,}|\t)[-*•]\s", line):
            item = re.sub(r"^(\s{2,}|\t)[-*•]\s+", "", line)
            item = _inline_format(item)
            if not in_sub_ul:
                html_lines.append('<ul style="margin: 2px 0 2px 16px; padding-left: 12px;">')
                in_sub_ul = True
            html_lines.append(f"<li>{item}</li>")
            continue

        # トップレベルリスト
        if re.match(r"^[-*•]\s", stripped):
            if in_sub_ul:
                html_lines.append("</ul>")
                in_sub_ul = False
            item = re.sub(r"^[-*•]\s+", "", stripped)
            item = _inline_format(item)
            if not in_ul:
                html_lines.append('<ul style="margin: 4px 0; padding-left: 18px;">')
                in_ul = True
            html_lines.append(f"<li>{item}</li>")
            continue

        # リスト外に出た
        if in_sub_ul:
            html_lines.append("</ul>")
            in_sub_ul = False
        if in_ul:
            html_lines.append("</ul>")
            in_ul = False

        # 見出し
        if stripped.startswith("### "):
            html_lines.append(f'<h4 style="margin: 8px 0 4px 0;">{_inline_format(stripped[4:])}</h4>')
        elif stripped.startswith("## "):
            html_lines.append(f'<h3 style="margin: 10px 0 4px 0;">{_inline_format(stripped[3:])}</h3>')
        elif stripped.startswith("# "):
            html_lines.append(f'<h2 style="margin: 10px 0 4px 0;">{_inline_format(stripped[2:])}</h2>')
        else:
            html_lines.append(f"<p style='margin: 3px 0;'>{_inline_format(stripped)}</p>")

    if in_sub_ul:
        html_lines.append("</ul>")
    if in_ul:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def _inline_format(text: str) -> str:
    """インラインMarkdown（太字・コード）→HTML。"""
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r'<code style="background:rgba(0,229,255,0.1);padding:1px 4px;border-radius:3px;">\1</code>', text)
    return text


def _make_icon(kind: str, size: int = 20) -> QPixmap:
    """アイコンをQPixmapで描画。"""
    px = QPixmap(size, size)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = float(size)

    if kind == "mic":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 229, 255, 180))
        p.drawRoundedRect(int(s * 0.32), int(s * 0.1), int(s * 0.36), int(s * 0.45), s * 0.12, s * 0.12)
        pen = QPen(QColor(0, 229, 255, 180), max(1.5, s * 0.08))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawArc(int(s * 0.22), int(s * 0.3), int(s * 0.56), int(s * 0.4), 0, -180 * 16)
        p.drawLine(int(s * 0.5), int(s * 0.7), int(s * 0.5), int(s * 0.85))
        p.drawLine(int(s * 0.32), int(s * 0.85), int(s * 0.68), int(s * 0.85))

    elif kind == "copy":
        pen = QPen(QColor(200, 210, 230, 180), max(1.2, s * 0.07))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(int(s * 0.28), int(s * 0.08), int(s * 0.52), int(s * 0.58), 3, 3)
        p.drawRoundedRect(int(s * 0.15), int(s * 0.28), int(s * 0.52), int(s * 0.58), 3, 3)

    elif kind == "close":
        pen = QPen(QColor(200, 210, 230, 160), max(1.5, s * 0.09))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        m = s * 0.28
        p.drawLine(int(m), int(m), int(s - m), int(s - m))
        p.drawLine(int(s - m), int(m), int(m), int(s - m))

    elif kind == "sparkle":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 229, 255, 200))
        cx, cy = s * 0.5, s * 0.5
        r1, r2 = s * 0.42, s * 0.12
        path = QPainterPath()
        path.moveTo(QPointF(cx, cy - r1))
        path.lineTo(QPointF(cx + r2, cy))
        path.lineTo(QPointF(cx, cy + r1))
        path.lineTo(QPointF(cx - r2, cy))
        path.closeSubpath()
        path2 = QPainterPath()
        path2.moveTo(QPointF(cx - r1, cy))
        path2.lineTo(QPointF(cx, cy - r2))
        path2.lineTo(QPointF(cx + r1, cy))
        path2.lineTo(QPointF(cx, cy + r2))
        path2.closeSubpath()
        p.drawPath(path)
        p.drawPath(path2)

    p.end()
    return px


_CARD_CSS = """
QWidget#researchCard {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 rgba(14,16,28,250), stop:1 rgba(8,10,22,250));
    border-radius: 16px;
    border: 1px solid rgba(0,229,255,0.18);
}
"""


class ResearchPopup(QWidget):
    """Typeless風のリサーチ結果ポップアップ。
    loading=True で「検索中...」表示、set_answer() で結果を表示。"""

    def __init__(self, query: str, answer: str = "", loading: bool = False, parent=None):
        super().__init__(parent)
        self._query = query
        self._answer = answer
        self._loading = loading
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(540)
        self._drag_pos = None
        self._dot_count = 0
        self._build_ui()
        self._position_center()

    def _position_center(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.adjustSize()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 3
            self.move(x, y)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QWidget()
        card.setObjectName("researchCard")
        card.setStyleSheet(_CARD_CSS)
        self._layout = QVBoxLayout(card)
        self._layout.setContentsMargins(24, 20, 24, 20)
        self._layout.setSpacing(0)

        # ─── ヘッダー（タイトル + 閉じる）───
        header = QHBoxLayout()
        header.setSpacing(8)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(_make_icon("mic", 18))
        icon_lbl.setFixedSize(20, 20)
        header.addWidget(icon_lbl)
        title = QLabel("音声入力")
        title.setFont(self._font(13, bold=True))
        title.setStyleSheet("color: rgba(226,232,240,0.9); background: transparent;")
        header.addWidget(title)
        header.addStretch()
        close_btn = QPushButton()
        close_btn.setIcon(QIcon(_make_icon("close", 20)))
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.05); border: none; border-radius: 14px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.12); }"
        )
        close_btn.clicked.connect(self.close)
        header.addWidget(close_btn)
        self._layout.addLayout(header)
        self._layout.addSpacing(12)

        # ─── 質問 ───
        q_label = QLabel(self._query)
        q_label.setFont(self._font(13))
        q_label.setStyleSheet(
            "color: rgba(226,232,240,0.75); padding: 8px 12px; border-radius: 8px;"
            "background: rgba(0,229,255,0.04); border: 1px solid rgba(0,229,255,0.08);"
        )
        q_label.setWordWrap(True)
        self._layout.addWidget(q_label)
        self._layout.addSpacing(14)

        # ─── 回答ヘッダー ───
        ans_header = QHBoxLayout()
        ans_header.setSpacing(6)
        sparkle = QLabel()
        sparkle.setPixmap(_make_icon("sparkle", 16))
        sparkle.setFixedSize(18, 18)
        ans_header.addWidget(sparkle)
        self._ans_title = QLabel("検索中" if self._loading else "回答")
        self._ans_title.setFont(self._font(12, bold=True))
        self._ans_title.setStyleSheet("color: rgba(0,229,255,0.85); background: transparent;")
        ans_header.addWidget(self._ans_title)
        ans_header.addStretch()
        self._copy_btn = QPushButton()
        self._copy_btn.setIcon(QIcon(_make_icon("copy", 20)))
        self._copy_btn.setFixedSize(28, 28)
        self._copy_btn.setToolTip("回答をコピー")
        self._copy_btn.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,0.05); border: none; border-radius: 6px; }"
            "QPushButton:hover { background: rgba(0,229,255,0.15); }"
        )
        self._copy_btn.clicked.connect(self._copy_answer)
        if self._loading:
            self._copy_btn.hide()
        ans_header.addWidget(self._copy_btn)
        self._layout.addLayout(ans_header)
        self._layout.addSpacing(6)

        # ─── 回答本文 / ローディング ───
        self._answer_view = QTextBrowser()
        self._answer_view.setOpenExternalLinks(True)
        self._answer_view.setFont(self._font(12.5))
        self._answer_view.setStyleSheet(
            "QTextBrowser { background: transparent; border: none;"
            "  color: rgba(226,232,240,0.88); selection-background-color: rgba(0,229,255,0.25); }"
            "QScrollBar:vertical { background: transparent; width: 5px; }"
            "QScrollBar::handle:vertical { background: rgba(0,229,255,0.2); border-radius: 2px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )
        self._answer_view.document().setDocumentMargin(8)
        self._answer_view.setMinimumHeight(60)
        self._answer_view.setMaximumHeight(400)
        self._answer_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        if self._loading:
            self._answer_view.setHtml(self._loading_html())
            self._dot_timer = QTimer(self)
            self._dot_timer.timeout.connect(self._animate_dots)
            self._dot_timer.start(400)
        else:
            self._set_answer_html()

        self._layout.addWidget(self._answer_view)
        outer.addWidget(card)

    def _loading_html(self) -> str:
        dots = "." * ((self._dot_count % 3) + 1)
        return (
            f'<div style="font-family: Hiragino Sans; font-size: 13px; color: rgba(0,229,255,0.6);'
            f' padding: 12px 0;">AIが回答を生成中{dots}</div>'
        )

    def _animate_dots(self):
        self._dot_count += 1
        self._answer_view.setHtml(self._loading_html())

    def set_answer(self, answer: str):
        """ローディング状態から回答を表示に切り替え。"""
        self._answer = answer
        self._loading = False
        if hasattr(self, "_dot_timer"):
            self._dot_timer.stop()
        self._ans_title.setText("回答")
        self._copy_btn.show()
        self._set_answer_html()
        self.adjustSize()

    def _set_answer_html(self):
        html = _md_to_html(self._answer)
        self._answer_view.setHtml(
            f'<div style="font-family: Hiragino Sans, sans-serif; font-size: 13px;'
            f' line-height: 1.7; color: rgba(226,232,240,0.88);">{html}</div>'
        )

    def _copy_answer(self):
        try:
            pyperclip.copy(self._answer)
            self._copy_btn.setStyleSheet(
                "QPushButton { background: rgba(0,229,255,0.2); border: none; border-radius: 6px; }"
            )
            QTimer.singleShot(800, lambda: self._copy_btn.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,0.05); border: none; border-radius: 6px; }"
                "QPushButton:hover { background: rgba(0,229,255,0.15); }"
            ))
        except Exception:
            pass

    @staticmethod
    def _font(size: float, bold: bool = False) -> QFont:
        f = QFont("Hiragino Sans")
        f.setPointSizeF(size)
        if bold:
            f.setBold(True)
        return f

    # ─── ドラッグ移動 ───
    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = ev.globalPosition().toPoint() - self.frameGeometry().topLeft()
            ev.accept()

    def mouseMoveEvent(self, ev):
        if self._drag_pos and ev.buttons() & Qt.MouseButton.LeftButton:
            self.move(ev.globalPosition().toPoint() - self._drag_pos)
            ev.accept()

    def mouseReleaseEvent(self, ev):
        self._drag_pos = None

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key.Key_Escape:
            self.close()
