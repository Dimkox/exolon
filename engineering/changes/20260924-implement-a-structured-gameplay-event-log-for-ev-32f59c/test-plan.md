# Test plan — wave A

Assertion style: **stream-only predicates** (integration §10) evaluated by
`evidence/gameplay_log_check.py` over JSONL produced by the Linux harness
(`evidence/harness/run.sh`, Swift 6.4, extended shim). Tests assert causal relations, never
absolute ticks (unseeded RNG, 16 sites).

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | P1-9 predicate A: no `player.motion` at the transition's `frame` after `state.zone_transition`; `tick.accumulator_reset` witness; ≤15 motion/frame globally; worst-case scripted frame-gap (x=510 on first step of a clamped 250 ms frame) | `gameplay_log_check.py::p1_9_fixed_passes_and_revert_fails` |
| P0 | P1-8 predicate B: ≤1 `bonus.stage_points` per `completed_zone` per playthrough, ≤5 per playthrough, and **every** stage-end trigger answered (`state.zone_exit` past x=510 at a stage end ⇒ `triggers == awards + suppressions`, so silence fails); the scenario parks the real player past the threshold. Measured: buggy 749 awards + 0 witnesses → fixed 1 award + 748 witnesses (the 2026-09-20 probe reported 750 → 1+524 at its own pacing) | `gameplay_log_check.py::p1_8_fixed_passes_and_revert_fails`, `::forbid_double_stage_bonus` |
| P0 | P1-4 predicate C: after `player.teleport{jump_latch_held:true}`, no `player.jump` until a `pressed:false` jump edge; driven on real `Player.swift` | `gameplay_log_check.py::p1_4_stream_predicate` |
| P1 | P1-6 predicate D: `bonus.double_launcher{launcher_active_after}` + subsequent `entity.launcher_fire` for the same `object_id` in a later zone load | `gameplay_log_check.py::p1_6_stream_predicate` |
| P0 | **Lane truth**: every one of the 44 producer-reachable records is packed by the production helper in `GameplayEventSink.swift` with distinctive values, formatted, parsed back, and compared field by field (`lane-roundtrip.tsv`). This is the class that shipped four wire lies | `gameplay_log_check.py::lane_round_trip_is_exact`, `::producer_sites_use_helpers_only` |
| P1 | Writer health: 0 drops at realtime level-2 session; starved-writer run produces counted visible drops; rotation at tiny `maxFileBytes` links files with `log.rotate` and continues `seq` | `gameplay_log_check.py::session_signal_health`, `::rotation_linkage` |
| P2 | Cost budget: level-2 emission ≤ 5 % of 16.67 ms tick measured in harness | `gameplay_log_check.py::emission_cost_budget` |
| P2 | Build registration: 4 pbxproj marker kinds per new file; single native target + scheme intact | `gameplay_log_check.py::pbxproj_registration_complete`, `::native_target_count` |

## Negative controls (mandatory — the checker must be able to fail)

1. Reverted-fix build FAILS predicates A and B — `EXOLON_REVERT=p1_9|p1_8` passes `false` / `0`
   into the real `FixedTickDriver` and `StageBoundaryLedger` initializers (the same product code, not
   a deleted path; the checker also asserts no product file passes those values). Measured flip:
   14 post-transition steps vs 0; 749-750 awards + 0 witnesses vs 1 award + 748 witnesses.
5. Lane control: each of the four wire lies from `review-code.md` reintroduced in a shadow copy of
   the tree reddens `lane_round_trip_is_exact`; in the working tree, corrupting one decoded field in
   a copy of the stream reddens it too.
6. Assertion-strength controls (encoded inside the checks, from `review-test.md` C1-C6): a deleted
   `player.motion` reddens AC-001; a truncated or `log.end`-less stream reddens INV-001; 744 of 748
   removed suppression witnesses redden AC-003; a leaked `player.jump` with
   `after_teleport:false` reddens AC-004; `String(describing:)` inside `appendRecord` reddens
   INV-004; `func rewind() { tickValue = 0 }` reddens INV-003.
2. Truncated log FAILS seq continuity rather than passing property checks by losing evidence
   (completeness runs inside `stream_invariants` now, not only in a helper).
3. `EXOLON_EVENT_LOG=off` produces NO file (empty file ≠ disabled).
4. Harness "must not build without the CGVector shim" step retained from 2026-09-19 precedent.

## Automated checks

- Unit (Linux, real product files): `FixedTickDriver` (clamp, budget=15, reset discards
  remainder), `StageBoundaryLedger` (once + suppression outcome, playthrough boundary),
  `LauncherBonusState` (pay-once vs active), `Player` latch (reproduction script of §1.1).
- Integration: harness full-loop JSONL → all predicates above.
- Contract: every line validates against `engineering/contracts/schemas/gameplay-event-v1.schema.json`
  (stdlib-only Python validator inside `gameplay_log_check.py`).
- E2E (manual, macOS): play through a teleport + stage boundary + launcher pickup with F1 overlay;
  verify file at `$TMPDIR/exolon/`, heartbeat gaps ≤ 10.5 s, stderr path echo. Recorded in
  `evidence/` after PR build. **Still the only full compile of `GameScene.swift`,
  `TMXLevelRuntime.swift`, `LevelObstacles.swift` and `AppDelegate.swift`**: Linux parses them
  (`touched_swift_files_parse_clean`) and executes their Foundation-only decision types and producer
  helpers, but `-frontend -parse` is not typecheck, so no type error in those four files is
  catchable here.
- Static: `touched_swift_files_parse_clean` runs `swiftc -frontend -parse` over every touched product Swift file (the SpriteKit-bound four included - nothing else compiles them on this host) and carries an injected-garbage control; `python3 scripts/grok_verify.py --mode pr`.
- Posture: `async_writer_healthy` runs the shipped Debug shape (`.asynchronous`: serial queue + drain timer + file writer) at level 2 and requires 0 drops and an empty ring after the barrier; `frame_step_budget` owns SIG-003 (≤15 simulated steps per rendered frame, none straddling a transition).
- Completeness: `stream_invariants` requires `log.end` to be the last record and `events == body records + declared drops` on every stream, so a torn tail cannot pass by losing evidence.

## Manual checks

- macOS `xcodebuild` of the shared scheme (catches what swiftc -parse cannot: link/registration).
- `EXOLON_EVENT_LOG=off` run: no file, no stderr path line, no behavior delta.
- Console spot-check: `tail -f` the path, grep `'"name":"bonus.stage_points"'`.
