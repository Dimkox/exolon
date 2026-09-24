# Architect design judgment — structured gameplay event log (EV, route `32f59cc7dcb6`)

Change: `20260924-implement-a-structured-gameplay-event-log-for-ev-32f59c`
Role: read-only analysis agent over the product tree. Base commit `295690b7fc72` (matches
`route.json.base_commit`), branch `codex/wave-a-gameplay-log-tick-fixes-20260924`.
Nothing under `Exolon/` was modified. Every number below was measured in this session on this
host (Linux, Swift 6.4 `swiftc -O`, 28 logical CPUs) against the actual product sources; probes
live in `/tmp/exolon-probe/` (bench.swift, proto2.swift, proto3.swift, log_core.swift, drv/main.swift).

## 1. Verified baseline

| Fact | Verdict | Evidence |
| --- | --- | --- |
| There is **no logging seam at all** today | TRUE | `grep -rn "print(\|NSLog\|os_log\|Logger(\|FileHandle" --include=*.swift Exolon/` → **0 hits** |
| Fixed-step loop lives in `GameScene.update` | TRUE | `GameScene.swift:123-146`; accumulator declared `:51`; `accumulator += frameTime` `:131`; `while accumulator >= fixedTimeStep { fixedUpdate… }` `:133-136` |
| `transition(to:)` does **not** reset the accumulator | TRUE (this *is* P1-9) | `GameScene.swift:633-658`; `accumulator` appears only at `:51, :131, :133, :135` in the whole file |
| One fixed step is 1/60 s, frame time clamped to 0.25 s | TRUE | `GameConstants.swift:5-6` (`fixedTimeStep`, `maximumFrameTime`) → up to 15 catch-up steps per frame |
| `Player` owns the jump latch, and `update` overwrites it unconditionally | TRUE (this *is* P1-4) | `Player.swift:113-116` (`jumpWasPressed = input.jump`), `:256-258` (`consumeContextualJumpPress`), `:236-241` (`teleport` sets `jumpWasPressed = true`) |
| The only input thread-crossing point is `InputState` (NSLock) | TRUE | `InputState.swift:36-38`; gamepad handlers call `inputState.set(...)` from GameController callbacks (`GamepadInput.swift:50-95`); `GameScene.swift:149` samples it once per step |
| `TMXLevelRuntime.collectDoubleLauncherBonus` returns only points, losing entity identity | TRUE | `TMXLevelRuntime.swift:188-194`; the flag flip is `LevelObstacles.swift:718-723` (`isActive = false`, never restored) → blocks the P1-6 log line until the API returns the launcher index |
| Level objects are SpriteKit-bound | TRUE | `LevelObstacles.swift`, `TMXLevelRuntime.swift` store `SKSpriteNode`/`SKTexture` → they cannot enter a headless harness as-is |
| Xcode project = **1 app target, 0 test targets, legacy file lists** | TRUE | `project.pbxproj:1029-1042` (`com.apple.product-type.application`), no `PBXFileSystemSynchronizedRootGroup` (0 hits) → a new file needs 4 pbxproj edits (`PBXBuildFile` @8, `PBXFileReference` @308, `PBXGroup` @623, `PBXSourcesBuildPhase` @1359) |
| macOS only; unsandboxed; bundle id `com.exolon.remake` | TRUE | `SDKROOT = macosx` (`:1395,1407`), no `.entitlements` file, `PRODUCT_BUNDLE_IDENTIFIER` at `:1425,1444` |
| `grok_verify.py` has no Swift awareness | TRUE | `scripts/grok_verify.py` (30 lines) → `.grok-stack/adaptive_grok/verification.py`, `grep -rn "swift"` → 0 hits. Only `swiftc -frontend -parse` / real builds catch Swift breakage |
| `InputState.swift`, `GameConstants.swift`, `Player.swift`, `GameState.swift` **typecheck on Linux** | PARTLY TRUE | With `import CoreGraphics` shimmed, only `Player.swift:21,222` fail: `cannot find 'CGVector' in scope`. `CGRect/CGPoint/CGSize/CGFloat(.intersects)` come from swift-corelibs-**Foundation** and need no shim (measured); the repo's existing shim (`…7db1f3/evidence/harness/coregraphics_shim.swift`, one line: `@_exported import Foundation`) does **not** provide `CGVector` |

### 1.1 The decisive harness proof

Adding **7 lines** (`public struct CGVector { dx, dy, .zero }`) to that shim module is enough to
compile and **run** the real product `Player.swift` + `InputState.swift` + `GameConstants.swift`
together with the proposed Foundation-only log on this Linux host. I then drove the shipped
`Player` through a scripted fixed-step loop that mirrors `GameScene.swift:231-265`:

