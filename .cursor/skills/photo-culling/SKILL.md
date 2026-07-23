---
name: photo-culling
description: Non-destructive first-pass culling for large photo folders. Use when the user wants to review, rank, cull, filter, shortlist keepers, find blurry shots, or group similar photos before website publish.
---

# Photo Culling

First-pass technical culling for large shoots. Never delete, overwrite, or move original photos unless the user explicitly asks.

## Place in the gallery pipeline

```text
RAW shoot(s) under D:\Photo\<event>
  → 1) photo-culling   (this skill)   → keepers/ (~50)
  → 2) compress-photo                  → compressed/
  → 3) gallery-publish                 → Cloudinary + js/photos.js + GitHub Pages
```

For cheerleading-gallery / friend sharing, use a **hard keep budget** so Cloudinary stays manageable.

## Prefer the project tool

```bash
python tools/cull-photos.py "SOURCE_FOLDER" "OUTPUT_FOLDER" --max-keepers 50 --copy-keepers
```

Useful flags:

```bash
--max-keepers 50          # hard top-N after de-dupe (default 50; 0 = no hard cap)
--similar-threshold 8
--review-percent 0.30     # only used when --max-keepers 0
--copy-keepers
--limit 50                # score only first N files (smoke test)
```

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
2. Dry-run one folder with `--limit 30 --max-keepers 10`.
3. Open `OUTPUT_FOLDER/culling-report.html` and spot-check keepers.
4. Run full folder with `--max-keepers 50 --copy-keepers`.
5. Hand `keepers/` to compress-photo / publish-events.
6. Do not auto-delete rejects.

## Ranking rule

1. Reject clearly blurry / weak shots.
2. Within each similar group, keep only the best 1 as a candidate.
3. Sort candidates by technical score descending.
4. Label top `--max-keepers` as `keeper`; remaining usable shots as `review`.

## Output layout

```text
OUTPUT_FOLDER/
  culling-report.html
  culling-report.csv
  thumbs/
  keepers/          # only when --copy-keepers (~50 files)
  rejects/          # only when --copy-rejects
```

## Caveat

Scores cover sharpness / exposure / similarity only — not expression or storytelling. Always skim the HTML report before uploading.
