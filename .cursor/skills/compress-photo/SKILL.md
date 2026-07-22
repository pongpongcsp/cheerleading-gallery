---
name: compress-photo
description: Batch-compress photos for web galleries while preserving originals. Use when compressing JPG/JPEG/PNG/WebP folders, reducing image size, preparing photos for GitHub Pages or cheerleading-gallery upload, generating thumbs plus display sizes, or optimizing image assets.
---

# Compress Photo

Non-destructive batch compression for website galleries. Prefer project-relative tools and portable commands over machine-specific paths.

## Goals

- Compress images with strong visual quality for web display
- Never overwrite or delete originals by default
- Write outputs to a separate folder, preserving relative structure
- Produce web-ready sizes suitable for large galleries
- Preserve EXIF/ICC when the tool supports it
- Report count, original size, compressed size, and savings

## Defaults (website gallery)

| Setting | Default | Notes |
|---------|---------|-------|
| Display max edge | `1920` | Lightbox / full view |
| Thumb max edge | `640` | Masonry grid cards |
| JPEG quality | `82` | Balance of size vs quality for GitHub Pages |
| WebP quality | `80` | Prefer WebP when target browser support allows |
| Progressive JPEG | on | Faster perceived load |
| Optimize | on | Huffman optimize when available |
| Chroma | `4:2:0` | Web default; use `4:4:4` only if user asks for max color fidelity |

For this repo (`cheerleading-gallery`), also follow `references/gallery-targets.md` in `gallery-photo-pipeline` when preparing site assets.

## Tool Discovery (portable)

Resolve tools in this order. Do **not** hardcode user home or Codex runtime paths.

1. Project scripts if present: `tools/compress-photos.py`, `scripts/compress-photos.py`, or skill `scripts/`
2. `python3` / `python` with Pillow (`PIL`)
3. `magick` / ImageMagick `convert`
4. `sharp-cli` or Node `sharp`
5. `cjpeg` / mozjpeg

Detect with `which` / `command -v` (or Windows `where`) before running.

### Preferred project command

```bash
python3 tools/compress-photos.py "SOURCE_FOLDER" "OUTPUT_FOLDER" \
  --quality 82 --max-edge 1920
```

Keep original dimensions (archives only — not for the live site):

```bash
python3 tools/compress-photos.py "SOURCE_FOLDER" "OUTPUT_FOLDER" \
  --quality 90 --max-edge 0
```

If a `.bat` wrapper exists, use it only on Windows after confirming it resolves a portable Python, not a machine-specific Codex path.

## Output Layout (large-volume ready)

When preparing photos for the website, write **two sizes** unless the user asks for one:

```text
OUTPUT_FOLDER/
  display/     # max edge 1920, quality ~82
  thumbs/      # max edge 640, quality ~78–80
```

Single-folder mode (legacy / simple compress) is fine when the user only asks to shrink files.

Suggested output root:

- Sibling folder: `<parent>/compressed/<source-folder-name>/`
- Or workspace-safe: `compressed/<source-folder-name>/`

## Workflow

1. Confirm or infer `SOURCE_FOLDER`.
2. Count supported images (`jpg`, `jpeg`, `png`, `webp`) and sum original bytes.
3. Choose a non-destructive `OUTPUT_FOLDER`.
4. Run a small smoke test first when the folder is large (`--limit 10` if supported, or process a subfolder).
5. Compress full set with website defaults (or user overrides).
6. Verify output count matches expected inputs (accounting for format conversion if any).
7. Fail if any 0-byte outputs exist; recompress those files.
8. Report: source, output, file count, original MB, compressed MB, % saved, average bytes/file.
9. Remind the user to publish **compressed** assets, never camera originals, into the site repo.

## Verification

```bash
# Count + total size (Linux/macOS)
find "OUTPUT_FOLDER" -type f \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.webp' -o -iname '*.png' \) \
  -printf '%s\n' | awk '{n++; s+=$1} END {print n, s}'

# Zero-byte check
find "OUTPUT_FOLDER" -type f -size 0
```

PowerShell equivalent is acceptable on Windows; prefer the same checks, not a different success standard.

## Safety Rules

- Never overwrite source images by default
- Never delete originals
- On permission errors, fall back to a workspace-writable output folder
- Resume interrupted runs by skipping non-empty existing outputs
- Recompress or replace 0-byte outputs
- For large folders, use longer command timeouts and batch in chunks if needed
- Always verify counts and sizes after compression

## Size Guidance for Large Galleries

| Role | Max edge | Target avg size |
|------|----------|-----------------|
| Grid thumb | 640 | 40–120 KB |
| Display / lightbox | 1920 | 150–400 KB |
| Hero / rare full-bleed | 2400 | ≤ 600 KB |

If average display files exceed ~500 KB, lower quality to `78–80` or max edge to `1600` before committing to git / GitHub Pages.

## Anti-patterns

- Hardcoding `C:\Users\...` or Codex runtime Python paths
- Committing RAW / full-resolution camera files to the website repo
- Using quality `95+` for gallery grids (diminishing returns, huge repos)
- Skipping verification after batch runs
- Treating compression as a substitute for culling (run photo-culling first when volume is high)
