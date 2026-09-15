#!/usr/bin/env python3
"""Non-destructive AI photo culling via PixCull CLI (offline).

Default path: ``pixcull run`` → map keep/maybe/cull → keepers/ + HTML/CSV report.
Never moves or deletes originals — copy keepers only.

Security: offline CLI only. Do not use ``pixcull serve``, LAN bind, share links,
or DeepSeek for gallery publish.

Legacy 4D culler: ``--legacy`` (requires opencv + ultralytics).
"""

from __future__ import annotations

import argparse
import csv
import html
import os
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageOps

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".heic", ".dng"}

# PixCull decision → gallery suggestion
_DECISION_MAP = {
    "keep": "keeper",
    "maybe": "review",
    "cull": "reject",
}


def iter_images(source: Path, limit: int | None) -> list[Path]:
    files = [
        p
        for p in sorted(source.rglob("*"))
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS
    ]
    if limit:
        files = files[:limit]
    return files


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


def make_thumb(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        im.thumbnail((360, 360), Image.Resampling.LANCZOS)
        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")
        im.save(dst, format="JPEG", quality=75, optimize=True)


def stage_limited_source(source: Path, files: list[Path], staging: Path) -> None:
    """Hardlink (or copy) limited files into staging, preserving relative paths."""
    for path in files:
        rel = path.relative_to(source)
        dest = staging / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            continue
        try:
            os.link(path, dest)
        except OSError:
            shutil.copy2(path, dest)


def resolve_pixcull_cmd() -> list[str]:
    """Prefer same-interpreter ``python -m pixcull``; fall back to PATH console script."""
    probe = subprocess.run(
        [sys.executable, "-m", "pixcull", "--help"],
        capture_output=True,
        text=True,
    )
    if probe.returncode == 0:
        return [sys.executable, "-m", "pixcull"]
    which = shutil.which("pixcull")
    if which:
        return [which]
    print(
        "PixCull is not installed for this Python.\n"
        "  pip install -r requirements.txt\n"
        "Requires Python 3.11 or 3.12.",
        file=sys.stderr,
    )
    raise SystemExit(1)


def run_pixcull(input_dir: Path, pix_out: Path, scene: str, strictness: str) -> Path:
    pix_out.mkdir(parents=True, exist_ok=True)
    cmd = resolve_pixcull_cmd() + [
        "run",
        str(input_dir),
        "-o",
        str(pix_out),
        "--scene",
        scene,
        "--strictness",
        strictness,
    ]
    print(f"$ {' '.join(cmd)}")
    # PixCull opens YAML templates with open() and no encoding=; on Windows
    # the locale codec (e.g. cp950) breaks UTF-8 Chinese in scene templates.
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    result = subprocess.run(cmd, env=env)
    if result.returncode != 0:
        print(f"pixcull run failed with exit code {result.returncode}", file=sys.stderr)
        raise SystemExit(result.returncode or 1)
    scores = pix_out / "scores.csv"
    if not scores.is_file():
        print(f"Expected scores.csv missing: {scores}", file=sys.stderr)
        raise SystemExit(1)
    return scores


def _cell(row: dict, *names: str, default: str = "") -> str:
    for name in names:
        if name in row and row[name] not in (None, ""):
            return str(row[name]).strip()
    return default


def load_pixcull_rows(scores_csv: Path, source: Path) -> list[dict]:
    """Parse PixCull scores.csv into gallery row dicts keyed to source paths."""
    rows: list[dict] = []
    with scores_csv.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            decision = _cell(raw, "decision").lower()
            suggestion = _DECISION_MAP.get(decision, "review")
            path_raw = _cell(raw, "path", "filepath", "file")
            filename = _cell(raw, "filename", "file", "name")

            resolved: Path | None = None
            if path_raw:
                candidate = Path(path_raw)
                if candidate.is_file():
                    resolved = candidate.resolve()
                else:
                    # Relative to source
                    under = (source / path_raw).resolve()
                    if under.is_file():
                        resolved = under

            if resolved is None and filename:
                # Basename search under source (handles staging / absolute mismatch)
                matches = list(source.rglob(filename))
                if len(matches) == 1:
                    resolved = matches[0].resolve()
                elif len(matches) > 1:
                    # Prefer exact relative match if path_raw looks like a relative path
                    for m in matches:
                        try:
                            m.relative_to(source)
                            resolved = m.resolve()
                            break
                        except ValueError:
                            continue
                    if resolved is None:
                        resolved = matches[0].resolve()

            if resolved is None or not resolved.is_file():
                print(f"  skip unresolved row: {path_raw or filename}", file=sys.stderr)
                continue

            try:
                score = float(_cell(raw, "score_final", "score", default="0") or 0)
            except ValueError:
                score = 0.0

            reason_bits = [
                f"pixcull:{decision or 'unknown'}",
            ]
            for axis in (
                "score_technical",
                "score_subject",
                "score_composition",
                "score_light",
                "score_moment",
                "score_aesthetic",
                "technical",
                "subject",
                "composition",
                "light",
                "moment",
                "aesthetic",
            ):
                val = _cell(raw, axis)
                if val:
                    reason_bits.append(f"{axis}={val}")

            rows.append(
                {
                    "path": resolved,
                    "suggestion": suggestion,
                    "reason": " · ".join(reason_bits[:8]),
                    "score": round(score, 4),
                    "decision": decision,
                    "width": _cell(raw, "width", default=""),
                    "height": _cell(raw, "height", default=""),
                    "group_size": 1,
                    "sharpness": "",
                    "pose_conf": "",
                    "occlusion_penalty": "",
                    "lighting_score": "",
                }
            )
    return rows


def apply_max_keepers(rows: list[dict], max_keepers: int) -> list[dict]:
    """Keep-only set; optional hard top-N by PixCull score_final."""
    if not max_keepers or max_keepers <= 0:
        return rows
    keepers = [r for r in rows if r["suggestion"] == "keeper"]
    if len(keepers) <= max_keepers:
        return rows
    ranked = sorted(keepers, key=lambda r: r["score"], reverse=True)
    keep_ids = {id(r) for r in ranked[:max_keepers]}
    for row in rows:
        if row["suggestion"] == "keeper" and id(row) not in keep_ids:
            row["suggestion"] = "review"
            row["reason"] = f"outside top {max_keepers} keepers · {row['reason']}"
    return rows


def write_csv(path: Path, rows: list[dict], source: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "file",
                "suggestion",
                "reason",
                "score",
                "decision",
                "width",
                "height",
            ],
        )
        writer.writeheader()
        for row in rows:
            try:
                rel = str(row["path"].relative_to(source))
            except ValueError:
                rel = row["path"].name
            writer.writerow(
                {
                    "file": rel,
                    "suggestion": row["suggestion"],
                    "reason": row["reason"],
                    "score": row["score"],
                    "decision": row.get("decision", ""),
                    "width": row.get("width", ""),
                    "height": row.get("height", ""),
                }
            )


