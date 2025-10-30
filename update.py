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
            json.dump(data, f, indent=2, sort_keys=True, ensure_ascii=True)
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
parser.add_argument('commands', nargs="+", help='Commands (starcount, releases, header, dates, commit, help)')
parser.add_argument("--githubtoken", dest="githubtoken", help="Authentication token for GitHub API and ")
parser.add_argument("--asset", dest="asset", help="Asset id (JSON file name without .json) to limit release update")
parser.add_argument("--limit", dest="limit", type=int, help="Limit number of releases to fetch (default depends on command)")
args = parser.parse_args()

help = """
COMMANDS:
starcount = Add GitHub star count to all assets that have a GitHub project (requires --githubtoken)
releases = Add sorted releases array (zip, tag, message[, min_defold_version, published_at]). Use --asset=<id> to limit to one asset. Use --limit=N to cap result (default 50; set 1 to fetch only the latest).
header = Update or initialize header.json with timestamps for changed asset JSON files (or initialize all if missing)
dates = Add creation date to all assets
commit = Commit changed files (requires --githubtoken)
help = Show this help
"""

def update_github_releases_for_assets(githubtoken, include_prerelease=False, per_page=100, release_limit=50):
    if githubtoken is None:
        print("No GitHub token specified")
        sys.exit(1)

    print("Update releases for assets")
    for filename in find_files("assets", "*.json"):
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
                        # If value contains encoded characters, keep as-is; strip trailing punctuation
                        val = val.strip()
                        # Some shields include color suffix via '-' already outside capture
                        min_defold = val
                    # drop this line
                    continue
                out_lines.append(line)
            return "\n".join(out_lines).strip(), min_defold

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
        found_prev = False
        for rel in response:
            if rel.get("draft"):
                continue
            if not include_prerelease and rel.get("prerelease"):
                continue
            collected_rels.append(rel)
            if prev_latest_tag and rel.get("tag_name") == prev_latest_tag:
                found_prev = True
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
            write_as_json(filename, asset)
        else:
            print("...no suitable releases found")

def update_github_releases_for_asset(githubtoken, asset_id, include_prerelease=False, per_page=100, release_limit=50):
    if githubtoken is None:
        print("No GitHub token specified")
        sys.exit(1)

    filename = os.path.join("assets", asset_id + ".json")
    if not os.path.exists(filename):
        print("Asset JSON not found: %s" % filename)
        sys.exit(1)

    print("Update releases for asset %s" % asset_id)

    asset = read_as_json(filename)
    if not asset:
        print("...error reading asset")
        sys.exit(1)

    project_url = asset.get("project_url", "")
    if "github.com" not in project_url:
        print("...not a GitHub repository!")
        sys.exit(0)

    path = urlparse(project_url).path.strip("/")
    parts = path.split("/")
    if len(parts) < 2:
        print("...could not parse owner/repo from URL!")
        sys.exit(1)
    repo = "/".join(parts[:2])

    def pick_zip_url(rel):
        assets = rel.get("assets") or []
        for a in assets:
            name = (a.get("name") or "").lower()
            ctype = (a.get("content_type") or "").lower()
            if name.endswith(".zip") or "zip" in ctype:
                return a.get("browser_download_url")
        tag = rel.get("tag_name")
        if tag:
            return f"https://github.com/{repo}/archive/refs/tags/{tag}.zip"
        return rel.get("zipball_url")

    def sanitize_text(text):
        if text is None:
            return ""
        if not isinstance(text, str):
            text = str(text)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)
        return text

    def parse_message_info(text):
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
                    val = m.group(1).strip()
                    if "-" in val:
                        val = val.split("-")[0]
                    min_defold = val
                continue
            out_lines.append(line)
        return "\n".join(out_lines).strip(), min_defold

    previous_releases = asset.get("releases") or []
    prev_latest_tag = previous_releases[0].get("tag") if previous_releases else None

    url = "https://api.github.com/repos/%s/releases?per_page=%d" % (repo, per_page)
    response = github_request(url, githubtoken)
    if not isinstance(response, list):
        print("...no releases or unexpected response")
        sys.exit(0)

    collected_rels = []
    found_prev = False
    for rel in response:
        if rel.get("draft"):
            continue
        if not include_prerelease and rel.get("prerelease"):
            continue
        collected_rels.append(rel)
        if prev_latest_tag and rel.get("tag_name") == prev_latest_tag:
            found_prev = True
            break
        if len(collected_rels) >= release_limit:
            break

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
        try:
            idx = next(i for i, r in enumerate(previous_releases) if r.get("tag") == prev_latest_tag)
        except StopIteration:
            idx = None

        existing_tags = set(item.get("tag") for item in new_items)
        if idx is not None:
            tail = [r for r in previous_releases[idx+1:] if r.get("tag") not in existing_tags]
        else:
            tail = [r for r in previous_releases if r.get("tag") not in existing_tags]

        releases_out = (new_items + tail)[:release_limit]
    else:
        releases_out = new_items[:release_limit]

    if releases_out:
        print("...assembled %d releases (incremental)" % len(releases_out))
        asset["releases"] = releases_out
        write_as_json(filename, asset)
    else:
        print("...no suitable releases found")

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
        if args.asset:
            update_github_releases_for_asset(args.githubtoken, args.asset, release_limit=limit)
        else:
            update_github_releases_for_assets(args.githubtoken, release_limit=limit)
    elif command == "header":
        update_header_json()
    elif command == "dates":
        add_creation_date_to_assets()
    elif command == "commit":
        commit_changes(args.githubtoken)
    else:
        print("Unknown command {}".format(command))
