# Analysis — integration_architect: gameplay event-log CONTRACT (frozen from the consumer side)

- Route: `32f59cc7dcb6` · change `20260924-implement-a-structured-gameplay-event-log-for-ev-32f59c`
- Baseline: `295690b7fc724e57b37b5fac86b71c1da7d8b032` · fingerprint `c2f0ebf799a2a474000b20e124b39de5169456b9ce46608221b7ef309b493b62`
- Role: read-only over the product tree; this file is the only write.
- Question answered only: **the shape of the event stream** (naming, catalog, payload, ordering, retention) and how each of the three consumers reads it. Implementation ownership stays with `integration_implementer`.

## 0. Method / evidence base

Read: `Exolon/GameCore/GameScene.swift` (1131 L), `Player/Player.swift`, `InputState.swift`,
`GameState.swift`, `GameConstants.swift`, `Levels/TMXLevelRuntime.swift`,
`Objects/LevelObstacles.swift`, `Platform/macOS/GameView.swift`, `main.swift`,
`Exolon.xcodeproj/project.pbxproj`, `.gitignore`, the 2026-09-19 loader harness
(`engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/harness/`),
and the audit rows for P1-4 / P1-6 / P1-8 / P1-9 in `engineering/reports/exolon-full-audit-20260920-v3.md:29-34`.

Built a throwaway executable probe in `/tmp/evlog-probe/` (nothing written into the repo):
verbatim copies of `GameConstants.swift` + `InputState.swift` + `Player.swift`, the harness
`CoreGraphics` shim, a fixed-step loop that is a line-for-line copy of
`GameScene.update` (`GameScene.swift:50-51,123-141`), plus the two audited seams
(`checkScreenExit`/`applyOriginalStageBoundaryIfNeeded`/`transition` at
`GameScene.swift:609-660`). It writes JSON-lines and a checker `check.py` reads the stream
back. All measurements below are from that probe run on this host
(`swiftc` = Swift 6.4, `swift-6.4-RELEASE`, `x86_64-unknown-linux-gnu`; Python 3.12.3; 22 logical CPUs).

## 1. The blocking structural fact (decides everything else)

**There is no Swift test target and `GameScene` cannot compile headless today.**

- `grep -o 'com.apple.product-type[a-z.-]*' Exolon.xcodeproj/project.pbxproj` → exactly one
  hit: `com.apple.product-type.application`. 0 unit-test targets; one shared scheme
  (`Exolon.xcodeproj/xcshareddata/xcschemes/Exolon.xcscheme`).
- Import graph (`grep -n "^import"`): SpriteKit-free = `Player.swift`, `InputState.swift`,
  `GameConstants.swift`, `GameState.swift`, `TMXMapLoader.swift`. Everything that owns the
  tick loop or the entities under audit (`GameScene`, `TMXLevelRuntime`, `LevelObstacles`,
  `BlasterBullet`, `Grenade`, `HUDNode`, `ExplosionEffect`, `PlayerSpriteNode`,
  `TMXTileMapRenderer`) imports **SpriteKit**.
- The existing 2026-09-19 harness proves the opposite direction on purpose and says so
  (`harness/README.md`: «`Player`/`GameScene` и любой код, зависящий от SpriteKit, в контур
  не входит») and refuses to run on macOS with `rc=75`.
- Shim gap measured: the harness 1-line shim (`@_exported import Foundation`) is **not**
  enough for `Player.swift` — Linux Foundation has no `CGVector`
  (`Player.swift:21,210,222`). Probe error count before the fix: 4. After adding a
  7-line `CGVector` (dx/dy/zero) the player physics compiled and ran clean.

**Contract consequence (mandatory):** the emitter must be a protocol with a SpriteKit-free
implementation, and every event must be produced by code reachable without an `SKScene`.
Concretely the log call sites must live behind an object the headless harness can
instantiate — a `GameEventSink` (`func emit(_ event: GameEvent)`) injected into the
gameplay code, with a file sink (product), an in-memory array sink (tests) and a
no-op sink (release). If the log is emitted only from `GameScene`, the Swift regression
tests can only exist as an Xcode test target on macOS — a second, larger change — and the
wave-A findings stay unmeasurable on Linux. Do not shim SpriteKit: `SKAction`, `SKTexture`,
`SKShapeNode` and the renderer are not reproducible cheaply, and a fake SpriteKit would let
a test pass on a fiction.

## 2. Consumer requirements → what each one forbids

