# Tasks — Wave E1 verification tooling from the A-D chain debt (issues #21/#22): add engineering/tools/wave_scan.py — a root-anchored (change-base 295690b..HEAD plus working tree plus untracked) union scanner that parses every touched Swift file with swiftc -frontend -parse, runs the per-wave added-lines attribution scan once from the root base so no committed wave is left unpoliced, and executes the merged per-package meters (A 28 checks, B 9, C 9, D handout+stage 10+10 and 11) as a cross-wave suite; fix the merged 20260919 loader harness run.sh file list (add GameConstants.swift, one line, recorded); mark v3_measurements.py mirrors as frozen-historical with a header (no behavior rewrite); harden wave B meter wave_base() to fail closed when origin/main is absent instead of silently widening to 295690b; make wave A M3 timing assert a soft warning band with the deterministic allocation grep kept hard; extend stage_boundary_check warp_debug_only to assert the owning target-block GUID. No Exolon/Resources edits, no gameplay semantics changes.

- [x] Freeze contracts and expected behavior.
- [x] Add failing test or characterization test.
- [x] Implement the smallest vertical change.
- [x] Run selected quality profile.
- [ ] Complete independent reviews.
- [ ] Bind evidence to the final tree fingerprint.

Analysis note (route 8f7b02): the formal analysis waits were skipped for this wave — the
read-only `repo_explorer` lane confirmed the six targets concurrently and its report
(`evidence/analysis-repo_explorer.md`, saved by the controller) is the input this file records;
where it disagreed with the brief, the measured fact won and is noted under *Rulings* below.

## What landed

New tooling (nothing else in the tree is new code):

| path | role |
| --- | --- |
| `engineering/tools/wave_scan.py` | root-anchored union parse + per-wave attribution scan + merged-meter suite; `--json`, one summary line per meter, 10-minute budget |
| `engineering/changes/…8f7b02/evidence/wave_e1_check.py` | the 11 named evidence probes (AC-001…AC-008, INV-001, FORBID-001/002), every one with a flipping control |

