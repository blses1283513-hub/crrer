"""Turn scanned media into scored candidate shots.

Photos  -> normalized JPEG (orientation fixed, HEIC decoded) + quality score.
Videos  -> shots from PySceneDetect, each scored on sampled frames.
All     -> near-duplicates removed with perceptual hashes; a thumbnail per candidate.

Score (0-1) = sharpness, exposure, colorfulness and (for video) motion.
Optional CLIP aesthetics can be layered on later without changing this format.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:  # HEIC support is optional
    pass

from .people import detect as detect_people, union as people_union

THUMB = (270, 480)  # 9:16 thumbnails for the storyboard


def quality(bgr: np.ndarray) -> dict:
    """Cheap, CPU-only image quality signals."""
    small = cv2.resize(bgr, (512, int(512 * bgr.shape[0] / bgr.shape[1])))
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    sharp = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    sharp_n = min(1.0, np.log10(sharp + 1) / 3.0)          # ~1000 var -> 1.0
    mean = gray.mean() / 255.0
    clipped = float(((gray < 8) | (gray > 247)).mean())
    exposure = max(0.0, 1 - abs(mean - 0.5) * 2) * (1 - min(1.0, clipped * 2))
    b, g, r = [c.astype(np.float32) for c in cv2.split(small)]
    rg, yb = np.abs(r - g), np.abs(0.5 * (r + g) - b)
    colorful = (np.sqrt(rg.std() ** 2 + yb.std() ** 2) + 0.3 * np.sqrt(rg.mean() ** 2 + yb.mean() ** 2)) / 100
    color_n = min(1.0, float(colorful))
    score = 0.45 * sharp_n + 0.25 * exposure + 0.30 * color_n
    return {"sharpness": round(sharp_n, 3), "exposure": round(exposure, 3),
            "color": round(color_n, 3), "score": round(score, 3)}


def _thumb(bgr: np.ndarray, out: Path) -> None:
    img = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    ImageOps.fit(img, THUMB).save(out, quality=85)


def _phash(bgr: np.ndarray):
    import imagehash
    return imagehash.phash(Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)))


def analyze_photo(item: dict, work: Path) -> dict | None:
    try:
        img = ImageOps.exif_transpose(Image.open(item["src"])).convert("RGB")
    except Exception as exc:  # unreadable file
        print(f"  skip {item['name']}: {exc}")
        return None
    img.thumbnail((3840, 3840))
    norm = work / "photos" / f"{item['id']}.jpg"
    norm.parent.mkdir(parents=True, exist_ok=True)
    img.save(norm, quality=92)
    bgr = cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
    thumb = work / "thumbs" / f"{item['id']}.jpg"
    thumb.parent.mkdir(parents=True, exist_ok=True)
    _thumb(bgr, thumb)
    q = quality(bgr)
    people = detect_people(bgr)
    return {**item, "cid": item["id"], "render_src": str(norm), "width": img.width, "height": img.height,
            "in": 0.0, "max_dur": None, "thumb": str(thumb), "hash": _phash(bgr),
            "people": people_union(people), "n_people": len(people), **q}


def _shots(path: str, duration: float) -> list[tuple[float, float]]:
    from scenedetect import AdaptiveDetector, detect
    try:
        scenes = detect(path, AdaptiveDetector(), show_progress=False)
    except Exception:
        scenes = []
    shots = [(s.get_seconds(), e.get_seconds()) for s, e in scenes] or [(0.0, duration)]
    return [(s, e) for s, e in shots if e - s >= 0.8]


def analyze_video(item: dict, work: Path) -> list[dict]:
    cap = cv2.VideoCapture(item["src"])
    out = []
    for n, (start, end) in enumerate(_shots(item["src"], item["duration"])):
        frames = []
        for frac in (0.25, 0.5, 0.75):
            cap.set(cv2.CAP_PROP_POS_MSEC, (start + (end - start) * frac) * 1000)
            ok, frame = cap.read()
            if ok:
                frames.append(frame)
        if not frames:
            continue
        qs = [quality(f) for f in frames]
        q = {k: round(float(np.mean([x[k] for x in qs])), 3) for k in qs[0]}
        # Moderate motion reads as "alive"; a frozen or chaotic shot scores lower.
        motion = 0.0
        if len(frames) > 1:
            a = cv2.cvtColor(cv2.resize(frames[0], (160, 90)), cv2.COLOR_BGR2GRAY).astype(np.float32)
            b = cv2.cvtColor(cv2.resize(frames[-1], (160, 90)), cv2.COLOR_BGR2GRAY).astype(np.float32)
            motion = float(np.abs(a - b).mean() / 255)
        motion_n = max(0.0, 1 - abs(motion - 0.12) / 0.12)
        q["motion"] = round(motion_n, 3)
        q["score"] = round(0.8 * q["score"] + 0.2 * motion_n + 0.05, 3)  # small bonus: clips feel livelier than stills
        mid = frames[len(frames) // 2]
        found = [detect_people(f) for f in frames]
        people = [b for boxes in found for b in boxes]
        cid = f"{item['id']}s{n:02d}"
        thumb = work / "thumbs" / f"{cid}.jpg"
        thumb.parent.mkdir(parents=True, exist_ok=True)
        _thumb(mid, thumb)
        out.append({**item, "cid": cid, "render_src": item["src"], "in": round(start, 3),
                    "max_dur": round(end - start, 3), "ts": item["ts"] + start,
                    "thumb": str(thumb), "hash": _phash(mid),
                    "people": people_union(people), "n_people": max(len(b) for b in found), **q})
    cap.release()
    return out


def analyze(items: list[dict], work: Path) -> list[dict]:
    cands: list[dict] = []
    for item in items:
        print(f"  analyzing {item['name']}")
        if item["kind"] == "photo":
            if (c := analyze_photo(item, work)):
                cands.append(c)
        else:
            cands.extend(analyze_video(item, work))

    # Near-duplicate removal: keep the best of each look-alike group.
    kept: list[dict] = []
    for c in sorted(cands, key=lambda c: -c["score"]):
        if any(c["hash"] - k["hash"] <= 6 for k in kept):
            continue
        kept.append(c)
    for c in kept:
        c["hash"] = str(c["hash"])
    dropped = len(cands) - len(kept)
    if dropped:
        print(f"  removed {dropped} near-duplicate shot(s)")
    return sorted(kept, key=lambda c: c["ts"])
