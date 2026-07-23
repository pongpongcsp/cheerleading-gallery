---
name: gallery-publish
description: End-to-end workflow to cull (~50/event), compress, upload, and publish multiple photo sets to cheerleading-gallery via Cloudinary. Use when sharing many event folders with friends.
---

# Gallery Publish

Publish large photo volumes to **cheerleading-gallery** without putting binary images in git.

## Why this architecture

| Layer | Role |
|-------|------|
| Local disk (`D:\Photo\...`) | RAW + cull keepers + compressed copies |
| Cloudinary | Host ~50 keepers per event on a CDN |
| GitHub Pages | Host only HTML/CSS/JS + `js/photos.js` |

## Full multi-folder pipeline (Desktop)

Configured events live in `tools/gallery-folders.json` (9 confirmed events).

```bat
copy .env.example .env
REM fill Cloudinary credentials

publish-all.bat
```

Equivalent:

```bash
node tools/publish-events.js --max-keepers 50
```

Per event this runs:

1. `cull-photos.py --max-keepers 50 --copy-keepers`
2. `compress-photos.py` (quality 85, max-edge 2000)
3. `upload-to-cloudinary.js`
4. After all events: `generate-photos.js` → `js/photos.js`

Useful flags:

```bash
node tools/publish-events.js --skip-upload          # cull+compress only
node tools/publish-events.js --only 20250928_桃園_樂天女孩
node tools/publish-events.js --photo-root "D:\Photo"
```

Single folder:

```bat
publish-event.bat "D:\Photo\20250928_桃園_樂天女孩" "20250928_桃園_樂天女孩" 50
```

## Budget

Default **50 keepers × 9 events ≈ 450** Cloudinary uploads — not full RAW dumps.

## Credentials

```bash
# .env (gitignored)
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```

## After generate

1. Spot-check `culling/<folder>/culling-report.html` for each event.
2. Commit metadata only: `js/photos.js`, `tools/gallery-folders.json`, tab updates.
3. Push → GitHub Pages.

## Anti-patterns

- Committing full-resolution photos into git
- Uploading uncullled RAW dumps
- Serving 4000×6000 originals without transforms
- Hardcoding API secrets in JS
