#!/usr/bin/env python

import base64
import datetime
import fnmatch
import json
import os
import re
import stat
import subprocess
import sys
import time
from argparse import ArgumentParser
from urllib.parse import urlparse

import requests


def call(args, retries=3, failonerror=True):
    print(args)

    while True:
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True
        )

        output = ""
        while True:
            line = process.stdout.readline().decode()
            if line != "":
                output += line
                print(line.rstrip())
            else:
                break

        if process.wait() == 0 or not failonerror:
            return output

        if retries == 0 and failonerror:
            exit(1)

        print("An error occurred - will retry soon")
        retries = retries - 1
        time.sleep(5)


def github_request(url, token):
    try:
        response = requests.get(url, headers={"Authorization": "token %s" % (token)})
        response.raise_for_status()
        return response.json()
    except Exception as err:
        print("github_request", err)


def read_as_json(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            decoded = json.load(f)
            return decoded
    except Exception as err:
        print("read_as_json", err)
    return None


def write_as_json(filename, data):
    try:
        os.chmod(filename, stat.S_IWUSR | stat.S_IWGRP | stat.S_IRUSR | stat.S_IRGRP)
        with open(filename, "w", encoding="utf-8") as f:
            # Use UTF-8 output to avoid JSON \uDXXX surrogate escapes that
            # can trip YAML/psych when the site ingests these files.
            json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=False)
    except Exception as err:
        print("write_as_json", err)
    return None


def find_files(root_dir, file_pattern):
    matches = []
    for root, dirnames, filenames in os.walk(root_dir):
        for filename in filenames:
            if fnmatch.fnmatch(filename, file_pattern):
                matches.append(os.path.join(root, filename))
    return matches


EXTERNAL_ACTION_TYPES = set(["support", "buy", "donate", "sponsor", "external"])
EXTERNAL_ACTION_FIELDS = set(["type", "label", "url"])
EXTERNAL_ACTION_HOSTS = [
    "itch.io",
    "patreon.com",
    "ko-fi.com",
    "paypal.com",
    "paypal.me",
    "buy.stripe.com",
    "checkout.stripe.com",
    "gumroad.com",
    "github.com",
    "opencollective.com",
]
EXTERNAL_ACTION_BLOCKED_LABELS = [
    "official defold purchase",
    "official defold checkout",
    "defold checkout",
]
ASSET_IMAGE_EXTENSIONS = set([".webp", ".png", ".jpg", ".jpeg"])
AUTHOR_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_asset_authors():
    print("Validating asset authors")
    errors = []
    for filename in sorted(find_files("assets", "*.json")):
        asset_id = os.path.basename(filename).replace(".json", "")
        asset = read_as_json(filename)
        if not isinstance(asset, dict):
            errors.append("{}: asset JSON must be an object".format(asset_id))
            continue
        if "author" in asset:
            errors.append("{}: legacy author field is not supported".format(asset_id))
        author_id = asset.get("author_id")
        if not isinstance(author_id, str) or not AUTHOR_ID_RE.fullmatch(author_id):
            errors.append(
                "{}: author_id must use lowercase ASCII kebab-case".format(asset_id)
            )

    if errors:
        print("Invalid asset authors:")
        for error in errors[:50]:
            print(" - {}".format(error))
        if len(errors) > 50:
            print("... and {} more".format(len(errors) - 50))
        sys.exit(1)

    print("...ok!")


def external_action_host_allowed(host):
    host = (host or "").lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    for allowed_host in EXTERNAL_ACTION_HOSTS:
        if host == allowed_host:
            return True
        if allowed_host != "github.com" and host.endswith("." + allowed_host):
            return True
    return False


def external_action_url_allowed(parsed_url):
    host = (parsed_url.hostname or "").lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    if not external_action_host_allowed(host):
        return False

    # GitHub links are allowed specifically for GitHub Sponsors. General project
    # links already have dedicated project_url and website_url asset fields.
    if host == "github.com":
        path_parts = parsed_url.path.strip("/").split("/")
        return (
            len(path_parts) >= 2
            and path_parts[0].lower() == "sponsors"
            and bool(path_parts[1])
        )

    return True


