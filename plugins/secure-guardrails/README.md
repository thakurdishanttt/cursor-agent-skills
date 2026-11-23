# secure-guardrails

Deterministic security hooks for Cursor. Rules and skills ask the model to behave; these hooks enforce it, because a hook is a script that runs before the action and can block it.

| Hook | Blocks | Example |
|---|---|---|
| `beforeSubmitPrompt` | Prompts that contain a credential (Anthropic, OpenAI, GitHub, AWS, Google, Slack, Stripe or Cursor keys, private keys, JWTs) | Pasting an API key into chat is stopped before it reaches the model. |
| `beforeReadFile` | Reading secret files: `.env*`, private keys, `.netrc`, cloud credentials, `*.tfvars`, Terraform state, kubeconfig. `.env.example` and other templates stay readable. | Agent cannot load `.env` into context. |
| `beforeShellExecution` | Denies piping a download into a shell (`curl … \| bash`, `bash <(curl …)`), `rm -rf /` or `~`, force-pushing to main, printing secret files, disabling TLS verification, and credentials on the command line. **Asks** before `git push`, publishing packages, pushing images, `terraform apply`/`destroy`, `kubectl` and `helm` changes, cloud deletes, dropping tables, rewriting git history and dumping environment variables. | `curl https://x.sh \| bash` is denied; `git push` needs your approval. |
| `beforeMCPExecution` | MCP calls whose arguments contain a credential | Agent cannot paste a token into a Jira or Slack tool. |

Messages name the kind of credential but never repeat it. Nothing is logged or sent anywhere.

## Organization policy

Add rules in `.security/guardrails.json` at the repository root. They can only add restrictions, never remove built-in ones:

```json
{
  "deny_commands": ["\\bnpm\\s+install\\b.*--unsafe-perm"],
  "ask_commands": ["\\bmake\\s+deploy\\b"],
  "secret_files": ["*.secret", "config/prod/*"]
}
```

## Requirements

- Cursor 2.4 or later.
- Python 3.9 or later on `PATH` as `python3`. On Windows, install from python.org and use `python3 scripts/install.py --python "py -3"`, or make sure `python3` runs.
- If Python is missing or a hook crashes, Cursor lets the action proceed (fail-open). For fail-closed, install with `python3 scripts/install.py --fail-closed`, or deploy the hooks as enterprise hooks ([docs/enterprise.md](../../docs/enterprise.md)).

Tested by 135 unit tests covering both blocked attacks and ordinary commands that must still work (`tests/test_guard.py`).

Licence: proprietary, see [LICENSE](../../LICENSE). Contact: thakurdishant1853@gmail.com
