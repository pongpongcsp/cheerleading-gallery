---
name: photo-culling
description: Non-destructive photo culling for large folders. Use when reviewing, ranking, shortlisting, filtering blurry or duplicate photos, generating keeper/review/reject reports, or selecting shots before compressing for a website gallery.
---

# Photo Culling

First-pass technical culling for large photo folders. Suggestions only — never treat algorithm output as final artistic selection.

## Default Principle

Never delete, overwrite, or move originals unless the user explicitly requests that exact action.

Default flow:

1. Read from the source folder
2. Write reports (and optional copied selections) to a separate output folder
3. Tell the user results are suggestions; they should review keepers manually

## When to Use

- Large shoot folders that need a shortlist before web publish
- Finding blurry, underexposed, or near-duplicate frames
- Generating HTML/CSV review reports
- Preparing a keeper set that will later be compressed for `cheerleading-gallery`

For website publishing, after culling use **compress-photo**, then **gallery-photo-pipeline**.

## Tool Discovery (portable)

Resolve tools in this order. Do **not** hardcode absolute user paths.

1. Project scripts: `tools/cull-photos.py`, `scripts/cull-photos.py`, or skill `scripts/`
2. Wrapper scripts in the repo root (`cull-photos.bat` / `cull-photos.sh`) only if they call a portable interpreter
3. Document clearly if no local tool exists and fall back to a limited manual review plan

### Preferred command

```bash
python3 tools/cull-photos.py "SOURCE_FOLDER" "OUTPUT_FOLDER"
```

Useful options (when supported):

```bash
--similar-threshold 8
--review-percent 0.30
--copy-keepers
--copy-rejects
--limit 50
```

Windows `.bat` wrappers are optional convenience only; prefer the Python entrypoint for portability.

## Capabilities (expected)

- Formats: JPG / JPEG / PNG / WEBP
- Sharpness scoring
- Brightness / contrast / clipping scoring
- Similar-photo grouping (dHash or equivalent)
- Labels: `keeper` / `review` / `reject`
- HTML report + CSV report
- Optional copy of keepers / rejects into output subfolders

## Workflow

1. Confirm `SOURCE_FOLDER` exists.
2. Count supported images and estimate total size.
3. Smoke-test with `--limit 20` (or similar) on large folders.
4. Open / summarize `culling-report.html` (and CSV if needed).
5. If scores look reasonable, run the full folder.
6. Report paths to HTML, CSV, and optional `keepers/` / `rejects/`.
7. Do **not** delete rejects automatically.
8. If the user is preparing the website, recommend next step: compress keepers with **compress-photo**, then update gallery data via **gallery-photo-pipeline**.

## Output Files

```text
OUTPUT_FOLDER/
  culling-report.html
  culling-report.csv
  thumbs/                 # report previews
  keepers/                # optional, with --copy-keepers
  rejects/                # optional, with --copy-rejects
```

Suggested output root: `culling/<source-folder-name>/` under the workspace or a user-chosen sibling folder.

## Report Interpretation

| Label | Meaning |
|-------|---------|
| `keeper` | Strongest technical score, or best frame in a similar group |
| `review` | Usable; needs human judgment |
| `reject` | Likely blurry, weak technical score, or weaker duplicate |

## Important Caveat

The algorithm cannot fully judge:

- Facial expression and eye contact
- Storytelling / peak action moment
- Emotional value
- Composition taste
- Client or brand preference

Always frame results as a **first-pass assistant**, not final selects.

## Safety Rules

- Non-destructive by default
- No automatic deletion of rejects
- Prefer copying keepers over moving originals
- On large folders, smoke-test before full runs
- Use longer timeouts for thousands of files
- If disk space is tight, skip `--copy-rejects` and rely on the report

## Anti-patterns

- Hardcoding `C:\Users\...` paths into the skill or commands
- Deleting rejects without an explicit user request
- Skipping the smoke test on 1k+ image folders
- Publishing unreviewed “keepers” straight to production without a human glance
- Using cull scores alone to pick hero/cover images
