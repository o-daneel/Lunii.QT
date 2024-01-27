import glob
import json
import os.path
import platform
import shutil
import unicodedata
import zipfile
import psutil
import py7zr
import xxtea
import binascii
import logging
from pathlib import Path
from uuid import UUID

from Crypto.Cipher import AES
from PySide6 import QtCore

from pkg.api.aes_keys import fetch_keys, reverse_bytes
from pkg.api.constants import *
from pkg.api import stories
from pkg.api.convert_audio import audio_to_mp3
from pkg.api.convert_image import image_to_bitmap_rle4
from pkg.api.stories import FILE_META, FILE_STUDIO_JSON, FILE_STUDIO_THUMB, FILE_THUMB, FILE_UUID, StoryList, Story, StudioStory


class FlamDevice(QtCore.QObject):
    signal_story_progress = QtCore.Signal(str, int, int)
    signal_logger = QtCore.Signal(int, str)
    stories: StoryList

    def __init__(self, mount_point, keyfile=None):
        super().__init__()
        self.mount_point = mount_point

        # dummy values
        self.lunii_version = 0
        self.UUID = ""
        self.dev_keyfile = keyfile
        self.device_key = None
        self.device_iv = None
        self.story_key = None
        self.story_iv = None
        self.snu = ""
        self.fw_vers_major = 0
        self.fw_vers_minor = 0
        self.fw_vers_subminor = 0
        self.memory_left = 0

        # internal device details
        if not self.__feed_device():
            return

        # internal stories
        self.stories = feed_stories(self.mount_point)

    @property
    def snu_str(self):
        return self.snu.hex().upper().lstrip("0")

    # opens the .mdf file to read all information related to device
    def __feed_device(self):

        mount_path = Path(self.mount_point)
        mdf_path = mount_path.joinpath(".mdf")

        # checking if specified path is acceptable
        if not os.path.isfile(mdf_path):
            return False

        with open(mdf_path, "rb") as fp_mdf:
            mdf_version = int.from_bytes(fp_mdf.read(2), 'little')

            if mdf_version == 1:
                self.__md1_parse(fp_mdf)
        return True

    def __md1_parse(self, fp_mdf):
        fp_mdf.seek(2)
        versions = fp_mdf.read(48)
        fws = versions.split(b"\n")
        self.fw_main = fws[0].split(b": ")[1].split(b"-")[0]
        self.fw_comm = fws[1].split(b": ")[1].split(b"-")[0]

        snu_str = fp_mdf.read(24).decode('utf-8').rstrip('\x00')
        self.snu = binascii.unhexlify(snu_str)

        vid = int.from_bytes(fp_mdf.read(2), 'little')
        pid = int.from_bytes(fp_mdf.read(2), 'little')

        if (vid, pid) == FLAM_USB_VID_PID:
            self.device_version = FLAM_V1
        else:
            self.device_version = UNDEF_DEV

        logger = logging.getLogger(LUNII_LOGGER)
        logger.log(logging.DEBUG, f"\n"
                                       f"SNU : {self.snu_str}\n"
                                       f"HW  : v{self.device_version-(FLAM_V1-1)}\n"
                                       f"FW (main) : {self.fw_main}\n"
                                       f"FW (comm) : {self.fw_comm}\n"
                                       f"VID/PID : 0x{vid:04X} / 0x{pid:04X}\n")

    def update_pack_index(self):
        lib_path = Path(self.mount_point).joinpath("etc/library/")
        list_path = Path(self.mount_point).joinpath("etc/library/list")
        list_path.unlink(missing_ok=True)
        lib_path.mkdir(parents=True, exist_ok=True)
        with open(list_path, "w") as fp:
            for story in self.stories:
                fp.write(str(story.uuid) + "\n")
        return

    def remove_story(self, short_uuid):
        if short_uuid not in self.stories:
            self.signal_logger.emit(logging.ERROR, "This story is not present on your storyteller")
            return False

        slist = self.stories.matching_stories(short_uuid)
        if len(slist) > 1:
            self.signal_logger.emit(logging.ERROR, f"at least {len(slist)} match your pattern. Try a longer UUID.")
            return False
        uuid = slist[0].str_uuid

        self.signal_logger.emit(logging.INFO, f"🚧 Removing {uuid[28:]} - {self.stories.get_story(uuid).name}...")

        short_uuid = uuid[28:]
        self.signal_story_progress.emit(short_uuid, 0, 3)

        # removing story contents
        st_path = Path(self.mount_point).joinpath(f"str/{str(uuid)}")
        if os.path.isdir(st_path):
            try:
                shutil.rmtree(st_path)
            except OSError as e:
                self.signal_logger.emit(logging.ERROR, e)
                return False
            except PermissionError as e:
                self.signal_logger.emit(logging.ERROR, e)
                return False

        self.signal_story_progress.emit(short_uuid, 1, 3)

        # removing story from class
        self.stories.remove(slist[0])
        # updating pack index file
        self.update_pack_index()

        self.signal_story_progress.emit(short_uuid, 2, 3)

        return True

# opens the .pi file to read all installed stories
def feed_stories(root_path) -> StoryList[UUID]:
    logger = logging.getLogger(LUNII_LOGGER)

    mount_path = Path(root_path)
    list_path = mount_path.joinpath("etc/library/list")

    story_list = StoryList()

    logger.log(logging.INFO, f"Reading Flam loaded stories...")

    # no pi file, done
    if not os.path.isfile(list_path):
        return story_list

    with open(list_path, "r") as fp_list:
        lines = fp_list.read().splitlines()
        for uuid_str in lines:
            one_uuid = UUID(uuid_str)
            logger.log(logging.DEBUG, f"- {str(one_uuid)}")
            story_list.append(Story(one_uuid))

    logger.log(logging.INFO, f"Read {len(story_list)} stories")
    return story_list

def is_flam(root_path):
    root_path = Path(root_path)
    md_path = root_path.joinpath(".mdf")

    try:
        if md_path.is_file():
            return True
    except PermissionError as e:
        pass
    return False