def validate_external_actions():
    print("Validating external asset actions")
    errors = []
    for filename in sorted(find_files("assets", "*.json")):
        asset_id = os.path.basename(filename).replace(".json", "")
        asset = read_as_json(filename)
        if asset is None:
            errors.append("{}: could not read asset JSON".format(asset_id))
            continue
        if not isinstance(asset, dict):
            errors.append("{}: asset JSON must be an object".format(asset_id))
            continue

        if "external_actions" not in asset:
            continue
        external_actions = asset["external_actions"]
        if not isinstance(external_actions, list):
            errors.append("{}: external_actions must be an array".format(asset_id))
            continue
        if len(external_actions) > 3:
            errors.append(
                "{}: external_actions can contain at most 3 entries".format(asset_id)
            )

        for index, action in enumerate(external_actions):
            label = "{} external_actions[{}]".format(asset_id, index)
            if not isinstance(action, dict):
                errors.append("{} must be an object".format(label))
                continue

            unexpected_fields = set(action.keys()) - EXTERNAL_ACTION_FIELDS
            if unexpected_fields:
                errors.append(
                    "{} has unsupported fields: {}".format(
                        label, ", ".join(sorted(unexpected_fields))
                    )
                )

            action_type = action.get("type")
            if not isinstance(action_type, str):
                errors.append("{} type must be a string".format(label))
            elif action_type not in EXTERNAL_ACTION_TYPES:
                errors.append(
                    "{} has unsupported type: {}".format(label, action.get("type"))
                )

            action_label = action.get("label")
            if not isinstance(action_label, str):
                errors.append("{} label must be a string".format(label))
            elif not action_label.strip():
                errors.append("{} must have a label".format(label))
            elif action_label != action_label.strip():
                errors.append(
                    "{} label must not have leading or trailing whitespace".format(
                        label
                    )
                )
            elif len(action_label) > 50:
                errors.append("{} label must be 50 characters or fewer".format(label))
            elif any(ord(char) < 32 or ord(char) == 127 for char in action_label):
                errors.append(
                    "{} label must not contain control characters".format(label)
                )
            elif action_label.lower() in EXTERNAL_ACTION_BLOCKED_LABELS:
                errors.append("{} label is misleading: {}".format(label, action_label))

            action_url = action.get("url")
            if not isinstance(action_url, str):
                errors.append("{} URL must be a string".format(label))
                continue
            if not action_url.strip():
                errors.append("{} must have a URL".format(label))
                continue
            if action_url != action_url.strip():
                errors.append(
                    "{} URL must not have leading or trailing whitespace".format(label)
                )
            if len(action_url) > 2048:
                errors.append("{} URL must be 2048 characters or fewer".format(label))
            if any(
                char.isspace() or ord(char) < 32 or ord(char) == 127
                for char in action_url
            ):
                errors.append(
                    "{} URL must not contain whitespace or control characters".format(
                        label
                    )
                )
            if any(char in action_url for char in ['"', "<", ">", "\\"]):
                errors.append("{} URL contains unsafe characters".format(label))

            try:
                parsed_url = urlparse(action_url)
                parsed_host = parsed_url.hostname
                parsed_port = parsed_url.port
            except ValueError:
                errors.append("{} URL is malformed".format(label))
                continue

            if parsed_url.scheme != "https":
                errors.append("{} URL must use https://".format(label))
            elif not parsed_host:
                errors.append("{} URL must include a host".format(label))
            elif parsed_url.username or parsed_url.password:
                errors.append("{} URL must not contain credentials".format(label))
            elif parsed_port not in (None, 443):
                errors.append("{} URL must not use a custom port".format(label))
            elif not external_action_url_allowed(parsed_url):
                errors.append(
                    "{} URL is not an allowed creator action: {}".format(
                        label, parsed_host
                    )
                )

    if errors:
        print("Invalid external asset actions:")
        for error in errors[:50]:
            print(" - {}".format(error))
        if len(errors) > 50:
            print("... and {} more".format(len(errors) - 50))
        sys.exit(1)

    print("...ok!")


