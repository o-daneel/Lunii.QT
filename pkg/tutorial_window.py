"""
Startup tutorial for the "Create an audiobook" feature.
Shown at launch until "Do not show again at startup" is ticked, can be reopened from the Help menu.
"""
import json
import os

from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QPainter, QColor, QFont, QPen
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QCheckBox, QStackedWidget,
                               QWidget, QSizePolicy)

from pkg.api.constants import CFG_DIR

SETTINGS_FILE = os.path.join(CFG_DIR, "audiobook.json")


# ---------------------------------------------------------------------- settings
def _load():
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as fp:
            return json.load(fp)
    except Exception:
        return {}


def tutorial_enabled() -> bool:
    return _load().get("show_tutorial", True)


def set_tutorial_enabled(value: bool):
    data = _load()
    data["show_tutorial"] = value
    try:
        os.makedirs(CFG_DIR, exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as fp:
            json.dump(data, fp, indent=2)
    except OSError:
        pass


# ---------------------------------------------------------------------- illustrations
class FlowDiagram(QWidget):
    """Small drawing of what the child sees on the device: cover -> chapter menu -> playback."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        fg = self.palette().windowText().color()
        accent = QColor(41, 128, 185)

        screens = [("📖", self.tr("Cover"), self.tr("title announced")),
                   ("1 / 9", self.tr("Menu"), self.tr("wheel = chapter")),
                   ("▶", self.tr("Playback"), self.tr("chains the next one"))]
        w, h, gap = 120, 90, 50
        total = len(screens) * w + (len(screens) - 1) * gap
        x0 = (self.width() - total) / 2
        y0 = 10

        for i, (icon, title, sub) in enumerate(screens):
            x = x0 + i * (w + gap)
            rect = QRectF(x, y0, w, h)
            p.setPen(QPen(accent, 2))
            p.setBrush(QColor(accent.red(), accent.green(), accent.blue(), 30))
            p.drawRoundedRect(rect, 10, 10)
            f = QFont(self.font())
            f.setPointSize(20)
            f.setBold(True)
            p.setFont(f)
            p.setPen(fg)
            p.drawText(rect, Qt.AlignCenter, icon)
            f.setPointSize(10)
            p.setFont(f)
            p.drawText(QRectF(x - 15, y0 + h + 6, w + 30, 18), Qt.AlignCenter, title)
            f.setBold(False)
            f.setPointSize(8)
            p.setFont(f)
            p.drawText(QRectF(x - 20, y0 + h + 24, w + 40, 16), Qt.AlignCenter, sub)

            if i < len(screens) - 1:
                ax = x + w + 8
                ay = y0 + h / 2
                p.setPen(QPen(fg, 2))
                p.drawLine(int(ax), int(ay), int(ax + gap - 16), int(ay))
                p.drawLine(int(ax + gap - 16), int(ay), int(ax + gap - 24), int(ay - 5))
                p.drawLine(int(ax + gap - 16), int(ay), int(ax + gap - 24), int(ay + 5))
                f.setPointSize(8)
                f.setBold(True)
                p.setFont(f)
                p.drawText(QRectF(ax, ay - 20, gap - 16, 14), Qt.AlignCenter, "OK")
        p.end()


# ---------------------------------------------------------------------- pages
class _Page(QWidget):
    def __init__(self, icon, title, html, extra_cls=None):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 16, 24, 8)

        head = QHBoxLayout()
        lbl_icon = QLabel(icon)
        f = lbl_icon.font()
        f.setPointSize(30)
        lbl_icon.setFont(f)
        head.addWidget(lbl_icon)
        lbl_title = QLabel(title)
        f = lbl_title.font()
        f.setPointSize(14)
        f.setBold(True)
        lbl_title.setFont(f)
        lbl_title.setWordWrap(True)
        head.addWidget(lbl_title, 1)
        lay.addLayout(head)

        body = QLabel(html)
        body.setWordWrap(True)
        body.setTextFormat(Qt.RichText)
        body.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        lay.addWidget(body)
        if extra_cls:
            lay.addWidget(extra_cls())
        lay.addStretch(1)


class TutorialDialog(QDialog):
    create_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Audiobooks - tutorial"))
        self.setFixedSize(600, 470)

        root = QVBoxLayout(self)
        self.stack = QStackedWidget()
        for page in self.pages():
            self.stack.addWidget(_Page(*page))
        root.addWidget(self.stack, 1)

        self.lbl_dots = QLabel()
        self.lbl_dots.setAlignment(Qt.AlignCenter)
        root.addWidget(self.lbl_dots)

        bottom = QHBoxLayout()
        self.cb_hide = QCheckBox(self.tr("Do not show again at startup"))
        self.cb_hide.setChecked(not tutorial_enabled())
        self.cb_hide.toggled.connect(lambda checked: set_tutorial_enabled(not checked))
        bottom.addWidget(self.cb_hide)
        bottom.addStretch(1)
        self.btn_prev = QPushButton(self.tr("◀ Previous"))
        self.btn_prev.clicked.connect(lambda: self.go(-1))
        self.btn_next = QPushButton(self.tr("Next ▶"))
        self.btn_next.setDefault(True)
        self.btn_next.clicked.connect(lambda: self.go(1))
        self.btn_create = QPushButton(self.tr("Create an audiobook"))
        self.btn_create.clicked.connect(self._create)
        self.btn_close = QPushButton(self.tr("Close"))
        self.btn_close.clicked.connect(self.accept)
        for b in (self.btn_prev, self.btn_next, self.btn_create, self.btn_close):
            bottom.addWidget(b)
        root.addLayout(bottom)

        self._refresh()

    def pages(self):
        return [
            ("🎧", self.tr("New: your audiobooks on the Lunii / Flam"),
             self.tr("Lunii.QT can now turn an <b>audiobook</b> (one MP3 file per chapter) into a story for your "
                     "storyteller, with a cover, a chapter menu and voice announcements."
                     "<br><br>To start:"
                     "<ul><li>menu <b>Stories → Create an audiobook...</b> (shortcut <b>Ctrl+B</b>)</li>"
                     "<li>or <b>drop your MP3 files</b> (or their folder) directly on the story list.</li></ul>")),
            ("📂", self.tr("1. Choose the chapters"),
             self.tr("<ul><li><b>Add MP3 files...</b> or <b>Add a folder...</b>: files are sorted by name.</li>"
                     "<li><b>Drag</b> the chapters to change their order, or use ▲ / ▼.</li>"
                     "<li><b>Double-click</b> a chapter to rename it: this name is the one <b>announced</b> and displayed.</li>"
                     "<li>The <b>title</b> and the <b>cover</b> are found automatically (MP3 tags, picture in the folder). "
                     "Click on the cover to choose another one.</li></ul>")),
            ("⚙️", self.tr("2. Options"),
             self.tr("<ul><li><b>Synthetic voice</b>: the book title and each chapter name are read aloud "
                     "in the menu (Windows voices).</li>"
                     "<li><b>Night mode</b>: makes the book available in the storyteller night mode.</li>"
                     "<li><b>Packs folder</b>: a copy of each book is kept there, to import it again later.</li></ul>"
                     "<i>FFMPEG is required to convert the audio. If it is missing, install it from the <b>Tools</b> menu.</i>")),
            ("📥", self.tr("3. Import on the storyteller"),
             self.tr("<ul><li>Connect your Lunii / Flam and select it at the top of the window.</li>"
                     "<li><b>Create and import</b>: the book is prepared then sent directly.</li>"
                     "<li><b>Create pack only</b>: to import it later (Stories → Import, or drop the .zip).</li></ul>"
                     "⏳ The Flam is slow over USB (about 1 minute for 35 MB): please be patient.<br>"
                     "⚠️ The Flam must run <b>firmware 2.x</b>. Remember to <b>eject</b> the storyteller before unplugging it.")),
            ("🧒", self.tr("4. On the storyteller"),
             self.tr("<ul><li>Choose the book like any story: its cover is displayed and the title is announced.</li>"
                     "<li><b>OK</b> opens the menu: turn the <b>wheel</b> to choose a chapter, then <b>OK</b>.</li>"
                     "<li>At the end of a chapter, <b>the next one starts automatically</b>.</li>"
                     "<li>The <b>Home</b> button goes back to the menu, <b>on the current chapter</b>: handy to resume later.</li></ul>"),
             FlowDiagram),
        ]

    def go(self, offset):
        self.stack.setCurrentIndex(max(0, min(self.stack.count() - 1, self.stack.currentIndex() + offset)))
        self._refresh()

    def _refresh(self):
        idx, count = self.stack.currentIndex(), self.stack.count()
        self.lbl_dots.setText("  ".join("●" if i == idx else "○" for i in range(count)))
        self.btn_prev.setEnabled(idx > 0)
        last = idx == count - 1
        self.btn_next.setVisible(not last)
        self.btn_create.setVisible(last)
        (self.btn_create if last else self.btn_next).setDefault(True)

    def _create(self):
        self.accept()
        self.create_requested.emit()