```
1 z0 jump   e1 a=0  b=512 c=512 d=0
2 z0 teleport e1 a=800 b=512
2 z0 jump   e1 a=0  b=512 c=512
3 z0 jump   e1 a=1  b=512 c=523      <-- a=1: a jump was taken on the step AFTER the teleport
3 z0 input  e1 a=1
--- P1-4 verdict ---
jumpedOnTick3=true velocity.dy=159.0 position.y=130.65
PASS REPRODUCED: held UP produces a jump on the step after a teleport (P1-4 is real)
```

So P1-4 is not a paper finding: it is executable here, and the tick-indexed event line is exactly
the artefact that makes it visible offline. This sets the whole testability bar for the design.

## 2. Measurements (why the shape below, and not the obvious shapes)

| # | Path under test | Cost | Note |
| --- | --- | --- | --- |
| M1 | fixed-layout struct append to a preallocated ring | **45.8 ns/event** | 6 M events, no formatting, no I/O |
| M2 | same append **under `NSLock`**, `@inline(never)` | **55.5 ns/event** | locking is *not* the problem |
| M3 | `beginTick` + `emit` (24 B record, mutex ring) | **69.6 ns/pair** | 500 k pairs in 34.8 ms |
| M4 | per-event `String` interpolation | **1 304 ns/event** (≈28× M1) | plus ~68 B of garbage per event |
| M5 | per-event `JSONSerialization` of `[String: Any]` | **33 907 ns/event** (≈740× M1) | 6.1 % of a 16.67 ms frame at 30 ev/tick |
| M6 | `FileHandle.write` **one line per event** | **1 945 ns/event** + syscall per event | 200 k events = 0.39 s |
| M7 | writer thread: format + batched 32 KiB writes | **1.40 M events/s**, 27.7 bytes/event | off the render thread, trivially keeps up |
| M8 | emit latency distribution while a 1 ms drain timer is active (producer unthrottled, ~1 300× the worst real rate) | p50 0.17 µs · p99 ~1.3–2.0 µs · p99.9 ~9 µs · max ≤ 362 µs | tail is dispatch wake-up noise, not batch size: sweeping `drainBatch` 64→2048 leaves p99.9 at ~9 µs |
| M9 | record size / memory | `MemoryLayout<Ev>.stride = 24 B` · 65 536-slot ring = **1.5 MiB** · 262 144 = 6 MiB | |
| M10 | correctness, realtime mode, ring > total events | **12 099 lines = 12 099 expected, dropped = 0**, ticks 1…8000 all present, file order non-decreasing | A1–A5 in `proto3.swift` |
| M11 | correctness, starved writer | backlog pinned at capacity 4 096, **495 904 drops counted**, newest tick retained | B1–B5 |

**Budget arithmetic for the real game.** Worst credible case 60 events per fixed step (tick marker +
10 input edges + 2 weapon + ≤10 bullets + ≤10 enemy bullets + hazards/pickups):
`60 × 70 ns = 4.2 µs` out of the 16 667 µs step = **0.025 %**. Real-time file volume:
`60 × 60 = 3 600 ev/s × 27.7 B ≈ 100 KB/s ≈ 6 MB/min`. Both numbers are what the retention
settings in §6 are sized against.

### 2.1 Two defects I actually hit while prototyping (they are the design's failure modes)

1. **A single-slot batch handoff silently loses almost everything.** My first prototype staged a
   512-event batch into one `ready` slot and the consumer read that slot. Result:
   **250 of 26 873 events reached the file (99.1 % loss)** — no crash, no error. Any design where
   the producer "hands the current batch to the writer" is wrong the moment the producer outruns
   the writer (which is exactly what a headless harness does). The correct handoff is *the ring
   itself* plus a consumer read cursor and an explicit drop counter.
2. **A `DispatchSourceTimer` scheduled on the drain queue must not call the `queue.sync` wrapper.**
   It produced a hard dispatch deadlock (`_dispatch_wait_for_queue` trap, Thread 3 crashed). The
   API must therefore split *on-queue body* from *cross-thread request*, and the harness mode must
   create **no queue at all**.
3. Minor but real: `beginTick` pre-incrementing from `startTick = 1` makes the first tick **2**.
   Pin the base explicitly (`tick` starts at 0, `beginTick` makes the first step 1) or the
   "monotonic from 1" acceptance criterion is silently off by one.

## 3. The four decisions the route asked for

