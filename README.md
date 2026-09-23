# prove-it

**No claim without executed evidence.** `prove-it` scans an agent's session
report: every result sentence (`all tests pass`, `fixed`, `ready to ship`,
`should be fixed`) must sit directly above an evidence block —
`$ command` + `[exit N]` — and `--run` replays the cited commands, failing
the gate when reality disagrees with the exit code written on the page.

![license](https://img.shields.io/badge/license-MIT-green)
![python](https://img.shields.io/badge/python-3.8%2B-blue)
![tests](https://img.shields.io/badge/tests-8%20passing-brightgreen)
![exit codes](https://img.shields.io/badge/exit%20codes-0%20proven%20%7C%201%20unproven%20%7C%202%20usage-orange)

## The problem

The most common failure in AI-assisted development is not a wrong fix — it
is a **wrong report**. The agent says "all tests pass", the human merges,
and the truth catches up in production. Live complaint data ranks *"review
passes clean when the environment is misconfigured"* as the #1 pain point;
every week, reports claiming done land on PRs whose tests nobody re-ran.

Claims are cheap because verifying them is manual. `prove-it` makes the
claim itself the artifact that must survive execution:

> A claim is a hypothesis until a process exits.

## How it works

`prove-it` parses the report's fenced blocks and applies four rules:

| Rule | Severity | What it does |
| --- | --- | --- |
| `unproven-claim` | fail | result sentence with no `$ cmd` + `[exit N]` block under it |
| `bad-evidence` | fail | block missing a command or exit marker, counts differ |
| `evidence-mismatch` | fail | (`--run`) replayed command exits differently than claimed |
| `weasel` | warn | hedge wording (`should be fixed`, `probably fine`) |

A claim is **proven** when the nearest non-empty line above its evidence
block is that claim. Ordinary code snippets (no `$`/`[exit N]` lines) are
never evidence. Static mode checks structure; `--run` is the authority — it
re-executes every cited command (default 120s timeout) and compares exits.

Full catalogue and the exact report format: [references/RULES.md](references/RULES.md).

## Install

```bash
git clone https://github.com/F0Rextasy/prove-it.git
# requires python 3.8+, nothing else
alias prove-it='python /path/to/prove-it/scripts/prove.py'
```

### As an Agent Skill

`prove-it` ships a [SKILL.md](SKILL.md) that teaches an AI coding agent to
list claims, execute each one, write the evidence blocks, and gate its own
report:

```bash
# one command — Claude Code, Cursor, Codex, and 75+ agents
npx skills add F0Rextasy/prove-it
```

Manual equivalent:

```bash
cp -r prove-it ~/.claude/skills/prove-it
```

## Usage

```bash
prove-it report.md            # structure: pairs, counts, hedges
prove-it report.md --run      # replay every command, compare exit codes
cat report.md | prove-it -    # pipe a report from stdin
prove-it report.md --strict   # warnings fail too
prove-it report.md --format json
```

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | every claim proven (or warnings only, without `--strict`) |
| `1` | unproven claim, malformed evidence, or replay mismatch |
| `2` | usage error (unreadable report, no report and no stdin) |

### CI (GitHub Actions)

```yaml
- name: replay the session report
  run: python scripts/prove.py report.md --run
```

## Evidence

A report with floating claims — real output:

```
prove-it/examples/unproven.md
  L3    FAIL  unproven-claim     All tests pass and the bug is fixed. -- claim with no `$ command` + `[exit N]` block under it
  L5    FAIL  unproven-claim     Everything is clean after the lint run. -- claim with no `$ command` + `[exit N]` block under it
  L7    FAIL  unproven-claim     This should be fixed now. -- claim with no `$ command` + `[exit N]` block under it
  L7    WARN  weasel             This should be fixed now. -- hedge wording instead of a stated result

prove-it: 3 failures, 1 warning across 1 report (0 exempt by 'prove-it: allow')
prove-it: attach executed evidence -- or justify one claim with:  # prove-it: allow -- <reason>
$ echo $?
1
```

Hand-written exit code, replay disagrees:

```
$ python scripts/prove.py examples/mismatch.md --run
prove-it/examples/mismatch.md
  L4    FAIL  evidence-mismatch  python -c "import sys; sys.exit(3)" -- claimed exit 0, command exited 3

prove-it: 1 failure, 0 warnings across 1 report (0 exempt by 'prove-it: allow')
$ echo $?
1
```

A proven report, same scanner with replay:

```
$ python scripts/prove.py examples/proven.md --run
prove-it: clean -- 2 claims proven across 1 report, 0 findings (0 exempt by 'prove-it: allow')
$ echo $?
0
```

Contract suite (`python -m unittest discover -s tests -v`):

```
test_escape_hatch_suppresses_and_counts ... ok
test_json_reports_structure ... ok
test_missing_report_is_usage_error ... ok
test_prose_without_claims_is_clean ... ok
test_proven_report_passes ... ok
test_run_confirms_proven_evidence ... ok
test_run_detects_evidence_mismatch ... ok
test_unproven_claims_fail_with_rules ... ok

----------------------------------------------------------------------
Ran 8 tests in 1.183s

OK
```

| Fixture | Expected | Observed |
| --- | --- | --- |
| [`examples/unproven.md`](examples/unproven.md) | exit 1, 3 failures + 1 weasel | exit 1, 3 failures + 1 weasel |
| [`examples/mismatch.md`](examples/mismatch.md) | exit 0 static, exit 1 `--run` | exit 0 static, exit 1 `--run` |
| [`examples/proven.md`](examples/proven.md) | exit 0 with `--run` | exit 0 with `--run` |
| `--format json` | `ok:false`, `fail:3`, `claims_proven:1` | `ok:false`, `fail:3`, `claims_proven:1` |

## Design notes

- **Pairing, not proximity.** The claim must be the line directly above the
  opening fence — a document full of evidence blocks cannot launder an
  unrelated floating claim.
- **Replay is the gate.** Static mode only validates structure; a fabricated
  transcript passes structure. `--run` re-executes the commands, which is
  why CI is the right place for it and why mismatches are hard failures.
- **Excerpts, not summaries.** Findings quote the offending claim so the
  fix is obvious without opening the file.
- **Hedges are warnings.** "Should be fixed" may be honest uncertainty —
  `--strict` turns honesty-without-evidence into a failure for teams that
  want claims binary.
- **The escape hatch is auditable.** `# prove-it: allow -- <reason>`
  suppresses one finding but increments the visible exempt counter.

## Project layout

```
prove-it/
├── SKILL.md               # Agent Skill: claim → execute → evidence → gate
├── scripts/prove.py       # the gate (single file, stdlib only)
├── references/RULES.md    # rules, report format, replay semantics
├── examples/              # fixtures: proven, unproven, mismatch
└── tests/test_prove.py    # contract tests driving the real CLI
```

## License

[MIT](LICENSE)
