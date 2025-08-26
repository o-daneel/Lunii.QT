import requests

from pkg.api.aes_keys import reverse_bytes
from pkg.api.constants import *

# anonymous fake lunii created to get v1 v2 fw
V1V2_FAHID = "-NnUun90mQ56GosDyA3R"

FW_HEADERS = {
    (3, 2, 2): (reverse_bytes(b"\x00\x00\x04\x20\xD9\x52\x03\x90\xBF\xAD\x02\x90\xC1\xAD\x02\x90"),
                reverse_bytes(b"\xEB\xAD\x02\x90\xED\xAD\x02\x90\xEF\xAD\x02\x90\x00\x00\x00\x00")),
}

def luniistore_get_authtoken(login, pwd):
    url_sign = "https://server-auth-prod.lunii.com/auth/signin"
    args1 = {'application': "luniistore_mobile",
             'email': login,
             'password': pwd
            }
    auth = requests.post(url_sign, json=args1)
    if auth.status_code != 200:
        return None

    # token = auth.json()['response']['tokens']['access_tokens']['user']['server']
    # user_id = auth.json()['response']['user_id']

    # print("\nToken: {0}".format(token))
    # print("\nUser ID: {0}".format(user_id))

    header_auth = {'x-auth-token': auth.json()['response']['tokens']['access_tokens']['user']['server'],
                   'authorization': 'Bearer {0}'.format(auth.json()['response']['tokens']['access_tokens']['user']['server'])
                  }

    return header_auth


def __lunii_vid_pid(hw_version):
    if hw_version == LUNII_V1:
        return FAH_V1_FW_2_USB_VID_PID
    else:
        return FAH_V2_V3_USB_VID_PID


def device_fw_getlist(hw_version, snu_str, json_auth):
    fw_list = []

    if hw_version == LUNII_V1:
        fw_list.append(f"fa.v{luniiv1_fw_version(hw_version, json_auth)}.bin")
        fw_list.append(f"fu.v{luniiv1_fw_version(hw_version, json_auth, True)}.bin")
    elif hw_version == LUNII_V2:
        fw_list.append(f"fa.v{luniiv1_fw_version(hw_version, json_auth)}.bin")
    elif hw_version == LUNII_V3:
        fw_list.append(f"fa.{snu_str}.v3xx.bin")
    elif hw_version == FLAM_V1:
        fw_list.append("update-main.enc")
        fw_list.append("update-comm.enc")

    return fw_list


def luniiv1_fw_version(hw_version, json_auth, fu_upgrade=False):
    vid, pid = __lunii_vid_pid(hw_version)

    if hw_version <= LUNII_V2:
        json_auth["user-agent"] = "unirest-java/3.1.00"
        fw = requests.get(f"https://server-user-prod.lunii.com/v2/fah/{V1V2_FAHID}/update/current?vendor_id={vid:04x}&product_id={pid:04x}", headers=json_auth, timeout=10)
        if fw.status_code == 200:
            # print(fw.json())
            versions = fw.json()["response"]["currentUpdate"]
            if versions.get("fu_version") and fu_upgrade:
                return f"{versions['fu_version']['major']}_{versions['fu_version']['minor']}"
            if versions.get("fa_version") and not fu_upgrade:
                return f"{versions['fa_version']['major']}_{versions['fa_version']['minor']}"

    return None


def device_fw_download(hw_version, snu, json_auth, filepath: str, second_fw=False):
    vid, pid = __lunii_vid_pid(hw_version)

    json_auth["user-agent"] = "unirest-java/3.1.00"
    if hw_version <= LUNII_V2:
        fw = requests.get(f"https://server-user-prod.lunii.com/v2/fah/{V1V2_FAHID}/update?vendor_id={vid:04x}&product_id={pid:04x}", headers=json_auth, timeout=10)
        if fw.status_code == 200:

            # getting FU.BIN
            if fw.json()['response']['update'].get('fu_file') and second_fw:
                url = fw.json()['response']['update']['fu_file']['url']
                # print(url)
                fw_file = requests.get(url, timeout=10)
                if fw_file.status_code == 200:
                    with open(filepath, "wb") as fu:
                        fu.write(fw_file.content)
                        return fu.tell()

            # getting FA.BIN
            if fw.json()['response']['update'].get('fa_file') and not second_fw:
                url = fw.json()['response']['update']['fa_file']['url']
                # print(url)
                fw_file = requests.get(url, timeout=10)
                if fw_file.status_code == 200:
                    with open(filepath, "wb") as fa:
                        fa.write(fw_file.content)
                        return fa.tell()

    elif hw_version == LUNII_V3:
        fw = requests.get(f"https://server-backend-prod.lunii.com/devices/{snu}/firmware?installed=3.1.2", headers=json_auth, timeout=10)

        # getting FA.BIN
        if fw.status_code == 200:
            with open(filepath, "wb") as fa:
                fa.write(fw.content)
                return fa.tell()

    elif hw_version == FLAM_V1:
        if not second_fw:
            chipset = "main"
        else:
            chipset = "comm"
        fw = requests.get(f"https://server-backend-prod.lunii.com/devices/{snu}/firmware?installed=1.1.1-01&chipset={chipset}", headers=json_auth, timeout=10)

        # getting FA.BIN
        if fw.status_code == 200:
            with open(filepath, "wb") as fa:
                fa.write(fw.content)
                return fa.tell()

    return 0

