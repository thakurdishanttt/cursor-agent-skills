#!/usr/bin/env python3
"""Run the skill eval suite in real headless Cursor Agent sessions.

  python3 scripts/run_evals.py                          # all cases, Cursor's default model
  python3 scripts/run_evals.py --case review-finds-planted-vulns --repeat 3
  python3 scripts/run_evals.py --model sonnet-4.5 --jobs 6 --json evals/last-run.json
  python3 scripts/run_evals.py --dry-run                # prepare fixtures, print commands, spend nothing

For each case: copy the fixture to a temp folder, commit `base/`, apply
`change/` as the working-tree diff, write a `.cursor/cli.json` that allows
only the tools the case needs, then run the Cursor CLI headless with the
`secure-coding` plugin loaded from this repo (`--plugin-dir`), so the real
plugin packaging is what gets tested. Checks:
  * the expected skill was loaded (or none, for negative cases)
  * every `must` pattern appears in the final answer, no `must_not` does
  * the working tree is unchanged when `unchanged` is set (read-only skills)
  * valid SARIF when the case asks for it

Needs the Cursor CLI (`agent`, https://cursor.com/install) and CURSOR_API_KEY.
Prints a Markdown table; exits non-zero unless every run passes. Stdlib only.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"
PLUGIN = ROOT / "plugins" / "secure-coding"
SKILLS = sorted(p.name for p in (PLUGIN / "skills").iterdir() if (p / "SKILL.md").is_file())
JUNK = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")


def cli() -> str | None:
    return shutil.which("agent") or shutil.which("cursor-agent")


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True).stdout


def permissions(tools: list[str]) -> dict:
    """Translate a case's tool list into Cursor CLI permission tokens."""
    allow, deny = ["Read(**)"], ["Read(.env*)", "Read(**/*.pem)", "Read(**/*.key)"]
    for t in tools:
        if t.startswith("Bash(git"):
            allow.append("Shell(git)")
        elif t in ("Edit", "Write"):
            allow.append("Write(**)")
        elif t in ("WebSearch", "WebFetch"):
            allow.append("WebFetch(*)")
    return {"permissions": {"allow": sorted(set(allow)), "deny": deny}}


def prepare(case: dict, work: Path) -> None:
    fx = EVALS / "fixtures" / case["fixture"]
    shutil.copytree(fx / "base", work, dirs_exist_ok=True, ignore=JUNK)
    git(work, "init", "-q", "-b", "main")
    git(work, "-c", "user.name=eval", "-c", "user.email=eval@example.invalid", "add", "-A")
    git(work, "-c", "user.name=eval", "-c", "user.email=eval@example.invalid", "commit", "-qm", "base")
    if (fx / "change").is_dir():
        shutil.copytree(fx / "change", work, dirs_exist_ok=True, ignore=JUNK)
        git(work, "add", "-N", ".")
    (work / ".cursor").mkdir(exist_ok=True)
    (work / ".cursor" / "cli.json").write_text(json.dumps(permissions(case["tools"]), indent=2), encoding="utf-8")


def command(case: dict, work: Path, model: str | None) -> list[str]:
    cmd = [cli() or "agent", "-p", case["prompt"], "--output-format", "stream-json",
           "--trust", "--workspace", str(work), "--plugin-dir", str(PLUGIN)]
    if model:
        cmd += ["--model", model]
    return cmd


def skills_in(event: dict) -> set[str]:
    """Skills a tool call loaded: a read of skills/<name>/SKILL.md, or a skill-type tool naming one."""
    blob = json.dumps(event)
    found = set(re.findall(r"skills/([a-z0-9-]+)/SKILL\.md", blob))
    if any("skill" in k.lower() for k in (event.get("tool_call") or {})):
        found |= {s for s in SKILLS if re.search(rf"\b{re.escape(s)}\b", blob)}
    return found & set(SKILLS)


