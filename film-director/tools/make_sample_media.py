"""Generate a synthetic "trip" (photos + clips with time/GPS tags) and a 120 BPM beat track for testing.

Usage: python tools/make_sample_media.py samples/
"""
from __future__ import annotations

import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

PLACES = [  # (label, lat, lon, date)
    ("Taipei", 25.0330, 121.5654, "2026:10:01"),
    ("Jiufen", 25.1092, 121.8445, "2026:10:02"),
    ("Hualien", 23.9872, 121.6015, "2026:10:03"),
]


def photo(path: Path, size, hue: int, label: str, seed: int) -> None:
    rng = np.random.default_rng(seed)
    w, h = size
    y = np.linspace(0, 1, h)[:, None]
    base = np.full((h, w, 3), hue % 255, np.float32)
    sky = np.array([90 + hue % 120, 140, 220 - hue % 80], np.float32)
    ground = np.array([60, 110 + hue % 100, 70], np.float32)
    grad = sky * (1 - y[..., None]) + ground * y[..., None]
    img = (0.2 * base + 0.8 * grad + rng.normal(0, 10, (h, w, 3))).clip(0, 255).astype(np.uint8)
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    for _ in range(25):  # "buildings / trees" for texture and sharpness
        x0, x1 = sorted(rng.integers(0, w, 2))
        top = int(rng.integers(h // 3, h - 10))
        d.rectangle([x0, top, x1, h], fill=tuple(int(c) for c in rng.integers(20, 200, 3)))
    d.ellipse([w * 0.7, h * 0.08, w * 0.7 + h * 0.12, h * 0.2], fill=(255, 230, 150))
    d.text((20, 20), label, fill=(255, 255, 255))
    im.save(path, quality=92)


def blurry_copy(src: Path, dst: Path) -> None:
    Image.open(src).filter(ImageFilter.GaussianBlur(12)).save(dst, quality=92)


def clip(path: Path, src_a: str, src_b: str, size: str, secs: float) -> None:
    half = secs / 2
    subprocess.run(["ffmpeg", "-y", "-v", "error",
                    "-f", "lavfi", "-t", str(half), "-i", f"{src_a}=size={size}:rate=30",
                    "-f", "lavfi", "-t", str(half), "-i", f"{src_b}=size={size}:rate=30",
                    "-f", "lavfi", "-i", f"sine=frequency=440:duration={secs}",
                    "-filter_complex", "[0:v][1:v]concat=n=2:v=1[v]", "-map", "[v]", "-map", "2:a",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)], check=True)


def beat_track(path: Path, bpm=120, secs=75, sr=44100) -> None:
    t = np.arange(int(secs * sr)) / sr
    beat = 60 / bpm
    out = np.zeros_like(t)
    for i, start in enumerate(np.arange(0, secs, beat)):
        n = int(start * sr)
        k = np.arange(int(0.25 * sr))
        accent = 1.0 if i % 4 == 0 else 0.6
        kick = accent * np.sin(2 * np.pi * (50 + 80 * np.exp(-k / 800)) * k / sr) * np.exp(-k / 4000)
        out[n:n + len(k)] += kick[: len(out) - n]
        h = int((start + beat / 2) * sr)
        hk = np.arange(int(0.05 * sr))
        hat = np.random.default_rng(i).normal(0, 0.15, len(hk)) * np.exp(-hk / 300)
        out[h:h + len(hk)] += hat[: max(0, len(out) - h)]
    chords = [220.0, 174.6, 261.6, 196.0]
    bar = 4 * beat
    pad = 0.08 * np.sin(2 * np.pi * np.array([chords[int(x // bar) % 4] for x in t]) * t)
    swell = 0.6 + 0.4 * np.clip((t - 20) / 10, 0, 1)  # gets louder after 20 s: an energy change for the planner
    out = (out + pad) * swell
    out = (out / np.abs(out).max() * 0.9 * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(out.tobytes())


def tag(path: Path, date: str, hhmm: str, lat: float, lon: float, video=False) -> None:
    stamp = f"{date} {hhmm}:00"
    args = ["exiftool", "-q", "-overwrite_original"]
    if video:
        args += [f"-Keys:CreationDate={stamp}+08:00", f"-Keys:GPSCoordinates={lat}, {lon}", "-api", "QuickTimeUTC"]
    else:
        args += [f"-DateTimeOriginal={stamp}", "-OffsetTimeOriginal=+08:00",
                 f"-GPSLatitude={lat}", "-GPSLatitudeRef=N", f"-GPSLongitude={lon}", "-GPSLongitudeRef=E"]
    subprocess.run(args + [str(path)], check=True)


def main(out_dir: str) -> None:
    out = Path(out_dir)
    media = out / "media"
    media.mkdir(parents=True, exist_ok=True)
    seed = 0
    for p, (city, lat, lon, date) in enumerate(PLACES):
        for j in range(4):
            seed += 1
            size = (3000, 2000) if j % 2 == 0 else (1500, 2000)
            f = media / f"{city.lower()}_{j}.jpg"
            photo(f, size, hue=40 * p + 15 * j, label=f"{city} #{j}", seed=seed)
            tag(f, date, f"{9 + 2 * j:02d}:1{j}", lat, lon)
        dup = media / f"{city.lower()}_0_burst.jpg"  # near-duplicate that should be dropped
        blurry_copy(media / f"{city.lower()}_0.jpg", dup)
        tag(dup, date, "09:11", lat, lon)
        v = media / f"{city.lower()}_clip.mp4"
        clip(v, ["testsrc2", "mandelbrot", "life"][p], "smptehdbars", "1920x1080" if p != 1 else "1080x1920", 6)
        tag(v, date, "16:30", lat, lon, video=True)
    beat_track(out / "music_120bpm.wav")
    print(f"Sample trip written to {media} and {out / 'music_120bpm.wav'}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "samples")
