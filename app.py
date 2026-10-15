"""tonix-gpt: локальные чат-боты — Qwen, Gemma, gpt-oss и их huihui-версии.

Модели работают на этом Mac (MLX), в интернет ходят сами — поиск и чтение
страниц, видят приложенные картинки и рисуют (Z-Image Turbo).
"""
import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import QMimeData, QPointF, QRectF, QSettings, QSize, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import (QAction, QColor, QDesktopServices, QDrag, QFont, QGuiApplication, QIcon, QImage,
                           QLinearGradient, QPainter, QPen, QPixmap, QTextOption)
from PySide6.QtWidgets import (QApplication, QDialog, QFileDialog, QFrame, QHBoxLayout, QInputDialog, QLabel,
                               QListWidget, QListWidgetItem, QMenu, QMenuBar, QMessageBox, QPlainTextEdit,
                               QProgressBar, QPushButton, QComboBox, QScrollArea, QSizePolicy, QStyle,
                               QStyledItemDelegate, QTextBrowser, QVBoxLayout, QWidget)

import _style
import catalog
import engine
import i18n
import store
from _style import STYLE
from i18n import t, tf

APP = "tonix-gpt"
TITLE = "tonix-gpt"
AUTHOR = "DrTonix"
SITE = "bdub.space"
URL = "https://bdub.space"
ACCENT = "#7c9cff"
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".heic", ".gif", ".bmp", ".tiff"}

EXTRA = """
QFrame#side { background: #19191c; border: none; }
QListWidget#chats { background: transparent; border: none; }
QFrame#composer { background: #26262a; border: none; border-radius: 16px; }
QPlainTextEdit#input {
    background: transparent; border: none; padding: 2px 4px; color: #e9ebef;
    font-family: "Helvetica Neue", Arial, sans-serif; font-size: 14px;
}
QPushButton#toggle {
    background: transparent; border: none; border-radius: 8px; padding: 5px 10px;
    color: #8a8f98; font-size: 12px;
}
QPushButton#toggle:hover   { color: #e9ebef; background: rgba(255,255,255,0.05); }
QPushButton#toggle:checked { color: #c9d4ff; background: rgba(124,156,255,0.16); }
QPushButton#send {
    background: #7c9cff; color: #1e1e20; border-radius: 10px; padding: 7px 16px;
    font-weight: 600;
}
QPushButton#send:hover    { background: #97b0ff; }
QPushButton#send:disabled { background: rgba(124,156,255,0.28); color: rgba(255,255,255,0.4); }
QPushButton#stop { background: rgba(255,255,255,0.12); border-radius: 10px; padding: 7px 16px; }
QFrame#bubble { background: #2c2c32; border: none; border-radius: 16px; }
QLabel#userText { color: #e9ebef; font-size: 14px; }
QLabel#muted   { color: #8a8f98; font-size: 12px; }
QLabel#faint   { color: #6b6f76; font-size: 12px; }
QLabel#think   { color: #8a8f98; font-size: 12px; }
QPushButton#link {
    background: transparent; border: none; padding: 0; color: #8a8f98; font-size: 12px; text-align: left;
}
QPushButton#link:hover { color: #c9d4ff; }
QPushButton#source {
    background: transparent; border: none; padding: 0 0 0 12px; color: #6b6f76; font-size: 12px; text-align: left;
}
QPushButton#source:hover { color: #c9d4ff; }
QTextBrowser#answer { background: transparent; border: none; color: #e9ebef; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 4px 2px; }
QScrollBar::handle:vertical { background: rgba(255,255,255,0.13); border-radius: 4px; min-height: 36px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0px; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QComboBox#model { min-width: 190px; }
QMenu { background: #2c2c31; border: 1px solid rgba(255,255,255,0.10); border-radius: 9px; padding: 4px; }
QMenu::item { padding: 6px 22px 6px 11px; border-radius: 6px; color: #e9ebef; font-size: 13px; }
QMenu::item:selected { background: #7c9cff; color: #1e1e20; }
QMenu::item:disabled { color: #6b6f76; }
"""

# Оформление ответа: Qt понимает урезанный CSS — только то, что ниже.
ANSWER_CSS = """
body { color: #e9ebef; font-family: 'Helvetica Neue'; font-size: 14px; }
p { margin: 0 0 8px 0; }
a { color: #a9bcff; text-decoration: none; }
code { font-family: Menlo; font-size: 12px; background-color: #1a1a1d; }
pre { font-family: Menlo; font-size: 12px; background-color: #1a1a1d; padding: 8px; margin: 4px 0 10px 0; }
h1, h2, h3, h4 { color: #f4f5f7; margin: 10px 0 6px 0; }
h1 { font-size: 19px; } h2 { font-size: 17px; } h3 { font-size: 15px; } h4 { font-size: 14px; }
table { border-collapse: collapse; margin: 4px 0 10px 0; }
th { background-color: #26262a; font-weight: 600; padding: 4px 8px; }
td { padding: 4px 8px; border-top: 1px solid #333338; }
blockquote { color: #a8adb6; margin: 4px 0 8px 12px; }
li { margin: 2px 0; }
"""


THEMES = ("system", "light", "dark")


def theme():
    name = QSettings("local", i18n.SETTINGS).value("theme", "system")
    return name if name in THEMES else "system"


def skin():
    name = theme()
    if name != "system":
        return name
    return "dark" if QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark else "light"


def themed(css):
    return _style.light(css) if skin() == "light" else css


def tone(hex_, alpha=255):
    c = QColor(_style.light_hex(hex_) if skin() == "light" else hex_)
    c.setAlpha(alpha)
    return c


def ink(alpha):
    """Полупрозрачная заливка: белая на тёмном, чёрная на светлом."""
    return QColor(0, 0, 0, int(alpha * 0.8)) if skin() == "light" else QColor(255, 255, 255, alpha)


def _no_raw_html(text):
    """Сырой HTML из ответа — как текст: модель повторяет то, что прочла на
    странице, а <img src="file:///…"> QTextBrowser послушно грузит с диска.
    Код в обратных кавычках не трогаем — его markdown экранирует сам."""
    import re
    out = []
    for i, chunk in enumerate(re.split(r"(```.*?```)", text or "", flags=re.S)):
        if i % 2 == 0:
            pieces = re.split(r"(`[^`\n]+`)", chunk)
            chunk = "".join(x if j % 2 else x.replace("&", "&amp;").replace("<", "&lt;")
                            for j, x in enumerate(pieces))
        out.append(chunk)
    return "".join(out)


