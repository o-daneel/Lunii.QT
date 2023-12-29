import os
from pathlib import Path


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

OFFICIAL_DB_URL = "https://server-data-prod.lunii.com/v2/packs"

CFG_DIR: Path = os.path.join(Path.home(), ".lunii-qt")
CACHE_DIR = os.path.join(CFG_DIR, "cache")
OFFICIAL_DB = os.path.join(CFG_DIR, "official.db")

LUNII_V2 = 2
LUNII_V3 = 3

TYPE_UNK    = 0
TYPE_PLAIN  = 1
TYPE_V2     = 2
TYPE_V3     = 3
TYPE_ZIP    = 10
TYPE_7Z     = 11

EXT_PK_PLAIN = ".plain.pk"
EXT_PK_V2    = ".v2.pk"
EXT_PK_V1    = ".v1.pk"
EXT_ZIP      = ".zip"
EXT_7z       = ".7z"

SUPPORTED_EXT = [EXT_ZIP, EXT_7z, EXT_PK_V1, EXT_PK_V2, EXT_PK_PLAIN]