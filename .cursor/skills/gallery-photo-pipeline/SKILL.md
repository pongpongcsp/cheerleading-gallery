---
name: gallery-photo-pipeline
description: End-to-end workflow to cull, compress, and publish large photo sets into cheerleading-gallery. Use when adding many photos to the website, preparing a shoot for GitHub Pages, updating js/photos.js, or building a scalable image folder layout for the gallery.
---

# Gallery Photo Pipeline

Orchestrates **photo-culling** → **compress-photo** → gallery integration for `cheerleading-gallery`. Optimized for large volumes on GitHub Pages.

## Why This Pipeline Exists

The site is a static HTML/CSS/JS gallery. Putting camera originals (or thousands of unoptimized JPGs) into git will:

- Blow up clone / deploy time
- Slow masonry loading on mobile
- Risk GitHub soft limits and Pages bandwidth pain

Always ship **culled + multi-size compressed** assets, never RAW/originals.

## End-to-End Workflow

```text
SOURCE shoot folder
  → photo-culling (keepers)
  → compress-photo (thumbs + display)
  → copy into images/<category>/
  → update js/photos.js
  → verify locally
  → commit only web assets
```

### 1. Cull

Use the **photo-culling** skill on the shoot folder.

- Smoke-test first on large sets
- Human-review `keepers` (and borderline `review` shots)
- Keep rejects on disk; do not delete unless asked

### 2. Compress

Use the **compress-photo** skill on the approved keeper folder.

Target layout:

```text
compressed/<shoot-name>/
  thumbs/     # max edge 640
  display/    # max edge 1920
```

Defaults: see compress-photo skill + `references/gallery-targets.md`.

### 3. Place Files in the Repo

```text
images/
  competition/
  campus/
  commercial/
  behind/
```

Copy compressed files into the matching category folder. Prefer stable, URL-safe filenames:

```text
20250810-dome-001.jpg
20250810-dome-001.thumb.jpg
```

Or paired folders:

```text
images/competition/display/...
images/competition/thumbs/...
```

Stay consistent within the repo. If the current site only references one URL per photo, use **display** in `url` for now and plan thumbs as a follow-up enhancement in `js/app.js`.

### 4. Update `js/photos.js`

Each entry should look like:

```javascript
{
  id: 31,
  title: '全國賽 — 開場演出',
  category: 'competition',       // competition | campus | commercial | behind
  categoryLabel: '2024全國賽',
  url: 'images/competition/20250810-dome-001.jpg',
  width: 1280,
  height: 1920,
  tags: ['啦啦隊', '比賽']
}
```

Rules:

- Increment `id` uniquely
- `category` must match tab `data-category` values in `index.html`
- Prefer local `images/...` paths over remote placeholders (replace picsum URLs when real assets land)
- Fill `width` / `height` from actual compressed dimensions when known
- Keep tags searchable (Chinese and/or English as used on the site)

### 5. Verify Before Commit

- Open `index.html` locally (or a simple static server)
- Check category tabs, search, lightbox prev/next
- Confirm no broken image URLs
- Spot-check file sizes (see targets in `references/gallery-targets.md`)

### 6. Git Hygiene for Large Volumes

- Commit compressed web assets only
- Do **not** commit RAW, cull reports, or full keeper originals into this repo
- If a single shoot exceeds ~50–100 MB of web images, consider:
  - External object storage / CDN for `url`s, or
  - Splitting shoots across releases, or
  - Git LFS only if the user explicitly wants it (Pages still needs reachable URLs)

## Scaling Notes

| Volume | Recommendation |
|--------|----------------|
| < 100 photos | Local `images/` + `photos.js` is fine |
| 100–500 | Required thumbs + display sizes; lazy load already in `app.js` |
| 500+ | Strongly consider CDN/R2/Cloudinary; generate `photos.js` (or JSON) via script; avoid multi-hundred-MB git history |
| Infinite scroll | Already batches 12 at a time in `app.js` — keep entries lean |

Future-friendly improvement (when implementing, not required to invent now): move `allPhotos` to `data/photos.json` and fetch it, so agents/scripts can append without rewriting a huge JS file.

## Agent Checklist

- [ ] Culled with human-reviewed keepers
- [ ] Compressed to web targets (thumb + display when possible)
- [ ] Files under `images/<category>/`
- [ ] `js/photos.js` updated with correct categories/tags
- [ ] Local visual check of grid + lightbox
- [ ] No originals / RAW / cull dumps in the commit

## Related Skills

- `photo-culling` — shortlist from large shoots
- `compress-photo` — web-size outputs

Read `references/gallery-targets.md` for numeric size/quality targets.
