#!/usr/bin/env python3
"""Install, update, list or remove the plugins' components without the marketplace.

  python3 scripts/install.py                                   # everything, for your user (all projects)
  python3 scripts/install.py --scope project --project-dir ../api   # into one repo; commit .cursor/
  python3 scripts/install.py --no-guardrails                   # skills, rules and subagents only
  python3 scripts/install.py --fail-closed                     # block the action if a guardrail hook fails
  sudo python3 scripts/install.py --scope enterprise           # guardrails for every user on this machine (MDM)
  python3 scripts/install.py --list
  python3 scripts/install.py --uninstall

Where things go (cursor.com/docs):
  user    skills ~/.cursor/skills/<name>/   subagents ~/.cursor/agents/   hooks ~/.cursor/hooks.json
          (Cursor has no file-based user rules: rules install with --scope project or the plugin)
  project skills .cursor/skills/<name>/     subagents .cursor/agents/     rules .cursor/rules/
          hooks .cursor/hooks.json
  enterprise  hooks only, in Cursor's system-wide config folder, which takes priority over
          team, project and user hooks and cannot be turned off by users:
          /etc/cursor (Linux/WSL), /Library/Application Support/Cursor (macOS), C:\\ProgramData\\Cursor (Windows)

Only files this installer owns are replaced or removed; your own skills, rules,
agents and hook entries are left alone. Re-run to update. Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODING = ROOT / "plugins" / "secure-coding"
GUARD = ROOT / "plugins" / "secure-guardrails"
MANIFEST = "cursor-agent-skills.json"
OWNED_MARK = "secure-guardrails/guard.py"


def version(plugin: Path) -> str:
    return json.loads((plugin / ".cursor-plugin" / "plugin.json").read_text(encoding="utf-8"))["version"]


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


def hooks_file_entries(base: Path, scope: str, python: str, fail_closed: bool) -> dict:
    cfg = json.loads((GUARD / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    # Project hooks run from the project root; user and enterprise hooks from their config folder.
    script = ".cursor/hooks/secure-guardrails/guard.py" if scope == "project" else "./hooks/secure-guardrails/guard.py"
    out = {}
    for event, defs in cfg["hooks"].items():
        out[event] = []
        for d in defs:
            check = d["command"].split()[-1]
            entry = {"command": f"{python} {script} {check}", "timeout": d.get("timeout", 10)}
            if fail_closed:
                entry["failClosed"] = True
            out[event].append(entry)
    return out


def merge_hooks(path: Path, ours: dict | None) -> None:
    """Remove our previous entries from hooks.json, then add the new ones (if any). Keeps everything else."""
    cfg = {"version": 1, "hooks": {}}
    if path.exists():
        try:
            cfg = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            sys.exit(f"{path} is not valid JSON; fix it first (nothing was changed)")
    hooks = cfg.setdefault("hooks", {})
    for event in list(hooks):
        hooks[event] = [d for d in hooks[event] if OWNED_MARK not in str(d.get("command", ""))]
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


def uninstall(base: Path) -> list[str]:
    m = read_manifest(base)
    removed = []
    for rel in m.get("files", []):
        p = base / rel
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()
        else:
            continue
        removed.append(rel)
    merge_hooks(base / "hooks.json", None)
    (base / MANIFEST).unlink(missing_ok=True)
    return removed


def install(base: Path, scope: str, guardrails: bool, python: str, fail_closed: bool) -> list[str]:
    old = read_manifest(base)
    files: list[str] = []
    skills_and_agents = scope != "enterprise"      # Cursor has no system-wide skills or subagents
    for skill in [] if not skills_and_agents else sorted(p for p in (CODING / "skills").iterdir() if (p / "SKILL.md").is_file()):
        replace_dir(skill, base / "skills" / skill.name)
        files.append(f"skills/{skill.name}")
    if skills_and_agents:
        (base / "agents").mkdir(parents=True, exist_ok=True)
    for agent in [] if not skills_and_agents else sorted((CODING / "agents").glob("*.md")):
        shutil.copyfile(agent, base / "agents" / agent.name)
        files.append(f"agents/{agent.name}")
    if scope == "project":
        (base / "rules").mkdir(parents=True, exist_ok=True)
        for rule in sorted((CODING / "rules").glob("*.mdc")):
            shutil.copyfile(rule, base / "rules" / rule.name)
            files.append(f"rules/{rule.name}")
    if guardrails:
        dst = base / "hooks" / "secure-guardrails"
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(GUARD / "scripts" / "guard.py", dst / "guard.py")
        files.append("hooks/secure-guardrails")
        merge_hooks(base / "hooks.json", hooks_file_entries(base, scope, python, fail_closed))
    else:
        merge_hooks(base / "hooks.json", None)
    for rel in set(old.get("files", [])) - set(files):       # removed in this version, or guardrails turned off
        p = base / rel
        shutil.rmtree(p) if p.is_dir() else p.unlink(missing_ok=True)
    (base / MANIFEST).write_text(json.dumps({
        "source": "https://github.com/thakurdishanttt/cursor-agent-skills",
        "secure-coding": version(CODING) if skills_and_agents else None, "secure-guardrails": version(GUARD) if guardrails else None,
        "scope": scope, "files": files}, indent=2) + "\n", encoding="utf-8")
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scope", choices=["user", "project", "enterprise"], default="user")
    ap.add_argument("--enterprise-dir", help="override the system config folder (for MDM packaging or tests)")
    ap.add_argument("--project-dir", default=".", help="project root for --scope project")
    ap.add_argument("--no-guardrails", action="store_true", help="skip the secure-guardrails hooks")
    ap.add_argument("--fail-closed", action="store_true", help="block the action if a guardrail hook crashes or times out")
    ap.add_argument("--python", default=default_python(), help="command that runs Python 3 for the hooks")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--uninstall", action="store_true")
    a = ap.parse_args()
    project = Path(a.project_dir).resolve()
    if a.scope == "project" and not project.is_dir():
        sys.exit(f"--project-dir {project} does not exist")
    base = targets(a.scope, project, a.enterprise_dir)
    if a.scope == "enterprise" and a.no_guardrails:
        sys.exit("--scope enterprise installs only the guardrail hooks; --no-guardrails leaves nothing to do")

    if a.list:
        m = read_manifest(base)
        if not m:
            print(f"not installed in {base}")
            return 0
        print(f"installed in {base} ({m.get('scope')} scope)")
        for plugin, src in (("secure-coding", CODING), ("secure-guardrails", GUARD)):
            have, avail = m.get(plugin), version(src)
            state = "not installed" if not have else ("up to date" if have == avail else f"update available: {avail}")
            print(f"  {plugin:<18} {have or '-':<8} {state}")
        return 0
    if a.uninstall:
        removed = uninstall(base)
        print(f"removed {len(removed)} item(s) from {base}; your own files were not touched")
        return 0
    if not a.no_guardrails and not shutil.which(a.python.split()[0]):
        print(f"warning: '{a.python}' was not found; the guardrail hooks need Python 3 (use --python)", file=sys.stderr)
    try:
        files = install(base, a.scope, not a.no_guardrails, a.python, a.fail_closed)
    except PermissionError:
        sys.exit(f"no permission to write {base}; enterprise scope needs an administrator (sudo / elevated shell)")
    what = [] if a.scope == "enterprise" else [f"secure-coding {version(CODING)}"]
    what += [] if a.no_guardrails else [f"secure-guardrails {version(GUARD)}"]
    print(f"installed {' and '.join(what)} into {base}")
    for f in files:
        print(f"  {f}")
    if a.scope == "enterprise":
        print("These hooks apply to every Cursor user on this machine and take priority over all other hooks. "
              "Deploy the same command through your MDM to roll out to a fleet.")
    elif a.scope == "user":
        print("note: Cursor has no file-based user rules; for the always-on security rules, install the "
              "secure-coding plugin or run with --scope project.")
    else:
        print("next: commit the .cursor/ folder so everyone who clones the repo gets the same versions.")
    print("Restart Cursor (or open a new Agent chat) to load the changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
