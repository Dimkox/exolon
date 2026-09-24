# Tasks — wave A (single write owner: `integration_implementer`)

Ordered; each fix lands with its failing-first regression against the product type it lives in.

1. [x] Contracts first: write `engineering/contracts/schemas/gameplay-event-v1.schema.json`
      (envelope §4, catalog §8 of `analysis-integration_architect.md`, families + reserved,
      `log.begin` fields) — implementer may not rename anything bound there.
2. [x] Linux gate skeleton: `evidence/harness/{run.sh, coregraphics_shim.swift}` — shim = existing
      1-liner + 7-line `CGVector`; step "must not build without shim" kept from 2026-09-19 precedent.
3. [x] `GameplayEventSink.swift` + `GameplayEventLog.swift` (+ Null/memory/file writers, ring,
      counters, modes, drop counter, rotation, flush semantics). Failing test: first-line JSON
      validity check (probe lesson: unquoted `meta`), first tick == 1, ring-overflow counted.
4. [x] `FixedTickDriver.swift`: clamp/accumulate/budget/step + `reset(reason:)` emitting
      `tick.accumulator_reset`. RED: characterization against current GameScene arithmetic (no
      reset). GameScene delegates; `transition()` calls `reset(reason: .zoneTransition)`;
      accumulator never touches `tick`.
5. [x] `StageBoundaryLedger.swift` RED→GREEN: per-playthrough once-per-zone award + suppression
      outcome; GameScene uses it at `applyOriginalStageBoundaryIfNeeded`; terminal path
      (`enterContentComplete`) cannot re-arm it; witness event on every suppression.
      Data-driven award sequence (controller amendment 2026-09-24): components carry their own
      once-keys, so wave D adds bravery/timed without touching this seam.
6. [x] `Player.swift`: `var events: (any GameplayEventSink)?` (nil = exact current behavior);
      latch fix — contextual consume suppresses until release→press edge; emit `player.jump`
      (`after_teleport`), `player.land`, `input.contextual_consumed` (`jump_suppressed`),
      `player.teleport` (`jump_latch_held`). RED = the §1.1 reproduction (already executable).
7. [x] `LauncherBonusState.swift` + `LevelObstacles.swift`/`TMXLevelRuntime.swift`: split
      `active` vs `bonusCollected`; `collectDoubleLauncherBonus` returns `(points, entityID)`;
      emit `bonus.double_launcher{launcher_object_id,launcher_active_after}` and
      `entity.launcher_fire{object_id,x,y}` from the fire gate.
8. [x] Entity identity plumbing: `entityID: UInt16` = ordinal in
      `map.objectGroups.flatMap{$0.objects}` assigned at build (`TMXLevelRuntime.swift:236`).
9. [x] GameScene emission sweep per `analysis-architect.md` §5 table: input-edge snapshot diff,
      `state.flow` didSet (11 sites), weapons, damage choke (`hitPlayer`), pickups, bonuses,
      zone load/exit/transition (`accumulator_us,pending_steps`), checkpoints, death/respawn,
      `score.awarded` (only funnel `awardPoints`), `tick.heartbeat` every 600, level gating.
10. [x] Composition root: env/config → mode+level (`EXOLON_EVENT_LOG`, Debug=1, Release=off);
      inject scene→runtime→player; stderr echo of path once; F1 overlay `view(8)` reused label.
11. [x] pbxproj: 4 edits per new file (PBXBuildFile, PBXFileReference, PBXGroup,
      PBXSourcesBuildPhase); scheme untouched.
12. [x] `GameConstants.swift`: 50 Hz comment → 60 Hz.
13. [x] `evidence/gameplay_log_check.py`: predicates A–D (stream-only), negative controls
      (revert-fix fails A/B; truncated log fails seq continuity; `off` produces no file),
      rotation test (tiny maxFileBytes), INV/FORBID/SIG checks, cost budget check; every
      `test` path named in `change-spec.yaml` exists here (23 checks, all with flipping controls).
