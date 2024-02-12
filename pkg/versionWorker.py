import requests
from PySide6.QtCore import QObject, Signal, QThread


class VersionChecker(QObject):
    update_available = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.url = "https://github.com/o-daneel/Lunii.QT/releases/latest"

    def check_for_updates(self):
        last_version=None

        try:
            headers = {'Referer': f"Lunii.QT"}
            response = requests.get(self.url, headers=headers, timeout=5)
            last_version = response.url.split("/").pop()
        except:
            pass

        self.update_available.emit(last_version)
        # We're done so ask the `QThread` to terminate.
        QThread.currentThread().quit()

