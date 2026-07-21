#!/usr/bin/env python3
"""
MHFA Live agent — sends metrics to https://live.mhfa.ir and runs remote commands.

Environment:
  MHFA_PANEL_URL, MHFA_SITE_SLUG, MHFA_AGENT_TOKEN (required)
  MHFA_HEARTBEAT_SECONDS=30, MHFA_POLL_COMMAND_SECONDS=5, MHFA_PANEL_PING_SECONDS=300
  MHFA_SYSTEMD_UNIT — optional default unit for restart_systemd
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from typing import Any, Optional

import psutil
import requests

PANEL_URL = os.environ.get("MHFA_PANEL_URL", "https://live.mhfa.ir").rstrip("/")
SITE_SLUG = os.environ.get("MHFA_SITE_SLUG", "").strip()
AGENT_TOKEN = os.environ.get("MHFA_AGENT_TOKEN", "").strip()
HEARTBEAT_SEC = int(os.environ.get("MHFA_HEARTBEAT_SECONDS", "30"))
POLL_SEC = int(os.environ.get("MHFA_POLL_COMMAND_SECONDS", "5"))
PING_SEC = int(os.environ.get("MHFA_PANEL_PING_SECONDS", "300"))
DEFAULT_SYSTEMD_UNIT = os.environ.get("MHFA_SYSTEMD_UNIT", "").strip()
TIMEOUT = 15


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {AGENT_TOKEN}",
        "Content-Type": "application/json",
    }


def _url(path: str) -> str:
    return f"{PANEL_URL}/api/v1/agent/site/{SITE_SLUG}{path}"


def collect_metrics() -> dict[str, Any]:
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    load1, _, _ = os.getloadavg() if hasattr(os, "getloadavg") else (0.0, 0.0, 0.0)
    return {
        "ram_used_mb": round((mem.total - mem.available) / (1024 * 1024), 1),
        "ram_total_mb": round(mem.total / (1024 * 1024), 1),
        "cpu_percent": round(psutil.cpu_percent(interval=0.5), 1),
        "disk_used_percent": round(disk.percent, 1),
        "load_1": round(load1, 2),
    }


def post_heartbeat(extra: Optional[dict[str, Any]] = None) -> Optional[dict[str, Any]]:
    body = collect_metrics()
    if extra:
        body.update(extra)
    r = requests.post(_url("/heartbeat/"), headers=_headers(), json=body, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    return data.get("command")


def get_pending_command() -> Optional[dict[str, Any]]:
    r = requests.get(_url("/commands/pending/"), headers=_headers(), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json().get("command")


def mark_command_done(cmd_id: int, ok: bool, message: str = "") -> None:
    requests.post(
        _url(f"/commands/{cmd_id}/done/"),
        headers=_headers(),
        json={"ok": ok, "message": message or ("ok" if ok else "failed")},
        timeout=TIMEOUT,
    ).raise_for_status()


def run_restart_systemd(unit: str) -> tuple[bool, str]:
    unit = (unit or DEFAULT_SYSTEMD_UNIT).strip()
    if not unit:
        return False, "no systemd unit"
    try:
        subprocess.run(
            ["systemctl", "restart", unit],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return True, f"restarted {unit}"
    except subprocess.CalledProcessError as exc:
        return False, (exc.stderr or exc.stdout or str(exc))[:500]
    except Exception as exc:
        return False, str(exc)[:500]


def execute_command(cmd: dict[str, Any]) -> tuple[bool, str]:
    cmd_type = cmd.get("type", "")
    if cmd_type == "restart_systemd":
        return run_restart_systemd(cmd.get("systemd_unit") or "")
    return False, f"unknown command type: {cmd_type}"


def panel_status_ping() -> None:
    requests.get(_url("/panel-status/"), headers=_headers(), timeout=TIMEOUT).raise_for_status()


def main() -> int:
    if not SITE_SLUG or not AGENT_TOKEN:
        print("MHFA_SITE_SLUG and MHFA_AGENT_TOKEN are required", file=sys.stderr)
        return 1

    last_heartbeat = 0.0
    last_poll = 0.0
    last_ping = 0.0
    startup_sent = False

    print(f"MHFA agent started slug={SITE_SLUG} panel={PANEL_URL}", flush=True)

    while True:
        now = time.time()
        try:
            if not startup_sent:
                post_heartbeat({"event": "startup", "message": "agent started"})
                startup_sent = True
                last_heartbeat = now
            elif now - last_heartbeat >= HEARTBEAT_SEC:
                cmd = post_heartbeat()
                last_heartbeat = now
                if cmd:
                    ok, msg = execute_command(cmd)
                    if cmd.get("id"):
                        mark_command_done(int(cmd["id"]), ok, msg)

            if now - last_poll >= POLL_SEC:
                pending = get_pending_command()
                last_poll = now
                if pending and pending.get("id"):
                    ok, msg = execute_command(pending)
                    mark_command_done(int(pending["id"]), ok, msg)

            if now - last_ping >= PING_SEC:
                panel_status_ping()
                last_ping = now
        except Exception as exc:
            print(f"agent error: {exc}", flush=True)

        time.sleep(1)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