**D1 — sync ring buffer + async file writer: yes, but "sync" means *synchronous append, no I/O*.**
`emit()` writes one 24-byte record into a preallocated ring under a mutex (M2: 55 ns) and returns.
A serial background queue drains in batches, formats text, and writes. Rationale: M4–M6 are each
20–700× the append cost, and only the append is on the 60 fps path. The mutex is affordable
(M2/M3 ≈ 0.025 % of the step), which *removes* the need for lock-free atomics — and lock-free
cleverness is precisely what produced defect 2.1/1. Chosen over the alternatives in §8.

**D2 — event names: `UInt8`-backed enum on the wire, `String` label resolved only in the formatter.**
The record stores `kind: UInt8`; `GameplayEventKind.label` is consulted on the drain thread when the
line is built. String names on the producer path cost M4 (1.3 µs + garbage); a `[String: Any]`
payload costs M5 (33.9 µs). Enum raw values are the stable wire contract — they must be **appended,
never renumbered**, and an unknown value must format as `unknown<N>` (not be silently mapped onto a
valid name, which is what `?? .rejected` in my prototype would have done).

**D3 — ownership: the composition root owns one concrete `GameplayEventLog`; everything else takes
`any GameplayEventSink`.** `main.swift`/`AppDelegate` builds it and injects it (`scene.events = log`,
`GamepadInput(inputState:scene.events…)`); `GameScene` passes it to `Player` and to
`TMXLevelRuntime`; the default is `NullGameplayEventSink.shared` so any object built without it
(including the current `didMove(to:)` order) behaves exactly as today. A `static let shared` reached
from inside the classes is rejected (§8, R4): the two P1 findings that need the log (P1-4, P1-9) are
only testable by constructing `Player` + a fake latch state directly, which a global defeats.
`GameState.swift:22` already ships the counter-example (`GamePersistence.shared` with a
`UserDefaults`-injecting `init(defaults:)` — inject the dependency, keep one shared convenience).

**D4 — how the fixed-tick loop exposes tick numbers: the log owns the counter; the loop calls
`beginTick(zone:)` once per executed fixed step.**
Call site: `GameScene.swift:133-136`, as the first statement inside the `while` body before
`fixedUpdate(dt:)`. Consequences that matter:
* tick advances only for steps that actually ran → the file shows 15 consecutive ticks inside one
  catch-up frame, which is the P1-9 signature;
* every `emit` between two `beginTick` calls is stamped with the same tick by construction, so the
  40+ call sites cannot pass (or disagree about) a tick number;
* pause/title/game-over do **not** freeze the counter (`fixedUpdate` returns early at `:151-207`
  but the step still ran) — that is desirable: a stalled tick counter is itself a symptom;
* `transition(to:)` must reset the **accumulator** and must **never** reset `tick`;
* `GameFlowState` changes become events (`flow`) so any tick can be attributed to a state.

## 4. Recommended API shape (Foundation only — no SpriteKit/AppKit/GameController import)

File: `Exolon/GameCore/Diagnostics/GameplayEventLog.swift` (plus
`GameplayEventSink.swift` if the split is preferred; see §7 for the pbxproj cost).

