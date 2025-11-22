import base64

from collections import deque

from PySide6.QtCore import QThreadPool, QRunnable, Signal, QObject, QSize, QBuffer, QIODevice, QRect
from PySide6.QtGui import QFont, Qt, QColor, QPixmap, QPainter, QStandardItemModel, QStandardItem, QPixmap, QPainter
from PySide6.QtWidgets import QStyledItemDelegate

from pkg.api import stories


class SimpleLazyLoadingModel(QStandardItemModel):
    def __init__(self, data_list, max_concurrent = 5):
        super().__init__()
        self._data = data_list
        self._loaded = {}
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
            if id_ in self._loaded:
                return self.generate_listview_icon(data["id"], data["local_db_path"] != "", data["lunii_story_id"] != "")
            elif id_ not in self._loading and id_ not in self._queue:
                self._queue.append((id_, index))
                self.try_start_loading()
            return None

        if role == Qt.DisplayRole:
            return str(self._data[index.row()]["name"])

        return super().data(index, role)

    def try_start_loading(self):
        while len(self._loading) < self._max_concurrent and self._queue:
            id_, index = self._queue.popleft()
            self._loading.add(id_)
            worker = ImageLoaderWorker(id_, index, self.signals)
            self.threadpool.start(worker)

    def on_image_loaded(self, id_, index):
        self._loaded[id_] = id_
        self._loading.discard(id_)
        self.dataChanged.emit(index, index, [Qt.DecorationRole])
        self.try_start_loading()

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


class FixedSizeDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        return QSize(320, 360)

class ImageLoaderSignals(QObject):
    loaded = Signal(str, object)

class ImageLoaderWorker(QRunnable):
    def __init__(self, id, index, signals):
        super().__init__()
        self.id_ = id
        self.index = index
        self.signals = signals

    def run(self):
        stories.get_picture(self.id_)
        self.signals.loaded.emit(self.id_, self.index)


def create_image_stack_base64(image_paths, target_width, max_images = 5, offset_step=30):
    if not image_paths:
        return None

    pixmaps = [QPixmap(p) for p in image_paths if not QPixmap(p).isNull()]
    if not pixmaps:
        return None
    displayed_images = min(len(pixmaps), max_images)
    scaled_pixmaps = [pixmap.scaledToWidth(target_width, Qt.SmoothTransformation) for pixmap in pixmaps[:displayed_images]]
    max_width = max(p.width() for p in scaled_pixmaps)
    max_height = max(p.height() for p in scaled_pixmaps)
    width = max_width + offset_step * (displayed_images -1)
    height = max_height + offset_step * (displayed_images -1)

    final_image = QPixmap(width, height)
    final_image.fill(Qt.transparent)

    painter = QPainter(final_image)
    x_offset = 0
    y_offset = 0
    for scaled_pixmap in scaled_pixmaps:
        painter.drawPixmap(x_offset, y_offset, scaled_pixmap)
        x_offset += offset_step
        y_offset += offset_step

    text = str(len(pixmaps))
    padding = 8
    font = QFont()
    font.setBold(True)
    font.setPointSize(32)
    painter.setFont(font)
    metrics = painter.fontMetrics()
    rect_width = metrics.horizontalAdvance(text) + 4 * padding
    rect_height = metrics.height() + 2 * padding
    x = width - rect_width - 2 * padding
    y = height - rect_height - 2* padding
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("white"))
    painter.drawRoundedRect(QRect(x, y, rect_width, rect_height), padding, padding)
    painter.setPen(QColor("black"))
    painter.drawText(QRect(x, y, rect_width, rect_height), Qt.AlignCenter, text)
    painter.end()
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    final_image.save(buffer, "PNG")
    buffer.close()

    base64_data = base64.b64encode(buffer.data()).decode()
    data_uri = f"data:image/png;base64,{base64_data}"
    return data_uri
