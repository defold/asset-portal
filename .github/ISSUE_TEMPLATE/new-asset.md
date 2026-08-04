---
name: New asset
about: Submit a new asset for inclusion in the Asset Portal on www.defold.com/assets
title: ''
labels: ''
assignees: ''

---

## Thumbnail

Provide one thumbnail using either of these options:

- Drag and drop the image here, then leave `images.thumb` empty below.
- Add a direct HTTPS image URL to `images.thumb` below.

<!-- Attach the thumbnail image here -->

WebP is preferred; PNG, JPG, and JPEG are also accepted. The recommended size is 900x600 pixels (3:2 aspect ratio).

## Asset metadata

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
    "external_actions": [],
    "platforms": [
        "iOS",
        "Android",
        "macOS",
        "Windows",
        "Linux",
        "HTML5"
    ],
    "images": {
        "thumb": ""
    }
}
```

* `name` - (REQUIRED) Name of the awesome Defold asset.
* `description` - (REQUIRED) Short text describing the asset.
* `license` - (OPTIONAL) The license used by the asset.
* `author` - (REQUIRED) Name of the extension author.
* `library_url` - (OPTIONAL) URL to add as Defold project dependency (eg <https://github.com/britzl/monarch/archive/master.zip>).
* `forum_url` - (OPTIONAL) URL to a Defold forum post for discussions about the asset.
* `project_url` - (OPTIONAL) URL to a site with additional information about the asset (eg <https://github.com/britzl/monarch>).
* `website_url` - (OPTIONAL) URL to a site with additional information.
* `external_actions` - (OPTIONAL) Up to three external creator links. Each entry must contain a `type` (`support`, `buy`, `donate`, `sponsor`, or `external`), a short `label`, and an allowlisted HTTPS `url`. Defold only links to the external platform and does not process payments.
* `tags` - (REQUIRED) One or more tags to categorize the asset.
* `platforms` - (REQUIRED) One or more platforms supported by the asset.
* `images` - (REQUIRED) Image information used when presenting the asset.
  * `thumb` - (REQUIRED unless the image is attached above) A direct HTTPS image URL. WebP is preferred; PNG, JPG, and JPEG are accepted. Recommended size is 900x600 pixels (3:2 aspect ratio).

Note: You must provide at least one of `library_url`, `website_url` and `project_url`.