```swift
import Foundation   // deliberately NOT SpriteKit: this file must build in the Linux harness

/// Stable wire contract. Append-only: never renumber, never reuse.
enum GameplayEventKind: UInt8 {
    case tickBegin = 1, rawInput = 2, inputEdge = 3, jumpStart = 4, land = 5
    case teleport = 6, changingRoom = 7, contextualConsume = 8
    case fire = 9, grenadeLaunch = 10, bulletHit = 11, entityDestroyed = 12
    case pickupCollect = 13, bonusCollect = 14, launcherShot = 15
    case missileSpawn = 16, mineTrigger = 17, pistonContact = 18, forceFieldHit = 19
    case playerHit = 20, deathStart = 21, respawn = 22, invulnerabilityEnd = 23
    case flowChange = 24, zoneTransition = 25, stageBonus = 26, scoreAward = 27
    case highScoreChange = 28, checkpointSave = 29, checkpointClear = 30
    case contentComplete = 31, gameOver = 32, testModeToggle = 33, debugOverlayToggle = 34
    case guardRejected = 35            // an action was ignored by a rule

    /// Format-time only. Never call on the fixed-step path.
    var label: String { /* switch over all cases; no default: */ }
    var payloadSchema: String { /* "posX,posY,latchBefore,latchAfter" */ }
}

/// One record. 24 bytes, no reference fields, no String, no Array.
struct GameplayEvent {
    var tick: UInt64
    var zone: UInt16        // 0-based, `GameState.zone`; `zoneNumber(for:)` at GameScene.swift:988
    var kind: UInt8
    var entity: UInt16      // 0 = "the player / no subject"; else TMX object ordinal in the zone
    var a: Int16; var b: Int16; var c: Int16; var d: Int16

    /// Quarter-pixel quantization: ±8191 px, exact for the 512x384 logical field.
    static func q(_ v: CGFloat) -> Int16
    static func q(_ p: CGPoint) -> (Int16, Int16)
}

/// The seam every emitter depends on.
protocol GameplayEventSink: AnyObject {
    var tick: UInt64 { get }
    var zone: UInt16 { get }
    func beginTick(zone: Int)
    func emit(_ kind: GameplayEventKind, entity: UInt16,
              _ a: Int16, _ b: Int16, _ c: Int16, _ d: Int16)
    /// Read the last n records for the in-game view. Never blocks on I/O.
    func view(_ n: Int?) -> [GameplayEvent]
    func flush()
}

/// Positional payloads are unreadable at 40 call sites; give the important ones named helpers.
extension GameplayEventSink {
    func emitPosition(_ kind: GameplayEventKind, entity: UInt16 = 0, at: CGPoint,
                      state: Int16 = 0, state2: Int16 = 0)
    func emitScore(before: Int, after: Int, reason: GameplayEventKind)
    func emitFlow(from: GameFlowState, to: GameFlowState)
    func emitZoneTransition(from: String, to: String,
                            accumulatorBeforeMs: Int, pendingStepsBefore: Int)
    var isRecording: Bool { get }   // default true; Null sink returns false
}

final class NullGameplayEventSink: GameplayEventSink { static let shared = NullGameplayEventSink() }

enum GameplayEventWriterMode: Equatable { case off, synchronous, asynchronous }

final class GameplayEventLog: GameplayEventSink {
    struct Limits {
        var ringCapacity = 65_536          // power of two; 1.5 MiB; ~18 s of worst-case backlog
        var drainBatchEvents = 512         // 12 KiB copy-out; M8 says this is NOT a latency knob
        var maxFileBytes = 4_000_000       // ~40 s at 3 600 ev/s
        var keptFiles = 5                  // hard bound ~20 MB in Caches
        var viewEvents = 512               // in-game window
        var drainInterval: TimeInterval = 0.25
    }
    init(limits: Limits, writer: any GameplayEventWriter, mode: GameplayEventWriterMode)
    // mode == .asynchronous  -> owns one serial queue + timer (production)
    // mode == .synchronous   -> NO queue, no timer; flush() writes immediately (headless harness)
    // mode == .off           -> ring only, no writer object is ever touched (Release / kill switch)

    func beginTick(zone: Int)                       // the ONLY tick mutator
    func emit(_ kind: GameplayEventKind, entity: UInt16 = 0,
              _ a: Int16 = 0, _ b: Int16 = 0, _ c: Int16 = 0, _ d: Int16 = 0)   // hot path
    func view(_ n: Int? = nil) -> [GameplayEvent]
    var stats: (written: UInt64, pending: UInt64, dropped: UInt64) { get }
    func requestDrain()   // async hand-off; safe from any thread EXCEPT the drain queue
    func flush()          // synchronous barrier: harness assertions + applicationWillTerminate
    func shutdown()       // cancel timer, flush, close
}

/// Writer is injectable so tests never touch a real disk.
protocol GameplayEventWriter: AnyObject {
    func write(_ batch: String)
    func open(sessionToken: String)
    func close()
}
final class GameplayEventFileWriter: GameplayEventWriter    // Caches dir + rotation + prune
final class GameplayEventMemoryWriter: GameplayEventWriter  // harness: asserts on exact lines
```

Hard API rules for the implementer (all three are load-bearing):
1. The **ring is the backlog**. Producer and writer share one buffer with a read cursor; never
   replace "the pending batch" with a single slot (§2.1/1). Overflow must increment `dropped` and
   emit a `# dropped N oldest events` marker line so truncation is visible to the reader.
2. `drainInterval > 0` creates the queue; the timer's handler calls the **on-queue** body directly
   (`drainNow`), never the `queue.sync` wrapper (§2.1/2). `.synchronous` mode creates no queue.
3. `emit` must contain no `String`, no `Array`, no `Dictionary`, no `DateFormatter`, no `Data`,
   no `URL`, no closure allocation. Payload arguments are `Int16`, by value.

## 5. Integration points (file:line → what to emit)

