#!/usr/bin/env python3
"""Validate the marketplace, both plugins and every component against Cursor's formats.

  python3 scripts/validate.py

Checks, following cursor.com/docs (plugins, skills, rules, subagents, hooks):
- marketplace: name, owner, unique plugin names, each source has a manifest
- plugin.json: kebab-case name matching the folder, semver, relative paths, logo present
- skills: name = folder, description <= 420 chars with a "Use when", SKILL.md
  <= ~1,600 tokens, metadata.version, only Cursor/Agent Skills keys, licence
  matches skills.json, referenced files exist, text only, synced from one kit version
- rules (.mdc): description, alwaysApply boolean, globs; always-on rules <= ~500 tokens
- subagents: known keys, name = file name, every agent shipped here is readonly
- hooks: version 1, known events, each command's script exists, timeouts set
- whole repo: no secrets, no symlinks, executables only in plugins/*/scripts/
Exit 0 = pass. Stdlib only.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEBAB = re.compile(r"^[a-z0-9]+(?:[-.][a-z0-9]+)*$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
SECRET = re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}|\bgh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|"
                    r"\bAKIA[0-9A-Z]{16}\b|-----BEGIN [A-Z ]*PRIVATE KEY-----|\bkey_[0-9a-f]{64}\b")
SKILL_KEYS = {"name", "description", "license", "compatibility", "metadata", "paths", "globs",
              "disable-model-invocation", "icon", "color", "allowed-tools"}
RULE_KEYS = {"description", "globs", "alwaysApply"}
AGENT_KEYS = {"name", "description", "model", "readonly", "is_background"}
HOOK_EVENTS = {"sessionStart", "sessionEnd", "preToolUse", "postToolUse", "postToolUseFailure", "subagentStart",
               "subagentStop", "beforeShellExecution", "afterShellExecution", "beforeMCPExecution",
               "afterMCPExecution", "beforeReadFile", "afterFileEdit", "beforeSubmitPrompt", "preCompact", "stop",
               "afterAgentResponse", "afterAgentThought", "beforeTabFileRead", "afterTabFileEdit", "workspaceOpen"}
TEXT_EXT = {".md", ".txt", ".json", ".yaml", ".yml", ".mdc", ".svg"}
# Token budgets (characters / 4). Descriptions and always-on rules load in every
# session; SKILL.md loads whenever the skill runs. Raise only with a measured reason.
MAX_DESCRIPTION_CHARS = 420
MAX_SKILL_TOKENS = 1600
MAX_ALWAYS_RULE_TOKENS = 500
errors: list[str] = []


def err(where: Path | str, msg: str) -> None:
    errors.append(f"{where.relative_to(ROOT) if isinstance(where, Path) else where}: {msg}")


def frontmatter(path: Path) -> tuple[dict[str, str], str] | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    fm: dict[str, str] = {}
    for line in text[4:end].splitlines():
        m = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2).strip().strip('"')
    return fm, text[end + 5:]


def load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        err(path, f"invalid JSON: {exc}")
        return None


def check_relative(where: Path, value) -> None:
    for v in value if isinstance(value, list) else [value]:
        if isinstance(v, str) and (v.startswith("/") or ".." in Path(v).parts or re.match(r"^[A-Za-z]:", v)):
            err(where, f"path '{v}' must be relative and inside the plugin")


def check_skills(plugin: Path, cfg: dict) -> int:
    root = plugin / "skills"
    dirs = sorted(p for p in root.iterdir() if p.is_dir()) if root.is_dir() else []
    names = {d.name for d in dirs}
    for missing in sorted(set(cfg["skills"]) - names):
        err("skills.json", f"lists '{missing}' but {root.relative_to(ROOT)}/{missing}/ does not exist")
    for extra in sorted(names - set(cfg["skills"])):
        err(root / extra, "not listed in skills.json")
    stamps = set()
    for d in dirs:
        skill = d / "SKILL.md"
        if not skill.is_file():
            err(d, "SKILL.md missing")
            continue
        parsed = frontmatter(skill)
        if not parsed:
            err(skill, "missing or malformed YAML frontmatter")
            continue
        fm, body = parsed
        text = skill.read_text(encoding="utf-8")
        for key in sorted(set(fm) - SKILL_KEYS - {"author", "version"}):
            if not text.count(f"\n  {key}:"):          # nested metadata keys are fine
                err(skill, f"unknown frontmatter key '{key}'")
        if fm.get("name") != d.name or not KEBAB.match(fm.get("name", "")) or len(d.name) > 64:
            err(skill, f"name '{fm.get('name')}' must equal the folder name, lowercase-hyphen, <= 64 chars")
        desc = fm.get("description", "")
        if not desc:
            err(skill, "description is required (Cursor skips skills without one)")
        elif len(desc) > MAX_DESCRIPTION_CHARS:
            err(skill, f"description is {len(desc)} chars; budget {MAX_DESCRIPTION_CHARS} (loads in every session)")
        if desc and "use when" not in desc.lower() and "use whenever" not in desc.lower():
            err(skill, "description must say when to use it ('Use when ...'); Cursor selects skills by it")
        if len(text) // 4 > MAX_SKILL_TOKENS:
            err(skill, f"~{len(text) // 4} tokens; budget {MAX_SKILL_TOKENS}. Move detail into references/")
        if not re.search(r'^\s+version:\s*"?\d+\.\d+\.\d+"?\s*$', text, re.M):
            err(skill, "metadata.version (semver) is required")
        lic = cfg["skills"].get(d.name, {}).get("license")
        if lic == "MIT" and fm.get("license") != "MIT":
            err(skill, "skills.json says MIT, so frontmatter must declare 'license: MIT'")
        if lic == "proprietary" and fm.get("license"):
            err(skill, "proprietary skills must not declare an open-source licence")
        for ref in sorted(set(re.findall(r"`(references/[^`]+)`", body))):
            if not (d / ref).is_file():
                err(skill, f"missing {ref} (run scripts/sync_from_kit.py)")
        for f in d.rglob("*"):
            if f.is_file() and f.suffix.lower() not in TEXT_EXT:
                err(f, "skills are text only; no executables or binaries")
        stamp = d / "references" / "KIT_VERSION.txt"
        if stamp.exists():
            stamps.add(stamp.read_text(encoding="utf-8").strip())
        else:
            err(d, "references/KIT_VERSION.txt missing (run scripts/sync_from_kit.py)")
    if len(stamps) > 1:
        err(root, f"skills synced from different kit versions: {sorted(stamps)}")
    return len(dirs)


def check_rules(plugin: Path) -> int:
    files = sorted((plugin / "rules").glob("*.mdc")) if (plugin / "rules").is_dir() else []
    for f in files:
        parsed = frontmatter(f)
        if not parsed:
            err(f, "missing YAML frontmatter")
            continue
        fm, body = parsed
        for key in sorted(set(fm) - RULE_KEYS):
            err(f, f"unknown rule key '{key}' (Cursor reads description, globs, alwaysApply)")
        if not fm.get("description"):
            err(f, "description is required")
        if fm.get("alwaysApply") not in ("true", "false"):
            err(f, "alwaysApply must be true or false")
        if fm.get("alwaysApply") == "true":
            if fm.get("globs"):
                err(f, "an always-on rule should not also set globs")
            if len(body) // 4 > MAX_ALWAYS_RULE_TOKENS:
                err(f, f"always-on rule is ~{len(body) // 4} tokens; budget {MAX_ALWAYS_RULE_TOKENS} (sent with every request)")
        elif not fm.get("globs") and not fm.get("description"):
            err(f, "a rule that is not always-on needs globs or a description")
        if fm.get("globs"):
            try:
                globs = json.loads(fm["globs"]) if fm["globs"].startswith("[") else [fm["globs"]]
                assert all(isinstance(g, str) and g for g in globs)
            except (ValueError, AssertionError):
                err(f, "globs must be a string or a JSON-style list of strings")
    return len(files)


def check_agents(plugin: Path) -> int:
    files = sorted((plugin / "agents").glob("*.md")) if (plugin / "agents").is_dir() else []
    for f in files:
        parsed = frontmatter(f)
        if not parsed:
            err(f, "missing YAML frontmatter")
            continue
        fm, body = parsed
        for key in sorted(set(fm) - AGENT_KEYS):
            err(f, f"unknown subagent key '{key}'")
        if fm.get("name", f.stem) != f.stem or not re.match(r"^[a-z-]+$", f.stem):
            err(f, "name must equal the file name (lowercase letters and hyphens)")
        if len(fm.get("description", "")) < 40:
            err(f, "description must say when to delegate (Agent reads it to decide)")
        if fm.get("readonly") != "true":
            err(f, "every subagent shipped here reviews or designs, so it must be readonly: true")
        if "never modify files" not in body.lower() and "do not modify files" not in body.lower():
            err(f, "prompt must also say it never modifies files (defence in depth for plugin-shipped agents)")
    return len(files)


def check_hooks(plugin: Path) -> int:
    path = plugin / "hooks" / "hooks.json"
    if not path.exists():
        return 0
    cfg = load_json(path)
    if cfg is None:
        return 0
    if cfg.get("version") != 1:
        err(path, "version must be 1")
    n = 0
    for event, defs in (cfg.get("hooks") or {}).items():
        if event not in HOOK_EVENTS:
            err(path, f"unknown hook event '{event}'")
        for d in defs:
            n += 1
            cmd = d.get("command", "")
            script = next((t for t in cmd.split() if t.startswith("./")), None)
            if not script or not (plugin / script).is_file():
                err(path, f"{event}: command must run a script inside the plugin (./scripts/...): '{cmd}'")
            if not isinstance(d.get("timeout"), (int, float)) or d["timeout"] <= 0:
                err(path, f"{event}: set a positive timeout so a hung hook cannot stall the agent")
    return n


def check_plugin(plugin: Path, entry: dict, cfg: dict) -> dict:
    manifest = plugin / ".cursor-plugin" / "plugin.json"
    if not manifest.is_file():
        err(plugin, "missing .cursor-plugin/plugin.json")
        return {}
    m = load_json(manifest) or {}
    if m.get("name") != entry.get("name") or m.get("name") != plugin.name or not KEBAB.match(m.get("name", "")):
        err(manifest, "name must be kebab-case and equal both the folder and the marketplace entry")
    if not SEMVER.match(str(m.get("version", ""))):
        err(manifest, "version must be semver")
    if not (m.get("author") or {}).get("name"):
        err(manifest, "author.name is required")
    if len(m.get("description", "")) < 40:
        err(manifest, "description must explain the plugin")
    for key in ("rules", "agents", "skills", "commands", "hooks", "mcpServers", "logo"):
        if key in m:
            check_relative(manifest, m[key])
    if m.get("logo") and not (plugin / m["logo"]).is_file():
        err(manifest, f"logo {m['logo']} not found")
    if not (plugin / "README.md").is_file():
        err(plugin, "README.md is required for marketplace review")
    counts = {"skills": check_skills(plugin, cfg) if (plugin / "skills").is_dir() else 0,
              "rules": check_rules(plugin), "agents": check_agents(plugin), "hooks": check_hooks(plugin)}
    if not any(counts.values()):
        err(plugin, "plugin has no components")
    return counts


def check_repo() -> None:
    for f in ROOT.rglob("*"):
        if ".git" in f.parts or "__pycache__" in f.parts or ".pytest_cache" in f.parts:
            continue
        rel = f.relative_to(ROOT)
        if f.is_symlink():
            err(f, "symlinks are not allowed")
        elif f.is_file():
            if f.stat().st_mode & 0o111 and not (rel.parts[0] == "plugins" and "scripts" in rel.parts):
                err(f, "executable bit set outside plugins/*/scripts/")
            if f.suffix.lower() in TEXT_EXT | {".py", ".yml", ".sh", ".ps1", ".tf", ""}:
                text = f.read_text(encoding="utf-8", errors="replace")
                if SECRET.search(text) and rel.as_posix() not in ("scripts/validate.py",):
                    err(f, "looks like a secret")
                if "__CLAUDE_HOME__" in text and rel.as_posix() != "scripts/validate.py":
                    err(f, "kit placeholder left in file")


def main() -> int:
    cfg = json.loads((ROOT / "skills.json").read_text(encoding="utf-8"))
    mp_path = ROOT / ".cursor-plugin" / "marketplace.json"
    mp = load_json(mp_path) or {}
    if not KEBAB.match(mp.get("name", "")):
        err(mp_path, "name must be kebab-case")
    if not (mp.get("owner") or {}).get("name"):
        err(mp_path, "owner.name is required")
    entries = mp.get("plugins") or []
    names = [e.get("name") for e in entries]
    if not entries or len(names) != len(set(names)):
        err(mp_path, "plugins must be a non-empty list with unique names")
    base = ROOT / (mp.get("metadata") or {}).get("pluginRoot", ".")
    totals: dict[str, int] = {}
    for e in entries:
        src = e.get("source")
        src = src.get("path") if isinstance(src, dict) else src
        check_relative(mp_path, src)
        plugin = base / str(src)
        if not plugin.is_dir():
            err(mp_path, f"plugin source '{src}' not found")
            continue
        for k, v in check_plugin(plugin, e, cfg).items():
            totals[k] = totals.get(k, 0) + v
    check_repo()
    for e in errors:
        print(f"FAIL  {e}")
    summary = ", ".join(f"{v} {k}" for k, v in totals.items())
    print(f"\n{'PASS' if not errors else 'FAIL'}: {len(entries)} plugin(s) ({summary}), {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
