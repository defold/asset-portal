---
name: New asset
about: Submit a new asset for inclusion in the Asset Portal on www.defold.com/assets
title: ''
labels: ''
assignees: ''

---

```json
{
    "name": "",
	"description": "",
    "license": "",
    "tags": [
		"AI",
		"Ads",
		"Analytics",
		"Animation",
		"Art assets",
		"Audio",
		"Camera",
		"Device control",
		"Editor",
		"GUI",
		"Game mechanic",
		"Input",
		"Math",
		"Network",
		"Physics",
		"Rendering",
		"Shaders",
		"Social",
		"System",
		"Template projects",
		"Tools",
		"Tutorials",
		"Video"
    ],
    "author": "",
    "library_url": "",
    "forum_url": "",
    "project_url": "",
	"website_url": "",
    "platforms": [
        "iOS",
        "Android",
        "macOS",
        "Windows",
        "Linux",
        "HTML5"
    ],
    "images": {
        "hero": "",
        "thumb": ""
    }
}
```

* `name` - (REQUIRED) Name of the awesome Defold asset.
* `description` - (REQUIRED) Short text describing the asset.
* `license` - (OPTIONAL) The license used by the asset.
* `author` - (REQUIRED) Name of the extension author.
* `library_url` - (OPTIONAL) URL to add as Defold project dependency (eg https://github.com/britzl/monarch/archive/master.zip).
* `forum_url` - (OPTIONAL) URL to a Defold forum post for discussions about the asset.
* `project_url` - (OPTIONAL) URL to a website with additional information about the asset (eg https://github.com/britzl/monarch).
* `website_url` - (OPTIONAL) URL to a website with additional information.
* `tags` - (REQUIRED) One or more tags to categorize the asset.
* `platforms` - (REQUIRED) One or more platforms supported by the asset.
* `images` - (OPTIONAL) Filenames of two images that can be used when presenting the asset.
  * `hero` - (OPTIONAL) Filename of attached image to use as banner image. PNG or JPG. Recommended size is 2400x666.
  * `thumb` - (OPTIONAL) Filename of attached image to use as thumbnail image. PNG or JPG. Recommended size is 380x570 pixels.

Note: You must provide at least one of `library_url`, `website_url` and `project_url`.
