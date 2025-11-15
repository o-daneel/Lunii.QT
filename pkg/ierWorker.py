import base64
import json
import os
import time
import traceback
from uuid import UUID

from PySide6 import QtCore
from PySide6.QtCore import QObject, QThread

from pkg.api import stories
from pkg.api.constants import FLAM_V1
from pkg.api.device_lunii import LuniiDevice, get_uuid_from_file
from pkg.api.stories import DB_LOCAL_LIBRARY_COL_AGE, DB_LOCAL_LIBRARY_COL_PATH, local_library_db_add_or_update, thirdparty_db_add_story, thirdparty_db_add_thumb

ACTION_IMPORT  = 1
ACTION_EXPORT  = 2
ACTION_REMOVE  = 3
ACTION_SIZE    = 4
ACTION_FIND    = 5
ACTION_RECOVER = 6
ACTION_CLEANUP = 7
ACTION_FACTORY = 8
ACTION_DB_IMPORT = 9
ACTION_IMPORT_IN_LIBRAIRY = 10

class ierWorker(QObject):
    signal_total_progress = QtCore.Signal(int, int)
    signal_refresh = QtCore.Signal()
    signal_finished = QtCore.Signal()
    signal_message = QtCore.Signal(str)
    signal_showlog = QtCore.Signal()

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
        if self.audio_device:
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
            elif self.action == ACTION_FIND:
                self._task_recover(True)
            elif self.action == ACTION_RECOVER:
                self._task_recover(False)
            elif self.action == ACTION_CLEANUP:
                self._task_cleanup()
            elif self.action == ACTION_FACTORY:
                self._task_factory_reset()
            elif self.action == ACTION_DB_IMPORT:
                self._task_db_import()
            elif self.action == ACTION_IMPORT_IN_LIBRAIRY:
                self._task_import_in_library()

        except Exception as e:
            # Abort requested
            self.signal_showlog.emit()
            self.signal_message.emit(self.tr("🛑 Critical error : {}").format(e))
            self.signal_message.emit(self.tr("Trace\n{}").format(traceback.format_exc()))
            traceback.print_exc()
            self.exit_requested()
            return
            
        self.signal_refresh.emit()
        QThread.currentThread().quit()

    def exit_requested(self):
        self.signal_finished.emit()
        self.signal_refresh.emit()
        self.signal_message.emit(self.tr("🛑 Aborted"))
        QThread.currentThread().quit()

    def _task_import(self):
        success = 0

        # on flam device, import is very long. Showing log to notify user
        if len(self.items) and self.audio_device.device_version == FLAM_V1:
            self.signal_showlog.emit()
            self.signal_message.emit(self.tr("😮‍💨 This process is veeeeeeeeery long due to Flam firmware. 😴 Be patient ..."))
            self.signal_message.emit(self.tr("Importing stories..."))

        # importing selected files
        for index, file in enumerate(self.items):
            if self.abort_process:
                self.exit_requested()
                return

            self.signal_total_progress.emit(index, len(self.items))
            ts_start = time.time()
            if self.audio_device.import_story(file):
                ts_end = time.time()
                duration = ts_end - ts_start
                if duration > 120:
                    minutes = int(duration // 60)
                    seconds = int(duration % 60)
                    time_msg = "{} min {} s".format(minutes, seconds)
                else:
                    time_msg = "{:d} s".format(int(duration))
                self.signal_message.emit(self.tr("Time to import : {}").format(time_msg))
                self.signal_message.emit(self.tr("👍 New story imported : '{}'").format(file))
                success += 1
            else:
                self.signal_showlog.emit()
                self.signal_message.emit(self.tr("🛑 Failed to import : '{}'").format(file))

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
        self.signal_message.emit(self.tr("✅ Import done : {}/{}").format(success, len(self.items)))

    def _task_export(self):
        success = 0

        # Save all files
        for index, str_uuid in enumerate(self.items):
            if self.abort_process:
                self.exit_requested()
                return

            # Official story export is forbidden
            story_to_export = self.audio_device.stories.get_story(str_uuid)
            # if not constants.REFRESH_CACHE and story_to_export.is_official():
            #     self.signal_message.emit(self.tr("🛑 Forbidden to export : '{}'").format(story_to_export.name))
            #     self.signal_refresh.emit()
            #     continue

            self.signal_total_progress.emit(index, len(self.items))
            
            res = self.audio_device.export_story(str_uuid, self.out_dir)
            if res:
                self.signal_message.emit(self.tr("👍 Story exported to '{}'").format(res))
                success += 1
            else:
                self.signal_showlog.emit()
                self.signal_message.emit(self.tr("🛑 Failed to export : '{}'").format(story_to_export.name))
            self.signal_refresh.emit()

        if self.abort_process:
            self.exit_requested()
            return

        # done
        self.signal_finished.emit()
        self.signal_refresh.emit()
        self.signal_message.emit(self.tr("✅ Export done : {}/{}").format(success, len(self.items)))

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
                self.signal_message.emit(self.tr("👍 Story removed: '{}'").format(story_to_remove.name))
                success += 1
            else:
                self.signal_showlog.emit()
                self.signal_message.emit(self.tr("🛑 Failed to remove : '{}'").format(story_to_remove.name))
            self.signal_refresh.emit()

        if self.abort_process:
            self.exit_requested()
            return

        # done
        self.signal_finished.emit()
        self.signal_refresh.emit()
        self.signal_message.emit(self.tr("✅ {} stories removed").format(success))

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

            # which BASEDIR ? hidden or not ?
            basedir = self.audio_device.STORIES_BASEDIR
            if story.hidden: 
                basedir = self.audio_device.HIDDEN_STORIES_BASEDIR
            uuid = story.short_uuid
            if self.audio_device.device_version == FLAM_V1:
                uuid = str(story.uuid)
            story_path = os.path.join(self.audio_device.mount_point, basedir, uuid)

            # processing all files in a story
            story.size = 0
            for parent_dir, _, files in os.walk(story_path):
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
        self.signal_message.emit(self.tr("✅ Stories parsed, sizes updated"))

    def _task_recover(self, dry_run=False):
        self.signal_message.emit(self.tr("🚧 Analyzing storage ..."))
        count = self.audio_device.recover_stories(dry_run)
        if not dry_run:
            self.audio_device.update_pack_index()

        # done
        self.signal_finished.emit()
        self.signal_refresh.emit()
        self.signal_message.emit(self.tr("✅ Storage parsed, {} lost stories {}").format(count, self.tr('found (try to recover them)') if dry_run else self.tr('recovered')))


    def _task_cleanup(self):
        self.signal_message.emit(self.tr("🚧 Cleaning storage ..."))
        count, size = self.audio_device.cleanup_stories()

        # done
        self.signal_finished.emit()
        self.signal_refresh.emit()
        self.signal_message.emit(self.tr("✅ Storage parsed, {} lost stories removed, {} MB recovered").format(count, size))

        pass

    def _task_factory_reset(self):
        self.audio_device.factory_reset()

        # done
        self.signal_finished.emit()
        self.signal_refresh.emit()
        self.signal_message.emit(self.tr("✅ Factory reset performed, device is empty"))


    def _task_db_import(self):
        count = 0

        # loading DB
        with open(self.items, encoding='utf-8') as fp_db:
            db_stories = json.load(fp_db)

        # checking for official DB instead of STUdio
        print(db_stories.keys())
        print(list(db_stories.keys()))
        if "response" in list(db_stories.keys()):
            self.signal_finished.emit()
            self.signal_message.emit(self.tr("🛑 Failed to import DB (wrong file ?)"))
            return

        # for each entry
        for index, s_uuid in enumerate(db_stories.keys()):
            if self.abort_process:
                self.exit_requested()
                return

            self.signal_total_progress.emit(index, len(self.items))
            # get uuuid/title/desc/image
            uuid = db_stories[s_uuid].get("uuid")
            title = db_stories[s_uuid].get("title")
            desc = db_stories[s_uuid].get("description")
            image = db_stories[s_uuid].get("image")

            # if enough details
            if not uuid and not title:
                continue

            try:
                one_uuid = UUID(uuid)
            except:
                continue

            # print(f"{uuid} - {title}")
            # if desc:
            #     print(f"({desc[:25]})")
            # if image:
            #     print(f"+{image[:5]}")

            # create db entry
            thirdparty_db_add_story(one_uuid, title, desc)

            # create image entry
            if image:
                _, encoded_data = image.split(',', 1)
                image_data = base64.b64decode(encoded_data)
                thirdparty_db_add_thumb(one_uuid, image_data)

            count += 1

        # done
        self.signal_finished.emit()
        self.signal_refresh.emit()
        self.signal_message.emit(self.tr("✅ STUdio DB imported ({}/{}).").format(count, len(db_stories.keys())))

    def _task_import_in_library(self):
        success = 0

        # importing selected files
        for index, file in enumerate(self.items):
            if self.abort_process:
                self.exit_requested()
                return
            filename = os.path.basename(file)
            age = str((lambda s: int(s) if s.isdigit() else "")(filename.split("+")[0]))
            uuid = str(get_uuid_from_file(file)).upper()
            if uuid == "":
                self.signal_message.emit(self.tr("🛑 Failed to extract UUID from : '{}'").format(file))
            else:
                if uuid in stories.DB_LOCAL_LIBRARY:
                    if DB_LOCAL_LIBRARY_COL_PATH not in stories.DB_LOCAL_LIBRARY[uuid] \
                            or stories.DB_LOCAL_LIBRARY[uuid][DB_LOCAL_LIBRARY_COL_PATH] != file \
                            or (age != "" and DB_LOCAL_LIBRARY_COL_AGE not in stories.DB_LOCAL_LIBRARY[uuid]) \
                            or (age != "" and stories.DB_LOCAL_LIBRARY[uuid][DB_LOCAL_LIBRARY_COL_AGE] != age):
                        self.signal_message.emit(self.tr("⚠️ Existing entry will be overridden: Age={} File='{}'...").format(age, file))
                    else:
                        continue
                local_library_db_add_or_update(uuid, file, age)
                self.signal_message.emit(self.tr("👍 New story imported in local Library : '{}'").format(file))
                success += 1
            
            self.signal_total_progress.emit(index, len(self.items))

        if self.abort_process:
            self.exit_requested()
            return

        # done
        self.signal_finished.emit()
        self.signal_refresh.emit()
        self.signal_message.emit(self.tr("✅ Import in local Library done : {}/{}").format(success, len(self.items)))
