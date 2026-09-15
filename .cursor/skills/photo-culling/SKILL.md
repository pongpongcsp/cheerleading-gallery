---
name: photo-culling
description: Non-destructive AI first-pass culling for large photo folders. Use when the user wants to review, rank, cull, filter, shortlist keepers, find blurry shots, or group similar photos before website publish.
---

# Photo Culling

AI first-pass culling for large shoots via **PixCull offline CLI**. Never delete, overwrite, or move original photos unless the user explicitly asks.

## Place in the gallery pipeline

```text
RAW shoot(s) under D:\Photo\<event>
  → 1) photo-culling   (this skill)   → keepers/ (PixCull keep, uncapped)
  → 2) manual confirm                  → review report / edit keepers/
  → 3) compress-photo                  → compressed/
  → 4) gallery-publish                 → Cloudinary + js/photos.js + GitHub Pages
```

Keeper volume is **score-based** from PixCull `keep` decisions (no default hard cap). Cloudinary cost scales with keepers — always skim the HTML report before upload.

## Prefer the project tool

Requires **Python 3.11 or 3.12**.

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\activate
pip install -r requirements.txt
python tools/cull-photos.py "SOURCE_FOLDER" "OUTPUT_FOLDER" --copy-keepers
```

`requirements.txt` installs PixCull from GitHub (`v2.36.0` tag) because PyPI may not have a wheel yet.
Useful flags:

```bash
--max-keepers 0           # default: no hard cap (all PixCull keep)
--max-keepers N           # optional hard top-N by PixCull score_final
--scene event             # default; PixCull scene override
--strictness standard     # strict | standard | lenient
--copy-keepers
--limit 50                # score only first N files (smoke test)
--legacy                  # retired 4D YOLO/OpenCV culler (optional deps)
```

First PixCull run downloads on-device models into `~/.pixcull` (and InsightFace cache).

**Security:** offline CLI only. Do **not** run `pixcull serve`, bind `0.0.0.0`, share links, LAN sync, or set `DEEPSEEK_API_KEY` for gallery publish.

Batch all configured events (Desktop):

```bat
publish-all.bat --skip-upload
```

or full publish:

```bat
publish-all.bat
```

## Recommended workflow

1. Confirm source folder(s) exist under `D:\Photo\`.
2. Dry-run one folder with `--limit 30`.
3. Open `OUTPUT_FOLDER/culling-report.html` and spot-check keepers (pipeline pauses here by default).
4. Edit `keepers/` if needed, then confirm to continue.
5. Compress / publish proceeds only after confirm.
6. Do not auto-delete originals.

## Ranking rule (PixCull)

1. PixCull scores each frame (6-axis rubric + fusion) and labels `keep` / `maybe` / `cull`.
2. Gallery mapping: `keep` → keeper, `maybe` → review, `cull` → reject.
3. Only **keepers** are copied for compress/upload (default).
4. Optional: `--max-keepers N` truncates keepers to top-N by `score_final`.

## Output layout

```text
OUTPUT_FOLDER/
  culling-report.html
  culling-report.csv
  thumbs/
  pixcull/          # raw PixCull run (scores.csv, etc.)
  keepers/          # only when --copy-keepers
  rejects/          # only when --copy-rejects
```

## Caveat

PixCull still misses storytelling nuance. Always skim the HTML report before uploading.
