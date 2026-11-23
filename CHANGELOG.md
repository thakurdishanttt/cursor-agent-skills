# Changelog

All notable changes. Each skill also carries its own `metadata.version`, and each plugin its own `version`.

## Unreleased

## v1.0.0 — 2026-11-23
### Added
- **`secure-coding` plugin 1.0.0**: six skills for Cursor (`secure-code-review` and `ai-security-standard` under MIT; `threat-model`, `dependency-vetting`, `iac-security-review` and `secure-feature-build`), each shipping the security standard from claude-code-secure-agents 1.4.1. Also an always-on `security-baseline` rule (about 450 tokens), an `infrastructure-security` rule scoped to infrastructure files, and read-only `security-reviewer` and `threat-modeler` subagents.
- **`secure-guardrails` plugin 1.0.0**: hooks that block credentials in prompts (`beforeSubmitPrompt`) and MCP calls (`beforeMCPExecution`), deny reading secret files (`beforeReadFile`), deny dangerous shell commands and ask before irreversible ones (`beforeShellExecution`). Organizations can add rules in `.security/guardrails.json`.
- `.cursor-plugin/marketplace.json`, so Cursor can import the repository from GitHub or a team marketplace.
- `scripts/install.py`: user, project and enterprise (MDM) scope; safe `hooks.json` merging; `--fail-closed`; `--list`; `--uninstall`.
- `scripts/validate.py`: checks every component against Cursor's documented formats, budgets, licences, secrets and executables.
- 164 tests (`tests/`) run on Linux, macOS and Windows with Python 3.10 and 3.13.
- `scripts/run_evals.py`: 12 eval cases in real headless Cursor sessions, with the plugin loaded through `--plugin-dir`.
- Reproducible release zips with `SHA256SUMS`, a weekly sync of the standard, and the enterprise, installation, customization, CI, compliance, quality and architecture docs.
