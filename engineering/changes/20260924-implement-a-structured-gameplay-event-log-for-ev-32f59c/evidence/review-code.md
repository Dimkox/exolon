# Code review — wave A gameplay event log + P1-9/P1-4/P1-8/P1-6 fixes

Route agent: `code_reviewer` · change `20260924-implement-a-structured-gameplay-event-log-for-ev-32f59c`
Base `295690b7fc724e57b37b5fac86b71c1da7d8b032` · branch `codex/wave-a-gameplay-log-tick-fixes-20260924`
Subject: the uncommitted working tree (`git diff HEAD`: 740 insertions / 110 deletions over 10 tracked
files, plus 5 new `GameCore/Diagnostics/` sources, the frozen schema and the change package).
Method: read the diff **and** the surrounding implementation of every touched type; mechanically
diffed the wire against the schema (all 46 wire-reachable names, not a 10-name sample); re-ran the
Linux gate. This review writes this file and nothing else.

## Verdict

**BLOCK — the log currently lies about the game in four record types.**

The *gameplay* is right: all four state-machine fixes work, and I found **no behavior regression** in
any of the 740 added lines (§8). The defect is confined to the **emission layer** — four lane-order /
lane-map mistakes that write wrong numbers and out-of-contract labels into `damage.player_hit`,
`damage.player_blocked`, `state.checkpoint_saved` and `state.restart`. Two of them are the
every-lethal-path choke point, so the records most likely to be read are the ones that misreport.

The gate is green anyway (`RESULT: PASS (23/23)`, my own run), and §3 explains why: the harness proves
the **formatter** and re-implements the **producers**. Every one of the four defects sits in the half
of the tree the gate never compiles.

---

## 1. Critical — wire-level lies

### R1-1 `damage.player_hit` — packed lane passed in the x lane (Critical, high confidence)

`Exolon/GameCore/GameScene.swift:1355`

```swift
events.emit(.damagePlayerHit, packed, x, y, Int16(truncatingIfNeeded: gameState.lives))
```

Four positional `Int16` arguments resolve to `emit(_:entity:_:_:_:_:)` with `entity = 0`, so the record
carries `a = packed, b = x, c = y, d = lives`. Both authorities say the opposite:

* frozen contract, `x-encode` of `damage.player_hit`: `a=xq b=yq c=pack(cause:5b,
  flow_state_before:3b, flow_state_after:3b) d=lives`;
* `GameplayEventKind.schemas[23]` — `GameplayEventSink.swift:197` — identical;
* formatter — `GameplayEventLog.swift:971-977` — `x = a`, `y = b`, cause/flows decoded from `c`.

Computed effect (not executed — see §3) for a force-field hit at logical (300, −85) px →
quarter-px `x=1200, y=−340`, `cause=.forceField(3)`, `playing(1) → playerDead(3)`, `packed = 1603`:

```json
"cause":"unknown44","x":1603,"y":1200,"flow_state_before":"respawning","flow_state_after":"unknown7","lives":2
```

The hit reports **the bitfield as the x coordinate, the x coordinate as y**, and payload labels outside
the frozen enums (`GameplayDamageCause(rawValue: 44)` and `GameplayWire.flowState(7)` are nil → the
`unknown<N>` fallbacks at `GameplayEventSink.swift:621` and `:481-483`). `envelope_schema_valid` would
reject such a line outright — it never sees one, because the only `damage.player_hit` records in any
stream come from the harness's generic `emit(kind, entity: 0, 1, 1, 1, 1)` loop
(`evidence/harness/main.swift:654`).
Fix: `events.emit(.damagePlayerHit, x, y, packed, Int16(truncatingIfNeeded: gameState.lives))`.

### R1-2 `damage.player_blocked` — formatter decodes a lane the product never fills (Critical, high confidence)

`GameplayEventLog.swift:967-970` decodes `cause` and `test_invulnerability` from the **entity** lane
(`subject`), while the contract (`x-encode`: `a,b = invulnerability_us i32; c = pack(cause:5b,
test_invulnerability:1b)`), `schemas[22]` (`GameplayEventSink.swift:196`) **and the product call site**
(`GameScene.swift:1361-1362`: `a=hi, b=lo, c=GameplayPack.blocked(...)`, entity left at 0 by the
3-positional overload) all put the pack in lane `c`. Consequence: **every** blocked hit logs
`cause:"bullet"` and `test_invulnerability:false` regardless of what blocked it or whether cheat
invulnerability was on. Only `invulnerability_us` is truthful.

