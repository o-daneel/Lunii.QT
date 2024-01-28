import os.path
import shutil
import zipfile
import binascii
import logging
from uuid import UUID

import psutil
import py7zr
from PySide6 import QtCore

from pkg.api.constants import *
from pkg.api.device_lunii import secure_filename
from pkg.api.stories import StoryList, Story


STORIES_BASEDIR = "str/"
LIB_BASEDIR = "etc/library/"


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

    @property
    def snu_hex(self):
        return self.snu

    def __repr__(self):
        repr_str = f"Flam device on \"{self.mount_point}\"\n"
        repr_str += f"- Main firmware : v{self.fw_main}\n"
        repr_str += f"- Comm firmware : v{self.fw_comm}\n"
        repr_str += f"- SNU      : {binascii.hexlify(self.snu_hex, ' ')}\n"
        repr_str += f"- stories  : {len(self.stories)}x"
        return repr_str


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
        self.fw_main = fws[0].split(b": ")[1].split(b"-")[0].decode('utf-8')
        self.fw_comm = fws[1].split(b": ")[1].split(b"-")[0].decode('utf-8')

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
        lib_path = Path(self.mount_point).joinpath(LIB_BASEDIR)
        list_path = lib_path.joinpath("list")
        list_path.unlink(missing_ok=True)
        lib_path.mkdir(parents=True, exist_ok=True)
        with open(list_path, "w") as fp:
            for story in self.stories:
                fp.write(str(story.uuid) + "\n")
        return

    def import_story(self, story_path):
        archive_type = TYPE_UNK

        self.signal_logger.emit(logging.INFO, f"🚧 Loading {story_path}...")

        archive_size = os.path.getsize(story_path)
        free_space = psutil.disk_usage(str(self.mount_point)).free
        if archive_size >= free_space:
            self.signal_logger.emit(logging.ERROR, f"Not enough space left on Flam (only {free_space//1024//1024}MB)")
            return False

        # identifying based on filename
        if story_path.lower().endswith(EXT_PK_FLAM):
            archive_type = TYPE_FLAM_ZIP
        elif story_path.lower().endswith(EXT_ZIP):
            archive_type = TYPE_FLAM_ZIP
        elif story_path.lower().endswith(EXT_7z):
            archive_type = TYPE_FLAM_7Z

        # processing story
        if archive_type == TYPE_FLAM_ZIP:
            self.signal_logger.emit(logging.DEBUG, "Archive => TYPE_FLAM_ZIP")
            return self.import_flam_zip(story_path)
        elif archive_type == TYPE_FLAM_7Z:
            self.signal_logger.emit(logging.DEBUG, "Archive => TYPE_FLAM_7Z")
            return self.import_flam_7z(story_path)

    def import_flam_zip(self, story_path):
        # checking if archive is OK
        try:
            with zipfile.ZipFile(file=story_path):
                pass  # If opening succeeds, the archive is valid
        except zipfile.BadZipFile as e:
            self.signal_logger.emit(logging.ERROR, e)
            return False

        # opening zip file
        with zipfile.ZipFile(file=story_path) as zip_file:
            # reading all available files
            zip_contents = zip_file.namelist()

            # getting UUID from path
            dir_name = os.path.dirname(zip_contents[0])
            if len(dir_name) >= 16:  # long enough to be a UUID
                # self.signal_logger.emit(logging.DEBUG, dir_name)
                try:
                    if "-" not in dir_name:
                        new_uuid = UUID(bytes=binascii.unhexlify(dir_name))
                    else:
                        new_uuid = UUID(dir_name)
                except ValueError as e:
                    self.signal_logger.emit(logging.ERROR, e)
                    return False
            else:
                self.signal_logger.emit(logging.ERROR, "UUID directory is missing in archive !")
                return False

            # checking if UUID already loaded
            if str(new_uuid) in self.stories:
                self.signal_logger.emit(logging.WARNING, f"'{self.stories.get_story(new_uuid).name}' is already loaded, aborting !")
                return False

            # decompressing story contents
            short_uuid = str(new_uuid).upper()[28:]
            output_path = Path(self.mount_point).joinpath(f"{STORIES_BASEDIR}")
            if not output_path.exists():
                output_path.mkdir(parents=True)

            # Loop over each file
            for index, file in enumerate(zip_contents):
                self.signal_story_progress.emit(short_uuid, index, len(zip_contents))

                # Extract each zip file
                data = zip_file.read(file)

                target: Path = output_path.joinpath(file)

                # create target directory
                if not target.parent.exists():
                    target.parent.mkdir(parents=True)
                # write target file
                with open(target, "wb") as f_dst:
                    f_dst.write(data)

        # TODO
        # creating authorization file : key
        # self.signal_logger.emit(logging.INFO, "Authorization file creation...")
        # bt_path = output_path.joinpath(f"{str(new_uuid)}/key")
        # with open(bt_path, "wb") as fp_bt:
        #     fp_bt.write(self.key)

        # updating .pi file to add new UUID
        self.stories.append(Story(new_uuid))
        self.update_pack_index()

        return True
    
    def import_flam_7z(self, story_path):
        # checking if archive is OK
        try:
            with py7zr.SevenZipFile(story_path, mode='r'):
                pass  # If opening succeeds, the archive is valid
        except py7zr.exceptions.Bad7zFile as e:
            self.signal_logger.emit(logging.ERROR, e)
            return False

    def export_story(self, uuid, out_path):
        # is UUID part of existing stories
        if uuid not in self.stories:
            return None

        slist = self.stories.matching_stories(uuid)
        if len(slist) > 1:
            self.signal_logger.emit(logging.ERROR, f"at least {len(slist)} match your pattern. Try a longer UUID.")
            for st in slist:
                self.signal_logger.emit(logging.ERROR, f"[{st.str_uuid} - {st.name}]")
            return None

        one_story = slist[0]

        # checking that .content dir exist
        content_path = Path(self.mount_point).joinpath(STORIES_BASEDIR)
        if not content_path.is_dir():
            return None
        story_path = content_path.joinpath(str(one_story.uuid))
        if not story_path.is_dir():
            return None

        self.signal_logger.emit(logging.INFO, f"🚧 Exporting {one_story.short_uuid} - {one_story.name}")

        # for Lunii v3, checking keys (original or trick)
        # if self.device_version == FLAM_V1:
        #     #TODO

        # Preparing zip file
        sname = one_story.name
        sname = secure_filename(sname)

        zip_path = Path(out_path).joinpath(f"{sname}.{one_story.short_uuid}.flam.pk")
        # if os.path.isfile(zip_path):
        #     self.signal_logger.emit(logging.WARNING, f"Already exported")
        #     return None

        # preparing file list
        story_flist = []
        story_arcnames = []
        for root, _, filenames in os.walk(story_path):
            for filename in filenames:
                #TODO
                # if filename in ["keys"]:
                #     continue
                abs_file = os.path.join(root, filename)
                story_flist.append(abs_file)

                index = abs_file.find(str(one_story.uuid))
                story_arcnames.append(abs_file[index:])

        try:
            with zipfile.ZipFile(zip_path, 'w') as zip_out:
                self.signal_logger.emit(logging.DEBUG, "> Zipping story ...")
                for index, file in enumerate(story_flist):
                    self.signal_story_progress.emit(one_story.short_uuid, index, len(story_flist))
                    self.signal_logger.emit(logging.DEBUG, story_arcnames[index])
                    zip_out.write(file, story_arcnames[index])

        except PermissionError as e:
            self.signal_logger.emit(logging.ERROR, f"failed to create ZIP - {e}")
            return None

        return zip_path

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
    list_path = mount_path.joinpath(LIB_BASEDIR + "list")

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
