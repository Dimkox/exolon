# Architecture — wave A (gameplay event log + state-machine fixes)

> Typed authority: [`change-spec.yaml`](change-spec.yaml). Full measurements and catalog:
> `evidence/analysis-architect.md`, `evidence/analysis-integration_architect.md`.

## Current behavior

No emission of any kind (0 logging hits in product Swift). The fixed-step loop is
`GameScene.update` (`GameScene.swift:123-146`): `accumulator += min(frameTime, 0.25)` then
`while accumulator >= 1/60 { fixedUpdate(dt) }`. `transition(to:)` (`:633-658`) swaps the
level runtime and resets 7 scene fields but not `accumulator`/`previousUpdateTime` (P1-9).
`Player.update` unconditionally re-samples `jumpWasPressed = input.jump` each step
(`Player.swift:113-116`), so a contextual consume followed by a held UP becomes a jump
(P1-4). `applyOriginalStageBoundaryIfNeeded` (`GameScene.swift:622-631`) has no idempotency
flag and runs before the terminal guard (`:612` vs `:614`); the zone-124 title loop re-awards
`lives*1000` per FIRE cycle (P1-8). `collectDoubleLauncherBonus` flips the launcher's sole
`isActive` flag (`LevelObstacles.swift:717-722`) and returns only points — bonus payment
destroys the weapon and its identity (P1-6).

## Proposed behavior

Same gameplay except the four audited defects. A `GameplayEventLog` (Foundation-only) receives
every player action and game state change as a 24-byte record appended under `NSLock` into a
preallocated ring (the ring IS the file backlog), drained and formatted to JSON-lines by one
serial `.utility` queue (production) or written synchronously (harness `.synchronous` mode,
`.off` mode = no writer touched). Default sink is `NullGameplayEventSink.shared`, so anything
constructed without injection behaves exactly as today.

## Components and boundaries

| Component | File (Foundation-only unless noted) | Responsibility |
| --- | --- | --- |
| `GameplayEventSink` + `GameplayEvent` + `GameplayEventKind` | `Exolon/GameCore/Diagnostics/GameplayEventSink.swift` | the seam; protocol + 24 B struct + UInt8 wire enum + payloadSchema strings |
| `GameplayEventLog` | `Exolon/GameCore/Diagnostics/GameplayEventLog.swift` | ring, counters (`beginTick`/`beginFrame`), drop counter, modes off/sync/async, `view(_:)`, `flush()`, `shutdown()` |
| Writers | same file | `GameplayEventWriter` protocol; `GameplayEventFileWriter` (JSONL, `$TMPDIR/exolon/` default, injectable dir, 8 MiB × 8 rotation, 64 KiB buffered); `GameplayEventMemoryWriter` (harness) |
| `FixedTickDriver` | `Exolon/GameCore/Diagnostics/FixedTickDriver.swift` | clamp+accumulator+budget (15)+step loop+`reset(reason:)`; GameScene delegates (P1-9) |
| `StageBoundaryLedger` | `Exolon/GameCore/Diagnostics/StageBoundaryLedger.swift` | once-per-playthrough award at zones 24/49/74/99/124 + explicit suppression outcome (P1-8) |
| `LauncherBonusState` | `Exolon/GameCore/Diagnostics/LauncherBonusState.swift` | `active` (fire gate) separated from `bonusCollected` (pay-once); pure value type (P1-6) |
| `Player` | product, SpriteKit-free | gets `var events: (any GameplayEventSink)?`; emits `player.jump/land/contextual*`, fixes latch (P1-4) |
| `GameScene` | product, SpriteKit | emit call sites (~25 fns), `state.flow` via `didSet`, input-edge snapshot diff per tick; single-thread emitter |
| Composition root | `main.swift`/`AppDelegate` | builds the concrete log from env/config, injects into scene → runtime → player |

Boundary rule: nothing under `Diagnostics/` may import SpriteKit or use `CGVector`
(keeps the Linux gate alive; `CGFloat/CGPoint/CGRect` from corelibs-Foundation are safe).

## Data flow

`update(_:)` → `beginFrame()` → `FixedTickDriver.step` → per executed step: `beginTick(zone:)`
→ `fixedUpdate(dt:)` → gameplay mutates state AND appends records → serial queue drains ring →
formatter maps UInt8 kind → stable dotted name → JSONL file + stderr-echoed path → consumers:
in-memory sink (tests), Python auditors (`json.loads`), human (`tail -f`, F1 overlay via
`view(8)` in one reused `SKLabelNode`, throttled to every 10th rendered frame, gated on
`showHitboxes`).

