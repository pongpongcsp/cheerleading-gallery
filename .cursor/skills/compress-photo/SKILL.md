---
name: compress-photo
description: Batch compress JPG/JPEG photos for web use while preserving quality, EXIF, ICC profile, and folder structure. Use when preparing photos for website upload, GitHub Pages, Cloudinary, or gallery publish.
---

# Compress Photo

Compress JPG/JPEG folders for web delivery. Preserve originals; write to a separate output folder.

## Place in the gallery pipeline

```text
RAW shoot
  → 1) photo-culling                   → keepers/
  → 2) compress-photo  (this skill)    → compressed/
  → 3) gallery-publish                 → Cloudinary + js/photos.js + GitHub Pages
```

Always compress **after** culling, **before** Cloudinary upload. Uploading camera originals wastes bandwidth and slows friend sharing.

## Defaults (website / cheerleading-gallery)

| Setting | Value |
|---------|-------|
| JPEG quality | `85` |
| Max edge | `2000` |
| Progressive | on |
| Optimize | on |
| Chroma subsampling | `0` (4:4:4) |
| Output | sibling `compressed/<source-folder-name>/` |

Override only when the user asks. For lightbox-quality archives keep `--max-edge 0` and quality `90`–`92`, but still prefer `2000` for the public gallery.

## Prefer the project tool

```bash
python tools/compress-photos.py "SOURCE_FOLDER" "OUTPUT_FOLDER" --quality 85 --max-edge 2000
```

Keep original dimensions:

```bash
python tools/compress-photos.py "SOURCE_FOLDER" "OUTPUT_FOLDER" --quality 90 --max-edge 0
```

Windows:

```bat
compress-photos.bat "SOURCE_FOLDER" "OUTPUT_FOLDER" 85 2000
```

## Workflow

1. Confirm source path (usually cull `keepers/`).
2. Count JPG/JPEG files and original total size.
3. Choose a non-destructive output folder.
4. Run `tools/compress-photos.py`.
5. Verify output count matches input; no 0-byte files.
6. Report original size, compressed size, saved %, and paths.
7. Hand `OUTPUT_FOLDER` to gallery-publish.

## Safety

- Never overwrite sources by default.
- Never delete originals.
- Resume by skipping non-empty existing outputs.
- Recompress any 0-byte outputs.
- Use long timeouts for large folders.

## Why these numbers

Friends open the gallery on phones. A 4000×6000 camera JPEG is often 8–15 MB; a quality-85 / max-edge-2000 file is usually ~200–500 KB and still looks sharp fullscreen. Cloudinary can resize further with URL transforms, but uploading already-web-sized files is faster and cheaper.
