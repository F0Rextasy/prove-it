---
name: prove-it
description: Verifies completion claims with executed evidence. Use whenever an agent or a human is about to write "done", "fixed", "all tests pass", "ready to ship", or file any completion/PR/session report. Requires every claim to carry a $ command + [exit N] block, then re-executes the commands with scripts/prove.py --run so a claim that disagrees with reality fails the gate.
license: MIT
compatibility: Requires Python 3.8+. Runs in Claude Code, Codex, Cursor, and any Agent Skills compatible client.
metadata:
  author: F0Rextasy
  version: "1.0"
---

# prove-it

A claim is a hypothesis until a process exits. "All tests pass" is not a
status — it is a prediction that the test command exits 0 right now.

## The one rule

You may not state a result you have not executed in this session. Every
claim ships with its command and real exit code, and the gate re-runs them:

```bash
python scripts/prove.py report.md --run
```

Exit 0 means the claims survived a replay. Exit 1 means a claim floats,
the evidence is malformed, or reality disagreed with the written exit code.
Never report success over a non-zero exit.

See [references/RULES.md](references/RULES.md) for the rules and the exact
report format.

## Protocol

### 1. Write the claims first

List every result you intend to assert: tests, lint, types, the reproduced
bug, the benchmark. If you cannot name the command that proves a claim,
you have not done the work — go do it.

### 2. Execute, do not recall

Run each command now, in this session, and record the actual exit code.
Memory of a previous run is not evidence: HEAD may have moved, the
environment may differ, the fixture may have rotted.

### 3. Format evidence exactly like this

```markdown
- `python -m pytest -q` exits 0
  ```
  $ python -m pytest -q
  [exit 0] 8 passed in 1.3s
  ```
```

One claim line, then its fenced block: `$ command` lines and `[exit N]`
lines in matching counts. The claim line sits directly above the block —
that pairing is what the checker validates.

### 4. Gate it

```bash
python scripts/prove.py report.md --run
```

`--run` re-executes every cited command. A mismatch is a failure, not a
disagreement to negotiate.

### 5. Hard bans

| Tempting move | Why it fails the gate | Do this instead |
| --- | --- | --- |
| "should be fixed now" | a hedge is not a result | state the exit code, or say it is unverified |
| claim from memory ("tests passed earlier") | evidence older than HEAD | re-run it |
| `[exit 0]` written by hand | `--run` replays and exposes it | paste the real run |
| claim with no command | unfalsifiable | name the command or drop the claim |
| fabricating output under the command | structure passes, replay fails | run it |

An intentional exception is justified on the claim line itself:

```markdown
- benchmark number pending  # prove-it: allow -- rerun after hardware swap, BENCH-14
```

### 6. Report back

1. **Claims** — each one as: claim → command → exit code.
2. **Evidence** — the fenced blocks, in the report.
3. **Gate** — `prove.py report.md --run` and its exit 0.

Never write "done" without those three lines.
