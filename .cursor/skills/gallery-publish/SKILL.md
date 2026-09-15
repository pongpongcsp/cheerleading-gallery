---
name: gallery-publish
description: End-to-end workflow to cull (PixCull keep), compress, upload, and publish multiple photo sets to cheerleading-gallery via Cloudinary. Use when sharing many event folders with friends.
---

# Gallery Publish

Publish large photo volumes to **cheerleading-gallery** without putting binary images in git.

## Why this architecture

| Layer | Role |
|-------|------|
| Local disk (`D:\Photo\...`) | RAW + cull keepers + compressed copies |
| Cloudinary | Host score-based keepers per event on a CDN |
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
node tools/publish-events.js
```

Per event this runs:

1. `cull-photos.py --max-keepers 0 --copy-keepers` (PixCull offline CLI; uncapped keep)
2. **Manual confirm** — open `culling-report.html`, optionally edit `keepers/`, then continue (or skip/abort)
3. `compress-photos.py` (quality 85, max-edge 2000)
4. `upload-to-cloudinary.js`
5. After all events: `generate-photos.js` → `js/photos.js`

Requires **Python 3.11–3.12** + project `.venv` with `pip install -r requirements.txt` (PixCull from GitHub). Offline cull only — no `pixcull serve` / LAN / DeepSeek. `publish-events.js` prefers `.venv` when present.

Useful flags:

```bash
node tools/publish-events.js --skip-upload          # cull+confirm+compress only
node tools/publish-events.js --skip-confirm         # no pause (automation)
node tools/publish-events.js --only 20250928_桃園_樂天女孩
node tools/publish-events.js --photo-root "D:\Photo"
node tools/publish-events.js --max-keepers 80       # optional hard cap override
```

Single folder:

```bat
publish-event.bat "D:\Photo\20250928_桃園_樂天女孩" "20250928_桃園_樂天女孩"
```

## Budget

Default is **uncapped** PixCull keep decisions. After each cull the pipeline **pauses for manual confirm** before compress. Cloudinary cost grows with volume — skim/edit keepers at that pause. Optional `--max-keepers N` for a hard cap; `--skip-confirm` to auto-continue.

## Credentials

```bash
# .env (gitignored)
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
```

## After generate

1. Confirm uploads look right on the site / Cloudinary.
2. Commit metadata only: `js/photos.js`, `tools/gallery-folders.json`, tab updates.
3. Push → GitHub Pages.

## Anti-patterns

- Committing full-resolution photos into git
- Uploading uncullled RAW dumps
- Serving 4000×6000 originals without transforms
- Hardcoding API secrets in JS
- Running `pixcull serve` or LAN bind as part of publish
