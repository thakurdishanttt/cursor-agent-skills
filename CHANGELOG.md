# Changelog

All notable changes. Each skill also carries its own `metadata.version`, and each plugin its own `version`.

## Unreleased

## v1.0.0 — 2026-11-23
### Added
- **`secure-coding` plugin 1.0.0**: six skills for Cursor (`secure-code-review` and `ai-security-standard` under MIT; `threat-model`, `dependency-vetting`, `iac-security-review` and `secure-feature-build`), each shipping the security standard from claude-code-secure-agents 1.4.1. Also an always-on `security-baseline` rule (about 450 tokens), an `infrastructure-security` rule scoped to infrastructure files, and read-only `security-reviewer` and `threat-modeler` subagents.
- **`secure-guardrails` plugin 1.0.0**: hooks that block credentials in prompts (`beforeSubmitPrompt`) and MCP calls (`beforeMCPExecution`), deny reading secret files (`beforeReadFile`), deny dangerous shell commands and ask before irreversible ones (`beforeShellExecution`). Organizations can add rules in `.security/guardrails.json`.
- `.cursor-plugin/marketplace.json`, so Cursor can import the repository from GitHub or a team marketplace.
- **One-time setup** (`scripts/install.py`, default user scope): installs once and then works in every project. A `sessionStart` hook adds the always-on security rule to every Agent chat, because Cursor has no file-based user rules, and checks once a day for a newer release tag on main to update to. It never downgrades or overwrites local edits; turn it off with `--no-auto-update` or `CURSOR_AGENT_SKILLS_AUTO_UPDATE=0`. Project and enterprise (MDM) scopes, safe `hooks.json` merging, `--fail-closed`, `--list` and `--uninstall` are also included.
- `scripts/validate.py`: checks every component against Cursor's documented formats, budgets, licences, secrets and executables.
- 169 tests (`tests/`) run on Linux, macOS and Windows with Python 3.10 and 3.13.
- `scripts/run_evals.py`: 12 eval cases in real headless Cursor sessions, with the plugin loaded through `--plugin-dir`.
- Reproducible release zips with `SHA256SUMS`, a weekly sync of the standard, and the enterprise, installation, customization, CI, compliance, quality and architecture docs.
