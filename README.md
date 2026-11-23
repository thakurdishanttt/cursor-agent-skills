# cursor-agent-skills

**Enterprise security for Cursor.** Two Cursor plugins that make Agent review, design and build code against OWASP's LLM, Agentic and application-security standards, and that block the most damaging mistakes deterministically: credentials pasted into prompts, secret files read into context, and `curl | bash`.

| | |
|---|---|
| **Plugins** | `secure-coding`: 6 skills, 2 rules, 2 read-only subagents · `secure-guardrails`: 4 security hooks |
| **Standards** | OWASP Top 10 for LLM Applications 2025 · OWASP Top 10 for Agentic Applications 2026 · OWASP ASVS L2 |
| **Works in** | Cursor 2.4+ editor, Cursor CLI (`agent`) and Cloud Agents (repo-installed skills) |
| **Install** | From GitHub in Cursor, a team marketplace, per repository, per user, or system-wide through MDM |
| **Quality gate** | 164 automated tests on Linux, macOS and Windows; 12 eval cases in real headless Cursor sessions ([details](docs/quality.md)) |
| **Integrations** | SARIF 2.1.0 for GitHub code scanning · organization rules in `.security/rules.md` and `.security/guardrails.json` · releases with SHA256SUMS |
| **Owner** | Thakur Dishant Kumar |

---

## What's inside

### `secure-coding`: how Agent thinks

| Component | Use it for | Triggers on | Output |
|---|---|---|---|
| Skill `secure-code-review` (MIT) | Security and correctness review of a diff, commit or PR | "review my changes", "is this change safe?" | APPROVE / REQUEST CHANGES / BLOCK, findings with `file:line`, attack scenario and fix; SARIF on request |
| Skill `ai-security-standard` (MIT) | Applying the standard while coding or answering security questions | "should we log prompts?", code touching input, auth, secrets, LLMs, RAG, tools | Rules applied, cited by section |
| Skill `threat-model` | Threat modelling a feature, service or AI/agent design | "threat model…", "what could go wrong" | Assets, trust boundaries, threat table with mitigation and test |
| Skill `iac-security-review` | Terraform, CloudFormation, Kubernetes, Helm, Dockerfiles, compose, GitHub Actions | "review our infrastructure changes" | Verdict and findings with resource or `file:line` and the exact setting to change |
| Skill `dependency-vetting` | Packages, SDKs, model APIs, MCP servers | adding or upgrading a dependency | ADOPT / ADOPT WITH CONDITIONS / REJECT with cited CVEs |
| Skill `secure-feature-build` | Building a feature end to end under security gates | "build…", "implement…", "add an endpoint" | Sized plan with threat model → your approval → implementation → review loop → real test output |
| Rule `security-baseline` | Always-on core rules, about 450 tokens per request | every request | — |
| Rule `infrastructure-security` | Applies when editing infrastructure and pipeline files | `*.tf`, Dockerfiles, Kubernetes, Helm, workflows | — |
| Subagent `security-reviewer` | Independent read-only review with fresh context (`/security-reviewer`) | before merging; `secure-feature-build`'s review gate | Verdict and findings |
| Subagent `threat-modeler` | Read-only threat modelling (`/threat-modeler`) | new trust boundaries | Threat table |

### `secure-guardrails`: what Agent cannot do

| Hook | Effect |
|---|---|
| `beforeSubmitPrompt` | Blocks a prompt that contains a credential (Anthropic, OpenAI, GitHub, AWS, Google, Slack, Stripe or Cursor keys, private keys, JWTs) before it reaches the model. |
| `beforeReadFile` | Denies reading `.env*`, private keys, cloud credentials, `.netrc`, `*.tfvars` and Terraform state. `.env.example` and other templates stay readable. |
| `beforeShellExecution` | Denies `curl \| bash` and its variants, `rm -rf /` or `~`, force-pushing to main, printing secret files, disabling TLS verification, and credentials on the command line. Asks before `git push`, publishing, image pushes, `terraform apply`, `kubectl` and `helm` changes, cloud deletes and `DROP TABLE`. |
| `beforeMCPExecution` | Denies MCP calls whose arguments contain a credential. |

Messages name the kind of credential but never repeat it. Nothing is logged or sent anywhere.

## Install

**In Cursor:** open Customize → Plugins, choose **From GitHub Repository**, enter `thakurdishanttt/cursor-agent-skills`, then install `secure-coding` and, if you want the hooks, `secure-guardrails`.

**Per repository** (recommended for teams, because everyone gets the same versions):

