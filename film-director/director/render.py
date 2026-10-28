"""Render an edit plan with FFmpeg.

1. Every segment is normalized to 1080x1920, 30 fps CFR, yuv420p (xfade requires identical inputs).
   Photos get slow pan / zoom motion; clips are cover-cropped to 9:16.
2. Segments are chained with xfade. Hard cuts are one-frame fades, so every cut still lands
   on its beat. Offsets equal the planned cut times: the transition starts exactly on the beat.
3. Grade, captions, end fade and the trimmed music are applied in the same final pass.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image

from . import FPS, HEIGHT, WIDTH

ASSET_FONTS = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FILM_TITLE_FONT = ASSET_FONTS / "Anton-Regular.ttf"        # bold condensed (OFL)
FILM_KICKER_FONT = ASSET_FONTS / "CrimsonText-Regular.ttf"  # classic serif (OFL)
FILM_YELLOW = "0xF2B21B"

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def _run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-15:])
        raise RuntimeError(f"ffmpeg failed:\n{tail}")


def _font() -> str:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return path
    found = shutil.which("fc-match") and subprocess.run(
        ["fc-match", "-f", "%{file}", "sans:bold"], capture_output=True, text=True).stdout.strip()
    if found:
        return found
    raise SystemExit("No font found for captions; install DejaVu fonts or run with --no-captions.")


def _q(path: str | Path) -> str:
    """Quote a path for use inside an FFmpeg filter argument."""
    return "'" + str(path).replace("\\", "/").replace("'", r"'\''").replace(":", r"\:") + "'"


def _transition_len(seg: dict, last: bool) -> float:
    if last:
        return 0.0
    t = seg["transition"]
    return 1 / FPS if t["type"] == "cut" or t["dur"] <= 0 else t["dur"]


def _lead(seg: dict | None) -> float:
    """How far before the cut a transition starts (centred transitions straddle the beat)."""
    if not seg or seg["transition"]["type"] == "cut":
        return 0.0
    return float(seg["transition"].get("lead", 0.0))


def _cover(w: float, h: float, fw: int, fh: int) -> tuple[float, float]:
    """Largest window with the frame's shape that fits inside a w x h picture."""
    a = fw / fh
    return (h * a, h) if w / h > a else (w, w / a)


def _people_window(w, h, fw, fh, people):
    """Where to put the cover window so it holds everyone, or None if they can't all fit."""
    cw, ch = _cover(w, h, fw, fh)
    px0, py0, px1, py1 = people[0] * w, people[1] * h, people[2] * w, people[3] * h
    if px1 - px0 > cw + 0.5 or py1 - py0 > ch + 0.5:
        return None

    def place(c, size, lo_edge, hi_edge, total):
        lo, hi = max(0.0, hi_edge - size), min(lo_edge, total - size)
        return min(max(c - size / 2, lo), hi)

    x0 = place((px0 + px1) / 2, cw, px0, px1, w)
    y0 = place((py0 + py1) / 2, ch, py0, py1, h)
    return x0, y0, cw, ch, (px0, py0, px1, py1)


def _fit_graph(fw: int, fh: int, pre: str = "") -> str:
    """Whole picture, nothing cropped; a blurred, darkened copy of itself fills the frame."""
    return (f"{pre}split[a][b];"
            f"[a]scale={fw}:{fh}:force_original_aspect_ratio=increase,crop={fw}:{fh},"
            f"gblur=sigma=40,eq=brightness=-0.08:saturation=0.8[bg];"
            f"[b]scale={fw}:{fh}:force_original_aspect_ratio=decrease:flags=lanczos[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,fps={FPS},format=yuv420p")