This one is visible in the gate's own artifact, which is why I rate it above argument:

```
{"seq":20,"name":"damage.player_blocked","cause":"bullet","invulnerability_us":65537,"test_invulnerability":false}
```

— produced from `a=1,b=1,c=1`: `invulnerability_us = join(1,1) = 65537` ✓, cause lane `c = 1` = `mine`,
but the wire says `bullet` because the formatter read entity `0`. Type-level validation cannot see it:
`bullet` is a valid enum member. Fix: decode from `GameplayEvent.word(record.c)`.

### R1-3 `state.checkpoint_saved` — `lives` written at bit 12, read at bit 13 (Critical, high confidence)

`GameplayEventSink.swift:337-341` (`GameplayPack.checkpoint`, lives at `:340`) vs
`GameplayEventLog.swift:1051-1056` (`lives` read at `:1056`).

* pack: `ammo & 0b111_1111` (bits 0-6) | `grenades & 0b11_1111 << 7` (bits **7-12**, 6 bits) |
  `lives & 0b1111 << 12` (bits **12-15**);
* formatter: grenades `(subject >> 7) & 0b11_1111` (7-12), lives `(subject >> 13) & 0b1111` (13-16);
* contract `x-encode`: `a = pack(ammo:7b, grenades:5b, lives:4b)` → bits 0-6 / 7-11 / **12-15**, in
  lane `a`; `schemas[38]` (`:212`) says `entity=pack(ammo:0..6,grenades:7..12,lives:13..15)`.

Three different layouts for one record. The pack reserves 17 bits in a 16-bit lane, so bit 12 is
shared, and the formatter reads `lives` one bit too high. Computed wire values:

| real (ammo, grenades, lives) | wire `grenades` | wire `lives` |
| --- | --- | --- |
| 99, 10, 3 | **42** | **1** |
| 99, 10, 1 | **42** | **0** |
| 99, 0, 2 | 0 | **1** |

`ammo` and `points` survive; `grenades` and `lives` do not, and the wrong values look plausible, so no
validator can catch it. Fix: 5-bit grenades field at 7-11 and `lives >> 12 & 0b1111`, in pack,
formatter and `schemas[38]` together (lane choice: see R2-3).

### R1-4 `state.restart` — an extra zone argument shifts the i32 apart (Critical, high confidence)

`GameScene.swift:1147`

```swift
events.emit(.stateRestart, Int16(truncatingIfNeeded: gameState.zone), discardedPointsSplit.0, discardedPointsSplit.1)
```

Contract (`x-encode`) and `schemas[42]` (`GameplayEventSink.swift:216`): `a,b = points i32`, and
`from_zone` comes from the record's zone lane — which the formatter already does
(`GameplayEventLog.swift:1062-1065`). Passing the zone again in `a` shifts the i32 one lane right, so
`points = join(high: zone, low: pointsHi)`:

| discarded points (zone) | wire `points` |
| --- | --- |
| 1000 (zone 0) | **0** |
| 1000 (zone 3) | **196608** |
| 250000 (zone 24) | **1572867** |

`restartFromBeginning` is reachable from the pause menu at any zone, and zone 0 is the default — so the
record claims a discarded run scored nothing exactly when the player restarts the game. Fix: pass
`(discardedPointsSplit.0, discardedPointsSplit.1)` only.

---

## 2. Medium — the writer's own records

### R2-1 `log.events_dropped.first_seq`/`last_seq` name events that are present (medium, high confidence)

`GameplayEventLog.swift:658` builds the record as `firstSeq: nextSeq - drops, lastSeq: nextSeq - 1`
(written verbatim at `:760-770`). But `seq` is assigned **by the drain, after the loss**: `storeLocked`
(`:566-580`) overwrites the oldest undrained slot and bumps `droppedTotal` only, while `nextSeq`
advances solely for surviving records (`:664`). Ring laps therefore never create a seq gap, and the
declared range always names seq numbers that were handed to records that are in the file. Evidence from
the gate's own starved-writer artifact (`drops-3fc942234051a4d4-0.jsonl`, my run):

```
seq 0   log.begin
seq 1   log.events_dropped  count:4496  first_seq:0  last_seq:0
seq 2.. player.motion …
→ 515 lines, seqs contiguous 0..514
```

