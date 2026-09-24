# Wave D: stage-end sequence (P1-10) + release Track A contract (P1-11 remainder)

> Typed authority: [`change-spec.yaml`](change-spec.yaml).

Change ID: `20260924-complete-wave-d-specification-and-release-audit-8341b7`
Route base `295690b` · branch `codex/wave-d-spec-release-20260924` · risk red/high
Gate `scope_and_design_approval`: **APPROVED by owner 2026-09-24** (rulings below).
Analysis: `evidence/analysis-{repo_explorer,architect,docs_researcher,integration_architect}.md`.

## Problem

- **P1-10** (issue #14): stage-end sequence implements 3/6 canonical clauses (`ORIGINAL_MECHANICS.md:138-148`). Missing: bravery 10 000 (no-exos condition), timed bonus 0/1000/3000/5000/7000 (no clock/cursor in tree), exoskeleton clear at boundary (`setExoskeleton(false)` exists only in `restartFromBeginning`, `GameScene.swift:963`). Life cap is borrowed from `startingLives=9`; points ceiling is a bare literal (`GameScene.swift:662`). The "deliberately dormant" comment at `:623-625` is FALSE — all five boundaries are live today.
- **P1-11 remainder** (issue #15): signing/hardened/notarization end-to-end on a "clean machine". Merged assets (`release_layer_check.py` 44 EXPECTED keys + 29 controls; `macos-probe.sh`) stop by design at Debug-build observation; `notarytool`/`stapler` appear nowhere; two NEW defects found during analysis: M-8 tee-flush race loses `--out` in ~7/10 runs after rc=0, M-9 in-repo build artifacts stale every fingerprint receipt.

## Owner rulings at the gate (binding)

1. **Design approved** as scoped below.
2. **Timed bonus = tick ladder** (owner chose the approximation over deferral): `phase = min(4, (tick − stageStartTick)/PHASE_TICKS)`, `PHASE_TICKS = 1800`, ladder `[7000,5000,3000,1000,0]`; `PHASE_TICKS` is a named constant whose comment records it as owner-approved deviation from the norm's interactive-cursor text — NOT asserted as canonical. The interactive cursor minigame remains out of scope forever in this change.
3. **Ordering**: Track A (probe/handout/checker) implemented now; P1-10 ledger sequence lands after wave A merges (the ledger lives in wave-A files; no new product files from wave D to avoid pbxproj conflicts on rebase).
4. **Debug warp granted**: bounded `EXOLON_DEBUG_WARP=LxxSyy`, off by default, `#if !DEBUG`-disabled so it is absent from Release builds, goes through the real `transition(to:)` path (exercising wave-A accumulator reset), echoes stderr + emits event after rebase.

Explicitly deferred (recorded, not silent): stage-start coordinates OM:147; consuming `stageExitMarkers` (dead data stays, trigger stays `x>510` per wave-A ruling 3); reset-vs-title semantics after 124 keep current behavior; `VERSION`/README release wiring (protected-path decision, separate ask).

## Scope

### In scope
- D-2 (now): `macos-probe.sh` Track A extension (mandatory archive + `.xcarchive` content inspection, 5-valued verdicts PASS/FAIL/NOT_ATTEMPTED/TOOL_ABSENT/REFUSED, new exit codes 77/78, key=value machine-readable verdicts, M-8 flush barrier, M-9 out-of-tree SYMROOT contract); handout JSON schema `exolon.macos-probe-report/1` + `evidence/macos_handout_check.py` (consistency rules + contradictory synthetic controls, commit-then-receipt order, `MACOS_EVIDENCE=ABSENT → unverified`, never red-as-gone); agent/human boundary enforcement (double env gate + tty refusal, argv/env abort-not-redact with forbidden list, credentials never handled, Team ID/cert hashed); L0 characterization verifier `evidence/stage_boundary_check.py` (current 3/6 clauses pinned as table).
- D-1 (after wave-A merge, rebase onto main): full ledger sequence data-driven — lives×1000 (pre +1), bravery 10 000 with activation-latch semantics (OM:142 vs :118 contradiction resolved by the falsifiable latch reading: activated-once-in-stage forfeits bravery), timed ladder per ruling 2, +1 life under new explicit `maxLives=9` constant, exoskeleton clear at boundary, refill 99/10 reused via constants (also `updatePickups` literals `:526/:533` switch to the shared constants), debug warp per ruling 4, pbxproj: `ENABLE_HARDENED_RUNTIME=YES` in both target blocks + tracked minimal `Exolon.entitlements` + `CODE_SIGN_ENTITLEMENTS`.
- Cutover honesty: merged `release_layer_check.py` stays UNMODIFIED; after D-1 it reddens exactly on the measured set {hardened_runtime_key_count} — `hardened_deferral_recorded` reads immutable dated plan text and is declared non-red (amended 2026-09-24 after D-2 measurement); documented expected cutover (precedent: v3_measurements shared_xcschemes pin), wave-D checker owns the new EXPECTED set.

### Out of scope
- Track B execution (Developer ID, real notary submission) — closes only as human run on a clean machine consuming this change's handout; no PR claim of notarization.
- Interactive bonus-cursor minigame; stage-start coordinates; stage_end marker consumption; VERSION/README; any credential handling by any agent (AGENTS.md).

## Constraints
- Backward compatibility: pre-D-1 behavior of the three existing clauses unchanged; score funnel stays `awardPoints` single path; wave-A witness `bonus.stage_boundary_suppressed` must keep firing for repeats.
- Data/privacy: no secrets/PII in logs or handouts; only hashes of identity material.
- Performance: n/a (probe steps are human-paced).
- Operational: rollback = revert (probe/handout) + `EXOLON_DEBUG_WARP` unset (warp); one step.