def _photo_filter(seg: dict, length: float, fw: int, fh: int) -> str:
    img = Image.open(seg["src"])
    w, h = img.size
    frames = max(1, round(length * FPS))
    motion = seg.get("motion", "zoom_in")
    # Lift very dark photos (night shots) so they still read after the grade.
    luma = sum(img.convert("L").resize((64, 64)).getdata()) / (64 * 64 * 255)
    lift = ",eq=gamma=1.45:saturation=1.1" if luma < 0.18 else ",eq=gamma=1.2" if luma < 0.28 else ""

    people = seg.get("people")
    if people:
        win = _people_window(w, h, fw, fh, people)
        if win is None:  # everyone can't fit in a crop: show the whole photo instead
            seg["framing"] = "fit"
            return _fit_graph(fw, fh, lift.lstrip(",") + "," if lift else "")
        x0, y0, cw, ch, (px0, py0, px1, py1) = win
        k = 2 * fw / cw  # crop window -> 2x working resolution
        qx0, qy0, qx1, qy1 = (px0 - x0) * k, (py0 - y0) * k, (px1 - x0) * k, (py1 - y0) * k
        zmax = max(1.0, min(1.10, 2 * fw / (qx1 - qx0), 2 * fh / (qy1 - qy0)))
        if motion == "zoom_in":
            z = f"1+{zmax - 1:.4f}*on/{frames}"
        elif motion == "zoom_out":
            z = f"{zmax:.4f}-{zmax - 1:.4f}*on/{frames}"
        else:
            z = f"{zmax:.4f}"
        # Every frame's window is clamped so it still contains everyone.
        xlo, xhi = f"max(0,{qx1:.1f}-iw/zoom)", f"min({qx0:.1f},iw-iw/zoom)"
        ylo, yhi = f"max(0,{qy1:.1f}-ih/zoom)", f"min({qy0:.1f},ih-ih/zoom)"
        if motion == "pan_lr":
            x = f"clip({xlo}+({xhi}-{xlo})*on/{frames},{xlo},{xhi})"
        elif motion == "pan_rl":
            x = f"clip({xhi}-({xhi}-{xlo})*on/{frames},{xlo},{xhi})"
        else:
            x = f"clip({(qx0 + qx1) / 2:.1f}-iw/zoom/2,{xlo},{xhi})"
        y = f"clip({(qy0 + qy1) / 2:.1f}-ih/zoom/2,{ylo},{yhi})"
        seg["framing"] = "people-safe crop"
        return (f"crop={cw:.0f}:{ch:.0f}:{x0:.0f}:{y0:.0f},scale={2 * fw}:{2 * fh}:flags=lanczos{lift},"
                f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={fw}x{fh}:fps={FPS},setsar=1,format=yuv420p")

    seg["framing"] = "crop"
    if motion.startswith("pan"):
        # 10% overscan guarantees some travel even when the photo already matches the frame shape.
        scale = max(fw / w, fh / h) * 1.10
        sw, sh = round(w * scale / 2) * 2, round(h * scale / 2) * 2
        travel = min(sw - fw, round(0.18 * fw * length))  # gentle: ~200 px per second
        x0 = (sw - fw - travel) / 2
        x = f"{x0:.1f}+{travel}*t/{length:.4f}" if motion == "pan_lr" else f"{x0 + travel:.1f}-{travel}*t/{length:.4f}"
        return (f"scale={sw}:{sh}:flags=lanczos,crop={fw}:{fh}:x='{x}':y='(ih-{fh})/2'{lift},"
                f"setsar=1,fps={FPS},format=yuv420p")
    z = f"1+0.10*on/{frames}" if motion == "zoom_in" else f"1.10-0.10*on/{frames}"
    # Work at 2x resolution so zoompan's integer positions do not jitter.
    return (f"scale={2 * fw}:{2 * fh}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={2 * fw}:{2 * fh}{lift},"
            f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={fw}x{fh}:fps={FPS},"
            f"setsar=1,format=yuv420p")


def _video_filter(seg: dict, fw: int, fh: int) -> str:
    people, w, h = seg.get("people"), seg.get("width"), seg.get("height")
    if people and w and h:
        win = _people_window(w, h, fw, fh, people)
        if win is None:
            seg["framing"] = "fit"
            return _fit_graph(fw, fh, f"fps={FPS},")
        x0, y0, cw, ch, _ = win
        seg["framing"] = "people-safe crop"
        return f"fps={FPS},crop={cw:.0f}:{ch:.0f}:{x0:.0f}:{y0:.0f},scale={fw}:{fh},setsar=1"
    seg["framing"] = "crop"
    return f"fps={FPS},scale={fw}:{fh}:force_original_aspect_ratio=increase,crop={fw}:{fh},setsar=1"


def render_segment(seg: dict, length: float, out: Path, frame=(WIDTH, HEIGHT)) -> None:
    fw, fh = frame
    frames = max(1, round(length * FPS))
    common = ["-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "17", "-pix_fmt", "yuv420p",
              "-r", str(FPS), "-video_track_timescale", str(FPS * 512), "-frames:v", str(frames), str(out)]
    if seg["kind"] == "photo":
        cmd = ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", str(FPS), "-t", f"{length + 0.5:.3f}",
               "-i", seg["src"], "-vf", _photo_filter(seg, length, fw, fh)] + common
    else:
        # Pad generously with the last frame; -frames:v trims to the exact length.
        vf = _video_filter(seg, fw, fh) + f",tpad=stop_mode=clone:stop_duration={length:.3f},format=yuv420p"
        cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{seg['in']:.3f}", "-i", seg["src"],
               "-t", f"{length + 0.2:.3f}", "-vf", vf] + common
    _run(cmd)


