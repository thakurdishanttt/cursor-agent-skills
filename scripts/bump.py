#!/usr/bin/env python3
"""Bump the patch version of the named skills, the secure-coding plugin and the marketplace.

  python3 scripts/bump.py threat-model secure-code-review

Used by the weekly kit sync; also handy by hand. Stdlib only.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def patch(v: str) -> str:
    a, b, c = (int(x) for x in v.split("."))
    return f"{a}.{b}.{c + 1}"


def main(names: list[str]) -> int:
    for name in names:
        p = ROOT / "plugins" / "secure-coding" / "skills" / name / "SKILL.md"
        t = p.read_text(encoding="utf-8")
        m = re.search(r'(\n\s+version:\s*")(\d+\.\d+\.\d+)(")', t)
        if not m:
            sys.exit(f"{p}: no metadata.version")
        p.write_text(t.replace(m.group(0), f"{m.group(1)}{patch(m.group(2))}{m.group(3)}", 1), encoding="utf-8")
        print(f"{name} {m.group(2)} -> {patch(m.group(2))}")
    for p, keys in ((ROOT / "plugins" / "secure-coding" / ".cursor-plugin" / "plugin.json", ["version"]),
                    (ROOT / ".cursor-plugin" / "marketplace.json", ["metadata", "version"])):
        d = json.loads(p.read_text(encoding="utf-8"))
        node = d
        for k in keys[:-1]:
            node = node[k]
        node[keys[-1]] = patch(node[keys[-1]])
        p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"{p.relative_to(ROOT)} -> {node[keys[-1]]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
