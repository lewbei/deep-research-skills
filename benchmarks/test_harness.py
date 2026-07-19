"""Regression tests for the benchmark harness."""
import sys
import tempfile
from pathlib import Path

# Ensure package root is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from benchmarks.action_parser import parse_action
from benchmarks.runner import score_math
from benchmarks.drs import DERSAgent


def test_parse_action_clean():
    response = (
        "I will search now.\n"
        "```json\n"
        '{"tool": "Search", "arguments": {"query": "test"}}\n'
        "```"
    )
    t, a = parse_action(response)
    assert t == "Search" and a == {"query": "test"}, f"FAIL: {t} {a}"
    print("Test 1 (clean JSON block): PASS")


def test_parse_action_braces_in_content():
    """Braces and links inside report content must not truncate the JSON."""
    import json as _json
    content = '## Title\nSome {nested} content with [links](url) and {"inner": "json"}'
    payload = {"tool": "Write", "arguments": {"path": "final-report.md", "content": content}}
    response = (
        "Writing report.\n"
        "```json\n"
        + _json.dumps(payload)
        + "\n```"
    )
    t, a = parse_action(response)
    assert t == "Write" and "content" in a, f"FAIL: {t} {a}"
    print("Test 2 (braces in report content): PASS")


def test_parse_action_old_format_rejected():
    """Old Action: Search[query] format must be rejected."""
    t, a = parse_action("Action: Search[query]")
    assert t is None, f"FAIL: {t}"
    print("Test 3 (old Action[] format rejected): PASS")


def test_parse_action_last_block_wins():
    response = (
        "First attempt:\n"
        "```json\n"
        '{"tool": "Search", "arguments": {"query": "first"}}\n'
        "```\n"
        "Actually, second:\n"
        "```json\n"
        '{"tool": "Search", "arguments": {"query": "second"}}\n'
        "```"
    )
    t, a = parse_action(response)
    assert a["query"] == "second", f"FAIL: {a}"
    print("Test 4 (last block wins): PASS")


def test_score_math_judge_error_excluded():
    results = [
        {"weight": 10, "verdict": "MET",         "axis": "f"},
        {"weight": 10, "verdict": "JUDGE_ERROR",  "axis": "f"},
        {"weight": 10, "verdict": "UNMET",        "axis": "f"},
    ]
    s = score_math(results)
    assert s["judge_error_count"] == 1, s
    assert s["scoreable_criteria"] == 2, s
    # max_possible = 20 (two scoreable positive), raw = 10 (one MET)
    assert s["normalized_score"] == 50.0, s
    # 1 correct out of 2 scoreable
    assert s["pass_rate"] == 50.0, s
    print("Test 5 (JUDGE_ERROR excluded from score): PASS")


def test_path_sandbox():
    agent = DERSAgent()
    ws = Path(tempfile.mkdtemp())

    # Non-existent file inside workspace → not found, not an escape error
    result = agent._safe_read(ws, "some_file.md")
    assert "not found" in result, f"FAIL: {result}"

    # Path traversal attempt
    result2 = agent._safe_read(ws, "../../../etc/passwd")
    assert "escapes" in result2, f"FAIL: {result2}"

    # Absolute path attempt
    result3 = agent._safe_read(ws, "/etc/passwd")
    assert "escapes" in result3, f"FAIL: {result3}"

    print("Test 6 (path sandbox .relative_to()): PASS")


def test_parse_action_invalid_json_skipped():
    """Malformed JSON block must be skipped; valid block after it is returned."""
    response = (
        "Bad block:\n"
        "```json\n"
        "{invalid json here\n"
        "```\n"
        "Good block:\n"
        "```json\n"
        '{"tool": "CLI", "arguments": {"args": "status"}}\n'
        "```"
    )
    t, a = parse_action(response)
    assert t == "CLI" and a == {"args": "status"}, f"FAIL: {t} {a}"
    print("Test 7 (invalid JSON block skipped, valid block parsed): PASS")


if __name__ == "__main__":
    test_parse_action_clean()
    test_parse_action_braces_in_content()
    test_parse_action_old_format_rejected()
    test_parse_action_last_block_wins()
    test_score_math_judge_error_excluded()
    test_path_sandbox()
    test_parse_action_invalid_json_skipped()
    print("\nAll 7 regression tests PASSED.")
