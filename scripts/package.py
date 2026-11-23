#!/usr/bin/env python3
"""Build reproducible release zips and dist/SHA256SUMS.

  python3 scripts/package.py

Produces, for each plugin, a zip of the whole plugin folder (for local install
with `agent --plugin-dir` or a team marketplace), and one zip per skill (for
copying into `.cursor/skills/`), e.g.:
  dist/secure-coding-1.0.0.zip, dist/secure-guardrails-1.0.0.zip,
  dist/skill-threat-model-1.0.0.zip
Fixed timestamps and permissions (scripts 0755, everything else 0644) make the
zips byte-for-byte reproducible, so `sha256sum -c SHA256SUMS` verifies them.
Stdlib only.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {"__pycache__", ".pytest_cache"}


def add_tree(z: zipfile.ZipFile, folder: Path) -> None:
    for f in sorted(folder.rglob("*")):
        if f.is_file() and not f.is_symlink() and not SKIP & set(f.parts) and f.suffix != ".pyc":
            info = zipfile.ZipInfo(f.relative_to(folder.parent).as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
            info.external_attr = (0o755 if "scripts" in f.relative_to(folder).parts else 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, f.read_bytes())


def build(out: Path, folder: Path) -> None:
    with zipfile.ZipFile(out, "w") as z:
        add_tree(z, folder)
    print(f"{out.relative_to(ROOT)}  {out.stat().st_size // 1024} KB")


def main() -> int:
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    for old in dist.glob("*.zip"):
        old.unlink()
    for plugin in sorted((ROOT / "plugins").iterdir()):
        manifest = plugin / ".cursor-plugin" / "plugin.json"
        if manifest.is_file():
            build(dist / f"{plugin.name}-{json.loads(manifest.read_text())['version']}.zip", plugin)
    for skill in sorted((ROOT / "plugins" / "secure-coding" / "skills").iterdir()):
        if (skill / "SKILL.md").is_file():
            m = re.search(r'^\s+version:\s*"?([0-9][^"\s]*)"?', (skill / "SKILL.md").read_text(), re.M)
            build(dist / f"skill-{skill.name}-{m.group(1) if m else '0.0.0'}.zip", skill)
    sums = "".join(f"{hashlib.sha256(z.read_bytes()).hexdigest()}  {z.name}\n" for z in sorted(dist.glob("*.zip")))
    (dist / "SHA256SUMS").write_text(sums, encoding="utf-8")
    print("dist/SHA256SUMS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
