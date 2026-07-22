---
name: photo-culling
description: Non-destructive first-pass culling for large photo folders. Use when the user wants to review, rank, cull, filter, shortlist keepers, find blurry shots, or group similar photos before website publish.
---

# Photo Culling

First-pass technical culling for large shoots. Never delete, overwrite, or move originals unless the user explicitly asks.

## Place in the gallery pipeline

```text
RAW shoot
  → 1) photo-culling   (this skill)   → keepers/
  → 2) compress-photo                  → compressed/
  → 3) gallery-publish                 → Cloudinary + js/photos.js + GitHub Pages
```

For cheerleading-gallery / friend sharing, cull aggressively before compress+upload. A 2000-shot event should usually become a few hundred keepers, not thousands of near-duplicates.

## Prefer the project tool

```bash
python tools/cull-photos.py "SOURCE_FOLDER" "OUTPUT_FOLDER"
```

Useful flags:

```bash
--similar-threshold 8
--review-percent 0.30
--copy-keepers
--limit 50
```

Windows wrapper (if present):

```bat
cull-photos.bat "SOURCE_FOLDER" "OUTPUT_FOLDER"
```

## Recommended workflow

1. Confirm source folder exists; count images and total size.
2. Dry-run with `--limit 20` first.
3. Open `OUTPUT_FOLDER/culling-report.html` and spot-check keepers/rejects.
4. Run the full folder with `--copy-keepers`.
5. Hand the `keepers/` folder to the compress-photo skill.
6. Do not auto-delete rejects.

## Output layout

```text
OUTPUT_FOLDER/
  culling-report.html
  culling-report.csv
  thumbs/
  keepers/          # only when --copy-keepers
  rejects/          # only when --copy-rejects
```

## Suggestion meanings

| Label | Meaning |
|-------|---------|
| keeper | Best technical pick, or best in a similar group |
| review | Usable; check manually |
| reject | Blurry, weak exposure, or weaker duplicate |

## Caveat

Scores cover sharpness / exposure / similarity only. They cannot judge expression, storytelling, or taste. Always treat results as a first pass.

## Gallery tip

When publishing to cheerleading-gallery, prefer uploading only `keepers/` (or a manually trimmed subset). Full RAW dumps make the site slow for friends on mobile.
