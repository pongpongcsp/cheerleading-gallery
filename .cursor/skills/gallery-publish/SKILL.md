---
name: gallery-publish
description: End-to-end workflow to cull, compress, upload, and publish large photo sets to the cheerleading-gallery GitHub Pages site via Cloudinary. Use when sharing many photos with friends, adding event folders, or updating the live gallery.
---

# Gallery Publish

Publish large photo volumes to **cheerleading-gallery** without putting binary images in git.

## Why this architecture

| Layer | Role |
|-------|------|
| Local disk | RAW + cull keepers + compressed copies |
| Cloudinary | Host images on a CDN (fast for friends) |
| GitHub Pages | Host only HTML/CSS/JS + `js/photos.js` metadata |

Do **not** commit camera originals or hundreds of MB of JPEGs into this repo. GitHub Pages soft-limits and slow clones make that painful. The sibling `photo-website` repo already proved Cloudinary + metadata works (~2900 photos).

## Full pipeline

```text
1. Cull     python tools/cull-photos.py RAW OUT --copy-keepers
2. Compress python tools/compress-photos.py keepers compressed --quality 85 --max-edge 2000
3. Upload   node tools/upload-to-cloudinary.js compressed "EventFolderName"
4. Generate node tools/generate-photos.js
5. Ship     git add js/photos.js && git commit && git push
```

Live site: https://pongpongcsp.github.io/cheerleading-gallery/

## Credentials

Never hardcode Cloudinary secrets in source. Use environment variables:

```bash
export CLOUDINARY_CLOUD_NAME="your_cloud"
export CLOUDINARY_API_KEY="your_key"
export CLOUDINARY_API_SECRET="your_secret"
```

Or a single URL:

```bash
export CLOUDINARY_URL="cloudinary://API_KEY:API_SECRET@CLOUD_NAME"
```

Copy `.env.example` → `.env` locally. `.env` is gitignored.

## Folder → category mapping

Edit `tools/gallery-folders.json`:

```json
[
  {
    "folder": "20250810_台北大巨蛋_樂天女孩",
    "category": "competition",
    "categoryLabel": "2024全國賽",
    "tags": ["啦啦隊", "比賽"]
  }
]
```

Valid `category` values must match tabs in `index.html`:

| category | Tab |
|----------|-----|
| competition | 2024 全國賽 |
| campus | 校園寫真 |
| commercial | 商業拍攝 |
| behind | 幕後花絮 |

Add new tabs in `index.html` if you need more event groups.

## Upload

```bash
node tools/upload-to-cloudinary.js "PATH/TO/compressed" "CloudinaryFolderName"
```

- Uploads JPG/JPEG only
- Concurrency 8
- Resumable via `upload-log.json` (gitignored)
- Does not overwrite existing public IDs

## Generate gallery data

```bash
node tools/generate-photos.js
```

Writes `js/photos.js` with:

- Responsive Cloudinary URLs (`f_auto,q_auto`)
- Grid thumbs (~800px) + lightbox URLs (~2000px)
- Width/height from Cloudinary metadata
- Stable numeric ids

## After generate

1. Spot-check a few URLs in the browser.
2. Commit **only** metadata (`js/photos.js`, maybe `tools/gallery-folders.json`).
3. Push to `main` (or open a PR). GitHub Pages updates automatically.

## Agent checklist

When the user asks to publish a new event folder:

1. Confirm source path and intended category/label.
2. Cull → compress → upload → generate (skip steps already done).
3. Never commit `.env`, `upload-log.json`, `images/`, or RAW folders.
4. Report: file counts, compressed size savings, Cloudinary folder, live URL.
5. Remind that cull scores are technical suggestions only.

## Anti-patterns

- Committing full-resolution photos into git
- Uploading uncullled RAW dumps
- Serving 4000×6000 originals without transforms
- Hardcoding API secrets in JS (rotate if previously committed elsewhere)