def open_link(url):
    """Открываются только веб-адреса: file:///…/что-то.app по щелчку
    запустил бы программу."""
    url = QUrl(url) if isinstance(url, str) else url
    if url.scheme().lower() in ("http", "https", "mailto"):
        QDesktopServices.openUrl(url)


def md_html(text):
    import markdown
    body = markdown.markdown(_no_raw_html(text), extensions=["fenced_code", "tables", "sane_lists", "nl2br"])
    return f"<style>{themed(ANSWER_CSS)}</style>{body}"


def app_icon():
    here = Path(__file__).resolve().parent
    for p in (here.parent / "AppIcon.icns", here / "icon" / "AppIcon.icns"):
        if p.exists():
            return QIcon(str(p))
    return QIcon()


def reveal(path):
    import subprocess
    subprocess.run(["open", "-R", str(path)])


class Turn(QThread):
    """Один ответ модели со всеми вызовами инструментов."""
    event = Signal(str, object)
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, server, chat, model, web, draw):
        super().__init__()
        self.setStackSize(64 * 1024 * 1024)
        self.server, self.chat, self.model, self.web, self.draw = server, chat, model, web, draw
        self.stop = False

    def run(self):
        try:
            rec = engine.run_turn(self.server, self.chat, self.model, self.web, self.draw,
                                  lambda k, d: self.event.emit(k, d), lambda: self.stop)
            self.done.emit(rec)
        except Exception as e:
            msg = str(e) or type(e).__name__
            if "Connection refused" in msg or "Remote end closed" in msg:
                msg = t("сервер моделей остановился — подробности в server.log")
            self.failed.emit(msg[:400])


class Warmup(QThread):
    """Модель грузится, пока человек печатает: первый ответ — без ожидания."""

    def __init__(self, server, model):
        super().__init__()
        self.server, self.model = server, model

    def run(self):
        try:
            path = engine.model_path(self.model)
            body = {"model": path, "stream": True, "max_tokens": 1,
                    "messages": [{"role": "user", "content": "."}]}
            for _ in self.server.stream(body):
                pass
            engine._loaded["repo"] = path
        except Exception:
            pass


class Answer(QTextBrowser):
    """Текст ответа: Markdown, высота — по содержимому, ссылки — в браузер."""

    def __init__(self):
        super().__init__()
        self.setObjectName("answer")
        self.setOpenLinks(False)
        self.anchorClicked.connect(open_link)
        self.setFrameShape(QFrame.NoFrame)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.document().setDocumentMargin(0)
        self.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.text = ""

    def set_text(self, text):
        self.text = text
        self.setHtml(md_html(text))
        self._fit()

    def _fit(self):
        self.document().setTextWidth(max(self.viewport().width(), 100))
        self.setFixedHeight(int(self.document().size().height()) + 4)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._fit()


class Picture(QLabel):
    """Картинка в чате: щелчок — открыть, правый — меню, тянуть — файл наружу."""

    def __init__(self, path, width=380):
        super().__init__()
        self.path = Path(path)
        pix = QPixmap(str(path))
        if not pix.isNull():
            ratio = self.devicePixelRatioF() or 2.0
            scaled = pix.scaledToWidth(int(min(width, pix.width()) * ratio), Qt.SmoothTransformation)
            scaled.setDevicePixelRatio(ratio)
            self.setPixmap(scaled)
        self.setCursor(Qt.PointingHandCursor)
        self.press = None

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton:
            menu = QMenu(self)
            menu.addAction(t("Открыть"), lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.path))))
            menu.addAction(t("Показать в Finder"), lambda: reveal(self.path))
            menu.addAction(t("Сохранить как…"), self._save)
            menu.exec(e.globalPosition().toPoint())
        else:
            self.press = e.position()

    def mouseMoveEvent(self, e):
        if self.press is not None and (e.position() - self.press).manhattanLength() > 8:
            self.press = None
            mime = QMimeData()
            mime.setUrls([QUrl.fromLocalFile(str(self.path))])
            drag = QDrag(self)
            drag.setMimeData(mime)
            if self.pixmap():
                drag.setPixmap(self.pixmap().scaledToWidth(120 * 2, Qt.SmoothTransformation))
            drag.exec(Qt.CopyAction)

    def mouseReleaseEvent(self, e):
        if self.press is not None and e.button() == Qt.LeftButton:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.path)))
        self.press = None

    def _save(self):
        dst, _ = QFileDialog.getSaveFileName(self, t("Сохранить"), str(Path.home() / "Downloads" / self.path.name))
        if dst:
            import shutil
            shutil.copy2(self.path, dst)


class UserMessage(QWidget):
    def __init__(self, msg):
        super().__init__()
        row = QHBoxLayout(self)
        row.setContentsMargins(80, 0, 0, 0)
        row.addStretch()
        bubble = QFrame()
        bubble.setObjectName("bubble")
        v = QVBoxLayout(bubble)
        v.setContentsMargins(14, 10, 14, 10)
        v.setSpacing(8)
        for p in msg.get("images", []):
            if Path(p).exists():
                v.addWidget(Picture(p, 240))
        if msg.get("text"):
            lab = QLabel(msg["text"])
            lab.setObjectName("userText")
            lab.setWordWrap(True)
            lab.setTextInteractionFlags(Qt.TextSelectableByMouse)
            v.addWidget(lab)
        row.addWidget(bubble)


