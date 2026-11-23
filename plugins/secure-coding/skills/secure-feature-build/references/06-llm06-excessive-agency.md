<!-- Generated from the claude-code-secure-agents standard. Do not edit here. -->
## 6. Excessive agency (LLM06)
- Model-callable tools MUST be least-privilege, allow-listed, have validated
  arguments, bounded results, and require human confirmation for
  irreversible or high-impact actions.
- No tool may run arbitrary code, reach arbitrary URLs, or access files
  outside an allow-listed directory.