`first_seq:0, last_seq:0` while seq 0 is that file's header. Two consequences: (a) both fields
misreport which events were lost; (b) the schema's stated safety property — *"`seq` … a gap is lost
data and must be declared by `log.events_dropped`"* and *"it accounts for the seq gap left behind, so
silent loss is impossible"* — is structurally unenforceable: loss is detectable only by trusting this
record. `INV-001`/`stream_invariants` pass correctly, because the stream really is gapless. `count` is
accurate and loss is never silent, so FORBID-004 is **not** violated; the numeric fields are wrong.
Options: assign `seq` at append time (restores gap semantics), or redefine the two fields as the
surviving boundary and say so in the schema.

### R2-2 `log.rotate` is the second line of the new file, not the last line of the retired one (medium, high confidence)

`GameplayEventLog.swift:724-742` calls `rotateToNextFile()` (which closes the old handle) first, then
`beginRecordLine` (`:744-758`), then the rotate line — both land in the **new** file. Its own
`x-encode` says "last line of the file being retired". Evidence from the rotation scenario of my run:

```
rotation-337b0ba9917cf533-124.jsonl line 1: log.begin   seq 4215 rot 124
rotation-337b0ba9917cf533-124.jsonl line 2: log.rotate  seq 4216 from …-123.jsonl to …-124.jsonl
rotation-337b0ba9917cf533-123.jsonl last:  player.motion seq 4214
```

The retired file ends mid-stream with no marker, so a consumer holding only `-123.jsonl` cannot
distinguish "retired at 8 MiB" from "truncated" — precisely what the annotation exists to guarantee.
`rotation_linkage` passes because it checks only path linkage and seq continuation. The rest of the
rotation design is coherent: rotation decided per batch *before* numbering (`:648-652`) so seq never
decreases at a boundary, header/rotate records stamped from the following batch so `tick`/`frame` stay
non-decreasing within a file, `bytesInCurrentFile` includes the buffer, and `pruneOldFiles`
(`:119-127`) keys on the parsed suffix to keep exactly `keptFiles` generations.

### R2-3 The schema declares itself the formatter's single authority, but lane maps disagree (low, high confidence)

`x-encode` for `state.zone_load` says `a = cause code`, while the code carries it in the entity lane
(`GameScene.swift:1299` + `GameplayEventLog.swift:1020-1024`) and `schemas[32]` says `a=cause`. Same
pattern for `state.checkpoint_saved` (R1-3). The `zone_load` wire output is correct (both sides use
entity), so this is documentation debt — but it is exactly the debt that makes R1-3/R1-4 look plausible,
and it is invisible to `kind_enum_append_only`, whose lane-map comparison is textual.

---

## 3. Why the gate cannot see any of this (structural; fix it with the defects)

`evidence/harness/run.sh:35-45` compiles `GameConstants`, `InputState`, `GameState`, `Player` and
`Diagnostics/*` only. `GameScene.swift` (~30 of the 47 emission sites), `TMXLevelRuntime.swift` and
`LevelObstacles.swift` are **never built or run** by the gate; the harness re-implements their packing
instead (`evidence/harness/main.swift:250-366`, `:578-588`, `:654`) — a replica, which this change's own
`architecture.md` declares is never an assertion source. All four Critical defects sit in that uncovered
surface, and no check is aimed at it:

* `envelope_schema_valid` / `forbid_wallclock_fields` are type- and enum-level: `196608` is a valid
  integer and `"bullet"` a valid cause. R1-1 is the only one a validator would reject, and only if a
  real hit line ever reached a stream.
* `kind_enum_append_only` diffs names/levels/lane-maps as **text** between schema and
  `GameplayEventKind`, never between the schema and what the formatter actually reads.
* `hot_path_is_allocation_free` is scoped to `emit()` and the locked append, correctly; it cannot be
  widened into a producer test.

`test-plan.md` is honest about this (it never claims producer coverage, and its macOS E2E row is still
pending), so the gap is not a false claim — it is an untested surface that shipped four defects.
Recommendations, in cost order: (1) a table-driven lane test in the gate that, for every catalog name,
packs a *distinctive* value into each lane declared by `x-encode` through the same `GameplayPack`
helpers and asserts the decoded JSON equals the input — that one check fails on R1-1..R1-4 today;
(2) move the emission helpers out of `GameScene` into a Foundation-only producer, the way
`FixedTickDriver`/`StageBoundaryLedger`/`LauncherBonusState` already did, so the gate compiles the real
call sites.

