# Exolon — Step 9 Rebase (test archive)

This is the first runnable archive from the new level-rebase branch.

Key changes in this archive:
- keeps the existing 125-zone project and original-visual pipeline;
- Zone 009 object placement is rebuilt from the reference TMX coordinates rather than the old source-marker approximation;
- Zone 009 pistons now use x=64/192, y=320 (not y=384);
- changing room is a real 32x80 rectangle at x=368, y=176 in Tiled coordinates;
- rectangle-object coordinate conversion is explicit, so tile objects and rectangles are no longer conflated;
- pistons are lethal when exposed (unless test Invulnerability is ON);
- pressing UP inside the changing room toggles Exoskeleton mode;
- Exoskeleton fires a double blaster and protects against mines/pistons;
- Restart/new session resets Exoskeleton;
- every application launch still starts from Zone 000; High Score persists.

Important: this archive is a runnable checkpoint of the rebase work, not the claim that every late-zone action is already audited.

## Rebase cabin fix

- Changing-room artwork is now pass-through scenery: its action trigger no longer remains hidden behind compiled static collision.
- The collision exclusion is applied by object type, so it affects every changing-room screen, not only Zone 009.
- UP inside a changing room/teleport is consumed as a contextual action and cannot become an accidental jump on the following fixed step.

## Structured gameplay event log (wave A, 2026-09-24)

Every player action and game state change is now observable as one versioned JSON-lines record, and
the four wave-A state-machine findings are fixed with stream-only regression predicates
(`engineering/changes/20260924-implement-a-structured-gameplay-event-log-for-ev-32f59c/`).

- Contract: `engineering/contracts/schemas/gameplay-event-v1.schema.json` (envelope
  `schema_version,seq,tick,frame,rot,ts_us,name` + per-event payload; `ts_us` is derived from the
  tick counter, never wall clock).
- Core: `Exolon/GameCore/Diagnostics/` - Foundation-only, no SpriteKit and no `CGVector`, so the
  fixed-step driver, the stage-boundary ledger, the launcher bonus state and `Player` compile and
  run on Linux (`evidence/harness/run.sh`, judged by `evidence/gameplay_log_check.py`).
- Where the file goes: `$TMPDIR/exolon/gameplay-<run_id>-<rot>.jsonl`, 8 MiB x 8 files, path echoed
  once to stderr. Never inside this repository - an untracked log here would stale every
  fingerprint-bound receipt.
- Switches: `EXOLON_EVENT_LOG=off|0|1|2|<directory>`; default is level 1 in Debug and off in
  Release. `off` creates no file at all. It is **file**-inert, not path-inert: level-0 records still
  append to the in-memory ring (nanoseconds each, and the ring laps quietly-counted when nothing
  drains it), and `GameplayEventLog` remains the injected sink. A build that must touch nothing is a
  build that does not construct the log; every non-injected object still uses `NullGameplayEventSink`.
- In-game: the F1 hitbox window also shows the last 8 log lines in one reused label.
- Fixed behavior: no catch-up step runs in a new zone inside the frame that transitioned (P1-9); a
  held UP cannot jump after a teleport/changing-room consume (P1-4); the stage bonus awards once per
  completed zone per playthrough with a visible suppression record (P1-8); the double-launcher bonus
  pays once and the launcher keeps firing (P1-6).

## Map-data physics (wave B, 2026-09-24, PR #19)

One SpriteKit-free `TMXSurfaceQuery` (`Exolon/GameCore/Levels/TMXMapLoader.swift`) is now the only
interpretation of the Collision layer: spawn (bounded ±16 px correction with body-clear preference,
P1-2), piston anchors (46/46 lethal, P1-1), fallback plane and the renderer's rects all read it;
beam pairs share one 25-hit-point pool destroyed as a unit (P1-5, award now 1000/beam); blaster and
grenade cull bounds derive from clamp+muzzle+projectile size (P1-3). Judge:
`…/engineering/changes/20260924-fix-wave-b-map-data-and-physics-audit-findings-i-35bac2/evidence/wave_b_check.py`
(9 probes, 14-section mutation battery, `TOOL_ABSENT rc=3` without swiftc).

