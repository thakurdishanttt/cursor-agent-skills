#!/usr/bin/env python3
"""Deterministic security guardrails for Cursor hooks.

Cursor pipes one JSON object to stdin and reads one JSON object from stdout.
Usage (from hooks.json):  python3 ./scripts/guard.py <check>

  prompt   beforeSubmitPrompt    block prompts that contain a credential
  read     beforeReadFile        deny reading secret files (.env, keys, ...)
  shell    beforeShellExecution  deny dangerous commands, ask before irreversible ones
  mcp      beforeMCPExecution    deny MCP calls whose arguments contain a credential

Organizations can add (never remove) rules in `.security/guardrails.json` at
the workspace root:
  {"deny_commands": ["regex"], "ask_commands": ["regex"], "secret_files": ["glob"]}

Design rules:
- Always print valid JSON: Cursor treats invalid output from a permission hook
  as a block, so a bug here must not freeze the agent.
- Never echo a secret back: messages name the kind of credential only.
- Stdlib only, no network, no logging of prompts or file contents.
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
import sys
from pathlib import PurePath

VERSION = "1.0.0"

# Credential formats with a distinctive prefix or structure, so ordinary text
# does not trigger them. (kind, pattern)
SECRET_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("Anthropic API key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}")),
    ("OpenAI API key", re.compile(r"\bsk-(?:proj-|svcacct-|admin-)?[A-Za-z0-9_-]{32,}")),
    ("GitHub token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})")),
    ("AWS access key ID", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("Slack token", re.compile(r"\bxox[abprs]-[0-9A-Za-z-]{10,}")),
    ("Stripe live key", re.compile(r"\b(?:sk|rk)_live_[0-9A-Za-z]{20,}")),
    ("private key", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
    ("Cursor API key", re.compile(r"\bkey_[0-9a-f]{64}\b")),
    ("JSON Web Token", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
]

# File names whose contents are credentials. Matched against the base name
# (case-insensitive) unless the pattern contains a slash.
SECRET_FILES = [
    ".env", ".env.*", "*.env", ".envrc",
    "*.pem", "*.key", "*.p12", "*.pfx", "*.jks", "*.keystore",
    "id_rsa", "id_rsa*", "id_dsa*", "id_ecdsa*", "id_ed25519*",
    ".netrc", "_netrc", ".pgpass", ".git-credentials",
    "credentials", "credentials.json", "service-account*.json", "*-credentials.json",
    "secrets.yaml", "secrets.yml", "secrets.json", "*.tfvars", "terraform.tfstate*",
    "*/.aws/credentials", "*/.docker/config.json", "*/.kube/config", "*/.ssh/*",
]
# Templates that are meant to be committed and read.
SAFE_FILES = [".env.example", ".env.sample", ".env.template", ".env.dist", "*.example", "*.sample",
              "*.pub", "*.tfvars.example", "known_hosts"]

READERS = r"(?:cat|less|more|head|tail|bat|nl|strings|xxd|od|base64|type|get-content|gc|sed|awk|grep|cp|scp|curl)"

# (reason, pattern) — always denied.
DENY_COMMANDS: list[tuple[str, re.Pattern]] = [
    ("pipes a download straight into a shell or interpreter",
     re.compile(r"\b(?:curl|wget|iwr|invoke-webrequest)\b[^|;&]*\|\s*(?:sudo\s+)?(?:ba|z|k|da|fi)?sh\b|"
                r"\b(?:curl|wget)\b[^|;&]*\|\s*(?:sudo\s+)?(?:python3?|node|perl|ruby)\b|"
                r"\b(?:iwr|irm|invoke-webrequest|invoke-restmethod)\b[^|;]*\|\s*iex\b|"
                r"\b(?:ba|z|k|da)?sh\b[^;&|]*(?:\$\(|`|<\()\s*(?:curl|wget)\b|"
                r"\b(?:eval|source|\.)\s+(?:\"?\$\(|<\()\s*(?:curl|wget)\b", re.I)),
    ("recursively deletes the filesystem root or home directory",
     re.compile(r"\brm\s+(?:-[a-z]*\s+)*-[a-z]*(?:r[a-z]*f|f[a-z]*r)[a-z]*\s+(?:-[a-z-]+\s+)*"
                r"(?:/|/\*|~|~/|~/\*|\$home|\$\{home\}|\.\.?/?)(?:\s|$|;|&)", re.I)),
    ("force-pushes to the main branch",
     re.compile(r"\bgit\s+push\b(?=.*(?:\s--force\b|\s-f\b|\s--force-with-lease\b|\s\+))(?=.*\b(?:main|master)\b)", re.I)),
    ("prints a secret file",
     re.compile(READERS + r"\b[^|;&]*(?:^|[\s/'\"])(?:\.env(?:\.(?!example\b|sample\b|template\b|dist\b)[a-z0-9_-]+)?|id_(?:rsa|dsa|ecdsa|ed25519)|"
                r"\.netrc|\.git-credentials|credentials(?:\.json)?|[\w.-]+\.pem|[\w.-]+\.key)(?=$|[\s'\";|&)])", re.I)),
    ("disables TLS certificate verification globally",
     re.compile(r"\bgit\s+config\s+(?:--global\s+)?http\.sslverify\s+false\b|\bnpm\s+config\s+set\s+strict-ssl\s+false\b|"
                r"NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*0", re.I)),
]

# (reason, pattern) — the user must confirm. Irreversible or outward-facing.
ASK_COMMANDS: list[tuple[str, re.Pattern]] = [
    ("pushes commits", re.compile(r"\bgit\s+push\b", re.I)),
    ("rewrites or discards git history", re.compile(r"\bgit\s+(?:reset\s+--hard|clean\s+-[a-z]*f[a-z]*|filter-branch|filter-repo)\b", re.I)),
    ("skips git hooks", re.compile(r"\bgit\s+(?:commit|push)\b.*\s--no-verify\b", re.I)),
    ("publishes a package", re.compile(r"\b(?:npm|pnpm|yarn)\s+publish\b|\btwine\s+upload\b|\bcargo\s+publish\b|"
                                       r"\bgem\s+push\b|\bpoetry\s+publish\b|\bdotnet\s+nuget\s+push\b", re.I)),
    ("pushes a container image", re.compile(r"\b(?:docker|podman)\s+push\b", re.I)),
    ("changes cloud infrastructure", re.compile(r"\bterraform\s+(?:apply|destroy|import|state\s+rm)\b|\bpulumi\s+(?:up|destroy)\b|"
                                               r"\bkubectl\s+(?:apply|delete|replace|patch|scale|drain)\b|"
                                               r"\bhelm\s+(?:install|upgrade|uninstall|rollback)\b|"
                                               r"\b(?:aws|gcloud|az)\b.*\b(?:delete|terminate|destroy|remove|rm|rb)\b", re.I)),
    ("deletes database data", re.compile(r"\b(?:drop\s+(?:database|table|schema)|truncate\s+table)\b|\bdropdb\b", re.I)),
    ("dumps environment variables", re.compile(r"^\s*(?:printenv|env|set)\s*$|\bprintenv\s*(?:$|[|>])|\bget-childitem\s+env:", re.I)),
    ("makes files world-writable", re.compile(r"\bchmod\s+(?:-[a-z]+\s+)*(?:0?777|a\+w|o\+w)\b", re.I)),
]


def project_dir(event: dict) -> str:
    roots = event.get("workspace_roots") or []
    return os.environ.get("CURSOR_PROJECT_DIR") or (roots[0] if roots else os.getcwd())


def org_policy(event: dict) -> dict:
    """Extra rules from .security/guardrails.json. Adds only; bad entries are ignored."""
    path = os.path.join(project_dir(event), ".security", "guardrails.json")
    try:
        with open(path, encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, ValueError):
        return {"deny": [], "ask": [], "files": []}

    def regexes(key: str) -> list[tuple[str, re.Pattern]]:
        out = []
        for pat in raw.get(key, []) if isinstance(raw.get(key), list) else []:
            try:
                out.append((f"matches organization rule `{pat}`", re.compile(str(pat), re.I)))
            except re.error:
                continue
        return out

    files = [str(f) for f in raw.get("secret_files", []) if isinstance(f, str)] if isinstance(raw.get("secret_files"), list) else []
    return {"deny": regexes("deny_commands"), "ask": regexes("ask_commands"), "files": files}


def find_secret(text: str) -> str | None:
    for kind, pat in SECRET_PATTERNS:
        if pat.search(text or ""):
            return kind
    return None


def is_secret_file(path: str, extra: list[str]) -> bool:
    if not path:
        return False
    p = str(PurePath(path)).replace("\\", "/")
    name = p.rsplit("/", 1)[-1].lower()
    full = p.lower()

    def hit(patterns: list[str]) -> bool:
        for pat in patterns:
            pat = pat.lower()
            if "/" in pat:
                if fnmatch.fnmatch(full, pat) or fnmatch.fnmatch("/" + full, pat):
                    return True
            elif fnmatch.fnmatch(name, pat):
                return True
        return False

    return hit(SECRET_FILES + extra) and not hit(SAFE_FILES)


def check_prompt(event: dict) -> dict:
    texts = [event.get("prompt") or ""]
    kind = find_secret("\n".join(texts))
    if kind:
        return {"continue": False,
                "user_message": f"Blocked: your message contains what looks like a {kind}. Remove it and send again. "
                                "If it was a real credential, rotate it, because it may already be in your clipboard "
                                "history or chat drafts. (secure-guardrails)"}
    return {"continue": True}


def check_read(event: dict) -> dict:
    path = event.get("file_path") or ""
    if is_secret_file(path, org_policy(event)["files"]):
        return {"permission": "deny",
                "user_message": f"secure-guardrails blocked reading {PurePath(path).name}: it is a secret file. "
                                "Use the matching .example file or describe the values instead."}
    if find_secret(event.get("content") or "") == "private key":
        return {"permission": "deny",
                "user_message": f"secure-guardrails blocked reading {PurePath(path).name}: it contains a private key."}
    return {"permission": "allow"}


def check_shell(event: dict) -> dict:
    cmd = event.get("command") or ""
    policy = org_policy(event)
    for reason, pat in DENY_COMMANDS + policy["deny"]:
        if pat.search(cmd):
            return {"permission": "deny",
                    "user_message": f"secure-guardrails blocked a command that {reason}.",
                    "agent_message": f"This command was blocked by policy because it {reason}. "
                                     "Do not retry it or work around the block; tell the user what you needed and why."}
    kind = find_secret(cmd)
    if kind:
        return {"permission": "deny",
                "user_message": f"secure-guardrails blocked a command containing a {kind}.",
                "agent_message": "Never put credentials on a command line. Read them from the environment or a secret manager."}
    for reason, pat in ASK_COMMANDS + policy["ask"]:
        if pat.search(cmd):
            return {"permission": "ask",
                    "user_message": f"This command {reason}. Approve only if you meant to.",
                    "agent_message": f"The user must approve this command because it {reason}."}
    return {"permission": "allow"}


def check_mcp(event: dict) -> dict:
    raw = event.get("tool_input")
    text = raw if isinstance(raw, str) else json.dumps(raw or {})
    kind = find_secret(text)
    if kind:
        return {"permission": "deny",
                "user_message": f"secure-guardrails blocked an MCP call ({event.get('tool_name', 'tool')}) "
                                f"whose arguments contain a {kind}.",
                "agent_message": "Never send credentials to an MCP tool. Remove the secret and use the server's own auth."}
    return {"permission": "allow"}


CHECKS = {"prompt": check_prompt, "read": check_read, "shell": check_shell, "mcp": check_mcp}
FALLBACK = {"prompt": {"continue": True}}


def main(argv: list[str]) -> int:
    check = argv[1] if len(argv) > 1 else ""
    if check == "--version":
        print(VERSION)
        return 0
    try:
        event = json.loads(sys.stdin.read() or "{}")
        result = CHECKS[check](event if isinstance(event, dict) else {})
    except Exception as exc:  # noqa: BLE001 - must always answer with valid JSON
        result = dict(FALLBACK.get(check, {"permission": "allow"}))
        print(f"secure-guardrails: internal error in '{check}': {type(exc).__name__}", file=sys.stderr)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
