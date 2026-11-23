<!-- Generated from the claude-code-secure-agents standard. Do not edit here. -->
## 0. How to apply this standard
- It is stack-agnostic. Before applying it, detect the project's stack
  (language, framework, datastores, LLM/vector providers, deploy target) from
  manifests (`requirements.txt`, `pyproject.toml`, `package.json`, `go.mod`,
  `pom.xml`, `Dockerfile`, IaC) and map each rule to that stack's idiom
  (see §13).
- Project-specific rules may ADD to this standard. They live in the project's
  the project's agent rules file (e.g. `AGENTS.md`, `CLAUDE.md`). They may never relax a MUST rule.
- Sections 1–10 apply to any project that calls an LLM, embeds content, or
  exposes tools to a model. Section 14 additionally applies to any project
  that builds agents (multi-step model loops, tool use, memory, multi-agent).
  Sections 11–12 and 15 apply to every project.