14. [x] `decisions.md`: one entry — ring-is-backlog + format/storage rulings with the measured why.
15. [x] Run: `evidence/harness/run.sh`, `python3 evidence/gameplay_log_check.py`,
      `swiftc -frontend -parse` on all changed Swift, `python3 scripts/grok_verify.py --mode pr`.
16. [ ] Do NOT commit/push/PR — controller owns git and receipts.

Blocked-on-owner items intentionally absent: none (all spec gaps ruled in `architecture.md`).

## Review round 1 (code_review BLOCK + test_review FAIL) — fix batch and its evidence

Both reviews were right on their own evidence. Nothing about the four gameplay fixes was shown to be
wrong; the emission layer and the gate's coverage claims were. All of the following is now in the
tree and green (28 checks, `evidence/gameplay_log_check.py`):

### P0 — the four wire lies, and the class that produced them

| Finding | Was | Now |
| --- | --- | --- |
| R1-1 `damage.player_hit` | `events.emit(.damagePlayerHit, packed, x, y, lives)` → the bitfield in the `x` lane, labels `unknown44`/`unknown7` | `events.emitPlayerHit(cause:position:flowBefore:flowAfter:lives:)`; lane order owned by the sink helper |
| R1-2 `damage.player_blocked` | formatter decoded cause/test-invulnerability from the **entity** lane, producer packed lane `c` → every blocked hit read `cause:"bullet"` | formatter reads `record.c`, matching `x-encode`, `schemas[22]` and the helper |
| R1-3 `state.checkpoint_saved` | 7+6+4 = 17 bits in a 16-bit lane: writer put `lives` at bit 12, formatter read bit 13, grenades overflowed (`99,10,3` → `42`/`1`) | `ammo` 0-6, `grenades` 7-11, `lives` 12-15 = exactly 16 bits in pack, formatter, `schemas[38]` and `x-encode` |
| R1-4 `state.restart` | zone passed as a third positional → `points = join(zone, hi)` (1000 pts at zone 0 reported **0**) | `events.emitRunRestarted(discardedPoints:)`; `from_zone` comes from the record's zone lane, as declared |

**Class closure (not four one-liners).** `GameplayEventSink.swift` now carries one named producer
helper per wire name (`emitPlayerHit`, `emitStageBoundaryPoints`, `emitCheckpointSaved`, … 44 of them),
and **no product file may touch lanes**: `producer_sites_use_helpers_only` forbids `events.emit(`,
`GameplayPack.`, `GameplayEvent.lane(`, `GameplayEvent.split(`, `GameplayEvent.q(` and
`Int16(truncatingIfNeeded` in `GameScene.swift`, `Player.swift`, `TMXLevelRuntime.swift`,
`LevelObstacles.swift` and `FixedTickDriver.swift`, requires every non-writer kind to be owned by a
helper, and requires every helper to be called from product code (a dead lane map is a finding).
`lane_round_trip_is_exact` then packs **distinctive** values through those helpers - which the Linux
gate compiles - writes the stream, and compares every payload field against the literal expectations
in `lane-roundtrip.tsv` (49 records, all 44 producer-reachable names; `tick.heartbeat` is asserted
from the stream). Corrupting one decoded field reddens it; a shadow copy of this tree with each of
the four original defects reintroduced reddens it too.

### P1 — coverage root cause

* `touched_swift_files_parse_clean` runs `swiftc -frontend -parse` over every touched product Swift
  file (13 today, including the four SpriteKit-bound ones) and refuses to pass on injected garbage.
  Test review S7 (12 real syntax errors → 22/23 PASS) is now impossible; `test-plan.md`'s promise is
  a gate instead of prose.
* `.asynchronous` - the shipped Debug posture, queue + timer + file writer - is now executed by
  `scenarioAsyncWriter` / `async_writer_healthy`: 15 600 level-2 motions, 0 drops, barrier-empty ring.

