# Test plan — Wave E1 verification tooling from the A-D chain debt (issues #21/#22)

Typed authority: [`change-spec.yaml`](change-spec.yaml). Every `test` path in the spec resolves to a
function in [`evidence/wave_e1_check.py`](evidence/wave_e1_check.py); this plan says which scenario
each one evidences and how each verdict can be shown to fail.

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | A committed wave's Swift stops being parsed by anyone (the #21 hole): syntax garbage in a file a *previous* wave committed must redden the tool | `wave_e1_check.py::scan_covers_committed_union` (committed garbage in `BlasterBullet.swift`, clean worktree; plus an untracked-file control proving the set is dynamic) |
| P0 | The accumulated A..HEAD delta stops being policed for magic offsets / per-map tables | `wave_e1_check.py::attribution_scan_flips` (root-anchored scan: 2938 added code lines, 16 files, 6 merge-history buckets; planted `L01S02`, `+ 16`, `544.0` each redden; allow-list proven per-predicate) |
| P0 | The series contour must pass on this head, and one red meter must redden the contour | `wave_e1_check.py::cross_wave_suite_green` (A 28, B 9, C 9, D handout 11, D stage 10, loader 125/125) + forced-red `wave-d-stage` + absent-meter controls |
| P0 | E1 must not touch the product | `wave_e1_check.py::product_untouched` (FORBID-001) |
| P1 | A hardening must not be a relaxation in disguise | `wave_e1_check.py::no_silent_relaxation` (FORBID-002: B's non-vacuity guard + a planted ±16 still red at the root anchor, A's hard checks byte-identical to HEAD, C's edit text-only, `wave_scan` red without `swiftc`) |
| P1 | The merged 20260919 loader harness must compile and reproduce 125/125 again | `wave_e1_check.py::loader_harness_green` (AC-004) + the one-line-revert control in a clone |
| P1 | A clone without `origin/main` must not false-green wave B's meter | `wave_e1_check.py::b_meter_failclosed` (exit 4, `FAIL-CLOSED`, no scan line at all) + the pinned-ref positive control |
| P1 | The warp's Debug condition must bind to the owning project block, not to a GUID-shaped regex | `wave_e1_check.py::warp_guid_bound` (AC-008): moves into project Release, target Debug, **target Release** and a duplicate copy all redden |
| P1 | Suite and standalone must not disagree | `wave_e1_check.py::suite_standalone_agreement` (INV-001); the counters are derived twice, by two different implementations |
| P2 | A stale mirror must not read as current truth | `wave_e1_check.py::v3_header_present` (AC-005) + stripped-header falsification + before/after stdout-and-traceback identity |
| P2 | A load spike must not redden a correct tree, and a clock that measured nothing must not pass | `wave_e1_check.py::m3_soft_band` (AC-007) with over-band / zero-cost / control-ratio / drain-low and the on-disk allocation-mutation controls |

## Automated checks

- Unit: `python3 engineering/changes/…8f7b02/evidence/wave_e1_check.py` — 11 probes, each with its
  control; `--json` gives pure JSON on stdout (`evidence/wave-e1-check.json`), `--only` runs one.
- Integration: `python3 engineering/tools/wave_scan.py --json` — union parse + attribution +
  merged-meter suite in one command (budget 600 s; measured 81 s on this head); human transcript in
  `evidence/wave-scan-end-to-end.txt`.
- Contract: the merged meters are themselves the A-D contract contour (A's schema round-trip, B's
  pinned geometry, C's manifest seal, D's ledger and handout binding). `wave_scan` *executes* them
  instead of restating their claims, and records the verdict counts it expects.
- E2E: the 20260919 loader harness (`REAL MAPS ok=125/125 failures=0`) and wave A's executed
  Foundation contour run inside the same suite, so the chain is proven on real Swift, not on text.
- Static analysis: `python3 -m ruff check` on the new tools (output in
  `evidence/ruff-new-tools.txt`, together with the merged files' *pre-existing* findings, which wave
  E1 neither introduced nor silently "fixed").

## Manual checks

- `git status --porcelain -- Exolon Exolon.xcodeproj` empty after the whole freeze.
- `git show-ref | grep refs/heads/origin` empty (no ref pollution from the clone-based controls).
- Read `evidence/wave-scan-end-to-end.txt`: every meter line must carry its recorded count and rc,
  not just the word green.

## What this plan does **not** prove

- Nothing class-2/macOS: type-checking beyond `-frontend -parse`, SpriteKit behaviour, signing,
  Track A/B probe runs (no Apple host; permanent residual, #22 item 6).
- `vitorc` spawn regeneration (48 maps) and issue #16 acceptance — out of scope by ruling (E2/owner).
- The `//`-inside-a-string-literal blind spot inherited from the merged `strip_comments()`; it is
  disclosed in `wave_scan.py` and `tasks.md`, not papered over.