---

## 4. The four fixes in product code — verdicts

**P1-9 (fixed-tick accumulator) — correct; the only fix whose decision logic is gate-executed with a
flipping control.** `GameScene.swift:186-193` delegates the whole loop to `FixedTickDriver`
(`:188 beginFrame`, `:191 beginStep`); `accumulator`/`previousUpdateTime` are gone from the scene
(`:92-93` is now a comment). `beginStep` (`FixedTickDriver.swift:89-94`) enforces
`stepBudget = floor(0.25/(1/60)) = 15` and only then calls `events.beginTick`; `reset(reason:)`
(`:103-110`) zeroes **only** the accumulator (`:108`) and leaves `tick`/`frame` and
`previousUpdateTime` alone — the reasoning in the comment is sound: zeroing the reference would hand
the next frame a paused-size delta and immediately re-run a 15-step burst in the new zone.
`transition(to:)` emits the witness **before** resetting (`GameScene.swift:791` then `:796`), so
`state.zone_transition{accumulator_us,pending_steps}` names the discarded charge while the record zone
lane still holds the outgoing zone, exactly as `x-encode` requires. `restartFromBeginning` resets too
(`:1156`) — the second zone-swap-inside-a-rendered-frame site, correctly covered. My run: `fixed: 0
steps after transition, witness 233333 us / 14 steps discarded; reverted: 17 motion records and
predicate A fails as required`. Minor: `reset` also clears `stepsThisFrame`, so a frame that caught up
and *then* transitioned loses its `tick.slow_step` (`FixedTickDriver.swift:133-140` reads a zeroed
count) — absence of a diagnostic, not a wrong one.

**P1-4 (jump latch) — correct; the root cause is genuinely removed.** The base defect is visible in the
diff: the scene built a one-step `jump: false` mask and passed it to `player.update`, whose trailing
`jumpWasPressed = input.jump` re-sampled **the mask**, so the *next* step saw a fresh edge from a
physically held key. The mask is gone — `GameScene.swift:340` passes `rawInput` and `:347`
`finalizeMotionState(input: rawInput)` — and `Player.consumeContextualJumpPress()`
(`Player.swift:289-292`) sets `jumpWasPressed = true` **and** `contextHoldsJumpLatch = true` before that
same `update` call. `Player.swift:131-139` is the release-edge rule: while the latch is held and the key
is still down, `jumpWasPressed` stays `true`; only `input.jump == false` clears both. I traced
held-UP-across-teleport (no jump), release-then-press (one jump, `after_teleport:false`), and the
regression path (a jump while the latch is set reports `after_teleport:true` — `Player.swift:125,129`),
which is exactly the canary the schema describes. `teleport`/`beginDeath`/`respawn` arm or clear both
flags consistently (`:240-241`, `:252-253`, `:268-269`). Gate: `1 teleport with the latch held, 1
legitimate jump after a release edge, 0 leaks; the hand-written violation stream fails predicate C`.

**P1-8 (stage bonus) — correct; the farm's arming condition is closed.** `StageBoundaryLedger` owns
once-semantics per `(zone, component)` key (`outcome` `:105-131`, `onceKey` `:138`), `.suppressed` is
returned for every repeat and emitted at `GameScene.swift:774-776` — never silence — and
`.notApplicable` produces no record, as INV-003 requires. The decisive part is where a playthrough is
armed: `beginPlaythrough()` runs on `beginFromTitle` **only when `!hasSavedCheckpoint`**
(`GameScene.swift:885-889`), so the `contentComplete → title → FIRE` loop that caused the farm cannot
re-arm; `enterGameOver` closes the playthrough (`:903`) and `restartFromBeginning` starts a new one
(`:1151`). Award arithmetic matches the removed base body exactly: `lives * 1000`
(`StageBoundaryLedger.swift:19`), `livesAfter = min(startingLives, lives + 1)` (`:127`) ≡ base
`if lives < startingLives { lives += 1 }`, and the ammo/grenade refill is unchanged. Gate: `fixed: 1
award + 749 suppression witnesses; reverted: 750 awards, 0 witnesses`. Two notes: `.notStageEnd` is
reachable only through an empty `awardSequence` (`:122`), which mislabels that case; and with multiple
components the loop returns on the first exhausted one, so a later wave's boundary is all-or-nothing
(fine for one component, but the sequence exists to be extended).

