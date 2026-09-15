#!/usr/bin/env python3
"""Add exposure, in-focus people, and face-coverage metrics. Originals never modified."""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps, ImageStat

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.photo_culler.lighting import lighting_stats
from tools.photo_culler.occlusion import audience_shadow_score
from tools.photo_culler.pose_detector import detect_pose

try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover
    def tqdm(it, **_kw):  # type: ignore[misc]
        return it

PERSON_CONF = 0.40
MIN_AREA_RATIO = 0.025
FACE_DET = 0.62
SHARP_OK = 90.0
SUBJECT_SHARP_OK = 80.0
FACE_CROP_OK = 40.0
BURST_KEEP = 5
BURST_GAP_SEC = 3.0
MIN_FOLDER_KEEP = 50
OCCLUDED = {"前景遮擋"}
REJECT_CAPS = {
    "動作重複",
    "連拍組最高分",
    "連拍組前五",
    "五官不清",
    "失焦",
    "過暗",
    "過曝",
    "前景遮擋",
    "",
}

_FACE_APP = None


def face_app():
    """InsightFace detector + 5-point landmarks (eyes, nose, mouth corners)."""
    global _FACE_APP
    if _FACE_APP is None:
        from insightface.app import FaceAnalysis

        app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        app.prepare(ctx_id=-1, det_size=(640, 640))
        _FACE_APP = app
    return _FACE_APP


def features_ok_face(face, img_w: int, img_h: int) -> bool:
    """True only when 五官 are actually readable: both eyes, nose, mouth."""
    if float(getattr(face, "det_score", 0)) < FACE_DET:
        return False
    kps = getattr(face, "kps", None)
    if kps is None or len(kps) < 5:
        return False
    le, re, nose, lm, rm = (kps[i] for i in range(5))
    # Profile / back: eyes must sit on opposite sides of the nose.
    if not (float(le[0]) + 3.0 < float(nose[0]) < float(re[0]) - 3.0):
        return False
    eye_w = float(re[0]) - float(le[0])
    if eye_w < 14.0:
        return False
    if abs(float(le[1]) - float(re[1])) > eye_w * 0.35:
        return False
    # Nose must sit near the midpoint of the eyes — rejects strong side views.
    mid_x = (float(le[0]) + float(re[0])) / 2.0
    if abs(float(nose[0]) - mid_x) > eye_w * 0.20:
        return False
    mouth_w = abs(float(rm[0]) - float(lm[0]))
    if mouth_w < eye_w * 0.45:
        return False
    mouth_y = (float(lm[1]) + float(rm[1])) / 2.0
    if mouth_y <= float(nose[1]) + 3.0:
        return False
    bbox = getattr(face, "bbox", None)
    if bbox is None or len(bbox) < 4:
        return False
    x1, y1, x2, y2 = (float(v) for v in bbox[:4])
    if (x2 - x1) < 32.0 or (y2 - y1) < 32.0:
        return False
    for x, y in (le, re, nose, lm, rm):
        if float(x) < 4 or float(y) < 4 or float(x) > img_w - 4 or float(y) > img_h - 4:
            return False
    return True


def primary_features_ok(persons, faces, img_w: int, img_h: int) -> tuple[bool, int]:
    """Main in-focus person must show 五官. Ignore background faces."""
    good = [f for f in faces if features_ok_face(f, img_w, img_h)]
    if not persons:
        return (bool(good), len(good))
    primary = max(persons, key=lambda p: p.area_ratio)
    x1, y1, x2, y2 = primary.xyxy
    pw = max(1.0, x2 - x1)
    ph = max(1.0, y2 - y1)
    head_y2 = y1 + ph * 0.45
    matched = 0
    for face in good:
        fx1, fy1, fx2, fy2 = (float(v) for v in face.bbox[:4])
        cx = (fx1 + fx2) / 2.0
        cy = (fy1 + fy2) / 2.0
        fw = fx2 - fx1
        # Face must sit on the primary subject's head, not a crowd face in the same box.
        if not (x1 + pw * 0.12 <= cx <= x2 - pw * 0.12):
            continue
        if not (y1 - 8 <= cy <= head_y2):
            continue
        if fw < max(32.0, pw * 0.12):
            continue
        matched += 1
    return (matched > 0, matched)