| Consumer | Needs | Rules this imposes |
| --- | --- | --- |
| Swift headless regression tests (Linux, `swiftc` + shim, harness pattern of `run.sh`) | deterministic ordering, in-memory sink, byte-for-byte stable lines, exit codes | no wall-clock ordering key; no allocation-per-frame requirement that only exists in the SpriteKit path; ordering keys must be integers a test can compare |
| Python "измерители" (offline, `scripts/` or `engineering/`) | stdlib-only parsing, one record per line, a machine-readable schema version, stable enum spellings | flat records, no nesting beyond one level, snake_case keys, no locale-dependent number formatting |
| Human debugging in-game / in terminal | grep-able, `tail -f`-able, self-describing line, path printed at start | `name=`-style flat keys, integers for time, one file per run, no binary framing, no compression while running |

All three are satisfied by the same format only if the envelope is identical on **every**
line, including the first (the probe's first version emitted a richer header line without
`frame`, and the Python consumer died on it — see §7 rule 1).

## 3. Naming and versioning

- Stream identity: `schema_version` = `1` (integer, every line) + `schema` =
  `"exolon.gameplay.v1"` (string, `log.begin` only). Bump the integer **only** for a
  breaking change; adding an optional payload field is non-breaking and does not bump it;
  renaming/removing a field or changing its type does. A consumer must
  `reject` an unknown major version rather than mis-read it.
- Event names: `<family>.<object>_<verb>` — lowercase ASCII, one `.` separator, `_` inside
  a word, `[a-z][a-z0-9_]*` per segment, ≤ 40 chars total. Names are **stable identifiers**,
  so they must never carry a numeric argument that belongs in the payload
  (✅ `bonus.stage_points`, ❌ `bonus.stage24_points`).
- Families (closed set): `meta`, `input`, `player`, `bullet`, `entity`, `pickup`, `damage`,
  `bonus`, `state`, `tick`, `hud`. Wave A only requires `meta`, `input`, `player`, `damage`,
  `bonus`, `state`, `tick` — the rest are reserved so a later wave does not have to
  rename (a rename is a breaking change).
- Field names: lowercase `snake_case`, ≤ 24 chars, never abbreviated to the point of
  ambiguity (`completed_zone`, not `cz`). Every field name is also a stable identifier.
- Enum values are spelled exactly as the existing Swift enum raw values wherever one
  exists (`GameFlowState.rawValue`: `title|playing|paused|playerDead|respawning|gameOver|contentComplete`,
  `GameState.swift:3-11`) — do not invent a second vocabulary; `flow_state` in the payload
  is literally that string.

## 4. Envelope (every line, same order)

Order of keys is normative so a byte-level test can compare whole lines:
`schema_version, seq, tick, frame, rot, ts_us, name, …payload`.

| Field | Type | Meaning / origin |
| --- | --- | --- |
| `schema_version` | int | §3. Always `1`. |
| `seq` | int ≥ 0 | event ordinal, strictly `+1` per line, **never reset inside a run**. Proof of total order; a gap is lost data. |
| `tick` | int ≥ 0 | fixed-step index (§5). 0 for pre-loop records. |
| `frame` | int ≥ 0 | `SKScene.update` render-frame index, 0 for pre-loop records. The only key that makes P1-9 visible. |
| `rot` | int ≥ 0 | rotation index within the run (§7). 0 for the first file. |
| `ts_us` | int ≥ 0 | **simulation** time, µs, derived: `ts_us = round(tick * 1_000_000 / 60)`. Never a wall clock. |
| `name` | string | §3. |

`log.begin` (the first line of every file, `seq`-bearing, envelope-complete) additionally
carries: `run_id` (string, 8-32 hex, generated once per process), `build` (string,
CFBundleShortVersion+CFBundleVersion or `harness`), `wall_utc` (string, RFC 3339 UTC with
ms, e.g. `2026-09-24T19:10:39.412Z` — the only wall-clock field in the contract, for human
correlation only), `level` (int, §6), `path` (string, absolute file path), `seed`
(string, RNG seed if the run pins one, else `"nondeterministic"`), `zone` (int, 0),
`flow_state` (string). `log.end` carries `reason`
(`app_quit|error|harness_complete`) and `events` (int, total emitted).

Why `tick` **and** `frame` and `seq`: they are three different clocks and the wave-A bugs
live exactly in the gaps between them. `tick` counts simulated steps (the physics truth),
`frame` counts `update()` calls (the display truth), `seq` counts emitted records (the log
truth). P1-9 is invisible if you keep only one or two of them.

## 5. Tick numbering origin

- `fixedTimeStep = 1/60` and `maximumFrameTime = 0.25` (`GameConstants.swift:13-14`), so the
  per-frame step budget is `floor(0.25 / (1/60)) = 15` (probe printed `budget=15`).
- **`tick = 0` is reserved** for everything emitted before the first fixed step: bootstrap
  (`didMove(to:)`, `GameScene.swift:55-121`), `log.begin`, title-screen and pause-screen
  records. **`tick = N ≥ 1` is the N-th completed `fixedUpdate(dt:)` invocation** since the
  process started, counted *before* the loop at `GameScene.swift:131-135` runs it. The
  counter is never reset by a zone transition, a death, a restart, `beginFromTitle` or
  `showTitleAfterContentComplete` — it is process-global, not level-local.
