import json
import os
import subprocess
import sys
import tempfile
import unittest


REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPDATE_SCRIPT = os.path.join(REPOSITORY_ROOT, "update.py")


class AssetAuthorValidationTest(unittest.TestCase):
    def run_validator(self, author_fields):
        asset = {
            "name": "Test asset",
            "images": {"thumb": "https://example.com/test.webp"},
            **author_fields,
        }
        with tempfile.TemporaryDirectory() as directory:
            assets_directory = os.path.join(directory, "assets")
            os.mkdir(assets_directory)
            with open(
                os.path.join(assets_directory, "test.json"), "w", encoding="utf-8"
            ) as asset_file:
                json.dump(asset, asset_file)
            return subprocess.run(
                [sys.executable, UPDATE_SCRIPT, "validate"],
                cwd=directory,
                capture_output=True,
                text=True,
            )

    def test_accepts_stable_author_id(self):
        result = self.run_validator({"author_id": "defold-foundation"})
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_rejects_missing_or_malformed_author_id(self):
        for fields in ({}, {"author_id": "Defold Foundation"}, {"author_id": "-bad"}):
            with self.subTest(fields=fields):
                result = self.run_validator(fields)
                self.assertNotEqual(0, result.returncode)
                self.assertIn("author_id must use lowercase ASCII kebab-case", result.stdout)

    def test_rejects_legacy_author_field(self):
        result = self.run_validator(
            {"author_id": "defold-foundation", "author": "Defold Foundation"}
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("legacy author field is not supported", result.stdout)


if __name__ == "__main__":
    unittest.main()
