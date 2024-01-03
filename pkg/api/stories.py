import json
import os
from pathlib import Path
from uuid import UUID

import requests

from pkg.api.constants import OFFICIAL_DB, OFFICIAL_DB_URL, CFG_DIR, CACHE_DIR

STORY_UNKNOWN  = "Unknown story (maybe a User created story)..."
DESC_NOT_FOUND = "No description found."

# https://server-data-prod.lunii.com/v2/packs
UUID_DB = {}


def story_load_db(reload=False):
    global UUID_DB
    # fetching db if necessary
    if not os.path.isfile(OFFICIAL_DB) or reload:
        # creating dir if not there
        if not os.path.isdir(CFG_DIR):
            Path(CFG_DIR).mkdir(parents=True, exist_ok=True)

        try:
            # Set the timeout for the request
            response = requests.get(OFFICIAL_DB_URL, timeout=5)
            if response.status_code == 200:
                # Load image from bytes
                with open(OFFICIAL_DB, "wb") as fp:
                    fp.write(response.content)

        except requests.exceptions.Timeout:
            pass
        except requests.exceptions.RequestException:
            pass

    # trying to load DB
    if os.path.isfile(OFFICIAL_DB):
        with open(OFFICIAL_DB, encoding='utf-8') as fp_db:
            db_stories = json.load(fp_db).get('response')
            UUID_DB = {db_stories[key]["uuid"].upper(): value for (key, value) in db_stories.items()}


def story_load_pict(story_uuid: UUID, reload=False):
    image_data = None

    # creating cache dir if necessary
    if not os.path.isdir(CACHE_DIR):
        Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

    # checking if present in cache
    one_uuid = str(story_uuid).upper()
    res_file = os.path.join(CACHE_DIR, one_uuid)

    if reload or not os.path.isfile(res_file):
        # downloading the image to a file
        one_story_imageURL = story_pict_URL(story_uuid)
        # print(f"Downloading for {one_uuid} to {res_file}")
        try:
            # Set the timeout for the request
            response = requests.get(one_story_imageURL, timeout=1)
            if response.status_code == 200:
                # Load image from bytes
                image_data = response.content
                with open(res_file, "wb") as fp:
                    fp.write(image_data)
            else:
                pass
        except requests.exceptions.Timeout:
            pass
        except requests.exceptions.RequestException:
            pass

    if not image_data and os.path.isfile(res_file):
        # print(f"in cache {res_file}")
        # returning file content
        with open(res_file, "rb") as fp:
            image_data = fp.read()

    return image_data


def story_name(story_uuid: UUID):
    one_uuid = str(story_uuid).upper()
    if one_uuid in UUID_DB:
        title = UUID_DB[one_uuid].get("title")
        if not title:
            locale = list(UUID_DB[one_uuid]["locales_available"].keys())[0]
            title = UUID_DB[one_uuid]["localized_infos"][locale].get("title")
        return title
    return STORY_UNKNOWN


def story_desc(story_uuid: UUID):
    one_uuid = str(story_uuid).upper()
    if one_uuid in UUID_DB:
        locale = list(UUID_DB[one_uuid]["locales_available"].keys())[0]
        desc: str = UUID_DB[one_uuid]["localized_infos"][locale].get("description")
        if desc.startswith("<link href"):
            pos = desc.find(">")
            desc = desc[pos+1:]
        return desc
    return DESC_NOT_FOUND


def story_pict_URL(story_uuid: UUID):
    one_uuid = str(story_uuid).upper()
    if one_uuid in UUID_DB:
        locale = list(UUID_DB[one_uuid]["locales_available"].keys())[0]
        image = UUID_DB[one_uuid]["localized_infos"][locale].get("image")
        if image:
            url = "https://storage.googleapis.com/lunii-data-prod" + image.get("image_url")
            return url
    return None


def _uuid_match(uuid: UUID, key_part: str):
    uuid = str(uuid).upper()
    uuid = uuid.replace("-", "")

    key_part = key_part.upper()
    key_part = key_part.replace("-", "")

    return key_part in uuid


class StoryList(list):
    def __init__(self):
        super().__init__()

    def __contains__(self, key_part):
        for uuid in self:
            if _uuid_match(uuid, key_part):
                return True
        return False
    
    def full_uuid(self, short_uuid):
        ulist = [uuid for uuid in self if _uuid_match(uuid, short_uuid)]
        return ulist
    
    def name(self, short_uuid: str):
        short_uuid = short_uuid.upper()
        for uuid in self:
            if str(uuid).upper().endswith(short_uuid):
                return story_name(uuid)
        return None
