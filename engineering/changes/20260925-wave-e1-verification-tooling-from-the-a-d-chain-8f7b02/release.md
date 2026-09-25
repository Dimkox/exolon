# Release plan — Wave E1 verification tooling from the A-D chain debt (issues #21/#22)

> Route 8f7b02 · base `0b0dea9` (A+B+C+D merged) · tooling-only change. Typed authority:
> [`change-spec.yaml`](change-spec.yaml). Local evidence below is preflight only; the merge gate is
> the App-owned policy-epoch check on the exact PR head SHA.

## Deployment

Nothing is deployed. There is no runtime, no schema, no data, no service and no product byte
involved: wave E1 ships `engineering/tools/wave_scan.py`, this package's
`evidence/wave_e1_check.py`, and the seven recorded tool touches listed in
[`tasks.md`](tasks.md). Rollout is therefore "merge to `main`, then run the tool":

1. merge the PR (external Trust CI check on the exact head SHA must be green first);
2. from a clone with `refs/remotes/origin/main` present, run
   `python3 engineering/tools/wave_scan.py` — one command, ≤10 min budget, measured 81 s here;
3. the next wave rebases onto the merged head and runs the same command; its own commits land in
   the "committed on this branch" attribution bucket automatically (bucket boundaries are read from
   the merge history, not hard-coded).

## Feature flags / staged rollout

No flags. Two switches exist for offline/partial use and neither relaxes a verdict:

- `wave_scan.py --only parse|attribution|meters` and `--meter NAME` restrict contours; a restricted
  run prints `RESULT: WAVE_SCAN_GREEN_PARTIAL`, exits **3** (0 = the series contour, 1 = red,
  2 = usage, 3 = green-but-partial) and reports `"partial": true` plus `skipped=…`, so a partial
  green can never be read as the series contour or as a gate.
- `wave_b_check.py` keeps its own `--artifact-only`; wave E1 added no opt-in path around the
  `origin/main` fail-closed rule.
- Soft M3 bands are not a flag: they always print a `WARNING` line with the measured value, in both
  layers (`harness/main.swift`, `gameplay_log_check.py::emission_cost_budget`).

## Metrics and alerts

| Signal | Where it is emitted | Alert condition |
| --- | --- | --- |
| one line per meter (`expected/passed/failed/rc/seconds/verdict line`) | `wave_scan.py` `SUMMARY meter …` | any `green=NO`, or a count that differs from the recorded one |
| per-wave attribution counts | `wave_scan.py` `bucket …` lines (also in `--json`) | a merged-wave bucket with `code_lines=0`, or `violations>0` |
| suite wall time | `SUMMARY TOTAL … elapsed=…s budget=600s` | `elapsed` over budget → the run is red by rule (SIG-001) |
| tree writes caused by a run | `SUMMARY TOTAL … tree_writes=…` | non-`none` on a tooling wave → somebody's evidence-refresh moved the fingerprint |
| load-sensitive cost | `WARNING emission-cost band …` / `WARNING … (M3) …` | not an alert; it is the disclosed measurement limit (wave A M3 tripped under host load 16-18) |
| stale mirror | `wave_c_check.py` prints two `WARNING … frozen-historical …` lines | wording points at the header; not a failure of wave C or E1 |
| probe verdicts | `wave_e1_check.py` `RESULT: WAVE_E1_PROBES_PASS \| probes=11 failed=0` | any failed probe, including a control that refused to flip |

Load sensitivity is now explicit rather than folk-knowledge: the wave-A append budget, the 0.5 %/5 %
tick ratios and the 55-70 ns sizing band are warnings; the deterministic twins
(`producer <= 0`, `>5×` formatting-control relation, `8×` drain floor, allocation scan) still fail.

## Go/no-go criteria

Go requires **all** of:

- `engineering/tools/wave_scan.py` exits 0 with `parse_failures=0`, `attribution_violations=0`,
  `meters=6/6 green` and elapsed under the 600 s budget (this head: 20 files parsed, 2938 added code
  lines scanned, 81 s) — `evidence/wave-scan-end-to-end.txt`;
- `python3 evidence/wave_e1_check.py` reports `probes=11 failed=0` with every flipping control
  executed — `evidence/wave-e1-check-green.txt`, `evidence/wave-e1-check.json`;
- `git status --porcelain -- Exolon Exolon.xcodeproj` empty (FORBID-001) and
  `git show-ref | grep refs/heads/origin` empty (the controls run only inside clones);
- `python3 scripts/grok_verify.py --mode pr --no-record` PASS — `evidence/grok-verify-pr.txt`;
- `ruff check` clean on the two new files (pre-existing findings in the merged tools are listed,
  not silently rewritten) — `evidence/ruff-new-tools.txt`.

No-Go / hold: any meter red at its recorded count (a red merged meter blocks **E1**, per the brief —
it does not get excused in place); a control that does not flip; an unattributable violation
(`bucket=unattributed`); an elapsed time over budget.

Permanent residuals that do **not** block and are not hidden: everything class-2/macOS (no Apple
host, #22 item 6), `vitorc` spawn regeneration for 48 maps (wave E2, needs owner data approval),
issue #16 acceptance (owner call), and the `//`-inside-a-string-literal limit inherited from
`strip_comments()` (shared by every predicate in the series).

PR body rule from #22 item 7: each `Closes #N` on its own line — this PR closes #21 and #22 only
when both are stated separately.