- `frame = 0` is the first `update(_:)` call that returns early because
  `previousUpdateTime == 0` (`GameScene.swift:124-127`); `frame` increments once per
  `update(_:)` entry after that. The first simulated tick therefore has `frame ≥ 1`.
- `ts_us` must be derived from `tick`, not measured, so two runs of the same scripted input
  produce byte-identical `ts_us`. Do **not** accumulate the rounded constant `16667` µs per
  tick — that formula was in the probe's first version and it drifts `+12 000 µs (12 ms)` by
  tick 36 000 (`36 000 × 16 667 = 600 012 000` vs the true `600 000 000`), which a
  long-session auditor would read as the simulation running slow. Use
  `ts_us = round(tick * 1_000_000 / 60)`, computed from `tick` each time, never accumulated.
- Real elapsed time is not free: it belongs only in anomaly payloads
  (`raw_frame_time_us`, `discarded_us`), because those fields *are* about the difference
  between simulated and real time.

## 6. Emission levels

`level` in `log.begin` selects what is emitted; it is a property of the run, not of a line.

| level | Contents | Use |
| --- | --- | --- |
| 0 | `meta`, `state.*`, `tick.*` anomalies | release default candidate |
| 1 | + `input.*` edges, `player.*` actions, `damage.*`, `bonus.*`, `pickup.*` | **shipped default for a debug build; sufficient for three of the four wave-A assertions** |
| 2 | + `player.motion` every tick, entity per-tick state | **required default for regression tests** (the only way to count ticks per zone/frame) |

Rationale for levels instead of "always on": the probe measured the per-tick motion event at
175 B and 52.6 % of all bytes; a frame-heartbeat event would have added another 44.2 %. The
per-tick sampling must be opt-in and opt-out at one place, not per call site.

## 7. Serialization: JSON-lines, one object per line — decided, with the numbers

Measured on the probe's 74 626-event run (600 s of simulated play):

| Metric | JSON-lines | flat `key=value` | verdict |
| --- | --- | --- | --- |
| size | 11 980 125 B | 9 977 581 B | KV 17 % smaller |
| Python parse (stdlib) | 181 856 ev/s | 274 951 ev/s | KV 1.5× faster |
| realtime emission need | ~124 ev/s | ~124 ev/s | both >1 400× headroom |
| `grep -c '"name":"bonus.stage_points"'` on 12 MB | 9 ms | 9 ms | tie |
| stdlib validation of the record | `json.loads` free | hand-rolled splitter, no type check | JSON |
| nested payload (rect, vector) | native | needs a sub-format, becomes the worst of both | JSON |

**Decision: JSON-lines.** The only advantage of KV is 17 % bytes and a 1.5× parsing margin
against a consumer that is already 1 400× faster than the producer — while the cost of KV is
a bespoke parser whose idea of a value is a string (the probe KV writer had to invent
space→`_` escaping to stay split-able, which is exactly how "readable" logs rot). JSON also
gives one enforceable artifact: a JSON Schema file in `engineering/contracts/schemas/` that
both the Swift writer and the Python auditor can be tested against.

Hard rules, because hand-built JSON breaks silently:
1. Every value must be a JSON literal. The probe's own first version wrote
   `"kind":meta` (unquoted) in the header: the file was otherwise fine and the Swift side
   never noticed, but the Python consumer aborted on **line 1** (`json.decoder.JSONDecodeError:
   Expecting value: line 1 column 28`) before reading a single event. **Use `JSONEncoder`
   with per-event dictionaries, or a formatter whose only output path quotes values;
   never `"\(rawString)"`.**
2. One line = one object, `\n` terminated, UTF-8, no BOM, no trailing whitespace.
3. Field order as in §4 (byte-stable lines let a Swift test compare whole lines).
4. Floats: `%.3f` for positions/velocities (the current motion is exact at 3 decimals:
   90 px/s ÷ 60 = 1.5 px/tick), fixed-point only — no `String(Double)` (locale/shortest-form
   instability). Integers stay integers, never `1.0`.
5. No key may be null; omit the key instead. Consumers must ignore unknown keys (that is
   what makes adding a field non-breaking).
6. Coordinates are the existing scene space: 512×384 logical, bottom-left origin, y up
   (`GameConstants.swift:6`, `GameScene.swift:57`), with the documented motion range
   `x ∈ [24, 544]` (the player is clamped to `logicalSize.width + 32`,
   `Player.swift:128`; the probe reached `x=544.000`).

Rotation and retention (measured, not guessed):
- Volume at level 2 with per-tick motion and **no** per-frame heartbeat: 185.7 B/tick →
  **11.1 KB/s → ~40.1 MB per hour** of continuous play.
