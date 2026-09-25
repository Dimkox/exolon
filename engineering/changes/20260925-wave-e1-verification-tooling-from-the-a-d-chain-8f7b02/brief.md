# Wave E1 — verification tooling for the A–D chain debt (#21/#22)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). Route 8f7b02 · base `0b0dea9` (A+B+C+D merged).

## Problem
Four chained waves left the verification story fragmented and partially self-defeating
(measured, itemized in issues #21/#22): committed waves freeze their own parse/attribution sets
while each later rebase moves lines out of everyone's scope (2 494 wave-A code lines scanned by
nobody); the 20260919 loader harness no longer compiles after wave B moved the query into the
loader; `v3_measurements.py` mirrors print stale 76/51 rc=0 on the fixed tree; wave B's
`wave_base()` silently falls back to the WIDE base in clones without `origin/main` (false green);
wave A's M3 timing assert is load-sensitive; `warp_debug_only` misses a GUID move.

## Outcome
One root-anchored `engineering/tools/wave_scan.py` that re-polices the whole chain and runs every
merged meter as a suite; the four targeted tool hardenings; zero product/gameplay/data changes.

## Scope
IN: wave_scan.py (union parse `295690b..HEAD ∪ working ∪ untracked`; root-anchored attribution
scan with per-wave bucketing so violations are attributed; cross-meter runner with recorded
sub-results: A 28, B 9, C 9, D handout 11 + stage 10, plus the loader-harness run);
`run.sh:51` += GameConstants.swift (recorded one-liner in the merged 20260919 package);
frozen-historical header on `v3_measurements.py` (no behavior rewrite); B-meter `wave_base()`
fail-closed when the remote ref is absent; A-meter M3 → soft warning band with the deterministic
allocation grep kept hard; `warp_debug_only` asserts the owning target-block GUID.
OUT: `Exolon/Resources` (untouched by design), gameplay semantics, wave-D Track A/B runs
(permanently external), `vitorc` regeneration (wave E2 — requires explicit owner data approval),
issue #16 acceptance (owner call).

## Constraints
- Merged-file edits ONLY the two tool lines/headers named above (living tools, not dated claims);
  every hardening ships with a flipping control; no silent policy relaxations.
- wave_scan single command ≤ 10 min, stdlib + swiftc; emits machine-readable summary.
- All five merged meters must stay green on the E1 head; a red there blocks E1, not them.
- GitHub closing-keyword rule from #22 item 7 applies to this PR body (no stray close-tokens).
