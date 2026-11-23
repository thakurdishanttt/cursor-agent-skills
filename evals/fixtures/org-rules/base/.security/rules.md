# Organization security rules

These add to the standard. Severity is High unless stated.

- **ORG-1** Every outbound HTTP call MUST set an explicit timeout. Severity: Medium.
- **ORG-2** Secrets MUST be read from the secrets manager client `vault.get()`, never from environment variables. Severity: High.
