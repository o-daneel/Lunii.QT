import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import py7zr

from pkg.api.constants import LUNII_V1, LUNII_V2, LUNII_V3
from pkg.api.device_lunii import LuniiDevice
from test_studio_story import personal_story


class StudioImportTests(unittest.TestCase):
    def test_zip_and_7z_mark_v3_imports_personal_but_preserve_legacy(self):
        for version, expected_marker in [(LUNII_V1, 1), (LUNII_V2, 1), (LUNII_V3, 0)]:
            for archive_format in ["zip", "7z"]:
                with self.subTest(version=version, archive_format=archive_format):
                    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as root:
                        root = Path(root)
                        volume = root / "volume"
                        volume.mkdir()
                        # Device detection and the application-global catalogue are outside this test.
                        with patch.object(LuniiDevice, "_LuniiDevice__feed_device", return_value=True):
                            device = LuniiDevice(str(volume))
                        device.device_version = version
                        device.device_key = bytes(16)
                        device.device_iv = bytes(16)
                        device.story_key = bytes(16)
                        device.story_iv = bytes(16)
                        device.bt = bytes(32)

                        story = personal_story()
                        payload = json.dumps({
                            "format": "v1", "version": 7,
                            "title": "Synthetic import test", "description": "",
                            "stageNodes": story.js_snodes,
                            "actionNodes": story.js_anodes,
                        })
                        archive = root / f"story.{archive_format}"
                        if archive_format == "zip":
                            with zipfile.ZipFile(archive, "w") as output:
                                output.writestr("story.json", payload)
                        else:
                            with py7zr.SevenZipFile(archive, "w") as output:
                                output.writestr(payload, "story.json")

                        with patch("pkg.api.stories.thirdparty_db_add_story"):
                            importer = getattr(device, f"import_studio_{archive_format}")
                            self.assertTrue(importer(str(archive)))
                        ni = volume / ".content" / story.short_uuid / "ni"
                        self.assertEqual(ni.read_bytes()[24], expected_marker)
                        self.assertEqual((volume / ".pi").read_bytes(), story.uuid.bytes)


if __name__ == "__main__":
    unittest.main()