| Site | Line(s) | Event | Payload that must be present |
| --- | --- | --- | --- |
| `GameScene.update` fixed-step loop | `:133-136` | `beginTick(zone:)` + `tickBegin` | `accumulatorMs`, `stepsThisFrame` (P1-9 evidence) |
| `transition` re-samples input twice | `:653-654` | (no new event; note for the fix) | — |
| `fixedUpdate` entry, input sample | `:148-149` | `inputEdge` per changed action | `InputSnapshot` bitmask before/after, `source` |
| pause edge | `:151-157` | `flowChange` | `from`, `to`, `stateBeforePause` |
| title / gameOver / contentComplete menu edges | `:160-205` | `flowChange`, `guardRejected` | selected index, menu action |
| invulnerability expiry | `:208-213` | `invulnerabilityEnd` | remaining ms |
| contextual UP: changing room | `:233-238` | `changingRoom`, `contextualConsume` | box origin, `hasExoskeleton` after |
| contextual UP: teleport | `:239-245` | `teleport`, `contextualConsume` | departure + destination, `jumpWasPressed` latch state |
| `player.consumeContextualJumpPress` + the `jump:false` snapshot | `:250-267` | `contextualConsume` | `sceneJumpWasPressed`, `playerJumpWasPressed` (P1-4 evidence — needs Player to emit; §5.1) |
| `player.update` / jump / land | `:270-273`, `Player.swift:113-116` | `jumpStart`, `land` | velocity.dy, grounded, position |
| solid resolution + ground refresh | `:275-281` | `guardRejected` on overlap fallback | resolution branch taken |
| `updateWeapons` fire / grenade | call `:285`, body `:338-360` | `fire`, `grenadeLaunch`, `guardRejected(noAmmo)` | ammo, grenades, origin, facing, exoskeleton twin |
| bullet collisions | `:362-410` | `bulletHit`, `entityDestroyed` | `entity` id of the victim, points awarded |
| grenade collisions | `:412-470` | `entityDestroyed`, `bonusCollect(guidance)` | centre, `guidanceHit.points` |
| enemy bullets vs player | `:472-499` | `playerHit` | bullet `kind`, invulnerability |
| pickups | `:501-516` | `pickupCollect` | pack type, ammo/grenades after (note `= 99` / `= 10` hard-coded) |
| lethal entities: missile/mine/piston/field/hazard/bubble/egg | `:518-599` | `mineTrigger`, `pistonContact`, `forceFieldHit`, `playerHit` | `entity`, box, `hasExoskeleton` |
| `hitPlayer` | `:601-607` | `playerHit` + `deathStart` + `flowChange` | lives, `testInvulnerabilityEnabled` |
| `checkScreenExit` | `:609-620` | `zoneTransition` or `contentComplete` | `playerX`, `nextLevelName`, `includedLevels.contains(next)` |
| `applyOriginalStageBoundaryIfNeeded` | `:622-631` | `stageBonus`, `scoreAward` | `completedZone`, `lives`, `livesBefore/After`, `pointsBefore/After` (P1-8 evidence) |
| `transition(to:)` | `:633-658` | `zoneTransition` + `checkpointSave` | **accumulator before/after**, pending steps, isStageStart, carriedY, parse ms |
| `updateDeathSequence` | `:311-336` | `respawn`, `flowChange`, `checkpointSave` | deathGroundTimer, lives after |
| `awardPoints` | `:660-666` | `scoreAward` | before, delta, after, highScore (the *only* funnel: 14 call sites) |
| `saveCheckpoint` / `clearCheckpoint` | `:696-706`, `:690`, `:722`, `:951` | `checkpointSave` / `checkpointClear` | levelName, ammo, grenades, points, lives |
| `beginFromTitle` / `enterGameOver` / `enterContentComplete` / `restartFromBeginning` / pause | `:708-765`, `:918-947`, `:949-986` | `flowChange` | from, to, `hasSavedCheckpoint` |
| pause-menu test-mode toggle | `:186-196` | `testModeToggle` | new value |
| `InputState.set` (gamepad/keyboard threads) | `InputState.swift:41-56` | `rawInput` | `source`, `action`, pressed |
| `Player` internals (only place that owns the latch) | `Player.swift:113-116, 236-241, 256-258` | `jumpStart`, `teleport`, `contextualConsume` | see §5.1 |
| `TMXLevelRuntime` level-side transitions | `:150-186, 188-194` | `launcherShot`, `missileSpawn`, `bonusCollect` | needs `entity` ids; see §5.2 |
| F1 debug view (in-game ring) | `GameScene.swift:1075-1114` | read-only `log.view(8)` | see §5.3 |

