"""Contact-sheet preview of an edit plan, for approval before rendering."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

TW, TH, PAD, LABEL, COLS = 216, 384, 14, 70, 6


def _font(size: int):
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/System/Library/Fonts/Supplemental/Arial.ttf"):
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def storyboard(plan: dict, out: Path) -> Path:
    segs = plan["segments"]
    rows = (len(segs) + COLS - 1) // COLS
    head = 56
    sheet = Image.new("RGB", (COLS * (TW + PAD) + PAD, head + rows * (TH + LABEL + PAD) + PAD), (18, 20, 24))
    d = ImageDraw.Draw(sheet)
    small, big = _font(15), _font(22)
    title = " / ".join(c["text"].replace("\n", " ") for c in plan["captions"][:1]) or "Untitled"
    d.text((PAD, 16), f"{title}  ·  {plan['style']}  ·  {plan['duration']:.1f}s  ·  {len(segs)} shots  ·  "
                      f"{plan['music']['tempo']:.0f} BPM", fill=(240, 240, 240), font=big)
    for k, s in enumerate(segs):
        x = PAD + (k % COLS) * (TW + PAD)
        y = head + (k // COLS) * (TH + LABEL + PAD)
        try:
            thumb = Image.open(s["thumb"]).convert("RGB").resize((TW, TH))
        except Exception:
            thumb = Image.new("RGB", (TW, TH), (60, 60, 60))
        sheet.paste(thumb, (x, y))
        tag = "VIDEO" if s["kind"] == "video" else s.get("motion", "photo").upper()
        d.rectangle([x, y, x + 8 + len(tag) * 9, y + 22], fill=(0, 0, 0))
        d.text((x + 4, y + 3), tag, fill=(255, 200, 120), font=small)
        trans = s["transition"]["type"] if k < len(segs) - 1 else "end"
        d.text((x, y + TH + 6), f"#{k + 1}  {s['start']:5.2f}s  +{s['dur']:.2f}s", fill=(230, 230, 230), font=small)
        d.text((x, y + TH + 26), f"→ {trans}", fill=(251, 138, 76), font=small)
        d.text((x, y + TH + 46), (s.get("city") or s["name"])[:24], fill=(150, 155, 165), font=small)
    sheet.save(out, quality=88)
    return out
