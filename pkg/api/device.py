import os
import shutil
import zipfile
import xxtea
import binascii
from pathlib import Path
from uuid import UUID

from tqdm import tqdm

from pkg.api.constants import *
from pkg.api.stories import StoryList


class LuniiDevice:
    stories: StoryList

    def __init__(self, mount_point):
        self.mount_point = mount_point

        # dummy values
        self.UUID = ""
        self.device_key = ""
        self.snu = ""
        self.fw_vers_major = 0
        self.fw_vers_minor = 0
        self.memory_left = 0

        # internal device details
        self.__feed_device()

        # internal stories
        self.stories = feed_stories(self.mount_point)

    # opens the .pi file to read all installed stories
    def __feed_device(self):
        
        mount_path = Path(self.mount_point)
        md_path = mount_path.joinpath(".md")

        with open(md_path, "rb") as fp_md:
            fp_md.seek(fp_md.tell() + 6)
            self.fw_vers_major = int.from_bytes(fp_md.read(2), 'little')
            self.fw_vers_minor = int.from_bytes(fp_md.read(2), 'little')
            self.snu = int.from_bytes(fp_md.read(8), 'little')
            
            fp_md.seek(0x100)
            self.raw_devkey = fp_md.read(0x100)
            dec = xxtea.decrypt(self.raw_devkey, lunii_generic_key, padding=False, rounds=lunii_tea_rounds(self.raw_devkey))
            # Reordering Key components
            self.device_key = dec[8:16] + dec[0:8]

    @property
    def snu_hex(self):
        return self.snu.to_bytes(8, 'little')
    
    def __repr__(self):
        repr_str  = f"Lunii device on \"{self.mount_point}\"\n"
        repr_str += f"- firmware : v{self.fw_vers_major}.{self.fw_vers_minor}\n"
        repr_str += f"- snu      : {binascii.hexlify(self.snu_hex, ' ')}\n"
        repr_str += f"- dev key  : {binascii.hexlify(self.device_key, ' ')}\n"
        repr_str += f"- stories  : {len(self.stories)}x\n"
        return repr_str

    def export_all(self, out_path):
        archives = []
        for count, story in enumerate(self.stories):
            print(f"{count+1:>2}/{len(self.stories)} ", end="")
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

    def export_story(self, uuid, out_path):
        # is UUID part of existing stories
        if uuid not in self.stories:
            return None

        ulist = self.stories.full_uuid(uuid)
        if len(ulist) > 1:
            print(f"ERROR: at least {len(ulist)} match your pattern. Try a longer UUID.")
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
        
        print(f"[{uuid} - {self.stories.name(uuid)}]")

        # Preparing zip file
        zip_path = Path(out_path).joinpath(f"{uuid} - {self.stories.name(uuid)}.zip")
        # preparing file list
        story_flist = []
        for root, dirnames, filenames in os.walk(story_path):
            for filename in filenames:
                if filename == "bt":
                    continue
                story_flist.append(os.path.join(root, filename))

        with zipfile.ZipFile(zip_path, 'w') as zip_out:
            print("> Zipping story ...")
            pbar = tqdm(iterable=story_flist, total=len(story_flist), bar_format=TQDM_BAR_FORMAT)
            for file in pbar:
                target_name = Path(file).relative_to(story_path)
                pbar.set_description(f"Processing {target_name}")

                # Extract each file to another directory
                # If you want to extract to current working directory, don't specify path
                zip_out.write(file, arcname=target_name)

            # adding uuid file
            print("> Adding UUID ...")
            zip_out.writestr("uuid.bin", full_uuid.bytes)

        return zip_path

    def import_story(self, story_path):
        # opening zip file
        with zipfile.ZipFile(file=story_path) as zip_file:
            # reading all available files
            zip_contents = zip_file.namelist()
            if "uuid.bin" not in zip_contents:
                print("ERROR: No UUID file found in archive. Unable to add this story.")
                return False

            # getting UUID file
            new_uuid = UUID(bytes=zip_file.read("uuid.bin"))

            # checking if UUID already loaded
            if str(new_uuid) in self.stories:
                print("ERROR: This story is already loaded, aborting !")
                return False

            # decompressing story contents
            output_path = Path(self.mount_point).joinpath(f".content/{str(new_uuid).upper()[28:]}")
            if not output_path.exists():
                output_path.mkdir(parents=True)

            # Loop over each file
            count = 0
            pbar = tqdm(iterable=zip_contents, total=len(zip_contents), bar_format=TQDM_BAR_FORMAT)
            for file in pbar:
                count += 1
                if file == "uuid.bin":
                    continue
                pbar.set_description(f"Processing {file}")

                # Extract each file to another directory
                # If you want to extract to current working directory, don't specify path
                zip_file.extract(member=file, path=output_path)

        # creating authorization file : bt
        print("INFO : Authorization file creation...")
        bt_path = output_path.joinpath("bt")
        ri_path = output_path.joinpath("ri")
        with open(bt_path, "wb") as fp_bt:
            with open(ri_path, "rb") as ri_bt:
                ri_chunk = ri_bt.read(0x40)
                enc = xxtea.encrypt(ri_chunk, self.device_key, padding=False, rounds=lunii_tea_rounds(ri_chunk))
                fp_bt.write(enc)

        # updating .pi file to add new UUID
        self.stories.append(new_uuid)
        self.update_pack_index()

        return True

    def remove_story(self, short_uuid):
        if short_uuid not in self.stories:
            print("ERROR: This story is not present on your storyteller")
            return False

        ulist = self.stories.full_uuid(short_uuid)
        if len(ulist) > 1:
            print(f"ERROR: at least {len(ulist)} match your pattern. Try a longer UUID.")
            # return False
        uuid = str(ulist[0])

        print(f"Removing {uuid[28:]} - {self.stories.name(uuid)}...")
        self.stories.remove(ulist[0])

        # asking for confirmation
        answer = input("Are you sure ? [y/N] ")
        if answer.lower() not in ["y", "yes"]:
            return False

        # removing story contents
        st_path = Path(self.mount_point).joinpath(f".content/{uuid[28:]}")
        shutil.rmtree(st_path)

        # updating pack index file
        self.update_pack_index()

        return True


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
