import os
import time
import traceback

from PySide6 import QtCore
from PySide6.QtCore import QObject

from pkg.api import constants
from pkg.api.constants import FLAM_V1
from pkg.api.device_lunii import LuniiDevice

ACTION_IMPORT  = 1
ACTION_EXPORT  = 2
ACTION_REMOVE  = 3
ACTION_SIZE    = 4
ACTION_RECOVER = 5
ACTION_CLEANUP = 6
ACTION_FACTORY = 7

class ierWorker(QObject):
    signal_total_progress = QtCore.Signal(int, int)
    signal_refresh = QtCore.Signal()
    signal_finished = QtCore.Signal()
    signal_message = QtCore.Signal(str)

    def __init__(self, device: LuniiDevice, action, story_list=None, out_dir=None, update_size=False):
        super().__init__()

        self.abort_process = False
        self.audio_device = device
        self.action = action
        self.items = story_list
        self.out_dir = out_dir
        self.update_size = update_size      # stories size to be computed at the end of import

    def process(self):
        # cleaning any previous abortion
        self.abort_process = False
        self.audio_device.abort_process = False

        # which action to perform ?
        try:
            if self.action == ACTION_IMPORT:
                self._task_import()
            elif self.action == ACTION_EXPORT:
                self._task_export()
            elif self.action == ACTION_REMOVE:
                self._task_remove()
            elif self.action == ACTION_SIZE:
                self._task_size()
            elif self.action == ACTION_RECOVER:
                self._task_recover()
            elif self.action == ACTION_CLEANUP:
                self._task_cleanup()
            elif self.action == ACTION_FACTORY:
                self._task_factory_reset()

        except Exception as e:
            # Abort requested
            self.exit_requested()
            self.signal_message.emit(f"🛑 Critical error : {e}")
            traceback.print_exc()

        self.signal_refresh.emit()

    def exit_requested(self):
        self.signal_finished.emit()
        self.signal_refresh.emit()
        self.signal_message.emit("🛑 Aborted")

    def _task_import(self):
        success = 0

        # importing selected files
        for index, file in enumerate(self.items):
            if self.abort_process:
                self.exit_requested()
                return

            self.signal_total_progress.emit(index, len(self.items))
            ts_start = time.time()
            if self.audio_device.import_story(file):
                ts_end = time.time()
                self.signal_message.emit(f"Time to import : {round(ts_end-ts_start, 3)}s'")
                self.signal_message.emit(f"👍 New story imported : '{file}'")
                success += 1
            else:
                self.signal_message.emit(f"🛑 Failed to import : '{file}'")

            self.signal_refresh.emit()

        if self.abort_process:
            self.exit_requested()
            return

        # size to be updated ?
        if self.update_size:
            self._task_size()

        # done
        self.signal_finished.emit()
        self.signal_refresh.emit()
        self.signal_message.emit(f"✅ Import done : {success}/{len(self.items)}")

    def _task_export(self):
        success = 0

        # Save all files
        for index, str_uuid in enumerate(self.items):
            if self.abort_process:
                self.exit_requested()
                return

            # Official story export is forbidden
            story_to_export = self.audio_device.stories.get_story(str_uuid)
            if not constants.REFRESH_CACHE and story_to_export.is_official():
                self.signal_message.emit(f"🛑 Forbidden to export : '{story_to_export.name}'")
                self.signal_refresh.emit()
                continue

            self.signal_total_progress.emit(index, len(self.items))
            
            res = self.audio_device.export_story(str_uuid, self.out_dir)
            if res:
                self.signal_message.emit(f"👍 Story exported to '{res}'")
                success += 1
            else:
                self.signal_message.emit(f"🛑 Failed to export : '{story_to_export.name}'")
            self.signal_refresh.emit()

        if self.abort_process:
            self.exit_requested()
            return

        # done
        self.signal_finished.emit()
        self.signal_refresh.emit()
        self.signal_message.emit(f"✅ Export done : {success}/{len(self.items)}")

    def _task_remove(self):
        success = 0

        for index, str_uuid in enumerate(self.items):
            if self.abort_process:
                self.exit_requested()
                return

            self.signal_total_progress.emit(index, len(self.items))
            # remove story contents from device
            story_to_remove = self.audio_device.stories.get_story(str_uuid)
            res = self.audio_device.remove_story(str_uuid)
            if res:
                self.signal_message.emit(f"👍 Story removed: '{story_to_remove.name}'")
                success += 1
            else:
                self.signal_message.emit(f"🛑 Failed to remove : '{story_to_remove.name}'")
            self.signal_refresh.emit()

        if self.abort_process:
            self.exit_requested()
            return

        # done
        self.signal_finished.emit()
        self.signal_refresh.emit()
        self.signal_message.emit(f"✅ {success} stories removed")

    def _task_size(self):
        # processing all stories
        for index, story in enumerate(self.audio_device.stories):
            if self.abort_process:
                self.exit_requested()
                return

            self.signal_total_progress.emit(index, len(self.audio_device.stories))

            # is the size already known ?
            if story.size != -1:
                continue

            # processing all files in a story
            story.size = 0
            for parent_dir, _, files in os.walk(f"{self.audio_device.mount_point}/{self.audio_device.STORIES_BASEDIR}/{str(story.uuid) if self.audio_device.device_version == FLAM_V1 else story.short_uuid }"):
                for file in files:
                    story.size += os.path.getsize(os.path.join(parent_dir, file))

                    if self.abort_process:
                        self.exit_requested()
                        return

            # updating to display story size
            self.signal_refresh.emit()

        if self.abort_process:
            self.exit_requested()
            return

        # done
        self.signal_finished.emit()
        self.signal_refresh.emit()
        self.signal_message.emit(f"✅ Stories parsed, sizes updated")

    def _task_recover(self):
        count = self.audio_device.recover_stories()
        self.audio_device.update_pack_index()

        # done
        self.signal_finished.emit()
        self.signal_refresh.emit()
        self.signal_message.emit(f"✅ Storage parsed, {count} lost stories recovered")


    def _task_cleanup(self):
        count, size = self.audio_device.cleanup_stories()

        # done
        self.signal_finished.emit()
        self.signal_refresh.emit()
        self.signal_message.emit(f"✅ Storage parsed, {count} lost stories removed, {size} MB recovered")

        pass

    def _task_factory_reset(self):
        self.audio_device.factory_reset()

        # done
        self.signal_finished.emit()
        self.signal_refresh.emit()
        self.signal_message.emit(f"✅ Factory reset performed, device is empty")

