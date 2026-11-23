<!-- Generated from the claude-code-secure-agents standard. Do not edit here. -->
## 11. Application security (all projects)
- **Secrets:** environment or a secret manager only. Never in code, tests,
  fixtures, logs, images, or git. `.env*` files (except `.env.example`) are
  never committed.
- **AuthN/AuthZ:** every non-public route authenticated; authorization
  checked server-side for every resource ID (no IDOR); deny by default.
  Passwords hashed with argon2/bcrypt/scrypt. Session tokens random,
  `HttpOnly`, `Secure`, `SameSite`. Constant-time comparison for secrets.
- **Input validation:** schema-validate every external input with explicit
  types and length/range limits. Reject invalid input.
- **Injection:** parameterized queries only; no shell with user input;
  no dynamic code execution; safe deserialization only (no pickle/yaml.load
  on untrusted data).
- **Paths & SSRF:** normalize paths against an allow-listed base directory;
  allow-list outbound hosts for any user-influenced URL.
- **Errors:** generic client messages; details in server logs only.
- **HTTP:** CORS restricted to known origins; CSP, X-Content-Type-Options,
  frame-ancestors, Referrer-Policy, HSTS.
- **Containers/IaC:** non-root user, minimal base image, no secrets in
  layers, least-privilege service accounts, no public buckets/DBs.
- **Crypto:** standard libraries only, no custom crypto, TLS everywhere,
  never disable certificate verification.
- **Audit:** security-relevant events (login, permission change, data
  export, admin action) are logged without sensitive payloads.
