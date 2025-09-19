import platform
import psutil
import logging

from pkg.api.constants import *
from pkg.api.device_flam import is_flam
from pkg.api.device_lunii import is_lunii


def find_devices(extra_path=None):
    logger = logging.getLogger(LUNII_LOGGER)

    dev_list = []

    current_os = platform.system()
    logger.log(logging.INFO, "Finding devices...")

    if current_os == "Windows":
        # checking all drive letters
        for drive in range(ord('A'), ord('Z')+1):
            drv_str = f"{chr(drive)}:/"
            dev_path = Path(drv_str)

            if is_lunii(dev_path):
                logger.log(logging.DEBUG, f"- {dev_path} : Lunii found")
                dev_list.append(dev_path)

            if is_flam(dev_path):
                logger.log(logging.DEBUG, f"- {dev_path} : Flam found")
                dev_list.append(dev_path)

        # checking for extra path
        if extra_path:
            dev_path = Path(extra_path)

            if is_lunii(dev_path):
                dev_list.append(dev_path)
            elif is_flam(dev_path):
                dev_list.append(dev_path)

    elif current_os == "Linux":
        # Iterate through all partitions
        for part in psutil.disk_partitions():
            logger.log(logging.DEBUG, f"- {part}")
            if (part.device.startswith("/dev/sd") and
                    (part.fstype.startswith("msdos") or part.fstype == "vfat")):
                if is_lunii(part.mountpoint):
                    logger.log(logging.DEBUG, "  Lunii found")
                    dev_list.append(part.mountpoint)
                elif is_flam(part.mountpoint):
                    logger.log(logging.DEBUG, "  Flam found")
                    dev_list.append(part.mountpoint)

    elif current_os == "Darwin":
        # Iterate through all partitions
        for part in psutil.disk_partitions():
            logger.log(logging.DEBUG, f"- {part}")
            if (any(part.mountpoint.lower().startswith(mnt_pt) for mnt_pt in ["/mnt", "/media", "/volume"]) and
                    (part.fstype.startswith("msdos") or part.fstype == "vfat")):
                if is_lunii(part.mountpoint):
                    logger.log(logging.DEBUG, "  Lunii found")
                    dev_list.append(part.mountpoint)
                elif is_flam(part.mountpoint):
                    logger.log(logging.DEBUG, "  Flam found")
                    dev_list.append(part.mountpoint)

    logger.log(logging.INFO, f"> found {len(dev_list)} devices")

    # done
    return dev_list



