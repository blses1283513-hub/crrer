"""Find where the people are in a photo or video frame, so framing never cuts them.

Faces come from YuNet (OpenCV, MIT, bundled in assets/models). Each face is grown into a
conservative whole-person box (hair to feet, arms' width); standing people found by OpenCV's
built-in HOG detector are added too. The union, plus a margin, is the region every crop,
pan and zoom must keep fully inside the picture.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

MODEL = Path(__file__).resolve().parent.parent / "assets" / "models" / "face_detection_yunet_2023mar.onnx"
DETECT_SIZE = 1024  # longest side used for detection


@lru_cache(maxsize=1)
def _face_net():
    if not MODEL.exists():
        return None
    return cv2.FaceDetectorYN.create(str(MODEL), "", (320, 320), 0.75, 0.3, 5000)


@lru_cache(maxsize=1)
def _hog():
    if not hasattr(cv2, "HOGDescriptor"):  # removed from OpenCV 5 core; optional extra signal
        return None
    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    return hog


def detect(bgr: np.ndarray) -> list[list[float]]:
    """Person boxes as [x0, y0, x1, y1] fractions of the image (0-1), already grown to the
    whole body and clamped to the image."""
    h, w = bgr.shape[:2]
    s = DETECT_SIZE / max(w, h)
    small = cv2.resize(bgr, (round(w * s), round(h * s))) if s < 1 else bgr
    sh, sw = small.shape[:2]
    boxes = []

    net = _face_net()
    if net is not None:
        net.setInputSize((sw, sh))
        _, faces = net.detect(small)
        for f in faces if faces is not None else []:
            fx, fy, fw, fh = f[:4]
            if fw < 0.015 * sw:  # tiny background faces (posters, crowds far away) don't count
                continue
            # Grow the face into the whole person: hair above, shoulders/arms to the sides,
            # body down to the feet (about 7.5 head heights), clamped to the image later.
            boxes.append([fx - 1.6 * fw, fy - 0.6 * fh, fx + 2.6 * fw, fy + 8.0 * fh])

    hog = _hog()
    if hog is not None:
        hog_img = cv2.resize(small, (round(sw * 640 / max(sw, sh)), round(sh * 640 / max(sw, sh))))
        k = sw / hog_img.shape[1]
        rects, weights = hog.detectMultiScale(hog_img, winStride=(8, 8), padding=(8, 8), scale=1.05)
        for (x, y, rw, rh), wt in zip(rects, np.ravel(weights) if len(rects) else []):
            if wt > 0.9:
                boxes.append([x * k, y * k, (x + rw) * k, (y + rh) * k])

    out = []
    for x0, y0, x1, y1 in boxes:
        out.append([float(max(0.0, x0 / sw)), float(max(0.0, y0 / sh)),
                    float(min(1.0, x1 / sw)), float(min(1.0, y1 / sh))])
    return out


def union(boxes: list[list[float]], margin: float = 0.03) -> list[float] | None:
    """One region covering everyone, with a small safety margin, clamped to the image."""
    if not boxes:
        return None
    x0 = min(b[0] for b in boxes) - margin
    y0 = min(b[1] for b in boxes) - margin
    x1 = max(b[2] for b in boxes) + margin
    y1 = max(b[3] for b in boxes) + margin
    return [round(float(max(0.0, x0)), 4), round(float(max(0.0, y0)), 4),
            round(float(min(1.0, x1)), 4), round(float(min(1.0, y1)), 4)]
