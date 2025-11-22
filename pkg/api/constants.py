import os
import shutil
import zlib
from pathlib import Path

# this logger MUST not be used from worker thread.
LUNII_LOGGER = "lunii-qt"
REFRESH_CACHE = False
CACHE_CRC32 = 0x0F77E60C

STORY_TRANSCODING_SUPPORTED = shutil.which("ffmpeg") is not None

def toggle_refresh_cache():
    global REFRESH_CACHE
    REFRESH_CACHE = True

def check_refresh_cache(snu):
    global REFRESH_CACHE
    REFRESH_CACHE = (zlib.crc32(snu) == CACHE_CRC32)

def vectkey_to_bytes(key_vect):
    joined = [k.to_bytes(4, 'little') for k in key_vect]
    return b''.join(joined)


def lunii_tea_rounds(buffer):
    return int(1 + 52 / (len(buffer)/4))

# external flash hardcoded value
# 91BD7A0A A75440A9 BBD49D6C E0DCC0E3
raw_key_generic = [0x91BD7A0A, 0xA75440A9, 0xBBD49D6C, 0xE0DCC0E3]
lunii_generic_key = vectkey_to_bytes(raw_key_generic)

# import binascii
# lunii_generic_key = binascii.unhexlify(b'00112233445566770011223344556677')

OFFICIAL_TOKEN_URL = "https://server-auth-prod.lunii.com/guest/create"
OFFICIAL_DB_URL = "https://server-data-prod.lunii.com/v2/packs"
OFFICIAL_DB_RESOURCES_URL = "https://storage.googleapis.com/lunii-data-prod"

CFG_DIR: Path = os.path.join(Path.home(), ".lunii-qt")
CACHE_DIR = os.path.join(CFG_DIR, "cache")
TEMP_DIR = os.path.join(CFG_DIR, "temp")
FILE_SETTINGS = os.path.join(CFG_DIR, "settings.json")
FILE_OFFICIAL_DB = os.path.join(CFG_DIR, "official.db")
FILE_LOCAL_LIBRAIRY_DB = os.path.join(CFG_DIR, "local-library.db")
FILE_THIRD_PARTY_DB = os.path.join(CFG_DIR, "third-party.db")
V3_KEYS = os.path.join(CFG_DIR, "v3.keys")

LUNII_V1or2_UNK = 0
LUNII_V1 = 1
LUNII_V2 = 2
LUNII_V3 = 3
FLAM_V1  = 10
UNDEF_DEV = 255

FAH_V1_USB_VID_PID      = (0x0c45, 0x6820)
FAH_V1_FW_2_USB_VID_PID = (0x0c45, 0x6840)
FAH_V2_V3_USB_VID_PID   = (0x0483, 0xa341)
FLAM_USB_VID_PID        = (0x303A, 0x819E)


TYPE_UNK            = 0x00 # undefined
TYPE_LUNII_PLAIN    = 0x01 # Lunii plain story
TYPE_LUNII_V3_ZIP   = 0x02 # Lunii v3 (aes) zip
TYPE_LUNII_FLAM_ZIP = 0x03 # Lunii from Flam (aes) zip
TYPE_LUNII_V2_ZIP   = 0x10 # Lunii v2 (xxtea) zip 
TYPE_LUNII_V2_7Z    = 0x11 # Lunii v2 (xxtea) 7zip
TYPE_STUDIO_ZIP     = 0x20 # Studio format
TYPE_STUDIO_7Z      = 0x21 # Studio format
TYPE_FLAM_ZIP       = 0x40 # Flam backup as zip
TYPE_FLAM_7Z        = 0x41 # Flam backup as 7z
TYPE_FLAM_PLAIN     = 0x42 # Flam plain story

EXT_PK_PLAIN = ".plain.pk"
EXT_PK_V2    = ".v2.pk"
EXT_PK_V1    = ".v1.pk"
EXT_PK_VX    = ".pk"
EXT_ZIP      = ".zip"
EXT_7Z       = ".7z"

LUNII_SUPPORTED_EXT = [EXT_ZIP, EXT_7Z, EXT_PK_V1, EXT_PK_V2, EXT_PK_PLAIN, EXT_PK_VX]
FLAM_SUPPORTED_EXT = [EXT_ZIP, EXT_7Z, EXT_PK_PLAIN, EXT_PK_VX]

LUNII_CFGPOS_IDLE_TIME      = 0
LUNII_CFGPOS_LOWBAT_TIME    = 2
LUNII_CFGPOS_NM_ENABLED     = 3
LUNII_CFGPOS_NM_VOL_LIMIT   = 4
LUNII_CFGPOS_NM_STORYCOUNT  = 5
LUNII_CFGPOS_NM_AUTOPLAY    = 7
LUNII_CFGPOS_NM_TURNOFF_NM  = 8