"""Contract tests for prove-it. Run: python -m unittest discover -s tests -v

Every test drives the real CLI against fixture reports and asserts the exit
code and reported findings a consumer would observe -- nothing internal.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "prove.py")
EXAMPLES = os.path.join(ROOT, "examples")


def run_cli(*args, stdin_text=None):
    proc = subprocess.run(
        [sys.executable, SCRIPT, *args], input=stdin_text,
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return proc.returncode, proc.stdout, proc.stderr


def fixture(name):
    return [os.path.join(EXAMPLES, name), "--no-color"]


class ProveContract(unittest.TestCase):
    def test_proven_report_passes(self):
        code, out, _ = run_cli(*fixture("proven.md"))
        self.assertEqual(code, 0, out)
        self.assertIn("clean", out)
        self.assertIn("2 claims proven", out)

    def test_unproven_claims_fail_with_rules(self):
        code, out, _ = run_cli(*fixture("unproven.md"))
        self.assertEqual(code, 1, out)
        self.assertIn("unproven-claim", out)
        self.assertIn("weasel", out)
        self.assertIn("3 failures, 1 warning", out)

    def test_run_detects_evidence_mismatch(self):
        code, out, _ = run_cli(*fixture("mismatch.md"))
        self.assertEqual(code, 0, out)          # structure is fine
        self.assertIn("1 claim proven", out)
        code, out, _ = run_cli(*fixture("mismatch.md"), "--run")
        self.assertEqual(code, 1, out)          # replay disagrees
        self.assertIn("evidence-mismatch", out)
        self.assertIn("claimed exit 0, command exited 3", out)

    def test_run_confirms_proven_evidence(self):
        code, out, _ = run_cli(*fixture("proven.md"), "--run")
        self.assertEqual(code, 0, out)
        self.assertIn("clean", out)

    def test_json_reports_structure(self):
        code, out, _ = run_cli(*fixture("unproven.md"), "--format", "json")
        self.assertEqual(code, 1)
        data = json.loads(out)
        self.assertFalse(data["ok"])
        self.assertEqual(data["counts"], {"fail": 3, "warn": 1, "suppressed": 0})
        self.assertEqual(data["scanned"]["claims_proven"], 1)
        self.assertEqual([f["line"] for f in data["findings"]][:3], [3, 5, 7])
        self.assertEqual(data["findings"][0]["excerpt"],
                         "All tests pass and the bug is fixed.")
        for f in data["findings"]:
            self.assertIn("suggestion", f)

    def test_escape_hatch_suppresses_and_counts(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("All tests pass  # prove-it: allow -- flaky suite, T-9\n")
            path = fh.name
        try:
            code, out, _ = run_cli(path, "--no-color")
        finally:
            os.unlink(path)
        self.assertEqual(code, 0, out)
        self.assertIn("clean", out)
        self.assertIn("1 exempt by 'prove-it: allow'", out)

    def test_prose_without_claims_is_clean(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False,
                                         encoding="utf-8") as fh:
            fh.write("# Notes\n\nRefactored the parser and updated the callers.\n")
            path = fh.name
        try:
            code, out, _ = run_cli(path, "--no-color")
        finally:
            os.unlink(path)
        self.assertEqual(code, 0, out)
        self.assertIn("0 claims proven", out)

    def test_missing_report_is_usage_error(self):
        code, _, _ = run_cli(os.path.join(EXAMPLES, "nope.md"))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
