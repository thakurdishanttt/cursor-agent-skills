<!-- Generated from the claude-code-secure-agents standard. Do not edit here. -->
## 5. Improper output handling (LLM05)
- Model output is untrusted. Escape/encode for the sink: HTML (no
  `innerHTML`/`dangerouslySetInnerHTML` with model text), SQL (parameterize),
  shell (never), file paths (never), URLs (allow-list), `eval` (never).
- Spreadsheet/CSV exports MUST neutralize formula injection
  (cells starting with `= + - @ \t \r`).
- Structured output MUST be schema-validated before use.
