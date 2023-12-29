import glob
import os
import shutil
import unicodedata
import zipfile
import psutil
import py7zr
import xxtea
import binascii
from pathlib import Path
from uuid import UUID

from Crypto.Cipher import AES

from PySide6.QtCore import Signal

from pkg.api.aes_keys import fetch_keys, reverse_bytes
from pkg.api.constants import *
from pkg.api.stories import StoryList, story_name


class LuniiDevice:
    stories: StoryList
    signal_zip_progress: Signal = Signal(str, int)

    def __init__(self, mount_point, keyfile=None):
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
        self.bt = b""

        # internal device details
        self.__feed_device()

        # internal stories
        self.stories = feed_stories(self.mount_point)

    # opens the .pi file to read all installed stories
    def __feed_device(self):
        
        mount_path = Path(self.mount_point)
        md_path = mount_path.joinpath(".md")

        with open(md_path, "rb") as fp_md:
            md_version = int.from_bytes(fp_md.read(2), 'little')

            if md_version == 6:
                self.__v3_parse(fp_md)
            elif md_version == 3:
                self.__v2_parse(fp_md)

    def __v2_parse(self, fp_md):
        self.lunii_version = LUNII_V2
        fp_md.seek(6)
        self.fw_vers_major = int.from_bytes(fp_md.read(2), 'little')
        self.fw_vers_minor = int.from_bytes(fp_md.read(2), 'little')
        self.snu = fp_md.read(8)
        
        fp_md.seek(0x100)
        self.raw_devkey = fp_md.read(0x100)
        dec = xxtea.decrypt(self.raw_devkey, lunii_generic_key, padding=False, rounds=lunii_tea_rounds(self.raw_devkey))
        # Reordering Key components
        self.device_key = dec[8:16] + dec[0:8]

    def __v3_parse(self, fp_md):
        self.lunii_version = LUNII_V3
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
        self.load_fakestory_keys()
        # real keys if available
        self.device_key, self.device_iv = fetch_keys(self.dev_keyfile)

    def __v2_decipher(self, buffer, key, offset, dec_len):
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
        if self.lunii_version == LUNII_V2:
            return self.__v2_decipher(buffer, key, offset, dec_len)
        else:
            return self.__v3_decipher(buffer, key, iv, offset, dec_len)

    def __v2_cipher(self, buffer, key, offset, enc_len):
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
        if enc_len%16 != 0:
            padlen = 16 - len(buffer)%16
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
        if self.lunii_version == LUNII_V2:
            return self.__v2_cipher(buffer, key, offset, enc_len)
        else:
            return self.__v3_cipher(buffer, key, iv, offset, enc_len)

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
             self.load_fakestory_keys()

    def load_fakestory_keys(self):
        # forging keys based on md ciphered part
        self.story_key = reverse_bytes(binascii.hexlify(self.snu) + b"\x00\x00")
        self.story_iv = reverse_bytes(b"\x00\x00\x00\x00\x00\x00\x00\x00" + binascii.hexlify(self.snu)[:8])

    @property
    def snu_hex(self):
        return self.snu
    
    def __repr__(self):
        dev_key = b""
        dev_iv  = b""

        if self.device_key:
            dev_key = binascii.hexlify(self.device_key, ' ')
        if self.device_iv:
            dev_iv = binascii.hexlify(self.device_iv, ' ')

        repr_str  = f"Lunii device on \"{self.mount_point}\"\n"
        if self.lunii_version == LUNII_V2:
            repr_str += f"- firmware : v{self.fw_vers_major}.{self.fw_vers_minor}\n"
        else:
            repr_str += f"- firmware : v{self.fw_vers_major}.{self.fw_vers_minor}.{self.fw_vers_subminor}\n"
        repr_str += f"- snu      : {binascii.hexlify(self.snu_hex, ' ')}\n"
        repr_str += f"- dev key  : {dev_key}\n"
        if self.lunii_version == LUNII_V3:
            repr_str += f"- dev iv   : {dev_iv}\n"
        repr_str += f"- stories  : {len(self.stories)}x\n"
        return repr_str

    def export_all(self, out_path):
        archives = []
        for count, story in enumerate(self.stories):
            # print(f"{count+1:>2}/{len(self.stories)} ", end="")
            one_zip = self.export_story(str(story)[28:], out_path)
            if one_zip:
                archives.append(one_zip)
        return archives

    def update_pack_index(self):
        pi_path = Path(self.mount_point).joinpath(".pi")
        pi_path.unlink()
        with open(pi_path, "wb") as fp:
            st_uuid: UUID
            for st_uuid in self.stories:
                fp.write(st_uuid.bytes)
        return

    def __get_plain_data(self, file):
        if not os.path.isfile(file):
            return b""

        # opening file
        with open(file, "rb") as fsrc:
            data = fsrc.read()

        # selecting key
        key = None
        if self.lunii_version == LUNII_V2:
            key = lunii_generic_key
            iv = None
        elif self.lunii_version == LUNII_V3:
            key = self.story_key
            iv = self.story_iv
           
        if file.endswith("bt"):
            if self.lunii_version == LUNII_V2:
                key = self.device_key
                iv = None
            elif self.lunii_version == LUNII_V3:
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
        if self.lunii_version == LUNII_V2:
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

    def __get_ciphered_name(self, file):
        file = file.removesuffix('.plain')
        file = file.removesuffix('.mp3')
        file = file.removesuffix('.bmp')

        # upcasing filename
        bn = os.path.basename(file)
        if len(bn) >= 8:
            file = os.path.join(os.path.dirname(file),bn.upper())

        # upcasing uuid dir if present
        dn = os.path.dirname(file)
        if len(dn) >= 8:
            dir_head = file[0:8]
            if "/" not in dir_head and "\\" not in dir_head:
                file = dir_head.upper() + file[8:]

        # print(file)
        return file

    def import_dir(self, story_path):
        # print(story_path + "**/*.plain.pk")
        pk_list = []
        for ext in SUPPORTED_EXT:
            pk_list += glob.glob(os.path.join(story_path, "**/*" + ext), recursive=True)
        # print(f"Importing {len(pk_list)} archives...")
        for index, pk in enumerate(pk_list):
            # print(f"{index+1:>2}/{len(pk_list)} > {pk}")
            self.import_story(pk)
        
        return True
    
    def import_story(self, story_path):
        type = TYPE_UNK

        archive_size = os.path.getsize(story_path)
        free_space = psutil.disk_usage(str(self.mount_point)).free
        if archive_size >= free_space:
            # print(f"   ERROR: Not enough space left on Lunii (only {free_space//1024//1024}MB)")
            return False
        
        # identifying based on filename
        if story_path.lower().endswith(EXT_PK_PLAIN):
            type = TYPE_PLAIN
        elif story_path.lower().endswith(EXT_PK_V2):
            type = TYPE_V2
        elif story_path.lower().endswith(EXT_PK_V1):
            type = TYPE_V2
        elif story_path.lower().endswith(EXT_ZIP):
            type = TYPE_ZIP
        elif story_path.lower().endswith(EXT_7z):
            type = TYPE_7Z
        else:
            # trying to figure out based on zip contents
            with zipfile.ZipFile(file=story_path) as zip_file:
                # reading all available files
                zip_contents = zip_file.namelist()

                # based on bt file
                bt_files = [entry for entry in zip_contents if entry.endswith("bt")]
                if bt_files:
                    bt_size = zip_file.getinfo(bt_files[0]).file_size
                    if bt_size == 0x20:
                        type = TYPE_V3
                    else:
                        type = TYPE_V2
                
                # based on ri decipher with xxtea
                        # type = TYPE_V2

        # processing story
        if type == TYPE_PLAIN:
            return self.import_story_plain(story_path)
        elif type == TYPE_ZIP:
            return self.import_story_zip(story_path)
        elif type == TYPE_7Z:
            return self.import_story_7z(story_path)
        elif type == TYPE_V2:
            return self.import_story_v2(story_path)
        elif type == TYPE_V3:
            return self.import_story_v3(story_path)

    def import_story_plain(self, story_path):
        # checking if archive is OK
        try:
            with zipfile.ZipFile(file=story_path):
                pass  # If opening succeeds, the archive is valid
        except zipfile.BadZipFile as e:
            print(f"   ERROR: {e}")
            return False
        
        # opening zip file
        with zipfile.ZipFile(file=story_path) as zip_file:
            # reading all available files
            zip_contents = zip_file.namelist()
            if "uuid.bin" not in zip_contents:
                print("   ERROR: No UUID file found in archive. Unable to add this story.")
                return False

            # getting UUID file
            try:
                new_uuid = UUID(bytes=zip_file.read("uuid.bin"))
            except ValueError as e:
                print(f"   ERROR: {e}")
                return False
        
            # checking if UUID already loaded
            if str(new_uuid) in self.stories:
                print(f"   WARN: '{story_name(new_uuid)}' is already loaded, aborting !")
                return False

            # decompressing story contents
            output_path = Path(self.mount_point).joinpath(f".content/{str(new_uuid).upper()[28:]}")
            if not output_path.exists():
                output_path.mkdir(parents=True)

            # Loop over each file
            for file in zip_contents:
                if file == "uuid.bin":
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
                with open(target, "wb") as f_dst:
                    f_dst.write(data)

                # in case of v2 device, we need to prepare bt file 
                if self.lunii_version == LUNII_V2 and file.endswith("ri.plain"):
                    self.bt = self.cipher(data[0:0x40], self.device_key)

        # creating authorization file : bt
        # print("   INFO : Authorization file creation...")
        bt_path = output_path.joinpath("bt")
        with open(bt_path, "wb") as fp_bt:
            fp_bt.write(self.bt)

        # updating .pi file to add new UUID
        self.stories.append(new_uuid)
        self.update_pack_index()

        return True

    def import_story_zip(self, story_path):
        # checking if archive is OK
        try:
            with zipfile.ZipFile(file=story_path):
                pass  # If opening succeeds, the archive is valid
        except zipfile.BadZipFile as e:
            print(f"   ERROR: {e}")
            return False
        
        # opening zip file
        with zipfile.ZipFile(file=story_path) as zip_file:
            # reading all available files
            zip_contents = zip_file.namelist()
            if "uuid.bin" not in zip_contents:
                print("   ERROR: No UUID file found in archive. Unable to add this story.")
                return False
            if "story.json" in zip_contents:
                print("   ERROR: Studio story format is not supported. Unable to add this story.")
                return False

            # getting UUID file
            try:
                new_uuid = UUID(bytes=zip_file.read("uuid.bin"))
            except ValueError as e:
                print(f"   ERROR: {e}")
                return False
        
            # checking if UUID already loaded
            if str(new_uuid) in self.stories:
                # print(f"   WARN: '{story_name(new_uuid)}' is already loaded, aborting !")
                return False

            # decompressing story contents
            output_path = Path(self.mount_point).joinpath(f".content/{str(new_uuid).upper()[28:]}")
            if not output_path.exists():
                output_path.mkdir(parents=True)

            # Loop over each file
            for file in zip_contents:
                if file == "uuid.bin" or file.endswith("bt"):
                    continue

                # Extract each zip file
                data_v2 = zip_file.read(file)

                if file.endswith("ni") or file.endswith("nm"):
                    data_plain = data_v2
                else:
                    data_plain = self.__v2_decipher(data_v2, lunii_generic_key, 0, 512)
                # updating filename, and ciphering header if necessary
                data = self.__get_ciphered_data(file, data_plain)
                file_newname = self.__get_ciphered_name(file)

                target: Path = output_path.joinpath(file_newname)

                # create target directory
                if not target.parent.exists():
                    target.parent.mkdir(parents=True)
                # write target file
                with open(target, "wb") as f_dst:
                    f_dst.write(data)

                # in case of v2 device, we need to prepare bt file 
                if self.lunii_version == LUNII_V2 and file.endswith("ri"):
                    self.bt = self.cipher(data[0:0x40], self.device_key)

        # creating authorization file : bt
        # print("   INFO : Authorization file creation...")
        bt_path = output_path.joinpath("bt")
        with open(bt_path, "wb") as fp_bt:
            fp_bt.write(self.bt)

        # updating .pi file to add new UUID
        self.stories.append(new_uuid)
        self.update_pack_index()

        return True

    def import_story_7z(self, story_path):
        # checking if archive is OK
        try:
            with py7zr.SevenZipFile(story_path, mode='r'):
                pass  # If opening succeeds, the archive is valid
        except py7zr.exceptions.Bad7zFile as e:
            print(f"   ERROR: {e}")
            return False

        # opening zip file
        with py7zr.SevenZipFile(story_path, mode='r') as zip:
            # reading all available files
            archive_contents = zip.list()

            # getting UUID from first dir
            if not archive_contents[0].is_directory:
                print("   ERROR: UUID directory is missing in archive !")
                return False

            try:
                if "-" not in archive_contents[0].filename:
                    new_uuid = UUID(bytes=binascii.unhexlify(archive_contents[0].filename))
                else:
                    new_uuid = UUID(archive_contents[0].filename)
            except ValueError as e:
                print(f"   ERROR: {e}")
                return False

            # checking if UUID already loaded
            if str(new_uuid) in self.stories:
                # print(f"   WARN: '{story_name(new_uuid)}' is already loaded, aborting !")
                return False
            
            # decompressing story contents
            output_path = Path(self.mount_point).joinpath(f".content/")
            # {str(new_uuid).upper()[28:]
            if not output_path.exists():
                output_path.mkdir(parents=True)

            # Loop over each file
            contents = zip.readall().items()
            for fname, bio in contents:
                if fname.endswith("bt"):
                    continue

                # Extract each zip file
                data_v2 = bio.read()

                # stripping extra uuid chars
                if "-" not in fname:
                    file = fname[24:]
                else:
                    file = fname[28:]

                if self.lunii_version == LUNII_V2:
                    # from v2 to v2, data can be kept as it is
                    data = data_v2
                else:
                    # need to transcipher for v3
                    if file.endswith("ni") or file.endswith("nm"):
                        data_plain = data_v2
                    else:
                        data_plain = self.__v2_decipher(data_v2, lunii_generic_key, 0, 512)
                    # updating filename, and ciphering header if necessary
                    data = self.__get_ciphered_data(file, data_plain)

                file_newname = self.__get_ciphered_name(file)
                target: Path = output_path.joinpath(file_newname)

                # create target directory
                if not target.parent.exists():
                    target.parent.mkdir(parents=True)
                # write target file
                with open(target, "wb") as f_dst:
                    f_dst.write(data)

                # in case of v2 device, we need to prepare bt file 
                if self.lunii_version == LUNII_V2 and file.endswith("ri"):
                    self.bt = self.cipher(data[0:0x40], self.device_key)

        # creating authorization file : bt
        # print("   INFO : Authorization file creation...")
        bt_path = output_path.joinpath(str(new_uuid)[28:]+"/bt")
        with open(bt_path, "wb") as fp_bt:
            fp_bt.write(self.bt)

        # updating .pi file to add new UUID
        self.stories.append(new_uuid)
        self.update_pack_index()

        return True

    def import_story_v2(self, story_path):
        # checking if archive is OK
        try:
            with zipfile.ZipFile(file=story_path):
                pass  # If opening succeeds, the archive is valid
        except zipfile.BadZipFile as e:
            print(f"   ERROR: {e}")
            return False
        
        # opening zip file
        with zipfile.ZipFile(file=story_path) as zip_file:
            # reading all available files
            zip_contents = zip_file.namelist()

            # getting UUID from path
            if zip_file.getinfo(zip_contents[0]).is_dir():
                # print(zip_contents[0][:-1])
                try:
                    if "-" not in zip_contents[0]:
                        new_uuid = UUID(bytes=binascii.unhexlify(zip_contents[0][:-1]))
                    else:
                        new_uuid = UUID(zip_contents[0][:-1])
                except ValueError as e:
                    print(f"   ERROR: {e}")
                    return False
            else:
                print("   ERROR: UUID directory is missing in archive !")
                return False

            # checking if UUID already loaded
            if str(new_uuid) in self.stories:
                # print(f"   WARN: '{story_name(new_uuid)}' is already loaded, aborting !")
                return False

            # decompressing story contents
            output_path = Path(self.mount_point).joinpath(f".content/")
            # {str(new_uuid).upper()[28:]
            if not output_path.exists():
                output_path.mkdir(parents=True)

            # Loop over each file
            for file in zip_contents:
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

                if self.lunii_version == LUNII_V2:
                    # from v2 to v2, data can be kept as it is
                    data = data_v2
                else:
                    # need to transcipher for v3
                    if file.endswith("ni") or file.endswith("nm"):
                        data_plain = data_v2
                    else:
                        data_plain = self.__v2_decipher(data_v2, lunii_generic_key, 0, 512)
                    # updating filename, and ciphering header if necessary
                    data = self.__get_ciphered_data(file, data_plain)

                file_newname = self.__get_ciphered_name(file)
                target: Path = output_path.joinpath(file_newname)

                # create target directory
                if not target.parent.exists():
                    target.parent.mkdir(parents=True)
                # write target file
                with open(target, "wb") as f_dst:
                    f_dst.write(data)

                # in case of v2 device, we need to prepare bt file 
                if self.lunii_version == LUNII_V2 and file.endswith("ri"):
                    self.bt = self.cipher(data[0:0x40], self.device_key)

        # creating authorization file : bt
        # print("   INFO : Authorization file creation...")
        bt_path = output_path.joinpath(str(new_uuid)[28:]+"/bt")
        with open(bt_path, "wb") as fp_bt:
            fp_bt.write(self.bt)

        # updating .pi file to add new UUID
        self.stories.append(new_uuid)
        self.update_pack_index()

        return True

    def import_story_v3(self, story_path):
        print("   ERROR : unsupported story format")
        return False

    def __story_check_key(self, story_path, key, iv):
        # Trying to decipher RI/SI for path check
        ri_path = story_path.joinpath("ri")
        if not os.path.isfile(ri_path):
            return False
        
        with open(ri_path, "rb") as fp_ri:
            ri_content = fp_ri.read()

        plain = self.decipher(ri_content, self.story_key, self.story_iv)
        return plain[:3] == b"000"

    def export_story(self, uuid, out_path):
        # is UUID part of existing stories
        if uuid not in self.stories:
            return None

        ulist = self.stories.full_uuid(uuid)
        if len(ulist) > 1:
            print(f"   ERROR: at least {len(ulist)} match your pattern. Try a longer UUID.")
            for st in ulist:
                print(f"[{st} - {self.stories.name(str(st))}]")
            return None

        full_uuid = ulist[0]
        uuid = str(full_uuid).upper()[28:]

        # checking that .content dir exist
        content_path = Path(self.mount_point).joinpath(".content")
        if not content_path.is_dir():
            return None
        story_path = content_path.joinpath(uuid)
        if not story_path.is_dir():
            return None
        
        # print(f"[{uuid} - {self.stories.name(uuid)}]")

        # for Lunii v3, checking keys (original or trick)
        if self.lunii_version == LUNII_V3:
            # loading story keys
            self.load_story_keys(str(story_path.joinpath("bt")))
            # are keys usable ?
            if not self.__story_check_key(story_path, self.story_key, self.story_iv):
                print("   ERROR: Lunii v3 requires Device Key for genuine story export.")
                return None

        # Preparing zip file
        sname = self.stories.name(uuid)
        sname = secure_filename(sname)

        zip_path = Path(out_path).joinpath(f"{sname}.{uuid}.plain.pk")
        if os.path.isfile(zip_path):
            # print(f"   WARN: Already exported")
            return None
        
        # preparing file list
        story_flist = []
        for root, dirnames, filenames in os.walk(story_path):
            for filename in filenames:
                if filename in ["bt", "md"]:
                    continue
                story_flist.append(os.path.join(root, filename))

        try:
            with zipfile.ZipFile(zip_path, 'w') as zip_out:
                # print("> Zipping story ...")
                for file in story_flist:
                    target_name = Path(file).relative_to(story_path)

                    # Extract each file to another directory
                    # decipher if necessary (mp3 / bmp / li / ri / si)
                    data_plain = self.__get_plain_data(file)
                    file_newname = self.__get_plain_name(file, uuid)
                    zip_out.writestr(file_newname, data_plain)

                # adding uuid file
                # print("> Adding UUID ...")
                zip_out.writestr("uuid.bin", full_uuid.bytes)
        except PermissionError as e:
            print(f"   ERROR: failed to create ZIP - {e}")
            return None
        
        return zip_path
    
    def remove_story(self, short_uuid):
        if short_uuid not in self.stories:
            # print("ERROR: This story is not present on your storyteller")
            return False

        ulist = self.stories.full_uuid(short_uuid)
        if len(ulist) > 1:
            # print(f"ERROR: at least {len(ulist)} match your pattern. Try a longer UUID.")
            return False
        uuid = str(ulist[0])

        # print(f"Removing {uuid[28:]} - {self.stories.name(uuid)}...")
  
        # removing story contents
        st_path = Path(self.mount_point).joinpath(f".content/{uuid[28:]}")
        shutil.rmtree(st_path)

        # removing story from class
        self.stories.remove(ulist[0])
        # updating pack index file
        self.update_pack_index()

        return True


