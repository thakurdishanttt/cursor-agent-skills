<!-- Generated from the claude-code-secure-agents standard. Do not edit here. -->
## 2. Sensitive information disclosure (LLM02)
- MUST NOT log full prompts, completions, document text, credentials, tokens,
  or PII. Log IDs, counts, latencies, and hashes.
- MUST NOT expose system prompts, internal config, stack traces, or other
  users' data in responses or model output.
- MUST enforce per-user/per-tenant authorization at data-access time
  (DB query, vector-store filter, object-store ACL), not only in the UI.
- Data sent to third-party model providers MUST be minimized and permitted by
  the project's data-handling policy.
