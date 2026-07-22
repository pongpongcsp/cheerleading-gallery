#!/usr/bin/env python3
"""Batch-compress JPG/JPEG photos for web galleries (non-destructive)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    from PIL import Image, ImageOps
except ImportError:
    print("Pillow is required. Install with: pip install pillow", file=sys.stderr)
    sys.exit(1)

IMAGE_EXTS = {".jpg", ".jpeg"}


def iter_images(source: Path):
    for path in sorted(source.rglob("*")):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            yield path


def human_size(num: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    size = float(num)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{num} B"


def compress_one(
    src: Path,
    dst: Path,
    quality: int,
    max_edge: int,
    progressive: bool,
) -> tuple[int, int]:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() and dst.stat().st_size > 0:
        return src.stat().st_size, dst.stat().st_size

    with Image.open(src) as im:
        im = ImageOps.exif_transpose(im)
        if max_edge and max(im.size) > max_edge:
            im.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)

        save_kwargs = {
            "format": "JPEG",
            "quality": quality,
            "optimize": True,
            "progressive": progressive,
            "subsampling": 0,
        }

        exif = im.info.get("exif")
        if exif:
            save_kwargs["exif"] = exif
        icc = im.info.get("icc_profile")
        if icc:
            save_kwargs["icc_profile"] = icc

        if im.mode not in ("RGB", "L"):
            im = im.convert("RGB")

        im.save(dst, **save_kwargs)

    return src.stat().st_size, dst.stat().st_size


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source")
    parser.add_argument("output")
    parser.add_argument("--quality", type=int, default=85)
    parser.add_argument("--max-edge", type=int, default=2000)
    parser.add_argument("--no-progressive", action="store_true")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    output = Path(args.output).expanduser().resolve()

    if not source.is_dir():
        print(f"Source folder not found: {source}", file=sys.stderr)
        return 1

    files = list(iter_images(source))
    if not files:
        print(f"No JPG/JPEG files found in {source}", file=sys.stderr)
        return 1

    original_total = 0
    compressed_total = 0
    written = 0

    print(f"Source : {source}")
    print(f"Output : {output}")
    print(f"Files  : {len(files)}")
    print(f"Quality: {args.quality}  max-edge: {args.max_edge}")
    print()

    for src in files:
        rel = src.relative_to(source)
        dst = output / rel
        before, after = compress_one(
            src,
            dst,
            quality=args.quality,
            max_edge=args.max_edge,
            progressive=not args.no_progressive,
        )
        original_total += before
        compressed_total += after
        written += 1
        saved = (1 - after / before) * 100 if before else 0
        print(f"  {rel}  {human_size(before)} → {human_size(after)}  ({saved:.0f}% saved)")

    zero_byte = [p for p in iter_images(output) if p.stat().st_size == 0]
    print()
    print(f"Done: {written}/{len(files)} files")
    print(f"Original  : {human_size(original_total)}")
    print(f"Compressed: {human_size(compressed_total)}")
    if original_total:
        print(f"Saved     : {human_size(original_total - compressed_total)} ({(1 - compressed_total / original_total) * 100:.1f}%)")
    if zero_byte:
        print(f"WARNING: {len(zero_byte)} zero-byte outputs", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
