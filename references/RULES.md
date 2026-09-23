# Rule catalogue

`scripts/prove.py` scans an agent session report. Every rule answers one
question: *is this sentence backed by a command that ran, and does replaying
that command still produce the claimed exit?*

Two severities:

- **fail** — a claim is not proven. Fails the gate (exit 1).
- **warn** — hedge wording; may be deliberate. Passes by default, fails with `--strict`.

## fail

| Rule | Catches | Example that fails |
| --- | --- | --- |
| `unproven-claim` | result sentence with no evidence block under it | `All tests pass.` standing alone in a paragraph |
| `bad-evidence` | block missing `$ cmd` or `[exit N]`, or counts differ | one command, two exit markers |
| `evidence-mismatch` (`--run`) | replay exits differently than claimed | `[exit 0]` over a command that now exits 3 |

## warn

| Rule | Catches | Example |
| --- | --- | --- |
| `weasel` | hedge instead of a result | `This should be fixed now.` |

## The report format

An evidence block is a fenced block containing `$ command` and/or
`[exit N]` lines. A claim is **proven** when the nearest non-empty line
above the block's opening fence is that claim line:

````markdown
- `python -m pytest -q` exits 0
  ```
  $ python -m pytest -q
  [exit 0] 8 passed in 1.3s
  ````

Ordinary code snippets (no `$` / `[exit N]` lines) are not evidence and
never pair with anything.

## What counts as a claim

Any line outside a code fence matching: test results (`all tests pass`),
fix assertions (`fixed`, `works now`), absence claims (`no errors`,
`no regressions`), cleanliness (`everything is clean`, `clean`, `green`),
ship claims (`ready to deploy/ship/merge`), hedges (`should be fixed`,
`should work`, `probably fine`), improvements (`20% faster`), and absolutes
(`bug-free`, `secure`).

A claim line paired with a block counts in `claims_proven`. The same line
still gets a `weasel` warning when it hedges.

## Replay is the authority

Static mode validates structure only: pairs, counts, formats. It cannot
tell a real transcript from a creative one. `--run` is what makes the gate
a gate — it re-executes every cited command (per-command timeout, default
120s) and fails on any exit-code disagreement. Run `--run` in CI, where the
environment matches the claim.

## The escape hatch

A claim you intentionally cannot prove yet justifies itself on the line:

```markdown
- benchmark pending  # prove-it: allow -- machine reimage in progress, BENCH-7
```

The comment is stripped before matching (the rule still saw the claim) and
the finding is counted as `exempt`, never silently dropped.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | every claim proven (or only warnings, without `--strict`) |
| `1` | unproven claim, malformed evidence, or replay mismatch — do not report done |
| `2` | usage error — unreadable report, no report and no piped stdin |