Ordering claim (normative): events are emitted synchronously into the ring from one thread — the
SpriteKit update thread — at the point where the state change happens; `seq` is assigned by the
single formatter writer and strictly +1 within `(run_id, rot)`; `tick`, `frame` are
non-decreasing along the file; therefore the stream is a total order. Input edges come from a
per-tick snapshot diff inside the loop, never from `InputState.set`.

## API and event contracts

- Wire: JSON-lines, envelope key order `schema_version,seq,tick,frame,rot,ts_us,name` + payload;
  `ts_us = round(tick*1_000_000/60)`; `schema_version=1` every line; `log.begin` carries
  `run_id,build,wall_utc,level,path,seed,zone,flow_state`.
- Names: `<family>.<object>_<verb>`, closed wave-A families `meta,input,player,damage,bonus,state,tick`
  (+ reserved `bullet,entity,pickup,hud`); `bonus.stage_boundary_suppressed` and
  `entity.launcher_fire` are mandatory witnesses.
- Frozen in: `engineering/contracts/schemas/gameplay-event-v1.schema.json` (committed with this
  change; Swift formatter and Python auditors test against it).
- Compatibility: adding an optional payload field is non-breaking; renaming/removing/type-change is
  a `schema_version` bump; consumers reject unknown majors.

## Governance context

`governance/` does not exist in this tree — sections not applicable (see `requirements.md`).

## Bitrix-specific impact

Not applicable (generic Swift game repository).

## Decisions

Eight controller rulings (format=JSONL, path=$TMPDIR, names, counters, levels, testability,
retention, 60 Hz) are recorded in `brief.md` → Design rulings; measurements behind each:
`analysis-architect.md` §2/§8, `analysis-integration_architect.md` §4–7. Spec gaps from
`analysis-docs_researcher.md` are closed by ruling:

1. **P1-4 no-jump promise becomes normative** (source only in README:23; OM silent): a jump latch
   consumed by a contextual action is suppressed until a fresh UP release→press edge. Implemented
   as latch state, tested headless on real `Player.swift`.
2. **P1-6 bonus region semantics**: OM never defines the invisible region or post-bonus firing.
   Ruling: collect pays 1000 once per launcher per zone instantiation; the launcher CONTINUES to
   fire under the existing proximity rule (stop only when Vitorc ≤ 110 px); `isActive` remains the
   fire gate; payout tracked by separate `bonusCollected`. Identity returned by
   `TMXLevelRuntime.collectDoubleLauncherBonus` → `(points, entityID)`.
3. **P1-8 terminal/one-shot definition**: stage-end trigger geometry stays the existing
   `x > 510` screen-exit check (no new geometry invented); a playthrough is
   `restart/title_enter → game_over/title_enter`; each `completed_zone` may award at most once
   per playthrough; every suppressed repeat MUST emit the witness event.
4. **P1-9 transition timing definition**: `transition()` runs inside a fixed step; the remaining
   accumulator is discarded (`tick.accumulator_reset{reason:"zone_transition",discarded_us}`),
   and no step may run in the new zone inside the render frame that transitioned into it.
5. **TC-05**: 60 Hz canonical; stale 50 Hz comment corrected (issue #13's "define transition
   timing" is satisfied by ruling 4).

## Risks and mitigations

| Risk | Mitigation (measured) |
| --- | --- |
| Producer outruns writer | ring = backlog, 65 536 × 24 B ≈ 18 s worst-case; drain clears 1.4 M ev/s (M7); overflow is counted + marker line, never silent |
| Drain timer + `queue.sync` deadlock (found in prototype) | API splits on-queue body from cross-thread request; `.synchronous` harness mode creates no queue |
| Harness floods disk (~4 M ev/s unthrottled) | harness default `.off`/memory writer; only the 4 scenario tests write small files |
| Missing pbxproj registration invisible on Linux | gate script greps 4 marker kinds per new file (AC-007) |
| Cost measured on Linux ≠ Apple Silicon | design rests on the 20–740× RELATIVE ordering of M1/M4/M5/M6, not absolute ns |
| Log contradicts a fix | fix tests assert on the log stream; never relax the log to match a fix |
| RNG nondeterminism breaks absolute-tick asserts | predicate style forbids absolute-tick assertions (16 unseeded sites) |
