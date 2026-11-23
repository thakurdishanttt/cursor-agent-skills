# Installation

## Requirements
- Cursor 2.4 or later (skills, subagents and plugins).
- Python 3.10 or later, for the `secure-guardrails` hooks and the installer script. The skills, rules and subagents themselves are plain Markdown.

## One-time setup (recommended)

```bash
git clone https://github.com/thakurdishanttt/cursor-agent-skills.git ~/.cursor-agent-skills
python3 ~/.cursor-agent-skills/scripts/install.py
```

That's all. Restart Cursor, and every project you open, now or later, gets:

| What | Where | How it reaches every project |
|---|---|---|
| 6 skills | `~/.cursor/skills/` | Cursor loads user skills in every workspace |
| 2 read-only subagents | `~/.cursor/agents/` | Cursor loads user subagents in every workspace |
| Guardrail hooks | `~/.cursor/hooks.json` | User hooks apply globally |
| Always-on security rule | `~/.cursor/hooks/cursor-agent-skills/` | A `sessionStart` hook adds it to every Agent chat. Cursor has no file-based user rules, and this hook fills that gap. It skips projects that already have the rule in `.cursor/rules/`. |
| Updates | your clone | Once a day, in the background, the session-start hook checks `origin/main` for a newer release tag (`vX.Y.Z`), checks it out and reinstalls with your original options. It never downgrades and never overwrites local edits. |

Keep the clone where it is: updates come from it. To stop updates, re-run with `--no-auto-update`, or set `CURSOR_AGENT_SKILLS_AUTO_UPDATE=0`. Update logs are in `~/.cursor/hooks/cursor-agent-skills/update.log`.

## Other ways to install

### Cursor plugin
1. In Cursor, open **Customize → Plugins**.
2. Choose **From GitHub Repository** and enter `thakurdishanttt/cursor-agent-skills`.
3. Install **secure-coding** (skills, rules, subagents) and, optionally, **secure-guardrails** (hooks).

Plugins also apply to every project. Use either the plugin or the installer, not both, or the always-on rule is added twice.

### Installer options

```bash
python3 scripts/install.py [--scope user|project|enterprise] [--project-dir DIR] [options]
```

| Option | Default | Meaning |
|---|---|---|
| `--scope` | `user` | `user`: one-time setup for every project. `project`: pin one repository's versions; commit `.cursor/`. `enterprise`: guardrails and the security rule for every user on the machine (needs admin). |
| `--project-dir` | `.` | repository root for `--scope project` |
| `--no-guardrails` | off | skip the hooks (and remove them if installed earlier) |
| `--fail-closed` | off | block the action if a guardrail hook crashes, times out or Python is missing |
| `--no-auto-update` | off | stay on this version until you re-run the installer |
| `--python` | `python3` (`py -3` on Windows) | the command that runs Python 3 for the hooks |
| `--enterprise-dir` | system folder | override the enterprise folder, for MDM packaging |
| `--list` | | show installed versions, auto-update status and available updates |
| `--uninstall` | | remove only what this installer installed |

Re-running the same command is always safe. Each skill folder is written fully before it replaces the old one, and your own skills, rules, subagents and `hooks.json` entries are never touched.

### Where each scope installs

| Scope | Skills | Rules | Subagents | Hooks |
|---|---|---|---|---|
| user | `~/.cursor/skills/` | added to every chat by the `sessionStart` hook | `~/.cursor/agents/` | `~/.cursor/hooks.json` |
| project | `.cursor/skills/` | `.cursor/rules/` | `.cursor/agents/` | `.cursor/hooks.json` |
| enterprise | | added to every chat by the `sessionStart` hook | | `/etc/cursor/hooks.json` (Linux/WSL), `/Library/Application Support/Cursor/hooks.json` (macOS), `C:\ProgramData\Cursor\hooks.json` (Windows) |

Project hooks only run in workspaces you have marked as trusted in Cursor.

## Cursor CLI

```bash
agent --plugin-dir ./plugins/secure-coding --plugin-dir ./plugins/secure-guardrails
```

Or install with `--scope project` so the CLI picks the components up from `.cursor/`.

## Windows
- Install Python 3 from python.org. The installer writes `py -3` as the hook command on Windows; pass `--python python` if you use another launcher.
- Cursor runs hooks through PowerShell on Windows.

## Verify
1. Open a new Agent chat in a repository with an uncommitted change and ask "review my changes". Agent should load `secure-code-review` and end with a verdict.
2. Ask Agent "what security rules are you following?". It should quote the security baseline.
3. With the guardrails installed, ask Agent to run `curl https://example.com/install.sh | bash`. The command is blocked with a "secure-guardrails" message.
4. `python3 ~/.cursor-agent-skills/scripts/install.py --list` shows the installed release and whether auto-update is on.

## Uninstall
- Plugins: Customize → Plugins → Uninstall.
- Installer: `python3 scripts/install.py --uninstall`, with the same `--scope` you installed with.