### Product defects the new gates found (fixed in this round)

1. **`flush()` was not a barrier.** It ran one `drainNow()` (one batch), so `shutdown()` could write
   `log.end` over 23 232 records still in the ring. It now drains until the ring is empty
   (`drainEverything`), found by the async scenario.
2. **`log.events_dropped.first_seq/last_seq` named seqs that were never issued** (R2-1): the writer
   numbers only surviving records, so a ring lap creates no gap and the old formula invented one.
   The fields are now a real bracket - `last_seq` is the record before the loss, `first_seq` the one
   after this line - and `total_dropped`/`ring_capacity` join them. `_seq_problems`/
   `drops_are_counted` verify both neighbours exist and that this line sits between them; a
   fabricated window reddens the control.
3. **`log.rotate` was the second line of the *new* file** (R2-2), leaving the retired file ending
   mid-stream - indistinguishable from truncation. It is now the last line of the retired
   generation (`GameplayEventWriter.nextFilePath()` exists so the successor can be named before it
   is opened), and `rotation_linkage` fails if it moves, with a control that moves it.
4. **`FixedTickDriver` snapshotted the sink at init** (S-1): a later injection would have logged
   every record except the `tick.*` ones, freezing `tick` at 0 in a non-empty file. The driver is
   created eagerly and `events.didSet` calls `useSink`.
5. Minor contract fidelity: `player.teleport{jump_latch_held}` now reports the *physically held* UP
   (it used to be read after `Player.teleport`, which always sets the latch → constant `true`,
   informationless); `input.contextual_consumed{jump_suppressed}` reports the same suppression
   explicitly; `log.end{reason}` takes the declared enum instead of a free-form string;
   `stats.written` became `stats.events` (it had counted writer-built lines as producer events);
   `minimumLevel` is exhaustive so an appended kind cannot silently inherit level 1;
   `collectDoubleLauncherBonus` returns `DoubleLauncherPayout(points, objectID, launcherActiveAfter)`
   so the witness cannot be skipped by a failed second lookup; the 70/60 s settle delay and the
   x=510 trigger became `GameConstants` names (`deathSettleDelay`, `screenExitX`) because the
   records quote them.

### Test review false-passes, each fixed with the reviewer's own control

