"""SARIF extraction from Cursor CLI JSON output and from plain text."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import extract_sarif  # noqa: E402

LOG = {"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "secure-code-review", "version": "1.0.0"}},
       "results": [{"ruleId": "S11-injection", "level": "error", "message": {"text": "SQL injection"},
                    "locations": [{"physicalLocation": {"artifactLocation": {"uri": "app.py"}, "region": {"startLine": 13}}}],
                    "properties": {"severity": "Critical"}}]}]}
ANSWER = "### Verdict\n**BLOCK**\n\n```sarif\n" + json.dumps(LOG, indent=2) + "\n```\n"


def test_from_cursor_json_result_field():
    out = json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": ANSWER})
    log = extract_sarif.extract(out)
    assert log["runs"][0]["results"][0]["ruleId"] == "S11-injection"
    assert extract_sarif.problems(log) == []


def test_from_plain_text():
    assert extract_sarif.extract(ANSWER)["version"] == "2.1.0"


def test_rejects_missing_block():
    with pytest.raises(ValueError):
        extract_sarif.extract("APPROVE, no findings")


def test_flags_result_without_location():
    bad = json.loads(json.dumps(LOG))
    del bad["runs"][0]["results"][0]["locations"]
    assert extract_sarif.problems(bad)
