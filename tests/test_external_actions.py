import json
import os
import subprocess
import sys
import tempfile
import unittest

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPDATE_SCRIPT = os.path.join(REPOSITORY_ROOT, "update.py")


class ExternalActionsValidationTest(unittest.TestCase):
    def run_validator(self, external_actions):
        asset = {
            "name": "Test asset",
            "author_id": "test-author",
            "external_actions": external_actions,
            "images": {"thumb": "https://example.com/test.webp"},
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

    def test_accepts_buy_through_github_sponsors(self):
        result = self.run_validator(
            [
                {
                    "type": "buy",
                    "label": "Purchase commercial license",
                    "url": "https://github.com/sponsors/creator?frequency=one-time",
                }
            ]
        )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_accepts_supported_action_types(self):
        for action_type in ("support", "buy", "donate", "sponsor", "external"):
            with self.subTest(action_type=action_type):
                result = self.run_validator(
                    [
                        {
                            "type": action_type,
                            "label": "Creator action",
                            "url": "https://ko-fi.com/creator",
                        }
                    ]
                )

                self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_accepts_support_through_allowlisted_platform(self):
        result = self.run_validator(
            [
                {
                    "type": "support",
                    "label": "Support on Ko-fi",
                    "url": "https://ko-fi.com/creator",
                }
            ]
        )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_rejects_non_string_values_without_traceback(self):
        result = self.run_validator(
            [
                {
                    "type": 123,
                    "label": ["Purchase"],
                    "url": {"host": "github.com"},
                }
            ]
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("type must be a string", result.stdout)
        self.assertIn("label must be a string", result.stdout)
        self.assertIn("URL must be a string", result.stdout)
        self.assertNotIn("Traceback", result.stdout + result.stderr)

    def test_rejects_general_github_and_unallowlisted_links(self):
        for url in (
            "https://github.com/creator/project",
            "https://pages.github.com/sponsors/creator",
            "https://example.com/checkout",
        ):
            with self.subTest(url=url):
                result = self.run_validator(
                    [
                        {
                            "type": "buy",
                            "label": "Purchase asset",
                            "url": url,
                        }
                    ]
                )

                self.assertNotEqual(0, result.returncode)
                self.assertIn("not an allowed creator action", result.stdout)

    def test_rejects_unsafe_url_characters(self):
        result = self.run_validator(
            [
                {
                    "type": "buy",
                    "label": "Purchase asset",
                    "url": 'https://github.com/sponsors/creator" onclick="alert(1)',
                }
            ]
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("URL contains unsafe characters", result.stdout)


if __name__ == "__main__":
    unittest.main()
