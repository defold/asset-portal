import json
import os
import subprocess
import sys
import tempfile
import unittest

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPDATE_SCRIPT = os.path.join(REPOSITORY_ROOT, "update.py")


class AssetImagesValidationTest(unittest.TestCase):
    def run_validator(self, images=None, image_files=()):
        asset = {"name": "Test asset", "author_id": "test-author"}
        if images is not None:
            asset["images"] = images

        with tempfile.TemporaryDirectory() as directory:
            assets_directory = os.path.join(directory, "assets")
            images_directory = os.path.join(assets_directory, "images")
            os.makedirs(images_directory)
            for image_file in image_files:
                with open(
                    os.path.join(images_directory, image_file), "wb"
                ) as output_file:
                    output_file.write(b"test image")
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

    def test_accepts_supported_local_thumbnail_formats(self):
        for extension in ("webp", "png", "jpg", "jpeg"):
            with self.subTest(extension=extension):
                filename = "test-thumb.{}".format(extension)
                result = self.run_validator(
                    {"thumb": filename}, image_files=(filename,)
                )

                self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_accepts_legacy_https_thumbnail_and_ignores_hero(self):
        result = self.run_validator(
            {
                "thumb": "https://example.com/test-thumb.jpg?version=1",
                "hero": "legacy-hero-file-that-does-not-exist.webp",
            }
        )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_rejects_missing_or_blank_thumbnail(self):
        for images in (None, {}, {"thumb": ""}):
            with self.subTest(images=images):
                result = self.run_validator(images)

                self.assertNotEqual(0, result.returncode)
                self.assertIn("Invalid asset images", result.stdout)

    def test_rejects_missing_local_thumbnail(self):
        result = self.run_validator({"thumb": "missing-thumb.webp"})

        self.assertNotEqual(0, result.returncode)
        self.assertIn("local thumbnail does not exist", result.stdout)

    def test_rejects_unsupported_thumbnail_format(self):
        result = self.run_validator({"thumb": "test-thumb.gif"})

        self.assertNotEqual(0, result.returncode)
        self.assertIn("must use WebP, PNG, JPG, or JPEG", result.stdout)

    def test_rejects_insecure_remote_thumbnail(self):
        result = self.run_validator({"thumb": "http://example.com/test-thumb.webp"})

        self.assertNotEqual(0, result.returncode)
        self.assertIn("must use https://", result.stdout)


if __name__ == "__main__":
    unittest.main()
