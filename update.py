#!/usr/bin/env python

import os
import sys
import stat
import shutil
import json
import fnmatch
import requests
from urllib.parse import urlparse
import subprocess
import time
import datetime
import re
import base64
from argparse import ArgumentParser

def call(args, retries = 3, failonerror = True):
    print(args)

    while True:
        process = subprocess.Popen(args, stdout = subprocess.PIPE, stderr = subprocess.STDOUT, shell = True)

        output = ''
        while True:
            line = process.stdout.readline().decode()
            if line != '':
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
        os.chmod(filename, stat.S_IWUSR | stat.S_IWGRP | stat.S_IRUSR | stat.S_IRGRP)
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
            fullname = os.path.join(root, filename)
            if fnmatch.fnmatch(filename, file_pattern):
                matches.append(os.path.join(root, filename))
    return matches


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
            project_url = asset["project_url"]
            date = call("git log --diff-filter=A --follow --format=%aD -1 -- {}".format(filename))
            date = re.sub(r'[+-].*', "", date).rstrip()
            # "Fri, 30 Aug 2019 13:11:58 +0200"
            # https://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior
            timestamp = time.mktime(datetime.datetime.strptime(date, "%a, %d %b %Y %H:%M:%S").timetuple())
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
            project_url = asset["project_url"]
            if "github.com" in project_url:
                repo = urlparse(project_url).path[1:]
                url = "https://api.github.com/repos/%s" % (repo)
                response = github_request(url, githubtoken)
                if response:
                    stars = response.get("stargazers_count")
                    print("...%d" % (stars))
                    asset["stars"] = stars
                    write_as_json(filename, asset)
            else:
                print("...not a GitHub repository!")


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
    call("git push 'https://%s@github.com/defold/asset-portal.git' HEAD:master" % (githubtoken))


parser = ArgumentParser()
parser.add_argument('commands', nargs="+", help='Commands (starcount, releases, header, dates, sanitize, library, commit, help)')
parser.add_argument("--githubtoken", dest="githubtoken", help="Authentication token for GitHub API and ")
parser.add_argument("--asset", dest="asset", help="Asset id (JSON file name without .json) to limit release update")
parser.add_argument("--limit", dest="limit", type=int, help="Limit number of releases to fetch (default depends on command)")
args = parser.parse_args()

help = """
COMMANDS:
starcount = Add GitHub star count to all assets that have a GitHub project (requires --githubtoken)
releases = Update releases array (zip, tag, message[, min_defold_version, published_at]) and release_tags (version, published_at, zip). Use --asset=<id> to limit to one asset. Use --limit=N to cap result (default 50; set 1 to fetch only the latest).
header = Update or initialize header.json with timestamps for changed asset JSON files (or initialize all if missing)
dates = Add creation date to all assets
sanitize = Re-save all asset JSON using UTF-8 (no surrogate escapes) to avoid YAML parser issues
library = Determine if assets are Defold libraries (adds isDefoldLibrary flag; requires --githubtoken)
commit = Commit changed files (requires --githubtoken)
help = Show this help
"""

def update_github_releases_and_tags(githubtoken, asset_id=None, include_prerelease=False, per_page=100, release_limit=50):
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
        if "github.com" not in project_url:
            print("...not a GitHub repository!")
            continue

        # Normalize to owner/repo in case of extra path segments
        path = urlparse(project_url).path.strip("/")
        parts = path.split("/")
        if len(parts) < 2:
            print("...could not parse owner/repo from URL!")
            continue
        repo = "/".join(parts[:2])

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
                published_at = (commit_data.get("committer") or {}).get("date") or \
                               (commit_data.get("author") or {}).get("date") or ""
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
                "published_at": (rel.get("published_at") or rel.get("created_at") or "")
            }
            if min_defold:
                item["min_defold_version"] = min_defold
            new_items.append(item)

        if prev_latest_tag and previous_releases:
            # Keep tail after the first occurrence of prev_latest_tag, avoiding duplicates
            try:
                idx = next(i for i, r in enumerate(previous_releases) if r.get("tag") == prev_latest_tag)
            except StopIteration:
                idx = None

            existing_tags = set(item.get("tag") for item in new_items)
            if idx is not None:
                tail = [r for r in previous_releases[idx+1:] if r.get("tag") not in existing_tags]
            else:
                tail = [r for r in previous_releases if r.get("tag") not in existing_tags]

            # Cap to release_limit
            releases_out = (new_items + tail)[:release_limit]
        else:
            releases_out = new_items[:release_limit]

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
                "published_at": rel.get("published_at", "")
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
                published_at = meta.get("published_at") or fetch_commit_published_at(tag.get("commit", {}).get("url"), commit_cache)
                if meta.get("zip"):
                    zip_url = meta.get("zip")
                tags_entries.append({
                    "version": version,
                    "published_at": published_at or "",
                    "zip": zip_url or ""
                })
                if len(tags_entries) >= release_limit:
                    break
        else:
            print("...no tags or unexpected response")

        if tags_entries:
            print("...assembled %d tags" % len(tags_entries))
            asset["release_tags"] = tags_entries

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
            in_library = (section == "library")
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
            print("%s already has isDefoldLibrary flag (%s)" % (filename, asset.get("isDefoldLibrary")))
            continue

        project_url = asset.get("project_url", "")
        if "github.com" not in project_url:
            print("%s is not a GitHub project -> not a Defold library" % filename)
            asset["isDefoldLibrary"] = False
            write_as_json(filename, asset)
            continue

        path = urlparse(project_url).path.strip("/")
        parts = path.split("/")
        if len(parts) < 2:
            print("...could not parse owner/repo from %s" % project_url)
            asset["isDefoldLibrary"] = False
            write_as_json(filename, asset)
            continue
        repo = "/".join(parts[:2])

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
        changed.update([l for l in out.splitlines() if l.strip()])
        out = call("git diff --name-only --cached -- assets/*.json", failonerror=False)
        changed.update([l for l in out.splitlines() if l.strip()])
        out = call("git ls-files --others --exclude-standard assets/*.json", failonerror=False)
        changed.update([l for l in out.splitlines() if l.strip()])

        changed = [c for c in changed if c.endswith('.json')]

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
        update_github_releases_and_tags(args.githubtoken, asset_id=args.asset, release_limit=limit)
    elif command == "header":
        update_header_json()
    elif command == "dates":
        add_creation_date_to_assets()
    elif command == "library":
        update_is_defold_library_flags(args.githubtoken, asset_id=args.asset)
    elif command == "commit":
        commit_changes(args.githubtoken)
    else:
        print("Unknown command {}".format(command))