### 5.1 P1-4 forces the sink *into* `Player`
`jumpWasPressed` is private to `Player.swift:34`. The log cannot prove the latch behaviour from the
scene alone. Minimal, already-proven-safe change: `Player` gets `var events: any GameplayEventSink?`
(`nil` → zero cost, no behaviour change) and emits `jumpStart` / `land` / `contextualConsume`
with `latchBefore`/`latchAfter`. `Player.swift` imports only `CoreGraphics`+`Foundation`, so the
Foundation-only sink keeps it Linux-buildable — that is exactly the configuration that reproduced
P1-4 in §1.1.

### 5.2 Entity identity must be surfaced by the level runtime
`entity` is only useful if it is stable and joinable to the map. Recommend `entity` = the ordinal
index of the object in `map.objectGroups.flatMap { $0.objects }` (deterministic today:
`TMXLevelRuntime.swift:236`), stored on each obstacle as `let entityID: UInt16` at build time.
Consequence for P1-6: `collectDoubleLauncherBonus` (`TMXLevelRuntime.swift:188-194`) must return
`(points: Int, launcher: UInt16)` — or it emits itself — because today it discards which launcher
fired, and a `bonusCollect` line without the launcher id cannot evidence "permanently disabled".

### 5.3 The in-game view must not inherit the overlay's per-frame allocation habit
`updateDebugOverlay()` (`:1075-1114`) calls `removeAllChildren()` and builds new `SKShapeNode`s every
rendered frame. Do **not** add N more `SKShapeNode`s for events: format up to 8 lines from
`log.view(8)` into **one reused `SKLabelNode`**, and only when `showHitboxes` is on, throttled to
every 10th rendered frame. Formatting 8 lines costs ~10 µs (M4) — invisible there, fatal per event.

## 6. Retention, path, rotation, PII

* **Where**: `FileManager.default.url(for: .cachesDirectory, in: .userDomainMask)` in a subdirectory
  `com.exolon.remake/gameplay-events/` → macOS `~/Library/Caches/com.exolon.remake/…` (unsandboxed,
  measured bundle id), iOS `…/Containers/<app>/Library/Caches/…`, and on this Linux host
  `~/.cache` (measured: `.cachesDirectory → /home/pall/.cache`, `.libraryDirectory → NIL`). The
  **directory is injected** via `GameplayEventLog.Limits`/writer init so the harness points at a temp
  dir; the resolution helper lives in the platform layer (`AppDelegate`), never in the core.
* **Bound**: rotate at 4 MB → new generation file; keep 5 → hard cap ≈ 20 MB (≈3 min at the worst
  credible 3 600 ev/s, ≈12 min at a realistic 1 000 ev/s). Prune oldest-on-open as well, and never
  delete the file the writer currently holds. Caches is OS-purgeable — acceptable for a debug log,
  and a stated reason it must not be the only copy of anything authoritative.
* **In-game view**: the ring is the single bounded window (65 536 records = 1.5 MiB);
  `view(_:)` serves the overlay; `stats.dropped` is the health signal.
* **Line format** (append-only, machine-parsable, 27.7 B average):
  `# exolon-events v1 tz=UTC app=<ver> zones=125` header, then
  `<tick> z<zone> <label> [e<entity>] <p0> <p1> <p2> <p3>`;
  `# dropped N oldest events (writer behind)` where truncation happened. Positions as integers are
  quarter-pixels; document each kind's `payloadSchema` in one place. A future binary reader is a
  non-goal.
* **Zero PII/secrets**: payload slots are integers and enum labels only. No free text at all —
  `showBanner(_ text:)` (`:669`) logs a banner **code**, never the string. No file paths, no
  hostname, no user or account data, no `UserDefaults` dump, no device identifiers (PID only, in the
  file name). No names exist in this game today, so keep it that way by construction: reject any
  `String` parameter on `emit`.
* **Kill switch**: `ProcessInfo.processInfo.environment["EXOLON_EVENT_LOG"] == "off"`, or
  `mode = .off` in Release → satisfies the `rollback.strategy = forward_fix`, `maximum_steps = 1`
  in `change-spec.yaml` without a rebuild.

## 7. Build/verification reality for this repo (do not skip)

1. A new file needs **4 `project.pbxproj` edits** (§1 table). Neither `swiftc -frontend -parse` nor
   `grok_verify --mode pr` detects a missing entry (measured: 0 Swift references in the verifier), so
   a forgotten registration is invisible until someone runs `xcodebuild` on macOS.
