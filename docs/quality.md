# Quality: how accuracy, speed and cost are measured

## Policy
- **No release without green gates.** Every test and every eval run must pass; there is no "mostly passing".
- **Measure, don't claim.** AI agents are not deterministic and no skill is 100% accurate. Accuracy is the pass rate across repeated runs, published here.
- **False positives are failures.** A review that cries wolf, or a guardrail that blocks everyday work, gets switched off. Both are tested.
- **Budgets are enforced in CI:** skill description ≤ 420 characters, `SKILL.md` ≤ ~1,600 tokens, always-on rule ≤ ~500 tokens.

## Layer 1: deterministic tests (`tests/`, every push, Linux, macOS and Windows, Python 3.10 and 3.13)

| Suite | Cases | What it proves |
|---|---|---|
| `test_guard.py` | 135 | Each guardrail blocks what it must (10 credential formats, 17 secret-file paths, 30 dangerous commands including `bash <(curl …)` and `eval "$(curl …)"`), asks before 20 irreversible commands, and **allows** 6 ordinary prompts, 13 ordinary files and 25 everyday commands (`rm -rf node_modules`, `cat .env.example`, `terraform plan` and others). Also: secrets are never echoed back, organization policy can add but not relax rules, invalid policy files are ignored, and malformed input still produces valid JSON so Agent never freezes. |
| `test_install.py` | 8 | User, project and enterprise scopes install to Cursor's documented paths, with the right working-directory-relative hook commands. The installed hook really blocks. Re-running updates without duplicates, and uninstalling removes only what was installed, keeping your own skills, agents and hooks. |
| `test_validate.py` | 17 | The validator passes this repository and **rejects** 15 kinds of broken package (writable subagent, unknown hook event, missing hook script, name mismatch, bad version, wrong licence, malformed rule, path escaping the plugin, over-budget description, leaked secret, executable in a skill), and release zips are byte-for-byte reproducible. |
| `test_extract_sarif.py` | 4 | SARIF is extracted from Cursor CLI JSON and plain text, and incomplete results are flagged. |

What the tests caught during development: the first guardrail draft blocked `cat .env.example`, a false positive, and missed `git clean -fdx` and `aws s3 rm`. All three were fixed before release, along with three common evasions of the download-and-run rule.

## Layer 2: evals in real Cursor sessions (`scripts/run_evals.py`)

Each case copies a fixture repository to a temporary folder, commits the base, applies the change as an uncommitted diff, and writes a `.cursor/cli.json` that allows only the tools the case needs. It then runs `agent -p` headless with the `secure-coding` plugin loaded from this repository (`--plugin-dir`), so the real packaging is what's tested.

| Case | Checks |
|---|---|
| `review-finds-planted-vulns` | Picks `secure-code-review`. Finds the planted SQL injection, command injection and path traversal. Verdict BLOCK. No files changed. |
| `review-no-false-positive` | Clean, tested change: APPROVE, no Critical or High finding. |
| `review-sarif-output` | Valid SARIF 2.1.0 with at least 3 located findings. |
| `review-enforces-org-rules` | Reports the violated `.security/rules.md` rule by ID (`ORG-1`). |
| `review-multi-file-idor` | Finds a missing tenant check that only shows up across four files. |
| `review-safe-but-scary-no-false-alarm` | Approves code that looks dangerous but is safe (fixed-argument `subprocess`, checksum-verified download, allowlisted `ORDER BY`). |
| `iac-review-finds-misconfigs` | Picks `iac-security-review`. Finds open SSH, wildcard IAM, a public database, a privileged and root container, `pull_request_target` and an unpinned action. |
| `threat-model-rag-design` | Picks `threat-model`. Covers prompt injection, tenant isolation, the auto-executing refund tool and the missing rate limit. |
| `dependency-vetting-known-cve` | Picks `dependency-vetting` for lodash 4.17.15. Cites a CVE and recommends 4.17.21. |
| `feature-build-plans-and-waits` | Picks `secure-feature-build`. States a tier, writes a threat model and waits for approval before writing code. |
| `standard-answers-logging-question` | Picks `ai-security-standard`. Says not to log full prompts unredacted. |
| `no-skill-for-unrelated-task` | Uses no skill for an unrelated prompt. |

The skill texts are the same ones that passed this suite 36/36 on Claude Sonnet, 12/12 on Opus and 12/12 on Haiku in [claude-secure-agents-skills](https://github.com/thakurdishanttt/claude-secure-agents-skills/blob/main/docs/quality.md). Cursor results are published below after each run.

## Latest Cursor results

Results are added here from the **Evals** workflow, which needs the `CURSOR_API_KEY` repository secret. Raw results are uploaded as the `evals-results` artifact of each run.

## Running it

```bash
python -m pytest tests/                                   # deterministic layer, about 3 s, no API calls
python3 scripts/run_evals.py --dry-run                    # prepare every eval case, print the commands, spend nothing
CURSOR_API_KEY=... python3 scripts/run_evals.py --jobs 6  # all cases once
python3 scripts/run_evals.py --repeat 3 --json evals/last-run.json
python3 scripts/run_evals.py --case threat-model-rag-design --model <cursor-model-id>
```

## Adding a case
1. Add a fixture folder under `evals/fixtures/`: `base/` is committed first, and `change/` holds the edited files when the case reviews a diff.
2. Add the case to `evals/cases.json`: the expected `skill` (or `null`), the `prompt`, the allowed `tools`, `must` and `must_not` regexes, and `unchanged` for read-only skills.
3. Run it with `--repeat 3`. A case that passes only sometimes is a finding: fix the skill, not the test.
4. Every reported bug becomes a case. Every guardrail false positive becomes a must-allow test.

## Limits
- Regex checks confirm that findings are *present*; they don't grade every sentence. Read the answers in the JSON after changes.
- `dependency-vetting` depends on live web results, so it may vary as advisories change.
- Pattern-based guardrails catch common and dangerous command forms, not every possible rewrite ([enterprise.md](enterprise.md#known-limitations)).