| # | Was | Now | Control that must (and does) redden |
| --- | --- | --- | --- |
| R-2 AC-001 | `motion >= len(set(ticks of those same motion records))`: unsatisfiable | the tick denominator is the harness-declared counter; requires `motion == distinct ticks == declared ticks` | deleting one motion record (measured: 1297 vs 1298 → FAIL) |
| R-3 INV-001 | density/monotonic only, a prefix passed while the PASS text claimed continuity | `_seq_problems` runs inside the check over every stream: density, monotonicity, `log.end` present and last, `events == body + declared drops` | half-truncated stream, tail-torn stream, +3 seq jump (all three FAIL; pruned rotation generations exempted) |
| R-4 AC-003 "never silence" | trigger anchor needed `player_x > 2040` but the scenario armed the exit at x=88, so triggers == 0 | the scenario parks the **real player** past the threshold (`placeAtSpawn`, geometry trigger paced per FIRE cycle); `triggers == awards + suppressions` per stream, and the unsatisfiable clause is gone | stripping 744 of 748 witnesses (FAIL), duplicate award (FAIL) |
| R-5 AC-004 | leak detection keyed on the record's own `after_teleport` flag | positional rule only: any `player.jump` between a held-latch teleport and the next `pressed:false` jump edge; the flag stays a payload, asserted separately | a leaked jump with `after_teleport:false` (FAIL - previously green) |
| R-6 AC-005 | "subsequent zone load" never executed | scenario crosses a zone boundary and fires again; check requires ≥1 fire after the load and asserts the harness counter | later-zone count zeroed (FAIL) |
| R-7 INV-003 | `= 0` exemption admitted `tickValue = 0` inside a function | only the two declarations and the two `x = x &+ 1` increments are legal | injected `rewindForNewGame() { tickValue = 0 }` (FAIL) |
| R-7 INV-004 | scanned `emit` and `storeLocked`, skipping `appendRecord` | all four hot-path frames scanned (`emit`, `appendRecord`, `storeLocked`, `beginTick`) | `String(describing:)` inside `appendRecord` (FAIL) |
| AC-006 | reported 54-68 ns but the gate band was 0.5-1000 ns | checker asserts the spec 5 % **and** a 0.5 % alarm margin; harness asserts its own margin | - |
| R-8 | every run rewrote `evidence/harness/last-run.txt` (a tree write, colliding between reviewers) | transcript goes beside the artifacts; `--record` opts into the in-tree copy, via `_write_if_changed` | - |
| R-9 | SIG-001/002/003 had no symbols; `observability[]` has no `evidence` field in this spec schema, so nothing binds them | symbols now exist (`session_signal_health`, `kill_switch_no_file`, `frame_step_budget`) and SIG-001 reads the 36 000-tick stream; **binding limitation**: `schemas/change-spec.schema.json` gives `evidence[]` only to AC/INV/FORBID, so SIG rows stay unbound at the receipt level - a factory gap, not a wave-A one; SIG-003 additionally stays asserted inline inside `predicate_a` |
| R-11 | predicate B's component whitelist was ahead of the schema | per-component rules come from `x-code-tables.stage_component_id`; an undeclared id is a failure and the extension rule is stated in the schema | renumber/whitelist drift (FAIL) |

### Gate re-run after this round

See `## Measured outcome` below; the artifact-mutation and shadow-source controls used by the two
reviews are encoded as in-check controls, so the next reviewer does not have to rebuild them.


## Measured outcome of task 15 (final fingerprint)

| Command | Result |
| --- | --- |
| `evidence/harness/run.sh` (3 variants + no-shim control) | `HARNESS OK scenarios=13` ×3 variants, `OK: без стаба не собирается`, exit 0 |
| `python3 evidence/gameplay_log_check.py` (builds + runs the harness itself: 13 scenarios x 3 variants) | `RESULT: PASS (28/28 checks passed)`, ~2 min |
| hot-path cost (AC-006) | 54–68 ns/event ⇒ **0.019–0.025 %** of a 16.67 ms tick at 60 ev/step (budget 5 %, design target 0.025 %); formatting-per-event control ≈1.1 µs (≈20×); drain ≈297 000 ev/s (82× the worst credible realtime rate) |
| P1-9 control pair | fixed: 0 steps in the transition frame, witness `233333 µs / 14 steps`; reverted driver: 14 steps after the transition ⇒ predicate A **fails** as required |
| P1-8 control pair (real geometry: player parked past x=510) | fixed: 1 award + 748 `bonus.stage_boundary_suppressed` answering 749 triggers; reverted ledger: 749-750 awards + 0 witnesses ⇒ predicate B **fails** as required |
| P1-6 later-zone clause | 20 shots in the payout zone + 20 after a real zone load, same `object_id`; pre-fix control fails predicate D |
| Drops (FORBID-004) | mid-stream lap: 812 of 5 308 written, 4 496 counted, window bracketed by seqs 300 and 302 that both exist |
| Shipped Debug posture | `.asynchronous` queue + timer + file writer: 15 600 motions, 2 heartbeats, 0 drops, ring empty after the barrier |
| P1-4 | 1 `player.teleport{jump_latch_held:true}`, 0 `player.jump` before the release edge, 1 legitimate jump after release→re-press; a hand-written violation stream **fails** predicate C |
| P1-6 | fixed: `launcher_active_after:true` + 40 later `entity.launcher_fire` for the same `object_id`; pre-fix single-flag control **fails** predicate D |
| `swiftc -frontend -parse`, every touched product file (13, incl. the 4 SpriteKit-bound ones) | clean - and now a *gate* (`touched_swift_files_parse_clean`, with an injected-garbage control) |
| Linux `-typecheck` of the real product subset (4 product + 5 Diagnostics files) + the 42 producer helpers | clean, zero warnings |
| Mechanical signature audit of every `events.emitX(...)` call in the non-typecheckable files | 42 helpers, 0 label/arity mismatches |
| Shadow-copy control: each review-found defect reintroduced, then the full 28-check suite re-run | every one reddens (table below) |
| `python3 scripts/grok_verify.py --mode pr` | see the verification receipt (recorded after the last tree write) |