**P1-6 (double launcher) — correct, with an honest identity chain.** `LauncherBonusState` (`:18-46`)
splits payout from fire gate: `payBonus` flips only `bonusCollected`, and `deactivate()` is the sole
writer of `isActive` and is called by nobody — the payout can no longer silence the launcher.
`LevelObstacles.swift:689` holds the state, `:697` exposes `isActive` as a read-only view of the fire
gate (so existing readers are unchanged), and `:733-738` keeps the dimmed sprite. Identity returns
intact: `TMXLevelRuntime.buildObjectsFromTMX` assigns a per-object ordinal (`:262-263`, `&+`, one
increment site, matching the declared "ordinal in `map.objectGroups.flatMap { $0.objects }`") →
`collectDoubleLauncherBonus` returns `(points, entityID)` (`:233-238`) →
`doubleLauncher(withEntityID:)` (`:244-246`) → `GameScene.swift:371-376` → `emitDoubleLauncherBonus`
(`:1279-1281`) reports `launcher_active_after` from the still-open gate. `entity.launcher_fire` is
emitted inside the runtime's own fixed update (`TMXLevelRuntime.swift:147-154`, `:153`) after
`shots.append`, so it cannot alter stepping. Gate: `1 payout(s), 40 subsequent launcher shot(s) for the
same object_id; the pre-fix single-flag control fails predicate D`. Consumer note: `nextEntityID`
restarts per zone instance, so the join key is `(record zone, object_id)`, not `object_id` alone —
neither the field name nor AC-005's wording says so.

## 5. GameScene emission sweep — verdicts

* **`state.flow`: complete.** 11 `changeFlow(to:cause:)` sites (`:283, 412, 734, 817, 889, 899, 925,
  956, 1113, 1127, 1173`) and **exactly one** raw assignment (`:1203`, inside `changeFlow`), so the
  observer at `:73-79` is the single emission point. The initial `.title` cannot fire `didSet`;
  `pendingFlowCause` is consumed-and-reset per transition, so an unlabelled future edit degrades to
  `unspecified` rather than borrowing a stale cause. `emitFlow` also drives `setFlowState` (`:1207`),
  which is what keeps `log.begin.flow_state` and `tick.heartbeat.flow_state` truthful. Nuance: the
  heartbeat's label is read at drain time (`GameplayEventLog.swift:1086`) instead of from the record, so
  a heartbeat drained within the 0.25 s window after a flow change names the newer state.
* **Per-tick input diff: correct seam.** `emitInputEdges(current: rawInput)` is the first statement of
  `fixedUpdate` (`:210`; body `:1229-1256`) and diffs the tick snapshot against `previousTickInput`.
  Nothing in `InputState.set` emits — its whole diff adds `sourceByAction` (`InputState.swift:42`) for
  the frozen `input.action_edge.source` field, read at `:66-70` and cleared consistently in
  `reset`/`resetAll`/`resetGamepad`. Edges are stamped with the tick that observed them, `held_us` comes
  from a fixed-step counter (no wall clock) and saturates at 32 767 ms.
* **No allocation at the sites.** The per-tick loop calls 10 non-capturing `static let` projections
  (`:48-49`, allocated once) and writes in place into a pre-allocated `[Int32](count: 10)` (`:47`); the
  dictionary lookup `inputState.source(for:)` runs only inside the changed-edge branch. `GameplayEvent.q`,
  `GameplayPack.*` and `GameplayEvent.split` are integer-only.
* **`awardPoints` funnel intact.** `:832` is the only `gameState.points` mutation in the tree; 10 call
  sites (`:373, 494, 501, 509, 518, 580, 601, 702, 712, 779`) all pass a `reason`, and
  `score.awarded.points_after`/`clamped` (`GameplayEventLog.swift:1006-1014`) reproduce the same
  `min(999_999, before + points)` arithmetic, so the record cannot disagree with the score. (`:827`
  claims "14 call sites"; it is 10.)

## 6. Diagnostics core — verdicts (clean except §2)

* **Ring-as-backlog: the banned single-slot handoff is gone.** `head`/`tail`/`pending` with the
  invariant `head + pending == tail` maintained through a lap (`GameplayEventLog.swift:566-580`), the
  writer consuming through `head` (`:607-671`) and keeping the newest on overflow. Capacity is a power
  of two (`:338`, `roundedPowerOfTwo`) so `& mask` is exact; `head`/`tail` only increase, so there is no
  negative-index path.