def _film_title(cap: dict, i: int, work: Path, fh: int, alpha: str, a: float, b: float) -> list[str]:
    """Small letter-spaced serif kicker over a bold condensed yellow title (the reference look)."""
    out = []
    size = round(fh * 0.115)
    title = work / "captions" / f"cap{i}.txt"
    title.write_text(cap["text"], encoding="utf-8")
    common = f"fontcolor={FILM_YELLOW}:x=(w-text_w)/2:enable='between(t,{a},{b})':alpha='{alpha}'"
    out.append(f"drawtext=fontfile={_q(FILM_TITLE_FONT)}:textfile={_q(title)}:fontsize={size}:"
               f"y={cap.get('y', 0.5)}*h-text_h/2+{round(size * 0.18)}:shadowcolor=black@0.35:shadowx=2:shadowy=2:{common}")
    if cap.get("kicker"):
        kick = work / "captions" / f"cap{i}k.txt"
        kick.write_text("  ".join(" ".join(word) for word in cap["kicker"].split()), encoding="utf-8")
        ksize = round(fh * 0.034)
        out.append(f"drawtext=fontfile={_q(FILM_KICKER_FONT)}:textfile={_q(kick)}:fontsize={ksize}:"
                   f"y={cap.get('y', 0.5)}*h-{round(size * 0.55)}-{ksize}:shadowcolor=black@0.5:shadowx=1:shadowy=1:{common}")
    return out


def _caption_filters(plan: dict, work: Path) -> list[str]:
    if not plan.get("captions"):
        return []
    fh = plan["canvas"].get("frame", [WIDTH, HEIGHT])[1]
    font = _font()
    out = []
    for i, cap in enumerate(plan["captions"]):
        txt = work / "captions" / f"cap{i}.txt"
        txt.parent.mkdir(parents=True, exist_ok=True)
        txt.write_text(cap["text"], encoding="utf-8")
        a, b = cap["start"], cap["end"]
        fade = 0.25
        alpha = f"if(lt(t,{a}+{fade}),(t-{a})/{fade},if(gt(t,{b}-{fade}),({b}-t)/{fade},1))"
        if cap.get("look") == "film":
            slow = f"if(lt(t,{a}+0.5),(t-{a})/0.5,if(gt(t,{b}-0.5),({b}-t)/0.5,1))"
            out += _film_title(cap, i, work, fh, slow, a, b)
            continue
        if cap.get("kind") == "title":
            size, y = 92, "(h-text_h)/2-h*0.06"
        else:
            # Lower third, kept above Instagram's caption/button area (bottom ~20%).
            size, y = 64, "h*0.66"
        out.append(
            f"drawtext=fontfile={_q(font)}:textfile={_q(txt)}:fontsize={size}:fontcolor=white:"
            f"text_align=C:line_spacing=12:borderw=3:bordercolor=black@0.35:"
            f"shadowcolor=black@0.45:shadowx=3:shadowy=4:x=(w-text_w)/2:y={y}:"
            f"enable='between(t,{a},{b})':alpha='{alpha}'")
    return out


