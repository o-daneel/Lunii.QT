import binascii
import json
from uuid import UUID
import zipfile
import py7zr
import xxtea

from Crypto.Cipher import AES

from pkg.api import stories
from pkg.api.constants import *
from pkg.api.stories import FILE_STUDIO_JSON, FILE_STUDIO_THUMB, FILE_UUID, StudioStory, archive_check_7zcontent, archive_check_plain, archive_check_zipcontent

def process_archive_type(story_path):
    archive_type = TYPE_UNK

    # identifying based on filename
    if story_path.lower().endswith(EXT_PK_PLAIN):
        archive_type = archive_check_plain(story_path)
    elif story_path.lower().endswith(EXT_PK_V2):
        archive_type = TYPE_LUNII_V2_ZIP
    elif story_path.lower().endswith(EXT_PK_V1):
        archive_type = TYPE_LUNII_V2_ZIP
    elif story_path.lower().endswith(EXT_ZIP):
        archive_type = archive_check_zipcontent(story_path)
    elif story_path.lower().endswith(EXT_7Z):
        archive_type = archive_check_7zcontent(story_path)
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
                    archive_type = TYPE_LUNII_V3_ZIP
                else:
                    archive_type = TYPE_LUNII_V2_ZIP

            # no bt file, so trying to guess based on ri
            elif (any(file.endswith("ri") for file in zip_contents) and
                    any(file.endswith("si") for file in zip_contents) and
                    any(file.endswith("ni") for file in zip_contents) and
                    any(file.endswith("li") for file in zip_contents)):
                # trying to decipher ri with v2

                ri_file = next(file for file in zip_contents if file.endswith("ri"))
                ri_ciphered = zip_file.read(ri_file)
                ri_plain = v1v2_decipher(ri_ciphered, lunii_generic_key, 0, 512)
                if ri_plain[:4] == b"000\\":
                    archive_type = TYPE_LUNII_V2_ZIP
                else:
                    archive_type = TYPE_LUNII_V3_ZIP
            else:
                archive_type = TYPE_UNK

    return archive_type

def get_uuid_from_file(path):
    
    archive_type = process_archive_type(path)
    if archive_type == TYPE_LUNII_PLAIN:
        return get_uuid_from_lunii_plain(path)
    elif archive_type == TYPE_LUNII_V2_ZIP:
        return get_uuid_from_lunii_v2_zip(path)
    elif archive_type == TYPE_LUNII_V2_7Z:
        return get_uuid_from_lunii_v2_7z(path)
    elif archive_type == TYPE_LUNII_V3_ZIP:
        return get_uuid_from_lunii_v3(path)
    elif archive_type == TYPE_STUDIO_ZIP:
        return get_uuid_from_studio_zip(path)
    elif archive_type == TYPE_STUDIO_7Z:
        return get_uuid_from_studio_7z(path)
    
    return ""

def get_uuid_from_lunii_plain(story_path):

    # checking if archive is OK
    try:
        with zipfile.ZipFile(file=story_path) as zip_file:
            return UUID(bytes=zip_file.read(FILE_UUID))
    except (zipfile.BadZipFile, ValueError):
        return ""

    return ""

def get_uuid_from_lunii_v2_zip(story_path):
    try:
        with zipfile.ZipFile(file=story_path) as zip_file:
            # reading all available files
            zip_contents = zip_file.namelist()

            # getting UUID from path
            uuid_path = Path(zip_contents[0])
            uuid_str = uuid_path.parents[0].name if uuid_path.parents[0].name else uuid_path.name
            if len(uuid_str) >= 16:  # long enough to be a UUID
                if "-" not in uuid_str:
                    new_uuid = UUID(bytes=binascii.unhexlify(uuid_str))
                else:
                    new_uuid = UUID(uuid_str)
                return new_uuid
    except (zipfile.BadZipFile, ValueError):
        return ""

    return ""

