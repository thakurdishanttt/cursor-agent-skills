#!/usr/bin/env python3
"""Cursor sessionStart hook installed by scripts/install.py (user and enterprise scope).

Runs once at the start of every Agent conversation, in every project:
1. Adds the security baseline rule to the session's context, so it applies
   everywhere without per-project setup. Skipped when the project already has
   the rule in .cursor/rules/, to avoid sending it twice.
2. At most once a day, starts a background update check (user scope only),
   which moves the source clone to the newest release tag on main and
   reinstalls. Set CURSOR_AGENT_SKILLS_AUTO_UPDATE=0 to turn it off.

Always prints valid JSON and returns quickly; it never blocks a session.
Stdlib only.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DAY = 24 * 3600


def project_has_rule(event: dict) -> bool:
    return any((Path(r) / ".cursor" / "rules" / "security-baseline.mdc").is_file()
               for r in event.get("workspace_roots") or [] if isinstance(r, str))


def maybe_update() -> None:
    cfg_path = HERE / "update.json"
    if os.environ.get("CURSOR_AGENT_SKILLS_AUTO_UPDATE", "1") == "0" or not cfg_path.is_file():
        return
    stamp = HERE / ".last-update-check"
    if stamp.exists() and time.time() - stamp.stat().st_mtime < DAY:
        return
    stamp.touch()
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    installer = Path(cfg["source_dir"]) / "scripts" / "install.py"
    if not installer.is_file():
        return
    log = open(HERE / "update.log", "a", encoding="utf-8")       # noqa: SIM115 - handed to the child
    kwargs: dict = {"stdout": log, "stderr": log, "stdin": subprocess.DEVNULL, "cwd": str(installer.parent.parent)}
    if sys.platform == "win32":
        kwargs["creationflags"] = 0x00000008 | 0x00000200        # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen([sys.executable, str(installer), "--update", "--scope", cfg.get("scope", "user")], **kwargs)


def main() -> int:
    out: dict = {}
    try:
        event = json.loads(sys.stdin.read() or "{}")
        event = event if isinstance(event, dict) else {}
        baseline = HERE / "baseline.md"
        if baseline.is_file() and not project_has_rule(event):
            out["additional_context"] = baseline.read_text(encoding="utf-8")
        maybe_update()
    except Exception as exc:  # noqa: BLE001 - a session must never fail because of this hook
        print(f"cursor-agent-skills: sessionStart: {type(exc).__name__}", file=sys.stderr)
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