## Stage-end & release layer (wave D, 2026-09-25, PR #17)

Stage boundaries award the full ORIGINAL_MECHANICS:140-146 sequence via data-driven
`StageBoundaryLedger` components: lives×1000, bravery 10 000 (activation-latch reading of
OM:142/118), timed bonus as an owner-approved deterministic tick ladder (`PHASE_TICKS=1800`,
shape-only — not the original interactive cursor), +1 life under `maxLives=9`, exoskeleton clear,
shared 99/10 refill. Debug-only zone warp: `EXOLON_DEBUG_WARP=LxxSyy` (compiled out of Release,
routes through `transition(to:)`). Release layer: `ENABLE_HARDENED_RUNTIME=YES` both target blocks,
tracked empty `Exolon/Exolon.entitlements`, probe Track A contract and the handout protocol under
`engineering/runbooks/macos-probe.sh` + `…/8341b7/evidence/`. Signing/notarization end-to-end
remains permanently externally-blocked (no Apple hardware; issue #15 stays open — read
`evidence/cutover.md` before trusting any `release_layer_check.py` verdict on this tree).

## Verification tooling (wave E1, 2026-09-25, issue #21/#22)

`engineering/tools/wave_scan.py` — one command that re-polices the whole A–E chain: root-anchored
union parse of every Swift file touched since `295690b`, per-wave attribution scan of added lines
(no committed wave escapes it), and a cross-meter suite running all merged meters with recorded
verdict counts (`--json`, budgets, fail-closed on missing remote refs). The attribution union also
covers **untracked** new product sources, and a `*.swift` that an ignore rule hides under `Exolon/`
reddens the contour instead of vanishing from it. Exit codes: 0 series-green, 1 red, 2 usage,
3 clean-but-partial (`WAVE_SCAN_PARTIAL`, never greppable as the series verdict). Meters of merged
waves stay authoritative standalone; wave_scan is the regression net across rebases. Re-certify the
head in one command with `engineering/changes/20260925-wave-e1-verification-tooling-from-the-a-d-chain-8f7b02/evidence/freeze.sh`.

## Level content contract

- `Exolon/Resources` ships 125 level files describing 101 distinct levels: 23 `L02Sxx≡L05Sxx` pairs plus `L03S09≡L04S11` are duplicate content. Change `f2d90a` **rules** these pairs intentional and pins them in [`engineering/contracts/level-content-v1.json`](engineering/contracts/level-content-v1.json) — no content was authored to dissolve them. The ruling's premise is source-backed for the 23 stage-2→stage-5 pairs (`ORIGINAL_MECHANICS.md:166`, `engineering/reports/exolon-full-audit-20260920-v3.md:37`, `evidence/perfile/level-graph.md:36`, and the imported ASM table in `LEVEL_COMPILER_AUDIT.md`, whose per-screen records are identical for 23 of the 24 pairs); `L03S09≡L04S11` is a stage-3→stage-4 pair that the premise does not reach, and that tension is disclosed in the manifest's `pair_notes`.
- The level factory resolves all 127 `source_marker` objects (11 of 11 distinct `sourceBlock` values, was 76 of 127). "Resolved" is not "implemented": 51 formerly-dropped markers became labeled safe models, 26 more are documented no-op/write-only arms, and only 50 reach gameplay. Content the factory cannot express as a gameplay object is recorded instead of silently dropped.
- Model, canonicalization version, the 0-based `zoneNumber` formula and the regeneration commands: [`engineering/reports/level-content-uniqueness-v1.md`](engineering/reports/level-content-uniqueness-v1.md).
- Status: P1-7 (issue #11) fixed and closed by merged PR #18. P1-12 (issue #16) is resolved **by
  the recorded ruling** and stays open upstream with `blocked-on-owner`: only the owner's
  acceptance closes it.
