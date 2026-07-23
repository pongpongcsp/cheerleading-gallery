#!/usr/bin/env python3
"""Non-destructive first-pass photo culling with HTML/CSV reports."""

from __future__ import annotations

import argparse
import csv
import html
import shutil
import sys
from collections import defaultdict
from pathlib import Path

try:
    from PIL import Image, ImageFilter, ImageOps, ImageStat
except ImportError:
    print("Pillow is required. Install with: pip install pillow", file=sys.stderr)
    sys.exit(1)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}


def iter_images(source: Path, limit: int | None):
    files = [
        p for p in sorted(source.rglob("*"))
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    ]
    if limit:
        files = files[:limit]
    return files


def dhash(im: Image.Image, hash_size: int = 8) -> int:
    gray = im.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
    if hasattr(gray, "get_flattened_data"):
        pixels = list(gray.get_flattened_data())
    else:
        pixels = list(gray.getdata())
    bits = 0
    bit = 0
    for row in range(hash_size):
        row_start = row * (hash_size + 1)
        for col in range(hash_size):
            left = pixels[row_start + col]
            right = pixels[row_start + col + 1]
            if left > right:
                bits |= 1 << bit
            bit += 1
    return bits


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def score_image(path: Path) -> dict:
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        w, h = im.size
        sample = im.copy()
        sample.thumbnail((512, 512), Image.Resampling.BILINEAR)
        gray = sample.convert("L")

        # Variance of FIND_EDGES response — portable blur proxy
        edges = gray.filter(ImageFilter.FIND_EDGES)
        sharpness = ImageStat.Stat(edges).stddev[0] ** 2
        brightness = ImageStat.Stat(gray).mean[0]
        contrast = ImageStat.Stat(gray).stddev[0]
        hist = gray.histogram()
        total = sum(hist) or 1
        clip_low = sum(hist[:5]) / total
        clip_high = sum(hist[-5:]) / total
        clipping = clip_low + clip_high
        hash_val = dhash(sample)

    sharp_score = max(0.0, min(45.0, (sharpness ** 0.5) * 3.5))
    contrast_score = max(0.0, min(25.0, contrast))
    bright_penalty = abs(brightness - 128) / 128 * 20
    clip_penalty = min(25.0, clipping * 100)
    score = max(0.0, sharp_score + contrast_score + 20 - bright_penalty - clip_penalty)

    return {
        "path": path,
        "width": w,
        "height": h,
        "sharpness": round(sharpness, 2),
        "brightness": round(brightness, 2),
        "contrast": round(contrast, 2),
        "clipping": round(clipping, 4),
        "score": round(score, 2),
        "dhash": hash_val,
    }


def group_similar(rows: list[dict], threshold: int) -> list[list[dict]]:
    groups: list[list[dict]] = []
    used = set()
    for i, row in enumerate(rows):
        if i in used:
            continue
        group = [row]
        used.add(i)
        for j in range(i + 1, len(rows)):
            if j in used:
                continue
            if hamming(row["dhash"], rows[j]["dhash"]) <= threshold:
                group.append(rows[j])
                used.add(j)
        groups.append(group)
    return groups


