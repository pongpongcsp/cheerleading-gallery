"""Audience occlusion heuristics from person bounding boxes and dark foreground 黑影."""

from __future__ import annotations

import numpy as np

from .pose_detector import PersonDetection


def occlusion_penalty(persons: list[PersonDetection], frame_h: float) -> dict:
    """
    Penalize shots where smaller (likely closer) people overlap the main subject,
    or where the primary subject is heavily cut by many overlapping boxes.

    Returns occlusion_penalty (0–25 subtracted from score) and a short reason.
    """
    if not persons:
        return {
            "occlusion_penalty": 0.0,
            "occlusion_reason": "no persons",
            "overlap_ratio": 0.0,
        }

    primary = max(persons, key=lambda p: p.conf * (0.5 + p.area_ratio))
    px1, py1, px2, py2 = primary.xyxy
    p_area = max(1.0, (px2 - px1) * (py2 - py1))

    # Others that sit lower in the frame (audience / closer) and overlap primary
    overlap_area = 0.0
    blockers = 0
    primary_cy = (py1 + py2) / 2

    for other in persons:
        if other is primary:
            continue
        ox1, oy1, ox2, oy2 = other.xyxy
        other_cy = (oy1 + oy2) / 2
        # Closer/audience tend to be lower (higher y) and often smaller or mid-size
        ix1 = max(px1, ox1)
        iy1 = max(py1, oy1)
        ix2 = min(px2, ox2)
        iy2 = min(py2, oy2)
        if ix2 <= ix1 or iy2 <= iy1:
            continue
        inter = (ix2 - ix1) * (iy2 - iy1)
        if inter <= 0:
            continue
        # Lower-center person overlapping primary → likely occlusion
        if other_cy > primary_cy or other.area_ratio < primary.area_ratio * 0.85:
            overlap_area += inter
            blockers += 1

    overlap_ratio = min(1.0, overlap_area / p_area)

    # Also penalize many people packed on the primary (dense crowd in front)
    crowd_penalty = 0.0
    if blockers >= 2 and overlap_ratio > 0.08:
        crowd_penalty = min(10.0, blockers * 2.5)

    penalty = min(25.0, overlap_ratio * 35 + crowd_penalty)

    reason = "clear"
    if penalty >= 12:
        reason = "severe audience occlusion"
    elif penalty >= 5:
        reason = "partial occlusion"
    elif blockers:
        reason = "mild overlap"

    return {
        "occlusion_penalty": round(penalty, 2),
        "occlusion_reason": reason,
        "overlap_ratio": round(overlap_ratio, 4),
    }


try:
    import cv2
except ImportError:
    cv2 = None  # type: ignore[assignment]


def _strip_letterbox(gray: np.ndarray, thresh: float = 10.0, frac: float = 0.88) -> tuple[int, int, int, int]:
    row_dark = (gray < thresh).mean(axis=1)
    col_dark = (gray < thresh).mean(axis=0)
    rows = np.where(row_dark < frac)[0]
    cols = np.where(col_dark < frac)[0]
    if rows.size == 0 or cols.size == 0:
        h, w = gray.shape
        return 0, h, 0, w
    return int(rows[0]), int(rows[-1] + 1), int(cols[0]), int(cols[-1] + 1)


def _bottom_connected(dark: np.ndarray) -> np.ndarray:
    """Keep dark pixels connected to the bottom edge (audience at the camera)."""
    h, w = dark.shape
    seed_y0 = max(0, h - max(3, int(h * 0.08)))
    mask = np.zeros((h, w), dtype=np.uint8)
    mask[seed_y0:] = dark[seed_y0:].astype(np.uint8)
    dark_u8 = dark.astype(np.uint8)
    if cv2 is not None:
        kernel = np.ones((5, 5), np.uint8)
        prev = -1
        for _ in range(40):
            nxt = cv2.dilate(mask, kernel, iterations=1)
            nxt = cv2.bitwise_and(nxt, dark_u8)
            total = int(nxt.sum())
            if total == prev:
                return nxt > 0
            mask = nxt
            prev = total
        return mask > 0
    vis = mask > 0
    from collections import deque

    q = deque()
    ys, xs = np.nonzero(vis)
    for y, x in zip(ys.tolist(), xs.tolist()):
        q.append((y, x))
    while q:
        y, x = q.popleft()
        for ny in (y - 1, y, y + 1):
            for nx in (x - 1, x, x + 1):
                if ny < 0 or nx < 0 or ny >= h or nx >= w:
                    continue
                if vis[ny, nx] or not dark[ny, nx]:
                    continue
                vis[ny, nx] = True
                q.append((ny, nx))
    return vis


