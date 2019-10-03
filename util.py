#!/usr/bin/env python

import os
import sys
import shutil
import json
import string

def split_it():
    valid_chars = "%s%s" % (string.ascii_letters, string.digits)
    with open("assets.json") as assets:
        for asset in json.load(assets).get("assets"):
            filename = ''.join(c for c in asset["name"] if c in valid_chars)
            filename = filename.lower() + ".json"
            with open(os.path.join("assets", filename), "w") as out:
                json.dump(asset, out, indent=4)


def write_thumbnail():
    for filename in os.listdir("assets"):
        if filename.endswith(".json"):
            with open(os.path.join("assets", filename)) as asset:
                print(filename)
                a = json.load(asset)
                extension = None
                jpg = os.path.join("assets", "images", "assets", filename.replace(".json", "-hero.jpg"))
                png = os.path.join("assets", "images", "assets", filename.replace(".json", "-hero.png"))
                if os.path.exists(jpg):
                    extension = ".jpg"
                    os.rename(jpg, jpg.replace("-hero.jpg", "-thumb.jpg"))
                elif os.path.exists(png):
                    extension = ".png"
                    os.rename(png, png.replace("-hero.png", "-thumb.png"))

                if extension:
                    a["images"]["hero"] = ""
                    a["images"]["thumb"] = filename.replace(".json", "") + "-thumb" + extension
                    with open(os.path.join("assets", filename), "w") as out:
                        json.dump(a, out, indent=4)

def write_hero():
    for filename in os.listdir("assets"):
        if filename.endswith(".json"):
            with open(os.path.join("assets", filename)) as asset:
                a = json.load(asset)
                if not a.get("images").get("hero"):
                    hero = a["images"]["thumb"].replace("-thumb", "-hero")
                    if os.path.exists(os.path.join("assets", "images", "assets", hero)):
                        a["images"]["hero"] = hero
                        with open(os.path.join("assets", filename), "w") as out:
                            json.dump(a, out, indent=4)


def write_id():
    for filename in os.listdir("assets"):
        if filename.endswith(".json"):
            with open(os.path.join("assets", filename)) as asset:
                a = json.load(asset)
                a["id"] = filename.replace(".json", "")
                with open(os.path.join("assets", filename), "w") as out:
                    json.dump(a, out, indent=4)


def write_asset_url():
    for filename in os.listdir("assets"):
        if filename.endswith(".json"):
            with open(os.path.join("assets", filename)) as asset:
                a = json.load(asset)
                a["asset_url"] = "https://github.com/defold/awesome-defold/blob/master/assets/%s.json" % (filename.replace(".json", ""))
                with open(os.path.join("assets", filename), "w") as out:
                    json.dump(a, out, indent=4)

#split_it()
#write_hero()
#write_id()
write_asset_url()
