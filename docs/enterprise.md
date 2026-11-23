# Enterprise guide

## What you get
- **`secure-coding`:** six security skills, an always-on security baseline rule, an infrastructure rule, and read-only `security-reviewer` and `threat-modeler` subagents.
- **`secure-guardrails`:** four hooks that deterministically block credentials in prompts and MCP calls, reading secret files, and dangerous shell commands. They also require approval for irreversible commands.
- **One standard** behind all of it: OWASP Top 10 for LLM Applications 2025, OWASP Top 10 for Agentic Applications 2026 and OWASP ASVS L2. It is kept current from [claude-code-secure-agents](https://github.com/thakurdishanttt/claude-code-secure-agents).
- **Your own policy** enforced alongside it: `.security/rules.md` for review rules and `.security/guardrails.json` for extra hook rules ([customization.md](customization.md)).
- **SARIF output** for GitHub code scanning ([ci-integration.md](ci-integration.md)), and a **control mapping** for auditors ([compliance.md](compliance.md)).

## Choosing a rollout

| Goal | How | Who can turn it off |
|---|---|---|
| Each developer, once: every project, self-updating | `git clone … ~/.cursor-agent-skills && python3 ~/.cursor-agent-skills/scripts/install.py` | the developer |
| Try it as a plugin | Customize → Plugins → From GitHub Repository | the developer |
| Same versions for everyone working on a repository, including CI and Cloud Agents | `install.py --scope project`, commit `.cursor/` | anyone who can change the repository (protect it with CODEOWNERS) |
| Company-curated catalogue | Add this repository to your **team marketplace**; teammates install from it | the developer |
| Guardrails nobody can disable on managed machines | `install.py --scope enterprise --fail-closed`, deployed by MDM | administrators only |

Enterprise hooks take priority over team, project and user hooks. If several hooks answer, `deny` wins over `ask`, which wins over `allow`, so no lower-level hook can weaken them.

### Deploying the guardrails through MDM
1. Package `plugins/secure-guardrails/scripts/guard.py`, or the release zip `secure-guardrails-<version>.zip`, with your MDM tool.
2. On each machine, run as administrator:
   `python3 scripts/install.py --scope enterprise --fail-closed`
   This writes `hooks.json`, the guardrail script and the session-start hook that adds the security rule to every chat into Cursor's system folder: `/etc/cursor` (Linux/WSL), `/Library/Application Support/Cursor` (macOS) or `C:\ProgramData\Cursor` (Windows).
3. Make sure Python 3 is part of your standard developer image. With `--fail-closed`, a missing Python blocks the guarded actions instead of silently skipping the checks.
4. To update, deploy the new version and run the same command.

### Cloud Agents, remote and self-hosted workers
Cursor copies only repository skills to Cloud Agents, remote SSH sessions and self-hosted workers. Personal skills in `~/.cursor/skills/` reach Cloud Agents only when the user turns on skill sync. For those environments, install with `--scope project` and commit `.cursor/`, or bake the files into the worker image. Team admins can disable personal skill sync under Team Settings → Security & Identity.

## Pinning and updating
- Each GitHub Release (tag `vX.Y.Z`) contains both plugin zips, one zip per skill, and `SHA256SUMS`. Verify downloads with `sha256sum -c SHA256SUMS`. The zips are reproducible, so rebuilding a tag gives identical hashes.
- `python3 scripts/install.py --list` shows installed versions and whether an update is available.
- [CHANGELOG.md](../CHANGELOG.md) lists every change. Each skill carries its own `metadata.version`, and each plugin its own `version`.

## Data handling and security
- The skills, rules and subagents are text. The only code is `guard.py`: Python standard library only, with no network access, no logging, and no storage of prompts or file contents.
- Guardrail messages name the kind of credential they found but never repeat it.
- Only `dependency-vetting` uses the web, to check public advisories and registries. It is instructed never to put code, secrets, internal hostnames or customer names into searches.
- **Air-gapped or restricted networks:** everything except `dependency-vetting` works without network access.
- The review, threat-model, vetting and IaC skills and both subagents are read-only. `secure-feature-build` asks you to approve its plan and never commits, pushes or deploys unless asked.
- Every component treats repository, web and tool content as data, never as instructions (prompt-injection defence).
- Cursor sends prompts and code to its model providers under your agreement with Cursor. This repository adds nothing to that data flow. The guardrails reduce it, by keeping secrets out.

## Known limitations
- Cursor does not yet enforce `readonly: true` on subagents shipped inside plugins; it does for `.cursor/agents/`. Both subagents also say in their instructions that they never modify files. For a hard guarantee, install with `install.py`, which places them in `.cursor/agents/`.
- Hooks are a safety net, not a sandbox. Pattern checks catch the common and dangerous forms of a command, but a determined user can construct commands they don't recognise. Combine them with Cursor's sandbox and allowlists, and with least-privilege credentials on developer machines.
- These tools make Agent apply a security standard consistently. They don't replace SAST/DAST tools, penetration testing or human review of high-risk releases.

## Licensing
- `secure-code-review` and `ai-security-standard` are MIT-licensed.
- Everything else, including `secure-guardrails`, is proprietary ([LICENSE](../LICENSE)). Team and organization licences, including deployment through your own repositories, marketplaces, MDM or CI and support, are available on request.

## Contact
- Licensing and support: **thakurdishant1853@gmail.com**
- Bugs and feature requests: [GitHub issues](https://github.com/thakurdishanttt/cursor-agent-skills/issues)
- Security vulnerabilities: [private vulnerability reporting](https://github.com/thakurdishanttt/cursor-agent-skills/security/advisories/new) (see [SECURITY.md](../SECURITY.md))
