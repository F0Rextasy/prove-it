---
name: prove-it
description: Verifies completion claims with executed evidence. Use whenever an agent or a human is about to write "done", "fixed", "all tests pass", "ready to ship", or file any completion/PR/session report. Requires every claim to carry a $ command + [exit N] block, then re-executes the cited commands with --run so a claim that no longer holds exits 1.
license: MIT
compatibility: Requires Python 3.8+. Runs in Claude Code, Codex, Cursor, and any Agent Skills compatible client.
metadata:
  author: F0Rextasy
  version: "1.0"
---

# prove-it

Agents report success faster than they verify it. A session report saying
"all tests pass and the bug is fixed" with no executed command behind it is
a guess wearing a status label. prove-it turns completion claims into
checkable evidence.

## The one rule

You may not write "done", "fixed", "passing", or "clean" unless the sentence
sits directly above an evidence block:

```markdown
All tests pass and the bug is fixed.

## Evidence

```console
$ python -m unittest discover -s tests
[exit 0] OK - 8 tests
```
```

The claim comes first, the command and its exit code sit under it. No exit
code, no claim.

## Protocol

1. **Collect the claim** - every result-bearing sentence (test outcomes, fix
   confirmations, build/deploy status, performance numbers). Hedge words
   (`should be`, `probably`, `looks clean`) are findings too.
2. **Execute every cited command** with `python scripts/prove.py <report>
   --run`. Replay compares the real exit code to the claimed `[exit N]`.
3. **Report back** - claim, the command you ran and its exit, and the exact
   block you observed.

## Rules at a glance

- Claim with no evidence block -> `unproven-claim` (fail).
- Evidence with no claim -> `orphan-evidence` (fail).
- Replayed exit differs from claimed exit -> `evidence-mismatch` (fail).
- `$ command` with no `[exit N]` or vice versa -> `bad-evidence` (fail).
- Hedge wording -> `weasel` (warn).

Full catalogue: [references/RULES.md](references/RULES.md).

## Escape hatch

One justified exception per line, with a reason:

```markdown
All tests pass # prove-it: allow -- runs green locally, CI blocked on T-9
```

Counted in every summary so the exceptions stay visible.

## Hard bans

Never write any of these without an evidence block directly below:

- "all tests pass" / "tests are green"
- "the bug is fixed" / "resolved"
- "ready to deploy" / "ship it" / "LGTM"
- "should work" (unverified)

And never cite an exit code you did not observe: a fabricated `[exit 0]`
passes static mode and fails `--run` immediately. Static mode checks
structure only. Replay is the authority.
