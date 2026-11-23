#!/usr/bin/env python3
"""Generate each skill's references/ from the kit's security standard.

The kit (claude-code-secure-agents) is the single source of truth for the
standard and keeps itself current. This script splits that standard into one
file per section and copies the sections each skill needs (skills.json) into
plugins/secure-coding/skills/<name>/references/, so every skill zip is self-contained.

  python3 scripts/sync_from_kit.py --kit-dir PATH     # use a local kit checkout
  python3 scripts/sync_from_kit.py                    # clone the kit at skills.json ref

Writes references/KIT_VERSION.txt with the kit version and commit used.
Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HEADING = re.compile(r"^## (\d+)\. (.+)$|^## (Severity scale.*)$", re.M)
# Short, stable file names (fewer tokens in every SKILL.md that cites them).
# A section the kit adds later falls back to a slug of its heading.
SHORT = {
    "0": "00-apply", "1": "01-llm01-prompt-injection", "2": "02-llm02-sensitive-data",
    "3": "03-llm03-supply-chain", "4": "04-llm04-poisoning", "5": "05-llm05-output-handling",
    "6": "06-llm06-excessive-agency", "7": "07-llm07-system-prompt", "8": "08-llm08-vectors",
    "9": "09-llm09-misinformation", "10": "10-llm10-unbounded-cost", "11": "11-appsec",
    "12": "12-engineering", "13": "13-stack-mapping", "14": "14-agentic", "15": "15-agent-rules",
}


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:48]


def split_standard(text: str) -> dict[str, tuple[str, str]]:
    """Return {section_id: (filename, markdown)}; ids are '0'..'15' and 'severity'."""
    out: dict[str, tuple[str, str]] = {}
    matches = list(HEADING.finditer(text))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.start():end].rstrip().rstrip("-").rstrip() + "\n"
        # Agent-neutral wording: the kit's paths do not exist inside a skill.
        body = body.replace("`CLAUDE.md` or `.claude/standards/*.md`", "the project's agent rules file (e.g. `AGENTS.md`, `CLAUDE.md`)")
        if m.group(1) is not None:
            sid, title = m.group(1), m.group(2)
            fname = f"{SHORT[sid]}.md" if sid in SHORT else f"{int(sid):02d}-{slug(title)}.md"
        else:
            sid, fname = "severity", "severity-scale.md"
        out[sid] = (fname, "<!-- Generated from the claude-code-secure-agents standard. Do not edit here. -->\n" + body)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kit-dir", help="local checkout of claude-code-secure-agents")
    a = ap.parse_args()
    cfg = json.loads((ROOT / "skills.json").read_text(encoding="utf-8"))
    tmp = None
    if a.kit_dir:
        kit = Path(a.kit_dir).resolve()
    else:
        tmp = tempfile.mkdtemp()
        subprocess.run(["git", "clone", "-q", "--depth", "1", "--branch", cfg["kit"]["ref"], cfg["kit"]["repo"], tmp], check=True)
        kit = Path(tmp)
    try:
        text = (kit / cfg["kit"]["standard_path"]).read_text(encoding="utf-8")
        version = (kit / "VERSION").read_text(encoding="utf-8").strip() if (kit / "VERSION").exists() else "unknown"
        commit = subprocess.run(["git", "-C", str(kit), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip() or "unknown"
        sections = split_standard(text)
        if len(sections) < 10 or "11" not in sections or "severity" not in sections:
            print("standard did not split as expected; refusing to write", file=sys.stderr)
            return 1
        changed = 0
        for name, spec in cfg["skills"].items():
            ref = ROOT / "plugins" / "secure-coding" / "skills" / name / "references"
            want = sorted(sections) if spec["sections"] == "all" else spec["sections"]
            missing = [s for s in want if s not in sections]
            if missing:
                print(f"{name}: sections not in standard: {missing}", file=sys.stderr)
                return 1
            ref.mkdir(parents=True, exist_ok=True)
            keep = {"KIT_VERSION.txt"}
            for sid in want:
                fname, body = sections[sid]
                keep.add(fname)
                p = ref / fname
                if not p.exists() or p.read_text(encoding="utf-8") != body:
                    p.write_text(body, encoding="utf-8")
                    changed += 1
            for p in ref.glob("[0-9][0-9]-*.md"):
                if p.name not in keep:
                    p.unlink()
                    changed += 1
            stamp = f"kit {version} ({commit})\n"
            (ref / "KIT_VERSION.txt").write_text(stamp, encoding="utf-8")
        print(f"synced standard from kit {version} ({commit}); {changed} file(s) changed")
        return 0
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
