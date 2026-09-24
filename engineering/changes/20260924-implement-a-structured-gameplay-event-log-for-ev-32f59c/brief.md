# Wave A: gameplay event log + fixed-tick/input/terminal state-machine fixes

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260924-implement-a-structured-gameplay-event-log-for-ev-32f59c`
Created: 2026-09-24T19:10:39+00:00
Route: `32f59cc7dcb6` · base `295690b7fc72` · branch `codex/wave-a-gameplay-log-tick-fixes-20260924`
Risk: medium · Domains: event · Workflow: bugfix + api-event-change

## Problem

The game emits nothing: 0 hits for print/NSLog/os_log/Logger/FileHandle across all product Swift
(`analysis-architect.md` §1). Every wave-A finding was proven in the 2026-09-20 audit only by code
tracing, and four are live state-machine defects:

- **P1-9** (`GameScene.swift:123-142,633-658`): `transition(to:)` resets 7 state fields but never
  `accumulator`/`previousUpdateTime`, so up to 15 catch-up steps run in the NEW zone inside the
  render frame that transitioned.
- **P1-4** (`Player.swift:113-116`): `update` rewrites `jumpWasPressed = input.jump` in the same
  step, so a held UP survives a teleport/changing-room consume and fires a jump on the next tick
  (reproduced executable: `analysis-architect.md` §1.1).
- **P1-8** (`GameScene.swift:609-631,708-765`): stage-boundary bonus has no idempotency flag;
  zone 124 (`x>510`, empty `nextLevel`) loops enterContentComplete→title→beginFromTitle,
  re-awarding `lives*1000` per FIRE cycle (750 awards in a 600 s probe run), persisted via
  `saveCheckpoint`.
- **P1-6** (`LevelObstacles.swift:717-722`): `collectDoubleLauncherBonus` is the sole `isActive`
  writer; collecting pays 1000 once and permanently kills the launcher with no restore path.

Without a log there is no cheap way to see tick/input/terminal anomalies — in tests or in the
field. User directive (2026-09-24): every player action and game event must be logged.

## Outcome

A structured, versioned, machine-parsable gameplay event log covering every player action and
game event, plus four regression-tested fixes. Each fix is assertable from the event stream alone
(predicates in `test-plan.md`); future findings in this state machine become a matter of reading
lines instead of tracing code.

## Scope

### In scope

- Foundation-only log core: 24-byte ring append (hot path) + batched async file writer + JSON-lines
  wire + in-memory sink for tests + `NullGameplayEventSink` default; injected from the composition
  root. Event contract frozen in `engineering/contracts/schemas/gameplay-event-v1.schema.json`.
- Pure-state extractions that make fixes Linux-testable: `FixedTickDriver`, `StageBoundaryLedger`,
  `LauncherBonusState`; `Player` gets `var events: (any GameplayEventSink)?`.
- Fixes: P1-9 accumulator reset on transition (never the `tick` counter); P1-4 latch suppression
  after contextual consume; P1-8 one-shot terminal/stage bonus with a visible suppression event;
  P1-6 separate bonus-paid from launcher-active (bonus pays once, launcher keeps firing).
- `state.flow` via `didSet`, input-edge snapshot diff in the tick loop, `entity.launcher_fire`
  event, `tick.heartbeat` every 600 ticks, F1 overlay tail via one reused `SKLabelNode`.
- Linux compile/run harness (extended 7-line `CGVector` shim) + committed self-checking verifier
  `evidence/gameplay_log_check.py`; pbxproj registration of every new file (4 edits each) verified
  by the gate.
- `GameConstants.swift` comment: stale 50 Hz note → 60 Hz (no behavior change).

### Out of scope

- P1-1 pistons; P1-2/P1-3/P1-5 (wave B); P1-7/P1-12 (wave C); P1-10/P1-11 remainder (wave D).
- A macOS XCTest target, SwiftPM, seeded RNG, per-tick entity state dumps (level 3), hud.banner
  events, a log viewer GUI.

## Design rulings (controller, where analysis reports differed)

1. **Wire = JSON-lines** (integration_architect §7), not the compact positional format the
   architect measured — formatting happens on the drain thread, never on the producer path; the
   producer only appends the 24-byte record (45.8–69.6 ns measured). Hand-written formatter emits
   only integers and whitelisted lowercase-ASCII labels; `log.begin` (once per file) may use
   JSONSerialization. Codable-per-event stays rejected (M5, 740×).
2. **Storage outside the clone, default `$TMPDIR/exolon/`** (integration §7 location hazard wins
   over architect's Caches): fingerprint-bound receipts treat untracked files inside the clone as
   tree changes. Writer directory injectable for tests; `EXOLON_EVENT_LOG=<path>|off` override;
   path echoed to stderr once at start.
3. **Names**: UInt8 enum on the wire (append-only raw values, unknown→`unknown<N>`); formatter maps
   to stable dotted names (`player.jump`, `state.zone_transition`, …); closed family set
   `meta,input,player,damage,bonus,state,tick` + reserved `bullet,entity,pickup,hud`.
4. **Counters**: `GameplayEventLog` owns `tick` (`beginTick(zone:)` sole mutator, first tick 1,
   never reset) plus `beginFrame()`; envelope key order
   `schema_version,seq,tick,frame,rot,ts_us,name`; `ts_us = round(tick*1_000_000/60)` derived,
   never accumulated (constant 16667 µs accumulation drifts +12 ms per 36 k ticks).
5. **Emission levels** 0/1/2; defaults: Debug=1, Release=off, tests=2; `player.motion` only at
   level 2; per-frame heartbeat banned; `tick.heartbeat` every 600 ticks is the only periodic record.
6. **Testability**: fixes live in SpriteKit-free types the Linux gate compiles as real product
   files; assertions run on harness-produced JSONL — a GameScene-logic replica inside the harness is
   never an assertion source.
7. **Retention**: 8 MiB × 8 files hard cap, 64 KiB buffer, flush at tick%60==0 and on
   state/damage/bonus/tick families, counted visible drops (`log.events_dropped`), rotation
   exercised by a test with tiny `maxFileBytes`.
8. **60 Hz is canonical** (`fixedTimeStep=1/60`); the stale 50 Hz comment is corrected, closing
   audit TC-05 by ruling.

## Constraints

- Backward compatibility: gameplay semantics change only in the four audited defects; kill switch
  `EXOLON_EVENT_LOG=off` restores byte-identical pre-change runtime behavior (no emission).
- Data/privacy: zero PII by construction — integer payloads + enum labels only, no free-text
  parameter on `emit`; `showBanner` logs a code, never the string; PID only, in the file name.
- Performance: hot path = one 24 B locked append (M2 55.5 ns); level-2 budget ≤ 5 % of a
  16.67 ms tick (measured 0.025 % at 60 ev/tick); writer off-thread, batched, `.utility` QoS.
- Operational: bounded disk (64 MiB cap); drops visible; no crash path on emit failure; log is
  never the only copy of anything authoritative; file location never inside the repository clone.

## Evidence and analysis

- `evidence/analysis-repo_explorer.md` — exact call sites, ~25 emit functions, choke points
  `hitPlayer:601`/`awardPoints:660`, pbxproj facts (1 target, 0 test targets, legacy file lists).
- `evidence/analysis-docs_researcher.md` — canonical mechanics per finding; spec gaps closed by
  ruling in `architecture.md` → Decisions.
- `evidence/analysis-architect.md` — measurements M1–M11, API shape, prototype failure modes
  (ring-is-backlog, drain-timer deadlock, tick-base off-by-one), pbxproj cost, F1 overlay rules.
- `evidence/analysis-integration_architect.md` — frozen contract: naming, envelope, catalog,
  retention numbers, stream-only predicates A–D, negative controls, typed spec rows.
