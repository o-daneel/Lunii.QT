import requests

from pkg.api.constants import *

# anonymous fake lunii created to get v1 v2 fw
V1V2_FAHID = "-NnUun90mQ56GosDyA3R"


def lunii_get_authtoken(login, password):
    user_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJ1aWQiOiItTHgya3dWeFdvRmY1STJteEVTTyIsInJvbGUiOiJDVVNUT01FUiIsImNvdW50cnlDb2RlIjoiZnIiLCJleHAiOjE3MDU2MTA4MDMuNDc0fQ.jMGz__wGv3c-_LBMdAxeyB-FegO3KcXfjn0Lf4kBxq3IFPDi_s2ldhQ04L9QHZb9p1LFqXL5H_PN14Ctks4d714ih1iH70eMd0VhSihSX1G9mJ5yiczVXN2x3Q1HHcwKCTDBaQd-iMVtldqRDNkph97DBKrjT7CKfRcPI5eXKqai6O-rLPSCM_kCOw-ST89Q96PlJaxSIU7p489UAFXQmZXQrBC14m-4sflfKInvnAcNxXTJzmJH5Rztj-OlSsyQPT-9z_Rc6NK_bJvzGUWwCN5LEzUAgA75YnCILTHl9WZT7597WiaiTJiauYLpSfA9n6Hvb6oS_JUs1zUZB1_L4w"
    header_auth = {'x-auth-token':user_token,
                   'authorization': f'Bearer {user_token}'
                  }
    return header_auth


def lunii_vid_pid(hw_version):
    if hw_version == LUNII_V1:
        return FAH_V1_FW_2_USB_VID_PID
    else:
        return FAH_V2_V3_USB_VID_PID


def lunii_fw_version(hw_version, json_auth, fu_upgrade=False):
    vid, pid = lunii_vid_pid(hw_version)

    if hw_version <= LUNII_V2:
        json_auth["user-agent"]="unirest-java/3.1.00"
        fw = requests.get(f"https://server-user-prod.lunii.com/v2/fah/{V1V2_FAHID}/update/current?vendor_id={vid:04x}&product_id={pid:04x}", headers=json_auth)
        if fw.status_code == 200:
            # print(fw.json())
            print("Last FW version :")
            versions = fw.json()["response"]["currentUpdate"]
            if versions.get("fu_version") and fu_upgrade:
                return f"{versions['fu_version']['major']}_{versions['fu_version']['minor']}"
            if versions.get("fa_version") and not fu_upgrade:
                return f"{versions['fa_version']['major']}_{versions['fa_version']['minor']}"

    return None


def lunii_fw_download(hw_version, snu, json_auth, filepath: str, fu_upgrade=False):
    vid, pid = lunii_vid_pid(hw_version)

    json_auth["user-agent"]="unirest-java/3.1.00"
    if hw_version <= LUNII_V2:
        fw = requests.get(f"https://server-user-prod.lunii.com/v2/fah/{V1V2_FAHID}/update?vendor_id={vid:04x}&product_id={pid:04x}", headers=json_auth)
        if fw.status_code == 200:

            # getting FU.BIN
            if fw.json()['response']['update'].get('fu_file') and fu_upgrade:
                url = fw.json()['response']['update']['fu_file']['url']
                # print(url)
                fw_file = requests.get(url)
                if fw_file.status_code == 200:
                    with open(filepath, "wb") as fu:
                        fu.write(fw_file.content)
                        return fu.tell()

            # getting FA.BIN
            if fw.json()['response']['update'].get('fa_file') and not fu_upgrade:
                url = fw.json()['response']['update']['fa_file']['url']
                # print(url)
                fw_file = requests.get(url)
                if fw_file.status_code == 200:
                    with open(filepath, "wb") as fa:
                        fa.write(fw_file.content)
                        return fa.tell()

    elif hw_version == LUNII_V3:
        fw = requests.get(f"https://server-backend-prod.lunii.com/devices/{snu}/firmware?installed=3.1.2", headers=json_auth)

        # getting FA.BIN
        if fw.status_code == 200:
            with open(filepath, "wb") as fa:
                fa.write(fw.content)
                return fa.tell()

    return 0