def secure_filename(filename):
    INVALID_FILE_CHARS = '/\\?%*:|"<>' # https://en.wikipedia.org/wiki/Filename#Reserved_characters_and_words

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


# opens the .pi file to read all installed stories
def feed_stories(root_path) -> StoryList[UUID]:
    
    mount_path = Path(root_path)
    pi_path = mount_path.joinpath(".pi")

    story_list = StoryList()
    with open(pi_path, "rb") as fp_pi:
        loop_again = True
        while loop_again:
            next_uuid = fp_pi.read(16)
            if next_uuid:
                story_list.append(UUID(bytes=next_uuid))
            else:
                loop_again = False
    return story_list


def find_devices(extra_path=None):
    lunii_dev = []

    # checking all drive letters
    for drive in range(ord('A'), ord('Z')+1):
        drv_str = f"{chr(drive)}:/"
        lunii_path = Path(drv_str)
        
        if is_device(lunii_path):
            lunii_dev.append(lunii_path)

    # checking for extra path
    if extra_path:
        lunii_path = Path(extra_path)
        
        if is_device(lunii_path):
            lunii_dev.append(lunii_path)

    # done
    return lunii_dev


def is_device(root_path):
    root_path = Path(root_path)
    pi_path = root_path.joinpath(".pi")
    md_path = root_path.joinpath(".md")
    cfg_path = root_path.joinpath(".cfg")
    content_path = root_path.joinpath(".content")

    if pi_path.is_file() and md_path.is_file() and cfg_path.is_file() and content_path.is_dir():
        return True
    return False