def render(plan: dict, work: Path, out: Path, keep_segments: bool = False) -> Path:
    work = Path(work)
    seg_dir = work / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)
    segs = plan["segments"]
    n = len(segs)
    frame = tuple(plan["canvas"].get("frame", [WIDTH, HEIGHT]))
    files = []
    for k, seg in enumerate(segs):
        # Visible span: from (start - previous lead) to (next cut - own lead + own transition).
        prev = segs[k - 1] if k else None
        length = seg["dur"] + _transition_len(seg, k == n - 1) - (_lead(seg) if k < n - 1 else 0) + _lead(prev)
        path = seg_dir / f"seg{k:03d}.mp4"
        render_segment(seg, length, path, frame)
        print(f"  segment {k + 1}/{n}: {seg['name']} ({seg['kind']}, {length:.2f}s, {seg.get('framing')})")
        files.append(path)

    total = plan["duration"]
    lines = []
    prev = "0:v"
    for k in range(1, n):
        t = segs[k - 1]["transition"]
        kind = "fade" if t["type"] == "cut" else t["type"]
        dur = _transition_len(segs[k - 1], False)
        label = f"x{k}"
        offset = segs[k]["start"] - _lead(segs[k - 1])  # centred: the transition's middle is on the beat
        lines.append(f"[{prev}][{k}:v]xfade=transition={kind}:duration={dur:.4f}:offset={offset:.4f}[{label}]")
        prev = label

    post = [f for f in [plan.get("grade")] if f]
    post += _caption_filters(plan, work)
    if frame != (WIDTH, HEIGHT):  # letterbox the film frame inside the 9:16 canvas
        post.append(f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=black")
    ef = plan.get("end_fade", 0.6)
    post += [f"fade=t=out:st={max(0, total - ef):.3f}:d={ef}", "format=yuv420p"]
    lines.append(f"[{prev}]" + ",".join(post) + "[vout]")

    music = plan["music"]
    afade = min(plan.get("audio_fade", 1.5), total / 4)
    lines.append(f"[{n}:a]atrim=start={music['start']:.3f}:duration={total:.3f},asetpts=PTS-STARTPTS,"
                 f"afade=t=in:d=0.05,afade=t=out:st={total - afade:.3f}:d={afade:.3f}[aout]")
    script = work / "filtergraph.txt"
    script.write_text(";\n".join(lines))

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["ffmpeg", "-y", "-v", "error"]
    for f in files:
        cmd += ["-i", str(f)]
    cmd += ["-i", music["path"], "-filter_complex_script", str(script),
            "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-maxrate", "10M", "-bufsize", "20M",
            "-profile:v", "high", "-pix_fmt", "yuv420p",
            "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(out)]
    print("  assembling final film")
    _run(cmd)
    if not keep_segments:
        shutil.rmtree(seg_dir, ignore_errors=True)
    return out


def verify(path: Path, max_duration: float = 60.0) -> dict:
    """Check the deliverable against the social-media spec."""
    info = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True).stdout)
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    has_audio = any(s["codec_type"] == "audio" for s in info["streams"])
    duration = float(info["format"]["duration"])
    report = {
        "file": str(path), "width": v["width"], "height": v["height"],
        "fps": v["r_frame_rate"], "duration": round(duration, 3), "audio": has_audio,
        "size_mb": round(int(info["format"]["size"]) / 1e6, 2),
    }
    problems = []
    if (v["width"], v["height"]) != (WIDTH, HEIGHT):
        problems.append("not 1080x1920")
    if duration > max_duration + 0.05:
        problems.append(f"longer than {max_duration:.0f}s")
    if not has_audio:
        problems.append("no audio track")
    report["ok"] = not problems
    report["problems"] = problems
    return report
