"""Command line: python -m director <command> ...

  make     --media DIR --music FILE   analyze + plan + storyboard + render + verify
  analyze  --media DIR                 -> work/analysis.json (scored candidate shots)
  plan     --music FILE                -> work/plan.json + work/storyboard.jpg
  render                               work/plan.json -> output/reel.mp4
  verify   FILE                        check 9:16, <= 60 s, audio
  styles                               list editing styles
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import MAX_DURATION


def _save(obj, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False))


def _palette(text: str | None) -> dict | None:
    """'impact=fadewhite:0.25,zoomin:0.5;move=hblur:0.5;soft=dissolve:1.5' -> palette dict."""
    if not text:
        return None
    out = {}
    for part in text.split(";"):
        kind, _, items = part.partition("=")
        out[kind.strip()] = [[n.strip(), float(b)] for n, b in (i.split(":") for i in items.split(",") if i)]
    return out


def cmd_analyze(a) -> list[dict]:
    from .analyze import analyze
    from .ingest import scan
    print(f"Scanning {a.media}")
    items = scan(a.media)
    print(f"  {sum(i['kind'] == 'photo' for i in items)} photos, {sum(i['kind'] == 'video' for i in items)} clips")
    cands = analyze(items, Path(a.work))
    _save(cands, Path(a.work) / "analysis.json")
    print(f"  {len(cands)} candidate shots -> {Path(a.work) / 'analysis.json'}")
    return cands


def cmd_plan(a, cands=None) -> dict:
    from .music import analyze_music
    from .plan import build_plan
    from .storyboard import storyboard
    work = Path(a.work)
    cands = cands if cands is not None else json.loads((work / "analysis.json").read_text())
    print(f"Analyzing music {a.music}")
    music = analyze_music(str(Path(a.music).resolve()))
    _save(music, work / "music.json")
    print(f"  {music['tempo']} BPM, {len(music['beats'])} beats, {music['duration']:.1f}s")
    plan = build_plan(cands, music, a.style, a.max_duration, a.title, captions=not a.no_captions,
                      keep_order=a.keep_order, palette=_palette(a.palette))
    _save(plan, work / "plan.json")
    sb = storyboard(plan, work / "storyboard.jpg")
    print(f"  plan: {len(plan['segments'])} shots, {plan['duration']:.2f}s -> {work / 'plan.json'}")
    print(f"  storyboard -> {sb}")
    return plan


def cmd_render(a, plan=None) -> None:
    from .render import render, verify
    work = Path(a.work)
    plan = plan or json.loads((Path(a.plan) if a.plan else work / "plan.json").read_text())
    print("Rendering")
    out = render(plan, work, Path(a.out), keep_segments=a.keep_segments)
    report = verify(out, a.max_duration)
    print(json.dumps(report, indent=2))
    if not report["ok"]:
        raise SystemExit("Output failed verification: " + ", ".join(report["problems"]))


def main() -> None:
    p = argparse.ArgumentParser(prog="director", description="Travel film director")
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp, media=False, music=False, render=False):
        sp.add_argument("--work", default="work", help="scratch folder (default: work)")
        if media:
            sp.add_argument("--media", required=True, help="folder of photos and clips")
        if music:
            sp.add_argument("--music", required=True, help="soundtrack (wav/mp3/m4a)")
            sp.add_argument("--style", default="balanced", help="punchy | balanced | cinematic")
            sp.add_argument("--title", help="opening title (default: place + month)")
            sp.add_argument("--no-captions", action="store_true")
            sp.add_argument("--palette", help='custom transitions per musical moment, e.g. '
                            '"impact=fadewhite:0.25,zoomin:0.5;move=hblur:0.5;soft=dissolve:1.5" '
                            "(name:length-in-beats)")
            sp.add_argument("--keep-order", action="store_true",
                            help="keep shots in time order (no hook shot moved to the front)")
        sp.add_argument("--max-duration", type=float, default=MAX_DURATION, help="seconds, capped at 60")
        if render:
            sp.add_argument("--out", default="output/reel.mp4")
            sp.add_argument("--plan", help="plan.json to render (default: <work>/plan.json)")
            sp.add_argument("--keep-segments", action="store_true")

    common(sub.add_parser("make"), media=True, music=True, render=True)
    common(sub.add_parser("analyze"), media=True)
    common(sub.add_parser("plan"), music=True)
    common(sub.add_parser("render"), render=True)
    v = sub.add_parser("verify")
    v.add_argument("file")
    v.add_argument("--max-duration", type=float, default=MAX_DURATION)
    sub.add_parser("styles")

    a = p.parse_args()
    if a.cmd == "make":
        a.plan = None
        cmd_render(a, cmd_plan(a, cmd_analyze(a)))
    elif a.cmd == "analyze":
        cmd_analyze(a)
    elif a.cmd == "plan":
        cmd_plan(a)
    elif a.cmd == "render":
        cmd_render(a)
    elif a.cmd == "verify":
        from .render import verify
        print(json.dumps(verify(Path(a.file), a.max_duration), indent=2))
    elif a.cmd == "styles":
        from .plan import STYLES
        for name, s in STYLES.items():
            print(f"{name:10s} {s['description']}")


if __name__ == "__main__":
    main()
