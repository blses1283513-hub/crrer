"""The app icon (3D M monogram on a wafer) and the Desktop shortcut script that uses it."""

from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ICO = ROOT / "assets" / "metro-toolkit.ico"
SIZES = {(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)}


def test_ico_has_every_windows_size_and_is_not_blank():
    ico = Image.open(ICO)
    assert ico.format == "ICO" and set(ico.info["sizes"]) >= SIZES
    for size in sorted(SIZES):
        ico.size = size
        im = np.asarray(ico.copy().convert("RGBA")).astype(int)
        px = im.reshape(-1, 4)
        opaque = px[px[:, 3] > 200]
        blue = opaque[(opaque[:, 2] > opaque[:, 0] + 60) & (opaque[:, 2] > 150)]  # the M's blue (the wafer is grey-blue)
        assert len(opaque) > 0.55 * len(px), size  # the wafer disc fills most of the square
        assert im[0, 0, 3] == 0, size  # transparent corners: it is a round wafer
        assert len(blue) > 0.04 * len(px), size  # the monogram is still visible, even at 16 px


def test_icon_can_be_rebuilt_from_the_generator(tmp_path, monkeypatch):
    import importlib.util

    spec = importlib.util.spec_from_file_location("make_icon", ROOT / "assets" / "make_icon.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "HERE", tmp_path)
    mod.main()
    assert set(Image.open(tmp_path / "metro-toolkit.ico").info["sizes"]) >= SIZES
    assert Image.open(tmp_path / "metro-toolkit.png").size == (256, 256)


def test_shortcut_script_is_wired_to_the_icon_and_launcher():
    raw = (ROOT / "Create Desktop Shortcut.bat").read_bytes()
    text = raw.decode("ascii")  # plain ASCII: cmd.exe code pages do not matter
    assert b"\r\n" in raw and "\n" not in text.replace("\r\n", "")
    assert "Metro Toolkit.bat" in text and r"assets\metro-toolkit.ico" in text and "IconLocation" in text
    assert "Desktop" in text and "startmenu" in text.lower() and "%~dp0" in text
    assert "C:\\Users" not in text  # no personal paths
    ps = [ln for ln in text.splitlines() if ln.strip().startswith('"$')]
    assert ps and all(ln.count('"') == 2 or ln.rstrip(" ^").endswith('"') for ln in ps)  # one quoted piece per line
    assert all(ln.rstrip().endswith("^") for ln in ps[:-1])  # continued lines are chained
    assert (ROOT / "Metro Toolkit.bat").exists() and ICO.exists()
