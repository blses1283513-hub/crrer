"""The director: map scored shots onto the music's beat grid and write an edit plan (JSON).

The plan is the contract between Claude and the renderer. Claude (or a person) may
reorder segments, swap sources, change transitions or captions, then render it.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from . import FPS, HEIGHT, MAX_DURATION, WIDTH
from .music import best_window

STYLES = json.loads((Path(__file__).with_name("styles.json")).read_text())
MIN_SHOT = 0.6  # seconds; anything shorter flickers
MIN_LAST = 1.5  # the closing shot needs time to land under the end fade


def _frame(t: float) -> float:
    return round(round(t * FPS) / FPS, 4)


def _beats_for(style: dict, energy: float, tempo: float) -> int:
    hi, mid, lo = style["beats_per_shot"]
    n = hi if energy > 0.66 else mid if energy > 0.33 else lo
    if tempo > 150:
        n *= 2
    return n


def _cut_grid(rel_beats, energy, downbeats, style, tempo, limit, max_slots, mult=1):
    """Beat-aligned cut points [0, c1, ..., cn] with cn <= limit."""
    cuts, idx = [0.0], 0
    first = True
    while len(cuts) - 1 < max_slots:
        step = (style["hook_beats"] if first else _beats_for(style, energy[idx], tempo)) * mult
        first = False
        nxt = idx + step
        while nxt < len(rel_beats) and rel_beats[nxt] - cuts[-1] < MIN_SHOT:
            nxt += 1
        if nxt >= len(rel_beats) or rel_beats[nxt] > limit:
            break
        cuts.append(rel_beats[nxt])
        idx = nxt
    # End on a downbeat when one is close, so the film finishes on the phrase.
    if len(cuts) > 1:
        last = cuts[-1]
        options = [d for d in downbeats if cuts[-2] + MIN_LAST <= d <= limit and abs(d - last) <= 2.5]
        if options:
            cuts[-1] = min(options, key=lambda d: abs(d - last))
    return cuts


def _select(cands: list[dict], n: int, per_source: int = 3) -> list[dict]:
    ranked = sorted(cands, key=lambda c: -c["score"])
    for cap in (per_source, per_source * 2, 10**6):
        picked, used = [], Counter()
        for c in ranked:
            if used[c["src"]] < cap:
                picked.append(c)
                used[c["src"]] += 1
            if len(picked) == n:
                return picked
    return picked


def _auto_title(chosen: list[dict]) -> str:
    cities = [c["city"] for c in chosen if c.get("city")]
    when = datetime.fromtimestamp(min(c["ts"] for c in chosen)).strftime("%b %Y")
    if cities:
        top = Counter(cities).most_common(2)
        place = top[0][0] if len(top) == 1 else f"{top[0][0]} & {top[1][0]}"
        return f"{place}\n{when}"
    return when


def build_plan(cands: list[dict], music: dict, style_name: str = "balanced",
               max_duration: float = MAX_DURATION, title: str | None = None,
               min_duration: float = 8.0, captions: bool = True) -> dict:
    if style_name not in STYLES:
        raise SystemExit(f"Unknown style {style_name!r}; choose from {', '.join(STYLES)}")
    if not cands:
        raise SystemExit("No usable shots after analysis.")
    style = STYLES[style_name]
    max_duration = min(max_duration, MAX_DURATION)

    usable = min(max_duration, music["duration"])
    start = best_window(music, usable)
    rel, energy = [], []
    for b, e in zip(music["beats"], music["energy"]):
        if start - 1e-3 <= b <= start + usable + 1e-3:
            rel.append(b - start)
            energy.append(e)
    if not rel or rel[0] > 1e-3:
        rel.insert(0, 0.0)
        energy.insert(0, energy[0] if energy else 0.5)
    downbeats = [d - start for d in music["downbeats"] if start <= d <= start + usable]

    # Fewer shots than beats? Hold each one longer instead of making a 5-second film.
    for mult in (1, 2, 3, 4):
        cuts = _cut_grid(rel, energy, downbeats, style, music["tempo"], usable, len(cands), mult)
        if cuts[-1] >= min(min_duration, usable) * 0.95:
            break
    cuts = [_frame(c) for c in cuts]
    n = len(cuts) - 1
    if n < 1:
        raise SystemExit("Music too short to cut a film.")

    chosen = _select(cands, n)
    n = len(chosen)
    cuts = cuts[: n + 1]
    hook = max(chosen, key=lambda c: c["score"])
    story = [hook] + sorted((c for c in chosen if c is not hook), key=lambda c: c["ts"])

    segments = []
    accent_i = 0
    moves_used = Counter()
    for k, c in enumerate(story):
        seg_len = cuts[k + 1] - cuts[k]
        trans = {"type": "cut", "dur": 0.0}
        if k < n - 1:
            nxt = story[k + 1]
            if k > 0 and c.get("city") and nxt.get("city") and c["city"] != nxt["city"]:
                trans = dict(style["location"])
            elif (k + 1) % style["accent_every"] == 0:
                trans = dict(style["accents"][accent_i % len(style["accents"])])
                accent_i += 1
            else:
                trans = dict(style["cut"])
            trans.setdefault("dur", 0.0)
            next_len = cuts[k + 2] - cuts[k + 1]
            trans["dur"] = _frame(min(trans["dur"], 0.5 * next_len, 0.5 * seg_len))
            if trans["type"] != "cut" and trans["dur"] < 2 / FPS:
                trans = {"type": "cut", "dur": 0.0}

        seg = {"cid": c["cid"], "kind": c["kind"], "src": c["render_src"], "name": c["name"],
               "start": cuts[k], "dur": _frame(seg_len), "transition": trans,
               "city": c.get("city"), "time": c["time"], "score": c["score"], "thumb": c["thumb"]}
        need = seg_len + trans["dur"]
        if c["kind"] == "video":
            slack = max(0.0, c["max_dur"] - need)
            seg["in"] = round(c["in"] + slack / 2, 3)
            seg["freeze"] = round(max(0.0, need - c["max_dur"]), 3)
        else:
            landscape = c["width"] > 1.1 * c["height"]
            moves = ["pan_lr", "pan_rl"] if landscape else ["zoom_in", "zoom_out"]
            seg["motion"] = moves[moves_used[landscape] % 2]
            moves_used[landscape] += 1
        segments.append(seg)

    total = cuts[n]
    texts = []
    if captions:
        texts.append({"text": title or _auto_title(story), "start": 0.15,
                      "end": round(min(3.0, max(1.5, cuts[1])), 3), "kind": "title"})
        for k in range(1, n):
            city, prev = story[k].get("city"), story[k - 1].get("city")
            if city and city != prev and k > 1:
                s = segments[k]
                texts.append({"text": city, "start": round(s["start"] + 0.15, 3),
                              "end": round(s["start"] + min(2.2, s["dur"]), 3), "kind": "place"})

    return {
        "version": 1,
        "style": style_name,
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps": FPS},
        "duration": round(total, 3),
        "music": {"path": music["path"], "start": round(start, 3), "tempo": music["tempo"]},
        "grade": style.get("grade", ""),
        "end_fade": style.get("end_fade", 0.6),
        "segments": segments,
        "captions": texts,
    }
