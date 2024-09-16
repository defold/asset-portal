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
        with open(filename, "r") as f:
            decoded = json.load(f)
            return decoded
    except Exception as err:
        print("read_as_json", err)
    return None


def write_as_json(filename, data):
    try:
        os.chmod(filename, stat.S_IWUSR | stat.S_IWGRP | stat.S_IRUSR | stat.S_IRGRP)
        with open(filename, "w") as f:
            json.dump(data, f, indent=2, sort_keys=True)
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
parser.add_argument('commands', nargs="+", help='Commands (starcount, commit, help)')
parser.add_argument("--githubtoken", dest="githubtoken", help="Authentication token for GitHub API and ")
args = parser.parse_args()

help = """
COMMANDS:
starcount = Add GitHub star count to all assets that have a GitHub project (requires --githubtoken)
dates = Add creation date to all assets
commit = Commit changed files (requires --githubtoken)
help = Show this help
"""

for command in args.commands:
    if command == "help":
        parser.print_help()
        print(help)
        sys.exit(0)
    elif command == "starcount":
        update_github_star_count_for_assets(args.githubtoken)
    elif command == "dates":
        add_creation_date_to_assets()
    elif command == "commit":
        commit_changes(args.githubtoken)
    else:
        print("Unknown command {}".format(command))
