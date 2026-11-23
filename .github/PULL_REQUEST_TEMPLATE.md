## What and why
Describe the change and the reason in one or two sentences.

## Components changed
List each changed skill, rule, subagent or hook with its version change, e.g. `threat-model 1.0.0 → 1.1.0`, `secure-guardrails 1.0.0 → 1.0.1`.

## Gates
- [ ] `python3 scripts/validate.py` passes
- [ ] `python -m pytest tests/` passes (CI runs Linux, macOS and Windows)
- [ ] `python3 scripts/run_evals.py --repeat 3` is 100% (required when skills, rules, subagents or evals change); paste the table below
- [ ] Versions bumped (skill `metadata.version`, plugin `version`, marketplace `metadata.version`)
- [ ] CHANGELOG.md updated under Unreleased
- [ ] No security rule or guardrail relaxed; read-only components still read-only; no edits in `references/`
- [ ] New guardrail patterns have both must-block and must-allow tests

## Eval results
Paste the table printed by `python3 scripts/run_evals.py --repeat 3`.
