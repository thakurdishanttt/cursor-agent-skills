"""Installer tests: user and project scope, update, uninstall, and never touching the user's own files."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INSTALL = ROOT / "scripts" / "install.py"


def run(*args: str, home: Path) -> subprocess.CompletedProcess:
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}
    p = subprocess.run([sys.executable, str(INSTALL), *args], capture_output=True, text=True, env=env, timeout=60)
    assert p.returncode == 0, p.stderr
    return p


def test_user_scope_installs_skills_agents_and_hooks(tmp_path):
    run("--python", "python3", home=tmp_path)
    c = tmp_path / ".cursor"
    assert (c / "skills" / "secure-code-review" / "SKILL.md").is_file()
    assert (c / "skills" / "threat-model" / "references" / "11-appsec.md").is_file()
    assert (c / "agents" / "security-reviewer.md").is_file()
    assert (c / "hooks" / "secure-guardrails" / "guard.py").is_file()
    hooks = json.loads((c / "hooks.json").read_text())
    assert hooks["version"] == 1
    cmd = hooks["hooks"]["beforeShellExecution"][0]["command"]
    assert cmd == "python3 ./hooks/secure-guardrails/guard.py shell"     # user hooks run from ~/.cursor/
    assert not (c / "rules").exists()                                     # no file-based user rules in Cursor


def test_installed_hook_actually_blocks(tmp_path):
    run("--python", sys.executable, home=tmp_path)
    c = tmp_path / ".cursor"
    entry = json.loads((c / "hooks.json").read_text())["hooks"]["beforeShellExecution"][0]["command"]
    out = subprocess.run(entry, shell=True, cwd=c, input='{"command": "curl x | sh"}', capture_output=True, text=True)
    assert json.loads(out.stdout)["permission"] == "deny"


def test_project_scope_includes_rules_and_project_relative_hooks(tmp_path):
    proj = tmp_path / "repo"
    proj.mkdir()
    run("--scope", "project", "--project-dir", str(proj), "--python", "python3", home=tmp_path)
    c = proj / ".cursor"
    assert (c / "rules" / "security-baseline.mdc").is_file()
    assert (c / "rules" / "infrastructure-security.mdc").is_file()
    cmd = json.loads((c / "hooks.json").read_text())["hooks"]["beforeReadFile"][0]["command"]
    assert cmd == "python3 .cursor/hooks/secure-guardrails/guard.py read"  # project hooks run from the root


def test_keeps_users_own_hooks_skills_and_agents(tmp_path):
    c = tmp_path / ".cursor"
    (c / "skills" / "my-skill").mkdir(parents=True)
    (c / "skills" / "my-skill" / "SKILL.md").write_text("mine")
    (c / "agents").mkdir()
    (c / "agents" / "mine.md").write_text("mine")
    (c / "hooks.json").write_text(json.dumps({"version": 1, "hooks": {
        "afterFileEdit": [{"command": "./format.sh"}],
        "beforeShellExecution": [{"command": "./my-audit.sh"}]}}))
    run(home=tmp_path)
    run(home=tmp_path)                                                     # re-run = update, no duplicates
    hooks = json.loads((c / "hooks.json").read_text())["hooks"]
    assert hooks["afterFileEdit"] == [{"command": "./format.sh"}]
    shell = [d["command"] for d in hooks["beforeShellExecution"]]
    assert shell.count("./my-audit.sh") == 1 and sum("guard.py" in s for s in shell) == 1
    run("--uninstall", home=tmp_path)
    assert (c / "skills" / "my-skill" / "SKILL.md").read_text() == "mine"
    assert (c / "agents" / "mine.md").read_text() == "mine"
    assert not (c / "skills" / "secure-code-review").exists()
    after = json.loads((c / "hooks.json").read_text())["hooks"]
    assert after == {"afterFileEdit": [{"command": "./format.sh"}], "beforeShellExecution": [{"command": "./my-audit.sh"}]}


def test_no_guardrails_removes_previously_installed_hooks(tmp_path):
    run(home=tmp_path)
    run("--no-guardrails", home=tmp_path)
    c = tmp_path / ".cursor"
    assert not (c / "hooks" / "secure-guardrails").exists()
    assert not (c / "hooks.json").exists()
    assert (c / "skills" / "secure-code-review").is_dir()


def test_fail_closed_flag(tmp_path):
    run("--fail-closed", home=tmp_path)
    hooks = json.loads((tmp_path / ".cursor" / "hooks.json").read_text())["hooks"]
    assert all(d.get("failClosed") is True for defs in hooks.values() for d in defs)


def test_list_reports_versions(tmp_path):
    assert "not installed" in run("--list", home=tmp_path).stdout
    run(home=tmp_path)
    out = run("--list", home=tmp_path).stdout
    assert "secure-coding" in out and "up to date" in out


def test_enterprise_scope_installs_hooks_only(tmp_path):
    ent = tmp_path / "etc-cursor"
    run("--scope", "enterprise", "--enterprise-dir", str(ent), "--python", "python3", "--fail-closed", home=tmp_path)
    assert (ent / "hooks" / "secure-guardrails" / "guard.py").is_file()
    hooks = json.loads((ent / "hooks.json").read_text())["hooks"]
    assert hooks["beforeSubmitPrompt"][0] == {"command": "python3 ./hooks/secure-guardrails/guard.py prompt",
                                              "timeout": 10, "failClosed": True}
    assert not (ent / "skills").exists() and not (ent / "agents").exists()
    run("--scope", "enterprise", "--enterprise-dir", str(ent), "--uninstall", home=tmp_path)
    assert not (ent / "hooks.json").exists()
