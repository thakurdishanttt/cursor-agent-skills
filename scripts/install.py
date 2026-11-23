#!/usr/bin/env python3
"""One-time setup: install the security skills, rules, subagents and guardrails for every project.

  python3 scripts/install.py                       # once, for your user: every project, updates itself
  python3 scripts/install.py --no-guardrails       # skills, subagents and the security rule only
  python3 scripts/install.py --fail-closed         # block the action if a guardrail hook fails
  python3 scripts/install.py --no-auto-update      # stay on this version until you re-run
  python3 scripts/install.py --list                # what is installed, and whether an update is out
  python3 scripts/install.py --uninstall
  python3 scripts/install.py --scope project --project-dir ../api   # pin one repo's versions; commit .cursor/
  sudo python3 scripts/install.py --scope enterprise                # every user on this machine (MDM)

What the default (user scope) does, using Cursor's documented locations:
  skills     ~/.cursor/skills/<name>/      used in every project
  subagents  ~/.cursor/agents/             used in every project
  hooks      ~/.cursor/hooks.json          guardrails in every project, plus a sessionStart hook that
                                           adds the always-on security rule to every Agent chat
                                           (Cursor has no file-based user rules) and checks once a day
                                           for a newer release
Project scope writes the same into <repo>/.cursor/ (rules as .cursor/rules/*.mdc); enterprise scope
writes the hooks into Cursor's system folder, which users cannot turn off:
  /etc/cursor (Linux/WSL), /Library/Application Support/Cursor (macOS), C:\\ProgramData\\Cursor (Windows)

Updates: only to release tags (vX.Y.Z) on origin/main of this clone, newest first, never a
downgrade, and never over local edits. Turn off with --no-auto-update or
CURSOR_AGENT_SKILLS_AUTO_UPDATE=0. Only files this installer owns are replaced or removed;
your own skills, rules, agents and hook entries are left alone. Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODING = ROOT / "plugins" / "secure-coding"
GUARD = ROOT / "plugins" / "secure-guardrails"
MANIFEST = "cursor-agent-skills.json"
OWNED_MARKS = ("secure-guardrails/guard.py", "cursor-agent-skills/session_start.py")
SEMVER_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


def version(plugin: Path) -> str:
    return json.loads((plugin / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]


def release() -> str:
    return json.loads((ROOT / ".cursor-plugin" / "marketplace.json").read_text(encoding="utf-8"))["metadata"]["version"]


def vtuple(v: str) -> tuple[int, int, int]:
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)$", v or "")
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else (0, 0, 0)


def enterprise_dir() -> Path:
    if sys.platform == "darwin":
        return Path("/Library/Application Support/Cursor")
    if sys.platform == "win32":
        return Path(os.environ.get("ProgramData", "C:\\ProgramData")) / "Cursor"
    return Path("/etc/cursor")


def default_python() -> str:
    return "py -3" if sys.platform == "win32" else "python3"


def replace_dir(src: Path, dst: Path) -> None:
    """Write the new folder fully, then swap it in, so a failed copy never leaves half a skill."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f".{dst.name}-", dir=dst.parent))
    shutil.rmtree(tmp)
    shutil.copytree(src, tmp, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if dst.exists():
        shutil.rmtree(dst)
    tmp.rename(dst)


def rule_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return text.split("\n---\n", 1)[1].strip() + "\n" if text.startswith("---\n") else text


def guard_entries(scope: str, python: str, fail_closed: bool) -> dict:
    cfg = json.loads((GUARD / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    # Project hooks run from the project root; user and enterprise hooks from their config folder.
    script = ".cursor/hooks/secure-guardrails/guard.py" if scope == "project" else "./hooks/secure-guardrails/guard.py"
    out: dict = {}
    for event, defs in cfg["hooks"].items():
        for d in defs:
            entry = {"command": f"{python} {script} {d['command'].split()[-1]}", "timeout": d.get("timeout", 10)}
            if fail_closed:
                entry["failClosed"] = True
            out.setdefault(event, []).append(entry)
    return out


def merge_hooks(path: Path, ours: dict | None) -> None:
    """Remove our previous entries from hooks.json, then add the new ones (if any). Keeps everything else."""
    cfg: dict = {"version": 1, "hooks": {}}
    if path.exists():
        try:
            cfg = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            sys.exit(f"{path} is not valid JSON; fix it first (nothing was changed)")
    hooks = cfg.setdefault("hooks", {})
    for event in list(hooks):
        hooks[event] = [d for d in hooks[event] if not any(m in str(d.get("command", "")) for m in OWNED_MARKS)]
        if not hooks[event]:
            del hooks[event]
    for event, defs in (ours or {}).items():
        hooks.setdefault(event, []).extend(defs)
    cfg["version"] = cfg.get("version", 1)
    if hooks:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    elif path.exists():
        path.unlink()


def targets(scope: str, project: Path, enterprise: str | None) -> Path:
    if scope == "enterprise":
        return Path(enterprise) if enterprise else enterprise_dir()
    return (project / ".cursor") if scope == "project" else (Path.home() / ".cursor")


def read_manifest(base: Path) -> dict:
    try:
        return json.loads((base / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def remove(base: Path, rel: str) -> bool:
    p = base / rel
    if p.is_dir():
        shutil.rmtree(p)
    elif p.exists():
        p.unlink()
    else:
        return False
    return True


def uninstall(base: Path) -> list[str]:
    removed = [rel for rel in read_manifest(base).get("files", []) if remove(base, rel)]
    merge_hooks(base / "hooks.json", None)
    (base / MANIFEST).unlink(missing_ok=True)
    return removed


def install(base: Path, scope: str, guardrails: bool, python: str, fail_closed: bool, auto_update: bool) -> list[str]:
    old = read_manifest(base)
    files: list[str] = []
    hooks: dict = {}
    if scope != "enterprise":                      # Cursor has no system-wide skills or subagents
        for skill in sorted(p for p in (CODING / "skills").iterdir() if (p / "SKILL.md").is_file()):
            replace_dir(skill, base / "skills" / skill.name)
            files.append(f"skills/{skill.name}")
        (base / "agents").mkdir(parents=True, exist_ok=True)
        for agent in sorted((CODING / "agents").glob("*.md")):
            shutil.copyfile(agent, base / "agents" / agent.name)
            files.append(f"agents/{agent.name}")
    if scope == "project":
        (base / "rules").mkdir(parents=True, exist_ok=True)
        for rule in sorted((CODING / "rules").glob("*.mdc")):
            shutil.copyfile(rule, base / "rules" / rule.name)
            files.append(f"rules/{rule.name}")
    else:
        # No file-based user or system rules in Cursor: a sessionStart hook adds the
        # always-on baseline to every conversation instead.
        own = base / "hooks" / "cursor-agent-skills"
        own.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "scripts" / "session_start.py", own / "session_start.py")
        (own / "baseline.md").write_text(rule_body(CODING / "rules" / "security-baseline.mdc"), encoding="utf-8")
        upd = own / "update.json"
        if auto_update and scope == "user" and (ROOT / ".git").exists():
            upd.write_text(json.dumps({"source_dir": str(ROOT), "scope": scope}, indent=2) + "\n", encoding="utf-8")
        else:
            upd.unlink(missing_ok=True)
        files.append("hooks/cursor-agent-skills")
        hooks["sessionStart"] = [{"command": f"{python} ./hooks/cursor-agent-skills/session_start.py", "timeout": 10}]
    if guardrails:
        dst = base / "hooks" / "secure-guardrails"
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(GUARD / "scripts" / "guard.py", dst / "guard.py")
        files.append("hooks/secure-guardrails")
        hooks.update(guard_entries(scope, python, fail_closed))
    merge_hooks(base / "hooks.json", hooks)
    for rel in set(old.get("files", [])) - set(files):       # removed in this version, or guardrails turned off
        remove(base, rel)
    (base / MANIFEST).write_text(json.dumps({
        "source": "https://github.com/thakurdishanttt/cursor-agent-skills",
        "release": release(),
        "secure-coding": version(CODING) if scope != "enterprise" else None,
        "secure-guardrails": version(GUARD) if guardrails else None,
        "scope": scope, "auto_update": bool(auto_update and scope == "user"),
        "options": {"guardrails": guardrails, "python": python, "fail_closed": fail_closed},
        "files": files}, indent=2) + "\n", encoding="utf-8")
    return files


def git(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, timeout=timeout)


def self_update(base: Path) -> int:
    """Move this clone to the newest release tag on origin/main and reinstall with the saved options."""
    m = read_manifest(base)
    if not m or not m.get("auto_update"):
        print("auto-update is off or nothing is installed; nothing to do")
        return 0
    if not (ROOT / ".git").exists():
        print(f"{ROOT} is not a git clone; re-clone to get updates")
        return 0
    if git("status", "--porcelain", "--untracked-files=no").stdout.strip():
        print(f"{ROOT} has local changes; not updating over them")
        return 0
    if git("fetch", "--quiet", "--tags", "origin", "main").returncode:
        print("fetch failed (offline?); will try again tomorrow")
        return 0
    tags = [t for t in git("tag", "--merged", "origin/main", "--list", "v*").stdout.split() if SEMVER_TAG.match(t)]
    if not tags:
        print("no release tags on origin/main yet")
        return 0
    newest = max(tags, key=vtuple)
    if vtuple(newest) <= vtuple(m.get("release", "0.0.0")):
        print(f"up to date ({m.get('release')})")
        return 0
    if git("checkout", "--quiet", "--detach", newest).returncode:
        print(f"could not check out {newest}")
        return 1
    opts = m.get("options", {})
    cmd = [sys.executable, str(ROOT / "scripts" / "install.py"), "--scope", "user", "--python", opts.get("python", default_python())]
    cmd += [] if opts.get("guardrails", True) else ["--no-guardrails"]
    cmd += ["--fail-closed"] if opts.get("fail_closed") else []
    print(f"updating {m.get('release')} -> {newest}")
    return subprocess.run(cmd, cwd=str(ROOT)).returncode      # runs the newly checked-out installer


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scope", choices=["user", "project", "enterprise"], default="user")
    ap.add_argument("--enterprise-dir", help="override the system config folder (for MDM packaging or tests)")
    ap.add_argument("--project-dir", default=".", help="project root for --scope project")
    ap.add_argument("--no-guardrails", action="store_true", help="skip the secure-guardrails hooks")
    ap.add_argument("--fail-closed", action="store_true", help="block the action if a guardrail hook crashes or times out")
    ap.add_argument("--no-auto-update", action="store_true", help="don't check for new releases (user scope)")
    ap.add_argument("--python", default=default_python(), help="command that runs Python 3 for the hooks")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--update", action="store_true", help=argparse.SUPPRESS)   # run by the sessionStart hook
    a = ap.parse_args()
    project = Path(a.project_dir).resolve()
    if a.scope == "project" and not project.is_dir():
        sys.exit(f"--project-dir {project} does not exist")
    base = targets(a.scope, project, a.enterprise_dir)

    if a.update:
        return self_update(base)
    if a.list:
        m = read_manifest(base)
        if not m:
            print(f"not installed in {base}")
            return 0
        print(f"installed in {base} ({m.get('scope')} scope), release {m.get('release')}, "
              f"auto-update {'on' if m.get('auto_update') else 'off'}")
        for plugin, src in (("secure-coding", CODING), ("secure-guardrails", GUARD)):
            have, avail = m.get(plugin), version(src)
            state = "not installed" if not have else ("up to date" if have == avail else f"update available: {avail}")
            print(f"  {plugin:<18} {have or '-':<8} {state}")
        return 0
    if a.uninstall:
        removed = uninstall(base)
        print(f"removed {len(removed)} item(s) from {base}; your own files were not touched")
        return 0
    if not shutil.which(a.python.split()[0]):
        print(f"warning: '{a.python}' was not found; the hooks need Python 3 (use --python)", file=sys.stderr)
    try:
        files = install(base, a.scope, not a.no_guardrails, a.python, a.fail_closed, not a.no_auto_update)
    except PermissionError:
        sys.exit(f"no permission to write {base}; enterprise scope needs an administrator (sudo / elevated shell)")
    what = [] if a.scope == "enterprise" else [f"secure-coding {version(CODING)}"]
    what += [] if a.no_guardrails else [f"secure-guardrails {version(GUARD)}"]
    print(f"installed {' and '.join(what)} into {base}")
    for f in files:
        print(f"  {f}")
    if a.scope == "user":
        auto = read_manifest(base).get("auto_update")
        print(f"Done. This works in every project from now on; nothing to set up per project. "
              f"{'Updates install automatically.' if auto else 'Re-run this command to update.'}")
        if auto:
            print(f"Keep this folder ({ROOT}) where it is; updates come from it.")
    elif a.scope == "enterprise":
        print("These hooks apply to every Cursor user on this machine and take priority over all other hooks. "
              "Deploy the same command through your MDM to roll out to a fleet.")
    else:
        print("next: commit the .cursor/ folder so everyone who clones the repo gets the same versions.")
    print("Restart Cursor (or open a new Agent chat) to load the changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
