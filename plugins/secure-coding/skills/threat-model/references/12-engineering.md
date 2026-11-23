<!-- Generated from the claude-code-secure-agents standard. Do not edit here. -->
## 12. Engineering standards (all projects)
- Typed code where the language supports it (type hints, TypeScript strict).
- No swallowed exceptions, no bare catch-alls without re-raise/logging.
- No debug prints in committed code; use the project's logger.
- Every behaviour change ships with a test (including one negative/abuse
  case for security-relevant code) or a documented manual check.
- Small, reviewable diffs. No unrelated refactors in feature changes.
- Follow the existing project conventions over personal preference.
