# CI integration: review every pull request and publish to code scanning

`secure-code-review` and `iac-security-review` can print their findings as SARIF 2.1.0. `scripts/extract_sarif.py` pulls that out of Agent's answer and validates it, and GitHub code scanning (or any SARIF-aware dashboard) then shows each finding on the exact line.

## How it works

1. The Cursor CLI runs headless (`agent -p`) in the checked-out PR, with the `secure-coding` plugin loaded.
2. The review prints its normal report, plus a SARIF block, because the prompt asks for SARIF.
3. `extract_sarif.py` checks the SARIF (version, rule IDs, levels, and a file and line for every finding) and writes `review.sarif`.
4. `github/codeql-action/upload-sarif` publishes it to the repository's Security → Code scanning tab and annotates the PR.

The eval case `review-sarif-output` runs the same steps on a fixture with planted SQL injection, command injection and path traversal, and requires valid SARIF with at least three located findings ([quality.md](quality.md)).

## Setup

1. Commit the components into the repository you want reviewed, so CI and developers use the same version:
   ```bash
   python3 /path/to/cursor-agent-skills/scripts/install.py --scope project --project-dir . --no-guardrails
   git add .cursor && git commit -m "Add security skills"
   ```
2. Copy `scripts/extract_sarif.py` from this repository to `.github/scripts/extract_sarif.py` in that repository.
3. Create a Cursor API key (Cursor dashboard → Integrations → API Keys) and add it as a repository secret named `CURSOR_API_KEY` (Settings → Secrets and variables → Actions).
4. Allow only read-only tools in CI by committing `.cursor/cli.json`:
   ```json
   { "permissions": { "allow": ["Read(**)", "Shell(git)"], "deny": ["Write(**)", "Read(.env*)", "WebFetch(*)"] } }
   ```
5. Add this workflow as `.github/workflows/security-review.yml`:

```yaml
name: Security review

on:
  pull_request:

permissions:
  contents: read
  security-events: write   # upload SARIF to code scanning

jobs:
  review:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
          persist-credentials: false
      - name: Install Cursor CLI
        run: |
          curl -fsS https://cursor.com/install | bash
          echo "$HOME/.local/bin" >> "$GITHUB_PATH"
      - name: Review
        env:
          CURSOR_API_KEY: ${{ secrets.CURSOR_API_KEY }}
          BASE: ${{ github.event.pull_request.base.sha }}
        run: |
          agent -p "Review the changes in this pull request (git diff $BASE...HEAD) and output SARIF." \
            --output-format json --trust < /dev/null > review.json
          python3 .github/scripts/extract_sarif.py review.json -o review.sarif
      - uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: review.sarif
          category: secure-code-review
```

## Notes
- **Forks:** `pull_request` workflows from forks don't receive secrets, so the review runs only on branches in the same repository. Don't switch to `pull_request_target` to work around this: that would run untrusted PR code with your secrets. The `iac-security-review` skill flags exactly that pattern.
- **Read-only:** `.cursor/cli.json` denies writes and web access. Without `--force`, the CLI also rejects anything else that would need approval.
- **Blocking merges:** to fail the job on a BLOCK verdict, add `grep -q '"level": "error"' review.sarif && exit 1` after the extract step, or use code-scanning branch protection rules.
- **Infrastructure PRs:** add a second job, or change the prompt to "review our infrastructure changes … and output SARIF", to run `iac-security-review`.
- **Pin the CLI** in regulated environments: mirror the installer and a known CLI version internally instead of piping it from the internet. That is the same advice the guardrails enforce on developer machines.
- Code scanning requires GitHub Advanced Security on private repositories. Public repositories have it for free.
