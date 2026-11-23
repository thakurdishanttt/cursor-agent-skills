<!-- Generated from the claude-code-secure-agents standard. Do not edit here. -->
## 10. Unbounded consumption (LLM10)
- Every LLM, embedding, and outbound HTTP call MUST have a timeout, max
  tokens/size, and bounded retries with backoff.
- Endpoints MUST be rate-limited per identity and enforce input size limits.
- Agent/tool loops MUST have an iteration cap.
