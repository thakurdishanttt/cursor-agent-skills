# Security policy

## Reporting a vulnerability
Please **do not open a public issue**. Report privately through GitHub's
[private vulnerability reporting](https://github.com/thakurdishanttt/cursor-agent-skills/security/advisories/new)
(Security tab → "Report a vulnerability"), or email thakurdishant1853@gmail.com.

Include the affected component and version (skill `metadata.version`, or the
plugin `version` in `.cursor-plugin/plugin.json`), your Cursor version and
model, and steps, a prompt or a command that reproduces the issue.

| Stage | Target |
|---|---|
| Acknowledgement | 3 business days |
| Triage and severity | 7 business days |
| Fix for Critical / High | 30 days, released as a new version |

## What counts as a vulnerability here
- **A guardrail bypass:** a dangerous command, secret file or credential format that `secure-guardrails` claims to block but doesn't, or a way to switch a hook off from a repository.
- A component that leads Agent to **leak data**: secrets, source code or internal names in web searches or output.
- A component that makes Agent **follow injected instructions** from repository, web or tool content.
- A read-only skill or subagent that **modifies files**, or anything that commits, pushes or deploys without being asked.
- A rule in the standard that is **wrong or unsafe**.
- Anything executable or obfuscated in a published package other than `guard.py`.

Missed findings in a review (false negatives) and guardrail false positives are quality bugs: open a normal issue with a minimal example, and it becomes a test or eval case.

## Security model
- **Skills, rules and subagents are text.** `scripts/validate.py` rejects executables, binaries and symlinks in them.
- **One script, audited by tests.** `plugins/secure-guardrails/scripts/guard.py` uses only the Python standard library. It makes no network calls, writes no files, logs nothing and never echoes a secret. 135 tests cover both blocking and must-allow behaviour on Linux, macOS and Windows.
- **Hooks fail safely.** The script always returns valid JSON. It fails open by default and closed with `--fail-closed`.
- **Policy only tightens.** Repository policy files add rules and can't relax the built-ins. Enterprise hooks outrank all others.
- **No network** except `dependency-vetting`, which searches public advisories and registries. It is instructed never to include code, secrets, internal hostnames or customer names in queries.
- **Untrusted content is data.** Every component tells Agent to treat file contents, comments, issues, PR text, web pages and tool output as data, and to report embedded instructions instead of following them.
- **Supply chain.** The standard is generated from the kit repository at a recorded commit (`references/KIT_VERSION.txt`). Updates arrive as reviewable pull requests, and nothing is fetched at run time. Releases are reproducible zips with `SHA256SUMS`.

## Supported versions
The latest release of each plugin is supported. Update with Customize → Plugins, or re-run `python3 scripts/install.py`.