def validate_asset_images():
    print("Validating asset images")
    errors = []
    for filename in sorted(find_files("assets", "*.json")):
        asset_id = os.path.basename(filename).replace(".json", "")
        asset = read_as_json(filename)
        if asset is None:
            errors.append("{}: could not read asset JSON".format(asset_id))
            continue
        if not isinstance(asset, dict):
            errors.append("{}: asset JSON must be an object".format(asset_id))
            continue

        images = asset.get("images")
        if not isinstance(images, dict):
            errors.append("{}: images must be an object".format(asset_id))
            continue

        thumbnail = images.get("thumb")
        if not isinstance(thumbnail, str):
            errors.append("{}: images.thumb must be a string".format(asset_id))
            continue
        if not thumbnail.strip():
            errors.append("{}: images.thumb is required".format(asset_id))
            continue
        if thumbnail != thumbnail.strip():
            errors.append(
                "{}: images.thumb must not have leading or trailing whitespace".format(
                    asset_id
                )
            )
            continue

        try:
            parsed_thumbnail = urlparse(thumbnail)
            parsed_host = parsed_thumbnail.hostname
            parsed_port = parsed_thumbnail.port
        except ValueError:
            errors.append("{}: images.thumb URL is malformed".format(asset_id))
            continue

        if parsed_thumbnail.scheme or parsed_thumbnail.netloc:
            if parsed_thumbnail.scheme != "https":
                errors.append(
                    "{}: remote images.thumb must use https://".format(asset_id)
                )
                continue
            if not parsed_host:
                errors.append(
                    "{}: remote images.thumb must include a host".format(asset_id)
                )
                continue
            if parsed_thumbnail.username or parsed_thumbnail.password:
                errors.append(
                    "{}: remote images.thumb must not contain credentials".format(
                        asset_id
                    )
                )
                continue
            if parsed_port not in (None, 443):
                errors.append(
                    "{}: remote images.thumb must not use a custom port".format(
                        asset_id
                    )
                )
                continue
            image_path = parsed_thumbnail.path
        else:
            if os.path.basename(thumbnail) != thumbnail:
                errors.append(
                    "{}: local images.thumb must be a filename in assets/images/".format(
                        asset_id
                    )
                )
                continue
            image_path = thumbnail

        extension = os.path.splitext(image_path)[1].lower()
        if extension not in ASSET_IMAGE_EXTENSIONS:
            errors.append(
                "{}: images.thumb must use WebP, PNG, JPG, or JPEG".format(asset_id)
            )
            continue

        if not parsed_thumbnail.scheme and not parsed_thumbnail.netloc:
            local_path = os.path.join("assets", "images", thumbnail)
            if not os.path.isfile(local_path):
                errors.append(
                    "{}: local thumbnail does not exist: {}".format(
                        asset_id, local_path
                    )
                )

    if errors:
        print("Invalid asset images:")
        for error in errors[:50]:
            print(" - {}".format(error))
        if len(errors) > 50:
            print("... and {} more".format(len(errors) - 50))
        sys.exit(1)

    print("...ok!")


def add_creation_date_to_assets():
    print("Adding creation date to assets")
    for filename in find_files("assets", "*.json"):
        print("Checking creation date for %s" % filename)
        asset = read_as_json(filename)
        if not asset:
            print("...error!")
        elif asset.get("timestamp"):
            print("...ok!")
        else:
            date = call(
                "git log --diff-filter=A --follow --format=%aD -1 -- {}".format(
                    filename
                )
            )
            date = re.sub(r"[+-].*", "", date).rstrip()
            # "Fri, 30 Aug 2019 13:11:58 +0200"
            # https://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior
            timestamp = time.mktime(
                datetime.datetime.strptime(date, "%a, %d %b %Y %H:%M:%S").timetuple()
            )
            print("...%f" % timestamp)
            asset["timestamp"] = timestamp
            write_as_json(filename, asset)


