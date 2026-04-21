"""
NFL Stats Analyzer — start/stop local dev services (FastAPI + Vite).

Stop/cleanup: kills processes listening on TCP 8000 and 5173 (Windows via
PowerShell Get-NetTCPConnection + taskkill). No fragile CommandLine filtering.

Usage (from repository root):
  python scripts/manage_services.py stop
  python scripts/manage_services.py cleanup   # same as stop
  python scripts/manage_services.py start
  python scripts/manage_services.py restart
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PORTS = (8000, 5173)


def _pids_listening_on_ports(ports: tuple[int, ...]) -> set[int]:
    """Return owning PIDs for LISTEN sockets on the given local ports (Windows)."""
    if sys.platform != "win32":
        raise SystemExit("manage_services.py stop/start is only wired for Windows in this repo.")

    pids: set[int] = set()
    for port in ports:
        ps = (
            f"Get-NetTCPConnection -LocalPort {port} -State Listen "
            f"-ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique"
        )
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        for line in r.stdout.splitlines():
            line = line.strip()
            if line.isdigit():
                pids.add(int(line))
    return pids


def stop_services() -> None:
    print("Stopping listeners on ports", ", ".join(map(str, PORTS)), "...")
    pids = _pids_listening_on_ports(PORTS)
    for pid in sorted(pids):
        if pid in (0, 4):
            continue
        print(f"  taskkill /PID {pid} /F")
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            cwd=REPO_ROOT,
            capture_output=True,
        )


def _start_cmd_in_new_console(args: str) -> None:
    if sys.platform != "win32":
        raise SystemExit("start/restart is only wired for Windows in this repo.")
    subprocess.Popen(
        ["cmd", "/k", args],
        cwd=REPO_ROOT,
        creationflags=subprocess.CREATE_NEW_CONSOLE,  # type: ignore[attr-defined]
    )


def start_services() -> None:
    print("Starting backend (port 8000)...")
    _start_cmd_in_new_console("set PYTHONPATH=src && python -m backend.main")
    time.sleep(3)
    print("Starting frontend (port 5173)...")
    _start_cmd_in_new_console("npm run dev --prefix frontend/nflstats-pro-ui")
    print("Launched. Open http://localhost:5173")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage NFL Stats Analyzer dev servers.")
    parser.add_argument(
        "action",
        choices=("stop", "cleanup", "start", "restart"),
        help="cleanup is an alias for stop",
    )
    args = parser.parse_args()

    if args.action in ("stop", "cleanup"):
        stop_services()
        return

    if args.action in ("start", "restart"):
        stop_services()
        start_services()
        return


if __name__ == "__main__":
    main()
