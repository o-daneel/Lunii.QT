import json
import os
from pathlib import Path
from typing import List
from uuid import UUID

import requests

from pkg.api.constants import OFFICIAL_DB_URL, CFG_DIR, CACHE_DIR, FILE_OFFICIAL_DB, FILE_THIRD_PARTY_DB

STORY_UNKNOWN  = "Unknown story (maybe a User created story)..."
DESC_NOT_FOUND = "No description found."

# https://server-data-prod.lunii.com/v2/packs
DB_OFFICIAL = {}
DB_THIRD_PARTY = {}


def story_load_db(reload=False):
    global DB_OFFICIAL
    global DB_THIRD_PARTY
    retVal = True

    # fetching db if necessary
    if not os.path.isfile(FILE_OFFICIAL_DB) or reload:
        # creating dir if not there
        if not os.path.isdir(CFG_DIR):
            Path(CFG_DIR).mkdir(parents=True, exist_ok=True)

        try:
            # Set the timeout for the request
            response = requests.get(OFFICIAL_DB_URL, timeout=30)
            if response.status_code == 200:
                # Load image from bytes
                j_resp = json.loads(response.content)
                with (open(FILE_OFFICIAL_DB, "w") as fp):
                    db = j_resp.get('response')
                    json.dump(db, fp)

        except requests.exceptions.Timeout:
            retVal = False
        except requests.exceptions.RequestException:
            retVal = False

    # trying to load official DB
    if os.path.isfile(FILE_OFFICIAL_DB):
        try:
            with open(FILE_OFFICIAL_DB, encoding='utf-8') as fp_db:
                db_stories = json.load(fp_db)
                DB_OFFICIAL = {db_stories[key]["uuid"].upper(): value for (key, value) in db_stories.items()}
        except:
            db = Path(FILE_OFFICIAL_DB)
            db.unlink(FILE_OFFICIAL_DB)

    # trying to load third-party DB
    if os.path.isfile(FILE_THIRD_PARTY_DB):
        try:
            with open(FILE_THIRD_PARTY_DB, encoding='utf-8') as fp_db:
                db_stories = json.load(fp_db)
                DB_THIRD_PARTY = {db_stories[key]["uuid"].upper(): value for (key, value) in db_stories.items()}
        except:
            db = Path(FILE_THIRD_PARTY_DB)
            db.unlink(FILE_THIRD_PARTY_DB)

    return retVal


def _uuid_match(uuid: UUID, key_part: str):
    uuid = uuid.hex.upper()
    key_part = key_part.replace("-", "").upper()

    return key_part in uuid


class Story:
    def __init__(self, uuid: UUID, size: int=-1):
        self.uuid = uuid
        self.size = size

    def __eq__(self, __value: UUID):
        return self.uuid == __value

    @property
    def str_uuid(self):
        return str(self.uuid).upper()

    @property
    def short_uuid(self):
        return self.uuid.hex[24:].upper()

    @property
    def name(self):
        one_uuid = str(self.uuid).upper()

        # checking official DB
        if one_uuid in DB_OFFICIAL:
            title = DB_OFFICIAL[one_uuid].get("title")
            if not title:
                locale = list(DB_OFFICIAL[one_uuid]["locales_available"].keys())[0]
                title = DB_OFFICIAL[one_uuid]["localized_infos"][locale].get("title")
            return title

        # checking third-party DB
        if one_uuid in DB_THIRD_PARTY:
            title = DB_THIRD_PARTY[one_uuid].get("title")
            if title:
                return title

        return STORY_UNKNOWN

    @property
    def desc(self):
        one_uuid = str(self.uuid).upper()

        # checking official DB
        if one_uuid in DB_OFFICIAL:
            locale = list(DB_OFFICIAL[one_uuid]["locales_available"].keys())[0]
            desc: str = DB_OFFICIAL[one_uuid]["localized_infos"][locale].get("description")
            if desc.startswith("<link href"):
                pos = desc.find(">")
                desc = desc[pos+1:]
            return desc

        # checking third-party DB
        if one_uuid in DB_THIRD_PARTY:
            desc = DB_THIRD_PARTY[one_uuid].get("description")
            if desc:
                return desc

        return DESC_NOT_FOUND

    def get_picture(self, reload: bool=False):
        image_data = None

        # creating cache dir if necessary
        if not os.path.isdir(CACHE_DIR):
            Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

        # checking if present in cache
        one_uuid = str(self.uuid).upper()
        res_file = os.path.join(CACHE_DIR, one_uuid)

        if reload or not os.path.isfile(res_file):
            # downloading the image to a file
            one_story_imageURL = self.picture_url()
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

    def picture_url(self):
        one_uuid = str(self.uuid).upper()

        if one_uuid in DB_OFFICIAL:
            locale = list(DB_OFFICIAL[one_uuid]["locales_available"].keys())[0]
            image = DB_OFFICIAL[one_uuid]["localized_infos"][locale].get("image")
            if image:
                url = "https://storage.googleapis.com/lunii-data-prod" + image.get("image_url")
                return url
        return None

    def is_official(self):
        global DB_OFFICIAL
        return str(self.uuid).upper() in DB_OFFICIAL


class StoryList(List[Story]):
    def __init__(self):
        super().__init__()

    def __contains__(self, key_part):
        for one_story in self:
            if _uuid_match(one_story.uuid, str(key_part)):
                return True
        return False

    def get_story(self, key_part: str):
        for one_story in self:
            if _uuid_match(one_story.uuid, str(key_part)):
                return one_story

    def matching_stories(self, short_uuid):
        slist = [one_story for one_story in self if _uuid_match(one_story.uuid, short_uuid)]
        return slist
