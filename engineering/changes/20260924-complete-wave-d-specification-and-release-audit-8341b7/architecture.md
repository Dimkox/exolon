# Architecture — wave D

> Typed authority: [`change-spec.yaml`](change-spec.yaml). Deep detail lives in the four
> `evidence/analysis-*.md` reports; this file is the integration view.

## Current behavior
Stage boundary = `checkScreenExit` x>510 → `applyOriginalStageBoundaryIfNeeded` (3/6 clauses;
award before terminal guard — the P1-8 farm seam) → `transition`/`enterContentComplete`.
Release verification stops at Debug-build observation; probe output is free text with EXPECTED
comments; no archive-content inspection; two probe defects (M-8 tee flush, M-9 in-repo artifacts).

## Proposed behavior
Two-phase, one owner:
- **D-2** (independent of wave A): `macos-probe.sh` gains Track A steps with machine-readable
  `key=value` verdicts (5-valued), mandatory archive + `.xcarchive` inspection, flush barrier,
  out-of-tree build roots; handout contract (`engineering/contracts/schemas/macos-probe-report-v1.schema.json`)
  + Linux checker `macos_handout_check.py` with contradictory synthetics; strict agent/human
  boundary (Track B physically unreachable from any agent path).
- **D-1** (after wave A merges): data-driven `StageBoundaryLedger` sequence (component list, each
  with once-key), bravery activation-latch, owner-approved timed tick-ladder, explicit
  `maxLives=9`, exoskeleton clear, shared refill constants, bounded debug warp, product
  hardening/entitlements pbxproj edits with expected cutover reds documented.

## Components and boundaries
- Ledger + sequence: wave-A files (`StageBoundaryLedger.swift`) — wave D edits only this file for
  P1-10 (no new product files → no pbxproj 4-edit conflict class).
- GameScene: sampling (`x>510`), application via `awardPoints` funnel (single), banner/terminal
  skin, `player.setExoskeleton(false)`; warp behind `#if !DEBUG` + env, through `transition(to:)`.
- Probe/handout: `engineering/runbooks/macos-probe.sh` (tracked, not protected),
  `engineering/contracts/schemas/macos-probe-report-v1.schema.json`,
  change-local `evidence/{macos_handout_check.py,stage_boundary_check.py}`.
- Merged historical evidence (`20260921-...2e7698/**`) is immutable; cutover reds are recorded in
  wave-D evidence, never patched into history.

## Data flow (D-1 award)
fixedUpdate → sample x>510 → ledger.award(completedZone, ctx{tick, stageStartTick, lives,
tookExoskeletonLatch}) → [Award(components)|Suppressed(reason)] → GameScene applies via
awardPoints(…, reason: .stage_boundary) + lives/refill/exo side effects → witness events through
injected sink (Null before rebase) → checkpoint save (after guard, never before terminal check).

## API and event contracts
- `bonus.stage_points` payload grows component fields (`lives_component, bravery_component,
  timed_component, phase_ticks`); wave-A identity predicate already accepts
  bravery∈{0,10000}, timed∈{0,1000,3000,5000,7000}.
- `exolon.macos-probe-report/1`: per-step {id, argv, rc, verdict, raw_digest, control_flip_expectation};
  binding fields repo_head, tree_fingerprint, probe_blob_sha1, artifact sha256/CDHash, notary uuid;
  10 consistency rules each with a flipping control; STALE-not-green policy.

## Governance context / Bitrix
n/a (no governance dir; not Bitrix).

## Decisions
Owner gate rulings 1–4 (brief.md) + analyst rulings: bravery = activation latch (OM:142 vs :118
falsifiable test); award ordering lives×1000 before +1 (keeps current `:627-628`); clamp case
asserted as `applied == min(earned, 999_999 − pointsBefore)`; "clean machine" defined as the
handout protocol's execution context (fresh user, Xcode CLT present, no repo-derived build state).

## Risks and mitigations
| Risk | Mitigation |
| --- | --- |
| Wave-A merge reorders GameScene seams | D-1 explicitly rebases; ledger-file-only edits; warp via existing transition |
| Timed-ladder read as canonical | constant comment + architecture note: owner-approved approximation, cursor minigame unimplemented |
| Handout looks "green" without machine | ABSENT→unverified rc semantics; synthetic contradictory handouts must redden checker |
| Merged checker reddens after D-1 | measured cutover set fixed to {hardened_runtime_key_count} (deferral-recorded cannot flip without forbidden edit of dated evidence); any other red = regression; observed⊆declared + liveness enforced by cutover_set_exact |
| tee flush race undetectable on macOS bash 3.2 via $! | line-count barrier design (integration §4-E), validated by local bash simulation + handout step |
| Credential leakage | no code path takes credentials; only keychain-profile name validated; abort-not-redact argv scan |