class ToolRow(QWidget):
    """Шаг инструмента: что делается, ход, найденные ссылки или картинка."""

    def __init__(self, part=None):
        super().__init__()
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(0, 0, 0, 0)
        self.v.setSpacing(3)
        self.line = QLabel("")
        self.line.setObjectName("muted")
        self.v.addWidget(self.line)
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(4)
        self.bar.setFixedWidth(260)
        self.bar.setVisible(False)
        self.v.addWidget(self.bar)
        if part:
            self.finish(part)

    def start(self, name, args):
        what = {"web_search": tf("Поиск: «{q}»", q=args.get("query", "")),
                "open_url": t("Страница: ") + str(args.get("url", "")).split("//")[-1].split("/")[0],
                "generate_image": t("Рисунок")}.get(name, name)
        self.line.setText(what + "…")

    def progress(self, text, share):
        self.line.setText(text)
        self.bar.setVisible(True)
        if share is None:
            self.bar.setRange(0, 0)
        else:
            self.bar.setRange(0, 100)
            self.bar.setValue(int(share * 100))

    def finish(self, part):
        self.bar.setVisible(False)
        text = part.get("summary") or part.get("name", "")
        if part.get("error"):
            text += tf(" — не вышло: {e}", e=part["error"])
        self.line.setText(text)
        for link in part.get("links", [])[:4]:
            b = QPushButton(link.get("title") or link["url"])
            b.setObjectName("source")
            b.setCursor(Qt.PointingHandCursor)
            b.setToolTip(link["url"])
            b.clicked.connect(lambda _=False, u=link["url"]: open_link(u))
            self.v.addWidget(b)
        for p in part.get("images", []):
            if Path(p).exists():
                pic = Picture(p, 420)
                if part.get("prompt"):
                    pic.setToolTip(part["prompt"])
                self.v.addWidget(pic)


class Thinking(QWidget):
    """Размышления модели: свёрнуты, по щелчку — текст."""

    def __init__(self, text=""):
        super().__init__()
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        self.head = QPushButton(t("Размышления"))
        self.head.setObjectName("link")
        self.head.setCursor(Qt.PointingHandCursor)
        self.head.clicked.connect(self._toggle)
        v.addWidget(self.head)
        self.body = QLabel(text)
        self.body.setObjectName("think")
        self.body.setWordWrap(True)
        self.body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.body.setVisible(False)
        v.addWidget(self.body)

    def add(self, chunk):
        self.body.setText(self.body.text() + chunk)

    def _toggle(self):
        self.body.setVisible(not self.body.isVisible())


class AssistantMessage(QWidget):
    """Ответ: размышления, шаги инструментов, текст — в том порядке, как шли."""

    def __init__(self, title, rec=None):
        super().__init__()
        self.v = QVBoxLayout(self)
        self.v.setContentsMargins(0, 0, 80, 0)
        self.v.setSpacing(8)
        self.head = QLabel(title)
        self.head.setObjectName("faint")
        self.v.addWidget(self.head)
        self.status = QLabel("")
        self.status.setObjectName("muted")
        self.status.setVisible(False)
        self.v.addWidget(self.status)
        self.answer = None
        self.thinking = None
        self.tool = None
        if rec:
            for part in rec.get("parts", []):
                if part["kind"] == "reasoning":
                    self.v.addWidget(Thinking(part["text"]))
                elif part["kind"] == "tool":
                    self.v.addWidget(ToolRow(part))
                elif part["kind"] == "text":
                    a = Answer()
                    a.set_text(part["text"])
                    self.v.addWidget(a)
            if rec.get("error"):
                err = QLabel(t("Не вышло: ") + rec["error"])
                err.setObjectName("muted")
                err.setWordWrap(True)
                self.v.addWidget(err)

    # поток событий от модели
    def on_event(self, kind, data):
        if kind == "status":
            self.status.setText(data)
            self.status.setVisible(True)
            self.answer = None
            self.thinking = None
        elif kind == "reasoning":
            self.status.setVisible(False)
            if self.thinking is None:
                self.thinking = Thinking()
                self.v.addWidget(self.thinking)
            self.thinking.add(data)
        elif kind == "text":
            self.status.setVisible(False)
            if self.answer is None:
                self.answer = Answer()
                self.v.addWidget(self.answer)
            self.answer.text += data
            self.answer.pending = True
        elif kind == "replace" and self.answer is not None:
            self.answer.text = data
            self.answer.pending = True
        elif kind == "tool_start":
            self.status.setVisible(False)
            self.tool = ToolRow()
            self.tool.start(data["name"], data["args"])
            self.v.addWidget(self.tool)
            self.answer = None
            self.thinking = None
        elif kind == "tool_progress" and self.tool is not None:
            self.tool.progress(*data)
        elif kind == "tool_done" and self.tool is not None:
            self.tool.finish(data)
            self.tool = None

    def flush(self):
        """Текст перерисовывается не на каждый кусок, а по таймеру."""
        if self.answer is not None and getattr(self.answer, "pending", False):
            self.answer.pending = False
            self.answer.set_text(self.answer.text)

    def fail(self, text):
        self.status.setText(t("Не вышло: ") + text)
        self.status.setWordWrap(True)
        self.status.setVisible(True)


class Attachment(QWidget):
    """Приложенная картинка до отправки; крестик в углу — убрать."""
    removed = Signal(str)

    def __init__(self, path):
        super().__init__()
        self.path = path
        self.setFixedSize(60, 60)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(t("Убрать"))
        pix = QPixmap(path)
        self.pix = pix.scaled(120, 120, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation) if not pix.isNull() else None
        self.hover = False

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        if self.pix:
            p.save()
            from PySide6.QtGui import QPainterPath
            clip = QPainterPath()
            clip.addRoundedRect(r, 10, 10)
            p.setClipPath(clip)
            src = QRectF((self.pix.width() - 120) / 2, (self.pix.height() - 120) / 2, 120, 120)
            p.drawPixmap(r, self.pix, src)
            p.restore()
        if self.hover:
            p.setBrush(QColor(0, 0, 0, 150))
            p.setPen(Qt.NoPen)
            p.drawRoundedRect(r, 10, 10)
            p.setPen(QPen(QColor("#ffffff"), 2))
            c = r.center()
            p.drawLine(QPointF(c.x() - 7, c.y() - 7), QPointF(c.x() + 7, c.y() + 7))
            p.drawLine(QPointF(c.x() - 7, c.y() + 7), QPointF(c.x() + 7, c.y() - 7))

    def enterEvent(self, e):
        self.hover = True
        self.update()

    def leaveEvent(self, e):
        self.hover = False
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.removed.emit(self.path)


