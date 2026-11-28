import struct
import unittest

from pkg.api.stories import StudioStory


def story_data():
    return {
        "format": "v1",
        "version": 7,
        "title": "Personal test story",
        "description": "Synthetic fixture without device data or media",
        "stageNodes": [
            {
                "uuid": "11111111-1111-4111-8111-111111111111",
                "image": "1111111111111111111111111111111111111111.png",
                "audio": "2222222222222222222222222222222222222222.mp3",
                "okTransition": {"actionNode": "play", "optionIndex": 0},
                "homeTransition": None,
                "controlSettings": {
                    "wheel": True, "ok": True, "home": False,
                    "pause": False, "autoplay": False,
                },
            },
            {
                "uuid": "22222222-2222-4222-8222-222222222222",
                "image": None,
                "audio": "2222222222222222222222222222222222222222.mp3",
                "okTransition": {"actionNode": "home", "optionIndex": 0},
                "homeTransition": {"actionNode": "home", "optionIndex": 0},
                "controlSettings": {
                    "wheel": False, "ok": True, "home": True,
                    "pause": True, "autoplay": True,
                },
            },
        ],
        "actionNodes": [
            {"id": "play", "options": ["22222222-2222-4222-8222-222222222222"]},
            {"id": "home", "options": ["11111111-1111-4111-8111-111111111111"]},
        ],
    }


def personal_story(factory_pack=False):
    return StudioStory(story_data(), factory_pack=factory_pack)


class StudioStoryTests(unittest.TestCase):
    def test_personal_import_is_not_marked_as_factory_pack(self):
        self.assertEqual(personal_story().get_ni_data()[24], 0)

    def test_ni_preserves_header_geometry_nodes_transitions_and_controls(self):
        expected_header = struct.pack("<HHIIIIIB", 1, 7, 512, 44, 2, 1, 1, 0)
        expected_header += bytes(512 - len(expected_header))
        expected_cover = struct.pack(
            "<8i6H", 0, 0, 0, 1, 0, -1, -1, -1, 1, 1, 0, 0, 0, 0
        )
        expected_audio = struct.pack(
            "<8i6H", -1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1, 1, 1, 0
        )
        self.assertEqual(
            personal_story().get_ni_data(),
            expected_header + expected_cover + expected_audio,
        )

    def test_explicit_factory_marker_is_preserved_for_other_devices(self):
        self.assertEqual(personal_story(factory_pack=True).get_ni_data()[24], 1)

    def test_constructor_defaults_to_existing_factory_marker(self):
        self.assertEqual(StudioStory(story_data()).get_ni_data()[24], 1)

    def test_asset_and_link_indexes_remain_unchanged(self):
        story = personal_story()
        self.assertEqual(story.get_ri_data(), b"000\\11111111")
        self.assertEqual(story.get_si_data(), b"000\\22222222")
        self.assertEqual(story.get_li_data(), struct.pack("<2i", 1, 0))


if __name__ == "__main__":
    unittest.main()
