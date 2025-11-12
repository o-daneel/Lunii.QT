from collections import deque

from PySide6.QtCore import QThreadPool, QRunnable, Signal, QObject, QSize
from PySide6.QtGui import QFont, Qt, QColor, QPixmap, QPainter, QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QStyledItemDelegate

from pkg.api import stories


class SimpleLazyLoadingModel(QStandardItemModel):
    def __init__(self, data_list, max_concurrent = 5):
        super().__init__()
        self._data = data_list
        self._cache = {}
        self._loading = set()
        self._queue = deque()
        self._max_concurrent = max_concurrent

        self.threadpool = QThreadPool()
        self.signals = ImageLoaderSignals()
        self.signals.loaded.connect(self.on_image_loaded)

        for data in self._data:
            item = QStandardItem()
            item.setText(data["name"])
            item.setData(data, Qt.UserRole)
            self.appendRow(item)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return super().data(index, role)

        if role == Qt.DecorationRole:
            data = self._data[index.row()]
            id_ = data["id"]
            if id_ in self._cache:
                return self._cache[id_]
            elif id_ not in self._loading and id_ not in self._queue:
                self._queue.append((id_, index, data))
                self.try_start_loading()
            return None

        if role == Qt.DisplayRole:
            return str(self._data[index.row()]["name"])

        return super().data(index, role)

    def try_start_loading(self):
        while len(self._loading) < self._max_concurrent and self._queue:
            id_, index, data = self._queue.popleft()
            self._loading.add(id_)
            worker = ImageLoaderWorker(id_, data, index, self.signals)
            self.threadpool.start(worker)

    def on_image_loaded(self, id_, pixmap, index):
        self._cache[id_] = pixmap
        self._loading.discard(id_)
        self.dataChanged.emit(index, index, [Qt.DecorationRole])
        self.try_start_loading()

class FixedSizeDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(320, 360)

class ImageLoaderSignals(QObject):
    loaded = Signal(str, QPixmap, object)

class ImageLoaderWorker(QRunnable):
    def __init__(self, id, data, index, signals):
        super().__init__()
        self.id_ = id
        self.data = data
        self.index = index
        self.signals = signals

    def run(self):
        pixmap = self.generate_listview_icon(self.data["id"], self.data["local_db_path"] != "", self.data["lunii_story_id"] != "")
        self.signals.loaded.emit(self.id_, pixmap, self.index)

    def generate_listview_icon(self, uuid: str, available: bool, installed: bool):
        image = stories.get_picture(uuid)
        if not image:
            pixmap = QPixmap("res/logo.png")
        else:
            pixmap = QPixmap()
            pixmap.loadFromData(image)
        scaled_pixmap = pixmap.scaled(300, 300, aspectMode=Qt.KeepAspectRatio, mode=Qt.SmoothTransformation)
        return self.create_icon_with_banner(scaled_pixmap, available, installed)
        
    def create_icon_with_banner(self, base_pixmap, available, installed):
        pixmap = base_pixmap.copy()
        w = pixmap.width()
        h = pixmap.height()
        banner_width = h // 2
        banner_height = 30

        if available:
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            font = QFont()
            font.setBold(True)
            font.setPointSize(10)
            painter.translate(w - banner_width // 1.8,  -20)
            painter.rotate(45)
            painter.fillRect(0, 0, banner_width, banner_height, QColor(255, 0, 0, 180))
            painter.setPen(Qt.GlobalColor.white)
            painter.setFont(font)
            painter.drawText(0, 0, banner_width, banner_height, Qt.AlignmentFlag.AlignCenter, "Disponible")
            painter.end()
        
        if installed:
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
            font = QFont()
            font.setBold(True)
            font.setPointSize(10)
            painter.translate(0, h - banner_width // 1.5)
            painter.rotate(45)
            painter.fillRect(0, 0, banner_width, banner_height, QColor(0, 255, 0, 180))
            painter.setPen(Qt.GlobalColor.black)
            painter.setFont(font)
            painter.drawText(0, 0, banner_width, banner_height, Qt.AlignmentFlag.AlignCenter, "Sur la Lunii")
            painter.end()
        
        return pixmap
