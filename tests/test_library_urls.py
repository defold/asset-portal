import json
import os
import subprocess
import sys
import tempfile
import unittest

REPOSITORY_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPDATE_SCRIPT = os.path.join(REPOSITORY_ROOT, "update.py")


class LibraryUrlUpdateTest(unittest.TestCase):
    def update_asset(self, asset):
        with tempfile.TemporaryDirectory() as directory:
            assets_directory = os.path.join(directory, "assets")
            os.mkdir(assets_directory)
            asset_path = os.path.join(assets_directory, "test.json")
            with open(asset_path, "w", encoding="utf-8") as asset_file:
                json.dump(asset, asset_file)

            result = subprocess.run(
                [sys.executable, UPDATE_SCRIPT, "libraryurls", "--asset=test"],
                cwd=directory,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            with open(asset_path, "r", encoding="utf-8") as asset_file:
                return json.load(asset_file)

    def base_asset(self, **overrides):
        asset = {
            "isDefoldLibrary": True,
            "project_url": "https://github.com/example/library",
            "library_url": "https://github.com/example/library/archive/refs/tags/1.0.0.zip",
            "releases": [
                {
                    "tag": "2.0.0",
                    "zip": "https://github.com/example/library/releases/download/2.0.0/library.zip",
                }
            ],
            "release_tags": [{"version": "2.0.0"}],
        }
        asset.update(overrides)
        return asset

    def test_updates_tag_archive_to_latest_release_archive(self):
        for library_url in (
            "https://github.com/example/library/archive/refs/tags/1.0.0.zip",
            "https://github.com/example/library/archive/1.0.0.zip",
        ):
            with self.subTest(library_url=library_url):
                asset = self.update_asset(self.base_asset(library_url=library_url))
                self.assertEqual(
                    "https://github.com/example/library/archive/refs/tags/2.0.0.zip",
                    asset["library_url"],
                )

    def test_preserves_release_download_url_style(self):
        asset = self.update_asset(
            self.base_asset(
                library_url="https://github.com/example/library/releases/download/1.0.0/library.zip"
            )
        )

        self.assertEqual(
            "https://github.com/example/library/releases/download/2.0.0/library.zip",
            asset["library_url"],
        )

    def test_populates_missing_url_from_latest_tag_when_releases_are_absent(self):
        asset = self.update_asset(
            self.base_asset(
                library_url="",
                releases=[],
                release_tags=[{"version": "3.0.0"}],
            )
        )

        self.assertEqual(
            "https://github.com/example/library/archive/refs/tags/3.0.0.zip",
            asset["library_url"],
        )

    def test_uses_newest_timestamp_across_releases_and_tags(self):
        asset = self.update_asset(
            self.base_asset(
                library_url="https://github.com/example/library/archive/refs/tags/2.0.0.zip",
                releases=[{"tag": "2.0.0", "published_at": "2025-01-01T00:00:00Z"}],
                release_tags=[
                    {"version": "1.0.0", "published_at": "2017-01-01T00:00:00Z"},
                    {"version": "3.0.0", "published_at": "2026-01-01T00:00:00Z"},
                ],
            )
        )

        self.assertEqual(
            "https://github.com/example/library/archive/refs/tags/3.0.0.zip",
            asset["library_url"],
        )
        self.assertEqual(
            ["3.0.0", "1.0.0"],
            [entry["version"] for entry in asset["release_tags"]],
        )

    def test_sorts_release_metadata_newest_first(self):
        asset = self.update_asset(
            self.base_asset(
                releases=[
                    {"tag": "1.0.0", "published_at": "2024-01-01T00:00:00Z"},
                    {"tag": "2.0.0", "published_at": "2025-01-01T00:00:00Z"},
                ],
                release_tags=[
                    {"version": "1.0.0", "published_at": "2024-01-01T00:00:00Z"},
                    {"version": "2.0.0", "published_at": "2025-01-01T00:00:00Z"},
                ],
            )
        )

        self.assertEqual(
            ["2.0.0", "1.0.0"],
            [entry["tag"] for entry in asset["releases"]],
        )
        self.assertEqual(
            ["2.0.0", "1.0.0"],
            [entry["version"] for entry in asset["release_tags"]],
        )

    def test_leaves_branch_and_custom_urls_unchanged(self):
        for library_url in (
            "https://github.com/example/library/archive/refs/heads/main.zip",
            "https://github.com/example/library/archive/refs/heads/v3.x.zip",
            "https://github.com/example/library/archive/master.zip",
            "https://github.com/example/library",
            "https://downloads.example.com/library.zip",
        ):
            with self.subTest(library_url=library_url):
                asset = self.update_asset(self.base_asset(library_url=library_url))
                self.assertEqual(library_url, asset["library_url"])

    def test_honors_tag_prefix_for_multi_product_repository(self):
        asset = self.update_asset(
            self.base_asset(
                library_release_tag_prefix="runtime.",
                library_url="https://github.com/example/library/archive/refs/tags/runtime.1.zip",
                releases=[{"tag": "editor.10", "zip": "editor.zip"}],
                release_tags=[
                    {"version": "editor.10"},
                    {"version": "runtime.3"},
                ],
            )
        )

        self.assertEqual(
            "https://github.com/example/library/archive/refs/tags/runtime.3.zip",
            asset["library_url"],
        )

    def test_honors_opt_out_and_non_library_entries(self):
        for overrides in (
            {"library_url_auto_update": False},
            {"isDefoldLibrary": False},
        ):
            with self.subTest(overrides=overrides):
                original_url = self.base_asset()["library_url"]
                asset = self.update_asset(self.base_asset(**overrides))
                self.assertEqual(original_url, asset["library_url"])


if __name__ == "__main__":
    unittest.main()
