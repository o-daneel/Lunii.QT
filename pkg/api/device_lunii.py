import glob
import json
import os.path
import shutil
from string import hexdigits
import zipfile
import psutil
import py7zr
import unicodedata
import xxtea
import binascii
import logging
from uuid import UUID

from Crypto.Cipher import AES
from PySide6 import QtCore

from pkg.api.aes_keys import fetch_keys, reverse_bytes
from pkg.api.constants import *
from pkg.api import stories
from pkg.api.convert_audio import audio_to_mp3, transcoding_required, tags_removal_required, mp3_tag_cleanup
from pkg.api.convert_image import image_to_bitmap_rle4
from pkg.api.firmware import FW_HEADERS, FW_SIZES
from pkg.api.stories import FILE_META, FILE_STUDIO_JSON, FILE_STUDIO_THUMB, FILE_THUMB, FILE_UUID, StoryList, Story, StudioStory


class LuniiDevice(QtCore.QObject):
    STORIES_BASEDIR = ".content/"

    signal_story_progress = QtCore.Signal(str, int, int)
    signal_logger = QtCore.Signal(int, str)
    stories: StoryList

    def __init__(self, mount_point, keyfile=None):
        super().__init__()
        self.mount_point = mount_point

        # dummy values
        self.device_version = 0
        self.dev_keyfile = keyfile
        self.device_key = None
        self.device_iv = None
        self.story_key = None
        self.story_iv = None
        self.snu = ""
        self.fw_vers_major = 0
        self.fw_vers_minor = 0
        self.fw_vers_subminor = 0
        self.bt = b""

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

    # opens the .md file to read all information related to device
    def __feed_device(self):
        
        mount_path = Path(self.mount_point)
        md_path = mount_path.joinpath(".md")

        # checking if specified path is acceptable
        if not os.path.isfile(md_path):
            return False

        with open(md_path, "rb") as fp_md:
            md_version = int.from_bytes(fp_md.read(2), 'little')

            if md_version == 7:
                self.__md7_parse(fp_md)
            elif md_version == 6:
                self.__md6_parse(fp_md)
            elif md_version >= 1:
                self.__md1to5_parse(fp_md)
            else:
                return False
        return True

    def __md1to5_parse(self, fp_md):
        fp_md.seek(6)
        self.fw_vers_major = int.from_bytes(fp_md.read(2), 'little')
        self.fw_vers_minor = int.from_bytes(fp_md.read(2), 'little')
        self.snu = fp_md.read(8)

        vid = int.from_bytes(fp_md.read(2), 'little')
        pid = int.from_bytes(fp_md.read(2), 'little')

        if (vid, pid) == FAH_V1_USB_VID_PID or (vid, pid) == FAH_V1_FW_2_USB_VID_PID:
            self.device_version = LUNII_V1
        elif (vid, pid) == FAH_V2_V3_USB_VID_PID:
            self.device_version = LUNII_V2
        else:
            self.device_version = LUNII_V1or2_UNK

        fp_md.seek(0x100)
        self.raw_devkey = fp_md.read(0x100)
        dec = xxtea.decrypt(self.raw_devkey, lunii_generic_key, padding=False, rounds=lunii_tea_rounds(self.raw_devkey))
        # Reordering Key components
        self.device_key = dec[8:16] + dec[0:8]

        logger = logging.getLogger(LUNII_LOGGER)
        logger.log(logging.DEBUG, f"\n"
                                       f"SNU : {self.snu_str}\n"
                                       f"HW  : v{self.device_version}\n"
                                       f"FW  : v{self.fw_vers_major}.{self.fw_vers_minor}\n"
                                       f"VID/PID : 0x{vid:04X} / 0x{pid:04X}\n"
                                       f"Dev Key : {binascii.hexlify(self.device_key, ' ', 1).upper()}")

    def __md6_parse(self, fp_md):
        self.device_version = LUNII_V3
        fp_md.seek(2)
        # reading fw version
        self.fw_vers_major = int.from_bytes(fp_md.read(1), 'little') - 0x30
        fp_md.read(1)
        self.fw_vers_minor = int.from_bytes(fp_md.read(1), 'little') - 0x30
        fp_md.read(1)
        self.fw_vers_subminor = int.from_bytes(fp_md.read(1), 'little') - 0x30
        # reading SNU
        fp_md.seek(0x1A)
        self.snu = binascii.unhexlify(fp_md.read(14).decode('utf-8'))

        # getting candidated for story bt file
        fp_md.seek(0x40)
        self.bt = fp_md.read(0x20)
        # forging keys based on md ciphered part
        self.load_md_fakestory_keys()
        # real keys if available
        V3_KEYS = os.path.join(CFG_DIR, f"{self.snu_str}.keys")
        self.dev_keyfile = V3_KEYS
        self.device_key, self.device_iv = fetch_keys(self.dev_keyfile)

        vid, pid = FAH_V2_V3_USB_VID_PID
        logger = logging.getLogger(LUNII_LOGGER)
        if self.device_key:
            logger.log(logging.INFO, f"v3 key file read from {self.dev_keyfile}")
        logger.log(logging.DEBUG, f"\n"
                                       f"SNU : {self.snu_str}\n"
                                       f"HW  : v3\n"
                                       f"FW  : v{self.fw_vers_major}.{self.fw_vers_minor}.{self.fw_vers_subminor}\n"
                                       f"VID/PID : 0x{vid:04X} / 0x{pid:04X}\n"
                                       f"Dev Key : {binascii.hexlify(self.device_key, ' ', 1).upper() if self.device_key else 'N/A'}\n"
                                       f"Dev IV  : {binascii.hexlify(self.device_iv, ' ', 1).upper() if self.device_iv else 'N/A'}\n"
                                       f"Story Key : {binascii.hexlify(self.story_key, ' ', 1).upper() if self.story_key  else 'N/A'}\n"
                                       f"Story IV  : {binascii.hexlify(self.story_iv,  ' ', 1).upper() if self.story_iv   else 'N/A'}")

    def __md7_parse(self, fp_md):
        self.device_version = LUNII_V3
        fp_md.seek(2)
        # reading fw version
        self.fw_vers_major = int.from_bytes(fp_md.read(1), 'little') - 0x30
        fp_md.read(1)
        self.fw_vers_minor = int.from_bytes(fp_md.read(1), 'little') - 0x30
        fp_md.read(1)
        self.fw_vers_subminor = int.from_bytes(fp_md.read(1), 'little') - 0x30
        # reading SNU
        fp_md.seek(0x1A)
        self.snu = binascii.unhexlify(fp_md.read(14).decode('utf-8'))

        logger = logging.getLogger(LUNII_LOGGER)

        # checking for fw file for each FW_HEARDERS entry
        for key in FW_HEADERS.keys():
            V3_FW = os.path.join(CFG_DIR, f"fa.{self.snu_str}.v{key[0]}{key[1]}{key[2]}.bin")
            if os.path.isfile(V3_FW):
                # checking FW size (best we can do)
                if FW_SIZES.get(key) and os.path.getsize(V3_FW) != FW_SIZES[key]:
                    logger.log(logging.WARNING, f"corrupted firmware (file size mismatch) for v{key[0]}.{key[1]}.{key[2]} ({V3_FW})")
                    continue
                # getting fake keys for story bt file
                with open(V3_FW, "rb") as fp_fw:
                    self.bt = fp_fw.read(0x20)
                    # forging keys based on fw
                    self.load_fw_fakestory_keys()
            else:
                logger.log(logging.INFO, f"no Firmware file for v{key[0]}.{key[1]}.{key[2]}")
        if self.story_key is None:
            logger.log(logging.WARNING, f"no working Firmware file found ({V3_FW})")

        #checking for md v6 file
        V3_MD = os.path.join(CFG_DIR, f"{self.snu_str}.md")
        if os.path.isfile(V3_MD):
            with open(V3_MD, "rb") as fp_md:
                # reading version as first 2 bytes
                md_version = int.from_bytes(fp_md.read(2), 'little')
                # ensure version is 6
                if md_version != 6:
                    logger.log(logging.WARNING, f".md file is not v6 ({V3_MD})")
                else:
                    # ensure that SNU in md is the same as seleced device
                    fp_md.seek(0x1A)
                    md_snu = binascii.unhexlify(fp_md.read(14).decode('utf-8'))
                    
                    if md_snu != self.snu:
                        logger.log(logging.WARNING, f".md v6 file SNU mismatch ({binascii.hexlify(md_snu)} vs. {binascii.hexlify(self.snu)})")
                    else:
                        # moving to 0x40 from beginning
                        fp_md.seek(0x40)
                        self.bt = fp_md.read(0x20)
                    
                        # forging keys based on md
                        self.load_md_fakestory_keys()
        else:
            logger.log(logging.WARNING, f"no .md v6 file found ({V3_MD})")

        # real keys if available
        V3_KEYS = os.path.join(CFG_DIR, f"{self.snu_str}.keys")
        self.dev_keyfile = V3_KEYS
        self.device_key, self.device_iv = fetch_keys(self.dev_keyfile)

        vid, pid = FAH_V2_V3_USB_VID_PID
        if self.device_key:
            self.load_md_fakestory_keys()
            # preparing bt file by ciphering fake keys with real device keys
            buffer = reverse_bytes(self.story_key) + reverse_bytes(self.story_iv)
            cipher = AES.new(self.device_key, AES.MODE_CBC, self.device_iv)
            self.bt = cipher.encrypt(buffer)

            logger.log(logging.INFO, f"v3 key file read from {self.dev_keyfile}")
        
        if self.story_key is None:
            logger.log(logging.WARNING, f"🛑 no keys at all, unable to import stories. See README on Github for help.")
        else:
            logger.log(logging.INFO, f"🟩 story keys found, import supported.")
            
        logger.log(logging.DEBUG, f"\n"
                                       f"SNU : {self.snu_str}\n"
                                       f"HW  : v3\n"
                                       f"FW  : v{self.fw_vers_major}.{self.fw_vers_minor}.{self.fw_vers_subminor}\n"
                                       f"VID/PID : 0x{vid:04X} / 0x{pid:04X}\n"
                                       f"Dev Key : {binascii.hexlify(self.device_key,  ' ', 1).upper() if self.device_key else 'N/A'}\n"
                                       f"Dev IV  : {binascii.hexlify(self.device_iv,   ' ', 1).upper() if self.device_iv  else 'N/A'}\n"
                                       f"Story Key : {binascii.hexlify(self.story_key, ' ', 1).upper() if self.story_key  else 'N/A'}\n"
                                       f"Story IV  : {binascii.hexlify(self.story_iv,  ' ', 1).upper() if self.story_iv   else 'N/A'}")
        # TODO : update log with details about keys used for stories

    def __v1v2_decipher(self, buffer, key, offset, dec_len):
        # checking offset
        if offset > len(buffer):
            offset = len(buffer)
        # checking len
        if offset + dec_len > len(buffer):
            dec_len = len(buffer) - offset
        # if something to be done
        if offset < len(buffer) and offset + dec_len <= len(buffer):
            plain = xxtea.decrypt(buffer[offset:dec_len], key, padding=False, rounds=lunii_tea_rounds(buffer[offset:dec_len]))
            ba_buffer = bytearray(buffer)
            ba_buffer[offset:dec_len] = plain
            buffer = bytes(ba_buffer)
        return buffer

    def __v3_decipher(self, buffer, key, iv, offset, dec_len):
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

    def decipher(self, buffer, key, iv=None, offset=0, dec_len=512):
        if self.device_version == LUNII_V3:
            return self.__v3_decipher(buffer, key, iv, offset, dec_len)
        else:
            return self.__v1v2_decipher(buffer, key, offset, dec_len)

    def __v1v2_cipher(self, buffer, key, offset, enc_len):
        # checking offset
        if offset > len(buffer):
            offset = len(buffer)
        # checking len
        if offset + enc_len > len(buffer):
            enc_len = len(buffer) - offset
        # if something to be done
        if offset < len(buffer) and offset + enc_len <= len(buffer):
            ciphered = xxtea.encrypt(buffer[offset:enc_len], key, padding=False, rounds=lunii_tea_rounds(buffer[offset:enc_len]))
            ba_buffer = bytearray(buffer)
            ba_buffer[offset:enc_len] = ciphered
            buffer = bytes(ba_buffer)
        return buffer

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

    def cipher(self, buffer, key, iv=None, offset=0, enc_len=512):
        if self.debug_plain:
            return buffer

        if self.device_version == LUNII_V3:
            return self.__v3_cipher(buffer, key, iv, offset, enc_len)
        else:
            return self.__v1v2_cipher(buffer, key, offset, enc_len)

    def load_story_keys(self, bt_file_path):
        if self.device_key and self.device_iv and bt_file_path and os.path.isfile(bt_file_path):
            # loading real keys from bt file
            with open(bt_file_path, "rb") as fpbt:
                ciphered = fpbt.read(0x20)
            plain = self.decipher(ciphered, self.device_key, self.device_iv)
            self.story_key = reverse_bytes(plain[:0x10])
            self.story_iv = reverse_bytes(plain[0x10:0x20])
        else:
            # forging keys based on md ciphered part
            self.load_md_fakestory_keys()

    def load_fw_fakestory_keys(self):
        # forging keys based on fw ciphered part
        item = FW_HEADERS.get((self.fw_vers_major, self.fw_vers_minor, self.fw_vers_subminor))
        if item is not None:
            (self.story_key, self.story_iv) = item
            return True
        return False

    def load_md_fakestory_keys(self):
        # forging keys based on md ciphered part
        self.story_key = reverse_bytes(binascii.hexlify(self.snu) + b"\x00\x00")
        self.story_iv = reverse_bytes(b"\x00\x00\x00\x00\x00\x00\x00\x00" + binascii.hexlify(self.snu)[:8])

    @property
    def snu_hex(self):
        return self.snu
    
    def __repr__(self):
        dev_key = b""
        dev_iv  = b""
        story_key = b""
        story_iv  = b""

        if self.device_key:
            dev_key = binascii.hexlify(self.device_key, ' ')
        if self.device_iv:
            dev_iv = binascii.hexlify(self.device_iv, ' ')
        if self.story_key:
            story_key = binascii.hexlify(self.story_key, ' ')
        if self.story_iv:
            story_iv = binascii.hexlify(self.story_iv, ' ')

        repr_str = f"Lunii device on \"{self.mount_point}\"\n"
        if self.device_version <= LUNII_V2:
            repr_str += f"- firmware : v{self.fw_vers_major}.{self.fw_vers_minor}\n"
        else:
            repr_str += f"- firmware : v{self.fw_vers_major}.{self.fw_vers_minor}.{self.fw_vers_subminor}\n"
        repr_str += f"- SNU      : {binascii.hexlify(self.snu_hex, ' ')}\n"
        repr_str += f"- dev key  : {dev_key}\n"
        if self.device_version == LUNII_V3:
            repr_str += f"- dev iv   : {dev_iv}\n"
            # story keys
            if self.story_key:
                repr_str += f"- story key: {story_key}\n"
            if self.device_version == LUNII_V3:
                repr_str += f"- story iv : {story_iv}\n"

        repr_str += f"- stories  : {len(self.stories)}x"
        return repr_str

    def export_all(self, out_path):
        archives = []
        for count, story in enumerate(self.stories):
            self.signal_logger.emit(logging.INFO, f"{count+1:>2}/{len(self.stories)} ")
            one_zip = self.export_story(str(story)[28:], out_path)
            if one_zip:
                archives.append(one_zip)
        return archives

    def update_pack_index(self):
        pi_path = Path(self.mount_point).joinpath(".pi")
        pi_hidden_path = Path(self.mount_point).joinpath(".pi.hidden")
        pi_path.unlink(missing_ok=True)
        pi_hidden_path.unlink(missing_ok=True)
        with open(pi_path, "wb") as fp_pi, open(pi_hidden_path, "wb") as fp_hidden:
            for story in self.stories:
                if story.hidden:
                    fp_hidden.write(story.uuid.bytes)
                else:
                    fp_pi.write(story.uuid.bytes)
        return

    def __valid_story(self, story_path):
        # getting all files in story
        story_files = glob.glob(os.path.join(story_path, "**/*"), recursive=True)

        # expected files
        expected_files = ["li", "ni", "ri", "si"]
        for pattern in expected_files:
            if not any(entry.lower().endswith(pattern) for entry in story_files):
                self.signal_logger.emit(logging.WARN, f"Missing {pattern} in {story_path}")
                return False

        # checking for bt file
        # for Lunii v3, checking keys (original or trick)
        if self.device_version == LUNII_V3:
            # loading story keys
            self.load_story_keys(os.path.join(story_path, "bt"))
            # are keys usable ?
            if not self.__story_check_v3key(Path(story_path), self.story_key, self.story_iv):
                # not the trick keys or dev keys unknown... can't get further
                return True

        # checking auth file (if possible) + fix
        if self.device_version <= LUNII_V2:
            if not self.__story_check_v2bt(Path(story_path)):
                self.signal_logger.emit(logging.WARN, f"Bad authorization file bt in {story_path}")

                # Fixing bt file
                data_ri = b""
                with open(os.path.join(story_path, "ri"), "rb") as fp:
                    data_ri = fp.read(0x40)
                self.bt = self.cipher(data_ri[0:0x40], self.device_key)

                # creating authorization file : bt
                self.signal_logger.emit(logging.INFO, "Authorization file creation...")
                with open(os.path.join(story_path, "bt"), "wb") as fp_bt:
                    fp_bt.write(self.bt)


        # expected dirs
        expected_dirs = ["rf", "sf"]
        for pattern in expected_dirs:
            if not any(entry.lower().endswith(pattern) for entry in story_files):
                self.signal_logger.emit(logging.WARN, f"Missing {pattern} in {story_path}")
                return False

        # parsing ri file - each resource must exist
        ri_plain = self.__get_plain_data(os.path.join(story_path, "ri")).decode("utf-8")
        ri_plain = ri_plain.rstrip('\x00')
        ri_lines = [ri_plain[i:i+12] for i in range(0, len(ri_plain), 12)]
        for res in ri_lines:
            res = res.replace('\\', '/')
            res_path = os.path.join(story_path, "rf", res)
            if not os.path.isfile(res_path):
                self.signal_logger.emit(logging.WARN, f"Missing rf/{res} in {story_path}")
                return False

        # parsing si file - each resource must exist
        si_plain = self.__get_plain_data(os.path.join(story_path, "si")).decode("utf-8")
        si_plain = si_plain.rstrip('\x00')
        si_lines = [si_plain[i:i+12] for i in range(0, len(si_plain), 12)]
        for res in si_lines:
            res = res.replace('\\', '/')
            res_path = os.path.join(story_path, "sf", res)
            if not os.path.isfile(res_path):
                self.signal_logger.emit(logging.WARN, f"Missing sf/{res} in {story_path}")
                return False

        # all requested files are there, including auth file ans resources
        return True

    # try to recover lost stories from .content directory
    def recover_stories(self, dry_run: bool):
        recovered = 0

        # getting all stories
        content_dir = os.path.join(self.mount_point, self.STORIES_BASEDIR)
        try:
            stories_dir = [entry for entry in os.listdir(content_dir) if os.path.isdir(os.path.join(content_dir, entry))]
        except FileNotFoundError:
            return recovered
        stories_dir.sort()

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
            # padding partial UUID
            if not str_uuid and len(story) == 8 and all(c in hexdigits for c in story):
                str_uuid = "00"*12 + story

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

    def __get_plain_data(self, file):
        if not os.path.isfile(file):
            return b""

        # opening file
        with open(file, "rb") as fsrc:
            data = fsrc.read()

        # selecting key
        key = None
        iv = None
        if self.device_version <= LUNII_V2:
            key = lunii_generic_key
            iv = None
        elif self.device_version == LUNII_V3:
            key = self.story_key
            iv = self.story_iv
           
        if file.endswith("bt"):
            if self.device_version <= LUNII_V2:
                key = self.device_key
                iv = None
            elif self.device_version == LUNII_V3:
                key = self.device_key
                iv = self.device_iv
        if file.endswith("ni") or file.endswith("nm"):
            key = None

        # process file with correct key
        if key:
            return self.decipher(data, key, iv)

        return data

    def __get_plain_name(self, file, uuid):
        file = file.split(uuid.upper())[1]
        while file.startswith("\\") or file.startswith("/"):
            file = file[1:]

        if "rf/" in file or "rf\\" in file:
            return file+".bmp"
        if "sf/" in file or "sf\\" in file:
            return file+".mp3"
        if file.endswith("li") or file.endswith("ri") or file.endswith("si"):
            return file+".plain"

        # untouched name
        return file

    def __get_ciphered_data(self, file, data):
        # selecting key
        if self.device_version <= LUNII_V2:
            key = lunii_generic_key
            iv = None
        else:
            # LUNII_V3
            key = self.story_key
            iv = self.story_iv
        if file.endswith("bt"):
            key = self.device_key
        if file.endswith("ni") or file.endswith("nm"):
            key = None

        # process file with correct key
        if key:
            return self.cipher(data, key, iv)

        return data

    def __get_ciphered_name(self, file: str, studio_ri=False, studio_si=False):
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

    def import_dir(self, story_path):
        # print(story_path + "**/*.plain.pk")
        pk_list = []
        for ext in LUNII_SUPPORTED_EXT:
            pk_list += glob.glob(os.path.join(story_path, "**/*" + ext), recursive=True)
        self.signal_logger.emit(logging.INFO, f"Importing {len(pk_list)} archives...")
        for index, pk in enumerate(pk_list):
            self.signal_logger.emit(logging.INFO, f"{index+1:>2}/{len(pk_list)} > {pk}")
            self.import_story(pk)
        
        return True
    
    def import_story(self, story_path):
        archive_type = TYPE_UNK

        self.signal_logger.emit(logging.INFO, f"🚧 Loading {story_path}...")

        archive_size = os.path.getsize(story_path)
        free_space = psutil.disk_usage(str(self.mount_point)).free
        if archive_size >= free_space:
            self.signal_logger.emit(logging.ERROR, f"Not enough space left on Lunii (only {free_space//1024//1024}MB)")
            return False

        # identifying based on filename
        if story_path.lower().endswith(EXT_PK_PLAIN):
            archive_type = TYPE_PLAIN
        elif story_path.lower().endswith(EXT_PK_V2):
            archive_type = TYPE_V2
        elif story_path.lower().endswith(EXT_PK_V1):
            archive_type = TYPE_V2
        elif story_path.lower().endswith(EXT_ZIP):
            archive_type = TYPE_ZIP
        elif story_path.lower().endswith(EXT_7z):
            archive_type = TYPE_7Z
        elif story_path.lower().endswith(EXT_PK_VX):
            # trying to guess version v1/2 or v3 based on bt contents
            with zipfile.ZipFile(file=story_path) as zip_file:
                # reading all available files
                zip_contents = zip_file.namelist()

                # based on bt file
                bt_files = [entry for entry in zip_contents if entry.endswith("bt")]
                if bt_files:
                    bt_size = zip_file.getinfo(bt_files[0]).file_size
                    if bt_size == 0x20:
                        archive_type = TYPE_V3
                    else:
                        archive_type = TYPE_V2
                # based on ri
                elif (any(file.endswith("ri") for file in zip_contents) and
                      any(file.endswith("si") for file in zip_contents) and
                      any(file.endswith("ni") for file in zip_contents) and
                      any(file.endswith("li") for file in zip_contents)):
                    # trying to decipher ri with v2

                    ri_file = next(file for file in zip_contents if file.endswith("ri"))
                    ri_ciphered = zip_file.read(ri_file)
                    ri_plain = self.__v1v2_decipher(ri_ciphered, lunii_generic_key, 0, 512)
                    if ri_plain[:4] == b"000\\":
                        archive_type = TYPE_V2
                    else:
                        archive_type = TYPE_V3
                else:
                    archive_type = TYPE_UNK

        # supplementary verification for zip
        if archive_type == TYPE_ZIP:
            # trying to figure out based on zip contents
            with zipfile.ZipFile(file=story_path) as zip_file:
                # reading all available files
                zip_contents = zip_file.namelist()

                # checking for STUdio format
                if FILE_STUDIO_JSON in zip_contents and any('assets/' in entry for entry in zip_contents):
                    archive_type = TYPE_STUDIO_ZIP
                elif FILE_UUID in zip_contents:
                    archive_type = TYPE_ZIP
                else:
                    archive_type = TYPE_V2
        # supplementary verification for 7z
        elif archive_type == TYPE_7Z:
            # trying to figure out based on 7z contents
            with py7zr.SevenZipFile(story_path, 'r') as archive:
                # reading all available files
                contents = archive.getnames()

                # checking for STUdio format
                if FILE_STUDIO_JSON in contents and any('assets/' in entry for entry in contents):
                    archive_type = TYPE_STUDIO_7Z

        # processing story
        if archive_type == TYPE_PLAIN:
            self.signal_logger.emit(logging.DEBUG, "Archive => TYPE_PLAIN")
            return self.import_story_plain(story_path)
        elif archive_type == TYPE_ZIP:
            self.signal_logger.emit(logging.DEBUG, "Archive => TYPE_ZIP")
            return self.import_story_zip(story_path)
        elif archive_type == TYPE_7Z:
            self.signal_logger.emit(logging.DEBUG, "Archive => TYPE_7Z")
            return self.import_story_7z(story_path)
        elif archive_type == TYPE_V2:
            self.signal_logger.emit(logging.DEBUG, "Archive => TYPE_V2")
            return self.import_story_v2(story_path)
        elif archive_type == TYPE_V3:
            self.signal_logger.emit(logging.DEBUG, "Archive => TYPE_V3")
            return self.import_story_v3(story_path)
        elif archive_type == TYPE_STUDIO_ZIP:
            self.signal_logger.emit(logging.DEBUG, "Archive => TYPE_STUDIO_ZIP")
            return self.import_story_studio_zip(story_path)
        elif archive_type == TYPE_STUDIO_7Z:
            self.signal_logger.emit(logging.DEBUG, "Archive => TYPE_STUDIO_7Z")
            return self.import_story_studio_7z(story_path)

    def import_story_plain(self, story_path):
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
            short_uuid = str(new_uuid).upper()[28:]
            output_path = Path(self.mount_point).joinpath(f"{self.STORIES_BASEDIR}{short_uuid}")
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

                # Extract each zip file
                data_plain = zip_file.read(file)

                # updating filename, and ciphering header if necessary
                data = self.__get_ciphered_data(file, data_plain)
                file_newname = self.__get_ciphered_name(file)

                target: Path = output_path.joinpath(file_newname)

                # create target directory
                if not target.parent.exists():
                    target.parent.mkdir(parents=True)
                # write target file
                self.signal_logger.emit(logging.DEBUG, f"File {index+1}/{len(zip_contents)} > {file_newname}")
                with open(target, "wb") as f_dst:
                    f_dst.write(data)

                # in case of v2 device, we need to prepare bt file 
                if self.device_version <= LUNII_V2 and file.endswith("ri.plain"):
                    self.bt = self.cipher(data[0:0x40], self.device_key)

        # creating authorization file : bt
        self.signal_logger.emit(logging.INFO, "Authorization file creation...")
        bt_path = output_path.joinpath("bt")
        with open(bt_path, "wb") as fp_bt:
            fp_bt.write(self.bt)

        # updating .pi file to add new UUID
        self.stories.append(Story(new_uuid))
        self.update_pack_index()

        return True

    def import_story_zip(self, story_path):
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
            if FILE_STUDIO_JSON in zip_contents:
                self.signal_logger.emit(logging.ERROR, "Studio story format is not supported. Unable to add this story.")
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
            short_uuid = str(new_uuid).upper()[28:]
            output_path = Path(self.mount_point).joinpath(f"{self.STORIES_BASEDIR}/{short_uuid}")
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

                if file == FILE_UUID or file.endswith("bt"):
                    continue

                # Extract each zip file
                data_v2 = zip_file.read(file)

                if file.endswith("ni") or file.endswith("nm"):
                    data_plain = data_v2
                else:
                    data_plain = self.__v1v2_decipher(data_v2, lunii_generic_key, 0, 512)
                # updating filename, and ciphering header if necessary
                data = self.__get_ciphered_data(file, data_plain)
                file_newname = self.__get_ciphered_name(file)

                target: Path = output_path.joinpath(file_newname)

                # create target directory
                if not target.parent.exists():
                    target.parent.mkdir(parents=True)
                # write target file
                self.signal_logger.emit(logging.DEBUG, f"File {index+1}/{len(zip_contents)} > {file_newname}")
                with open(target, "wb") as f_dst:
                    f_dst.write(data)

                # in case of v2 device, we need to prepare bt file 
                if self.device_version <= LUNII_V2 and file.endswith("ri"):
                    self.bt = self.cipher(data[0:0x40], self.device_key)

        # creating authorization file : bt
        self.signal_logger.emit(logging.INFO, "Authorization file creation...")
        bt_path = output_path.joinpath("bt")
        with open(bt_path, "wb") as fp_bt:
            fp_bt.write(self.bt)

        # updating .pi file to add new UUID
        self.stories.append(Story(new_uuid))
        self.update_pack_index()

        return True

    def import_story_7z(self, story_path):
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
            archive_contents = zip.list()

            # getting UUID from path
            uuid_path = Path(archive_contents[0].filename)
            uuid_str = uuid_path.parents[0].name if uuid_path.parents[0].name else uuid_path.name
            if len(uuid_str) >= 16:  # long enough to be a UUID
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
                self.signal_logger.emit(logging.WARNING, f"'{self.stories.get_story(new_uuid).name}' is already loaded !")
                return False
            
            # decompressing story contents
            output_path = Path(self.mount_point).joinpath(self.STORIES_BASEDIR)
            # {str(new_uuid).upper()[28:]
            if not output_path.exists():
                output_path.mkdir(parents=True)

            # Loop over each file
            short_uuid = str(new_uuid).upper()[28:]
            contents = zip.readall().items()
            for index, (fname, bio) in enumerate(contents):
                self.signal_story_progress.emit(short_uuid, index, len(contents))
                # abort requested ? early exit
                if self.abort_process:
                    self.signal_logger.emit(logging.WARNING, f"Import aborted, performing cleanup on current story...")
                    self.__clean_up_story_dir(new_uuid)
                    return False

                if fname.endswith("bt"):
                    continue

                # Extract each zip file
                data_v2 = bio.read()

                # stripping extra uuid chars
                if "-" not in fname:
                    file = fname[24:]
                else:
                    file = fname[28:]

                if self.device_version <= LUNII_V2:
                    # from v2 to v2, data can be kept as it is
                    data = data_v2
                else:
                    # need to transcipher for v3
                    if file.endswith("ni") or file.endswith("nm"):
                        data_plain = data_v2
                    else:
                        data_plain = self.__v1v2_decipher(data_v2, lunii_generic_key, 0, 512)
                    # updating filename, and ciphering header if necessary
                    data = self.__get_ciphered_data(file, data_plain)

                file_newname = self.__get_ciphered_name(file)
                target: Path = output_path.joinpath(file_newname)

                # create target directory
                if not target.parent.exists():
                    target.parent.mkdir(parents=True)
                # write target file
                self.signal_logger.emit(logging.DEBUG, f"File {index+1}/{len(contents)} > {file_newname}")
                with open(target, "wb") as f_dst:
                    f_dst.write(data)

                # in case of v2 device, we need to prepare bt file 
                if self.device_version <= LUNII_V2 and file.endswith("ri"):
                    self.bt = self.cipher(data[0:0x40], self.device_key)

        # creating authorization file : bt
        self.signal_logger.emit(logging.INFO, "Authorization file creation...")
        bt_path = output_path.joinpath(str(new_uuid).upper()[28:]+"/bt")
        with open(bt_path, "wb") as fp_bt:
            fp_bt.write(self.bt)

        # updating .pi file to add new UUID
        self.stories.append(Story(new_uuid))
        self.update_pack_index()

        return True

    def import_story_v2(self, story_path):
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
                self.signal_logger.emit(logging.WARNING, f"'{self.stories.get_story(new_uuid).name}' is already loaded !")
                return False

            # decompressing story contents
            output_path = Path(self.mount_point).joinpath(self.STORIES_BASEDIR)
            # {str(new_uuid).upper()[28:]
            if not output_path.exists():
                output_path.mkdir(parents=True)

            # Loop over each file
            short_uuid = str(new_uuid).upper()[28:]
            for index, file in enumerate(zip_contents):
                self.signal_story_progress.emit(short_uuid, index, len(zip_contents))
                # abort requested ? early exit
                if self.abort_process:
                    self.signal_logger.emit(logging.WARNING, f"Import aborted, performing cleanup on current story...")
                    self.__clean_up_story_dir(new_uuid)
                    return False

                if zip_file.getinfo(file).is_dir():
                    continue
                if file.endswith("bt"):
                    continue

                # Extract each zip file
                data_v2 = zip_file.read(file)

                # stripping extra uuid chars
                if "-" not in file:
                    file = file[24:]
                else:
                    file = file[28:]

                if self.device_version <= LUNII_V2:
                    # from v2 to v2, data can be kept as it is
                    data = data_v2
                else:
                    # need to transcipher for v3
                    if file.endswith("ni") or file.endswith("nm"):
                        data_plain = data_v2
                    else:
                        data_plain = self.__v1v2_decipher(data_v2, lunii_generic_key, 0, 512)
                    # updating filename, and ciphering header if necessary
                    data = self.__get_ciphered_data(file, data_plain)

                file_newname = self.__get_ciphered_name(file)
                target: Path = output_path.joinpath(file_newname)

                # create target directory
                if not target.parent.exists():
                    target.parent.mkdir(parents=True)
                # write target file
                self.signal_logger.emit(logging.DEBUG, f"File {index+1}/{len(zip_contents)} > {file_newname}")
                with open(target, "wb") as f_dst:
                    f_dst.write(data)

                # in case of v2 device, we need to prepare bt file 
                if self.device_version <= LUNII_V2 and file.endswith("ri"):
                    self.bt = self.cipher(data[0:0x40], self.device_key)

        # creating authorization file : bt
        self.signal_logger.emit(logging.INFO, "Authorization file creation...")
        bt_path = output_path.joinpath(str(new_uuid).upper()[28:]+"/bt")
        with open(bt_path, "wb") as fp_bt:
            fp_bt.write(self.bt)

        # updating .pi file to add new UUID
        self.stories.append(Story(new_uuid))
        self.update_pack_index()

        return True

    def import_story_v3(self, story_path):
        self.signal_logger.emit(logging.ERROR, "unsupported story format")
        return False

    def import_story_studio_zip(self, story_path):
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
            if FILE_UUID in zip_contents:
                self.signal_logger.emit(logging.ERROR, "plain.pk format detected ! Unable to add this story.")
                return False
            if FILE_STUDIO_JSON not in zip_contents:
                self.signal_logger.emit(logging.ERROR, "missing 'story.json'. Unable to add this story.")
                return False

            # getting UUID file
            try:
                story_json = json.loads(zip_file.read(FILE_STUDIO_JSON))
            except ValueError as e:
                self.signal_logger.emit(logging.ERROR, e)
                return False

            one_story = StudioStory(story_json)
            if not one_story.compatible:
                self.signal_logger.emit(logging.ERROR, "STUdio story with non MP3 audio file. You need FFMPEG tool to import such kind of story, refer to README.md")
                return False

            stories.thirdparty_db_add_story(one_story.uuid, one_story.title, one_story.description)

            # checking if UUID already loaded
            if str(one_story.uuid) in self.stories:
                self.signal_logger.emit(logging.WARNING, f"'{one_story.name}' is already loaded !")
                return False

            # decompressing story contents
            short_uuid = one_story.short_uuid
            output_path = Path(self.mount_point).joinpath(f"{self.STORIES_BASEDIR}{short_uuid}")
            if not output_path.exists():
                output_path.mkdir(parents=True)

            # Loop over each file
            for index, file in enumerate(zip_contents):
                self.signal_story_progress.emit(short_uuid, index, len(zip_contents))
                # abort requested ? early exit
                if self.abort_process:
                    self.signal_logger.emit(logging.WARNING, f"Import aborted, performing cleanup on current story...")
                    self.__clean_up_story_dir(one_story.uuid)
                    return False

                if zip_file.getinfo(file).is_dir():
                    continue
                if file.endswith(FILE_STUDIO_JSON):
                    continue
                if file.endswith(FILE_STUDIO_THUMB):
                    # adding thumb to DB
                    data = zip_file.read(file)
                    stories.thirdparty_db_add_thumb(one_story.uuid, data)
                    continue
                if not file.startswith("assets"):
                    continue

                # Extract each zip file
                data = zip_file.read(file)

                # stripping extra "assets/" chars
                file = file[7:]
                if file in one_story.ri:
                    file_newname = self.__get_ciphered_name(one_story.ri[file][0], studio_ri=True)
                    # transcode image if necessary
                    data = image_to_bitmap_rle4(data)
                elif file in one_story.si:
                    file_newname = self.__get_ciphered_name(one_story.si[file][0], studio_si=True)
                    # transcode audio if necessary
                    if transcoding_required(file, data):
                        if not STORY_TRANSCODING_SUPPORTED:
                            self.signal_logger.emit(logging.ERROR, "STUdio story with non MP3 audio file. You need FFMPEG tool to import such kind of story, refer to README.md")
                            return False

                        self.signal_logger.emit(logging.WARN, f"⌛ Transcoding audio {file_newname} : {len(data)//1024:4} KB ...")
                        # len_before = len(data)//1024
                        data = audio_to_mp3(data)
                        # print(f"Transcoded from {len_before:4}KB to {len(data)//1024:4}KB")
                    # removing tags if necessary
                    if tags_removal_required(data):
                        self.signal_logger.emit(logging.WARN, f"⌛ Removing tags from audio {file_newname}")
                        data = mp3_tag_cleanup(data)

                else:
                    # unexpected file, skipping
                    continue

                # updating filename, and ciphering header if necessary
                data_ciphered = self.__get_ciphered_data(file, data)
                target: Path = output_path.joinpath(file_newname)

                # create target directory
                if not target.parent.exists():
                    target.parent.mkdir(parents=True)
                # write target file
                self.signal_logger.emit(logging.DEBUG, f"File {index+1}/{len(zip_contents)} > {file_newname}")
                with open(target, "wb") as f_dst:
                    f_dst.write(data_ciphered)

        # creating lunii index files : ri
        ri_data = one_story.get_ri_data()
        self.__write(ri_data, output_path, "ri")
        # in case of v2 device, we need to prepare bt file
        if self.device_version <= LUNII_V2:
            ri_ciph = self.__get_ciphered_data("ri", ri_data)
            self.bt = self.cipher(ri_ciph[0:0x40], self.device_key)

        # creating lunii index files : si, ni, li
        self.__write(one_story.get_si_data(), output_path, "si")
        self.__write(one_story.get_li_data(), output_path, "li")
        self.__write(one_story.get_ni_data(), output_path, "ni")

        # creating authorization file : bt
        self.signal_logger.emit(logging.INFO, "Authorization file creation...")
        bt_path = output_path.joinpath("bt")
        with open(bt_path, "wb") as fp_bt:
            fp_bt.write(self.bt)

        # # updating .pi file to add new UUID
        self.stories.append(Story(one_story.uuid))
        self.update_pack_index()

        return True

    def import_story_studio_7z(self, story_path):
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
            zip_contents = zip.readall()
            if FILE_UUID in zip_contents:
                self.signal_logger.emit(logging.ERROR, "plain.pk format detected ! Unable to add this story.")
                return False
            if FILE_STUDIO_JSON not in zip_contents:
                self.signal_logger.emit(logging.ERROR, "missing 'story.json'. Unable to add this story.")
                return False
  
            # getting UUID file
            try:
                story_json = json.loads(zip_contents[FILE_STUDIO_JSON].read())
            except ValueError as e:
                self.signal_logger.emit(logging.ERROR, e)
                return False

            one_story = StudioStory(story_json)
            if not one_story.compatible:
                self.signal_logger.emit(logging.ERROR, "STUdio story with non MP3 audio file. You need FFMPEG tool to import such kind of story, refer to README.md")
                return False

            stories.thirdparty_db_add_story(one_story.uuid, one_story.title, one_story.description)

            # checking if UUID already loaded
            if str(one_story.uuid) in self.stories:
                self.signal_logger.emit(logging.WARNING, f"'{one_story.name}' is already loaded !")
                return False

            # decompressing story contents
            short_uuid = one_story.short_uuid
            output_path = Path(self.mount_point).joinpath(f"{self.STORIES_BASEDIR}{short_uuid}")
            if not output_path.exists():
                output_path.mkdir(parents=True)

            # Loop over each file
            contents = zip_contents.items()
            for index, (fname, bio) in enumerate(contents):
                self.signal_story_progress.emit(short_uuid, index, len(contents))
                # abort requested ? early exit
                if self.abort_process:
                    self.signal_logger.emit(logging.WARNING, f"Import aborted, performing cleanup on current story...")
                    self.__clean_up_story_dir(one_story.uuid)
                    return False

                if fname.endswith(FILE_STUDIO_JSON):
                    continue
                if fname.endswith(FILE_STUDIO_THUMB):
                    # adding thumb to DB
                    data = bio.read()
                    stories.thirdparty_db_add_thumb(one_story.uuid, data)
                    continue
                if not fname.startswith("assets"):
                    continue

                # Extract each zip file
                data = bio.read()

                # stripping extra "assets/" chars
                fname = fname[7:]
                if fname in one_story.ri:
                    file_newname = self.__get_ciphered_name(one_story.ri[fname][0], studio_ri=True)
                    # transcode image if necessary
                    data = image_to_bitmap_rle4(data)
                elif fname in one_story.si:
                    file_newname = self.__get_ciphered_name(one_story.si[fname][0], studio_si=True)
                    # transcode audio if necessary
                    if transcoding_required(fname, data):
                        if not STORY_TRANSCODING_SUPPORTED:
                            self.signal_logger.emit(logging.ERROR, "STUdio story with non MP3 audio file. You need FFMPEG tool to import such kind of story, refer to README.md")
                            return False

                        self.signal_logger.emit(logging.WARN, f"⌛ Transcoding audio {file_newname} : {len(data)//1024:4} KB ...")
                        data = audio_to_mp3(data)
                else:
                    # unexpected file, skipping
                    continue

                # updating filename, and ciphering header if necessary
                data_ciphered = self.__get_ciphered_data(fname, data)
                target: Path = output_path.joinpath(file_newname)

                # create target directory
                if not target.parent.exists():
                    target.parent.mkdir(parents=True)
                # write target file
                self.signal_logger.emit(logging.DEBUG, f"File {index+1}/{len(contents)} > {file_newname}")
                with open(target, "wb") as f_dst:
                    f_dst.write(data_ciphered)

        # creating lunii index files : ri
        ri_data = one_story.get_ri_data()
        self.__write(ri_data, output_path, "ri")
        # in case of v2 device, we need to prepare bt file
        if self.device_version <= LUNII_V2:
            ri_ciph = self.__get_ciphered_data("ri", ri_data)
            self.bt = self.cipher(ri_ciph[0:0x40], self.device_key)

        # creating lunii index files : si, ni, li
        self.__write(one_story.get_si_data(), output_path, "si")
        self.__write(one_story.get_li_data(), output_path, "li")
        self.__write(one_story.get_ni_data(), output_path, "ni")

        # creating authorization file : bt
        self.signal_logger.emit(logging.INFO, "Authorization file creation...")
        bt_path = output_path.joinpath("bt")
        with open(bt_path, "wb") as fp_bt:
            fp_bt.write(self.bt)

        # # updating .pi file to add new UUID
        self.stories.append(Story(one_story.uuid))
        self.update_pack_index()

        return True

    def __write(self, data_plain, output_path, file):
        path_file = os.path.join(output_path, file)
        with open(path_file, "wb") as fp:
            data = self.__get_ciphered_data(path_file, data_plain)
            # data =  data_plain
            fp.write(data)

    def __story_check_v3key(self, story_path: Path, key, iv):
        # Trying to decipher RI/SI for path check
        ri_path = story_path.joinpath("ri")
        if not os.path.isfile(ri_path):
            return False
        
        with open(ri_path, "rb") as fp_ri:
            ri_content = fp_ri.read()

        plain = self.decipher(ri_content, key, iv)
        return plain[:3] == b"000"

    def __story_check_v2bt(self, story_path: Path):
        bt_path = story_path.joinpath("bt")
        if not os.path.isfile(bt_path):
            return False
        ri_path = story_path.joinpath("ri")
        if not os.path.isfile(ri_path):
            return False

        # reading reference data
        with open(os.path.join(story_path, "ri"), 'rb') as fp:
            ri_data = fp.read(0x40)

        # Trying to decipher BT
        with open(bt_path, "rb") as fp_bt:
            bt_content = fp_bt.read()
            plain_bt = self.decipher(bt_content, self.device_key)
            return ri_data[:0x40] == plain_bt

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
        uuid = one_story.str_uuid[28:]

        # checking that .content dir exist
        content_path = Path(self.mount_point).joinpath(self.STORIES_BASEDIR)
        if not content_path.is_dir():
            return None
        story_path = content_path.joinpath(uuid)
        if not story_path.is_dir():
            return None
        
        self.signal_logger.emit(logging.INFO, f"🚧 Exporting {uuid} - {one_story.name}")

        # for Lunii v3, checking keys (original or trick)
        if self.device_version == LUNII_V3:
            # loading story keys
            self.load_story_keys(str(story_path.joinpath("bt")))
            # are keys usable ?
            if not self.__story_check_v3key(story_path, self.story_key, self.story_iv):
                self.signal_logger.emit(logging.ERROR, "Lunii v3 requires Device Key for genuine story export.")
                return None

        # Preparing zip file
        sname = one_story.name
        sname = secure_filename(sname)

        zip_path = Path(out_path).joinpath(f"{sname}.{uuid}.plain.pk")
        # if os.path.isfile(zip_path):
        #     self.signal_logger.emit(logging.WARNING, f"Already exported")
        #     return None
        
        # preparing file list
        story_flist = []
        for root, dirnames, filenames in os.walk(story_path):
            for filename in filenames:
                if filename in ["bt", "md"]:
                    continue
                story_flist.append(os.path.join(root, filename))

        try:
            with zipfile.ZipFile(zip_path, 'w') as zip_out:
                self.signal_logger.emit(logging.DEBUG, "> Zipping story ...")
                for index, file in enumerate(story_flist):
                    self.signal_story_progress.emit(uuid, index, len(story_flist))
                    # abort requested ? early exit
                    if self.abort_process:
                        return None

                    # Extract each file to another directory
                    # decipher if necessary (mp3 / bmp / li / ri / si)
                    data_plain = self.__get_plain_data(file)
                    file_newname = self.__get_plain_name(file, uuid)
                    zip_out.writestr(file_newname, data_plain)

                # adding uuid file
                self.signal_logger.emit(logging.DEBUG, "> Adding UUID ...")
                zip_out.writestr(FILE_UUID, one_story.uuid.bytes)

                # more files to be added for thirdparty stories
                if not one_story.is_official():
                    self.signal_logger.emit(logging.DEBUG, "> Adding thumbnail ...")
                    pict_data = one_story.get_picture()
                    if pict_data:
                        zip_out.writestr(FILE_THUMB, pict_data)

                    self.signal_logger.emit(logging.DEBUG, "> Adding metadata ...")
                    meta = one_story.get_meta()
                    if meta:
                        zip_out.writestr(FILE_META, meta)

        except PermissionError as e:
            self.signal_logger.emit(logging.ERROR, f"failed to create ZIP - {e}")
            return None
        
        return zip_path

    def __clean_up_story_dir(self, story_uuid: UUID):
        story_dir = Path(self.mount_point).joinpath(f"{self.STORIES_BASEDIR}{story_uuid.hex.upper()[-8:]}")
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
    pi_path = mount_path.joinpath(".pi")
    pi_hidden_path = mount_path.joinpath(".pi.hidden")

    story_list = StoryList()

    logger.log(logging.INFO, f"Reading Lunii loaded stories...")

    # if there is a .pi
    if os.path.isfile(pi_path):
        with open(pi_path, "rb") as fp_pi:
            loop_again = True
            while loop_again:
                next_uuid = fp_pi.read(16)
                if next_uuid:
                    one_uuid = UUID(bytes=next_uuid)
                    logger.log(logging.DEBUG, f"> {str(one_uuid)}")
                    if one_uuid in story_list:
                        logger.log(logging.WARNING, f"Found duplicate story, cleaning...")
                    else:
                        story_list.append(Story(one_uuid))
                else:
                    loop_again = False

    story_count = len(story_list)
    logger.log(logging.INFO, f"Read {story_count} stories")

    # if there is a hidden .pi
    if os.path.isfile(pi_hidden_path):
        with open(pi_hidden_path, "rb") as fp_pi:
            loop_again = True
            while loop_again:
                next_uuid = fp_pi.read(16)
                if next_uuid:
                    one_uuid = UUID(bytes=next_uuid)
                    logger.log(logging.DEBUG, f"> {str(one_uuid)}")
                    if one_uuid in story_list:
                        logger.log(logging.WARNING, f"Found duplicate story, cleaning...")
                    else:
                        story_list.append(Story(one_uuid, hidden=True))
                else:
                    loop_again = False

    logger.log(logging.INFO, f"Read {len(story_list) - story_count} hidden stories")
    return story_list


def is_lunii(root_path):
    MD_FILE = os.path.join(root_path, ".md")

    try:
        if os.path.isfile(MD_FILE):
            return True
    except PermissionError:
        pass
    return False


def secure_filename(filename):
    INVALID_FILE_CHARS = '/\\?%*:|"<>'  # https://en.wikipedia.org/wiki/Filename#Reserved_characters_and_words

    # keep only valid ascii chars
    output = list(unicodedata.normalize("NFKD", filename))

    # special case characters that don't get stripped by the above technique
    for pos, char in enumerate(output):
        if char == '\u0141':
            output[pos] = 'L'
        elif char == '\u0142':
            output[pos] = 'l'

    # remove unallowed characters
    output = [c if c not in INVALID_FILE_CHARS else '_' for c in output]
    return "".join(output).encode("ASCII", "ignore").decode()
