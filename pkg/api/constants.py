import os
import shutil
from pathlib import Path

# this logger MUST not be used from worker thread.
LUNII_LOGGER = "lunii-qt"
REFRESH_CACHE = False

STORY_TRANSCODING_SUPPORTED = shutil.which("ffmpeg") is not None

def toggle_refresh_cache():
    global REFRESH_CACHE
    REFRESH_CACHE = True


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

CFG_DIR: Path = os.path.join(Path.home(), ".lunii-qt")
CACHE_DIR = os.path.join(CFG_DIR, "cache")
FILE_OFFICIAL_DB = os.path.join(CFG_DIR, "official.db")
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


TYPE_UNK    = 0
TYPE_PLAIN  = 1
TYPE_V2     = 2
TYPE_V3     = 3
TYPE_ZIP    = 10
TYPE_7Z     = 11
TYPE_STUDIO_ZIP = 20
TYPE_STUDIO_7Z  = 21
TYPE_FLAM_ZIP   = 30
TYPE_FLAM_7Z    = 31


EXT_PK_PLAIN = ".plain.pk"
EXT_PK_V2    = ".v2.pk"
EXT_PK_V1    = ".v1.pk"
EXT_PK_VX    = ".pk"
EXT_ZIP      = ".zip"
EXT_7z       = ".7z"

LUNII_SUPPORTED_EXT = [EXT_ZIP, EXT_7z, EXT_PK_V1, EXT_PK_V2, EXT_PK_PLAIN, EXT_PK_VX]
FLAM_SUPPORTED_EXT = [EXT_ZIP, EXT_7z]