def people_group(n: int) -> str:
    if n <= 0:
        return "無人"
    if n == 1:
        return "1人"
    if n <= 5:
        return "2-5人"
    return "5人以上"


def exposure_label(mean_v: float, highlight_clip: float, shadow_clip: float) -> str:
    if highlight_clip >= 8.0 or mean_v >= 200:
        return "過曝"
    if shadow_clip >= 12.0 or mean_v < 50:
        return "過暗"
    if mean_v < 75:
        return "偏暗"
    if mean_v > 175:
        return "偏亮"
    return "正常"


def laplacian_var(im: Image.Image) -> float:
    g = im.convert("L")
    if max(g.size) > 320:
        g = g.resize((320, 320), Image.Resampling.BILINEAR)
    elif min(g.size) < 16:
        return 0.0
    edges = g.filter(ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1))
    return float(ImageStat.Stat(edges).var[0])


def person_in_focus(person, frame: Image.Image, frame_sharp: float) -> bool:
    x1, y1, x2, y2 = person.xyxy
    w, h = frame.size
    ix1 = max(0, int(x1))
    iy1 = max(0, int(y1))
    ix2 = min(w, int(x2))
    iy2 = min(h, int(y2))
    if ix2 - ix1 < 12 or iy2 - iy1 < 12:
        return False
    crop = frame.crop((ix1, iy1, ix2, iy2))
    crop_sharp = laplacian_var(crop)
    floor = 40.0 if min(crop.size) < 80 else 55.0
    return crop_sharp >= max(floor, frame_sharp * 0.40)


def load_pixcull(out: Path) -> dict[str, dict]:
    path = out / "pixcull" / "scores.csv"
    rows: dict[str, dict] = {}
    if not path.is_file():
        return rows
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            name = (row.get("filename") or Path(row.get("path", "")).name).strip()
            if name:
                rows[name] = row
    return rows


def _face_crop_sharp(frame: Image.Image, faces, persons, img_w: int, img_h: int) -> float | None:
    box = None
    if faces:
        face = max(faces, key=lambda f: max(0.0, float(f.bbox[2] - f.bbox[0]) * float(f.bbox[3] - f.bbox[1])))
        box = [float(v) for v in face.bbox[:4]]
    elif persons:
        primary = max(persons, key=lambda p: p.area_ratio)
        x1, y1, x2, y2 = primary.xyxy
        box = [x1, y1, x2, y1 + max(16.0, (y2 - y1) * 0.42)]
    if not box:
        return None
    x1 = max(0, int(box[0]))
    y1 = max(0, int(box[1]))
    x2 = min(img_w, int(box[2]))
    y2 = min(img_h, int(box[3]))
    if x2 - x1 < 16 or y2 - y1 < 16:
        return None
    return laplacian_var(frame.crop((x1, y1, x2, y2)))


def photo_datetime(path: Path) -> datetime | None:
    if not path.is_file():
        return None
    try:
        with Image.open(path) as im:
            exif = im.getexif()
            raw = None
            if exif:
                raw = exif.get(306)
                try:
                    ifd = exif.get_ifd(0x8769)
                    raw = ifd.get(36867) or ifd.get(36868) or raw
                except Exception:  # noqa: BLE001
                    pass
            if raw:
                return datetime.strptime(str(raw).split(".")[0], "%Y:%m:%d %H:%M:%S")
    except Exception:  # noqa: BLE001
        return None
    return None


