#!/usr/bin/env python3
"""Extract and validate the SARIF log that secure-code-review prints when asked.

  agent -p "review the changes against main and output SARIF" --output-format json --trust > review.json
  python3 scripts/extract_sarif.py review.json -o review.sarif     # then upload to code scanning

Accepts the Cursor CLI's JSON output (its "result" field) or plain text.
Exit 1 if no valid SARIF 2.1.0 block is found. Stdlib only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BLOCK = re.compile(r"```(?:sarif|json)\s*\n(.*?)\n```", re.S)
LEVELS = {"error", "warning", "note", "none"}


def extract(text: str) -> dict:
    try:
        outer = json.loads(text)
        if isinstance(outer, dict) and isinstance(outer.get("result"), str):
            text = outer["result"]
    except ValueError:
        pass
    for m in BLOCK.finditer(text):
        try:
            log = json.loads(m.group(1))
        except ValueError:
            continue
        if isinstance(log, dict) and log.get("version") == "2.1.0" and log.get("runs"):
            return log
    raise ValueError("no SARIF 2.1.0 block found")


def problems(log: dict) -> list[str]:
    out = []
    for i, run in enumerate(log.get("runs", [])):
        if not run.get("tool", {}).get("driver", {}).get("name"):
            out.append(f"runs[{i}].tool.driver.name missing")
        for j, r in enumerate(run.get("results", [])):
            where = f"runs[{i}].results[{j}]"
            if not r.get("ruleId"):
                out.append(f"{where}.ruleId missing")
            if r.get("level") not in LEVELS:
                out.append(f"{where}.level invalid: {r.get('level')!r}")
            if not (r.get("message") or {}).get("text"):
                out.append(f"{where}.message.text missing")
            loc = ((r.get("locations") or [{}])[0].get("physicalLocation") or {})
            if not (loc.get("artifactLocation") or {}).get("uri") or not isinstance((loc.get("region") or {}).get("startLine"), int):
                out.append(f"{where} needs physicalLocation.artifactLocation.uri and region.startLine")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("input", help="Claude Code JSON output or text; '-' for stdin")
    ap.add_argument("-o", "--output", help="write the SARIF log here")
    a = ap.parse_args()
    text = sys.stdin.read() if a.input == "-" else Path(a.input).read_text(encoding="utf-8")
    try:
        log = extract(text)
    except ValueError as exc:
        print(f"FAIL  {exc}", file=sys.stderr)
        return 1
    log.setdefault("$schema", "https://json.schemastore.org/sarif-2.1.0.json")
    errs = problems(log)
    for e in errs:
        print(f"FAIL  {e}", file=sys.stderr)
    if errs:
        return 1
    if a.output:
        Path(a.output).write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    n = sum(len(r.get("results", [])) for r in log["runs"])
    print(f"OK    SARIF 2.1.0 with {n} result(s){' → ' + a.output if a.output else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
