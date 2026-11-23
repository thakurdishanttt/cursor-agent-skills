# secure-coding

Security skills, rules and subagents for Cursor. They make Agent review, design and build code against OWASP Top 10 for LLM Applications 2025, OWASP Top 10 for Agentic Applications 2026 and OWASP ASVS L2.

## What's inside

| Component | Name | What it does |
|---|---|---|
| Skill | `secure-code-review` (MIT) | Reviews a diff, commit or PR. Ends with APPROVE, REQUEST CHANGES or BLOCK, and gives `file:line`, an attack scenario and a fix for each finding. Can print SARIF 2.1.0. |
| Skill | `ai-security-standard` (MIT) | Applies the security standard while writing code or answering security questions. |
| Skill | `threat-model` | Threat model of a feature, service or AI/agent design, with mitigations and tests. |
| Skill | `dependency-vetting` | ADOPT / ADOPT WITH CONDITIONS / REJECT for a package, SDK, model API or MCP server, with cited CVEs. |
| Skill | `iac-security-review` | Reviews Terraform, CloudFormation, Kubernetes, Helm, Dockerfiles, compose and GitHub Actions. |
| Skill | `secure-feature-build` | Builds a feature end to end: size, plan and threat model, approval, implementation, review loop, real test output. |
| Rule | `security-baseline` | Always on, about 450 tokens: secrets, input validation, authorization, prompt-injection handling, tool safety, cost limits. |
| Rule | `infrastructure-security` | Applies when you edit Terraform, Kubernetes, Docker, Helm or GitHub Actions files. |
| Subagent | `security-reviewer` | Read-only reviewer with fresh context. Used for `secure-feature-build`'s review gate, or run it yourself with `/security-reviewer`. |
| Subagent | `threat-modeler` | Read-only threat modeller (`/threat-modeler`). |

## Use

Agent picks the right skill from your request, for example "review my changes", "threat model this design", "is lodash 4.17.15 safe?", "review our Terraform" or "build a password reset flow". You can also call one directly by typing `/secure-code-review` in Agent chat.

Your organization's own rules go in `.security/rules.md` in the repository. Every skill and subagent enforces them by rule ID. See [docs/customization.md](../../docs/customization.md).

## Requirements

Cursor 2.4 or later. Only `dependency-vetting` uses the network, to check public advisories.

## Known Cursor limitation

Cursor does not yet apply `readonly: true` to subagents shipped inside plugins; it does for subagents in `.cursor/agents/`. Both subagents here also say in their own instructions that they never modify files. For the hard guarantee, install them with `python3 scripts/install.py`, which copies them into `.cursor/agents/`.

Licence: see [LICENSE](../../LICENSE). Contact: thakurdishant1853@gmail.com
