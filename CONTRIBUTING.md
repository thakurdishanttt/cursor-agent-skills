# Contributing

These plugins run inside other people's editors, often on enterprise code, so every change goes through the same gates.

## Ground rules
- **Never edit `plugins/secure-coding/skills/*/references/`.** It is generated from the [kit's standard](https://github.com/thakurdishanttt/claude-code-secure-agents/blob/main/standards/ai-security.md). Propose rule changes there; they arrive here through the weekly sync.
- Security rules and guardrails may be **added or tightened, never relaxed**.
- **Read-only stays read-only:** the review, threat-model, vetting and IaC skills and both subagents never modify files. Nothing commits, pushes or deploys unless the user asks.
- **Budgets:** skill description ≤ 420 characters, `SKILL.md` ≤ ~1,600 tokens, always-on rule ≤ ~500 tokens. Put detail in references, not in always-loaded text.
- **Guardrails need both directions of tests:** every new block or ask pattern comes with must-block cases and must-allow cases for the everyday commands it could catch by mistake.
- Follow Cursor's documented formats ([plugins](https://cursor.com/docs/reference/plugins), [skills](https://cursor.com/docs/skills), [subagents](https://cursor.com/docs/subagents), [hooks](https://cursor.com/docs/hooks)). Check the docs before relying on a field or behaviour.

## Making a change
1. Branch from `main`.
2. Edit the component and bump versions: the skill's `metadata.version`, the plugin's `version`, and the marketplace's `metadata.version` (`python3 scripts/bump.py <skill>` does the patch bump). Use patch for wording, minor for new behaviour, and major for changed output formats.
3. Run the gates:
   ```bash
   python3 scripts/validate.py                  # must pass
   python -m pytest tests/                      # must pass
   python3 scripts/run_evals.py --repeat 3      # must be 100% for skill, rule, subagent or eval changes (needs CURSOR_API_KEY)
   python3 scripts/package.py                   # zips build
   ```
4. Update `CHANGELOG.md` under **Unreleased**.
5. Open a PR using the template and paste the eval table. CODEOWNERS review is required.

## Adding a skill
- Folder name = `name` in the frontmatter (lowercase, hyphens, ≤ 64 characters).
- The description says **what** the skill does and **when** to use it, with two or three phrases users actually type.
- Add the skill to `skills.json` with its licence, and add at least one eval case. A review-type skill needs both a should-find case and a should-not-flag case.
- MIT skills declare `license: MIT`; proprietary skills declare no licence field.

## Reporting bugs
- Wrong or missed finding, or a guardrail false positive → open an issue with a minimal example.
- Security issue or guardrail bypass → follow [SECURITY.md](SECURITY.md) instead.