2. Therefore the change must add a **Linux compile gate for the Foundation-only subset** — exactly
   the shape proven in §1.1:
   `swiftc -I ext -L ext -lCoreGraphics Exolon/GameCore/InputState.swift GameConstants.swift
   Player/Player.swift Diagnostics/GameplayEventLog.swift <harness>/main.swift` — plus the extended
   7-line `CGVector` shim committed as harness evidence. This is what makes the four P1 regression
   tests executable rather than aspirational, and it is the precedent the repo already set for
   `TMXMapLoader` (`decisions.md`, 2026-09-20: "Product code executes on Linux for the loader path").
3. `Player.swift` cannot be Linux-built without `CGVector` — so **do not** let the Diagnostics files
   acquire a `CGVector`/`SKNode` dependency, or the whole gate collapses. `CGFloat/CGPoint/CGRect`
   are safe (they come from Foundation on Linux).
4. `SWIFT_VERSION = 5.0` today. `GameplayEventLog` is a mutex-guarded class, so under a future Swift 6
   language mode it needs `@unchecked Sendable` (or an `os_unfair_lock`, which does not exist on
   Linux — keep `NSLock`). **Do not model the log as an `actor`**: the hot path needs a synchronous
   call, and an `await` hop from `fixedUpdate` is impossible.

## 8. Risks, and rejected alternatives

**R1 Producer outruns the writer (the real risk).**
* Measured safe today: M10 = 0 lost at 12 099 events with a 65 536 ring; M11 shows the failure mode is a **counted** drop once the ring laps.
* Mitigation is capacity math, not cleverness: 65 536 records ≈ 18 s of the worst-case 3 600 ev/s, while M7 says one drain clears a backlog at 1.4 M ev/s.
* A `# dropped` line must exist — silent truncation in a *debugging* artefact is worse than no artefact.

**R2 Thread-count assumption breaks.**
* Today's only cross-thread writer is `InputState` (gamepad callbacks); `rawInput` events therefore carry the tick that was current when the callback fired, not the tick that consumed it. Ordering authority is append order, and the doc must say so.
* If a second emitter thread appears later, nothing else changes: the append is already mutex-guarded (M2, 55 ns).
* `GameScene.swift:653-654` calls `inputState.snapshot()` **twice** inside `transition`, and `:1063` snapshots again per rendered frame; those extra locks are unrelated to this design but are visible in the same profile and worth not multiplying.

**R3 Cost measured on Linux is not cost on the device.**
* Every number above is `swiftc -O` on x86-64 Linux; Apple Silicon will differ in absolute ns but not in the 20–700× ordering between M1/M4/M5/M6, which is what the design rests on.
* The remaining unmodelled cost is `TMXLevelRuntime` construction *inside* the tick loop (`:633-640`: parse + textures) — already the worst spike in the game, and P1-9 amplifies it to 15 catch-up steps; the log measures it rather than causing it.
* Disk behaviour on a real macOS volume (APFS, FileVault, fsync) is unmeasured; hence `qos: .utility`, batched writes, and "the writer never blocks the producer" as the invariant.

**R4 Scope creep into the fixes themselves.**
* The sink is the deliverable; the four P1 fixes are separate commits with separate regression tests, and a `guardRejected`-style event must never be *invented* just to make a fix observable.
* Adding `var events` to `Player` is behaviour-neutral when `nil`; that is the line to hold.
* If the log and a fix disagree, the fix's test must assert on the log, not the log be relaxed to match the fix.

**R5 Volume in the headless harness.**
* An unthrottled harness emits ~4 M events/s (M3 arithmetic: one emit per 70 ns) — ~1 300× the worst real-time rate of 3 600 ev/s — so a writer flushed per emit would push ~110 MB/s of lines (27.7 B x 4 M, M7) straight into the user's disk.
* Harness default must be `mode = .off` or a `GameplayEventMemoryWriter` bounded to N lines; only the four P1 scenarios write files, and they write small ones.
* Rotation must also be exercised *by* a test (tiny `maxFileBytes`) so the prune path is not dead code.