def _stage_subject(persons: list, w: int, h: int):
    """Pick the on-stage cheerleader, not a large foreground audience box."""
    if not persons:
        return None
    best = None
    best_s = -1e9
    for p in persons:
        x1, y1, x2, y2 = p.xyxy
        cx = ((x1 + x2) / 2.0) / max(1, w)
        cy = ((y1 + y2) / 2.0) / max(1, h)
        central = 1.0 - abs(cx - 0.5) * 2.0
        high = 1.0 - cy
        edge = 0.0
        if x1 <= 3 or x2 >= w - 3:
            edge += 0.35
        if y2 >= h * 0.95 and cy > 0.62:
            edge += 0.45
        score = (getattr(p, "area_ratio", 0.0) or 0.0) * 0.35 + 0.35 * high + 0.40 * central - edge
        if score > best_s:
            best_s = score
            best = p
    return best


def _shadow_zh(score: float) -> str:
    if score >= 88:
        return "無黑影"
    if score >= 65:
        return "黑影輕微"
    if score >= 38:
        return "黑影明顯"
    return "黑影擋住主角"


def audience_shadow_score(rgb: np.ndarray, persons: list | None = None) -> dict:
    """
    Score foreground 觀眾黑影. 100 = none; low = silhouette covers the main subject.
    """
    empty = {"shadow_score": 100.0, "shadow_cover": 0.0, "shadow_head_cover": 0.0, "shadow_zh": "無黑影"}
    if rgb.ndim != 3 or rgb.shape[2] < 3:
        return empty
    gray_full = (
        0.299 * rgb[:, :, 0].astype(np.float32)
        + 0.587 * rgb[:, :, 1].astype(np.float32)
        + 0.114 * rgb[:, :, 2].astype(np.float32)
    )
    y0, y1, x0, x1 = _strip_letterbox(gray_full)
    gray = gray_full[y0:y1, x0:x1]
    h, w = gray.shape
    if h < 16 or w < 16:
        return empty

    shifted_persons = []
    for p in persons or []:
        px1, py1, px2, py2 = p.xyxy
        shifted_persons.append(
            PersonDetection(
                xyxy=(px1 - x0, py1 - y0, px2 - x0, py2 - y0),
                conf=float(getattr(p, "conf", 0) or 0),
                area_ratio=float(getattr(p, "area_ratio", 0) or 0),
            )
        )

    primary = _stage_subject(shifted_persons, w, h)
    if primary is not None:
        sx1, sy1, sx2, sy2 = (int(v) for v in primary.xyxy)
        sx1 = max(0, min(w - 1, sx1))
        sx2 = max(sx1 + 1, min(w, sx2))
        sy1 = max(0, min(h - 1, sy1))
        sy2 = max(sy1 + 1, min(h, sy2))
        area = max(0.0, float(getattr(primary, "area_ratio", 0.0) or 0.0))
        if area >= 0.42 and sy2 >= h * 0.90:
            return {
                "shadow_score": 96.0,
                "shadow_cover": 0.0,
                "shadow_head_cover": 0.0,
                "shadow_zh": "無黑影",
            }
    else:
        sx1, sx2 = int(w * 0.22), int(w * 0.78)
        sy1, sy2 = int(h * 0.08), int(h * 0.70)

    upper = gray[: max(8, int(h * 0.40))]
    stage = float(np.median(upper)) if upper.size else 120.0
    dark_cut = min(48.0, max(20.0, stage * 0.34))
    sil = _bottom_connected(gray < dark_cut)

    # Dark sitting in front of the subject (same x-range, below / over lower body).
    front = sil[min(h - 1, sy1) :, sx1:sx2]
    front_frac = float(front.mean()) if front.size else 0.0
    below = sil[min(h, sy2) :, sx1:sx2]
    below_frac = float(below.mean()) if below.size else 0.0
    body = sil[sy1:sy2, sx1:sx2]
    cover = float(body.mean()) if body.size else 0.0
    hy = sy1 + max(8, int((sy2 - sy1) * 0.36))
    head = sil[sy1:hy, sx1:sx2]
    head_cover = float(head.mean()) if head.size else 0.0
    low_c = sil[int(h * 0.62) :, int(w * 0.22) : int(w * 0.78)]
    low_center = float(low_c.mean()) if low_c.size else 0.0

    score = 100.0 - 95.0 * front_frac - 55.0 * below_frac - 70.0 * cover - 90.0 * head_cover
    if low_center > 0.22:
        score -= 25.0 * min(1.0, (low_center - 0.22) / 0.5)
    score = float(max(0.0, min(100.0, score)))
    zh = _shadow_zh(score)
    return {
        "shadow_score": round(score, 1),
        "shadow_cover": round(max(cover, front_frac), 4),
        "shadow_head_cover": round(head_cover, 4),
        "shadow_zh": zh,
    }
