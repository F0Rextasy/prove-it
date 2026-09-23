# Rule catalogue

`scripts/prove.py` scans an agent session report. Every rule answers one
question: *is this sentence backed by a command that ran, and does replaying
that command still produce the claimed exit?*

Two severities:

- **fail** - a claim is not proven. Fails the gate (exit 1).
- **warn** - a claim is weakened or unverifiable by replay. Fails only
  with `--strict`.

## Fail rules

| Rule | Fires when | Example |
| --- | --- | --- |
| `unproven-claim` | a claim line has no evidence block below it | "All tests pass" floating alone |
| `orphan-evidence` | an evidence block has no claim line above it | a `$ command` block under a heading gap |
| `evidence-mismatch` | replayed exit differs from claimed `[exit N]` | claimed `[exit 0]`, command exited 3 (`--run` only) |
| `bad-evidence` | a `$ command` with no `[exit N]`, an `[exit N]` with no command, or unequal counts | `[exit 0] ok` with no command |

## Warn rules

| Rule | Fires when | Why it is not fatal |
| --- | --- | --- |
| `weasel` | hedge wording on a claim line | the claim may be true - it is just not stated |
| `unverified-exit` | `[exit N]` where N is outside 0-255 | a human wrote something odd |

## Pairing

A **claim line** is any non-empty line outside a fenced block that (a)
contains a claim marker (`tests pass`, `fixed`, `resolved`, `clean`,
`done`, `green`, `passing`, `ready`, `should`, `probably`, `looks`,
`hopefully`, `fast`, `improvement`, `regression`) or (b) reads like a result
("Bug fixed"). An **evidence block** is a fenced block with `$ cmd` lines
paired with `[exit N]` lines. For each block the scanner walks back from
the opening fence over blanks to find the claim - the fence interior cannot
serve as its own claim.

## Replay

`--run` re-executes every `$ command` (shell, unchanged cwd, 120s timeout
each) and compares the real exit code to the claimed one. Timeouts count as
a mismatch. Fabricated outputs pass static mode and fail here - replay is
the authority.

## Escape hatch

`# prove-it: allow -- <reason>` on a claim line suppresses that line's
findings and counts it as exempt. Imported from all lines of the report;
audit-visible in every summary.

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | clean, or only warnings without `--strict` |
| `1` | at least one fail (or any warning with `--strict`) |
| `2` | usage error - no report, unreadable file, bad flags |
