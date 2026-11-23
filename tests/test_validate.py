"""The validator must reject broken packages, not just pass good ones."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def copy_repo(tmp: Path) -> Path:
    dst = tmp / "repo"
    shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", ".pytest_cache", "evals"))
    return dst


def validate(repo: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(repo / "scripts" / "validate.py")], capture_output=True, text=True)


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    assert old in text, f"{old!r} not in {path}"
    path.write_text(text.replace(old, new, 1))


def test_repo_passes():
    p = validate(ROOT)
    assert p.returncode == 0, p.stdout


C = "plugins/secure-coding"
G = "plugins/secure-guardrails"


@pytest.mark.parametrize("path,old,new,expect", [
    (f"{C}/agents/security-reviewer.md", "readonly: true", "readonly: false", "readonly: true"),
    (f"{C}/agents/threat-modeler.md", "model: inherit", "tools: all", "unknown subagent key"),
    (f"{C}/skills/threat-model/SKILL.md", "name: threat-model", "name: threat-modeling", "must equal the folder"),
    (f"{C}/skills/threat-model/SKILL.md", 'version: "1.0.0"', 'version: "one"', "metadata.version"),
    (f"{C}/skills/secure-code-review/SKILL.md", "license: MIT", "license: Apache-2.0", "must declare 'license: MIT'"),
    (f"{C}/rules/security-baseline.mdc", "alwaysApply: true", "alwaysApply: yes", "alwaysApply must be"),
    (f"{C}/rules/security-baseline.mdc", "alwaysApply: true", "alwaysApply: true\nalways: true", "unknown rule key"),
    (f"{G}/hooks/hooks.json", '"beforeReadFile"', '"beforeFileRead"', "unknown hook event"),
    (f"{G}/hooks/hooks.json", "./scripts/guard.py read", "./scripts/missing.py read", "must run a script"),
    (f"{G}/.cursor-plugin/plugin.json", '"version": "1.0.0"', '"version": "1.0"', "version must be semver"),
    (f"{G}/.cursor-plugin/plugin.json", '"logo": "assets/logo.svg"', '"logo": "../logo.svg"', "must be relative"),
    (".cursor-plugin/marketplace.json", '"source": "secure-guardrails"', '"source": "nope"', "not found"),
])
def test_rejects(tmp_path, path, old, new, expect):
    repo = copy_repo(tmp_path)
    edit(repo / path, old, new)
    p = validate(repo)
    assert p.returncode == 1 and expect in p.stdout, p.stdout


def test_rejects_long_description(tmp_path):
    repo = copy_repo(tmp_path)
    f = repo / C / "skills" / "threat-model" / "SKILL.md"
    text = f.read_text()
    start = text.index("description: ") + len("description: ")
    f.write_text(text[:start] + "Use when " + "x" * 450 + "\n" + text[text.index("\n", start) + 1:])
    assert "budget 420" in validate(repo).stdout


def test_rejects_secret_anywhere(tmp_path):
    repo = copy_repo(tmp_path)
    (repo / "docs" / "leak.md").write_text("token " + "ghp_" + "x" * 36)
    assert "looks like a secret" in validate(repo).stdout


def test_rejects_executable_in_skill(tmp_path):
    repo = copy_repo(tmp_path)
    (repo / C / "skills" / "threat-model" / "run.sh").write_text("echo hi")
    assert "text only" in validate(repo).stdout


def test_package_is_reproducible(tmp_path):
    repo = copy_repo(tmp_path)
    run = lambda: subprocess.run([sys.executable, str(repo / "scripts" / "package.py")], capture_output=True, text=True, check=True)
    run()
    first = (repo / "dist" / "SHA256SUMS").read_text()
    run()
    assert (repo / "dist" / "SHA256SUMS").read_text() == first
    names = {line.split()[1] for line in first.splitlines()}
    assert {"secure-coding-1.0.0.zip", "secure-guardrails-1.0.0.zip", "skill-threat-model-1.0.0.zip"} <= names