* **NSLock only.** No `NSRecursiveLock`, `DispatchSemaphore`, `os_unfair_lock` or `@synchronized`
  anywhere in Diagnostics (grep). `appendHeartbeatLocked` (`:583-598`) deliberately re-implements the
  store inline instead of re-entering the lock. `reportOnce` (`:772-780`) takes the lock and is reachable
  only from `ensureFileOpen`/`rotateFile`, i.e. after `drainNow`'s `lock.unlock()`. `drainNow` mutates
  drain-side state (`nextSeq`, `fileIsOpen`, `openFailed`, `drainBuffer`) **without** the lock — sound
  in `.asynchronous`, where every entry point is the serial queue (timer handler runs on-queue `:358-362`;
  `requestDrain` `:499-502`; `flush` uses `queue.sync` behind the `getSpecific` guard at `:514`, which is
  the prototype-deadlock fix), and sound in `.synchronous` (documented single caller thread). `.off`
  short-circuits `drainNow` at `:608`.
* **Counters never reset; first tick == 1.** `beginTick` (`:463-471`) and `beginFrame` (`:454-457`) are
  the only mutators, `&+` from 0, so the first executed step is tick 1 and the first simulating frame is
  frame 1, with frame 0 reserved for the early-returning `update(_:)` — exactly the `frame` annotation.
  The type exposes no reset API at all; `stats` (`:285-288`) is read-only.