def update_github_star_count_for_assets(githubtoken):
    if githubtoken is None:
        print("No GitHub token specified")
        sys.exit(1)

    print("Update star count for assets")
    for filename in find_files("assets", "*.json"):
        print("Getting star count for %s" % filename)
        asset = read_as_json(filename)
        if not asset:
            print("...error!")
        else:
            project_url = asset.get("project_url", "")
            repo = github_repo_from_url(project_url)
            if repo:
                url = "https://api.github.com/repos/%s" % (repo)
                response = github_request(url, githubtoken)
                if response:
                    stars = response.get("stargazers_count")
                    print("...%d" % (stars))
                    asset["stars"] = stars
                    write_as_json(filename, asset)
            else:
                print("...not a GitHub repository!")


def github_repo_from_url(project_url):
    parsed = urlparse(project_url or "")
    if parsed.netloc.lower() not in ("github.com", "www.github.com"):
        return None

    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2:
        return None

    owner = parts[0]
    repository = parts[1]
    if repository.endswith(".git"):
        repository = repository[:-4]
    if not owner or not repository:
        return None
    return "%s/%s" % (owner, repository)


def sort_release_entries(entries):
    """Return release metadata ordered from newest to oldest.

    GitHub's tags endpoint does not guarantee that the first tag is the most
    recently published one. All generated release metadata includes an ISO 8601
    ``published_at`` value, so make that ordering explicit before consumers use
    the first entry as the latest release.
    """
    return sorted(
        entries or [],
        key=lambda entry: entry.get("published_at") or "",
        reverse=True,
    )


def normalize_release_metadata(asset):
    changed = False
    for field in ("releases", "release_tags"):
        entries = asset.get(field)
        if not isinstance(entries, list):
            continue
        sorted_entries = sort_release_entries(entries)
        if entries != sorted_entries:
            asset[field] = sorted_entries
            changed = True
    return changed


def classify_github_library_url(library_url, repo):
    """Return the supported GitHub library URL kind.

    Branch archives already float with their branch and should not be rewritten.
    Tag archives and release downloads can safely follow release metadata. Unknown
    URL shapes are treated as custom and preserved.
    """
    if not library_url:
        return "missing"

    parsed = urlparse(library_url)
    if parsed.netloc.lower() not in ("github.com", "www.github.com"):
        return "custom"

    parts = parsed.path.strip("/").split("/")
    if len(parts) < 3 or "/".join(parts[:2]).lower() != repo.lower():
        return "custom"

    suffix = "/".join(parts[2:])
    if re.fullmatch(r"archive/refs/heads/.+\.zip", suffix, re.IGNORECASE):
        return "branch"
    if re.fullmatch(r"archive/(?:main|master)\.zip", suffix, re.IGNORECASE):
        return "branch"
    if re.fullmatch(r"archive/refs/tags/.+\.zip", suffix, re.IGNORECASE):
        return "tag"
    if re.fullmatch(r"archive/(?!refs/).+\.zip", suffix, re.IGNORECASE):
        return "tag"
    if re.fullmatch(r"releases/download/[^/]+/.+\.zip", suffix, re.IGNORECASE):
        return "release"
    return "custom"


def latest_library_version(asset):
    tag_prefix = asset.get("library_release_tag_prefix")
    if not isinstance(tag_prefix, str):
        tag_prefix = ""

    candidates = []
    for field, version_field in (("releases", "tag"), ("release_tags", "version")):
        for entry in asset.get(field) or []:
            version = entry.get(version_field)
            if not version or (tag_prefix and not version.startswith(tag_prefix)):
                continue
            candidates.append(
                {
                    "version": version,
                    "published_at": entry.get("published_at") or "",
                }
            )

    if not candidates:
        return None
    return sort_release_entries(candidates)[0]["version"]


def sync_library_url(asset, repo):
    """Update a Defold library URL from its generated release metadata."""
    if asset.get("isDefoldLibrary") is not True:
        return False
    if asset.get("library_url_auto_update") is False:
        return False

    url_kind = classify_github_library_url(asset.get("library_url", ""), repo)
    if url_kind in ("branch", "custom"):
        return False

    version = latest_library_version(asset)
    if not version:
        return False

    library_url = "https://github.com/%s/archive/refs/tags/%s.zip" % (repo, version)
    if url_kind == "release":
        matching_release = next(
            (
                release
                for release in asset.get("releases") or []
                if release.get("tag") == version and release.get("zip")
            ),
            None,
        )
        if matching_release:
            library_url = matching_release["zip"]

    if asset.get("library_url") == library_url:
        return False

    asset["library_url"] = library_url
    return True


