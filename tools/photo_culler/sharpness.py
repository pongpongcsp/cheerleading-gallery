"""Laplacian variance sharpness scoring via OpenCV."""

from __future__ import annotations

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None  # type: ignore[assignment]


def laplacian_variance(gray: np.ndarray) -> float:
    """Return variance of Laplacian on a grayscale uint8 image."""
    if cv2 is None:
        # Fallback: approximate with NumPy second derivative energy
        gx = np.diff(gray.astype(np.float64), axis=1)
        gy = np.diff(gray.astype(np.float64), axis=0)
        return float(gx.var() + gy.var())
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def sharpness_score(laplacian_var: float) -> float:
    """Map Laplacian variance to 0–40 contribution for the composite score."""
    # Typical stadium/JPEG thumbs: soft ~20–80, sharp ~150–800+
    return max(0.0, min(40.0, (laplacian_var ** 0.5) * 1.8))