def get_uuid_from_lunii_v2_7z(story_path):
    try:
        with py7zr.SevenZipFile(story_path, mode='r') as zip:
            # reading all available files
            archive_contents = zip.list()

            # getting UUID from path
            uuid_path = Path(archive_contents[0].filename)
            uuid_str = uuid_path.parents[0].name if uuid_path.parents[0].name else uuid_path.name
            if len(uuid_str) >= 16:  # long enough to be a UUID
                if "-" not in uuid_str:
                    new_uuid = UUID(bytes=binascii.unhexlify(uuid_str))
                else:
                    new_uuid = UUID(uuid_str)
                return new_uuid
    except (py7zr.exceptions.Bad7zFile, ValueError):
        return ""

    return ""

def get_uuid_from_lunii_v3(story_path):
    try:
        with zipfile.ZipFile(file=story_path) as zip_file:
            # reading all available files
            zip_contents = zip_file.namelist()

            # getting UUID from path
            uuid_path = Path(zip_contents[0])
            uuid_str = uuid_path.parents[0].name if uuid_path.parents[0].name else uuid_path.name
            if len(uuid_str) >= 16:  # long enough to be a UUID
                if "-" not in uuid_str:
                    new_uuid = UUID(bytes=binascii.unhexlify(uuid_str))
                else:
                    new_uuid = UUID(uuid_str)
                
                return new_uuid
    except (zipfile.BadZipFile, ValueError):
        return ""
    
    return ""

def get_uuid_from_studio_zip(story_path):
    try:
        with zipfile.ZipFile(file=story_path) as zip_file:
            zip_contents = zip_file.namelist()
            if FILE_UUID in zip_contents:
                return ""
            if FILE_STUDIO_JSON not in zip_contents:
                return ""

            # getting UUID file
            try:
                story_json = json.loads(zip_file.read(FILE_STUDIO_JSON))
            except ValueError as e:
                return ""

            one_story = StudioStory(story_json)
            uuid = str(one_story.uuid).upper()
            if uuid not in stories.DB_THIRD_PARTY and uuid not in stories.DB_OFFICIAL:
                stories.thirdparty_db_add_story(one_story.uuid, one_story.title, one_story.description)

            if not os.path.isfile(os.path.join(CACHE_DIR, str(one_story.uuid))):
                # Loop over each file
                for _, file in enumerate(zip_contents):
                    if file.endswith(FILE_STUDIO_THUMB):
                        # adding thumb to DB
                        data = zip_file.read(file)
                        stories.thirdparty_db_add_thumb(one_story.uuid, data)
                        continue
                    
            return one_story.uuid
        
    except (ValueError, zipfile.BadZipFile):
        return ""
    
    return ""

def get_uuid_from_studio_7z(story_path):
    try:
        with py7zr.SevenZipFile(story_path, mode='r') as zip_file:
            zip_contents = zip_file.readall()
            if FILE_UUID in zip_contents:
                return ""
            if FILE_STUDIO_JSON not in zip_contents:
                return ""
  
            # getting UUID file
            try:
                story_json = json.loads(zip_file.read(FILE_STUDIO_JSON))
            except ValueError as e:
                return ""

            one_story = StudioStory(story_json)
            uuid = str(one_story.uuid).upper()
            if uuid not in stories.DB_THIRD_PARTY and uuid not in stories.DB_OFFICIAL:
                stories.thirdparty_db_add_story(one_story.uuid, one_story.title, one_story.description)

            if not os.path.isfile(os.path.join(CACHE_DIR, str(one_story.uuid))):
                # Loop over each file
                for _, file in enumerate(zip_contents):
                    if file.endswith(FILE_STUDIO_THUMB):
                        # adding thumb to DB
                        data = zip_file.read(file)
                        stories.thirdparty_db_add_thumb(one_story.uuid, data)
                        continue
                
            return one_story.uuid
    except (ValueError, py7zr.exceptions.Bad7zFile):
        return ""

    return ""

def v1v2_decipher(buffer, key, offset, dec_len):
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

def v3_decipher(buffer, key, iv, offset, dec_len):
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

def v1v2_cipher(buffer, key, offset, enc_len):
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

def v3_cipher(buffer, key, iv, offset, enc_len):
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