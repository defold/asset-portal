# Assets
Collection of Defold assets, libraries and extensions. The asset definitions listed in `assets` are used by the [Asset Portal on the Defold site](https://www.defold.com/assets).

## Submitting an asset
Submit a new asset for inclusion in this collection either via the `Submit Asset` button on the Asset Portal or by [creating an issue](https://github.com/defold/asset-portal/issues/new?template=new-asset.md).

## Updating an asset
You can update an asset by modifying its metadata file. The metadata for all assets can be found in the `assets` folder of this repository. Once you are happy with the changes please submit a pull request.

### Automatic release updates

GitHub release and tag metadata is refreshed every six hours. For entries marked as Defold libraries, version-tag archive URLs and missing `library_url` values automatically advance to the newest stable GitHub Release. Repositories without GitHub Releases fall back to their newest tag. Branch archive URLs such as `master.zip` and `refs/heads/main.zip` already float automatically and are left unchanged, as are custom URL formats.

Set `"library_url_auto_update": false` only when a version must remain intentionally pinned. If one repository publishes several products from different tag families, set `library_release_tag_prefix` to the library's prefix, for example `"runtime."`.

## External creator actions
Assets can optionally include up to three external creator action links. These links are rendered on the asset detail page on the Defold site. Defold only links to third-party platforms and does not process payments, manage purchases, provide refunds, or verify license entitlement.

Example:

```json
"external_actions": [
  {
    "type": "buy",
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

Supported `type` values are `support`, `buy`, `donate`, `sponsor`, and `external`.

Each action must contain only `type`, `label`, and `url`. The label must be 50 characters or fewer, and URLs must use `https://`.

Allowed external action destinations are itch.io, Patreon, Ko-fi, PayPal, Stripe Checkout or Payment Links, Gumroad, GitHub Sponsors, and Open Collective. Asset authors are responsible for keeping the label, destination, pricing, and licensing information accurate. Run `python3 update.py validate` before submitting a pull request to check the metadata.

## Images
New submissions use one thumbnail image throughout the Asset Portal. The recommended size is 900x600 pixels (3:2 aspect ratio). WebP is preferred; PNG, JPG, and JPEG are also accepted as submission sources.

If the image is already hosted, add its HTTPS URL as `images.thumb`. Otherwise, attach it directly to the submission issue. Before an asset is merged, store the normalized image in `assets/images/` as a 900x600 WebP named `<asset-id>-thumb.webp`, and reference that filename from `images.thumb`.

Older asset metadata may still contain an `images.hero` value and its corresponding file. These legacy values can remain, but hero images are no longer required or used by the Asset Portal.
