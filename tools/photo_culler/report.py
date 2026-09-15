"""HTML/CSV reports and thumbnail generation."""

from __future__ import annotations

import csv
import html
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageOps


def write_csv(path: Path, rows: list[dict], source: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "file",
                "suggestion",
                "reason",
                "score",
                "sharpness",
                "sharpness_score",
                "brightness",
                "lighting_score",
                "pose_conf",
                "pose_score",
                "person_count",
                "has_subject",
                "occlusion_penalty",
                "occlusion_reason",
                "width",
                "height",
                "group_size",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "file": str(row["path"].relative_to(source)),
                "suggestion": row["suggestion"],
                "reason": row["reason"],
                "score": row["score"],
                "sharpness": row["sharpness"],
                "sharpness_score": row.get("sharpness_score", ""),
                "brightness": row.get("brightness", ""),
                "lighting_score": row.get("lighting_score", ""),
                "pose_conf": row.get("pose_conf", ""),
                "pose_score": row.get("pose_score", ""),
                "person_count": row.get("person_count", 0),
                "has_subject": row.get("has_subject", False),
                "occlusion_penalty": row.get("occlusion_penalty", 0),
                "occlusion_reason": row.get("occlusion_reason", ""),
                "width": row["width"],
                "height": row["height"],
                "group_size": row["group_size"],
            })


def write_html(path: Path, rows: list[dict], source: Path, thumbs_dir: Path) -> None:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row["suggestion"]] += 1

    cards = []
    for row in rows:
        rel = row["path"].relative_to(source)
        thumb_rel = Path("thumbs") / f"{rel.as_posix().replace('/', '__')}.jpg"
        cards.append(
            f"""
            <article class="card {html.escape(row['suggestion'])}">
              <img src="{html.escape(thumb_rel.as_posix())}" loading="lazy" alt="">
              <div class="meta">
                <strong>{html.escape(row['suggestion'].upper())}</strong>
                <span>{html.escape(str(rel))}</span>
                <span>score {row['score']} · sharp {row['sharpness']} · pose {row.get('pose_conf', 0)} · occ −{row.get('occlusion_penalty', 0)} · light {row.get('lighting_score', '')} · group {row['group_size']}</span>
                <em>{html.escape(row['reason'])}</em>
              </div>
            </article>
            """
        )

    doc = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Culling Report</title>
  <style>
    :root {{ color-scheme: dark; font-family: system-ui, sans-serif; }}
    body {{ margin: 0; background: #111; color: #eee; }}
    header {{ padding: 24px; border-bottom: 1px solid #333; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 16px; padding: 24px; }}
    .card {{ background: #1b1b1b; border: 1px solid #333; border-radius: 10px; overflow: hidden; }}
    .card img {{ width: 100%; aspect-ratio: 1; object-fit: cover; display: block; background: #000; }}
    .meta {{ padding: 10px; display: grid; gap: 4px; font-size: 12px; }}
    .keeper {{ border-color: #3d8f5a; }}
    .review {{ border-color: #b8973b; }}
    .reject {{ border-color: #8a3d3d; opacity: 0.85; }}
  </style>
</head>
<body>
  <header>
    <h1>Culling Report</h1>
    <p>Source: {html.escape(str(source))}</p>
    <p>keepers {counts['keeper']} · review {counts['review']} · reject {counts['reject']} · total {len(rows)}</p>
    <p>4D score: Laplacian sharpness · HSV lighting · YOLOv8 pose (frontal/side/back) · audience occlusion.</p>
    <p>No hard keeper cap — skim keepers manually before publishing (Cloudinary cost scales with volume).</p>
  </header>
  <div class="grid">
    {''.join(cards)}
  </div>
</body>
</html>
"""
    path.write_text(doc, encoding="utf-8")


def make_thumb(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        im.thumbnail((360, 360), Image.Resampling.LANCZOS)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        im.save(dst, format="JPEG", quality=75, optimize=True)
