import json
import os.path
import shutil
import zipfile
import binascii
import logging
from uuid import UUID

import psutil
import py7zr

from Crypto.Cipher import AES
from PySide6 import QtCore

from pkg.api import stories
from pkg.api.aes_keys import reverse_bytes
from pkg.api.constants import *
from pkg.api.device_lunii import secure_filename
from pkg.api.stories import FILE_META, FILE_THUMB, FILE_UUID, StoryList, Story, story_is_flam, story_is_flam_plain, story_is_lunii_plain, story_is_plain, story_is_studio, story_is_lunii

LIB_BASEDIR = "etc/library/"
LIB_CACHE = "usr/0/library.cache"


class FlamDevice(QtCore.QObject):
    STORIES_BASEDIR = "str/"

    signal_story_progress = QtCore.Signal(str, int, int)
    signal_logger = QtCore.Signal(int, str)
    stories: StoryList

    def __init__(self, mount_point):
        super().__init__()
        self.mount_point = mount_point

        # dummy values
        self.lunii_version = 0
        self.UUID = ""
        self.snu = b""
        self.fw_main = "?.?.?"
        self.fw_comm = "?.?.?"
        self.memory_left = 0

        self.story_key = None
        self.story_iv = None
        self.keyfile = b""

        self.debug_plain = False
        self.abort_process = False

        # internal device details
        if not self.__feed_device():
            return

        # loading internal stories + pi update for duplicates filtering
        self.stories = feed_stories(self.mount_point)
        self.update_pack_index()

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
            self.__mdf_parse(fp_mdf)
        return True

    def __mdf_parse(self, fp_mdf):
        fp_mdf.seek(2)

        # parsing firmware versions
        raw = fp_mdf.read(48)
        raw_str = raw.decode('utf-8').strip('\x00')
        raw_str = raw_str.replace("main: ", "").replace("comm: ", "")
        versions = raw_str.splitlines()

        self.fw_main = versions[0].split("-")[0]
        if len(versions) > 1:
            self.fw_comm = versions[1].split("-")[0]

        # parsing snu
        snu_str = fp_mdf.read(24).decode('utf-8').rstrip('\x00')
        self.snu = binascii.unhexlify(snu_str)

        # parsing VID/PID
        vid = int.from_bytes(fp_mdf.read(2), 'little')
        pid = int.from_bytes(fp_mdf.read(2), 'little')

        logger = logging.getLogger(LUNII_LOGGER)

        # major v2 use decipher trick
        if self.fw_main.startswith("1."):
            fp_mdf.seek(0x4E)
            self.keyfile = fp_mdf.read(32)
            self.story_key = binascii.hexlify(self.snu) + b"\x00\x00"
            self.story_iv  = b"\x00\x00\x00\x00\x00\x00\x00\x00" + binascii.hexlify(self.snu)[:8]
        else:
            fp_mdf.seek(0x4E)
            self.keyfile = binascii.hexlify(self.snu) + b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00" + binascii.hexlify(self.snu)[:8]
            self.story_key = fp_mdf.read(16)
            self.story_iv = fp_mdf.read(16)

        # checking if md backup file is available 
        FLAM_MD = os.path.join(CFG_DIR, f"{self.snu_str}.v{self.fw_main}.mdf")
        if not os.path.isfile(FLAM_MD):
            logger.log(logging.INFO, f"No backup of v{self.fw_main} metadata file found, creating one...")
            # creating backup of md file
            with open(FLAM_MD, "wb") as fp_mdf_bak:
                fp_mdf.seek(0)
                fp_mdf_bak.write(fp_mdf.read())

        if (vid, pid) == FLAM_USB_VID_PID:
            self.device_version = FLAM_V1
        else:
            self.device_version = UNDEF_DEV

        logger.log(logging.DEBUG, f"\n"
                                       f"SNU : {self.snu_str}\n"
                                       f"HW  : v{self.device_version-(FLAM_V1-1)}\n"
                                       f"FW (main) : {self.fw_main}\n"
                                       f"FW (comm) : {self.fw_comm}\n"
                                       f"VID/PID : 0x{vid:04X} / 0x{pid:04X}")

    def update_pack_index(self):
        lib_path = Path(self.mount_point).joinpath(LIB_BASEDIR)

        # deleting previous files
        list_path = lib_path.joinpath("list")
        list_hidden_path = lib_path.joinpath("list.hidden")
        list_path.unlink(missing_ok=True)
        list_hidden_path.unlink(missing_ok=True)
        # cleaning library cache
        lib_cache = lib_path.joinpath(LIB_CACHE)
        lib_cache.unlink(missing_ok=True)
        
        # creating target dir
        lib_path.mkdir(parents=True, exist_ok=True)

        # writing file
        with open(list_path, "w", newline='\n') as fp, open(list_hidden_path, "w", newline='\n') as fp_hidden:
            for story in self.stories:
                if story.hidden:
                    fp_hidden.write(str(story.uuid) + "\n")
                else:
                    fp.write(str(story.uuid) + "\n")
        return

    def __valid_story(self, story_dir):
        return True

    def recover_stories(self, dry_run: bool):
        recovered = 0

        # getting all stories
        content_dir = os.path.join(self.mount_point, self.STORIES_BASEDIR)
        stories_dir = [entry for entry in os.listdir(content_dir) if os.path.isdir(os.path.join(content_dir, entry))]

        for index, story in enumerate(stories_dir):
            # directory is a partial UUID
            self.signal_story_progress.emit(story, index, len(stories_dir))

            str_uuid = None
            # looking complete UUID in official DB
            if not str_uuid:
                str_uuid = next((uuid for uuid in stories.DB_OFFICIAL if story.upper() in uuid.upper()), None)
            # looking complete UUID in third party DB
            if not str_uuid:
                str_uuid = next((uuid for uuid in stories.DB_THIRD_PARTY if story.upper() in uuid.upper()), None)
            if not str_uuid:
                str_uuid = story

            # prepare for story analysis
            try:
                full_uuid = UUID(str_uuid)
            except (TypeError, ValueError) as e:
                self.signal_logger.emit(logging.DEBUG, f"Not a valid UUID - {str_uuid}")
                continue

            one_story = Story(full_uuid)
            story_dir = os.path.join(content_dir, story)

            if str_uuid not in self.stories:
                # Lost Story
                if self.__valid_story(story_dir):

                    # is it a dry run ?
                    if not dry_run:
                        self.signal_logger.emit(logging.INFO, f"Recovered - {str(full_uuid).upper()} - {one_story.name}")
                        self.stories.append(Story(full_uuid))
                    else:
                        self.signal_logger.emit(logging.INFO, f"Found - {str(full_uuid).upper()} - {one_story.name}")
                    recovered += 1
                else:
                    self.signal_logger.emit(logging.INFO, f"Skipping lost story (seems broken/incomplete) - {str(full_uuid).upper()} - {one_story.name}")
            else:
                # In DB story
                if not self.__valid_story(story_dir):
                    self.signal_logger.emit(logging.WARNING, f"Already in list but invalid - {str(full_uuid).upper()} - {one_story.name}")
                else:
                    self.signal_logger.emit(logging.DEBUG, f"Already in list - {str(full_uuid).upper()} - {one_story.name}")

        return recovered

    def cleanup_stories(self):
        removed = 0
        recovered_size = 0

        # getting all stories
        content_dir = os.path.join(self.mount_point, self.STORIES_BASEDIR)
        stories_dir = [entry for entry in os.listdir(content_dir) if os.path.isdir(os.path.join(content_dir, entry))]

        for index, story in enumerate(stories_dir):
            # directory is a partial UUID
            self.signal_story_progress.emit(story, index, len(stories_dir))

            if story not in self.stories:
                # remove it
                try:
                    lost_story_path = os.path.join(content_dir, story)

                    # computing lost size
                    for parent_dir, _, files in os.walk(lost_story_path):
                        for file in files:
                            recovered_size += os.path.getsize(os.path.join(parent_dir, file))

                    # removing whole directory
                    self.signal_logger.emit(logging.INFO, f"Deleting - {lost_story_path}")
                    shutil.rmtree(lost_story_path)
                    removed += 1
                except (OSError, PermissionError) as e:
                    self.signal_logger.emit(logging.WARN, f"Failed to delete - {lost_story_path}")
                    self.signal_logger.emit(logging.ERROR, e)

        return removed, recovered_size//1024//1024

    def __v3_cipher(self, buffer, key, iv, offset, enc_len):
        # checking offset
        if offset > len(buffer):
            offset = len(buffer)
        # checking len
        if offset + enc_len > len(buffer):
            enc_len = len(buffer) - offset
        # checking padding
        if enc_len % 16 != 0:
            padlen = 16 - len(buffer) % 16
            buffer += b"\x00" * padlen
            enc_len += padlen
        # if something to be done
        if offset < len(buffer) and offset + enc_len <= len(buffer):
            cipher = AES.new(key, AES.MODE_CBC, iv)
            ciphered = cipher.encrypt(buffer[offset:enc_len])
            ba_buffer = bytearray(buffer)
            ba_buffer[offset:enc_len] = ciphered
            buffer = bytes(ba_buffer)
        return buffer

    def decipher(self, buffer, key, iv, offset, dec_len):
        # checking offset
        if offset > len(buffer):
            offset = len(buffer)
        # checking len
        if offset + dec_len > len(buffer):
            dec_len = len(buffer) - offset
        # if something to be done
        if offset < len(buffer) and offset + dec_len <= len(buffer):
            decipher = AES.new(key, AES.MODE_CBC, iv)
            plain = decipher.decrypt(buffer[offset:dec_len])
            ba_buffer = bytearray(buffer)
            ba_buffer[offset:dec_len] = plain
            buffer = bytes(ba_buffer)
        return buffer
    
    def cipher(self, buffer, key, iv=None, offset=0, enc_len=512):
        if self.debug_plain:
            return buffer

        return self.__v3_cipher(buffer, key, iv, offset, enc_len)

    def __get_ciphered_data(self, file, data, flam_story, force=False):
        if not flam_story:
            # LUNII
            key = reverse_bytes(self.story_key)
            iv = reverse_bytes(self.story_iv)

            if file.endswith("ni") or file.endswith("nm"):
                key = None
        else:
            # FLAM
            key = None
            if file.endswith(".lua") or file.endswith(".plain") or force:
                key = self.story_key
                iv = self.story_iv

        # data len to cipher
        cipher_len = len(data) if flam_story else 0x200

        # process file with correct key
        if key:
            return self.cipher(data, key, iv, enc_len=cipher_len)

        return data

    def  __get_flam_ciphered_name(self, file: str):
        file = file.removesuffix('.plain')
        
        if file.endswith(".lua"):
            file = file.replace(".lua", ".lsf")

        return file

    def __get_lunii_ciphered_name(self, file: str, studio_ri=False, studio_si=False):
        file = file.removesuffix('.plain')

        if studio_ri:
            file = f"rf/000/{file}"
        if studio_si:
            file = f"sf/000/{file}"

        file = file.lower().removesuffix('.mp3')
        file = file.lower().removesuffix('.bmp')

        # upcasing filename
        bn = os.path.basename(file)
        if len(bn) >= 8:
            file = os.path.join(os.path.dirname(file), bn.upper())

        # upcasing uuid dir if present
        dn = os.path.dirname(file)
        if len(dn) >= 8:
            dir_head = file[0:8]
            if "/" not in dir_head and "\\" not in dir_head:
                file = dir_head.upper() + file[8:]
        file = file.replace("\\", "/")

        # self.signal_logger.emit(logging.DEBUG, f"Target file : {file}")
        return file

    def __archive_check_plain(self, story_path):
        archive_type = TYPE_UNK
        
        # trying to guess plain contents
        with zipfile.ZipFile(file=story_path) as zip_file:
            # reading all available files
            zip_contents = zip_file.namelist()

            if not story_is_plain(zip_contents):
                return TYPE_UNK

            # lua files ?
            if story_is_flam_plain(zip_contents):
                archive_type = TYPE_FLAM_PLAIN
            # lunii files ?
            elif story_is_lunii_plain(zip_contents):
                archive_type = TYPE_LUNII_PLAIN

        return archive_type

    def __archive_check_flam_zipcontent(self, story_path):
        archive_type = TYPE_UNK
        
        # trying to guess plain contents
        with zipfile.ZipFile(file=story_path) as zip_file:
            # reading all available files
            zip_contents = zip_file.namelist()

            # lsf files ?
            if story_is_flam(zip_contents):
                archive_type = TYPE_FLAM_ZIP
            # lunii files ?
            elif story_is_lunii(zip_contents):
                archive_type = TYPE_LUNII_ZIP
            # studio files ?
            elif story_is_studio(zip_contents):
                archive_type = TYPE_STUDIO_ZIP

        return archive_type

    def __archive_check_flam_7zcontent(self, story_path):
        archive_type = TYPE_UNK
        
        # opening zip file
        with py7zr.SevenZipFile(story_path, mode='r') as zip:
            # reading all available files
            zip_contents = zip.getnames()

            # lsf files ?
            if story_is_flam(zip_contents):
                archive_type = TYPE_FLAM_7Z
            # lunii files ?
            elif story_is_lunii(zip_contents):
                archive_type = TYPE_LUNII_7Z
            # studio files ?
            elif story_is_studio(zip_contents):
                archive_type = TYPE_STUDIO_7Z

        return archive_type

    def import_story(self, story_path):
        archive_type = TYPE_UNK

        self.signal_logger.emit(logging.INFO, f"🚧 Loading {story_path}...")

        archive_size = os.path.getsize(story_path)
        free_space = psutil.disk_usage(str(self.mount_point)).free
        if archive_size >= free_space:
            self.signal_logger.emit(logging.ERROR, f"Not enough space left on Flam (only {free_space//1024//1024}MB)")
            return False

        # identifying based on filename
        if story_path.lower().endswith(EXT_PK_PLAIN):
            archive_type = self.__archive_check_plain(story_path)
        elif story_path.lower().endswith(EXT_ZIP):
            archive_type = self.__archive_check_flam_zipcontent(story_path)
        elif story_path.lower().endswith(EXT_7z):
            archive_type = self.__archive_check_flam_7zcontent(story_path)

        # processing story
        if archive_type in [TYPE_FLAM_ZIP, TYPE_FLAM_7Z, TYPE_FLAM_PLAIN]:
            self.signal_logger.emit(logging.WARN, "😮‍💨 This process is veeeeeeeeery long due to Flam firmware. 😴 Be patient ...")

        # processing story
        if archive_type == TYPE_LUNII_PLAIN:
            self.signal_logger.emit(logging.DEBUG, "Archive => TYPE_LUNII_PLAIN")
            return self.import_lunii_plain(story_path)
        elif archive_type == TYPE_FLAM_PLAIN:
            self.signal_logger.emit(logging.DEBUG, "Archive => TYPE_FLAM_PLAIN")
            return self.import_flam_plain(story_path)
        elif archive_type == TYPE_FLAM_ZIP:
            self.signal_logger.emit(logging.DEBUG, "Archive => TYPE_FLAM_ZIP")
            return self.import_flam_zip(story_path)
        elif archive_type == TYPE_FLAM_7Z:
            self.signal_logger.emit(logging.DEBUG, "Archive => TYPE_FLAM_7Z")
            return self.import_flam_7z(story_path)
        elif archive_type == TYPE_LUNII_ZIP:
            self.signal_logger.emit(logging.DEBUG, "Archive => TYPE_LUNII_ZIP")
            return None
            # return self.import_lunii_zip(story_path)
        elif archive_type == TYPE_LUNII_7Z:
            self.signal_logger.emit(logging.DEBUG, "Archive => TYPE_LUNII_7Z")
            return None
            # return self.import_lunii_7z(story_path)
        elif archive_type == TYPE_STUDIO_ZIP:
            self.signal_logger.emit(logging.DEBUG, "Archive => TYPE_STUDIO_ZIP")
            return None
            # return self.import_story_studio_zip(story_path)
        elif archive_type == TYPE_STUDIO_7Z:
            self.signal_logger.emit(logging.DEBUG, "Archive => TYPE_STUDIO_7Z")
            return None
            # return self.import_story_studio_7z(story_path)
        else:
            self.signal_logger.emit(logging.DEBUG, "Archive => Unsupported type")

        return None
    
    def import_lunii_plain(self, story_path):
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
            if FILE_UUID not in zip_contents:
                self.signal_logger.emit(logging.ERROR, "No UUID file found in archive. Unable to add this story.")
                return False

            # getting UUID file
            try:
                new_uuid = UUID(bytes=zip_file.read(FILE_UUID))
            except ValueError as e:
                self.signal_logger.emit(logging.ERROR, e)
                return False

            # checking if UUID already loaded
            if str(new_uuid) in self.stories:
                self.signal_logger.emit(logging.WARNING, f"'{self.stories.get_story(new_uuid).name}' is already loaded !")
                return False

            # thirdparty story ?
            if FILE_META in zip_contents:
                # creating story entry in thirdparty db
                meta = zip_file.read(FILE_META)
                s_meta = json.loads(meta)
                if s_meta.get("uuid").upper() != str(new_uuid).upper():
                    return False
                stories.thirdparty_db_add_story(new_uuid, s_meta.get("title"), s_meta.get("description"))
            if FILE_THUMB in zip_contents:
                # creating story picture in cache
                image_data = zip_file.read(FILE_THUMB)
                stories.thirdparty_db_add_thumb(new_uuid, image_data)

            # decompressing story contents
            long_uuid = str(new_uuid).lower()
            short_uuid = long_uuid[28:]
            output_path = Path(self.mount_point).joinpath(f"{self.STORIES_BASEDIR}{long_uuid}")
            if not output_path.exists():
                output_path.mkdir(parents=True)

            # Loop over each file
            for index, file in enumerate(zip_contents):
                self.signal_story_progress.emit(short_uuid, index, len(zip_contents))
                # abort requested ? early exit
                if self.abort_process:
                    self.signal_logger.emit(logging.WARNING, f"Import aborted, performing cleanup on current story...")
                    self.__clean_up_story_dir(new_uuid)
                    return False

                # skipping .plain.pk specific files 
                if file in [FILE_UUID, FILE_META, FILE_THUMB]:
                    continue
                if file.endswith("bt"):
                    continue

                # checking zip content
                info = zip_file.getinfo(file)
                if info.is_dir():
                    continue

                # Extract each zip file
                data_plain = zip_file.read(file)

                # updating filename, and ciphering header if necessary
                data = self.__get_ciphered_data(file, data_plain, False)
                file_newname = self.__get_lunii_ciphered_name(file)

                target: Path = output_path.joinpath(file_newname)

                # create target directory
                if not target.parent.exists():
                    target.parent.mkdir(parents=True)
                # write target file
                self.signal_logger.emit(logging.DEBUG, f"File {index+1}/{len(zip_contents)} > {file_newname}")
                with open(target, "wb") as f_dst:
                    f_dst.write(data)

        # keyfile creation
        self.signal_logger.emit(logging.INFO, "Authorization file creation...")
        bt_path = output_path.joinpath("key")
        with open(bt_path, "wb") as fp_bt:
            fp_bt.write(self.keyfile)

        # story creation
        loaded_story = Story(new_uuid)

        # creating info file creation
        info_path = output_path.joinpath("info")
        with open(info_path, "w") as fp_info:
            fp_info.write(f"{loaded_story.name}\n")
            fp_info.write(f"{loaded_story.name}\n")
            fp_info.write("0\n")
            fp_info.write(f"{loaded_story.name}\n")
            fp_info.write(loaded_story.author)

        # updating .pi file to add new UUID
        self.stories.append(loaded_story)
        self.update_pack_index()

        return True

    def import_flam_plain(self, story_path):
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
            if FILE_UUID not in zip_contents:
                self.signal_logger.emit(logging.ERROR, "No UUID file found in archive. Unable to add this story.")
                return False

            # getting UUID file
            try:
                new_uuid = UUID(bytes=zip_file.read(FILE_UUID))
            except ValueError as e:
                self.signal_logger.emit(logging.ERROR, e)
                return False

            # checking if UUID already loaded
            if str(new_uuid) in self.stories:
                self.signal_logger.emit(logging.WARNING, f"'{self.stories.get_story(new_uuid).name}' is already loaded !")
                return False

            # decompressing story contents
            long_uuid = str(new_uuid).lower()
            short_uuid = long_uuid[28:]
            output_path = Path(self.mount_point).joinpath(f"{self.STORIES_BASEDIR}{long_uuid}")
            if not output_path.exists():
                output_path.mkdir(parents=True)

            # Loop over each file
            for index, file in enumerate(zip_contents):
                self.signal_story_progress.emit(short_uuid, index, len(zip_contents))
                # abort requested ? early exit
                if self.abort_process:
                    self.signal_logger.emit(logging.WARNING, f"Import aborted, performing cleanup on current story...")
                    self.__clean_up_story_dir(new_uuid)
                    return False

                # skipping .plain.pk specific files 
                if file in [FILE_UUID, FILE_META, FILE_THUMB]:
                    continue

                # checking zip content
                info = zip_file.getinfo(file)
                if info.is_dir():
                    continue

                # Extract each zip file
                data_plain = zip_file.read(file)

                # updating filename, and ciphering header if necessary
                data = self.__get_ciphered_data(file, data_plain, True)
                file_newname = self.__get_flam_ciphered_name(file)

                target: Path = output_path.joinpath(file_newname)

                # create target directory
                if not target.parent.exists():
                    target.parent.mkdir(parents=True)
                # write target file
                self.signal_logger.emit(logging.DEBUG, f"File {index+1}/{len(zip_contents)} > {file_newname}")
                with open(target, "wb") as f_dst:
                    f_dst.write(data)

        # keyfile creation
        self.signal_logger.emit(logging.INFO, "Authorization file creation...")
        bt_path = output_path.joinpath("key")
        with open(bt_path, "wb") as fp_bt:
            fp_bt.write(self.keyfile)

        # story creation
        loaded_story = Story(new_uuid)

         # updating .pi file to add new UUID
        self.stories.append(loaded_story)
        self.update_pack_index()

        return True
    
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

            if story_is_lunii(zip_contents) or story_is_studio(zip_contents):
                self.signal_logger.emit(logging.ERROR, f"Archive seems to be made of Lunii story (not compatible with Flam)")
                return False

            # checking for keyfile
            storykeys_file = [entry for entry in zip_contents if entry.endswith("bt")]
            if storykeys_file:
                self.signal_logger.emit(logging.INFO, "Transciphering Flam story")
                data = zip_file.read(storykeys_file[0])
                story_key = data[:16]
                story_iv = data[16:]
            else:
                keyfile = [entry for entry in zip_contents if entry.endswith("key")]
                if not keyfile:
                    self.signal_logger.emit(logging.ERROR, "Flam story backup is incomplete, missing key file.")
                    return False
                self.signal_logger.emit(logging.INFO, "Restoring Flam story backup")

            # getting UUID from path
            uuid_path = Path(zip_contents[0])
            uuid_str = uuid_path.parents[0].name if uuid_path.parents[0].name else uuid_path.name

            if len(uuid_str) >= 16:  # long enough to be a UUID
                # self.signal_logger.emit(logging.DEBUG, uuid_str)
                try:
                    if "-" not in uuid_str:
                        new_uuid = UUID(bytes=binascii.unhexlify(uuid_str))
                    else:
                        new_uuid = UUID(uuid_str)
                except ValueError as e:
                    self.signal_logger.emit(logging.ERROR, f"UUID parse error {e}")
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
            output_path = Path(self.mount_point).joinpath(f"{self.STORIES_BASEDIR}")
            if not output_path.exists():
                output_path.mkdir(parents=True)

            # Loop over each file
            for index, file in enumerate(zip_contents):
                if self.abort_process:
                    self.signal_logger.emit(logging.WARNING, f"Import aborted, performing cleanup on current story...")
                    self.__clean_up_story_dir(new_uuid)
                    return False

                self.signal_story_progress.emit(short_uuid, index, len(zip_contents))

                if zip_file.getinfo(file).is_dir():
                    continue

                # Extract each zip file
                self.signal_logger.emit(logging.DEBUG, f"File {index+1}/{len(zip_contents)} > {file}")
                data = zip_file.read(file)

                # transcoding if necessary
                if storykeys_file:
                    if (file.endswith(".lsf") or file.endswith("info")):
                        self.signal_logger.emit(logging.DEBUG, f"Transciphering file {file}")
                        # decipher
                        data_plain = self.decipher(data, story_key, story_iv, 0, len(data))
                        # cipher
                        data = self.__get_ciphered_data(file, data_plain, True, True)

                target: Path = output_path.joinpath(file)

                # create target directory
                if not target.parent.exists():
                    target.parent.mkdir(parents=True)
                # write target file
                with open(target, "wb") as f_dst:
                    f_dst.write(data)

        # keyfile creation due to transciphering
        if storykeys_file:
            self.signal_logger.emit(logging.INFO, "Authorization file creation...")
            new_keyfile = os.path.join(output_path, str(new_uuid), "key")
            with open(new_keyfile, "wb") as fp_key:
                fp_key.write(self.keyfile)

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

        # opening zip file
        with py7zr.SevenZipFile(story_path, mode='r') as zip:
            # reading all available files
            zip_contents = zip.getnames()
            if story_is_lunii(zip_contents) or story_is_studio(zip_contents):
                self.signal_logger.emit(logging.ERROR, f"Archive seems to be made of Lunii story (not compatible with Flam)")
                return False

            # reading all available files
            zip_contents = zip.list()

            # checking for keyfile
            storykeys_file = [entry for entry in zip_contents if entry.filename.endswith("bt")]
            if storykeys_file:
                self.signal_logger.emit(logging.INFO, "Transciphering Flam story")
                dict = zip.read([storykeys_file[0].filename])
                data = dict[storykeys_file[0].filename].read()
                story_key = data[:16]
                story_iv = data[16:]
            else:
                keyfile = [entry for entry in zip_contents if entry.filename.endswith("key")]
                if not keyfile:
                    self.signal_logger.emit(logging.ERROR, "Flam story backup is incomplete, missing key file.")
                    return False
                self.signal_logger.emit(logging.INFO, "Restoring Flam story backup")

        # reopening zip file (SevenZip must work sequentially)
        with py7zr.SevenZipFile(story_path, mode='r') as zip:
            # reading all available files
            zip_contents = zip.list()

            # getting UUID from path
            uuid_path = Path(zip_contents[0].filename)
            uuid_str = uuid_path.parents[0].name if uuid_path.parents[0].name else uuid_path.name
            if len(uuid_str) >= 16:  # long enough to be a UUID
                # self.signal_logger.emit(logging.DEBUG, uuid_str)
                try:
                    if "-" not in uuid_str:
                        new_uuid = UUID(bytes=binascii.unhexlify(uuid_str))
                    else:
                        new_uuid = UUID(uuid_str)
                except ValueError as e:
                    self.signal_logger.emit(logging.ERROR, f"UUID parse error {e}")
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
            output_path = Path(self.mount_point).joinpath(f"{self.STORIES_BASEDIR}")
            if not output_path.exists():
                output_path.mkdir(parents=True)

            # Loop over each file
            self.signal_logger.emit(logging.INFO, "Reading 7zip archive... (takes time)")
            contents = zip.readall().items()
            for index, (fname, bio) in enumerate(contents):

                # abort requested ? early exit
                if self.abort_process:
                    self.signal_logger.emit(logging.WARNING, f"Import aborted, performing cleanup on current story...")
                    self.__clean_up_story_dir(new_uuid)
                    return False

                self.signal_story_progress.emit(short_uuid, index, len(contents))

                # Extract each zip file
                data = bio.read()

                self.signal_logger.emit(logging.DEBUG, f"File {index+1}/{len(contents)} > {fname}")

                # transcoding if necessary
                if storykeys_file:
                    if (fname.endswith(".lsf") or fname.endswith("info")):
                        self.signal_logger.emit(logging.DEBUG, f"Transciphering file {fname}")
                        # decipher
                        data_plain = self.decipher(data, story_key, story_iv, 0, len(data))
                        # cipher
                        data = self.__get_ciphered_data(fname, data_plain, True, True)

                target: Path = output_path.joinpath(fname)

                # create target directory
                if not target.parent.exists():
                    target.parent.mkdir(parents=True)
                # write target file
                with open(target, "wb") as f_dst:
                    f_dst.write(data)

        # keyfile creation due to transciphering
        if storykeys_file:
            self.signal_logger.emit(logging.INFO, "Authorization file creation...")
            new_keyfile = os.path.join(output_path, str(new_uuid), "key")
            with open(new_keyfile, "wb") as fp_key:
                fp_key.write(self.keyfile)

        # updating .pi file to add new UUID
        self.stories.append(Story(new_uuid))
        self.update_pack_index()

        return True

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
        content_path = Path(self.mount_point).joinpath(self.STORIES_BASEDIR)
        if not content_path.is_dir():
            return None
        story_path = content_path.joinpath(str(one_story.uuid))
        if not story_path.is_dir():
            return None

        self.signal_logger.emit(logging.INFO, f"🚧 Exporting {one_story.short_uuid} - {one_story.name}")

        # Preparing zip file
        sname = one_story.name
        sname = secure_filename(sname)

        zip_path = Path(out_path).joinpath(f"{sname}.{one_story.short_uuid}.zip")
        # if os.path.isfile(zip_path):
        #     self.signal_logger.emit(logging.WARNING, f"Already exported")
        #     return None

        # preparing file list
        story_flist = []
        story_arcnames = []
        for root, _, filenames in os.walk(story_path):
            for filename in filenames:
                abs_file = os.path.join(root, filename)
                story_flist.append(abs_file)

                index = abs_file.find(str(one_story.uuid))
                story_arcnames.append(abs_file[index:])

        try:
            with zipfile.ZipFile(zip_path, 'w') as zip_out:
                self.signal_logger.emit(logging.DEBUG, "> Zipping story ...")
                for index, file in enumerate(story_flist):
                    # abort requested ? early exit
                    if self.abort_process:
                        return None

                    self.signal_story_progress.emit(one_story.short_uuid, index, len(story_flist))
                    self.signal_logger.emit(logging.DEBUG, story_arcnames[index])
                    zip_out.write(file, story_arcnames[index])

        except PermissionError as e:
            self.signal_logger.emit(logging.ERROR, f"failed to create ZIP - {e}")
            return None

        return zip_path

    def __clean_up_story_dir(self, story_uuid: UUID):
        story_dir = Path(self.mount_point).joinpath(f"{self.STORIES_BASEDIR}{str(story_uuid)}")
        if os.path.isdir(story_dir):
            try:
                shutil.rmtree(story_dir)
            except OSError as e:
                self.signal_logger.emit(logging.ERROR, e)
                return False
            except PermissionError as e:
                self.signal_logger.emit(logging.ERROR, e)
                return False
        return True

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
        if not self.__clean_up_story_dir(slist[0].uuid):
            return False

        self.signal_story_progress.emit(short_uuid, 1, 3)

        # removing story from class
        self.stories.remove(slist[0])
        # updating pack index file
        self.update_pack_index()

        self.signal_story_progress.emit(short_uuid, 2, 3)

        return True

    #TODO
    def factory_reset(self):
        print("factory_reset")
        pass


