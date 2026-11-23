<!-- Generated from the claude-code-secure-agents standard. Do not edit here. -->
## 14. Agentic applications (OWASP Agentic Top 10, 2026)
Applies to projects that build agents. Complements sections 1–10.
- **ASI01 Agent goal hijack:** the agent's goal and constraints MUST come
  only from trusted configuration and the authenticated user. Content the
  agent reads (documents, web, tool output, other agents) MUST NOT change
  its goal, tools, or permissions.
- **ASI02 Tool misuse:** every tool MUST validate its arguments server-side,
  enforce per-call limits, and be scoped to the minimum resources. Chained
  tool calls MUST be checked as a whole for high-impact actions.
- **ASI03 Identity & privilege abuse:** agents MUST act with the calling
  user's identity and permissions (or a narrower service identity), never a
  shared admin credential. Credentials are short-lived and never placed in
  the model context.
- **ASI04 Agentic supply chain:** MCP servers, plugins, tools, prompts and
  agent definitions MUST come from an allow-list, be pinned, and be reviewed
  like code. Tool descriptions from third parties are untrusted.
- **ASI05 Unexpected code execution:** model-generated code MUST NOT run
  outside an isolated sandbox (no host credentials, restricted network,
  resource limits).
- **ASI06 Memory & context poisoning:** long-term memory and shared context
  MUST record provenance, be scoped per user/tenant, and be validated before
  it is written. Untrusted content MUST NOT be written to memory as fact or
  instruction.
- **ASI07 Insecure inter-agent communication:** messages between agents MUST
  be authenticated and schema-validated; a sub-agent's output is untrusted
  input to its caller.
- **ASI08 Cascading failures:** agent loops MUST have iteration, time, and
  cost caps, and a failing step MUST stop dependent steps rather than
  propagate guesses.
- **ASI09 Human-agent trust exploitation:** high-impact actions MUST show the
  human the exact action and its effect before confirmation; agents MUST NOT
  overstate certainty or hide failures.
- **ASI10 Rogue agents:** every agent action MUST be logged (actor, tool,
  arguments hash, result status) and there MUST be a kill switch that
  revokes an agent's tools and credentials.
