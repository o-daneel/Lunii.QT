import os

def reverse_bytes(input_bytes):
    if len(input_bytes) %4 != 0:
        print("Input buffer must be modulo 4")
        return None

    groups_of_4 = [input_bytes[i:i+4] for i in range(0, len(input_bytes), 4)]
    reversed_groups = [group[::-1] for group in groups_of_4]
    final_key = b''.join(reversed_groups)

    return final_key

def fetch_keys(keyfile):
    key = None
    iv  = None

    if keyfile and os.path.isfile(keyfile):
        with open(keyfile, "rb") as fk:
            key = reverse_bytes(fk.read(0x10))
            iv  = reverse_bytes(fk.read(0x10))

    return key, iv