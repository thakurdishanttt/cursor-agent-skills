<!-- Generated from the claude-code-secure-agents standard. Do not edit here. -->
## 8. Vector & embedding weaknesses (LLM08)
- Vector stores MUST require authentication and not be publicly reachable.
- Every similarity query MUST apply the caller's access filter.
- Deleting a source MUST delete its embeddings.
