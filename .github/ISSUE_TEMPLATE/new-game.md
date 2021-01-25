---
name: New game
about: Submit a new game for inclusion in the Defold Showcase/Games page on www.defold.com/showcase
title: ''
labels: ''
assignees: ''

---

```json
{
    "name": "",
	"description": "",
    "url": "",
    "developer": "",
    "publisher": "",
    "releasedate": "",
    "platforms": "iOS,Android,macOS,Windows,Linux,HTML5,Steam,Poki,itch.io,Kongregate,Facebook Instant Games,...",
    "images": {
        "full": "",
        "half": "",
        "third": ""
    }
}
```

* `name` - (REQUIRED) Name of the awesome Defold game.
* `description` - (REQUIRED) Short text describing the game.
* `url` - (REQUIRED) Link to a game or store page.
* `developer` - (REQUIRED) Name of the developer/studio.
* `publisher` - (OPTIONAL) Name of the publisher.
* `release_date` - (REQUIRED) Date of release (Month Year, eg April 2020).
* `platforms` - (REQUIRED) The platforms where the game can be played. Comma separated list.
* `images` - (REQUIRED) Filenames of images that can be used when presenting the asset.
  * `full` - (REQUIRED) Filename of attached image to use as full width image. PNG or JPG. Recommended size is 3000x750. Name: game-name-full.png|jpg
  * `half` - (REQUIRED) Filename of attached image to use as half width image. PNG or JPG. Recommended size is 1200x600 pixels. Name: game-name-half.png|jpg
  * `third` - (REQUIRED) Filename of attached image to use as one third width image. PNG or JPG. Recommended size is 800x600 pixels. Name: game-name-third.png|jpg

Note: We retain the right to not accept a submitted game and we decide if the game goes on the Showcase or Games page