def update_library_urls_from_release_metadata(asset_id=None):
    if asset_id:
        filename = os.path.join("assets", asset_id + ".json")
        if not os.path.exists(filename):
            print("Asset JSON not found: %s" % filename)
            sys.exit(1)
        files = [filename]
    else:
        files = find_files("assets", "*.json")

    updated = 0
    for filename in files:
        asset = read_as_json(filename)
        if not asset:
            print("...error reading %s" % filename)
            continue

        repo = github_repo_from_url(asset.get("project_url", ""))
        if not repo:
            continue
        metadata_updated = normalize_release_metadata(asset)
        library_url_updated = sync_library_url(asset, repo)
        if metadata_updated or library_url_updated:
            if metadata_updated:
                print("Sorted release metadata for %s" % filename)
            if library_url_updated:
                print("Updated library URL for %s" % filename)
            write_as_json(filename, asset)
            updated += 1

    print("Updated %d asset metadata file(s)" % updated)


def commit_changes(githubtoken):
    if githubtoken is None:
        print("You must specific a GitHub token")
        sys.exit(1)

    print("Committing changes")
    call("git config --global user.name 'services@defold.se'")
    call("git config --global user.email 'services@defold.se'")
    call("git add -A")
    # only commit if the diff isn't empty, ie there is a change
    # https://stackoverflow.com/a/8123841/1266551
    call("git diff-index --quiet HEAD || git commit -m 'Site changes [skip-ci]'")
    call(
        "git push 'https://%s@github.com/defold/asset-portal.git' HEAD:master"
        % (githubtoken)
    )


parser = ArgumentParser()
parser.add_argument(
    "commands",
    nargs="+",
    help=(
        "Commands (starcount, releases, libraryurls, header, dates, sanitize, "
        "library, validate, commit, help)"
    ),
)
parser.add_argument(
    "--githubtoken", dest="githubtoken", help="Authentication token for GitHub API and "
)
parser.add_argument(
    "--asset",
    dest="asset",
    help="Asset id (JSON file name without .json) to limit asset-specific updates",
)
parser.add_argument(
    "--limit",
    dest="limit",
    type=int,
    help="Limit number of releases to fetch (default depends on command)",
)
args = parser.parse_args()

help = """
COMMANDS:
starcount = Add GitHub star count to all assets that have a GitHub project (requires --githubtoken)
releases = Update releases array (zip, tag, message[, min_defold_version, published_at])
           and release_tags (version, published_at, zip). Use --asset=<id> to limit to
           one asset. It also advances eligible library_url values to the latest release.
           Use --limit=N to cap result (default 50; set 1 for only the latest).
libraryurls = Update eligible library_url values from existing release metadata. Use
              --asset=<id> to limit to one asset.
header = Update or initialize header.json with timestamps for changed asset JSON files (or initialize all if missing)
dates = Add creation date to all assets
sanitize = Re-save all asset JSON using UTF-8 (no surrogate escapes) to avoid YAML parser issues
library = Determine if assets are Defold libraries (adds isDefoldLibrary flag; requires --githubtoken)
validate = Validate asset metadata that is not derived from external APIs
commit = Commit changed files (requires --githubtoken)
help = Show this help
"""


