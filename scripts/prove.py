#!/usr/bin/env python3
"""prove-it -- no claim without executed evidence.

Scans an agent session report: every claim must sit directly above an
evidence block containing `$ command` and `[exit N]` lines. Floating claims
fail the gate. --run re-executes the cited commands and fails when reality
disagrees with the claimed exit code. Python stdlib only.

Exit codes: 0 proven, 1 claims fail (weasels only with --strict), 2 usage.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass

RULES = {
    # rule: (severity, suggestion)
    "unproven-claim": ("fail",
        "run the command for real and put `$ <cmd>` + `[exit N]` directly "
        "under the claim, or delete the claim"),
    "bad-evidence": ("fail",
        "an evidence block needs at least one `$ <command>` and one "
        "`[exit N]`, in matching counts"),
    "evidence-mismatch": ("fail",
        "the cited command does not exit as claimed -- re-run it and report "
        "the real exit code"),
    "weasel": ("warn",
        "state the fact or drop the hedge: 'should be fixed' is not a status"),
}

ESCAPE_RE = re.compile(r"#\s*prove-it\s*:\s*allow")
FENCE_RE = re.compile(r"^\s*```")
CMD_RE = re.compile(r"^\s*\$\s+(.+)$")
EXIT_RE = re.compile(r"^\s*\[exit\s+(\d+)\]")
CLAIM_RE = re.compile(
    r"(?i)\b(?:"
    r"all\s+tests?\s+pass|tests?\s+pass(?:es|ing)?|"
    r"fix(?:ed|es)|"
    r"works?\s+now|work(?:s|ing)\s+now|"
    r"no\s+(?:errors?|failures?|regressions?|exceptions?)|"
    r"everything\s+is\s+(?:clean|green|passing)|"
    r"clean|green|"
    r"ready\s+to\s+(?:deploy|ship|merge|release)|"
    r"should\s+(?:be\s+fixed|work|pass)|"
    r"probably\s+fine|hopefully|"
    r"\d+\s?%\s?(?:faster|less|fewer)|"
    r"bug[-\s]?free|secure"
    r")\b")
WEASEL_RE = re.compile(
    r"(?i)\b(?:should\s+(?:be\s+fixed|work|pass)|probably\s+fine|"
    r"hopefully|might\s+be\s+fixed)\b")

MAX_EXCERPT = 140


@dataclass
class Finding:
    file: str
    line: int
    rule: str
    text: str          # excerpt of the offending line or command
    message: str

    @property
    def severity(self) -> str:
        return RULES[self.rule][0]


def parse_blocks(lines):
    """Return [(claim_index, cmd_line_no, cmds, exits)] for evidence-shaped
    fenced blocks. A block is evidence-shaped when it contains a `$ cmd` or
    an `[exit N]` line; ordinary code snippets are ignored."""
    blocks = []
    in_fence = False
    fence_start = -1
    fence_cmds, fence_exits = [], []

    def close(_idx):
        if fence_cmds or fence_exits:
            # pair with the nearest non-empty line above the OPENING fence;
            # a fence line or block interior cannot serve as a claim
            claim = None
            for j in range(fence_start - 1, -1, -1):
                if not lines[j].strip():
                    continue
                if not FENCE_RE.match(lines[j]):
                    claim = j
                break
            blocks.append((claim, fence_start + 1, fence_cmds, fence_exits))

    for i, raw in enumerate(lines):
        if FENCE_RE.match(raw):
            if not in_fence:
                in_fence = True
                fence_start = i
                fence_cmds, fence_exits = [], []
            else:
                in_fence = False
                close(i)
            continue
        if in_fence:
            m = CMD_RE.match(raw)
            if m:
                fence_cmds.append(m.group(1))
            m = EXIT_RE.match(raw)
            if m:
                fence_exits.append(int(m.group(1)))
    if in_fence:
        close(len(lines))
    return blocks


def scan(path, text, run=False, timeout=120):
    lines = text.splitlines()
    blocks = parse_blocks(lines)
    proven = {claim for claim, _, _, _ in blocks if claim is not None}
    escaped = {i for i, raw in enumerate(lines) if ESCAPE_RE.search(raw)}
    stats = {"suppressed": 0, "claims": len(proven), "reports": [path]}
    findings = []

    def add(idx, rule, message, text_excerpt=None):
        if idx in escaped:
            stats["suppressed"] += 1
            return
        line_no = idx + 1
        excerpt = (text_excerpt or lines[idx]).strip()
        if len(excerpt) > MAX_EXCERPT:
            excerpt = excerpt[:MAX_EXCERPT] + "..."
        findings.append(Finding(path, line_no, rule, excerpt, message))

    in_fence = False
    for i, raw in enumerate(lines):
        if FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if i in proven and not WEASEL_RE.search(raw):
            continue
        if i not in proven and CLAIM_RE.search(raw):
            add(i, "unproven-claim",
                "claim with no `$ command` + `[exit N]` block under it")
        if WEASEL_RE.search(raw):
            add(i, "weasel", "hedge wording instead of a stated result")

    for claim, line_no, cmds, exits in blocks:
        idx = line_no - 1
        if not cmds or not exits or len(cmds) != len(exits):
            escaped_now = bool(ESCAPE_RE.search(lines[idx])) if idx < len(lines) else False
            if escaped_now:
                stats["suppressed"] += 1
            else:
                findings.append(Finding(
                    path, line_no, "bad-evidence",
                    "%d command(s) vs %d exit marker(s)"
                    % (len(cmds), len(exits)),
                    "evidence block is incomplete"))
            continue
        if not run:
            continue
        for cmd, claimed in zip(cmds, exits):
            try:
                proc = subprocess.run(
                    cmd, shell=True, timeout=timeout,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                actual = proc.returncode
            except subprocess.TimeoutExpired:
                actual = -1
            if actual != claimed:
                findings.append(Finding(
                    path, line_no, "evidence-mismatch", cmd,
                    "claimed exit %d, command exited %d%s"
                    % (claimed, actual,
                       " (timeout)" if actual == -1 else "")))

    findings.sort(key=lambda f: f.line)
    return findings, stats


def render_text(findings, stats, strict, color):
    red, yellow, bold, reset = "", "", "", ""
    if color:
        red, yellow, bold, reset = "\033[31m", "\033[33m", "\033[1m", "\033[0m"

    counts = {"fail": 0, "warn": 0}
    for f in findings:
        counts[f.severity] += 1

    out = []
    if findings:
        out.append(bold + stats["reports"][0] + reset)
        for f in findings:
            sev = "FAIL" if f.severity == "fail" else "WARN"
            sev_col = red if sev == "FAIL" else yellow
            detail = ("%s -- %s" % (f.text, f.message)) if f.text else f.message
            out.append("  L%-4d %s%-5s%s %-18s %s"
                       % (f.line, sev_col, sev, reset, f.rule, detail))
        out.append("")

    nf = "%d failure%s" % (counts["fail"], "" if counts["fail"] == 1 else "s")
    nw = "%d warning%s" % (counts["warn"], "" if counts["warn"] == 1 else "s")
    exempt = " (%d exempt by 'prove-it: allow')" % stats["suppressed"]

    if not findings:
        out.append("prove-it: clean -- %d claim%s proven across 1 report, "
                   "0 findings%s"
                   % (stats["claims"], "" if stats["claims"] == 1 else "s",
                      exempt))
        return "\n".join(out)

    out.append("prove-it: %s, %s across 1 report%s" % (nf, nw, exempt))
    if counts["fail"] > 0 or (strict and counts["warn"] > 0):
        out.append(red + "prove-it: attach executed evidence -- or justify "
                     "one claim with:  # prove-it: allow -- <reason>" + reset)
    else:
        out.append("prove-it: warnings pass by default; use --strict to "
                   "fail on them too")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="prove-it",
        description="Fail agent reports whose claims lack executed evidence. "
                    "Exit 1 when a claim is unproven, the evidence is "
                    "malformed, or (--run) reality disagrees.")
    ap.add_argument("report", nargs="?", metavar="REPORT",
                    help="report file to check; use - or omit when piping")
    ap.add_argument("--run", action="store_true",
                    help="re-execute every cited command and compare exits")
    ap.add_argument("--timeout", type=int, default=120,
                    help="per-command timeout seconds for --run (default 120)")
    ap.add_argument("--strict", action="store_true",
                    help="also fail on warnings")
    ap.add_argument("--format", choices=("text", "json"), default="text")
    ap.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    args = ap.parse_args(argv)

    if args.report in (None, "-"):
        if args.report is None and sys.stdin.isatty():
            ap.error("report file required (or pipe the report to stdin)")
        text = sys.stdin.read()
        path = "<stdin>"
    else:
        path = args.report
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError as exc:
            ap.error("cannot read report: %s" % exc)

    findings, stats = scan(path, text, run=args.run, timeout=args.timeout)
    counts = {"fail": 0, "warn": 0}
    for f in findings:
        counts[f.severity] += 1
    failing = counts["fail"] > 0 or (args.strict and counts["warn"] > 0)

    if args.format == "json":
        payload = {
            "ok": not failing,
            "counts": dict(counts, suppressed=stats["suppressed"]),
            "scanned": {"claims_proven": stats["claims"],
                        "reports": stats["reports"]},
            "findings": [
                {"file": f.file, "line": f.line, "rule": f.rule,
                 "severity": f.severity, "excerpt": f.text,
                 "message": f.message, "suggestion": RULES[f.rule][1]}
                for f in findings
            ],
        }
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        color = (not args.no_color and sys.stdout.isatty()
                 and not os.environ.get("NO_COLOR"))
        print(render_text(findings, stats, args.strict, color))

    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