class Input(QPlainTextEdit):
    """Поле сообщения: Enter — отправить, Shift+Enter — новая строка,
    картинка из буфера обмена — во вложения."""
    send = Signal()
    image = Signal(QImage)

    def __init__(self):
        super().__init__()
        self.setObjectName("input")
        self.setPlaceholderText(t("Сообщение"))
        self.setTabChangesFocus(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.document().contentsChanged.connect(self._grow)
        self._grow()

    def _grow(self):
        # Растёт до десяти строк, дальше — прокрутка.
        lines = max(1, int(self.document().size().height()))
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded if lines > 10 else Qt.ScrollBarAlwaysOff)
        self.setFixedHeight(min(lines, 10) * self.fontMetrics().lineSpacing() + 16)

    def keyPressEvent(self, e):
        if e.key() in (Qt.Key_Return, Qt.Key_Enter) and not (e.modifiers() & Qt.ShiftModifier):
            self.send.emit()
            return
        super().keyPressEvent(e)

    def canInsertFromMimeData(self, source):
        return source.hasImage() or super().canInsertFromMimeData(source)

    def insertFromMimeData(self, source):
        if source.hasImage() and not source.hasUrls():
            self.image.emit(QImage(source.imageData()))
            return
        if source.hasUrls() and all(Path(u.toLocalFile()).suffix.lower() in IMAGE_EXT for u in source.urls()):
            for u in source.urls():
                self.window().attach(u.toLocalFile())
            return
        super().insertFromMimeData(source)


class ChatDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 44)

    def paint(self, p, option, index):
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(option.rect).adjusted(6, 2, -6, -2)
        if option.state & QStyle.State_Selected:
            p.setPen(Qt.NoPen)
            p.setBrush(ink(22))
            p.drawRoundedRect(r, 9, 9)
        elif option.state & QStyle.State_MouseOver:
            p.setPen(Qt.NoPen)
            p.setBrush(ink(10))
            p.drawRoundedRect(r, 9, 9)
        f = QFont(option.font)
        f.setPixelSize(13)
        p.setFont(f)
        p.setPen(tone("#e9ebef"))
        width = int(r.width() - 20)
        title = p.fontMetrics().elidedText(index.data(Qt.DisplayRole) or t("Новый чат"), Qt.ElideRight, width)
        p.drawText(QRectF(r.left() + 10, r.top() + 5, width, 18), Qt.AlignVCenter, title)
        f.setPixelSize(11)
        p.setFont(f)
        p.setPen(tone("#75797f"))
        p.drawText(QRectF(r.left() + 10, r.top() + 22, width, 14), Qt.AlignVCenter, index.data(Qt.UserRole + 1) or "")
        p.restore()


class ChatList(QListWidget):
    """Края гаснут, когда есть что прокрутить."""

    def paintEvent(self, e):
        super().paintEvent(e)
        bar = self.verticalScrollBar()
        p = QPainter(self.viewport())
        w, h = self.viewport().width(), self.viewport().height()
        for show, y0, y1 in ((bar.value() > 0, 0, 24), (bar.value() < bar.maximum(), h, h - 24)):
            if show:
                g = QLinearGradient(0, y0, 0, y1)
                g.setColorAt(0, tone("#19191c"))
                g.setColorAt(1, tone("#19191c", 0))
                p.fillRect(QRectF(0, min(y0, y1), w, 24), g)