def write_html(path: Path, rows: list[dict], source: Path, thumbs_dir: Path) -> None:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[row["suggestion"]] += 1

    cards = []
    for row in rows:
        try:
            rel = row["path"].relative_to(source)
        except ValueError:
            rel = Path(row["path"].name)
        thumb_rel = Path("thumbs") / f"{rel.as_posix().replace('/', '__')}.jpg"
        cards.append(
            f"""
            <article class="card {html.escape(row['suggestion'])}">
              <img src="{html.escape(thumb_rel.as_posix())}" loading="lazy" alt="">
              <div class="meta">
                <strong>{html.escape(row['suggestion'].upper())}</strong>
                <span>{html.escape(str(rel))}</span>
                <span>score {row['score']} · pixcull {html.escape(str(row.get('decision', '')))}</span>
                <em>{html.escape(row['reason'])}</em>
              </div>
            </article>
            """
        )

    cap_note = (
        "No hard keeper cap — skim keepers manually before publishing "
        "(Cloudinary cost scales with volume)."
        if counts["keeper"]
        else "No keepers selected."
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
    <p>Engine: PixCull offline CLI (keep → keeper, maybe → review, cull → reject).</p>
    <p>{html.escape(cap_note)}</p>
  </header>
  <div class="grid">
    {''.join(cards)}
  </div>
</body>
</html>
"""
    path.write_text(doc, encoding="utf-8")


def run_legacy(args: argparse.Namespace) -> int:
    """Previous 4D YOLO/OpenCV culler (quarantined behind --legacy)."""
    tools_dir = Path(__file__).resolve().parent
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    from photo_culler import label_rows, make_thumb as legacy_thumb  # noqa: E402
    from photo_culler import score_image, write_csv as legacy_csv  # noqa: E402
    from photo_culler import write_html as legacy_html  # noqa: E402

    source = Path(args.source).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if not source.is_dir():
        print(f"Source folder not found: {source}", file=sys.stderr)
        return 1

    files = iter_images(source, args.limit or None)
    if not files:
        print(f"No images found in {source}", file=sys.stderr)
        return 1

    print(f"[legacy] Scoring {len(files)} images from {source} ...")
    rows = []
    try:
        from tqdm import tqdm

        iterator = tqdm(files, unit="img")
    except ImportError:
        iterator = files

    for i, path in enumerate(iterator, 1):
        try:
            rows.append(score_image(path))
        except Exception as exc:  # noqa: BLE001
            print(f"  skip {path.name}: {exc}", file=sys.stderr)
        if not hasattr(iterator, "update") and (i % 25 == 0 or i == len(files)):
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
            legacy_thumb(row["path"], thumb_path)
        except Exception as exc:  # noqa: BLE001
            print(f"  thumb failed {rel}: {exc}", file=sys.stderr)

    legacy_csv(output / "culling-report.csv", labeled, source)
    legacy_html(output / "culling-report.html", labeled, source, thumbs)

    if args.copy_keepers:
        n = copy_selection(labeled, "keeper", source, output / "keepers")
        print(f"Copied keepers: {n}")
    if args.copy_rejects:
        n = copy_selection(labeled, "reject", source, output / "rejects")
        print(f"Copied rejects: {n}")

    counts: dict[str, int] = defaultdict(int)
    for row in labeled:
        counts[row["suggestion"]] += 1
    print()
    print(f"Report: {output / 'culling-report.html'}")
    print(
        f"keepers {counts['keeper']} · review {counts['review']} · reject {counts['reject']}"
    )
    return 0


def run_pixcull_adapter(args: argparse.Namespace) -> int:
    source = Path(args.source).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()
    if not source.is_dir():
        print(f"Source folder not found: {source}", file=sys.stderr)
        return 1

    all_files = iter_images(source, None)
    if not all_files:
        print(f"No images found in {source}", file=sys.stderr)
        return 1

    files = all_files[: args.limit] if args.limit else all_files
    print(f"PixCull scoring {len(files)} images from {source} ...")
    if args.max_keepers:
        print(f"Max keepers: {args.max_keepers}")
    else:
        print("Max keepers: uncapped (PixCull keep decisions)")

    output.mkdir(parents=True, exist_ok=True)
    pix_out = output / "pixcull"
    staging_ctx = None
    input_dir = source

    try:
        if args.limit and args.limit < len(all_files):
            staging_ctx = tempfile.TemporaryDirectory(prefix="pixcull_limit_")
            staging = Path(staging_ctx.name)
            print(f"Staging limited set ({len(files)} files) → {staging}")
            stage_limited_source(source, files, staging)
            input_dir = staging

        scores_csv = run_pixcull(
            input_dir,
            pix_out,
            scene=args.scene,
            strictness=args.strictness,
        )
        # Resolve paths relative to the directory PixCull actually scanned
        rows = load_pixcull_rows(scores_csv, input_dir)

        # Remap staging paths back to the real source tree
        if input_dir != source:
            remapped = []
            for row in rows:
                try:
                    rel = row["path"].relative_to(input_dir)
                except ValueError:
                    remapped.append(row)
                    continue
                real = (source / rel).resolve()
                if real.is_file():
                    row["path"] = real
                    remapped.append(row)
                else:
                    print(f"  skip missing after remap: {rel}", file=sys.stderr)
            rows = remapped

        rows = apply_max_keepers(rows, args.max_keepers)

        thumbs = output / "thumbs"
        for row in rows:
            try:
                rel = row["path"].relative_to(source)
            except ValueError:
                rel = Path(row["path"].name)
            thumb_path = thumbs / f"{rel.as_posix().replace('/', '__')}.jpg"
            try:
                make_thumb(row["path"], thumb_path)
            except Exception as exc:  # noqa: BLE001
                print(f"  thumb failed {rel}: {exc}", file=sys.stderr)

        write_csv(output / "culling-report.csv", rows, source)
        write_html(output / "culling-report.html", rows, source, thumbs)

        if args.copy_keepers:
            n = copy_selection(rows, "keeper", source, output / "keepers")
            print(f"Copied keepers: {n}")
        if args.copy_rejects:
            n = copy_selection(rows, "reject", source, output / "rejects")
            print(f"Copied rejects: {n}")

        counts: dict[str, int] = defaultdict(int)
        for row in rows:
            counts[row["suggestion"]] += 1
        print()
        print(f"Report: {output / 'culling-report.html'}")
        print(f"PixCull run dir: {pix_out}")
        print(
            f"keepers {counts['keeper']} · review {counts['review']} · "
            f"reject {counts['reject']}"
        )
        print(
            "Suggestions only — review before publishing "
            "(non-destructive; originals untouched)."
        )
        return 0
    finally:
        if staging_ctx is not None:
            staging_ctx.cleanup()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument(
        "--similar-threshold",
        type=int,
        default=8,
        help="Legacy only: dHash similar-group threshold.",
    )
    parser.add_argument(
        "--review-percent",
        type=float,
        default=0.30,
        help="Legacy only: demote bottom percent of keepers to review.",
    )
    parser.add_argument(
        "--max-keepers",
        type=int,
        default=0,
        help="Optional hard cap of keepers (0 = no hard cap, default).",
    )
    parser.add_argument("--copy-keepers", action="store_true")
    parser.add_argument("--copy-rejects", action="store_true")
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Score only first N images (smoke test).",
    )
    parser.add_argument(
        "--scene",
        default="event",
        help="PixCull scene override (default: event). Ignored with --legacy.",
    )
    parser.add_argument(
        "--strictness",
        default="standard",
        choices=("strict", "standard", "lenient"),
        help="PixCull strictness (default: standard).",
    )
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Use retired 4D YOLO/OpenCV culler instead of PixCull.",
    )
    args = parser.parse_args()

    if args.legacy:
        return run_legacy(args)
    return run_pixcull_adapter(args)


if __name__ == "__main__":
    sys.exit(main())
