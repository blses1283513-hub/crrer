"""The no-terminal launcher: finds the app, picks a free port, listens on localhost only."""

import socket
import tomllib
from pathlib import Path

from metro_toolkit import launch

ROOT = Path(__file__).resolve().parents[1]


def test_command_points_at_the_app_and_stays_on_localhost():
    cmd = launch.command(8600)
    assert launch.APP.exists() and str(launch.APP) in cmd
    assert cmd[cmd.index("--server.port") + 1] == "8600"
    assert cmd[cmd.index("--server.address") + 1] == "localhost"
    assert "0.0.0.0" not in cmd and cmd[cmd.index("--browser.gatherUsageStats") + 1] == "false"
    assert launch.command(8600, browser=False)[cmd.index("--server.headless") + 1] == "true"


def test_free_port_skips_a_busy_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        s.listen()
        busy = s.getsockname()[1]
        assert launch.free_port(busy) != busy


def test_console_script_and_windows_launcher_are_wired():
    meta = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert meta["project"]["scripts"]["metro-toolkit"] == "metro_toolkit.launch:main"
    assert callable(launch.main)
    bat = (ROOT / "Metro Toolkit.bat").read_bytes()
    assert b"\r\n" in bat and b"metro_toolkit.launch" in bat and b"%~dp0" in bat  # CRLF, runs from its own folder
    assert not any(p in bat for p in (b"C:\\Users", b"D:\\"))  # no personal paths