- Volume at level 1 (state/actions/bonus only): the probe's non-motion residue is
  378 184 B over 600 s → **0.63 KB/s → ~1.1 MB/hour** for this scenario; allow ~5 MB/hour
  once turret/explosion/pickup traffic is included (estimate, flagged in §11).
- Emit cost, whole probe: 1.214 s for 4 runs, 148 505 events and 72 000 simulated steps →
  **≈ 8.2 µs per event end-to-end** (format + buffered write + physics), i.e. 0.05 % of one
  16.67 ms tick. The requirement "cheap" is met by buffering, not by skipping events.
- **Policy:** buffer 64 KiB, flush at a `tick % 60 == 0` boundary and on every
  `state.*`/`damage.*`/`bonus.*`/`tick.*` record; rotate at **8 MiB per file**, keep
  **8 files** (64 MiB cap), then **stop writing** (never delete the current run's head).
  On rotate: write `log.rotate{from_path,to_path,rot,rotated_at_tick}`, continue `seq`.
  A drop must be visible: `log.events_dropped{count,first_seq,last_seq}` — and the drop
  counter must exist so a test can assert it is zero rather than infer silence.
- **Location: never inside the repository working tree.** `.gitignore` covers `*.log.tmp`
  only, and the fingerprint filter treats untracked files as tree changes
  (`.gitignore` header comment, upstream #168) — a log written under the clone would
  invalidate every fingerprint-bound receipt in this route. Default path:
  `URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("exolon/gameplay-\(run_id)-\(rot).jsonl")`;
  no entitlements/sandbox file exists in this target (`find . -name "*.entitlements"` → 0
  hits), so a plain file write is available. Override with `EXOLON_EVENT_LOG=<path>`;
  `EXOLON_EVENT_LOG=off` disables emission (release default candidate).
  The path must be echoed to stderr once at start so a human knows what to `tail -f`.

## 8. Event catalog for wave-A debuggability

Payload column lists fields **beyond** the envelope. Types: `int`, `float3` (3-decimal
fixed), `bool`, `str`, `rect{x,y,w,h:float3}`, `vec{dx,dy:float3}`, `zone=int 0…124`
(the 0-based convention already in `GameState.swift:90-91` and `zoneNumber(for:)`,
`GameScene.swift:988-996`).

### meta
| name | payload | trigger |
| --- | --- | --- |
| `log.begin` | §4 | first line of every file |
| `log.rotate` | `from_path:str`, `to_path:str`, `rotated_at_tick:int` | size rotation |
| `log.events_dropped` | `count:int`, `first_seq:int`, `last_seq:int` | buffer overrun / write error |
| `log.end` | `reason:str`, `events:int` | teardown |

### input (edge-only; ≤ a few per second)
| name | payload | trigger |
| --- | --- | --- |
| `input.action_edge` | `action:str(moveLeft,moveRight,jump,crouch,fire,grenade,pause,menuUp,menuDown,debugHitboxes — the `GameAction` cases)`, `pressed:bool`, `source:str(keyboard,gamepadDPad,gamepadStick,gamepadButtons)`, `held_us:int` | `InputState.set` (`InputState.swift:37-51`); `source` comes from the caller |
| `input.pause_consumed` | `pending:bool` | `consumePausePress()` returns true (`InputState.swift:75-81`) |
| `input.contextual_consumed` | `kind:str(changing_room,teleport)`, `jump_suppressed:bool` | `consumeContextualJumpPress()` site, `GameScene.swift:234-250` — **this is the P1-4 witness** |

### player (actions; `player.motion` only at level 2)
| name | payload | trigger |
| --- | --- | --- |
| `player.motion` | `zone:zone`, `x:float3`, `y:float3`, `vx:float3`, `vy:float3`, `grounded:bool`, `motion_state:str(idle,running,jumping,falling,crouching,dying)`, `facing:str(left,right)`, `exoskeleton:bool` | once per `fixedUpdate` for level 2 |
| `player.jump` | `x:float3`, `y:float3`, `velocity:float3(=165)`, `grounded_before:bool`, `after_teleport:bool` | `Player.update` jump latch fires (`Player.swift:110-115`) |
| `player.land` | `x`, `y`, `vy_before:float3`, `support:str(fallback_floor,solid)` | `landOnFallbackFloorIfNeeded` / `resolveSolidCollision` top branch |
| `player.crouch_begin` / `player.crouch_end` | `x`, `y` | `motionState` edge |
| `player.exoskeleton` | `enabled:bool`, `cause:str(changing_room,cheat,reset)` | `toggleExoskeleton` (`Player.swift:243`), `setExoskeleton` |
| `player.shoot_blaster` | `origin:rect→x,y`, `facing`, `double:bool`, `ammo_before:int`, `ammo_after:int` | `updateWeapons` (`GameScene.swift:338-368`) |
| `player.shoot_denied` | `reason:str(no_ammo)`, `ammo:int` | same guard |
| `player.throw_grenade` | `origin`, `direction`, `grenades_before:int`, `grenades_after:int`, `blocked_by:bool(one_in_flight)` | `GameScene.swift:355-363` |
| `player.teleport` | `from:vec`, `to:vec`, `portal_index:int`, `jump_latch_held:bool` | `GameScene.swift:239-245` + `Player.teleport` (`Player.swift:207-214`) — **P1-4 witness** |

### damage / death
| name | payload | trigger |
| --- | --- | --- |
| `damage.player_blocked` | `cause:str(bullet,mine,piston,force_field,source_hazard,bubble,egg,missile)`, `invulnerability_us:int`, `test_invulnerability:bool` | any guard that swallowed a hit (`GameScene.swift:601-607`, `522-599`) |
| `damage.player_hit` | `cause`, `x`, `y`, `flow_state_before:str`, `flow_state_after:str`, `lives:int` | `hitPlayer()` (`GameScene.swift:601-608`) |
| `player.death_begin` | `x`, `y`, `lives:int`, `ammo:int`, `grenades:int` | `beginDeath` |
| `player.death_landed` | `x`, `y`, `ground_ticks:int` | `updateDeathSequence` grounded branch |
| `player.death_settled` | `delay_us:int(=70 * 16_667)`, `lives_before:int`, `lives_after:int`, `invulnerability_us:int(=400_000)`, `checkpoint_saved:bool` | `GameScene.swift:311-336` |
| `game.game_over` | `points:int`, `high_score:int`, `zone:zone`, `checkpoint_cleared:bool` | `enterGameOver` (`GameScene.swift:719-737`) |

### pickup / bonus
| name | payload | trigger |
| --- | --- | --- |
| `pickup.collect` | `kind:str(grenade_pack,ammo_pack)`, `count_before:int`, `count_after:int`(99/10 semantics), `x`, `y` | `updatePickups` (`GameScene.swift:522-538`) |
| `bonus.double_launcher` | `points:int(1000)`, `completed_zone:zone`, `launcher_object_id:str`, `x`, `y`, `launcher_active_after:bool` | `collectDoubleLauncherBonus` (`GameScene.swift:300-302`, `TMXLevelRuntime.swift:219-224`, `LevelObstacles.swift:716-722`) — **P1-6 witness** |
| `bonus.stage_points` | `completed_zone:zone`, `points:int`, `lives_before:int`, `lives_after:int`, `ammo_reset:bool` | `applyOriginalStageBoundaryIfNeeded` (`GameScene.swift:622-631`) — **P1-8 witness** |
| `bonus.stage_boundary_suppressed` | `completed_zone:zone`, `reason:str(already_awarded,not_stage_end)` | the guard added by the P1-8 fix; must be *observable*, not silent |
| `score.awarded` | `points:int`, `reason:str(blaster_shotdown,bubble,egg,force_field,grenade_kill,guidance,launcher,stage_boundary)`, `points_before:int`, `points_after:int`, `clamped:bool(999_999)` | `awardPoints` (`GameScene.swift:660-667`) |
| `score.high_score_saved` | `value:int` | persistence write |

### state
| name | payload | trigger |
| --- | --- | --- |
| `state.flow` | `from:str`, `to:str`, `cause:str(fire_press,pause_press,resume,restart,death,respawn_timeout,zone_transition,content_complete,title_return)` | **every** `flowState = ` assignment (11 sites: `GameScene.swift:216,334,605,650,710,720,739,764,920,932,968`) |
| `state.zone_load` | `resource:str(L\d\dS\d\d)`, `zone:zone`, `cause:str(app_launch,transition,checkpoint,restart)` | before `TMXLevelRuntime` init |
| `state.zone_loaded` | `resource`, `zone`, `solid_count:int`, `spawn_x:float3`, `spawn_y:float3`, `ground_y:float3`, `invulnerability_us:int`, `carried_y:bool` | after `player.configure` (`GameScene.swift:646`); carried-Y rule at `:639-645` |
| `state.zone_exit` | `zone`, `trigger_x:float3(=510)`, `player_x:float3`, `next_level:str("" when empty)` | `checkScreenExit` (`GameScene.swift:609-612`) |
| `state.zone_transition` | `from_zone:zone`, `to_zone:zone`, `accumulator_us:int`, `pending_steps:int` | `transition(to:)` head (`GameScene.swift:633`) — **P1-9 witness** |
| `state.content_complete` | `zone`, `next_level:str`, `points:int`, `final:bool(zone≥124)` | `enterContentComplete` (`GameScene.swift:738-765`) |
| `state.title_enter` | `high_score:int`, `has_saved_checkpoint:bool` | `didMove(to:)` and `showTitleAfterContentComplete` (`GameScene.swift:760-766`) |
| `state.checkpoint_saved` | `resource`, `ammo`, `grenades`, `points`, `lives` | `saveCheckpoint` (`GameScene.swift:696-705`) |
| `state.checkpoint_cleared` | `reason:str(new_game,game_over,launch)` | `persistence.clearCheckpoint()` |
| `state.pause_enter` / `state.pause_exit` | `state_before:str`, `selected_index:int` | `GameScene.swift:920,932` |
| `state.restart` | `from_zone:zone`, `points:int` | `restartFromBeginning` (`GameScene.swift:950-974`) |
| `state.cheat_invulnerability` | `enabled:bool`, `menu_index:int` | pause-menu toggle (`GameScene.swift:186`) |

### tick anomalies (must exist at level 0)
| name | payload | trigger |
| --- | --- | --- |
| `tick.frame_gap_clamped` | `raw_frame_time_us:int`, `clamp_us:int(=250_000)`, `lost_us:int` | `min(currentTime - previousUpdateTime, maximumFrameTime)` actually clamped (`GameScene.swift:129`) |
| `tick.accumulator_reset` | `reason:str(zone_transition,new_game,paused_exit,explicit)`, `discarded_us:int`, `discarded_steps:int` | the P1-9 fix site |
| `tick.slow_step` | `step_us:int`, `budget_us:int(=16_667)`, `steps_this_frame:int` | a frame ran > 1 step or a step took > budget (optional, level 2) |
| `tick.heartbeat` | `uptime_us:int`, `events:int`, `drops:int`, `zone`, `flow_state` | every 600 ticks (10 s), **the only periodic record**; proves liveness and bounds a gap's cost to 10 s |

Deliberately **not** in the contract: `tick.frame_begin` (a heartbeat event per frame —
measured at 44 % of bytes for information the `frame` field already carries),
per-explosion-effect frames, per-pellet trail dots, and per-tick entity state for every
obstacle (that is a wave-B "simulation dump", not an event log; if needed later it becomes a
separate `name` family at level 3, never a format change).

## 9. Ordering and idempotency

Claim to write into `architecture.md` verbatim:

> The event log is emitted from one thread — the SpriteKit update thread — from inside the
> fixed-step loop, at the point where the state change actually happens. Emission is
> non-reentrant and never deferred, so a single writer assigns `seq` monotonically and the
> stream is a **total order**. Two events never share a `seq`, and `seq`, `tick` and `frame`
> are all non-decreasing along the file.

Justification, and the limits of it:
- `GameScene.fixedUpdate(dt:)` is called only from `update(_:)` on the scene's render
  thread; there is no `DispatchQueue`, `async`, or `actor` anywhere in `GameCore` (grep for
  `DispatchQueue|async |actor ` → 0 hits; the only `Timer` matches are the
  `deathGroundTimer` variable), and no timer in the gameplay path
  (`GameScene.swift:148`). Total order follows from that, **provided the emitter is
  synchronous into a buffer**. If the implementation ever hands events to a background
  queue for writing, it must keep the enqueue on the update thread, and the contract's
  total-order guarantee then applies to enqueue order, not to file order.
- The only lock in the gameplay path is `InputState.lock` (`InputState.swift:35`), which
  spans the input sources. Gamepad callbacks already hop to the main queue
  (`GamepadInput.swift:97 DispatchQueue.main.async`), and AppKit key handling is on the main
  thread (`GameView.swift:11-31`), so the update loop and the input writers are the same
  thread in the shipped app. `input.action_edge` must be emitted **from the tick loop**, not
  from `InputState.set`: a press released between two ticks otherwise disappears or lands on
  the wrong tick. Recommendation — diff `inputState.snapshot()` against the previous
  snapshot once per tick and emit the edges from there: one lock acquisition per tick, one
  writer, no new ordering hazard, and the edge is stamped with the `tick` that actually saw
  it. Treating `input.action_edge` as a level-2 diagnostic is the fallback if a
  same-thread guarantee is ever lost.
- **Idempotency:** there is none at the event level, and none is wanted — the log is an
  append-only record of a process, not a message queue. Consumers deduplicate by
  `(run_id, rot, seq)` and must treat a re-delivered line as the same event. The only
  idempotency requirement is on the **writer**: rotating, flushing and retrying must not
  duplicate `seq`.
- **Duplicate suppression inside the game loop** is a separate, product-level invariant that
  the log must expose, not solve: an award must never fire twice for one game fact
  (P1-8, P1-6). The log's job is to make the duplicate visible; the fix's job is to make the
  assertion pass.
- **Ordering across runs:** `run_id` is unique per process. Two runs are never interleaved
  into one file, and a consumer that concatenates files must group by `run_id` first.

## 10. The four wave-A assertions, computable from the stream alone

These are the acceptance tests. Each predicate reads only log records — no game state, no
Swift symbols — so the same predicate works in a Swift test over an in-memory array and in a
Python auditor over the file. The probe (`/tmp/evlog-probe/check.py`) implements them;
results below are from the real runs.

**A. "no extra ticks after transition" (P1-9)**

```
for each `state.zone_transition` at (frame F, seq S):
    count C = number of `player.motion` records with frame == F and seq > S
    assert C == 0
    assert a `tick.accumulator_reset{reason:"zone_transition"}` exists with
           seq in (S, first record with frame > F)
    assert `tick.accumulator_reset.discarded_steps` == 0
               || discarded_us < fixedTimeStep * 1_000_000
also globally: no frame may carry more than floor(maximumFrameTime / fixedTimeStep) = 15
               `player.motion` records, and none of those 15 may straddle a transition.
```
Probe result: buggy run `max_ticks_after_transition = 1` over 124 transitions; the
worst-case run (player crosses x=510 on the first step of a clamped 250 ms frame)
`15 steps total, 14 of them after the transition` → **FAIL**; the fixed run
`1 step, 0 after` → **PASS**. The control flips, so the assertion measures the fix and not
the harness.

**B. "no double stage bonus" (P1-8)**

```
playthrough = the records between `state.title_enter{cause}` or `state.restart`
              and the next `game.game_over` / `state.title_enter`
for each playthrough, for each `completed_zone` Z:
    count(`bonus.stage_points` with completed_zone == Z) <= 1
    count(`bonus.stage_points`) <= 5                      # zones 24,49,74,99,124
    sum(points) from `score.awarded{reason:"stage_boundary"}` <= 5 * lives_cap_bonus
and: if `state.zone_exit` fires with x > 510 at a stage-end zone twice, the second one
     must be witnessed by `bonus.stage_boundary_suppressed`, never by silence.
```
Probe result: buggy 600 s run awarded zone 124 **750 times** (`bonus.stage_points` counts
`[(24,1),(49,1),(74,1),(99,1),(124,750)]`) → **FAIL**; fixed run
`[(24,1),(49,1),(74,1),(99,1),(124,1)]` + 524 `bonus.stage_boundary_suppressed` → **PASS**.
Note the fixed build must still emit the suppression witness: an assertion that only counts
awards would also pass on a run where the bonus silently never fires at all.

**C. P1-4 (jump after teleport while UP held)** — stream-only form:

```
for each `player.teleport`:
    assert no `player.jump` with the same run_id and tick in (t, t+N]
           while `input.contextual_consumed{jump_suppressed:true}` is the last
           jump-relevant record, unless a fresh `input.action_edge{action:"jump",
           pressed:false}` precedes it.
    equivalently: `input.contextual_consumed.after_teleport` must be followed by
           `player.jump` only after a jump release edge.
```
Requires the payload `jump_latch_held` on `player.teleport` and `after_teleport` on
`player.jump`; without those two booleans the property is **not** decidable from the log,
which is why they are mandatory in §8.

**D. P1-6 (double launcher permanently disabled after bonus)** — stream-only form:

```
for each `bonus.double_launcher`:
    assert `launcher_active_after == false` for the collected object
    and assert a subsequent `state.zone_transition{to_zone != completed_zone}` is
           followed (within that zone) by at least one
           `entity.launcher_fire{object_id, kind:"double_launcher"}` **or** an explicit
           `entity.launcher_state{active:true}` restoration witness.
    forbidden: zero launcher activity for the rest of the run after a collect on every
           map that carries `double_launcher` (19 objects on 18 maps, audit P1-6).
```
This one needs an `entity.launcher_fire` event in wave A (reserved family `entity` in §3),
otherwise the defect is not observable and the regression test has to fake it. Flagged as a
catalog addition in §11.

**Negative controls the harness must include** (the 2026-09-19 harness already sets the
precedent with its "must not build without the shim" step, `run.sh` step 6):
1. a run with the fix reverted must FAIL A and B (the probe demonstrates exactly this);
2. a run whose log is truncated must FAIL the `seq` continuity check rather than pass the
   property checks by losing evidence;
3. a run where emission is disabled must produce no file at all (not an empty file), so a
   consumer cannot confuse "off" with "no events happened".

## 11. What the implementer must decide / must not do

Open, bounded decisions (not blockers):
1. Add `entity.launcher_fire{object_id,str, kind, x,y, muzzle_y:int}` to make §10-D
   decidable (P1-6 is otherwise untestable from the stream).
2. Whether `state.flow` is emitted from a property `didSet` or at each of the 11 assignment
   sites. `didSet` on `flowState` is 1 edit and cannot drift; prefer it, and keep `cause`
   explicit at the call sites via a small helper.
3. RNG: 16 `.random` sites exist in gameplay (`LevelObstacles.swift:102,331,383,419,422,449,493,574,578,580,671,672,686,708,713`
   and `TMXLevelRuntime.swift:170`), so runs are **not** reproducible today. Do not assert on
   absolute tick numbers of random-driven entity events in tests; assert on causal
   relations. If a seeded RNG is introduced later, `log.begin.seed` already carries it
   (do not retro-fit that field into the envelope; it belongs to `log.begin` only).
4. Whether the in-game human view shows a tail of the log: `inputLabel`/`debugOverlay`
   already exist (`GameScene.swift:1062-1130`). If it is added, it must read the same
   records (a rendered ring buffer of the last N events), never a second, cheaper format.
5. `hud.banner` is intentionally excluded from wave A (the 0.75 s `showBanner` is a
   presentation effect, not a game fact); reserve the `hud` family for it.

Must not:
- Do not put the emitter behind `SKScene` only, and do not shim SpriteKit (§1).
- Do not put wall-clock time in the ordering key or in `ts_us` (§5).
- Do not write the log inside the clone (fingerprint hazard, §7).
- Do not hand-build JSON strings (§7 rule 1).
- Do not rename an event or a field after this document is bound into the PR — that is a
  `schema_version` bump, and `schema_version` bumps require both consumers to move.
- Do not add a per-frame heartbeat event.
- Do not use `fatalError`/precondition on an emit failure: a log that can crash the game is
  worse than no log. Increment `log.events_dropped` and continue.

## 12. Proposed typed rows for `change-spec.yaml` (patterns are `AC|INV|FORBID|SIG-\d{3,6}`)

`contracts.events` / `contracts.json_schema` entries are validated as plain strings ≤ 512
chars (`schemas/change-spec.schema.json`), so the catalog itself must live in a file, e.g.
`engineering/contracts/schemas/gameplay-event-v1.schema.json`, and the spec reference it.

- `AC-001` a headless Linux harness run drives the fixed-step loop and produces ≥ 1 record
  per simulated tick at level 2, parseable by `json.loads`, 0 dropped.
- `AC-002` the P1-9 predicate (§10-A) passes on the fixed build and fails on the reverted
  build (contradictory control).
- `AC-003` the P1-8 predicate (§10-B) passes on the fixed build and fails on the reverted
  build.
- `AC-004` the P1-4 predicate (§10-C) is decidable and passes.
- `AC-005` the P1-6 predicate (§10-D) is decidable and passes.
- `AC-006` level 2 emission costs ≤ 5 % of a 16.67 ms tick on this host (probe measured
  0.05 %).
- `INV-001` `seq` strictly increases by 1 within `(run_id, rot)`; `tick` and `frame` are
  non-decreasing across the file; single writer.
- `INV-002` `ts_us == round(tick * 1_000_000 / 60)` for every record.
- `INV-003` every game state mutation observable in wave A has exactly one event; no
  observable event without a state change.
- `FORBID-001` a run where `bonus.stage_points` is awarded twice for one `completed_zone`
  within a playthrough.
- `FORBID-002` any fixed step simulated in a new zone inside the render frame that
  transitioned to it.
- `FORBID-003` a wall-clock or locale-dependent value in any field other than
  `log.begin.wall_utc`.
- `SIG-001` `log.events_dropped` count == 0 during a 10-minute level-2 session;
  `tick.heartbeat` gap ≤ 10.5 s.

## 13. Reproduction of the probe (kept outside the repo)

```
/opt/swift/usr/bin/swiftc -emit-module -emit-library -module-name CoreGraphics \
  -emit-module-path /tmp/evlog-probe/CoreGraphics.swiftmodule \
  -o /tmp/evlog-probe/libCoreGraphics.so /tmp/evlog-probe/shim.swift
cd /tmp/evlog-probe && /opt/swift/usr/bin/swiftc -I . -L . -lCoreGraphics \
  GameConstants.swift InputState.swift Player.swift main.swift -o probe
LD_LIBRARY_PATH=/tmp/evlog-probe ./probe        # 4 runs: buggy/fixed + worst-case pair
python3 /tmp/evlog-probe/check.py buggy.jsonl fixed.jsonl worst_buggy.jsonl worst_fixed.jsonl
```
`shim.swift` = the harness 1-liner plus a 7-line `CGVector`. `main.swift` = verbatim product
copies of `GameConstants`/`InputState`/`Player` and a copy of the `GameScene` accumulator
loop; the buggy/fixed booleans are the only deltas. Nothing in `/home/pall/projects/exolon`
was modified (`git status --porcelain` shows only this evidence directory).
