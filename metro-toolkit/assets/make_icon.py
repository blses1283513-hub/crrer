"""Draw the metro-toolkit icon: a 3D extruded "M" in the dashboard's series blue on a wafer.

Run:  python assets/make_icon.py   ->  assets/metro-toolkit.ico (16-256 px) and assets/metro-toolkit.png (preview)
Only needs Pillow (installed with matplotlib).
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
S = 1024  # master canvas; every size is reduced from it
SERIES_BLUE = (42, 120, 214)  # viz.SERIES[0]
BLUES = [(13, 54, 107), (24, 79, 149), (37, 106, 191)]  # viz.SEQ_BLUE, darkest first (the extrusion sides)
SIZES = [16, 24, 32, 48, 64, 128, 256]


def wafer(size: int = S) -> Image.Image:
    """A silver wafer disc with a bevelled rim, a flat notch at the bottom and a faint die grid."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    c, r = size / 2, size * 0.47
    # rim shadow, then the disc as a radial gradient (light top-left)
    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).ellipse([c - r, c - r + size * 0.025, c + r, c + r + size * 0.025], fill=(20, 40, 70, 110))
    img.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(size * 0.012)))
    disc = Image.new("RGBA", (size, size))
    px = disc.load()
    for y in range(size):
        for x in range(size):
            d = math.hypot(x - c, y - c) / r
            lit = 1 - 0.5 * (((x - c) + (y - c)) / (2 * r)) * 0.6  # light from the top-left
            v = max(0.0, min(1.0, lit)) * (1 - 0.1 * d)
            px[x, y] = (int(176 + 44 * v - 44), int(192 + 40 * v - 40), int(216 + 26 * v - 26), 255)
    mask = Image.new("L", (size, size), 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([c - r, c - r, c + r, c + r], fill=255)
    md.ellipse([c - size * 0.06, c + r - size * 0.045, c + size * 0.06, c + r + size * 0.075], fill=0)  # notch
    disc.putalpha(mask)
    img.alpha_composite(disc)
    d = ImageDraw.Draw(img)
    # die grid, faint (it fades away at small sizes)
    grid = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grid)
    step = size * 0.115
    k = -6
    while k <= 6:
        gd.line([c + k * step, c - r, c + k * step, c + r], fill=(60, 100, 160, 38), width=max(1, size // 300))
        gd.line([c - r, c + k * step, c + r, c + k * step], fill=(60, 100, 160, 38), width=max(1, size // 300))
        k += 1
    grid.putalpha(ImageChops.multiply(grid.getchannel("A"), mask))
    img.alpha_composite(grid)
    # bevelled rim: light edge top-left, dark edge bottom-right
    for w, col in ((size * 0.014, (255, 255, 255, 190)), (size * 0.012, (45, 75, 125, 210))):
        ring = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        ImageDraw.Draw(ring).ellipse([c - r, c - r, c + r, c + r], outline=col, width=int(w))
        ring.putalpha(ImageChops.multiply(ring.getchannel("A"), mask))
        img.alpha_composite(ring)
    return img


def m_polygon(size: int = S) -> list[tuple[float, float]]:
    """A plain, heavy geometric M (no font): two stems and a V in the middle."""
    c = size / 2
    w, h = size * 0.50, size * 0.40  # overall width / height of the letter
    x0, y0 = c - w / 2, c - h / 2 - size * 0.035
    t = w * 0.22  # stem thickness
    pts = [(0, h), (0, 0), (t * 0.95, 0), (w / 2, h * 0.52), (w - t * 0.95, 0), (w, 0), (w, h), (w - t, h), (w - t, h * 0.34),
           (w / 2, h * 0.80), (t, h * 0.34), (t, h)]
    return [(x0 + x, y0 + y) for x, y in pts]


def monogram(size: int = S) -> Image.Image:
    """The M with an extrusion toward the bottom-right, a lit top face and a soft shadow on the wafer."""
    poly = m_polygon(size)
    depth = int(size * 0.062)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    # soft shadow on the wafer
    sh = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(sh).polygon([(x + depth * 1.1, y + depth * 1.9) for x, y in poly], fill=(10, 30, 60, 120))
    out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(size * 0.016)))
    d = ImageDraw.Draw(out)
    for i in range(depth, 0, -1):  # sides: darkest at the back, lighter toward the face
        col = BLUES[min(2, int(3 * (1 - i / depth) + 0.0))] if i < depth else BLUES[0]
        d.polygon([(x + i, y + i * 0.9) for x, y in poly], fill=col + (255,))
    # top face: vertical gradient from a lighter to the series blue, then a bright bevel on the top-left edges
    face = Image.new("RGBA", (size, size))
    fp = face.load()
    y_top, y_bot = min(y for _, y in poly), max(y for _, y in poly)
    for y in range(size):
        f = max(0.0, min(1.0, (y - y_top) / (y_bot - y_top)))
        col = tuple(int(a + (b - a) * f) for a, b in zip((98, 164, 245), SERIES_BLUE))
        for x in range(size):
            fp[x, y] = col + (255,)
    fmask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(fmask).polygon(poly, fill=255)
    face.putalpha(fmask)
    out.alpha_composite(face)
    edge = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ed = ImageDraw.Draw(edge)
    ed.line(poly + [poly[0]], fill=(214, 233, 255, 200), width=max(2, size // 190), joint="curve")
    # keep the bevel only on the top-left side: mask out edges facing the extrusion by shifting the face mask
    keep = ImageChops.subtract(fmask, ImageChops.offset(fmask, int(size * 0.008), int(size * 0.008)))
    keep = keep.filter(ImageFilter.GaussianBlur(size * 0.002))
    edge.putalpha(ImageChops.multiply(edge.getchannel("A"), ImageChops.multiply(fmask, keep.point(lambda v: min(255, v * 6)))))
    out.alpha_composite(edge)
    return out


def master(size: int = S) -> Image.Image:
    img = wafer(size)
    img.alpha_composite(monogram(size))
    return img


def main() -> None:
    big = master()
    big.resize((256, 256), Image.LANCZOS).save(HERE / "metro-toolkit.png")
    big.save(HERE / "metro-toolkit.ico", sizes=[(s, s) for s in SIZES])
    print("wrote", HERE / "metro-toolkit.ico", "and", HERE / "metro-toolkit.png")


if __name__ == "__main__":
    main()
