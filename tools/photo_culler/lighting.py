"""HSV lighting / exposure scoring."""

from __future__ import annotations

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None  # type: ignore[assignment]


def lighting_stats(bgr_or_rgb: np.ndarray, is_bgr: bool = True) -> dict:
    """
    Compute lighting metrics from an image array (HxWx3).

    Returns mean V (0–255), dark-pixel ratio, and a 0–25 lighting score.
    """
    if cv2 is not None:
        if is_bgr:
            hsv = cv2.cvtColor(bgr_or_rgb, cv2.COLOR_BGR2HSV)
        else:
            hsv = cv2.cvtColor(bgr_or_rgb, cv2.COLOR_RGB2HSV)
        v = hsv[:, :, 2].astype(np.float64)
    else:
        # Approximate V from max channel
        arr = bgr_or_rgb.astype(np.float64)
        v = arr.max(axis=2)

    mean_v = float(v.mean())
    dark_ratio = float((v < 40).mean())
    bright_ratio = float((v > 245).mean())

    # Prefer mid-high stadium lighting (~90–180)
    mid_penalty = abs(mean_v - 135) / 135 * 15
    dark_penalty = min(20.0, dark_ratio * 40)
    bright_penalty = min(10.0, bright_ratio * 30)
    score = max(0.0, 25.0 - mid_penalty - dark_penalty - bright_penalty)

    return {
        "mean_v": round(mean_v, 2),
        "dark_ratio": round(dark_ratio, 4),
        "bright_ratio": round(bright_ratio, 4),
        "lighting_score": round(score, 2),
    }