def update_github_releases_and_tags(
    githubtoken, asset_id=None, include_prerelease=False, per_page=100, release_limit=50
):
    """Update GitHub releases/tags for all assets or a single asset.

    When asset_id is provided, only that asset JSON is processed.
    Otherwise, all JSON files under assets/ are updated.
    """
    if githubtoken is None:
        print("No GitHub token specified")
        sys.exit(1)

    # Build file list
    if asset_id:
        filename = os.path.join("assets", asset_id + ".json")
        if not os.path.exists(filename):
            print("Asset JSON not found: %s" % filename)
            sys.exit(1)
        files = [filename]
        print("Update releases for asset %s" % asset_id)
    else:
        files = find_files("assets", "*.json")
        print("Update releases for assets")

    for filename in files:
        if not asset_id:
            print("Getting latest release for %s" % filename)

        asset = read_as_json(filename)
        if not asset:
            print("...error!")
            continue

        project_url = asset.get("project_url", "")
        repo = github_repo_from_url(project_url)
        if not repo:
            print("...not a GitHub repository!")
            continue

        normalize_release_metadata(asset)

        def pick_zip_url(rel):
            assets = rel.get("assets") or []
            for a in assets:
                name = (a.get("name") or "").lower()
                ctype = (a.get("content_type") or "").lower()
                if name.endswith(".zip") or "zip" in ctype:
                    return a.get("browser_download_url")
            # Prefer canonical GitHub archive URL for the tag
            tag = rel.get("tag_name")
            if tag:
                return f"https://github.com/{repo}/archive/refs/tags/{tag}.zip"
            # Last resort: API zipball URL
            return rel.get("zipball_url")

        def sanitize_text(text):
            if text is None:
                return ""
            if not isinstance(text, str):
                text = str(text)
            # Normalize newlines and strip unsafe control characters
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)
            return text

        def parse_message_info(text):
            # returns (clean_message, min_defold_version or None)
            txt = sanitize_text(text)
            if not txt:
                return "", None
            lines = txt.split("\n")
            out_lines = []
            min_defold = None
            badge_re = re.compile(r"https?://img\.shields\.io/badge/Defold-([^\s/]+)")
            for line in lines:
                if "https://img.shields.io/badge/Defold-" in line:
                    m = badge_re.search(line)
                    if m and not min_defold:
                        # Trim any trailing characters such as -blue
                        val = m.group(1)
                        if "-" in val:
                            val = val.split("-")[0]
                        val = val.strip()
                        min_defold = val
                    # drop this line
                    continue
                out_lines.append(line)
            return "\n".join(out_lines).strip(), min_defold

        def fetch_commit_published_at(commit_url, cache):
            if not commit_url:
                return ""
            if commit_url in cache:
                return cache[commit_url]
            published_at = ""
            data = github_request(commit_url, githubtoken)
            if isinstance(data, dict):
                commit_data = data.get("commit") or {}
                published_at = (
                    (commit_data.get("committer") or {}).get("date")
                    or (commit_data.get("author") or {}).get("date")
                    or ""
                )
            cache[commit_url] = published_at
            return published_at

        # Determine previous latest tag if any
        previous_releases = asset.get("releases") or []
        prev_latest_tag = previous_releases[0].get("tag") if previous_releases else None

        # Single request; process up to release_limit items
        url = "https://api.github.com/repos/%s/releases?per_page=%d" % (repo, per_page)
        response = github_request(url, githubtoken)
        if not isinstance(response, list):
            print("...no releases or unexpected response")
            continue

        collected_rels = []
        for rel in response:
            if rel.get("draft"):
                continue
            if not include_prerelease and rel.get("prerelease"):
                continue
            collected_rels.append(rel)
            if prev_latest_tag and rel.get("tag_name") == prev_latest_tag:
                break
            if len(collected_rels) >= release_limit:
                break

        # Map collected to output format
        new_items = []
        for rel in collected_rels:
            message, min_defold = parse_message_info(rel.get("body"))
            item = {
                "zip": pick_zip_url(rel) or "",
                "tag": rel.get("tag_name") or "",
                "message": message,
                "published_at": (
                    rel.get("published_at") or rel.get("created_at") or ""
                ),
            }
            if min_defold:
                item["min_defold_version"] = min_defold
            new_items.append(item)

        if prev_latest_tag and previous_releases:
            # Keep tail after the first occurrence of prev_latest_tag, avoiding duplicates
            try:
                idx = next(
                    i
                    for i, r in enumerate(previous_releases)
                    if r.get("tag") == prev_latest_tag
                )
            except StopIteration:
                idx = None

            existing_tags = set(item.get("tag") for item in new_items)
            if idx is not None:
                tail = [
                    r
                    for r in previous_releases[idx + 1 :]
                    if r.get("tag") not in existing_tags
                ]
            else:
                tail = [
                    r for r in previous_releases if r.get("tag") not in existing_tags
                ]

            # Cap to release_limit
            releases_out = sort_release_entries(new_items + tail)[:release_limit]
        else:
            releases_out = sort_release_entries(new_items)[:release_limit]

        if releases_out:
            print("...assembled %d releases (incremental)" % len(releases_out))
            asset["releases"] = releases_out
        else:
            print("...no suitable releases found")

        # Build lookup for release metadata when creating tags
        release_meta_lookup = {}
        for rel in releases_out:
            tag_name = rel.get("tag")
            if not tag_name:
                continue
            release_meta_lookup[tag_name] = {
                "zip": rel.get("zip", ""),
                "published_at": rel.get("published_at", ""),
            }

        # Fetch tags to cover repositories without releases or to supplement releases
        tags_entries = []
        commit_cache = {}
        tags_url = "https://api.github.com/repos/%s/tags?per_page=%d" % (repo, per_page)
        tags_response = github_request(tags_url, githubtoken)
        if isinstance(tags_response, list):
            for tag in tags_response:
                version = tag.get("name") or ""
                if not version:
                    continue
                zip_url = f"https://github.com/{repo}/archive/refs/tags/{version}.zip"
                meta = release_meta_lookup.get(version, {})
                published_at = meta.get("published_at") or fetch_commit_published_at(
                    tag.get("commit", {}).get("url"), commit_cache
                )
                if meta.get("zip"):
                    zip_url = meta.get("zip")
                tags_entries.append(
                    {
                        "version": version,
                        "published_at": published_at or "",
                        "zip": zip_url or "",
                    }
                )

            # A formal GitHub release may be absent from the first page/order of
            # the tags endpoint. Include it explicitly so release_tags remains a
            # complete source for the website's latest-release selector.
            tag_versions = set(entry.get("version") for entry in tags_entries)
            for release in releases_out:
                version = release.get("tag")
                if not version or version in tag_versions:
                    continue
                tags_entries.append(
                    {
                        "version": version,
                        "published_at": release.get("published_at") or "",
                        "zip": release.get("zip") or "",
                    }
                )
                tag_versions.add(version)

            tags_entries = sort_release_entries(tags_entries)[:release_limit]
        else:
            print("...no tags or unexpected response")

        if tags_entries:
            print("...assembled %d tags" % len(tags_entries))
            asset["release_tags"] = tags_entries

        normalize_release_metadata(asset)
        if sync_library_url(asset, repo):
            print("...updated library URL")

        write_as_json(filename, asset)


