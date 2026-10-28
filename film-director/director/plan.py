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


def _snap(t: float, accents: list[float], tol: float) -> float:
    if not accents:
        return t
    near = min(accents, key=lambda a: abs(a - t))
    return near if abs(near - t) <= tol else t


def _burst_grid(rel_beats, accents, style, tempo, limit, n_avail):
    """"Film" pacing: opening hold, a burst of quick cuts, a long hold, a second burst,
    medium shots, then a long closing hold. Cuts snap to musical accents (onsets or beats)
    rather than a strict beat grid. Returns (cuts, roles)."""
    p = style["pattern"]
    beat = 60 / max(tempo, 1)
    burst_len = p["burst_beats"] * beat
    while burst_len < 0.36:
        burst_len *= 2
    if n_avail < 5:  # too few shots for bursts: open, mids, end
        b1 = b2 = 0
    else:
        b1 = b2 = min(p["burst"], max(3, (n_avail - 3) // 3))
    if b1 + b2 + 3 > n_avail:
        b1 = b2 = 0
    m_max = max(0, n_avail - 3 - b1 - b2) if b1 else max(0, n_avail - 2)

    def layout(m):
        roles, lens = ["open"], [p["open"]]
        if b1:
            roles += ["burst"] * b1 + ["hold"] + ["burst"] * b2
            lens += [burst_len] * b1 + [p["hold"]] + [burst_len] * b2
        roles += ["mid"] * m
        lens += [p["mid"][i % len(p["mid"])] for i in range(m)]
        return roles + ["end"], lens + [p["end"]]

    m = m_max
    roles, lens = layout(m)
    while sum(lens) > limit and m > 0:
        m -= 1
        roles, lens = layout(m)
    if sum(lens) > limit:  # still too long: shrink the long holds proportionally
        fixed = sum(l for r, l in zip(roles, lens) if r == "burst")
        scale = max(0.3, (limit - fixed) / max(1e-6, sum(lens) - fixed))
        lens = [l if r == "burst" else l * scale for r, l in zip(roles, lens)]

    grid = sorted(set(accents) | set(rel_beats))
    cuts, t = [0.0], 0.0
    for r, l in zip(roles[:-1], lens[:-1]):
        t = _snap(t + l, grid, 0.08 if r == "burst" else 0.15)
        t = max(t, cuts[-1] + 0.3)
        cuts.append(t)
    end = min(limit, cuts[-1] + lens[-1])
    end = _snap(end, [b for b in rel_beats if b <= limit], 0.3)
    cuts.append(max(end, cuts[-1] + 1.5))
    return cuts, roles


def _fit_holds(story: list[dict], roles: list[str], cuts: list[float]) -> list[dict]:
    """Move the strongest nearby shots onto the long holds, keeping roughly chronological order.
    A long hold prefers a clip long enough to fill it, or a photo (which can pan for any length)."""
    story = list(story)
    locked = {0}
    for k, role in enumerate(roles):
        if role not in ("hold", "end") or k in locked:
            continue
        need = cuts[k + 1] - cuts[k]

        def fit(c):
            if c["kind"] == "video":
                return c["score"] + (0.1 if c["max_dur"] >= need else -0.25)
            return c["score"]

        window = [j for j in range(max(1, k - 3), min(len(story), k + 4)) if j not in locked]
        best = max(window, key=lambda j: fit(story[j]))
        story[k], story[best] = story[best], story[k]
        locked.add(k)
    return story


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

    roles = None
    if style.get("pacing") == "bursts":
        accents = [o - start for o in music.get("onsets", []) if start <= o <= start + usable]
        n_avail = len(_select(cands, len(cands)))
        cuts, roles = _burst_grid(rel, accents, style, music["tempo"], usable, n_avail)
    else:
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
    if len(chosen) < n:
        # Burst layouts depend on the shot count, so a shortfall means the last slots go unused.
        cuts = cuts[: len(chosen)] + [cuts[-1]]
        roles = roles[: len(chosen) - 1] + ["end"] if roles else None
    n = len(chosen)
    cuts = cuts[: n + 1]
    hook = max(chosen, key=lambda c: c["score"])
    story = [hook] + sorted((c for c in chosen if c is not hook), key=lambda c: c["ts"])
    if roles:
        story = _fit_holds(story, roles, cuts)

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
            if roles and "burst" in (roles[k], roles[k + 1]):
                trans = {"type": "cut", "dur": 0.0}  # quick-cut runs stay hard cuts
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
    if captions and style.get("title_look") == "film":
        # Small spaced kicker over a bold title, held across the first two shots.
        kicker, main = style.get("kicker", ""), None
        if title and "|" in title:
            kicker, main = (s.strip() for s in title.split("|", 1))
        elif title:
            main = title
        if not main:
            countries = Counter(c["country"] for c in story if c.get("country"))
            cities = Counter(c["city"] for c in story if c.get("city"))
            main = (countries.most_common(1)[0][0] if len(cities) > 1 and countries
                    else cities.most_common(1)[0][0] if cities
                    else datetime.fromtimestamp(story[0]["ts"]).strftime("%B %Y"))
        end = cuts[1] + 2.0
        texts.append({"text": main.upper(), "kicker": kicker.upper(), "start": 0.8,
                      "end": round(max(2.5, min(6.0, end, total - 1.0)), 3), "kind": "title", "look": "film"})
    elif captions:
        texts.append({"text": title or _auto_title(story), "start": 0.15,
                      "end": round(min(3.0, max(1.5, cuts[1])), 3), "kind": "title"})
    if captions and style.get("place_captions", True):
        for k in range(1, n):
            city, prev = story[k].get("city"), story[k - 1].get("city")
            if city and city != prev and k > 1:
                s = segments[k]
                texts.append({"text": city, "start": round(s["start"] + 0.15, 3),
                              "end": round(s["start"] + min(2.2, s["dur"]), 3), "kind": "place"})

    return {
        "version": 1,
        "style": style_name,
        "canvas": {"width": WIDTH, "height": HEIGHT, "fps": FPS,
                   "frame": style.get("frame", [WIDTH, HEIGHT])},
        "duration": round(total, 3),
        "music": {"path": music["path"], "start": round(start, 3), "tempo": music["tempo"]},
        "grade": style.get("grade", ""),
        "end_fade": style.get("end_fade", 0.6),
        "audio_fade": style.get("audio_fade", 1.5),
        "segments": segments,
        "captions": texts,
    }
