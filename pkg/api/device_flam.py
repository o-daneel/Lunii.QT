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


class FlamDevice():
    def __init__(self, mount_point, keyfile=None):
        super().__init__()
        self.mount_point = mount_point

    @property
    def snu_str(self):
        return self.snu.hex().upper().lstrip("0")

    # opens the .pi file to read all installed stories
    def __feed_device(self):

        mount_path = Path(self.mount_point)
        md_path = mount_path.joinpath(".mdf")

        # checking if specified path is acceptable
        if not os.path.isfile(md_path):
            return False

        with open(md_path, "rb") as fp_md:
            md_version = int.from_bytes(fp_md.read(2), 'little')
            #
            # if md_version == 6:
            #     self.__md6_parse(fp_md)
            # else:
            #     self.__md1to5_parse(fp_md)
        return True


def is_flam(root_path):
    root_path = Path(root_path)
    md_path = root_path.joinpath(".mdf")

    try:
        if md_path.is_file():
            return True
    except PermissionError as e:
        pass
    return False