**Rejected alternatives.**
* **`os.Logger` / Console.app (`import os`)** — Darwin-only, so the Linux gate in §7 dies; not injectable, so no deterministic assertions; the payload is a human sentence, so `tick`/`zone`/`entity` cannot be parsed back; no bounded in-game ring is reachable.
* **JSON-lines via `Codable`/`JSONEncoder` per event** — measured 33.9 µs/event (M5), 740× the append; 35 payload shapes force 35 Codable structs or an existential dictionary; the reader's keys become an unbounded, drifting schema; the size win is negative (27.7 B/line positional beats ~55 B/event measured for a 5-key JSON object).
* **Synchronous `FileHandle` append per event (no ring)** — 1.94 µs/event plus a syscall and a lock inside `fixedUpdate` (M6); latency spikes come from the filesystem, not from our code; there is nothing left to serve the in-game view; and the loss profile is worse than the ring's, because it is invisible.
* **`GameplayLog.shared` global reached from inside `Player`/`TMXLevelRuntime`/`GameScene`** — prevents a per-test recorder and a clean reset between harness cases, which is the whole point of requirement (b); `GamePersistence.shared` (`GameState.swift:22`) shows the injection fix already used in this repo; it makes a Release kill switch a runtime check at every call site; and it hides the SpriteKit/`CGVector` boundary that §7.3 depends on.
* **String event names + `[String: Any]` payload ("flexibility")** — M4/M5 numbers are exactly this shape; key spelling errors become invisible data bugs in a debugging tool; no stable contract to assert on; and `Int16` positions silently degrade to `Double`/`String`.
* **Full per-tick world-state snapshot instead of events** — ~1–2 KB/tick vs 27.7 B/event; SpriteKit-bound objects (`SKTexture`, node graphs) cannot be serialised from a headless harness at all, so it is less testable, not more.
* **Third-party logging framework (SwiftLog/SwiftyBeaver/CocoaLumberjack)** — a new dependency for an app target with zero test targets and no package pins today; `AGENTS.md` forbids it — "Do not introduce a service, database, queue, framework, or dependency without explicit architectural justification"; its API is level-and-message shaped, not tick-and-payload shaped; it adds its own queue and file policy, which are the exact things this change must own and bound.
* **Lock-free SPSC with atomics instead of `NSLock`** — the lock costs 10 ns/event over the unlocked append (M1→M2) against a 16 667 µs step; `os_unfair_lock` does not exist on Linux, and `Synchronization.Mutex` needs macOS 15+ against this target (`MACOSX_DEPLOYMENT_TARGET = 10.14`, `SWIFT_VERSION = 5.0`: `project.pbxproj:1394,1396`); and my prototype's lock-free handoff is what lost 99 % of the events (§2.1/1).

## 9. What the log must make provable, per finding

| Finding | Line that proves it | Assertion in the headless regression test |
| --- | --- | --- |
| P1-9 accumulator | `tickBegin` on the first tick of the new zone, carrying `accumulatorMs` | `zoneTransition` is followed by a tick with `pendingStepsBefore > 0` only on the *old* zone; after `transition`, `accumulatorMs < 16.67` and at most 1 step runs in that frame |
| P1-4 jump latch | `contextualConsume` (tick N) then `jumpStart` (tick N+1) with `latchBefore/latchAfter` | after a teleport with UP held, no `jumpStart` until an `inputEdge` shows release-then-press; §1.1 shows the failing trace exists today |
| P1-8 bonus farm | repeated `stageBonus` + `scoreAward` at the same `z124` | `count(stageBonus where zone == 124) <= 1` per playthrough; `pointsBefore/After` monotone per award and no duplicate bonus for one `completedZone` |
| P1-6 launcher | `bonusCollect e<launcher>` then `launcherShot e<launcher>` | shots from the same `entity` after the bonus are present (or the launcher is gone from the file at all, which is the *fixed* signature) |

## 10. Open items for the route owner

1. **Default in Release?** Recommend on in Debug and in the test build (which already resets the
   checkpoint on every launch, `GameScene.swift:685-695`), `mode = .off` in Release, both overridable
   by `EXOLON_EVENT_LOG`.
2. **Is the in-game F1 event view in scope?** It is requirement (d) as written, so yes — 8 lines in
   one reused `SKLabelNode` (§5.3), no new node types.
3. **`Player.events` + `TMXLevelRuntime` returning entity identity** are needed for P1-4 and P1-6 to
   be *observable*; they touch product files outside `Diagnostics/` and should be named explicitly in
   `tasks.md` so the single write owner is unambiguous.
4. **`governance/` is absent from this tree** (`ls Exolon`, `find . -maxdepth 2 -name governance`), so
   the governance sections of `requirements.md`/`architecture.md` cannot be filled from evidence; the
   change package's `acceptance_criteria`, `contracts.events`, `invariants` and `observability` arrays
   are all currently empty (`change-spec.yaml`) — they should be filled from §4/§6/§9 of this document
   before implementation, otherwise the verifier has nothing to bind to.