### Shadow controls executed after the fix round (mutation -> what reddened)

| Reintroduced defect (in `/tmp/shadow-lanes*`, never in the working tree) | Reddened |
| --- | --- |
| R1-1 call site passes the packed lane as `x` | `producer_sites_use_helpers_only` (raw `events.emit(` banned at call sites) |
| R1-1 decoder reads the packed lane as `x` | `lane_round_trip_is_exact` (`damage.player_hit.x: wire '1607' != packed input '2043'`), `envelope_schema_valid`, `forbid_wallclock_fields` |
| R1-2 formatter decodes `damage.player_blocked` from the entity lane | `lane_round_trip_is_exact` (`cause: 'bullet' != 'force_field'`, `test_invulnerability: false != true`) |
| R1-3 formatter reads `lives` at bit 13 | `lane_round_trip_is_exact` (`state.checkpoint_saved.lives: '1' != '3'`) |
| R1-4 extra positional lane at the `state.restart` call site | `producer_sites_use_helpers_only` |
| R1-4 decoder reads the shifted i32 pair | `lane_round_trip_is_exact` (`points: '-499122176' != '123456'`) + `envelope_schema_valid` minimum |
| `String(describing:)` inside `appendRecord` (hot-path middle frame) | harness cost band (`60 locked appends ... got 5106 ns`) and `hot_path_is_allocation_free` |
| Pre-fix fabricated `log.events_dropped` window (`nextSeq - count`) | `drops_are_counted` + `stream_invariants` (`drop record at seq 301 does not sit between 0 and 302`) |
| `log.rotate` moved out of the retired file | `rotation_linkage` + `stream_invariants` |
| Artifact copies: one `player.motion` deleted / stream truncated / `log.end` torn off / 744 witnesses stripped / duplicate award / leak without `after_teleport` / corrupt decoded field / stripped async motions | `harness_level2_complete`, `stream_invariants`, `p1_8_*`, `forbid_double_stage_bonus`, `p1_4_*`, `lane_round_trip_is_exact`, `async_writer_healthy` respectively |

## Deviations (bounded, all inside the owned scope; no contract identifier renamed)

1. **Record lanes.** The architect §4 sketch (`tick: UInt64` + 4×Int16) has no lane for `frame`,
   which the frozen envelope (integration §4) requires on every line. `tick` and `frame` are
   `UInt32` (UInt32 tick = 2 271 years at 60 Hz); `MemoryLayout<GameplayEvent>.stride == 24` is
   asserted by the harness, the four Int16 payload lanes survive, and 32-bit contract values
   (`*_i32` in `x-encode`) occupy a lane pair. Zone/family/`next_level`/`resource` strings are
   derived from the record's zone lane by the formatter, so no string ever crosses the producer path.
2. **Family set vs catalog names.** Integration §3 closes the families at
   `meta,input,player,damage,bonus,state,tick` (+reserved `bullet,entity,pickup,hud`) while the §8
   catalog it also freezes emits `pickup.collect`, `entity.launcher_fire`, `game.game_over`,
   `score.*` and `log.*`. Renaming a frozen name would be a `schema_version` bump, so the names are
   kept verbatim and the schema's `x-families` records the eleven active prefixes plus the reason.