Measured input set on this head (not pinned in code): 20 `*.swift` files = 16 product +
4 evidence-harness drivers (`20260919` loader `main.swift`, wave A harness `main.swift` +
`coregraphics_shim.swift`, wave B `wave_b_harness/main.swift`, wave D `ledger-xcheck/main.swift`);
working-tree and untracked Swift enter the set dynamically (proved in AC-001's second control).

## Authorized merged-tool edits (each one is a living tool, not a dated claim)

1. `engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/harness/run.sh`
   — step 4 compiles `"$ROOT/Exolon/GameCore/GameConstants.swift"` as a third translation unit,
   plus a `# E1 provenance` header comment. AC-004. This is the one-line loader-harness fix
   (#21/T1): wave B's `6c7dfe5` made `TMXMapLoader.swift` reference `GameConstants`
   (`TMXMapLoader.swift:107,110-112,120,167,234-236`), so the two-file contour stopped compiling.
   No product byte changed: the harness compiles a repo file it did not compile before.
2. `…/20260919-…-7db1f3/evidence/harness/last-run.txt` + `…/harness/README.md`
   — the transcript re-recorded by the fixed `run.sh` (same scrub convention: `<build-tmp>` for the
   PID build dir, no absolute paths, no trailing blanks), and the README row that cited the stale
   `HEAD 52795d1` run. Regenerated because the old file could no longer be produced by the
   committed harness; the body is byte-identical apart from the `cut -c1-90` width of one
   negative-control line.
3. `…/20260919-…-7db1f3/evidence/v3_measurements.py` — 12 added docstring lines, zero code lines:
   the frozen-historical header (AC-005). Verified inert: stdout identical and the same last
   traceback line before/after (control in `wave_e1_check.py::v3_header_present`).
4. `…/20260924-…-f2d90a/evidence/wave_c_check.py` — only the string literal of the stale-mirror
   divergence message: it now points at the header and at this meter as the maintained truth
   instead of promising "owner-route cleanup owed" (AC-005). Logic, keys and probes untouched
   (`+5/-2` lines, all inside the one literal; asserted text-only in FORBID-002's probe).
5. `…/20260924-…-i-35bac2/evidence/wave_b_check.py::wave_base()` — (a) missing
   `refs/remotes/origin/main` is now an explicit `FAIL-CLOSED` on stderr with exit 4 (the silent
   wide fallback to `295690b` is gone; that fallback is what false-greened the release reviewer's
   clone); (b) when `merge-base(HEAD, origin/main) == HEAD` — a tooling wave, or a branch equal to
   main, i.e. no product delta of its own — the scan re-anchors to the root base and **prints the
   reason**, so the accumulated A..HEAD delta stays policed by B's own predicate too. Both are
   widenings: the non-vacuity guard (`files>=7`, `code lines>=150`) is untouched and still reddens
   (FORBID-002 proves it with a planted ±16). AC-003/AC-006.
6. `…/20260924-…-32f59c/evidence/gameplay_log_check.py::emission_cost_budget` and
   `…/32f59c/evidence/harness/main.swift` — the load-sensitive absolute timing bands (the ~4 µs
   M3 60-append band, the 0.5 %/5 % wall-clock ratios, the 55-70 ns sizing band) became WARNINGs
   carrying the measured value, in both mirror layers. Kept HARD: `producer <= 0` /
   `producerNs > 1` (a clock that measured nothing is a broken gate), the ≥5× formatting-control
   *relation*, the 8× realtime drain floor, and `hot_path_is_allocation_free` — which wave E1 did
   not touch at all (its body is byte-identical to `HEAD`, asserted in FORBID-002). AC-007.
7. `…/20260924-…-8341b7/evidence/stage_boundary_check.py::warp_debug_only` — the DEBUG condition
   is now bound to its **owning block**, derived from the project objects
   (`PBXProject/PBXNativeTarget → buildConfigurationList → buildConfigurations`), and the condition
   must be absent from all three other `XCBuildConfiguration` blocks; the exactly-once count stays
   as belt-and-braces. Replaces the hard-coded `800…002`-only regex. AC-008.

## Controls that must flip (all executed in `wave_e1_check.py`, each in a fresh
## `git clone --no-hardlinks` tree — never mutate-then-restore in the real worktree)

| AC | green side | flipping control |
| --- | --- | --- |
| AC-001 | 20 files parse, `verdict=ok` | committed syntax garbage in `BlasterBullet.swift` reddens the scan and names the file; untracked garbage enters the set (21 files) and reddens it; the parse gate's own selftest requires broken≠good |
| AC-002 | 0 violations / 2938 added code lines / 16 files, buckets wave-a 2494, wave-b 237, wave-c 95, wave-d 124 | planted `if name == "L01S02"`, planted `+ 16`, planted `544.0` each redden it; a committed plant is attributed to the branch bucket; `544` in `GameConstants.swift` stays allowed while `L01S02` there reddens (allowance is per predicate, not per file) |
| AC-003 | 6/6 meters green at the recorded counts (28, 9, 9, 11, 10, 125/125) in one command | `phaseTicks 1_800→1_801` in a clone reddens `wave-d-stage` and the whole suite; deleting a meter script is red, never a skip; a restricted `--meter` run is reported `partial` |
| AC-004 | `run.sh` rc=0, `REAL MAPS ok=125/125 failures=0`, both negative controls printed | reverting the one line in a clone gives `cannot find 'GameConstants' in scope` and rc≠0 |
| AC-005 | header present, C meter green with two header-citing WARNINGs | predicate fed a copy with the docstring stubbed must report problems; the pre-edit copy must produce the same stdout and the same last traceback line |
| AC-006 | pinned clone: 9/9 with 2938 lines in 16 files | clone with `refs/remotes/origin/main` deleted: exit 4, `FAIL-CLOSED`, no scan line at all |
| AC-007 | over-band extras pass with a WARNING naming the measured value | `producer=0`, formatting-control `<5×`, drain `<8×` each still FAIL; an `appendRecord` that allocates on disk reddens the hard scan; in the Swift layer one mutated build prints `WARNING … M3 …` while the impossible lower bound still `FAIL`s the run |
| AC-008 | DEBUG in the project Debug block passes | moving the condition into project Release / target Debug / **target Release** (the reviewer's mutation) each redden it, and a duplicate copy reddens it |
| FORBID-001 | `Exolon/`, `Exolon.xcodeproj` byte-clean; every working path is in scope | (structural: any product path in the working diff fails the probe; a scratch `.bak/.orig/.rej/fixture` file fails it) |
| FORBID-002 | B guard present + planted ±16 still red; A hard checks byte-identical to HEAD; C edit text-only; wave_scan red without `swiftc` | each of those four is itself the flipped side of a leniency |
| INV-001 | standalone verdict counts == suite verdict counts for all 6 meters, same rc | the counters are computed twice, by `wave_scan.verdicts()` and by `wave_e1_check.count_verdicts()`, from the meters' own output |

## Rulings (measured fact beating the briefing text)

- `v3_measurements.py` does **not** "print 76/51 with rc=0" on this head: it aborts with `rc=1` at
  its `BlasterBullet` pin (wave B removed the `logicalSize.width + 16` wording it greps for).
  `linux_static_audit.py` still prints and still exits 0. AC-005 therefore freezes the mirror with
  a header that states the abort, and wave C's reworded WARNING no longer claims `rc=0`. No
  behavior was "fixed" — that stays out of E1's scope.
- Running merged tools can rewrite dated evidence: `linux_static_audit.py` regenerated
  `linux-static-audit.json`/`.md` (18→23 Swift sources, `CFBundleShortVersionString` now
  `$(MARKETING_VERSION)`) during a read-only probe; restored to HEAD bytes. All E1 controls that
  run a merged tool do it inside a clone, and the freeze runs tools in the real tree only where the
  tool is idempotent (`wave_b_check.py` rewrites `wave_b_deltas.md` only on content change —
  verified: `git status` clean after B runs).
- `wave_base()`: the release reviewer's `false green` and wave C's Deviation-14 `loud red` are two
  different defects. E1 keeps B loud (missing ref ⇒ exit 4) and makes the no-delta case *wider*
  instead of either red or vacuously green; per-wave attribution is now wave_scan's job, where the
  buckets are explicit.

## Package paperwork (this route's own files)

`test-plan.md`, `requirements.md`, `architecture.md`, `release.md` and `rollback.md` arrived as empty
templates; the wave-D reviewers scored exactly that (an empty `release.md` Go/no-go slot, an empty
`requirements.md` Performance slot), so they are now filled with the measured numbers and the named
residuals rather than prose. The typed spec stays the authority; the Markdown only explains.

## Residuals (disclosed, not blocking)

- The attribution scan inherits wave B's `strip_comments()`, which cuts at a `//` inside a string
  literal — a violation hidden behind `"https://…"` on the same physical line stays invisible to
  every predicate in the series (documented in `wave_scan.py`; changing it would re-open what
  A-D certified).
- The Swift-layer soft M3 band is falsifiable only through the value the harness reports: the
  over-band `WARNING` path is proven by a mutated build in a clone, and the hard twins
  (`producerNs > 1`, `>5×` control, `8×` drain) stay asserts. A slow machine can no longer redden
  the gate, and a fast one cannot hide an allocating hot path (that is a static scan).
- `wave_scan` bucket names come from `Merge pull request #N` subjects; a squash-merge wave would
  land in the "committed on this branch" bucket rather than a named one (still scanned, just less
  precisely attributed).
- `macos_handout_check.py`/`ledger-xcheck` Track A/B runs and every class-2 macOS fact remain
  permanently external (no Apple host); `vitorc` regeneration (48 maps) and issue #16 acceptance
  are wave E2 / owner calls, untouched here.
- **README handoff for the controller (AGENTS.md "README before push")**: `README.md` has no
  "current state" entry for `engineering/tools/` at all, and no wave B/C/D/E1 sections - the file is
  behind the tree independently of this change. E1's own scope forbids touching anything outside
  `engineering/tools/`, the three merged touch-points and this package, so the README line for the
  new root-anchored tool is a PR-body/controller step, not an E1 file edit.
## Freeze measurements (this head, 2026-09-25; artifacts in `evidence/`)

| command | result | wall |
| --- | --- | --- |
| `python3 engineering/tools/wave_scan.py` | `RESULT: WAVE_SCAN_GREEN`, parse 20 files (16 product + 4 evidence, 0 deleted, 0 failures, selftest true), attribution 2 938 added code lines / 16 files / 0 violations / 6 buckets, `meters=6/6 green`, `tree_writes=none` | 82 s (`elapsed=81.9s` of the 600 s budget) - `evidence/wave-scan-end-to-end.txt` |
| `python3 evidence/wave_e1_check.py` | `RESULT: WAVE_E1_PROBES_PASS \| probes=11 failed=0` (`seconds=214.2`) | 215 s - `evidence/wave-e1-check-green.txt` |
| `python3 evidence/wave_e1_check.py --json` | same 11 green, pure JSON on stdout | 212 s - `evidence/wave-e1-check.json` |
| `python3 -m ruff check` (new tools) | `All checks passed!` rc=0; the merged files' 7 findings are pre-existing lines, listed and left alone | `evidence/ruff-new-tools.txt` |
| `python3 scripts/grok_verify.py --mode pr --no-record` | `RESULT: PASS \| profiles=base,frontend`, incl. `PASS git-diff-check`, `PASS change-spec`, `PASS secret-scan`, `PASS ruff`, `PASS bandit`, `PASS source-stability` | 181 s - `evidence/grok-verify-pr.txt` |

The two earlier grok_verify attempts are recorded here as process facts, not hidden: one failed
`source-stability` because I was still writing this package's artifacts while it ran, and the fix was
to run verification last with the tree settled (that is exactly the failure mode the "read-only
auditors still mutate the tree" lesson describes). Per-check wall times inside `wave_e1_check.py`:
`suite_standalone_agreement` ~79 s (six standalone meter runs) and `cross_wave_suite_green` ~82 s
(the contour dominates), everything else ≤27 s.

Process fact, kept in the record rather than hidden: the first AC-003 implementation timed at 242-245 s
because `wave_e1_check.wave_scan()` appended its `--meter` flags **after** starting the subprocess, so
the "restricted" control silently ran all six meters in the clone. The verdicts it asserted were still
true (a red meter reddens the contour, an absent meter is red, a restricted run reports `partial`), but
the control was not the control it claimed to be. Fixed by moving the flags into `argv` before the run
and by asserting the restricted run returns exactly one meter entry and five skips - a control must
demonstrate that it ran what it says it ran.

## Exit-code and result vocabulary (so a log line cannot be misread)

- `wave_scan.py`: `WAVE_SCAN_GREEN` (exit 0, the full contour), `WAVE_SCAN_GREEN_PARTIAL`
  (exit 3, restricted run - `partial: true` and `skipped=…` in the same output), `WAVE_SCAN_RED`
  (exit 1, with every reason in `problems[]`), usage errors exit 2.
- `wave_e1_check.py`: `RESULT: WAVE_E1_PROBES_PASS | probes=11 failed=0` (exit 0) or
  `WAVE_E1_PROBES_FAIL` (exit 1); `--json` keeps stdout pure JSON and moves progress to stderr.
