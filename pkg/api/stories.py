import json
import os
from uuid import UUID

STORY_UNKNOWN = "Unknown story (maybe a User created story)..."

# https://server-data-prod.lunii.com/v2/packs
UUID_DB = {}
if os.path.isfile("packs/official.json"):
    with open("packs/official.json", encoding='utf-8') as fp_db:
        db_stories = json.load(fp_db).get('response')
        UUID_DB = {db_stories[key]["uuid"].upper():value for (key, value) in db_stories.items()}



def story_name(story_uuid: UUID):
    one_uuid = str(story_uuid).upper()
    if one_uuid in UUID_DB:
        title = UUID_DB[one_uuid].get("title")
        if not title:
            locale = list(UUID_DB[one_uuid]["locales_available"].keys())[0]
            title = UUID_DB[one_uuid]["localized_infos"][locale].get("title")
        return title
    return STORY_UNKNOWN


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