class SettingsDialog(QDialog):
    changed = Signal()
    restyled = Signal()
    relang = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("root")
        self.setMinimumWidth(640)
        self.resize(640, 720)
        self.outer = QVBoxLayout(self)
        self.outer.setContentsMargins(0, 0, 0, 0)
        self.body = None
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.refresh)
        self.restyle()
        self._build()
        self.timer.start()

    def restyle(self):
        self.setStyleSheet(themed(STYLE + EXTRA + "QDialog#root { background: #1e1e20; }"))

    def _card(self, v, title, note=""):
        card = QFrame()
        card.setObjectName("card")
        h = QHBoxLayout(card)
        h.setContentsMargins(16, 12, 14, 12)
        h.setSpacing(10)
        tv = QVBoxLayout()
        tv.setSpacing(2)
        cap = QLabel(title)
        cap.setObjectName("cardName")
        tv.addWidget(cap)
        if note:
            sub = QLabel(note)
            sub.setObjectName("faint")
            tv.addWidget(sub)
        h.addLayout(tv, 1)
        v.addWidget(card)
        return h, tv

    def _build(self):
        if self.body is not None:
            self.body.deleteLater()
        self.setWindowTitle(t("Настройки"))
        # Своя прокрутка: моделей десяток, и на экране ноутбука окно не помещалось.
        self.body = QScrollArea()
        self.body.setWidgetResizable(True)
        self.body.setFrameShape(QFrame.NoFrame)
        self.body.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        inner = QWidget()
        self.body.setWidget(inner)
        self.outer.addWidget(self.body)
        v = QVBoxLayout(inner)
        v.setContentsMargins(20, 18, 20, 18)
        v.setSpacing(10)

        def section(text):
            if v.count():
                v.addSpacing(8)
            lab = QLabel(t(text))
            lab.setObjectName("section")
            v.addWidget(lab)

        section("Модели")
        h, tv = self._card(v, t("Папка для моделей"), t("Куда ставятся новые модели"))
        # Путь — справа, как у моделей ниже.
        self.place = QLabel("")
        self.place.setObjectName("muted")
        h.addWidget(self.place)
        self.inside = QPushButton(t("Сбросить"))
        self.inside.setObjectName("cardbtn")
        self.inside.setCursor(Qt.PointingHandCursor)
        self.inside.clicked.connect(lambda: self._set_folder(None))
        h.addWidget(self.inside)
        pick = QPushButton(t("Выбрать папку…"))
        pick.setObjectName("cardbtn")
        pick.setCursor(Qt.PointingHandCursor)
        pick.clicked.connect(self._pick_folder)
        h.addWidget(pick)

        self.rows = {}
        for m in catalog.MODELS:
            card = QFrame()
            card.setObjectName("card")
            h = QHBoxLayout(card)
            h.setContentsMargins(16, 12, 14, 12)
            h.setSpacing(12)
            text = QVBoxLayout()
            text.setSpacing(2)
            name = QLabel(m.title)
            name.setObjectName("cardName")
            text.addWidget(name)
            size = QLabel(f"{m.size_gb:g} " + t("ГБ"))
            size.setObjectName("muted")
            text.addWidget(size)
            bar = QProgressBar()
            bar.setTextVisible(False)
            bar.setFixedHeight(4)
            bar.setVisible(False)
            text.addWidget(bar)
            h.addLayout(text, 1)
            state = QLabel("")
            state.setObjectName("muted")
            h.addWidget(state)
            btn = QPushButton("")
            btn.setObjectName("cardbtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, k=m.key: self._act(k))
            h.addWidget(btn)
            v.addWidget(card)
            self.rows[m.key] = (state, btn, bar)
        section("Приложение")
        h, _ = self._card(v, t("Язык"))
        for code, label in (("ru", "Русский"), ("en", "English")):
            b = QPushButton(label)
            b.setObjectName("cardbtnAccent" if code == i18n.current() else "cardbtn")
            b.setEnabled(code != i18n.current())
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, c=code: self._set_lang(c))
            h.addWidget(b)

        h, _ = self._card(v, t("Оформление"))
        seg = QFrame()
        seg.setObjectName("segment")
        sl = QHBoxLayout(seg)
        sl.setContentsMargins(3, 3, 3, 3)
        sl.setSpacing(3)
        for name, label in zip(THEMES, (t("Как в системе"), t("Светлое"), t("Тёмное"))):
            b = QPushButton(label)
            b.setObjectName("seg")
            b.setCheckable(True)
            b.setAutoExclusive(True)
            b.setChecked(name == theme())
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, n=name: self._set_theme(n))
            sl.addWidget(b)
        h.addWidget(seg)

        v.addSpacing(8)
        self._support_card(v)
        self.refresh()

    def _support_card(self, v):
        """Поддержать: ссылки и кошелёк кнопками; «USDT TRC-20» копирует адрес."""
        import support
        h, _ = self._card(v, t("Поддержать"))
        for b in support.link_buttons(t("Скопировано")):
            h.addWidget(b)

    def _set_lang(self, code):
        i18n.set_current(code)
        self._build()
        self.relang.emit()

    def _set_theme(self, name):
        QSettings("local", i18n.SETTINGS).setValue("theme", name)
        self.restyle()
        self.restyled.emit()

    def _pick_folder(self):
        start = str(catalog.folder() or Path.home())
        path = QFileDialog.getExistingDirectory(self, t("Папка для моделей"), start)
        if path:
            self._set_folder(path)

    def _set_folder(self, path):
        catalog.set_folder(path)
        self.refresh()
        self.changed.emit()

    def refresh(self):
        base = catalog.folder()
        off = "" if base is None or catalog.mounted(base) else t(" — недоступна")
        self.place.setText(catalog.home.label(base) + off)
        self.inside.setVisible(base is not None)
        for m in catalog.MODELS:
            state, btn, bar = self.rows[m.key]
            st = catalog.state(m)
            if st == "downloading":
                p = catalog.home.progress(m.repo)
                state.setText(catalog.home.describe(m.repo))
                bar.setVisible(True)
                bar.setRange(0, 1000)
                bar.setValue(int((p[0] if p else 0) * 1000))
                btn.setText(t("Остановить"))
                btn.setObjectName("cardbtn")
                btn.setEnabled(True)
            elif st == "queued":
                state.setText(catalog.home.describe(m.repo))
                bar.setVisible(False)
                btn.setText(t("Убрать"))
                btn.setObjectName("cardbtn")
                btn.setEnabled(True)
            elif st == "ready":
                state.setText(catalog.where(m))
                bar.setVisible(False)
                btn.setText(t("Удалить"))
                btn.setObjectName("cardbtn")
                btn.setEnabled(True)
            elif st == "offline":
                state.setText(tf("Папка недоступна: {where}", where=catalog.where(m)))
                bar.setVisible(False)
                btn.setText(t("Удалить"))
                btn.setObjectName("cardbtn")
                btn.setEnabled(False)
            else:
                err = catalog.home.describe(m.repo)
                have = catalog.downloaded_bytes(m)
                state.setText(err or (tf("скачано {gb} ГБ · {where}", gb=f"{have / 1e9:.1f}", where=catalog.where(m))
                                      if st == "partial" else
                                      tf("установится в {where}", where=catalog.where(m))))
                bar.setVisible(False)
                btn.setText(t("Докачать") if st == "partial" else t("Скачать"))
                btn.setObjectName("cardbtnAccent")
                where = catalog.target(m)
                btn.setEnabled(where is None or catalog.mounted(where))
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _act(self, key):
        m = catalog.BY_KEY[key]
        st = catalog.state(m)
        if st in ("downloading", "queued"):
            catalog.cancel(m)
        elif st == "ready":
            box = QMessageBox(self)
            box.setText(tf("Удалить {name}?", name=m.title))
            shared = t(" Она в общем кэше — другим приложениям, которые ею пользуются, придётся скачать её заново.") \
                if catalog.shared(m) else ""
            box.setInformativeText(tf("Освободится {gb} ГБ.", gb=f"{m.size_gb:g}") + shared)
            yes = box.addButton(t("Удалить"), QMessageBox.DestructiveRole)
            box.addButton(t("Отмена"), QMessageBox.RejectRole)
            box.exec()
            if box.clickedButton() is yes:
                catalog.remove(m)
                self.changed.emit()
        else:
            where = None
            if st != "partial":           # докачивается туда, где начата
                where = self._install_place(self.rows[key][1], m)
                if where is False:
                    return
            try:
                catalog.download(m, where)
            except Exception as e:
                QMessageBox.warning(self, t("Настройки"), str(e))
        self.refresh()

    def _install_place(self, anchor, m):
        """Куда ставить модель: в папку по умолчанию или в свою. False — передумали."""
        menu = QMenu(self)
        default = menu.addAction(tf("В {where}", where=catalog.where(m)))
        other = menu.addAction(t("В другую папку…"))
        chosen = menu.exec(anchor.mapToGlobal(anchor.rect().bottomLeft()))
        if chosen is default:
            return None
        if chosen is other:
            path = QFileDialog.getExistingDirectory(self, t("Папка для модели"),
                                                    str(catalog.folder() or Path.home()))
            return path or False
        return False


