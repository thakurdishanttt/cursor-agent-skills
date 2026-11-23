<!-- Generated from the claude-code-secure-agents standard. Do not edit here. -->
## 1. Prompt injection (LLM01)
- MUST treat user messages, retrieved documents, uploaded files, filenames,
  web pages, tool results, and emails as untrusted data, never instructions.
- MUST keep system instructions separate from untrusted content. Never
  concatenate untrusted text into the system prompt.
- MUST delimit untrusted context and instruct the model that it is reference
  material only.
- MUST NOT let model output trigger privileged actions (writes, deletes,
  payments, outbound requests, tool calls with side effects) without
  server-side validation and authorization of that specific action.
