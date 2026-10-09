"""Start the dashboard from anywhere: ``metro-toolkit`` (or ``python -m metro_toolkit.launch``).

Finds app.py next to this package, picks a free port and runs Streamlit, which opens the browser.
Options: ``--port 8600`` to choose the port, ``--no-browser`` to only print the address.
"""

from __future__ import annotations

import argparse
import socket
import subprocess
import sys
from pathlib import Path

APP = Path(__file__).resolve().parent / "dashboard" / "app.py"


def free_port(start: int = 8501, tries: int = 50) -> int:
    """First port from ``start`` that nothing is listening on."""
    for port in range(start, start + tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError(f"no free port between {start} and {start + tries - 1}")


def command(port: int, browser: bool = True) -> list[str]:
    # localhost only: imported fab data must not be reachable from the office network
    return [sys.executable, "-m", "streamlit", "run", str(APP), "--server.port", str(port),
            "--server.address", "localhost", "--server.headless", "false" if browser else "true",
            "--browser.gatherUsageStats", "false"]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="metro-toolkit", description="Open the metro-toolkit dashboard.")
    ap.add_argument("--port", type=int, help="port to use (default: first free port from 8501)")
    ap.add_argument("--no-browser", action="store_true", help="do not open a browser window")
    args = ap.parse_args(argv)
    try:
        import streamlit  # noqa: F401
    except ImportError:
        print("Streamlit is not installed in this Python environment.\n"
              'Install the dashboard extras:  pip install -e ".[dashboard]"', file=sys.stderr)
        return 1
    if not APP.exists():
        print(f"Dashboard not found: {APP}", file=sys.stderr)
        return 1
    port = args.port or free_port()
    print(f"metro-toolkit dashboard -> http://localhost:{port}   (close this window or press Ctrl+C to stop)")
    try:
        return subprocess.call(command(port, not args.no_browser))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