* **`unknown<N>`: no aliasing.** `names` is derived from `label` over raw values 1...48
  (`GameplayEventSink.swift:80-86`), the formatter falls back to `"unknown\(record.kind)"`
  (`GameplayEventLog.swift:865`) and suppresses the payload for a kind that does not resolve (`:868`),
  per `x-unknown-name`. Verified live in the streams: `unknown200` and `unknown255` present, envelope
  only. `appendRawKind` (`:434-436`) is a documented test seam bypassing only the level gate
  (`emit`'s gate is `:427`).
* **Formatter purity: integers and whitelisted labels only.** Every producer-path `string()` is
  `String(subject)` for `launcher_object_id`/`object_id` (schema `^[0-9]+$` ✓), `resource(for:)`
  (`GameplayEventSink.swift:614-617` → `^L\d{2}S\d{2}$` ✓, `min(124, …)` keeps 2+2 digits) and
  `next_level`, whose empty string the pattern `^(|L\d{2}S\d{2})$` explicitly allows. No `Date`/
  `DateFormatter` outside `log.begin` (`GameplayEventLog.swift:750`); `escapedJSONString` only for the
  exempt fields. `state.zone_exit.next_level` and `state.content_complete.next_level` are *derived* from
  the zone lane rather than from `currentLevel.nextLevelName` — contract-sanctioned ("next_level derived
  like state.zone_exit") but silently assuming a map's `nextLevel` equals `L(stage)S(screen)` for
  zone+1; worth one comment at `GameplayEventLog.swift:1037`/`:1045`.
* **ts_us:** `microseconds(fromSteps:)` (`GameplayEventSink.swift:273-275`) is
  `(n*1_000_000 + 30)/60` on Int64 — exact round-half-up, not accumulated. Holds on all 131 796 records.
* **Flush policy** (`GameplayEventLog.swift:673-676`, family table `:680-700`): every state/damage/
  bonus/tick/log record plus every 60th tick; correct, exhaustive without a `default:` so a new kind
  lands in exactly one branch.
* **Mechanical contract sample — all 46 wire-reachable names, not 10.** Against the gate's own
  `contract-*.jsonl`: envelope order `schema_version,seq,tick,frame,rot,ts_us,name` exact on every line;
  no missing required payload key; no undeclared key; payload key order matches the schema's
  `properties` order for all 46. `log.rotate`/`log.events_dropped` are absent from that stream but
  present (and conforming) in the rotation/drop streams. `x-families` matches the enum (`bullet`/`hud`
  reserved-unused, and no such cases exist ✓).

## 7. pbxproj, scheme, AGENTS.md

* **28 added lines = exactly 4 kinds × 5 files:** 5 `PBXBuildFile` (`project.pbxproj:22-26`), 5
  `PBXFileReference` (`:322-326`), a new `PBXGroup 400000000000000000000020 /* Diagnostics */` with 5
  children plus its registration in GameCore's children (6 structural lines), and 5
  `PBXSourcesBuildPhase` entries. The group's `path = Diagnostics; sourceTree = "<group>"` matches the
  real directory. Confirmed independently by the checker's unregistered-mutant control.
* **Scheme untouched:** `git status` shows only `project.pbxproj` modified under `Exolon.xcodeproj`;
  `xcshareddata/xcschemes/Exolon.xcscheme` is unmodified and `native_target_count` confirms one
  `PBXNativeTarget`.
* **AGENTS.md:** no new dependency (Foundation in Diagnostics, SpriteKit/Cocoa elsewhere —
  `diagnostics_import_boundary` PASS), no actor, no `fatalError`/`precondition`/`assert` on any emission
  path (the only match in Diagnostics is `GameplayEventLog.swift:14`, the comment asserting their
  absence), no `.github/workflows`, no protected-path edit, no log inside the clone
  (`forbid_log_in_clone` PASS; my `git status` stayed clean apart from the change itself).
* **Signature/compile sanity:** every changed signature has consistent call sites repo-wide
  (`DoubleLauncherObstacle(bottomLeft:entityID:)` 1 construction site at `TMXLevelRuntime.swift:347`;
  `teleportDestination` tuple `:248` → `GameScene.swift:309`; `collectDoubleLauncherBonus` tuple
  `:233` → `GameScene.swift:371`; `toggleExoskeleton(cause:)`/`setExoskeleton(_:cause:)` →
  `GameScene.swift:303, 1168`; `hitPlayer(cause:at:)` → 8 sites + definition `:722`).
  `swiftc -frontend -parse` is OK on all 12 touched sources. The test plan's manual `xcodebuild -target
  Exolon` row is still required: `-parse` cannot see overload or lane errors, which is exactly how
  R1-1/R1-4 compiled.

## 8. Behavior preservation (what I hunted hardest, since `intent=bugfix`)

Compared against `git show HEAD:` and judged equivalent: `hitPlayer`'s guards became if-returns with the
same truth table (`GameScene.swift:722-737`); the grenade one-in-flight rule split into
blocked/throw under the same condition (`:446-472`); `checkScreenExit`'s `playableNext` is De Morgan of
the base guard (`:739-750`); the stage award is R-equivalent to the removed base body (§4 P1-8);
`player.update` now receiving the unmasked snapshot is *safer* than base because the latch is armed
before the call (base's mask was what defeated `consumeContextualJumpPress`); `setExoskeleton` gained a
`hasExoskeleton != enabled` guard (`Player.swift:279-284`) so a restart cannot log a change that did not
happen; `previousUpdateTime`/`accumulator` semantics moved to the driver 1:1 (clamp, budget, early-return
ordering). Blocked-hit records are bounded, not per-step: every `invulnerability <= 0` caller guard is
preserved (`:624, 668, 679, 687, 693`), and the bubble/egg paths destroy the entity before `hitPlayer`,
so `damage.player_blocked` cannot flood the ring. `GameConstants.swift:5-12` is a comment-only
clarification of the 0.4 s window (TC-05), no value change.

## 9. Low / suggestions

* **S-1** `GameScene.swift:37` — `private lazy var tickDriver = FixedTickDriver(events: events)`
  snapshots `events` at first access, while the `events` `didSet` (`:29-34`) rebinds only
  `currentLevel`/`player`. Today the composition root injects before `presentScene`
  (`AppDelegate.swift:34-42`), so it is correct. Any later injection would silently leave tick/frame,
  heartbeats and all `tick.*` records in `NullGameplayEventSink` while everything else logs — i.e.
  `tick` frozen at 0 and `ts_us` 0 in a non-empty file, breaking INV-002 silently. Make the driver's
  sink settable from the `didSet`, or construct it eagerly.
* **S-2** The kill switch is file-inert, not path-inert. `README.md`'s new bullet — "`off` … restores the
  pre-change runtime path" — overstates it: `off` yields `mode = .off, level = 0`
  (`GameplayEventLog.swift:263-266` via `Configuration.resolved`), and `NullGameplayEventSink` is only
  `GameScene`'s *default* (`GameScene.swift:29`), never what the composition root injects. Level-0 kinds
  (`GameplayEventSink.swift:147-157`) still pass the gate and append to a ring that can never drain
  (`GameplayEventLog.swift:608`); `beginTick`/`beginFrame` still take the lock; every emit site still
  computes `GameplayEvent.q(...)` lanes before `emit` rejects them by level. Cost is nanoseconds and
  `kill_switch_no_file` genuinely passes, so this is a wording fix plus a note that the ring eventually
  laps (and counts drops) in a multi-day `.off` session.
* **S-3** Three contract fields are informationless by construction:
  `player.teleport.jump_latch_held` is read *after* `player.teleport(to:)` (`GameScene.swift:313-317`),
  which unconditionally sets `jumpWasPressed = true` (`Player.swift:240`) → always `true`, so it cannot
  distinguish "UP held" from "UP not held" (the comment at `:312-314` is honest that this is the
  inherited state); `input.contextual_consumed.jump_suppressed` is `physicalJumpHeld || latch`
  (`:1258-1262`) inside a block that only runs on `jumpJustPressed` → always `true`;
  `input.pause_consumed.pending` is emitted as the literal `1` (`:215`). AC-004 stays decidable, so this
  is a strengthening opportunity (capture the latch *before* the mutation, and report the physical key
  state), not a defect.
* **S-4** `log.end.reason` is a free-form `String` parameter (`GameplayEventLog.swift:529`,
  `AppDelegate.swift:59`) landing in an enum-constrained field; `GameplayLogEndReason`/`logEndReasonLabel`
  exist and are dumped by `contractDump` but never used on the wire path. Take the enum.
  `GameplayWire.flowLabel(forCode:)` (`GameplayEventSink.swift:637`) is unreferenced, and
  `LauncherBonusState.canFire` (`LauncherBonusState.swift:30`) has no product user
  (`DoubleLauncherObstacle` exposes `isActive` directly).
* **S-5** Comment/placement nits: the `teleportDestination` portal-index paragraph sits above
  `doubleLauncher(withEntityID:)` (`TMXLevelRuntime.swift:239-243`); "14 call sites" → 10
  (`GameScene.swift:827`); the 70/60 s settle delay is hardcoded twice (`:397` and `:1376`), so moving one
  silently makes `player.death_settled.delay_us` lie — hoist into `GameConstants`;
  `minimumLevel` uses `default:` (`GameplayEventSink.swift:156-157`) while `label` and `appendPayload` are
  exhaustive-on-purpose, so a new kind silently lands at level 1; `case let .suppressed(zone, reason)`
  …`_ = zone` (`GameScene.swift:774-776`) reads better as `case .suppressed(_, let reason)`; the
  `doubleLauncher(withEntityID:) == nil` path would award points with no `bonus.double_launcher` witness
  (unreachable today, worth an `else` counter).
* **S-6** `stats.written` returns `nextSeq` (`GameplayEventLog.swift:285-288`), which also counts
  writer-built lines, so "written" over-counts producer events by ≥1 per file. Only the harness reads it;
  rename or subtract.
* **S-7** The process-shared `DateFormatter` (`GameplayEventLog.swift:329-335`) is used only from the
  drain thread; `Formatter` is not thread-safe, so state that as a constraint if the log ever becomes
  multi-instance.

## 10. Required before this review passes

1. Fix R1-1, R1-2, R1-3, R1-4 — one-liners, all in the emission layer, none touching gameplay.
2. Add the table-driven lane check from §3 so the class of defect cannot return, and record the pending
   macOS E2E row from `test-plan.md` — it is the only thing that has ever executed a `GameScene` emission.
3. Correct or re-anchor the two writer records in §2 (`log.events_dropped.first_seq/last_seq`,
   `log.rotate` placement), keeping schema annotation and code in one direction.
4. Pick one direction for the R2-3 lane maps so `x-encode`, `GameplayEventKind.schemas`, the formatter
   and the call sites are one fact.

## 11. Gate re-run evidence (my run, this tree)

`RESULT: PASS (23/23 checks passed)` — AC-001 1298 motion / 1298 ticks, 0 dropped; AC-002 fixed 0 steps
after transition vs reverted 17 with predicate A failing; AC-003 1 award + 749 witnesses vs reverted 750
awards; AC-004 1 latch-held teleport, 0 leaks, hand-written violation stream fails predicate C; AC-005
1 payout + 40 subsequent shots, pre-fix control fails; AC-006 54.8 ns/event = 0.0197 % of a tick;
AC-007 5 files × 4 kinds, 1 native target; INV-001..004 PASS; FORBID-001..004 PASS; SIG-001/002 PASS.
Artifacts stayed outside the clone; the only side effect inside the tree is the gitignored
`evidence/__pycache__/` (`.gitignore:12`), so no tracked file changed and the bound verification receipt
is untouched by this review.
