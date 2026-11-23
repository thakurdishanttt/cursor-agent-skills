# Installation

## Requirements
- Cursor 2.4 or later (skills, subagents and plugins).
- Python 3.10 or later, for the `secure-guardrails` hooks and the installer script. The skills, rules and subagents themselves are plain Markdown.

## Option 1: install the plugins in Cursor
1. In Cursor, open **Customize → Plugins**.
2. Choose **From GitHub Repository** and enter `thakurdishanttt/cursor-agent-skills`.
3. Install **secure-coding** (skills, rules, subagents) and, optionally, **secure-guardrails** (hooks).

Cursor reads `.cursor-plugin/marketplace.json` at the root of this repository, which lists both plugins. To pin a version, import a release tag or your own fork.

## Option 2: the installer script

```bash
git clone https://github.com/thakurdishanttt/cursor-agent-skills.git
cd cursor-agent-skills
python3 scripts/install.py [--scope user|project|enterprise] [--project-dir DIR] [options]
```

| Option | Default | Meaning |
|---|---|---|
| `--scope` | `user` | `user`: all your projects. `project`: one repository; commit `.cursor/`. `enterprise`: guardrail hooks for every user on the machine (needs admin). |
| `--project-dir` | `.` | repository root for `--scope project` |
| `--no-guardrails` | off | skip the hooks (and remove them if installed earlier) |
| `--fail-closed` | off | block the action if a guardrail hook crashes, times out or Python is missing |
| `--python` | `python3` (`py -3` on Windows) | the command that runs Python 3 for the hooks |
| `--enterprise-dir` | system folder | override the enterprise folder, for MDM packaging |
| `--list` | | show installed versions and whether an update is available |
| `--uninstall` | | remove only what this installer installed |

Re-run the same command to update. Each skill folder is written fully before it replaces the old one. Your own skills, rules, subagents and `hooks.json` entries are never touched.

### Where each scope installs

| Scope | Skills | Rules | Subagents | Hooks |
|---|---|---|---|---|
| user | `~/.cursor/skills/` | (Cursor has no file-based user rules; use the plugin or project scope) | `~/.cursor/agents/` | `~/.cursor/hooks.json` |
| project | `.cursor/skills/` | `.cursor/rules/` | `.cursor/agents/` | `.cursor/hooks.json` |
| enterprise | | | | `/etc/cursor/hooks.json` (Linux/WSL), `/Library/Application Support/Cursor/hooks.json` (macOS), `C:\ProgramData\Cursor\hooks.json` (Windows) |

Project hooks only run in workspaces you have marked as trusted in Cursor.

## Option 3: Cursor CLI

```bash
agent --plugin-dir ./plugins/secure-coding --plugin-dir ./plugins/secure-guardrails
```

Or install with `--scope project` so the CLI picks the components up from `.cursor/`.

## Windows
- Install Python 3 from python.org. The installer writes `py -3` as the hook command on Windows; pass `--python python` if you use another launcher.
- Cursor runs hooks through PowerShell on Windows.

## Verify
1. Open a new Agent chat in a repository with an uncommitted change and ask "review my changes". Agent should load `secure-code-review` and end with a verdict.
2. With the guardrails installed, ask Agent to run `curl https://example.com/install.sh | bash`. The command is blocked with a "secure-guardrails" message.
3. `python3 scripts/install.py --list` shows the installed versions.

## Uninstall
- Plugins: Customize → Plugins → Uninstall.
- Installer: `python3 scripts/install.py --uninstall`, with the same `--scope` you installed with.