def label_rows(
    rows: list[dict],
    similar_threshold: int,
    review_percent: float,
    max_keepers: int = 0,
) -> list[dict]:
    if not rows:
        return []

    sharp_values = sorted(r["sharpness"] for r in rows)
    blur_cutoff = sharp_values[max(0, int(len(sharp_values) * 0.15) - 1)]
    median_sharp = sharp_values[len(sharp_values) // 2]

    groups = group_similar(rows, similar_threshold)
    labeled = []
    for group in groups:
        ranked = sorted(group, key=lambda r: r["score"], reverse=True)
        best = ranked[0]
        for idx, row in enumerate(ranked):
            item = dict(row)
            item["group_size"] = len(group)

            very_blurry = row["sharpness"] < max(median_sharp * 0.12, 1e-6)
            is_blurry = (
                very_blurry
                or (
                    row["sharpness"] <= blur_cutoff
                    and row["sharpness"] < max(best["sharpness"] * 0.55, 1e-6)
                )
            )
            if is_blurry and (very_blurry or len(group) == 1 or idx > 0 or row["score"] < 35):
                item["suggestion"] = "reject"
                item["reason"] = "likely blurry vs batch"
            elif idx == 0:
                # Best in group is a candidate; weaker duplicates are reject
                item["suggestion"] = "keeper"
                item["reason"] = "best in similar group" if len(group) > 1 else "strong technical score"
            elif best["score"] - row["score"] >= 6 or row["score"] < best["score"] * 0.85:
                item["suggestion"] = "reject"
                item["reason"] = "weaker duplicate or low score"
            else:
                item["suggestion"] = "review"
                item["reason"] = "similar alternative"
            labeled.append(item)

    # Optional soft demotion when no hard max-keepers cap
    keepers = [r for r in labeled if r["suggestion"] == "keeper"]
    if not max_keepers and keepers and review_percent > 0 and len(keepers) > 1:
        ranked_scores = sorted((r["score"] for r in keepers), reverse=True)
        keep_n = max(1, int(round(len(ranked_scores) * (1 - review_percent))))
        keep_cutoff = ranked_scores[keep_n - 1]
        for row in labeled:
            if row["suggestion"] == "keeper" and row["group_size"] == 1 and row["score"] < keep_cutoff:
                row["suggestion"] = "review"
                row["reason"] = "borderline solo shot"

    # Hard top-N budget for Cloudinary / friend sharing
    if max_keepers and max_keepers > 0:
        ranked_keepers = sorted(
            [r for r in labeled if r["suggestion"] == "keeper"],
            key=lambda r: r["score"],
            reverse=True,
        )
        keep_set = {id(r) for r in ranked_keepers[:max_keepers]}
        for row in labeled:
            if row["suggestion"] == "keeper" and id(row) not in keep_set:
                row["suggestion"] = "review"
                row["reason"] = f"outside top {max_keepers} keepers"

    labeled.sort(key=lambda r: (-{"keeper": 2, "review": 1, "reject": 0}[r["suggestion"]], -r["score"]))
    return labeled


def write_csv(path: Path, rows: list[dict], source: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "file", "suggestion", "reason", "score", "sharpness",
                "brightness", "contrast", "clipping", "width", "height", "group_size",
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
                "brightness": row["brightness"],
                "contrast": row["contrast"],
                "clipping": row["clipping"],
                "width": row["width"],
                "height": row["height"],
                "group_size": row["group_size"],
            })


def write_html(path: Path, rows: list[dict], source: Path, thumbs_dir: Path) -> None:
    counts = defaultdict(int)
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
                <span>score {row['score']} · sharp {row['sharpness']} · group {row['group_size']}</span>
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
    <p>Suggestions only — review keepers manually before publishing.</p>
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


def copy_selection(rows: list[dict], suggestion: str, source: Path, dest: Path) -> int:
    count = 0
    for row in rows:
        if row["suggestion"] != suggestion:
            continue
        rel = row["path"].relative_to(source)
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(row["path"], out)
        count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument("--similar-threshold", type=int, default=8)
    parser.add_argument("--review-percent", type=float, default=0.30)
    parser.add_argument(
        "--max-keepers",
        type=int,
        default=50,
        help="Hard cap of keeper photos after de-dupe (0 = no hard cap). Default: 50",
    )
    parser.add_argument("--copy-keepers", action="store_true")
    parser.add_argument("--copy-rejects", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if not source.is_dir():
        print(f"Source folder not found: {source}", file=sys.stderr)
        return 1

    files = iter_images(source, args.limit or None)
    if not files:
        print(f"No images found in {source}", file=sys.stderr)
        return 1

    print(f"Scoring {len(files)} images from {source} ...")
    if args.max_keepers:
        print(f"Max keepers: {args.max_keepers}")
    rows = []
    for i, path in enumerate(files, 1):
        try:
            rows.append(score_image(path))
        except Exception as exc:  # noqa: BLE001
            print(f"  skip {path.name}: {exc}", file=sys.stderr)
        if i % 25 == 0 or i == len(files):
            print(f"  {i}/{len(files)}")

    labeled = label_rows(
        rows,
        args.similar_threshold,
        args.review_percent,
        max_keepers=args.max_keepers,
    )
    output.mkdir(parents=True, exist_ok=True)
    thumbs = output / "thumbs"

    for row in labeled:
        rel = row["path"].relative_to(source)
        thumb_path = thumbs / f"{rel.as_posix().replace('/', '__')}.jpg"
        try:
            make_thumb(row["path"], thumb_path)
        except Exception as exc:  # noqa: BLE001
            print(f"  thumb failed {rel}: {exc}", file=sys.stderr)

    write_csv(output / "culling-report.csv", labeled, source)
    write_html(output / "culling-report.html", labeled, source, thumbs)

    if args.copy_keepers:
        n = copy_selection(labeled, "keeper", source, output / "keepers")
        print(f"Copied keepers: {n}")
    if args.copy_rejects:
        n = copy_selection(labeled, "reject", source, output / "rejects")
        print(f"Copied rejects: {n}")

    counts = defaultdict(int)
    for row in labeled:
        counts[row["suggestion"]] += 1
    print()
    print(f"Report: {output / 'culling-report.html'}")
    print(f"keepers {counts['keeper']} · review {counts['review']} · reject {counts['reject']}")
    print("Suggestions only — review before publishing.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