# opens the .pi file to read all installed stories
def feed_stories(root_path) -> StoryList[UUID]:
    logger = logging.getLogger(LUNII_LOGGER)

    mount_path = Path(root_path)
    list_path = mount_path.joinpath(LIB_BASEDIR + "list")
    list_hidden_path = mount_path.joinpath(LIB_BASEDIR + "list.hidden")

    story_list = StoryList()

    logger.log(logging.INFO, f"Reading Flam loaded stories...")

    # if there is a list
    if os.path.isfile(list_path):
        with open(list_path, "r") as fp_list:
            lines = fp_list.read().splitlines()
            for uuid_str in lines:
                one_uuid = UUID(uuid_str.strip())
                logger.log(logging.DEBUG, f"> {str(one_uuid)}")
                if one_uuid in story_list:
                    logger.log(logging.WARNING, f"Found duplicate story, cleaning...")
                else:
                    story_list.append(Story(one_uuid))

    story_count = len(story_list)
    logger.log(logging.INFO, f"Read {len(story_list)} stories")

    # if there is a hidden list
    if os.path.isfile(list_hidden_path):
        with open(list_hidden_path, "r") as fp_list:
            lines = fp_list.read().splitlines()
            for uuid_str in lines:
                one_uuid = UUID(uuid_str.strip())
                logger.log(logging.DEBUG, f"> {str(one_uuid)}")
                if one_uuid in story_list:
                    logger.log(logging.WARNING, f"Found duplicate story, cleaning...")
                else:
                    story_list.append(Story(one_uuid, True))

    logger.log(logging.INFO, f"Read {len(story_list) - story_count} hidden stories")
    return story_list


def is_flam(root_path):
    MDF_FILE = os.path.join(root_path, ".mdf")

    try:
        if os.path.isfile(MDF_FILE):
            return True
    except PermissionError:
        pass
    return False