3. **No raw comment line in a JSON-lines file.** AC-001 requires every line to parse with
   `json.loads`, so the architect's `# exolon-events v1 …` header and `# dropped N` marker are the
   `log.begin` record and the `marker` field of `log.events_dropped` (`"# dropped N oldest events
   (writer behind)"`), which keeps the grep-able text inside valid JSON.
4. **`tick.accumulator_reset` predicate form.** Integration §10-A literally asserts
   `discarded_steps == 0 || discarded_us < 16667`; ruling 4 (discard the remainder) makes that
   unsatisfiable in exactly the frame the fix targets (it discards up to 14 steps). The checker
   implements what the typed authority AC-002 words - "consistent `discarded_us`" - as
   `|discarded_us − discarded_steps·16667| ≤ 16667` and `discarded_steps ≤ 15`. The primary clause
   (no `player.motion` after the transition inside its frame) is unchanged and is what flips.
5. **Playthrough boundary for predicate B.** §10-B writes `restart/title_enter → game_over/title_enter`,
   but the zone-124 farm reaches the title screen carrying the same score/lives/position, so
   splitting on any title visit declares each farm cycle a fresh playthrough and predicate B passes
   on the defect (the probe itself measured 1 award + 524 witnesses, not 150 awards). Boundary =
   where the state is re-initialised: `game.game_over`, `state.restart`, or
   `state.title_enter{has_saved_checkpoint:false}`. Documented in `playthroughs()` and in
   `StageBoundaryLedger`'s doc comment.
6. **P1-4 mechanism.** The scene's one-step `jump:false` mask was itself the leak vector (Player
   re-sampled the physical button on the next step, README:23's promise notwithstanding). The hold
   moved into `Player` (`contextHoldsJumpLatch`, released only by an observed key-up) and the mask
   is gone. The consuming step keeps its old behavior because the latch is armed before
   `player.update`. `p1_4_stream_predicate` pins the guard textually as well as by stream.
7. **`collectDoubleLauncherBonus` API.** Returns `(points: Int, entityID: UInt16)` (was `Int`).
   One in-module caller; required by AC-005 so `bonus.double_launcher` can name the launcher and be
   joined to its `entity.launcher_fire` records.
8. **One new mandatory name: `bonus.stage_component`.** Controller amendment 2026-09-24: the award
   sequence is a list of components with their own once-keys. The frozen total name
   `bonus.stage_points` keeps its payload; the components ride alongside it (same tick +
   `completed_zone`) so wave D's bravery/timed components extend the identity without a rename, a
   new GameScene seam or new witness plumbing. Wave A implements exactly `lives_x1000`.
9. **Predicate B's sum cap replaced** by the component identity (`points == sum(components)` and
   each known component against its own rule), per the same amendment: the `≤ 5 × lives_cap_bonus`
   bound in the analysis text becomes false under correct P1-10. The counts and mandatory-witness
   clauses of AC-003/FORBID-001 are unchanged.
10. **Duration encodings.** Values that are exact multiples of a fixed step
    (`invulnerability_us` on `state.zone_loaded`, `player.death_settled.delay_us`/`invulnerability_us`,
    `input.action_edge.held_us`) travel as step/millisecond counts and are rendered with the same
    `round(n·1e6/60)` derivation as `ts_us`; arbitrary durations (`discarded_us`, `accumulator_us`,
    `raw_frame_time_us`, `damage.player_blocked.invulnerability_us`) travel as exact µs in an i32
    pair. Both forms are declared per field in the schema (`x-unit`, `x-encode`).
    `clamp_us`/`budget_us` are constants of `GameConstants` and are emitted by the formatter, which
    pins them with an `enum` in the schema so a change cannot pass silently.
