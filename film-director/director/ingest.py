"""Scan a media folder and read capture time, GPS and dimensions for every photo and clip.

Metadata is read from the originals with ExifTool before anything is transcoded,
because FFmpeg drops iPhone GPS tags when remuxing MOV -> MP4.
"""
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

PHOTO_EXT = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tif", ".tiff"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".mts", ".3gp"}

_TIME_TAGS = [
    "DateTimeOriginal",      # photos (local time)
    "CreationDate",          # iPhone QuickTime Keys, local time with offset
    "SubSecDateTimeOriginal",
    "CreateDate",            # QuickTime (UTC) / EXIF
    "MediaCreateDate",
    "FileModifyDate",
]


def _pick(meta: dict, name: str):
    """Return the first value whose tag (any group) is `name`."""
    for key, value in meta.items():
        if key == name or key.endswith(":" + name):
            return value
    return None


def _parse_time(value) -> float | None:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    for fmt in ("%Y:%m:%d %H:%M:%S%z", "%Y:%m:%d %H:%M:%S.%f%z",
                "%Y:%m:%d %H:%M:%S.%f", "%Y:%m:%d %H:%M:%S"):
        try:
            dt = datetime.strptime(text[:32], fmt)
            # Keep wall-clock (local) time so a trip sorts the way it was lived.
            return dt.replace(tzinfo=None).timestamp()
        except ValueError:
            continue
    return None


def _ffprobe(path: Path) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True, check=False,
    )
    try:
        return json.loads(out.stdout or "{}")
    except json.JSONDecodeError:
        return {}


def _video_geometry(path: Path) -> tuple[int, int, float, bool]:
    info = _ffprobe(path)
    duration = float(info.get("format", {}).get("duration") or 0)
    has_audio = False
    width = height = 0
    for stream in info.get("streams", []):
        if stream.get("codec_type") == "audio":
            has_audio = True
        if stream.get("codec_type") == "video" and not width:
            width, height = int(stream.get("width", 0)), int(stream.get("height", 0))
            rotation = 0
            for side in stream.get("side_data_list", []) or []:
                if "rotation" in side:
                    rotation = int(side["rotation"])
            rotation = rotation or int(stream.get("tags", {}).get("rotate", 0) or 0)
            if abs(rotation) % 180 == 90:
                width, height = height, width
    return width, height, duration, has_audio


def scan(media_dir: str | os.PathLike) -> list[dict]:
    """Return one record per usable media file, sorted by capture time."""
    import exiftool  # PyExifTool
    import reverse_geocode

    root = Path(media_dir)
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in PHOTO_EXT | VIDEO_EXT)
    if not files:
        raise SystemExit(f"No photos or videos found in {root}")

    with exiftool.ExifToolHelper() as et:
        metas = et.get_metadata([str(p) for p in files], params=["-n"])

    items = []
    for path, meta in zip(files, metas):
        kind = "photo" if path.suffix.lower() in PHOTO_EXT else "video"
        ts = None
        for tag in _TIME_TAGS:
            ts = _parse_time(_pick(meta, tag))
            if ts:
                break
        ts = ts or path.stat().st_mtime

        lat, lon = _pick(meta, "GPSLatitude"), _pick(meta, "GPSLongitude")
        if lat is None and (iso := _pick(meta, "GPSCoordinates")):
            parts = str(iso).replace(",", " ").split()
            if len(parts) >= 2:
                lat, lon = parts[0], parts[1]
        try:
            lat, lon = float(lat), float(lon)
        except (TypeError, ValueError):
            lat = lon = None

        record = {
            "id": f"m{len(items):03d}",
            "kind": kind,
            "src": str(path.resolve()),
            "name": path.name,
            "ts": ts,
            "time": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M"),
            "lat": lat, "lon": lon, "city": None, "country": None,
        }
        if kind == "video":
            w, h, dur, has_audio = _video_geometry(path)
            if dur < 0.5 or not w:
                continue
            record.update(width=w, height=h, duration=round(dur, 3), has_audio=has_audio)
        else:
            w = _pick(meta, "ImageWidth") or 0
            h = _pick(meta, "ImageHeight") or 0
            if int(_pick(meta, "Orientation") or 1) in (5, 6, 7, 8):
                w, h = h, w
            record.update(width=int(w), height=int(h))
        items.append(record)

    located = [i for i in items if i["lat"] is not None]
    if located:
        places = reverse_geocode.search([(i["lat"], i["lon"]) for i in located])
        for item, place in zip(located, places):
            item["city"], item["country"] = place.get("city"), place.get("country")

    items.sort(key=lambda i: i["ts"])
    return items
