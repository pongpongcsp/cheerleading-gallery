"""Per-image composite scoring: sharpness + lighting + pose + occlusion."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

from .lighting import lighting_stats
from .occlusion import occlusion_penalty
from .pose_detector import detect_pose
from .sharpness import laplacian_variance, sharpness_score

try:
    import cv2
except ImportError:
    cv2 = None  # type: ignore[assignment]


def dhash(gray: np.ndarray, hash_size: int = 8) -> int:
    """Difference hash on a grayscale array."""
    if cv2 is not None:
        small = cv2.resize(gray, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    else:
        from PIL import Image as PILImage

        im = PILImage.fromarray(gray).resize((hash_size + 1, hash_size), PILImage.Resampling.LANCZOS)
        small = np.array(im)
    bits = 0
    bit = 0
    for row in range(hash_size):
        for col in range(hash_size):
            if small[row, col] > small[row, col + 1]:
                bits |= 1 << bit
            bit += 1
    return bits


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def _imread_bgr(path: Path) -> np.ndarray | None:
    """Read BGR image; supports Unicode paths on Windows (cv2.imread often fails)."""
    if cv2 is not None:
        try:
            data = np.fromfile(str(path), dtype=np.uint8)
            if data.size:
                bgr = cv2.imdecode(data, cv2.IMREAD_COLOR)
                if bgr is not None:
                    return bgr
        except Exception:  # noqa: BLE001
            pass
    return None


def _load_sample(path: Path, max_edge: int = 960) -> tuple[np.ndarray, np.ndarray, int, int]:
    """
    Return (bgr_sample, gray_sample, full_width, full_height).

    Prefers OpenCV (Unicode-safe); falls back to Pillow.
    """
    bgr_full = _imread_bgr(path)
    if bgr_full is not None and cv2 is not None:
        h, w = bgr_full.shape[:2]
        bgr = bgr_full
        if max(h, w) > max_edge:
            scale = max_edge / max(h, w)
            bgr = cv2.resize(
                bgr,
                (int(w * scale), int(h * scale)),
                interpolation=cv2.INTER_AREA,
            )
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        return bgr, gray, w, h

    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        w, h = im.size
        sample = im.copy()
        sample.thumbnail((max_edge, max_edge), Image.Resampling.BILINEAR)
        rgb = np.array(sample.convert("RGB"))
        bgr = rgb[:, :, ::-1].copy()
        gray = np.array(sample.convert("L"))
        return bgr, gray, w, h


def score_image(path: Path) -> dict:
    """Score one image across sharpness, lighting, pose, and occlusion."""
    bgr, gray, full_w, full_h = _load_sample(path)
    sample_h, sample_w = gray.shape[:2]

    lap = laplacian_variance(gray)
    sharp = sharpness_score(lap)
    light = lighting_stats(bgr, is_bgr=True)
    pose = detect_pose(bgr)
    occ = occlusion_penalty(pose.persons, float(sample_h))

    # Composite: sharpness + lighting + pose − occlusion
    score = max(
        0.0,
        sharp + light["lighting_score"] + pose.pose_score - occ["occlusion_penalty"],
    )

    return {
        "path": path,
        "width": full_w,
        "height": full_h,
        "sharpness": round(lap, 2),
        "sharpness_score": round(sharp, 2),
        "brightness": light["mean_v"],
        "dark_ratio": light["dark_ratio"],
        "lighting_score": light["lighting_score"],
        "pose_conf": round(pose.best_conf, 3),
        "person_count": pose.person_count,
        "has_subject": pose.has_usable_subject,
        "pose_score": pose.pose_score,
        "occlusion_penalty": occ["occlusion_penalty"],
        "occlusion_reason": occ["occlusion_reason"],
        "overlap_ratio": occ["overlap_ratio"],
        "score": round(score, 2),
        "dhash": dhash(gray),
        # Kept for report compatibility / soft ranking
        "frontal_faces": 1 if pose.has_usable_subject else 0,
    }