11. **Harness-side witness emission.** `player.motion`, `player.teleport`, `state.zone_transition`,
    `state.zone_*` and `input.action_edge` are emitted by `GameScene`/`TMXLevelRuntime`, which are
    SpriteKit-bound and cannot be Linux-compiled; the harness's `Loop` reproduces those emission
    calls and reads every payload value from real product getters (`player.jumpLatchHeld`,
    `player.position/velocity/motionState`, `driver.accumulatorMicroseconds/pendingSteps`,
    `LauncherBonusState`, `StageBoundaryLedger`). SpriteKit is not shimmed (integration §1). The
    scene wiring is additionally pinned by source assertions inside
    `p1_9_fixed_passes_and_revert_fails` / `p1_8_fixed_passes_and_revert_fails` / `p1_4_*`.
12. **Rotation granularity and meta stamps.** Rotation is decided per batch, before the batch is
    numbered, because `seq` is assigned as lines are built and a header written mid-batch would
    carry a higher `seq` than the records it precedes (observed in the first p1-8 run). A file
    therefore stops at 8 MiB plus at most one batch (≤ 110 KB at the shipped batch size). Meta
    records (`log.begin`, `log.rotate`, `log.events_dropped`) take their envelope `tick`/`frame`
    from the batch that follows them so INV-001's non-decreasing rule holds.
13. **`state.checkpoint_cleared{reason:"launch"}`** is emitted from `didMove` (the test-build policy
    there clears the checkpoint) rather than from inside `GamePersistence`, which has no sink.
14. **`damage.player_blocked` scope.** Emitted at the `hitPlayer` choke (test-invulnerability and
    invulnerability/dying guards), not at every inline `invulnerability <= 0` guard in
    `updateLethalEntities`, and not for the exoskeleton `continue` on mines/pistons: those would be
    per-frame records while the player merely stands next to a piston (INV-003).
15. **`Player.setExoskeleton` no-ops when the value is unchanged**, so `player.exoskeleton` cannot
    duplicate a record without a state change. Gameplay-identical (assigning the same Bool).
16. **`InputState` gained `source(for:)`.** `input.action_edge{source}` is a frozen field and the
    merged `snapshot()` cannot answer it; attribution is recorded where the press arrives (the
    input thread) and read once per emitted edge - a few per second, never per frame.
17. **P1-9 widened to `restartFromBeginning`** (`tick.accumulator_reset{reason:"new_game"}`):
    repo_explorer §8-4 names it as the same defect class (a level swap inside a rendered frame), and
    the frozen reason vocabulary already declares `new_game`.
18. **No P1-4 revert knob.** AC-002/AC-003 require fix-reverted controls and have them
    (`resetAccumulatorOnZoneTransition: false`, `awardsPerComponentPerZone: 0`, both rejected from
    product code by source assertion). AC-004 requires none, so `Player` got no bug re-introduction
    switch; predicate C is instead proven decidable against a stream the harness writes directly in
    the forbidden shape.
19. **P1-6 identity of the `str`-typed ids.** `launcher_object_id` / `object_id` are the decimal
    string of the TMX object ordinal (the record's `entity` lane), which keeps §8's declared `str`
    type without putting a string on the producer path.
20. **The `EXOLON_EVENT_LOG=<path>` form** is a directory override (level stays the build default,
    `off`/`0`/`1`/`2` are the other three accepted values), per release.md's "custom file prefix".

### Reviewer-facing commands

```bash
# builds the gate, runs 13 scenarios x3 variants (fixed, EXOLON_REVERT=p1_9, EXOLON_REVERT=p1_8)
python3 engineering/changes/20260924-implement-a-structured-gameplay-event-log-for-ev-32f59c/evidence/gameplay_log_check.py
# reuse an existing artifact directory instead of rebuilding
... gameplay_log_check.py --artifacts /tmp/exolon-harness-XXXX/artifacts [--only name,name] [--record]
python3 engineering/changes/20260924-implement-a-structured-gameplay-event-log-for-ev-32f59c/evidence/harness/run.sh | tail -20
```