def assign_bursts(rows: list[dict], source: Path) -> int:
    """Group shots within 3 seconds. Skip if burst_id is already present."""
    have = sum(1 for r in rows if r.get("burst_id") not in (None, ""))
    if have >= max(1, len(rows) // 2):
        return 0
    timed: list[tuple[datetime, dict]] = []
    for lab in rows:
        dt = photo_datetime(source / lab["file"]) if source.is_dir() else None
        timed.append((dt or datetime.max, lab))
    timed.sort(key=lambda x: (x[0], x[1].get("file") or ""))
    bid = 0
    group: list[dict] = []
    prev: datetime | None = None

    def flush() -> None:
        nonlocal bid, group
        if not group:
            return
        bid += 1
        n = len(group)
        for i, lab in enumerate(group, 1):
            lab["burst_id"] = bid
            lab["burst_rank"] = i
            lab["burst_size"] = n
        group = []

    for dt, lab in timed:
        if prev is None or dt == datetime.max or prev == datetime.max or (dt - prev).total_seconds() > BURST_GAP_SEC:
            flush()
        group.append(lab)
        prev = dt
    flush()
    return bid


def _f(row: dict, key: str, default: float = 0.0) -> float:
    try:
        return float(row.get(key) or default)
    except (TypeError, ValueError):
        return default


def analyze_image(thumb_path: Path, pix: dict | None, frame_sharp: float | None) -> dict:
    with Image.open(thumb_path) as im:
        frame = ImageOps.exif_transpose(im).convert("RGB")
        rgb = np.asarray(frame)
    bgr = rgb[:, :, ::-1].copy()
    h, w = bgr.shape[:2]
    light = lighting_stats(bgr, is_bgr=True)
    mean_v = light["mean_v"]
    highlight = float(light["bright_ratio"]) * 100.0
    shadow_clip = float(light["dark_ratio"]) * 100.0
    score_exposure = None
    lap_subject = None
    if pix:
        if pix.get("mean_luma") not in (None, ""):
            mean_v = _f(pix, "mean_luma", mean_v)
        highlight = _f(pix, "highlight_clip_pct", highlight)
        shadow_clip = _f(pix, "shadow_clip_pct", shadow_clip)
        if pix.get("score_exposure") not in (None, ""):
            score_exposure = _f(pix, "score_exposure")
        if pix.get("laplacian_subject") not in (None, ""):
            lap_subject = _f(pix, "laplacian_subject")

    exp = exposure_label(mean_v, highlight, shadow_clip)
    sharp = float(frame_sharp) if frame_sharp not in (None, "") else laplacian_var(frame)
    pose = detect_pose(bgr)

    candidates = [
        p
        for p in pose.persons
        if p.conf >= PERSON_CONF and p.area_ratio >= MIN_AREA_RATIO
    ]
    in_focus = [p for p in candidates if person_in_focus(p, frame, sharp)]
    n = len(in_focus)
    try:
        faces = face_app().get(bgr)
    except Exception:  # noqa: BLE001
        faces = []
    features_ok, feature_count = primary_features_ok(in_focus, faces, w, h)
    face_zh = "五官可見" if features_ok else "五官不清"
    sharp_val = sharp
    face_sharp = _face_crop_sharp(frame, faces, in_focus, w, h)
    if lap_subject is None and face_sharp is not None:
        lap_subject = face_sharp
    shadow_info = audience_shadow_score(rgb, in_focus or candidates)

    return {
        "exposure": exp,
        "mean_luma": round(mean_v, 1),
        "highlight_clip_pct": round(highlight, 3),
        "shadow_clip_pct": round(shadow_clip, 3),
        "score_exposure": None if score_exposure is None else round(score_exposure, 3),
        "people_total": len(candidates),
        "people_in_focus": n,
        "people_group": people_group(n),
        "face_half": features_ok,
        "face_half_count": feature_count,
        "face_half_zh": face_zh,
        "features_ok": features_ok,
        "face_count": len(faces),
        "exposure_fail": exp in ("過暗", "過曝"),
        "face_fail": not features_ok,
        "sharp": round(float(sharp_val), 1),
        "laplacian_subject": None if lap_subject is None else round(lap_subject, 1),
        "face_sharp": None if face_sharp is None else round(face_sharp, 1),
        "subject_from_pixcull": bool(pix and pix.get("laplacian_subject") not in (None, "")),
        "shadow_score": shadow_info["shadow_score"],
        "shadow_cover": shadow_info["shadow_cover"],
        "shadow_head_cover": shadow_info.get("shadow_head_cover", 0.0),
        "shadow_zh": shadow_info["shadow_zh"],
    }


def _score_tuple(lab: dict) -> tuple:
    try:
        shd = -float(lab.get("shadow_score") if lab.get("shadow_score") not in (None, "") else 50)
    except (TypeError, ValueError):
        shd = -50.0
    try:
        sf = -float(lab.get("score_final") or 0)
    except (TypeError, ValueError):
        sf = 0.0
    subj = lab.get("laplacian_subject")
    if subj in (None, ""):
        subj = lab.get("face_sharp")
    try:
        sj = -float(subj or 0)
    except (TypeError, ValueError):
        sj = 0.0
    try:
        sh = -float(lab.get("sharp") or 0)
    except (TypeError, ValueError):
        sh = 0.0
    return (shd, sf, sj, sh, lab.get("file") or "")


def _num(lab: dict, key: str, default: float = 0.0) -> float:
    try:
        return float(lab.get(key) if lab.get(key) not in (None, "") else default)
    except (TypeError, ValueError):
        return default


def is_blurry(lab: dict) -> bool:
    """True when the subject/face is soft. Global sharp can look high on a blurry face."""
    if _num(lab, "sharp") < SHARP_OK:
        return True
    if lab.get("subject_from_pixcull") and lab.get("laplacian_subject") not in (None, ""):
        return _num(lab, "laplacian_subject") < SUBJECT_SHARP_OK
    if lab.get("face_sharp") not in (None, ""):
        return _num(lab, "face_sharp") < FACE_CROP_OK
    if lab.get("laplacian_subject") not in (None, ""):
        # Thumb-scale subject crop when PixCull is missing.
        return _num(lab, "laplacian_subject") < FACE_CROP_OK
    return False


def is_acceptable(lab: dict) -> bool:
    if not lab.get("features_ok"):
        return False
    if lab.get("exposure_fail") or lab.get("exposure") in ("過暗", "過曝"):
        return False
    if is_blurry(lab):
        return False
    if (lab.get("_orig_caption") or lab.get("caption") or "") in OCCLUDED:
        return False
    return True


def reject_reason(lab: dict) -> tuple[str, str]:
    """Return (caption, note) for a reject."""
    if is_blurry(lab):
        return "失焦", "主體不夠銳利，看不清五官細節"
    if not lab.get("features_ok"):
        return "五官不清", "主體看不見完整五官（背影、側臉或臉被擋住）"
    if lab.get("exposure") in ("過暗", "過曝"):
        return lab["exposure"], f"曝光不佳（{lab['exposure']}）"
    if (lab.get("_orig_caption") or lab.get("caption") or "") in OCCLUDED:
        return "前景遮擋", lab.get("note") or "前景觀眾或手臂擋住主體"
    return "動作重複", "連拍近幀，同組已另留分數較高的畫面"


def _burst_size(group: list[dict]) -> int:
    size = group[0].get("burst_size") or len(group)
    try:
        size = int(size)
    except (TypeError, ValueError):
        size = len(group)
    if size < 2:
        size = len(group) if len(group) >= 2 else 1
    return size


def _keep_caption(lab: dict, note: str) -> None:
    old_cap = lab.get("_orig_caption") or ""
    lab["bucket"] = "keep"
    if old_cap in REJECT_CAPS or old_cap in OCCLUDED:
        lab["caption"] = "動作清楚"
        lab["note"] = note
    else:
        lab["caption"] = old_cap
        lab["note"] = note


def apply_features_and_bursts(rows: list[dict], min_keep: int = MIN_FOLDER_KEEP) -> dict:
    """
    Reject shots without readable 五官.
    Inside each 連拍組, keep up to 5 shots that pass the other checks.
    If the folder still has fewer than min_keep keeps, keep the best 5
    in each 連拍組 regardless of overall score / quality gates.
    """
    for lab in rows:
        lab["_orig_caption"] = lab.get("caption") or ""
        lab["_orig_bucket"] = lab.get("bucket") or "discard"
        lab["features_ok"] = bool(lab.get("features_ok", lab.get("face_half")))
        lab["face_half_zh"] = "五官可見" if lab["features_ok"] else "五官不清"
        lab["face_fail"] = not lab["features_ok"]

    by_burst: dict = {}
    for lab in rows:
        bid = lab.get("burst_id")
        if bid in (None, ""):
            bid = f"solo:{lab.get('file')}"
        by_burst.setdefault(bid, []).append(lab)

    stats = {
        "rejected_features": 0,
        "promoted": 0,
        "demoted": 0,
        "burst_groups": 0,
        "loosened": False,
        "loose_promoted": 0,
    }

    for bid, group in by_burst.items():
        size = _burst_size(group)
        if size >= 2:
            stats["burst_groups"] += 1
            acceptable = [r for r in group if is_acceptable(r)]
            acceptable.sort(key=_score_tuple)
            top_files = {r["file"] for r in acceptable[:BURST_KEEP]}
            for lab in group:
                if lab["file"] in top_files:
                    if lab.get("bucket") != "keep":
                        stats["promoted"] += 1
                    _keep_caption(lab, f"同連拍組 #{bid} 內可接受畫面，依分數留下")
                    continue
                cap, note = reject_reason(lab)
                if not lab.get("features_ok"):
                    stats["rejected_features"] += 1
                if is_acceptable(lab):
                    cap, note = "動作重複", "連拍近幀，同組已另留分數較高的畫面"
                if lab.get("_orig_bucket") == "keep":
                    stats["demoted"] += 1
                lab["bucket"] = "discard"
                lab["caption"] = cap
                lab["note"] = note
            continue

        for lab in group:
            if is_acceptable(lab):
                continue
            cap, note = reject_reason(lab)
            if not lab.get("features_ok"):
                stats["rejected_features"] += 1
            if lab.get("_orig_bucket") != "discard":
                stats["demoted"] += 1
            lab["bucket"] = "discard"
            lab["caption"] = cap
            lab["note"] = note

    keep_n = sum(1 for r in rows if r.get("bucket") == "keep")
    if keep_n >= min_keep:
        return stats

    stats["loosened"] = True
    for bid, group in by_burst.items():
        if _burst_size(group) < 2:
            continue
        ranked = sorted(group, key=_score_tuple)
        top_files = {r["file"] for r in ranked[:BURST_KEEP]}
        for lab in group:
            if lab["file"] not in top_files:
                if lab.get("bucket") == "keep":
                    stats["demoted"] += 1
                    lab["bucket"] = "discard"
                    lab["caption"] = "動作重複"
                    lab["note"] = "連拍近幀，同組已另留相對較佳的畫面"
                continue
            if lab.get("bucket") != "keep":
                stats["promoted"] += 1
                stats["loose_promoted"] += 1
            _keep_caption(
                lab,
                f"同連拍組 #{bid} 內相對最好的 {min(BURST_KEEP, len(group))} 張之一"
                f"（此資料夾 keep 未滿 {min_keep}，不看分數門檻）",
            )
    return stats


def _print_apply_stats(applied: dict) -> None:
    extra = ""
    if applied.get("loosened"):
        extra = f" · loosened +{applied.get('loose_promoted', 0)}"
    print(
        f"apply 五官 reject {applied['rejected_features']} · "
        f"promoted {applied['promoted']} · demoted {applied['demoted']} · "
        f"bursts {applied['burst_groups']}{extra}"
    )


def _label_backup(out: Path, labels_name: str) -> Path:
    for name in ("visual-labels.before-wuguan.json", "visual-labels.before-enrich.json", labels_name):
        path = out / name
        if path.is_file():
            return path
    return out / labels_name


def score_shadow_thumb(thumb_path: Path) -> dict:
    with Image.open(thumb_path) as im:
        frame = ImageOps.exif_transpose(im).convert("RGB")
        rgb = np.asarray(frame)
    bgr = rgb[:, :, ::-1].copy()
    pose = detect_pose(bgr)
    return audience_shadow_score(rgb, pose.persons)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--apply-cull",
        action="store_true",
        help="Reject 五官不清; inside each 連拍組 keep up to 5 acceptable shots. "
        "If keep < 50, keep the best 5 per 連拍組 regardless of score.",
    )
    parser.add_argument(
        "--apply-only",
        action="store_true",
        help="Reuse image-metrics.json and re-apply keep/discard rules (no rescan).",
    )
    parser.add_argument(
        "--shadow-only",
        action="store_true",
        help="Score 觀眾黑影 on existing thumbs and write into image-metrics.json (no face rescan).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip photos already present in image-metrics.json.",
    )
    parser.add_argument(
        "--labels",
        default="visual-labels.json",
        help="Merge metrics into this labels file (default visual-labels.json).",
    )
    args = parser.parse_args()
    out = Path(args.output).expanduser().resolve()
    if args.shadow_only:
        index = json.loads((out / "review-index.json").read_text(encoding="utf-8"))
        metrics_path = out / "image-metrics.json"
        metrics = json.loads(metrics_path.read_text(encoding="utf-8")) if metrics_path.is_file() else {"rows": []}
        by = {r["file"]: r for r in metrics.get("rows", []) if r.get("file")}
        thumbs = out / "thumbs"
        photos = list(index["photos"])
        if args.limit:
            photos = photos[: args.limit]
        counts = {"無黑影": 0, "黑影輕微": 0, "黑影明顯": 0, "黑影擋住主角": 0}
        n_done = 0
        for p in tqdm(photos, desc="shadow"):
            row = by.get(p["file"]) or {"file": p["file"], "i": p.get("i")}
            if row.get("shadow_zh") in counts:
                counts[row["shadow_zh"]] += 1
                n_done += 1
                continue
            thumb = thumbs / p["thumb"]
            if not thumb.is_file():
                raise FileNotFoundError(thumb)
            sh = score_shadow_thumb(thumb)
            row.update(sh)
            by[p["file"]] = row
            counts[sh["shadow_zh"]] = counts.get(sh["shadow_zh"], 0) + 1
            n_done += 1
            if n_done % 25 == 0:
                metrics["rows"] = [by[ph["file"]] for ph in index["photos"] if ph["file"] in by]
                metrics["count"] = len(metrics["rows"])
                metrics_path.write_text(json.dumps(metrics, ensure_ascii=False), encoding="utf-8")
                print(f"checkpoint {n_done}/{len(photos)}", flush=True)
        metrics["rows"] = [by[p["file"]] for p in index["photos"] if p["file"] in by]
        metrics["count"] = len(metrics["rows"])
        metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
        labels_path = out / args.labels
        if labels_path.is_file():
            labels = json.loads(labels_path.read_text(encoding="utf-8"))
            for lab in labels.get("rows", []):
                m = by.get(lab["file"])
                if not m:
                    continue
                lab["shadow_score"] = m.get("shadow_score")
                lab["shadow_cover"] = m.get("shadow_cover")
                lab["shadow_head_cover"] = m.get("shadow_head_cover")
                lab["shadow_zh"] = m.get("shadow_zh")
            labels_path.write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"shadow {metrics_path}")
        print(
            " · ".join(f"{k} {v}" for k, v in counts.items())
        )
        if not args.apply_cull:
            return
        args.apply_only = True
    if args.apply_only:
        metrics_path = out / "image-metrics.json"
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        src = _label_backup(out, args.labels)
        labels = json.loads(src.read_text(encoding="utf-8"))
        current_path = out / args.labels
        current_by = {}
        if current_path.is_file():
            current_by = {
                r["file"]: r
                for r in json.loads(current_path.read_text(encoding="utf-8")).get("rows", [])
                if r.get("file")
            }
        enrich_keys = (
            "exposure",
            "mean_luma",
            "people_group",
            "people_in_focus",
            "people_total",
            "face_half",
            "face_half_zh",
            "face_half_count",
            "features_ok",
            "face_count",
            "exposure_fail",
            "face_fail",
            "sharp",
            "laplacian_subject",
            "face_sharp",
            "subject_from_pixcull",
            "score_final",
            "burst_id",
            "burst_rank",
            "burst_size",
            "shadow_score",
            "shadow_cover",
            "shadow_head_cover",
            "shadow_zh",
        )
        met = {r["file"]: r for r in metrics.get("rows", [])}
        for lab in labels.get("rows", []):
            cur = current_by.get(lab["file"], {})
            for key in enrich_keys:
                if cur.get(key) not in (None, ""):
                    lab[key] = cur[key]
            m = met.get(lab["file"])
            if not m:
                continue
            lab.update(
                {key: m[key] for key in enrich_keys if key in m and m.get(key) not in (None, "")}
            )
        pix_by = load_pixcull(out)
        for lab in labels.get("rows", []):
            prow = pix_by.get(lab["file"]) or pix_by.get(Path(lab["file"]).name)
            if not prow:
                continue
            if prow.get("laplacian_subject") not in (None, ""):
                lab["laplacian_subject"] = round(_f(prow, "laplacian_subject"), 1)
            if prow.get("score_final") not in (None, "") and lab.get("score_final") in (None, ""):
                lab["score_final"] = round(_f(prow, "score_final"), 4)
        index_path = out / "review-index.json"
        if index_path.is_file():
            index = json.loads(index_path.read_text(encoding="utf-8"))
            n_burst = assign_bursts(labels["rows"], Path(index.get("source") or ""))
            if n_burst:
                print(f"assigned {n_burst} 連拍組 from EXIF ({BURST_GAP_SEC:.0f}s)")
        applied = apply_features_and_bursts(labels["rows"])
        for r in labels["rows"]:
            r.pop("_orig_caption", None)
            r.pop("_orig_bucket", None)
        labels["keep"] = sum(1 for r in labels["rows"] if r.get("bucket") == "keep")
        labels["maybe"] = sum(1 for r in labels["rows"] if r.get("bucket") == "maybe")
        labels["discard"] = sum(1 for r in labels["rows"] if r.get("bucket") == "discard")
        dest = out / "visual-labels.json"
        dest.write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"applied from {src.name} + {metrics_path.name} → {dest}")
        _print_apply_stats(applied)
        print(f"keep {labels['keep']} · maybe {labels['maybe']} · discard {labels['discard']}")
        return

    index = json.loads((out / "review-index.json").read_text(encoding="utf-8"))
    labels_path = out / args.labels
    labels = json.loads(labels_path.read_text(encoding="utf-8")) if labels_path.is_file() else {"rows": []}
    pix_by = load_pixcull(out)
    thumbs = out / "thumbs"

    photos = list(index["photos"])
    if args.limit:
        photos = photos[: args.limit]

    by_file = {r["file"]: r for r in labels.get("rows", [])}
    metrics_path = out / "image-metrics.json"
    done: dict[str, dict] = {}
    if args.resume and metrics_path.is_file():
        prev = json.loads(metrics_path.read_text(encoding="utf-8"))
        done = {r["file"]: r for r in prev.get("rows", []) if r.get("file")}
        print(f"resume {len(done)} already scored")
    metrics_rows = []
    fail_exp = fail_face = 0
    groups = {"無人": 0, "1人": 0, "2-5人": 0, "5人以上": 0}

    for n_done, p in enumerate(tqdm(photos, desc="enrich"), 1):
        thumb = thumbs / p["thumb"]
        if not thumb.is_file():
            raise FileNotFoundError(thumb)
        pix = pix_by.get(p["file"]) or pix_by.get(Path(p["file"]).name)
        if p["file"] in done:
            m = dict(done[p["file"]])
        else:
            try:
                m = analyze_image(thumb, pix, p.get("sharp"))
            except Exception as exc:  # noqa: BLE001
                print(f"WARN skip {p.get('file')}: {exc}", flush=True)
                m = {
                    "exposure": "正常",
                    "mean_luma": 0,
                    "people_total": 0,
                    "people_in_focus": 0,
                    "people_group": "無人",
                    "face_half": False,
                    "face_half_count": 0,
                    "face_half_zh": "五官不清",
                    "features_ok": False,
                    "face_count": 0,
                    "exposure_fail": False,
                    "face_fail": True,
                    "sharp": p.get("sharp"),
                    "laplacian_subject": None,
                    "face_sharp": None,
                    "subject_from_pixcull": False,
                    "shadow_score": 100.0,
                    "shadow_cover": 0.0,
                    "shadow_head_cover": 0.0,
                    "shadow_zh": "無黑影",
                }
        m.update({"i": p["i"], "file": p["file"]})
        metrics_rows.append(m)
        groups[m["people_group"]] += 1
        fail_exp += int(m["exposure_fail"])
        fail_face += int(m["face_fail"])

        lab = by_file.get(p["file"])
        if lab is not None:
            lab.update(
                {
                    "exposure": m["exposure"],
                    "mean_luma": m["mean_luma"],
                    "people_group": m["people_group"],
                    "people_in_focus": m["people_in_focus"],
                    "people_total": m["people_total"],
                    "face_half": m["face_half"],
                    "face_half_zh": m["face_half_zh"],
                    "face_half_count": m["face_half_count"],
                    "features_ok": m["features_ok"],
                    "face_count": m["face_count"],
                    "exposure_fail": m["exposure_fail"],
                    "face_fail": m["face_fail"],
                    "laplacian_subject": m.get("laplacian_subject"),
                    "face_sharp": m.get("face_sharp"),
                    "subject_from_pixcull": m.get("subject_from_pixcull"),
                    "shadow_score": m.get("shadow_score"),
                    "shadow_cover": m.get("shadow_cover"),
                    "shadow_head_cover": m.get("shadow_head_cover"),
                    "shadow_zh": m.get("shadow_zh"),
                    "sharp": m.get("sharp", lab.get("sharp")),
                }
            )
            if lab.get("score_final") in (None, "") and pix:
                try:
                    lab["score_final"] = round(float(pix.get("score_final") or 0), 4)
                except (TypeError, ValueError):
                    pass

        if n_done % 25 == 0:
            metrics_path.write_text(
                json.dumps({"count": len(metrics_rows), "rows": metrics_rows}, ensure_ascii=False),
                encoding="utf-8",
            )
            print(f"checkpoint {n_done}/{len(photos)}", flush=True)

    metrics_path = out / "image-metrics.json"
    metrics_path.write_text(
        json.dumps(
            {
                "count": len(metrics_rows),
                "people_groups": groups,
                "exposure_fail": fail_exp,
                "face_fail": fail_face,
                "rows": metrics_rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    if labels_path.is_file():
        backup = out / "visual-labels.before-enrich.json"
        if not backup.is_file():
            shutil.copy2(labels_path, backup)
        labels["rows"] = [by_file.get(r["file"], r) for r in labels["rows"]]
        source = Path(index.get("source") or "")
        n_burst = assign_bursts(labels["rows"], source)
        if n_burst:
            print(f"assigned {n_burst} 連拍組 from EXIF ({BURST_GAP_SEC:.0f}s)")
        if args.apply_cull:
            applied = apply_features_and_bursts(labels["rows"])
            for r in labels["rows"]:
                r.pop("_orig_caption", None)
                r.pop("_orig_bucket", None)
            labels["keep"] = sum(1 for r in labels["rows"] if r.get("bucket") == "keep")
            labels["maybe"] = sum(1 for r in labels["rows"] if r.get("bucket") == "maybe")
            labels["discard"] = sum(1 for r in labels["rows"] if r.get("bucket") == "discard")
            _print_apply_stats(applied)
        labels_path.write_text(json.dumps(labels, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"metrics {metrics_path}")
    print(
        f"people 無人 {groups['無人']} · 1人 {groups['1人']} · "
        f"2-5人 {groups['2-5人']} · 5人以上 {groups['5人以上']}"
    )
    print(f"exposure fail {fail_exp} · 五官不清 {fail_face}")
    if args.apply_cull:
        print(f"keep {labels.get('keep')} · maybe {labels.get('maybe')} · discard {labels.get('discard')}")


if __name__ == "__main__":
    import faulthandler
    import traceback

    faulthandler.enable()
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
