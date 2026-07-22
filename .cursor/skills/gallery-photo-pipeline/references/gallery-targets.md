# Gallery Image Targets

Numeric targets for publishing into `cheerleading-gallery` (GitHub Pages).

## Formats

| Preference | Format | Notes |
|------------|--------|-------|
| Default today | Progressive JPEG | Matches current site; widest compatibility |
| Better size | WebP | Prefer when updating `app.js` / HTML to serve WebP with JPEG fallback |
| Avoid in repo | PNG (photos), TIFF, HEIC, RAW | Convert before publish |

## Dimensions & Quality

| Asset | Max long edge | Quality | Target average size |
|-------|---------------|---------|---------------------|
| Masonry thumb | 640 px | JPEG 78–80 / WebP 75–78 | 40–120 KB |
| Lightbox display | 1920 px | JPEG 80–85 / WebP 78–82 | 150–400 KB |
| Rare hero/cover | 2400 px | JPEG ≤ 85 | ≤ 600 KB |

## Repo Budget Heuristics

- Prefer shoots that add **under ~30–50 MB** of new web images per commit when possible
- If a single event would add **> 100 MB**, discuss external hosting before committing
- Camera originals and cull working folders stay **outside** this git repo

## Category Keys

Must match `index.html` tab `data-category` values:

| `category` | Tab label |
|------------|-----------|
| `competition` | 2024 全國賽 |
| `campus` | 校園寫真 |
| `commercial` | 商業拍攝 |
| `behind` | 幕後花絮 |

## Filename Pattern

```text
YYYYMMDD-short-slug-###.jpg
```

Examples:

```text
20250810-taipei-dome-001.jpg
20250810-taipei-dome-001.thumb.jpg
```

Use ASCII slugs in filenames for fewer URL/encoding issues; keep Chinese in `title` / `tags` / `categoryLabel`.