class Window(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("root")
        self.setWindowTitle(TITLE)
        self.setAcceptDrops(True)
        self.settings = QSettings("local", os.environ.get("TONIX_GPT_SETTINGS", APP))
        g = self.settings.value("geometry")
        if g is not None:
            self.restoreGeometry(g)
        else:
            self.resize(1160, 800)
        self.setMinimumSize(860, 560)
        self.server = engine.Server()
        self.chats = store.load_all()
        self.chat = None
        self.turn = None
        self.alive = set()
        self.attached = []
        self.current = None          # AssistantMessage, в который идёт ответ
        self.warm = None
        self.started = 0.0

        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        side = QFrame()
        side.setObjectName("side")
        side.setFixedWidth(250)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(12, 16, 12, 12)
        sv.setSpacing(10)
        new = QPushButton(t("Новый чат"))
        new.setObjectName("cardbtnAccent")
        new.setCursor(Qt.PointingHandCursor)
        new.clicked.connect(self.new_chat)
        sv.addWidget(new)
        self.list = ChatList()
        self.list.setObjectName("chats")
        self.list.setItemDelegate(ChatDelegate())
        self.list.setMouseTracking(True)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._chat_menu)
        self.list.itemClicked.connect(lambda it: self.open_chat(it.data(Qt.UserRole)))
        sv.addWidget(self.list, 1)
        prefs = QPushButton(t("Настройки"))
        prefs.setObjectName("cardbtn")
        prefs.setCursor(Qt.PointingHandCursor)
        prefs.clicked.connect(self.show_settings)
        sv.addWidget(prefs)
        outer.addWidget(side)

        main = QVBoxLayout()
        main.setContentsMargins(24, 14, 24, 18)
        main.setSpacing(12)
        top = QHBoxLayout()
        self.model_box = QComboBox()
        self.model_box.setObjectName("model")
        self.model_box.currentIndexChanged.connect(self._model_chosen)
        top.addWidget(self.model_box)
        top.addStretch()
        main.addLayout(top)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        host = QWidget()
        self.feed = QVBoxLayout(host)
        self.feed.setContentsMargins(0, 8, 8, 8)
        self.feed.setSpacing(18)
        self.feed.addStretch(1)
        self.scroll.setWidget(host)
        self.scroll.verticalScrollBar().rangeChanged.connect(self._follow)
        self.follow = True
        self.scroll.verticalScrollBar().valueChanged.connect(self._scrolled)
        main.addWidget(self.scroll, 1)

        composer = QFrame()
        composer.setObjectName("composer")
        cv = QVBoxLayout(composer)
        cv.setContentsMargins(14, 12, 14, 10)
        cv.setSpacing(8)
        self.thumbs = QHBoxLayout()
        self.thumbs.setSpacing(8)
        self.thumbs.addStretch()
        self.thumbs_box = QWidget()
        self.thumbs_box.setLayout(self.thumbs)
        self.thumbs_box.setVisible(False)
        cv.addWidget(self.thumbs_box)
        self.input = Input()
        self.input.send.connect(self.send)
        self.input.image.connect(self._paste_image)
        self.input.textChanged.connect(self._typing)
        cv.addWidget(self.input)
        row = QHBoxLayout()
        row.setSpacing(4)
        self.pic_btn = self._toggle(t("Картинка"), False)
        self.pic_btn.setCheckable(False)
        self.pic_btn.clicked.connect(self.choose_images)
        row.addWidget(self.pic_btn)
        self.web_btn = self._toggle(t("Интернет"), self.settings.value("web", True, type=bool))
        self.web_btn.toggled.connect(lambda on: self.settings.setValue("web", on))
        self.web_btn.setToolTip(t("Модель сама ищет и читает страницы, когда нужны свежие данные"))
        row.addWidget(self.web_btn)
        self.draw_btn = self._toggle(t("Рисование"), self.settings.value("draw", True, type=bool))
        self.draw_btn.toggled.connect(lambda on: self.settings.setValue("draw", on))
        self.draw_btn.setToolTip(t("Модель рисует, когда просят: Z-Image Turbo, около 30 с на картинку"))
        row.addWidget(self.draw_btn)
        self.think_btn = self._toggle(t("Размышления"), False)
        self.think_btn.toggled.connect(self._think)
        self.think_btn.setToolTip(t("Прежде чем ответить, модель рассуждает: точнее, но дольше"))
        row.addWidget(self.think_btn)
        row.addStretch()
        self.send_btn = QPushButton(t("Отправить"))
        self.send_btn.setObjectName("send")
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self.send)
        row.addWidget(self.send_btn)
        cv.addLayout(row)
        main.addWidget(composer)
        outer.addLayout(main, 1)

        self.ticker = QTimer(self)
        self.ticker.setInterval(80)
        self.ticker.timeout.connect(self._tick)
        self._build_menu()
        self.apply_theme()
        # macOS переключает оформление на ходу — окно идёт следом.
        QGuiApplication.styleHints().colorSchemeChanged.connect(lambda _s: self.apply_theme())
        self._fill_models()
        self._fill_list()
        if self.chats:
            self.open_chat(self.chats[0]["id"])
        else:
            self.new_chat()

    def _toggle(self, text, on):
        b = QPushButton(text)
        b.setObjectName("toggle")
        b.setCheckable(True)
        b.setChecked(on)
        b.setCursor(Qt.PointingHandCursor)
        b.setFocusPolicy(Qt.NoFocus)
        return b

    def _follow(self, lo, hi):
        if self.follow:
            self.scroll.verticalScrollBar().setValue(hi)

    def _scrolled(self, value):
        bar = self.scroll.verticalScrollBar()
        self.follow = value >= bar.maximum() - 40

    def _fill_models(self):
        keep = self.model_box.currentData() or (self.chat or {}).get("model") or self.settings.value("model", "qwen")
        self.model_box.blockSignals(True)
        self.model_box.clear()
        for m in catalog.MODELS:
            if m.kind == "chat" and catalog.installed(m):
                self.model_box.addItem(m.title, m.key)
        if self.model_box.count() == 0:
            self.model_box.addItem(t("Нет скачанных моделей"), None)
        i = self.model_box.findData(keep)
        self.model_box.setCurrentIndex(max(i, 0))
        self.model_box.blockSignals(False)
        self._model_chosen()

    def _model(self):
        key = self.model_box.currentData()
        return catalog.BY_KEY.get(key) if key else None

    def _model_chosen(self, *_):
        m = self._model()
        if m is None:
            self.send_btn.setEnabled(False)
            return
        self.send_btn.setEnabled(self.turn is None)
        self.settings.setValue("model", m.key)
        if self.chat is not None and self.chat.get("model") != m.key:
            self.chat["model"] = m.key
            if self.chat["messages"]:
                store.save(self.chat)
        self.warm = None

    def _typing(self):
        # Модель грузится, пока человек печатает.
        m = self._model()
        if m is None or self.turn is not None or self.warm is not None or not self.input.toPlainText().strip():
            return
        if engine._loaded["repo"] == str(catalog.local_path(m)) and self.server.alive():
            return
        self.warm = Warmup(self.server, m)
        self.alive.add(self.warm)
        self.warm.finished.connect(lambda w=self.warm: self.alive.discard(w))
        self.warm.start()

    def show_settings(self):
        dlg = SettingsDialog(self)
        dlg.changed.connect(self._fill_models)
        dlg.restyled.connect(self.apply_theme)
        dlg.relang.connect(self.retranslate)
        QGuiApplication.styleHints().colorSchemeChanged.connect(dlg.restyle)
        dlg.exec()
        QGuiApplication.styleHints().colorSchemeChanged.disconnect(dlg.restyle)
        self._fill_models()

    def apply_theme(self):
        self.setStyleSheet(themed(STYLE + EXTRA))
        self.list.viewport().update()
        if self.turn is None and self.chat is not None:
            self._render()
        else:
            for a in self.findChildren(Answer):
                a.set_text(a.text)

    def retranslate(self):
        """Перевод собранного окна: ключ ищется по видимой надписи."""
        self.about_act.setText(tf("О программе {name}", name=TITLE))
        for w in self.findChildren(QWidget):
            for get, put in (("text", "setText"), ("toolTip", "setToolTip"), ("placeholderText", "setPlaceholderText")):
                if not (hasattr(w, get) and hasattr(w, put)):
                    continue
                try:
                    cur = getattr(w, get)()
                except TypeError:
                    continue
                key = i18n.key_of(cur) if isinstance(cur, str) and cur else None
                if key:
                    getattr(w, put)(t(key))
        self._fill_models()
        self._fill_list()

    def _fill_list(self):
        self.list.blockSignals(True)
        keep = self.list.verticalScrollBar().value()
        self.list.clear()
        for c in self.chats:
            if not c["messages"] and c is not self.chat:
                continue
            it = QListWidgetItem(c.get("title") or t("Новый чат"))
            it.setData(Qt.UserRole, c["id"])
            when = time.localtime(c.get("updated", c["created"]))
            m = catalog.BY_KEY.get(c.get("model"))
            it.setData(Qt.UserRole + 1, time.strftime("%d.%m %H:%M", when) + (f" · {m.title}" if m else ""))
            self.list.addItem(it)
            if self.chat is not None and c["id"] == self.chat["id"]:
                it.setSelected(True)
        self.list.verticalScrollBar().setValue(keep)
        self.list.blockSignals(False)

    def new_chat(self):
        if self.chat is not None and not self.chat["messages"]:
            return
        m = self._model()
        self.chat = store.new_chat(m.key if m else self.settings.value("model", "qwen"))
        self.chats.insert(0, self.chat)
        self._render()
        self._fill_list()
        self.input.setFocus()

    def open_chat(self, chat_id):
        chat = next((c for c in self.chats if c["id"] == chat_id), None)
        if chat is None or chat is self.chat:
            return
        if self.chat is not None and not self.chat["messages"] and self.chat in self.chats:
            self.chats.remove(self.chat)
        self.chat = chat
        i = self.model_box.findData(chat.get("model"))
        if i >= 0:
            self.model_box.setCurrentIndex(i)
        self.think_btn.blockSignals(True)
        self.think_btn.setChecked(bool(chat.get("think")))
        self.think_btn.blockSignals(False)
        self._render()
        self._fill_list()

    def _render(self):
        while self.feed.count() > 1:
            item = self.feed.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        self.current = None
        for msg in self.chat["messages"]:
            self._add_message(msg)
        self.follow = True

    def _add_message(self, msg):
        if msg["role"] == "user":
            w = UserMessage(msg)
        else:
            m = catalog.BY_KEY.get(msg.get("model"))
            w = AssistantMessage(m.title if m else "", msg)
        self.feed.addWidget(w)
        return w

    def _chat_menu(self, pos):
        it = self.list.itemAt(pos)
        if it is None:
            return
        chat = next((c for c in self.chats if c["id"] == it.data(Qt.UserRole)), None)
        if chat is None:
            return
        menu = QMenu(self)
        menu.addAction(t("Переименовать"), lambda: self._rename(chat))
        act = menu.addAction(t("Удалить"), lambda: self._delete(chat))
        act.setEnabled(not (self.turn is not None and chat is self.chat))
        menu.exec(self.list.viewport().mapToGlobal(pos))

    def _rename(self, chat):
        text, ok = QInputDialog.getText(self, t("Переименовать"), t("Название"), text=chat.get("title", ""))
        if ok and text.strip():
            chat["title"] = text.strip()
            store.save(chat)
            self._fill_list()

    def _delete(self, chat):
        box = QMessageBox(self)
        box.setText(tf("Удалить чат «{title}»?", title=chat.get("title") or t("Новый чат")))
        yes = box.addButton(t("Удалить"), QMessageBox.DestructiveRole)
        box.addButton(t("Отмена"), QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is not yes:
            return
        store.delete(chat)
        self.chats.remove(chat)
        if chat is self.chat:
            self.chat = None
            if self.chats:
                self.open_chat(self.chats[0]["id"])
            else:
                self.new_chat()
        self._fill_list()

    def _think(self, on):
        if self.chat is not None:
            self.chat["think"] = on
            if self.chat["messages"]:
                store.save(self.chat)

    def choose_images(self):
        paths, _ = QFileDialog.getOpenFileNames(self, t("Картинки"), str(self.settings.value("dir", str(Path.home()))),
                                                t("Картинки") + " (" + " ".join("*" + e for e in sorted(IMAGE_EXT)) + ")")
        if paths:
            self.settings.setValue("dir", str(Path(paths[0]).parent))
            for p in paths:
                self.attach(p)

    def attach(self, path):
        kept = store.keep_image(path)
        self.attached.append(kept)
        a = Attachment(kept)
        a.removed.connect(self._unattach)
        self.thumbs.insertWidget(self.thumbs.count() - 1, a)
        self.thumbs_box.setVisible(True)

    def _paste_image(self, img):
        engine.IMAGES.mkdir(parents=True, exist_ok=True)
        path = engine.IMAGES / (t("вставка") + f" {time.strftime('%Y-%m-%d %H-%M-%S')}.png")
        img.save(str(path))
        self.attach(str(path))

    def _unattach(self, path):
        self.attached.remove(path)
        for i in range(self.thumbs.count()):
            w = self.thumbs.itemAt(i).widget()
            if isinstance(w, Attachment) and w.path == path:
                w.deleteLater()
                break
        self.thumbs_box.setVisible(bool(self.attached))

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and any(Path(u.toLocalFile()).suffix.lower() in IMAGE_EXT
                                          for u in e.mimeData().urls()):
            e.acceptProposedAction()

    def dropEvent(self, e):
        for u in e.mimeData().urls():
            if Path(u.toLocalFile()).suffix.lower() in IMAGE_EXT:
                self.attach(u.toLocalFile())

    def send(self):
        if self.turn is not None:
            return
        text = self.input.toPlainText().strip()
        m = self._model()
        if m is None or (not text and not self.attached):
            return
        msg = {"role": "user", "text": text, "images": list(self.attached)}
        if not self.chat["messages"]:
            self.chat["title"] = store.title_from(text)
        self.chat["messages"].append(msg)
        self.chat["model"] = m.key
        store.save(self.chat)
        self.input.clear()
        for p in list(self.attached):
            self._unattach(p)
        self._add_message(msg)
        self.current = AssistantMessage(m.title)
        self.feed.addWidget(self.current)
        self.follow = True
        self.turn = Turn(self.server, self.chat, m, self.web_btn.isChecked(), self.draw_btn.isChecked())
        self.alive.add(self.turn)
        self.turn.event.connect(self._event)
        self.turn.done.connect(self._done)
        self.turn.failed.connect(self._failed)
        self.turn.finished.connect(lambda t=self.turn: self.alive.discard(t))
        self._busy(True)
        self.started = time.time()
        self.turn.start()
        self._fill_list()

    def stop(self):
        if self.turn is not None:
            self.turn.stop = True

    def _busy(self, on):
        self.send_btn.setText(t("Стоп") if on else t("Отправить"))
        self.send_btn.setObjectName("stop" if on else "send")
        self.send_btn.style().unpolish(self.send_btn)
        self.send_btn.style().polish(self.send_btn)
        try:
            self.send_btn.clicked.disconnect()
        except RuntimeError:
            pass
        self.send_btn.clicked.connect(self.stop if on else self.send)
        self.send_btn.setEnabled(on or self._model() is not None)
        if on:
            self.ticker.start()
        else:
            self.ticker.stop()

    def _event(self, kind, data):
        if self.sender() is not self.turn or self.current is None:
            return
        self.current.on_event(kind, data)

    def _tick(self):
        if self.current is not None:
            self.current.flush()

    def _done(self, rec):
        if self.sender() is not self.turn:
            return
        self.turn = None
        if self.current is not None:
            self.current.flush()
        self.current = None
        if rec.get("parts"):
            self.chat["messages"].append(rec)
            store.save(self.chat)
        self._busy(False)
        self._fill_list()

    def _failed(self, text):
        if self.sender() is not self.turn:
            return
        self.turn = None
        if self.current is not None:
            self.current.fail(text)
        self.current = None
        self._busy(False)

    def _build_menu(self):
        bar = QMenuBar(self)
        self.about_act = QAction(tf("О программе {name}", name=TITLE), self)
        self.about_act.setMenuRole(QAction.AboutRole)
        self.about_act.triggered.connect(self.show_about)
        bar.addMenu(APP).addAction(self.about_act)

    def show_about(self):
        box = QMessageBox(self)
        box.setIconPixmap(app_icon().pixmap(72, 72))
        box.setTextFormat(Qt.RichText)
        box.setText(f"<b>{TITLE}</b>")
        box.setInformativeText(f'<nobr>{AUTHOR} · <a href="{URL}">{SITE}</a></nobr>')
        box.setTextInteractionFlags(Qt.TextBrowserInteraction)
        for lab in box.findChildren(QLabel):
            lab.setOpenExternalLinks(True)
        box.addButton(t("Закрыть"), QMessageBox.AcceptRole)
        box.exec()

    def closeEvent(self, e):
        self.settings.setValue("geometry", self.saveGeometry())
        if self.turn is not None:
            self.turn.stop = True
        self.server.stop()
        super().closeEvent(e)


def _proxy_env():
    """Поиск и загрузки берут прокси из окружения, а у приложения из Finder его
    нет — переносим системный. Свой сервер — мимо прокси."""
    import urllib.request
    found = urllib.request.getproxies()
    for scheme in ("http", "https"):
        if found.get(scheme):
            os.environ.setdefault(f"{scheme}_proxy", found[scheme])
    skip = [x for x in (os.environ.get("no_proxy") or found.get("no") or "").split(",") if x.strip()]
    os.environ["no_proxy"] = ",".join(dict.fromkeys(skip + ["localhost", "127.0.0.1", "::1"]))


def main():
    _proxy_env()
    app = QApplication(sys.argv)
    app.setApplicationName(APP)
    app.setApplicationDisplayName(TITLE)
    w = Window()
    w.show()
    code = app.exec()
    w.settings.sync()
    w.server.stop()
    os._exit(code or 0)


if __name__ == "__main__":
    main()
