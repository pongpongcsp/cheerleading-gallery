#!/usr/bin/env python3
"""Build review thumbs + numbered contact sheets. Originals are never modified."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps, ImageStat

EXTS = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff", ".heic", ".dng"}
COLS, ROWS = 4, 4
CELL = 420
LABEL_H = 36
PAD = 8
PER = COLS * ROWS


def laplacian_var(im: Image.Image) -> float:
    g = im.convert("L").resize((320, 320), Image.Resampling.BILINEAR)
    edges = g.filter(ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1))
    return float(ImageStat.Stat(edges).var[0])


def font(size: int) -> ImageFont.ImageFont:
    for p in (
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\arial.ttf",
        r"C:\Windows\Fonts\segoeui.ttf",
    ):
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def write_sheet(sheets: Path, chunk: list, sheet_idx: int, n_sheets: int, fnt_sm, pad: int) -> None:
    sheet_w = COLS * CELL
    sheet_h = ROWS * (CELL + LABEL_H)
    sheet = Image.new("RGB", (sheet_w, sheet_h), (245, 240, 232))
    draw = ImageDraw.Draw(sheet)
    for j, (idx, name, preview, sharp, w, h, _thumb) in enumerate(chunk):
        r, c = divmod(j, COLS)
        x = c * CELL
        y = r * (CELL + LABEL_H)
        draw.rectangle([x, y, x + CELL - 1, y + CELL + LABEL_H - 1], outline=(200, 196, 188))
        px = x + (CELL - preview.width) // 2
        py = y + (CELL - preview.height) // 2
        sheet.paste(preview, (px, py))
        label = f"{idx:04d} {name}  {w}x{h}  s{int(sharp)}"
        draw.text((x + 6, y + CELL + 8), label, fill=(40, 40, 40), font=fnt_sm)
    out = sheets / f"sheet-{sheet_idx:0{pad}d}-of-{n_sheets:0{pad}d}.jpg"
    sheet.save(out, format="JPEG", quality=85, optimize=True)
    print(f"wrote {out.name}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("output")
    args = parser.parse_args()
    source = Path(args.source).expanduser().resolve()
    out = Path(args.output).expanduser().resolve()
    if not source.is_dir():
        raise SystemExit(f"Source folder not found: {source}")

    thumbs = out / "thumbs"
    sheets = out / "sheets"
    files = sorted(p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in EXTS)
    thumbs.mkdir(parents=True, exist_ok=True)
    sheets.mkdir(parents=True, exist_ok=True)
    fnt_sm = font(14)
    n_sheets = (len(files) + PER - 1) // PER
    pad = max(2, len(str(n_sheets)))
    print(f"photos={len(files)} sheets={n_sheets} source={source}", flush=True)

    index = []
    chunk: list = []
    sheet_idx = 1
    for i, path in enumerate(files, 1):
        rel = path.relative_to(source)
        thumb_name = f"{rel.as_posix().replace('/', '__')}.jpg"
        thumb_path = thumbs / thumb_name
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im)
            w, h = im.size
            sharp = round(laplacian_var(im), 1)
            preview = im.copy()
            preview.thumbnail((CELL - PAD * 2, CELL - PAD * 2 - 4), Image.Resampling.LANCZOS)
            if preview.mode not in ("RGB", "L"):
                preview = preview.convert("RGB")
            elif preview.mode == "L":
                preview = preview.convert("RGB")
            if not thumb_path.exists():
                web = im.copy()
                web.thumbnail((360, 360), Image.Resampling.LANCZOS)
                if web.mode not in ("RGB", "L"):
                    web = web.convert("RGB")
                web.save(thumb_path, format="JPEG", quality=75, optimize=True)
        chunk.append((i, path.name, preview, sharp, w, h, thumb_name))
        index.append(
            {
                "i": i,
                "file": rel.as_posix(),
                "width": w,
                "height": h,
                "mp": round(w * h / 1_000_000, 2),
                "sharp": sharp,
                "thumb": thumb_name,
            }
        )
        if len(chunk) == PER:
            write_sheet(sheets, chunk, sheet_idx, n_sheets, fnt_sm, pad)
            sheet_idx += 1
            chunk = []
        if i % 50 == 0 or i == len(files):
            print(f"prepared {i}/{len(files)}", flush=True)

    if chunk:
        write_sheet(sheets, chunk, sheet_idx, n_sheets, fnt_sm, pad)

    (out / "review-index.json").write_text(
        json.dumps({"source": str(source), "count": len(index), "photos": index}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"DONE {source.name} photos={len(index)} sheets={n_sheets}", flush=True)


if __name__ == "__main__":
    main()