def fetch_game_project_content(repo, githubtoken):
    url = "https://api.github.com/repos/%s/contents/game.project" % repo
    headers = {}
    if githubtoken:
        headers["Authorization"] = "token %s" % githubtoken
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 404:
            return False, None
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            content = data.get("content")
            encoding = data.get("encoding")
            if content and encoding == "base64":
                try:
                    decoded = base64.b64decode(content).decode("utf-8", errors="ignore")
                except Exception as err:
                    print("decode_game_project", err)
                    return None, None
                return True, decoded
            elif content:
                return True, content
        return None, None
    except Exception as err:
        print("fetch_game_project_content", err)
        return None, None


def parse_is_defold_library(game_project_text):
    if not game_project_text:
        return False
    in_library = False
    for line in game_project_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(";"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1].strip().lower()
            in_library = section == "library"
            continue
        if not in_library:
            continue
        if stripped.lower().startswith("include_dirs"):
            parts = stripped.split("=", 1)
            if len(parts) == 2 and parts[1].strip():
                return True
    return False


def update_is_defold_library_flags(githubtoken, asset_id=None):
    if githubtoken is None:
        print("No GitHub token specified")
        sys.exit(1)

    if asset_id:
        filename = os.path.join("assets", asset_id + ".json")
        if not os.path.exists(filename):
            print("Asset JSON not found: %s" % filename)
            sys.exit(1)
        files = [filename]
        print("Checking Defold library flag for asset %s" % asset_id)
    else:
        files = find_files("assets", "*.json")
        print("Checking Defold library flags for assets")

    for filename in files:
        asset = read_as_json(filename)
        if not asset:
            print("...error reading %s" % filename)
            continue

        if "isDefoldLibrary" in asset:
            print(
                "%s already has isDefoldLibrary flag (%s)"
                % (filename, asset.get("isDefoldLibrary"))
            )
            continue

        project_url = asset.get("project_url", "")
        repo = github_repo_from_url(project_url)
        if not repo:
            print("%s is not a GitHub project -> not a Defold library" % filename)
            asset["isDefoldLibrary"] = False
            write_as_json(filename, asset)
            continue

        exists, content = fetch_game_project_content(repo, githubtoken)
        if exists is None:
            print("...failed to inspect repository %s; skipping" % repo)
            continue
        if not exists:
            print("...no game.project found in %s" % repo)
            asset["isDefoldLibrary"] = False
            write_as_json(filename, asset)
            continue

        is_library = parse_is_defold_library(content)
        asset["isDefoldLibrary"] = is_library
        if is_library:
            print("...%s is a Defold library" % repo)
        else:
            print("...%s is not a Defold library" % repo)
        write_as_json(filename, asset)


