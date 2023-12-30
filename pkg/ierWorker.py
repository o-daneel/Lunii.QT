import time

from PySide6 import QtCore
from PySide6.QtCore import QObject

from pkg.api.device import LuniiDevice

ACTION_IMPORT = 1
ACTION_EXPORT = 2
ACTION_REMOVE = 3


class ExitException(Exception):
    pass


class ierWorker(QObject):
    signal_total_progress = QtCore.Signal(int, int)
    signal_refresh = QtCore.Signal()
    signal_finished = QtCore.Signal()
    signal_message = QtCore.Signal(str)

    def __init__(self, device: LuniiDevice, action, story_list, out_dir = None):
        super().__init__()

        self.early_exit = False
        self.lunii = device
        self.action = action
        self.items = story_list
        self.out_dir = out_dir

    def process(self):
        try:
            if self.action == ACTION_IMPORT:
                self._task_import()
            elif self.action == ACTION_EXPORT:
                self._task_export()
            elif self.action == ACTION_REMOVE:
                self._task_remove()

        except ExitException:
            # Abort requested
            self.signal_message.emit("🛑 Aborted")

        self.signal_refresh.emit()

    def _task_import(self):
        # importing selected files
        for index, file in enumerate(self.items):
            self.signal_total_progress.emit(index, len(self.items))
            self.lunii.import_story(file)
            self.signal_refresh.emit()

        # done
        self.signal_finished.emit()
        self.signal_refresh.emit()

    def _task_export(self):
        # Save all files
        for index, file in enumerate(self.items):
            self.signal_total_progress.emit(index, len(self.items))
            self.lunii.export_story(file, self.out_dir)
            self.signal_refresh.emit()

        # done
        self.signal_finished.emit()
        self.signal_refresh.emit()

    def _task_remove(self):
        for index, item in enumerate(self.items):
            self.signal_total_progress.emit(index, len(self.items))
            # remove story contents from device
            self.lunii.remove_story(item)
            self.signal_refresh.emit()

        # done
        self.signal_finished.emit()
        self.signal_refresh.emit()
