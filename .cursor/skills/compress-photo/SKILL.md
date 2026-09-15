---
name: compress-photo
description: Batch compress JPG/JPEG photos for web use while preserving quality, EXIF, ICC profile, and folder structure. Use when preparing photos for website upload, GitHub Pages, Cloudinary, or gallery publish.
---

# Compress Photo

Compress JPG/JPEG folders for web delivery. Preserve originals; write to a separate output folder.

## Place in the gallery pipeline

```text
RAW shoot
  → 1) photo-culling (PixCull keep, uncapped) → keepers/
  → 2) manual confirm (review / edit keepers)
  → 3) compress-photo  (this skill)          → compressed/
  → 4) gallery-publish                       → Cloudinary + js/photos.js
```

Always compress **after** culling **and manual confirm**, **before** Cloudinary upload. Prefer compressing only the keepers folder, not the full RAW dump.

## Defaults (website / cheerleading-gallery)

| Setting | Value |
|---------|-------|
| JPEG quality | `85` |
| Max edge | `2000` |
| Progressive | on |
| Optimize | on |
| Chroma subsampling | `0` (4:4:4) |

## Prefer the project tool

```bash
python tools/compress-photos.py "SOURCE_FOLDER" "OUTPUT_FOLDER" --quality 85 --max-edge 2000
```

Batch via:

```bat
publish-all.bat
```

## Safety

- Never overwrite sources by default.
- Never delete originals.
- Resume by skipping non-empty existing outputs.
- Always verify counts and total size after compression.
