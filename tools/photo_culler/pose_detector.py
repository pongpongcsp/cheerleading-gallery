"""YOLOv8 pose / person detection for cheerleading subjects."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

_MODEL = None
_MODEL_WARNED = False
_MODEL_FAILED = False

_WEIGHTS_DIR = Path(__file__).resolve().parent / "weights"
_WEIGHTS_PATH = _WEIGHTS_DIR / "yolov8n-pose.pt"


@dataclass
class PersonDetection:
    """One detected person with box and optional keypoints."""

    xyxy: tuple[float, float, float, float]
    conf: float
    keypoints: np.ndarray | None = None  # (K, 2) or (K, 3) if available
    area_ratio: float = 0.0


@dataclass
class PoseResult:
    persons: list[PersonDetection] = field(default_factory=list)
    best_conf: float = 0.0
    person_count: int = 0
    has_usable_subject: bool = False
    pose_score: float = 0.0  # 0–25 contribution


def _ensure_weights() -> Path:
    """Return path to yolov8n-pose.pt, downloading once into tools/photo_culler/weights/."""
    _WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)
    if _WEIGHTS_PATH.exists():
        return _WEIGHTS_PATH

    # Ultralytics may download into CWD; relocate into weights/
    cwd_weights = Path.cwd() / "yolov8n-pose.pt"
    if cwd_weights.exists():
        cwd_weights.replace(_WEIGHTS_PATH)
        return _WEIGHTS_PATH

    from ultralytics import YOLO

    # Triggers download of yolov8n-pose.pt into CWD
    YOLO("yolov8n-pose.pt")
    if cwd_weights.exists():
        cwd_weights.replace(_WEIGHTS_PATH)
    if not _WEIGHTS_PATH.exists():
        raise FileNotFoundError(f"Expected weights at {_WEIGHTS_PATH} after download")
    return _WEIGHTS_PATH


def _load_model():
    global _MODEL, _MODEL_WARNED, _MODEL_FAILED
    if _MODEL_FAILED:
        return None
    if _MODEL is not None:
        return _MODEL
    try:
        from ultralytics import YOLO
    except ImportError:
        if not _MODEL_WARNED:
            print(
                "Warning: ultralytics not installed — skipping YOLO pose. "
                "Install with: pip install ultralytics",
                file=sys.stderr,
            )
            _MODEL_WARNED = True
        _MODEL_FAILED = True
        return None
    try:
        weights = _ensure_weights()
        _MODEL = YOLO(str(weights))
        return _MODEL
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: could not load YOLOv8 pose model: {exc}", file=sys.stderr)
        _MODEL_FAILED = True
        return None


def detect_pose(image_bgr: np.ndarray) -> PoseResult:
    """
    Run YOLOv8 pose on a BGR image.

    Accepts frontal and side/back bodies as valid subjects (not face-only).
    """
    model = _load_model()
    h, w = image_bgr.shape[:2]
    frame_area = float(h * w) or 1.0
    result = PoseResult()

    if model is None:
        return result

    try:
        preds = model.predict(image_bgr, verbose=False, conf=0.35)
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: YOLO predict failed: {exc}", file=sys.stderr)
        return result

    if not preds:
        return result

    pred = preds[0]
    boxes = pred.boxes
    kpts = getattr(pred, "keypoints", None)

    if boxes is None or len(boxes) == 0:
        return result

    persons: list[PersonDetection] = []
    for i in range(len(boxes)):
        xyxy = boxes.xyxy[i].cpu().numpy().tolist()
        conf = float(boxes.conf[i].cpu().numpy())
        x1, y1, x2, y2 = xyxy
        area = max(0.0, (x2 - x1) * (y2 - y1))
        area_ratio = area / frame_area
        kp = None
        if kpts is not None and hasattr(kpts, "data") and i < len(kpts.data):
            kp = kpts.data[i].cpu().numpy()
        persons.append(
            PersonDetection(
                xyxy=(float(x1), float(y1), float(x2), float(y2)),
                conf=conf,
                keypoints=kp,
                area_ratio=area_ratio,
            )
        )

    persons.sort(key=lambda p: p.conf * (0.5 + p.area_ratio), reverse=True)
    result.persons = persons
    result.person_count = len(persons)
    result.best_conf = persons[0].conf if persons else 0.0

    # Usable subject: at least one person with decent confidence and size
    primary = persons[0] if persons else None
    result.has_usable_subject = bool(
        primary and primary.conf >= 0.4 and primary.area_ratio >= 0.02
    )

    # Pose score: confidence + subject size (side/back still score well)
    if primary:
        size_bonus = min(10.0, primary.area_ratio * 40)
        conf_bonus = min(15.0, primary.conf * 15)
        result.pose_score = round(conf_bonus + size_bonus, 2)
    else:
        result.pose_score = 0.0

    return result
