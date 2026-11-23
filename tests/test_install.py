"""Installer tests: user and project scope, update, uninstall, and never touching the user's own files."""
from __future__ import annotations

import json
import os
import shutil
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
    hooks = json.loads((c / "hooks.json").read_text())["hooks"]
    assert list(hooks) == ["sessionStart"]                              # the security rule stays; guardrails gone
    assert (c / "skills" / "secure-code-review").is_dir()


def test_fail_closed_flag(tmp_path):
    run("--fail-closed", home=tmp_path)
    hooks = json.loads((tmp_path / ".cursor" / "hooks.json").read_text())["hooks"]
    guards = {e: defs for e, defs in hooks.items() if e != "sessionStart"}
    assert guards and all(d.get("failClosed") is True for defs in guards.values() for d in defs)
    assert "failClosed" not in hooks["sessionStart"][0]                 # never block a chat over the rule hook


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


# ---------------------------------------------------------------- one-time setup: every project, self-updating
NO_UPDATE = {"CURSOR_AGENT_SKILLS_AUTO_UPDATE": "0"}


def session_start(cursor_dir: Path, event: dict, extra_env: dict | None = None) -> dict:
    hooks = json.loads((cursor_dir / "hooks.json").read_text())["hooks"]
    cmd = hooks["sessionStart"][0]["command"].replace("python3", f'"{sys.executable}"', 1)
    env = {**os.environ, **NO_UPDATE, **(extra_env or {})}
    out = subprocess.run(cmd, shell=True, cwd=cursor_dir, input=json.dumps(event), capture_output=True,
                         text=True, env=env, timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_user_scope_adds_security_rule_to_every_project(tmp_path):
    run("--python", "python3", home=tmp_path)
    c = tmp_path / ".cursor"
    any_project = tmp_path / "some-other-repo"
    any_project.mkdir()
    out = session_start(c, {"workspace_roots": [str(any_project)]})
    assert "Never hardcode, log, print or commit secrets" in out["additional_context"]
    assert "alwaysApply" not in out["additional_context"]           # frontmatter stripped


def test_rule_not_sent_twice_when_project_has_it(tmp_path):
    run("--python", "python3", home=tmp_path)
    proj = tmp_path / "repo"
    run("--scope", "project", "--project-dir", str(proj.mkdir() or proj), "--python", "python3", home=tmp_path)
    assert session_start(tmp_path / ".cursor", {"workspace_roots": [str(proj)]}) == {}


def test_session_start_survives_bad_input(tmp_path):
    run("--python", "python3", home=tmp_path)
    c = tmp_path / ".cursor"
    p = subprocess.run([sys.executable, str(c / "hooks" / "cursor-agent-skills" / "session_start.py")], input="not json",
                       capture_output=True, text=True, env={**os.environ, **NO_UPDATE})
    assert p.returncode == 0 and json.loads(p.stdout) == {}


def test_no_auto_update_flag(tmp_path):
    run("--no-auto-update", home=tmp_path)
    c = tmp_path / ".cursor"
    assert not (c / "hooks" / "cursor-agent-skills" / "update.json").exists()
    assert json.loads((c / "cursor-agent-skills.json").read_text())["auto_update"] is False


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                          capture_output=True, text=True, check=True).stdout.strip()


def _release(origin: Path, version: str) -> None:
    """Bump the marketplace version in the test origin, commit and tag it."""
    mp = origin / ".cursor-plugin" / "marketplace.json"
    d = json.loads(mp.read_text())
    d["metadata"]["version"] = version
    mp.write_text(json.dumps(d, indent=2) + "\n")
    _git(origin, "commit", "-qam", f"release {version}")
    _git(origin, "tag", f"v{version}")


def test_auto_update_moves_to_newest_release_only(tmp_path):
    origin = tmp_path / "origin"
    shutil.copytree(ROOT, origin, ignore=shutil.ignore_patterns(".git", "dist", "__pycache__", ".pytest_cache"))
    _git(origin, "init", "-q", "-b", "main")
    _git(origin, "add", "-A")
    _git(origin, "commit", "-qm", "base")
    _release(origin, "1.0.0")
    clone = (tmp_path / "clone").resolve()
    subprocess.run(["git", "clone", "-q", str(origin), str(clone)], check=True)
    home = tmp_path / "home"
    home.mkdir()
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}

    def installer(*args: str) -> str:
        p = subprocess.run([sys.executable, str(clone / "scripts" / "install.py"), *args], capture_output=True,
                           text=True, env=env, timeout=120)
        assert p.returncode == 0, p.stdout + p.stderr
        return p.stdout

    installer("--python", "python3")
    manifest = home / ".cursor" / "cursor-agent-skills.json"
    assert json.loads(manifest.read_text())["release"] == "1.0.0"
    assert json.loads((home / ".cursor" / "hooks" / "cursor-agent-skills" / "update.json").read_text())["source_dir"] == str(clone.resolve())

    assert "up to date" in installer("--update")
    _release(origin, "1.1.0")
    _git(origin, "tag", "v0.9.0", "HEAD~1")                     # an older tag must never win
    assert "updating 1.0.0 -> v1.1.0" in installer("--update")
    assert json.loads(manifest.read_text())["release"] == "1.1.0"
    assert _git(clone, "describe", "--tags") == "v1.1.0"
    assert "up to date" in installer("--update")

    _release(origin, "1.2.0")
    (clone / "README.md").write_text("local edit")            # local edits are never overwritten
    assert "local changes" in installer("--update")
    assert json.loads(manifest.read_text())["release"] == "1.1.0"
