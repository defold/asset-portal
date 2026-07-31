# Assets
Collection of Defold assets, libraries and extensions. The asset definitions listed in `assets` are used by the [Asset Portal on the Defold website](https://www.defold.com/assets). 

## Submitting an asset
Submit a new asset for inclusion in this collection either via the `Submit Asset` button on the Asset Portal or by [Creating an Issue](https://github.com/defold/awesome-defold/issues/new?assignees=&labels=&template=new-asset.md&title=).

## Updating an asset
You can update an asset by modifying its metadata file. The metadata for all assets can be found in the `assets` folder of this repository. Once you are happy with the changes please submit a pull request.

## External creator actions
Assets can optionally include up to three external creator action links. These links are rendered on the asset detail page on the Defold website. Defold only links to third-party platforms and does not process payments, manage purchases, provide refunds, or verify license entitlement.

Example:

```json
"external_actions": [
  {
    "type": "purchase",
    "label": "Purchase commercial license",
    "url": "https://github.com/sponsors/creator?frequency=one-time"
  },
  {
    "type": "support",
    "label": "Support on Ko-fi",
    "url": "https://ko-fi.com/creator"
  }
]
```

Supported `type` values are:

* `purchase` for a purchase, paid download, or commercial license.
* `support` for an optional donation or sponsorship which does not itself describe a purchase.

Each action must contain only `type`, `label`, and `url`. The label must be 50 characters or fewer, and URLs must use `https://`.

Allowed external action destinations are itch.io, Patreon, Ko-fi, PayPal, Stripe Checkout or Payment Links, Gumroad, GitHub Sponsors, and Open Collective. Asset authors are responsible for keeping the label, destination, pricing, and licensing information accurate. Run `python3 update.py validate` before submitting a pull request to check the metadata.

## Images
Each asset has a thumbnail image and a hero image. The thumbnail image is a rectangular image with a maximum resolution of 570x380 piexels. The hero image is a wide image with a maximum resolution of 2400x666 pixels. If you submit smaller images, please make sure to maintain the correct aspect ratio.