```bash
git clone https://github.com/thakurdishanttt/cursor-agent-skills.git
python3 cursor-agent-skills/scripts/install.py --scope project --project-dir ./my-service
cd my-service && git add .cursor && git commit -m "Add security skills, rules and guardrails"
```

**Per developer:** `python3 scripts/install.py`. **Every user on a machine, through MDM:** `sudo python3 scripts/install.py --scope enterprise`. **Cursor CLI:** `agent --plugin-dir ./plugins/secure-coding`.

All options, Windows notes and verification: [docs/installation.md](docs/installation.md).

## For enterprises

| Need | Where |
|---|---|
| Rollout through a team marketplace, per repository, or MDM; Cloud Agents; air-gapped use | [docs/enterprise.md](docs/enterprise.md) |
| Your own security rules and guardrails | [docs/customization.md](docs/customization.md) |
| Review every PR in CI and publish to GitHub code scanning (SARIF) | [docs/ci-integration.md](docs/ci-integration.md) |
| Controls mapped to SOC 2, ISO 27001, PCI DSS and NIST SSDF for auditors | [docs/compliance.md](docs/compliance.md) |
| How quality is measured | [docs/quality.md](docs/quality.md) |
| Verify a release | each GitHub Release has the zips and `SHA256SUMS` (`sha256sum -c SHA256SUMS`) |

## Why it is cheap and fast

- **Progressive loading.** At session start Agent sees only each skill's one-line description, at most 420 characters. A `SKILL.md` (≤ ~1,600 tokens) loads only when needed, and it reads only the standard sections the change touches.
- **One small always-on rule.** About 450 tokens; the infrastructure rule loads only for infrastructure files.
- **Hooks cost no tokens.** They are local scripts that run in milliseconds and never call a model.
- **Sized work.** `secure-feature-build` picks tier S, M or L first, so small changes skip the full planning and review cycle.
- **Budgets enforced in CI.** The validator fails a description over 420 characters, a skill over ~1,600 tokens or an always-on rule over ~500 tokens.

## Accuracy

No AI system is 100% accurate, so this repo measures accuracy instead of claiming it:
- **Hooks are deterministic** and tested by 135 cases. These cover attacks that must be blocked and everyday commands that must keep working, so false positives count as failures too.
- **Skills** are tested by `scripts/run_evals.py` in real headless Cursor sessions, with the plugin loaded from this repo. The cases check skill selection, planted-vulnerability detection (including a cross-file IDOR), no false alarms on code that only looks dangerous, valid SARIF, organization rules, and that read-only skills change nothing.

A release needs every run to pass. Results and method: [docs/quality.md](docs/quality.md).

## How it stays current

The security standard has one source of truth, [claude-code-secure-agents](https://github.com/thakurdishanttt/claude-code-secure-agents), which watches OWASP, NIST, MITRE and AI-tooling changes. A weekly workflow syncs it into every skill's `references/`, bumps versions and opens a pull request for review.

## Repository layout

```
.cursor-plugin/marketplace.json    lists both plugins (for "From GitHub Repository" and team marketplaces)
plugins/
  secure-coding/                   .cursor-plugin/plugin.json, skills/, rules/, agents/, assets/
  secure-guardrails/               .cursor-plugin/plugin.json, hooks/hooks.json, scripts/guard.py
scripts/
  install.py                       install / update / list / remove: user, project or enterprise scope
  validate.py                      marketplace, plugins, skills, rules, subagents and hooks against Cursor's formats
  run_evals.py                     eval suite in real headless Cursor sessions (needs CURSOR_API_KEY)
  package.py                       reproducible plugin and skill zips + SHA256SUMS
  sync_from_kit.py, bump.py        sync the standard from the kit; bump versions
  extract_sarif.py                 pulls and validates SARIF from a review, for CI
tests/                             hooks, installer and validator tests (pytest)
evals/                             12 cases and their fixture repositories
docs/                              installation, enterprise, customization, ci-integration, compliance, quality, architecture
.github/workflows/                 ci.yml (3 OSes), evals.yml, release.yml, sync-kit.yml
```

## Support

Bugs and requests: [GitHub issues](https://github.com/thakurdishanttt/cursor-agent-skills/issues). Security issues: [SECURITY.md](SECURITY.md). Change process: [CONTRIBUTING.md](CONTRIBUTING.md). Releases: [CHANGELOG.md](CHANGELOG.md).

## Licence

Copyright © 2026 Thakur Dishant Kumar. `secure-code-review` and `ai-security-standard` are MIT-licensed. Everything else, including `secure-guardrails`, is proprietary, and team and organization licences are available on request. See [LICENSE](LICENSE). Contact: thakurdishant1853@gmail.com.