def update_header_json():
    header_file = "header.json"
    now = int(time.time())

    # Load existing header map if present
    header_map = {}
    if os.path.exists(header_file):
        try:
            with open(header_file, "r", encoding="utf-8") as f:
                header_map = json.load(f)
        except Exception as err:
            print("Failed to read existing header.json:", err)

    def last_commit_ts(path):
        out = call("git log -1 --format=%ct -- {}".format(path), failonerror=False)
        out = out.strip()
        try:
            return int(out)
        except Exception:
            return now

    def update_entry(relpath):
        fname = os.path.basename(relpath)
        header_map[fname] = now

    def initialize_all():
        print("Initializing header.json for all assets")
        for filename in find_files("assets", "*.json"):
            ts = last_commit_ts(filename)
            fname = os.path.basename(filename)
            header_map[fname] = ts

    if not os.path.exists(header_file):
        initialize_all()
    else:
        # Determine changed asset JSON files (modified, staged, or untracked)
        changed = set()
        out = call("git diff --name-only -- assets/*.json", failonerror=False)
        changed.update([line for line in out.splitlines() if line.strip()])
        out = call("git diff --name-only --cached -- assets/*.json", failonerror=False)
        changed.update([line for line in out.splitlines() if line.strip()])
        out = call(
            "git ls-files --others --exclude-standard assets/*.json", failonerror=False
        )
        changed.update([line for line in out.splitlines() if line.strip()])

        changed = [c for c in changed if c.endswith(".json")]

        if not changed:
            print("No changed asset JSON files detected; header.json unchanged")
        else:
            print("Updating header.json for changed files:")
            for relpath in sorted(changed):
                print(" - {}".format(relpath))
                update_entry(relpath)

    # Ensure file exists before using write_as_json (which chmods)
    if not os.path.exists(header_file):
        open(header_file, "a", encoding="utf-8").close()
    write_as_json(header_file, header_map)


for command in args.commands:
    if command == "help":
        parser.print_help()
        print(help)
        sys.exit(0)
    elif command == "starcount":
        update_github_star_count_for_assets(args.githubtoken)
    elif command == "releases":
        limit = args.limit if args.limit is not None else 50
        update_github_releases_and_tags(
            args.githubtoken, asset_id=args.asset, release_limit=limit
        )
    elif command == "libraryurls":
        update_library_urls_from_release_metadata(asset_id=args.asset)
    elif command == "header":
        update_header_json()
    elif command == "dates":
        add_creation_date_to_assets()
    elif command == "library":
        update_is_defold_library_flags(args.githubtoken, asset_id=args.asset)
    elif command == "validate":
        validate_asset_authors()
        validate_external_actions()
        validate_asset_images()
    elif command == "commit":
        commit_changes(args.githubtoken)
    else:
        print("Unknown command {}".format(command))
