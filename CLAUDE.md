# Working in this repository

This repository ships Cursor plugins that other people install into their editors and fleets. Treat every change as a release to customers.

- Never edit `plugins/secure-coding/skills/*/references/`. Run `python3 scripts/sync_from_kit.py` instead.
- After changing a skill, rule, subagent or hook: bump its version (`python3 scripts/bump.py <skill>` for skills), then run `python3 scripts/validate.py` and `python -m pytest tests/`. For skill, rule, subagent or eval changes, also run `python3 scripts/run_evals.py --repeat 3` (needs `CURSOR_API_KEY`) and report the table. Do not finish with a failing gate.
- Keep descriptions ≤ 420 characters, `SKILL.md` ≤ ~1,600 tokens and always-on rules ≤ ~500 tokens.
- Never relax a security rule or guardrail. Never make a read-only component write. Every new guardrail pattern needs must-block and must-allow tests.
- Check Cursor's docs (cursor.com/docs) before relying on a field or behaviour.
- Update CHANGELOG.md under "Unreleased".