def run_case(case: dict, model: str | None, dry: bool) -> dict:
    t0 = time.monotonic()
    with tempfile.TemporaryDirectory(prefix=f"eval-{case['id']}-") as d:
        work = Path(d)
        prepare(case, work)
        cmd = command(case, work, model)
        if dry:
            return {"id": case["id"], "pass": True, "fails": [], "skills": [], "seconds": 0, "tool_calls": 0,
                    "answer": "", "command": " ".join(cmd[:2] + ["<prompt>"] + cmd[3:]),
                    "cli_json": (work / ".cursor" / "cli.json").read_text()}
        scope = ["--", ".", ":!.cursor"]
        before = git(work, "status", "--porcelain", "--untracked-files=all", *scope)
        try:
            proc = subprocess.run(cmd, cwd=work, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                                  timeout=case.get("timeout_s", 420))
            out, err = proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as exc:
            out = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            err = "timeout"
        used: list[str] = []
        texts: list[str] = []
        result_text, calls = "", 0
        for line in out.splitlines():
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            kind = ev.get("type")
            if kind == "tool_call" and ev.get("subtype") == "started":
                calls += 1
                used += [s for s in sorted(skills_in(ev)) if s not in used]
            elif kind == "assistant":
                for block in (ev.get("message") or {}).get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "text":
                        texts.append(block.get("text") or "")
            elif kind == "result":
                result_text = ev.get("result") or ""
        answer = result_text or "".join(texts)
        after = git(work, "status", "--porcelain", "--untracked-files=all", *scope)

    fails: list[str] = []
    want = case["skill"]
    if want and want not in used:
        fails.append(f"skill '{want}' not used (used: {used or 'none'})")
    if not want and used:
        fails.append(f"no skill expected, used {used}")
    if not answer:
        fails.append("no final answer: " + (err or "").strip()[-200:])
    for pat in case.get("must", []):
        if not re.search(pat, answer, re.I | re.M):
            fails.append(f"missing /{pat}/")
    for pat in case.get("must_not", []):
        if re.search(pat, answer, re.I | re.M):
            fails.append(f"forbidden /{pat}/ present")
    if case.get("unchanged") and before != after:
        fails.append("working tree was modified")
    if "sarif_min_results" in case:
        sys.path.insert(0, str(ROOT / "scripts"))
        import extract_sarif  # noqa: E402
        try:
            log = extract_sarif.extract(answer)
            errs = extract_sarif.problems(log)
            n = sum(len(r.get("results", [])) for r in log["runs"])
            if errs:
                fails.append("invalid SARIF: " + "; ".join(errs[:3]))
            if n < case["sarif_min_results"]:
                fails.append(f"SARIF has {n} result(s), expected >= {case['sarif_min_results']}")
        except ValueError as exc:
            fails.append(str(exc))
    return {"id": case["id"], "pass": not fails, "fails": fails, "skills": used,
            "seconds": round(time.monotonic() - t0, 1), "tool_calls": calls, "answer": answer}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", action="append", help="run only these case ids")
    ap.add_argument("--model", default=os.environ.get("EVAL_MODEL") or None, help="Cursor model id (default: account default)")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--json", help="write full results here")
    ap.add_argument("--dry-run", action="store_true", help="prepare every case and print the command; no API calls")
    a = ap.parse_args()
    if not a.dry_run:
        if not cli():
            print("Cursor CLI not found: curl https://cursor.com/install -fsS | bash", file=sys.stderr)
            return 2
        if not os.environ.get("CURSOR_API_KEY"):
            print("CURSOR_API_KEY is not set", file=sys.stderr)
            return 2
    cases = json.loads((EVALS / "cases.json").read_text(encoding="utf-8"))["cases"]
    if a.case:
        cases = [c for c in cases if c["id"] in set(a.case)]
    runs = [c for c in cases for _ in range(a.repeat)]
    t0 = time.monotonic()
    with cf.ThreadPoolExecutor(max_workers=a.jobs) as pool:
        results = list(pool.map(lambda c: run_case(c, a.model, a.dry_run), runs))
    wall = time.monotonic() - t0
    if a.dry_run:
        for r in results:
            print(f"{r['id']}: {r['command']}\n  cli.json: {json.dumps(json.loads(r['cli_json']))}")
        print(f"\nprepared {len(results)} case(s); nothing was sent")
        return 0
    passed = sum(r["pass"] for r in results)
    print("| Case | Result | Skill used | Time (s) | Tool calls |\n|---|---|---|---|---|")
    for r in results:
        print(f"| {r['id']} | {'PASS' if r['pass'] else 'FAIL'} | {', '.join(r['skills']) or '—'} | "
              f"{r['seconds']} | {r['tool_calls']} |")
    print(f"\n**{passed}/{len(results)} passed** · Cursor model {a.model or 'default'} · wall time {wall:.0f}s "
          f"({a.jobs} parallel)")
    for r in results:
        if not r["pass"]:
            print(f"\nFAIL {r['id']}:\n  - " + "\n  - ".join(r["fails"]) + f"\n  answer: {r['answer'][:300]!r}")
    if a.json:
        Path(a.json).write_text(json.dumps({"model": a.model or "default", "results": results}, indent=2) + "\n",
                                encoding="utf-8")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
