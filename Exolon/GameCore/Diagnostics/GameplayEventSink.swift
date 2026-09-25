import Foundation

/// The seam every emitter depends on. Foundation-only on purpose: nothing in this file may
/// import SpriteKit or use `CGVector`, because the Linux gate in
/// `engineering/changes/20260924-implement-a-structured-gameplay-event-log-for-ev-32f59c/evidence/harness/`
/// compiles these files as real product sources (architecture.md -> Boundary rule).
///
/// Frozen contract: `engineering/contracts/schemas/gameplay-event-v1.schema.json`.
/// Renaming a `label`, renumbering a raw value or dropping a payload lane is a
/// `schema_version` bump, not an edit.

/// Stable wire contract, appended by `integration_implementer` wave A.
///
/// Rules (brief.md ruling 3, architect ruling D2):
/// * raw values are the wire identity: **append only**, never renumber, never reuse;
/// * the record carries the raw value, the String label is resolved in the formatter only;
/// * a raw value with no case formats as `unknown<N>` and never aliases a real name.
enum GameplayEventKind: UInt8 {
    // meta — written by the stream writer, never by the producer path (raw values reserved so
    // the numbering below stays the numbering of the frozen catalog).
    case logBegin = 1
    case logRotate = 2
    case logEventsDropped = 3
    case logEnd = 4
    // input
    case inputActionEdge = 5
    case inputPauseConsumed = 6
    case inputContextualConsumed = 7
    // player
    case playerMotion = 8
    case playerJump = 9
    case playerLand = 10
    case playerCrouchBegin = 11
    case playerCrouchEnd = 12
    case playerExoskeleton = 13
    case playerShootBlaster = 14
    case playerShootDenied = 15
    case playerThrowGrenade = 16
    case playerTeleport = 17
    case playerDeathBegin = 18
    case playerDeathLanded = 19
    case playerDeathSettled = 20
    // game / damage
    case gameGameOver = 21
    case damagePlayerBlocked = 22
    case damagePlayerHit = 23
    // pickup / bonus / score
    case pickupCollect = 24
    case bonusDoubleLauncher = 25
    case bonusStagePoints = 26
    case bonusStageComponent = 27
    case bonusStageBoundarySuppressed = 28
    case scoreAwarded = 29
    case scoreHighScoreSaved = 30
    // state
    case stateFlow = 31
    case stateZoneLoad = 32
    case stateZoneLoaded = 33
    case stateZoneExit = 34
    case stateZoneTransition = 35
    case stateContentComplete = 36
    case stateTitleEnter = 37
    case stateCheckpointSaved = 38
    case stateCheckpointCleared = 39
    case statePauseEnter = 40
    case statePauseExit = 41
    case stateRestart = 42
    case stateCheatInvulnerability = 43
    // tick anomalies
    case tickFrameGapClamped = 44
    case tickAccumulatorReset = 45
    case tickSlowStep = 46
    case tickHeartbeat = 47
    // entity
    case entityLauncherFire = 48

    /// raw value -> frozen dotted name. Derived from `label`, so the switch below stays the single
    /// source of truth; the harness dumps it to `contract.txt` and the checker diffs it against the
    /// schema, which makes an accidental renumbering or a dropped case visible on Linux.
    static let names: [UInt8: String] = Dictionary(
        uniqueKeysWithValues: (UInt8(1) ... UInt8(48)).compactMap { raw -> (UInt8, String)? in
            guard let kind = GameplayEventKind(rawValue: raw) else { return nil }
            return (raw, kind.label)
        }
    )

    /// The stable dotted name. Resolved on the drain thread only.
    /// No `default:` on purpose: adding a case must break this switch, so a new kind can never
    /// silently borrow another name.
    var label: String {
        switch self {
        case .logBegin: return "log.begin"
        case .logRotate: return "log.rotate"
        case .logEventsDropped: return "log.events_dropped"
        case .logEnd: return "log.end"
        case .inputActionEdge: return "input.action_edge"
        case .inputPauseConsumed: return "input.pause_consumed"
        case .inputContextualConsumed: return "input.contextual_consumed"
        case .playerMotion: return "player.motion"
        case .playerJump: return "player.jump"
        case .playerLand: return "player.land"
        case .playerCrouchBegin: return "player.crouch_begin"
        case .playerCrouchEnd: return "player.crouch_end"
        case .playerExoskeleton: return "player.exoskeleton"
        case .playerShootBlaster: return "player.shoot_blaster"
        case .playerShootDenied: return "player.shoot_denied"
        case .playerThrowGrenade: return "player.throw_grenade"
        case .playerTeleport: return "player.teleport"
        case .playerDeathBegin: return "player.death_begin"
        case .playerDeathLanded: return "player.death_landed"
        case .playerDeathSettled: return "player.death_settled"
        case .gameGameOver: return "game.game_over"
        case .damagePlayerBlocked: return "damage.player_blocked"
        case .damagePlayerHit: return "damage.player_hit"
        case .pickupCollect: return "pickup.collect"
        case .bonusDoubleLauncher: return "bonus.double_launcher"
        case .bonusStagePoints: return "bonus.stage_points"
        case .bonusStageComponent: return "bonus.stage_component"
        case .bonusStageBoundarySuppressed: return "bonus.stage_boundary_suppressed"
        case .scoreAwarded: return "score.awarded"
        case .scoreHighScoreSaved: return "score.high_score_saved"
        case .stateFlow: return "state.flow"
        case .stateZoneLoad: return "state.zone_load"
        case .stateZoneLoaded: return "state.zone_loaded"
        case .stateZoneExit: return "state.zone_exit"
        case .stateZoneTransition: return "state.zone_transition"
        case .stateContentComplete: return "state.content_complete"
        case .stateTitleEnter: return "state.title_enter"
        case .stateCheckpointSaved: return "state.checkpoint_saved"
        case .stateCheckpointCleared: return "state.checkpoint_cleared"
        case .statePauseEnter: return "state.pause_enter"
        case .statePauseExit: return "state.pause_exit"
        case .stateRestart: return "state.restart"
        case .stateCheatInvulnerability: return "state.cheat_invulnerability"
        case .tickFrameGapClamped: return "tick.frame_gap_clamped"
        case .tickAccumulatorReset: return "tick.accumulator_reset"
        case .tickSlowStep: return "tick.slow_step"
        case .tickHeartbeat: return "tick.heartbeat"
        case .entityLauncherFire: return "entity.launcher_fire"
        }
    }

    /// The human-readable lane map of this kind, mirroring `x-encode` in the frozen schema.
    var payloadSchema: String { GameplayEventKind.schemas[self.rawValue] ?? "unknown" }

    /// Minimum emission level (brief.md ruling 5).
    /// Exhaustive on purpose (same rule as `label`): appending a kind forces an explicit level
    /// choice instead of silently inheriting level 1 (brief ruling 5).
    var minimumLevel: Int {
        switch self {
        case .playerMotion:
            return 2
        case .stateFlow, .stateZoneLoad, .stateZoneLoaded, .stateZoneExit, .stateZoneTransition,
             .stateContentComplete, .stateTitleEnter, .stateCheckpointSaved, .stateCheckpointCleared,
             .statePauseEnter, .statePauseExit, .stateRestart, .stateCheatInvulnerability,
             .tickFrameGapClamped, .tickAccumulatorReset, .tickSlowStep, .tickHeartbeat,
             .logBegin, .logRotate, .logEventsDropped, .logEnd:
            return 0
        case .inputActionEdge, .inputPauseConsumed, .inputContextualConsumed,
             .playerJump, .playerLand, .playerCrouchBegin, .playerCrouchEnd, .playerExoskeleton,
             .playerShootBlaster, .playerShootDenied, .playerThrowGrenade, .playerTeleport,
             .playerDeathBegin, .playerDeathLanded, .playerDeathSettled,
             .gameGameOver, .damagePlayerBlocked, .damagePlayerHit, .pickupCollect,
             .bonusDoubleLauncher, .bonusStagePoints, .bonusStageComponent,
             .bonusStageBoundarySuppressed, .scoreAwarded, .scoreHighScoreSaved, .entityLauncherFire:
            return 1
        }
    }

    /// Family of the dotted name; the closed wave-A set plus the catalog names integration
    /// section 8 freezes (`pickup`, `entity`, `game`, `score`) — see the schema's x-families note.
    var family: String {
        guard let dot = label.firstIndex(of: ".") else { return "" }
        return String(label[label.startIndex..<dot])
    }

    /// Lane maps, keyed by raw value so a consumer can dump the whole table
    /// (the harness prints it to `contract.txt` and the checker diffs it against the schema's
    /// `x-encode` values, which is what keeps this comment block and the contract one fact
    /// instead of two). A `*_q` lane is a quarter-pixel integer, `*_i32` spans two consecutive
    /// lanes (high, low), `entity=` is the subject lane (an ordinal, or a packed bitfield for
    /// subject-free kinds), and every `*_zone` payload field is the record's zone lane.
    static let schemas: [UInt8: String] = [
        1: "writer-built",
        2: "writer-built",
        3: "writer-built",
        4: "writer-built",
        5: "entity=pack(action:0..5,source:6..7),a=held_ms,b=pressed",
        6: "a=pending",
        7: "entity=contextual_kind,a=jump_suppressed",
        8: "a=x_q,b=y_q,c=vx_q,d=vy_q,entity=pack(motion:0..2,grounded:3,facing:4,exoskeleton:5)",
        9: "a=x_q,b=y_q,c=velocity_q,entity=pack(grounded_before:0,after_teleport:1)",
        10: "a=x_q,b=y_q,c=vy_before_q,entity=support",
        11: "a=x_q,b=y_q",
        12: "a=x_q,b=y_q",
        13: "a=enabled,entity=cause",
        14: "a=x_q,b=y_q,c=ammo_before,d=ammo_after,entity=pack(facing:0,double:1)",
        15: "a=ammo,entity=reason",
        16: "a=x_q,b=y_q,c=grenades_before,d=grenades_after,entity=pack(direction:0,blocked_by:1)",
        17: "a=from_x_q,b=from_y_q,c=to_x_q,d=to_y_q,entity=pack(portal_index:0..7,jump_latch_held:8)",
        18: "a=x_q,b=y_q,c=lives,d=ammo,entity=grenades",
        19: "a=x_q,b=y_q,c=ground_ticks",
        20: "a=lives_before,b=lives_after,c=invulnerability_ticks,d=delay_ticks,entity=pack(checkpoint_saved:0)",
        21: "a,b=points_i32,c,d=high_score_i32,entity=pack(checkpoint_cleared:0)",
        22: "a,b=invulnerability_us_i32,c=pack(cause:0..5,test_invulnerability:6)",
        23: "a=x_q,b=y_q,c=pack(cause:0..5,flow_before:6..8,flow_after:9..11),d=lives",
        24: "a=x_q,b=y_q,c=count_before,d=count_after,entity=kind",
        25: "a=points,b=x_q,c=y_q,d=launcher_active_after,entity=launcher_object_ordinal",
        26: "a,b=points_i32,entity=pack(lives_before:0..3,lives_after:4..7,ammo_reset:8)",
        27: "a=points,entity=component_id",
        28: "entity=reason",
        29: "a=points,b,c=points_before_i32,entity=reason",
        30: "a,b=value_i32",
        31: "a=from,b=to,c=cause",
        32: "entity=cause",
        33: "a=solid_count,b=spawn_x_q,c=spawn_y_q,d=ground_y_q,entity=pack(invulnerability_ticks:0..8,carried_y:9)",
        34: "a=trigger_x_q,b=player_x_q,entity=has_next_level",
        35: "a,b=accumulator_us_i32,c=pending_steps,entity=to_zone",
        36: "a,b=points_i32,entity=pack(final:0,has_next_level:1)",
        37: "a,b=high_score_i32,entity=pack(has_saved_checkpoint:0)",
        38: "b,c=points_i32,entity=pack(ammo:0..6,grenades:7..11,lives:12..15)",
        39: "entity=reason",
        40: "a=state_before,b=selected_index",
        41: "a=state_before,b=selected_index",
        42: "a,b=points_i32",
        43: "a=enabled,b=menu_index",
        44: "a,b=raw_frame_time_us_i32",
        45: "a,b=discarded_us_i32,c=discarded_steps,entity=reason",
        46: "a,b=step_us_i32,c=steps_this_frame",
        47: "a,b=events_i32,c,d=drops_i32,entity=flow_code",
        48: "a=x_q,b=y_q,c=muzzle_y_q,entity=launcher_object_ordinal"
    ]
}

/// One record. Fixed 24 bytes, no reference field, no String, no collection: the harness asserts
/// `MemoryLayout<GameplayEvent>.stride == 24` (measurement M9, architect section 2).
struct GameplayEvent {
    var tick: UInt32
    var frame: UInt32
    var zone: UInt16
    var entity: UInt16
    var kind: UInt8
    var a: Int16
    var b: Int16
    var c: Int16
    var d: Int16

    static let zero = GameplayEvent(tick: 0, frame: 0, zone: 0, entity: 0, kind: 0, a: 0, b: 0, c: 0, d: 0)

    // MARK: Lane helpers (integer only, all allocation-free)

    /// Quarter-pixel quantization: +/- 8191 px, exact for the 512x384 logical field.
    static func q(_ value: CGFloat) -> Int16 {
        let scaled = value * 4
        if scaled >= CGFloat(Int16.max) { return Int16.max }
        if scaled <= CGFloat(Int16.min) { return Int16.min }
        return Int16(scaled.rounded())
    }

    static func q(_ point: CGPoint) -> (Int16, Int16) { (q(point.x), q(point.y)) }

    /// Split a 32-bit value over two 16-bit lanes (hi, lo). Values stay non-negative.
    static func split(_ value: Int32) -> (Int16, Int16) {
        (Int16(truncatingIfNeeded: value >> 16), Int16(truncatingIfNeeded: value & 0xFFFF))
    }

    static func split(_ value: Int) -> (Int16, Int16) {
        split(Int32(max(0, min(Int(Int32.max), value))))
    }

    static func join(high: Int16, low: Int16) -> Int32 {
        (Int32(high) << 16) | Int32(UInt16(bitPattern: low))
    }

    /// Bit-packed lanes travel as unsigned bit patterns.
    static func lane(_ bits: UInt16) -> Int16 { Int16(bitPattern: bits) }
    static func word(_ laneValue: Int16) -> UInt16 { UInt16(bitPattern: laneValue) }
    static func word(_ laneValue: Int32) -> UInt16 { UInt16(truncatingIfNeeded: laneValue) }

    /// `round(n * 1_000_000 / 60)`: derived from a step count, never accumulated (M9/ruling 4;
    /// accumulating the rounded constant 16667 drifts +12 ms per 36 k ticks).
    static func microseconds(fromSteps steps: Int) -> Int {
        Int((Int64(steps) * 1_000_000 + 30) / 60)
    }
}

/// Producer-side lane packing. Every function here is integer-only and allocation-free, so the
/// emission sites stay readable without putting a String anywhere near the fixed-step path.
/// Bit positions mirror `x-encode` in the frozen schema.
enum GameplayPack {
    /// motion:0...2, grounded:3, facing:4, exoskeleton:5 (`player.motion`, entity lane).
    static func motion(state: UInt16, grounded: Bool, facing: UInt16, exoskeleton: Bool) -> UInt16 {
        (state & 0b111) | (grounded ? 1 << 3 : 0) | ((facing & 1) << 4) | (exoskeleton ? 1 << 5 : 0)
    }

    /// action:0...5, source:6...7 (`input.action_edge`, entity lane).
    static func edge(action: UInt16, source: UInt16) -> UInt16 {
        (action & 0b11_1111) | ((source & 0b11) << 6)
    }

    /// grounded_before:0, after_teleport:1 (`player.jump`, entity lane).
    static func jumpWitness(groundedBefore: Bool, afterTeleport: Bool) -> UInt16 {
        (groundedBefore ? 1 : 0) | (afterTeleport ? 2 : 0)
    }

    /// facing:0, double:1 (`player.shoot_blaster`, entity lane).
    static func blaster(facing: UInt16, double: Bool) -> UInt16 {
        (facing & 1) | (double ? 2 : 0)
    }

    /// direction:0, blocked_by:1 (`player.throw_grenade`, entity lane).
    static func grenadeThrow(direction: UInt16, blockedByOneInFlight: Bool) -> UInt16 {
        (direction & 1) | (blockedByOneInFlight ? 2 : 0)
    }

    /// portal_index:0...7, jump_latch_held:8 (`player.teleport`, entity lane).
    static func teleport(portalIndex: Int, jumpLatchHeld: Bool) -> UInt16 {
        (UInt16(truncatingIfNeeded: portalIndex) & 0xFF) | (jumpLatchHeld ? 1 << 8 : 0)
    }

    /// cause:0...5, flow_before:6...8, flow_after:9...11 (`damage.player_hit`, c lane).
    static func hit(cause: UInt16, before: UInt16, after: UInt16) -> UInt16 {
        (cause & 0b11_1111) | ((before & 0b111) << 6) | ((after & 0b111) << 9)
    }

    /// cause:0...5, test_invulnerability:6 (`damage.player_blocked`, c lane).
    static func blocked(cause: UInt16, testInvulnerability: Bool) -> UInt16 {
        (cause & 0b11_1111) | (testInvulnerability ? 1 << 6 : 0)
    }

    /// checkpoint_saved:0 (`player.death_settled`, entity lane).
    static func settled(checkpointSaved: Bool) -> UInt16 { checkpointSaved ? 1 : 0 }

    /// checkpoint_cleared:0 (`game.game_over`, entity lane).
    static func gameOver(checkpointCleared: Bool) -> UInt16 { checkpointCleared ? 1 : 0 }

    /// final:0, has_next_level:1 (`state.content_complete`, entity lane).
    static func contentComplete(final: Bool, hasNextLevel: Bool) -> UInt16 {
        (final ? 1 : 0) | (hasNextLevel ? 2 : 0)
    }

    /// has_saved_checkpoint:0 (`state.title_enter`, entity lane).
    static func titleEnter(hasSavedCheckpoint: Bool) -> UInt16 { hasSavedCheckpoint ? 1 : 0 }

    /// ammo:0...6, grenades:7...11, lives:12...15 (`state.checkpoint_saved`, entity lane).
    /// 7+5+4 = 16 bits exactly: the previous 6-bit grenades field overlapped `lives` at bit 12.
    static func checkpoint(ammo: Int, grenades: Int, lives: Int) -> UInt16 {
        (UInt16(truncatingIfNeeded: ammo) & 0b111_1111)
            | ((UInt16(truncatingIfNeeded: grenades) & 0b11111) << 7)
            | ((UInt16(truncatingIfNeeded: lives) & 0b1111) << 12)
    }

    /// invulnerability ticks:0...8, carried_y:9 (`state.zone_loaded`, entity lane).
    static func zoneLoaded(invulnerabilityTicks: Int, carriedY: Bool) -> UInt16 {
        (UInt16(truncatingIfNeeded: invulnerabilityTicks) & 0b1_1111_1111) | (carriedY ? 1 << 9 : 0)
    }

    /// lives_before:0...3, lives_after:4...7, ammo_reset:8 (`bonus.stage_points`, entity lane).
    static func stagePoints(livesBefore: Int, livesAfter: Int, ammoReset: Bool) -> UInt16 {
        (UInt16(truncatingIfNeeded: livesBefore) & 0b1111)
            | ((UInt16(truncatingIfNeeded: livesAfter) & 0b1111) << 4)
            | (ammoReset ? 1 << 8 : 0)
    }
}

/// The seam. `Player`, `TMXLevelRuntime` and `GameScene` depend on this, never on the concrete log.
protocol GameplayEventSink: AnyObject {
    var isRecording: Bool { get }
    var emissionLevel: Int { get }
    var tick: UInt32 { get }
    var frame: UInt32 { get }
    var zone: UInt16 { get }

    /// One rendered `update(_:)` frame.
    func beginFrame()
    /// The only mutator of the tick counter; the first executed fixed step is tick 1.
    func beginTick(zone: Int)
    /// Hot path: one locked append, no I/O, no allocation.
    func emit(_ kind: GameplayEventKind, entity: UInt16, _ a: Int16, _ b: Int16, _ c: Int16, _ d: Int16)
    /// Keeps the sink's `flow_state` witness in step with the scene (`log.begin`, `tick.heartbeat`).
    func setFlowState(_ state: GameFlowState)
    /// Last `n` records for the in-game view. Never blocks on I/O.
    func view(_ n: Int?) -> [GameplayEvent]
    /// Barrier: everything appended so far is durably requested from the writer.
    func flush()
}

extension GameplayEventSink {
    func emit(_ kind: GameplayEventKind) {
        emit(kind, entity: 0, 0, 0, 0, 0)
    }

    func emit(_ kind: GameplayEventKind, entity: UInt16) {
        emit(kind, entity: entity, 0, 0, 0, 0)
    }

    func emit(_ kind: GameplayEventKind, entity: UInt16, _ a: Int16) {
        emit(kind, entity: entity, a, 0, 0, 0)
    }

    func emit(_ kind: GameplayEventKind, entity: UInt16, _ a: Int16, _ b: Int16) {
        emit(kind, entity: entity, a, b, 0, 0)
    }

    func emit(_ kind: GameplayEventKind, entity: UInt16, _ a: Int16, _ b: Int16, _ c: Int16) {
        emit(kind, entity: entity, a, b, c, 0)
    }

    func emit(_ kind: GameplayEventKind, _ a: Int16) {
        emit(kind, entity: 0, a, 0, 0, 0)
    }

    func emit(_ kind: GameplayEventKind, _ a: Int16, _ b: Int16) {
        emit(kind, entity: 0, a, b, 0, 0)
    }

    func emit(_ kind: GameplayEventKind, _ a: Int16, _ b: Int16, _ c: Int16) {
        emit(kind, entity: 0, a, b, c, 0)
    }

    func emit(_ kind: GameplayEventKind, _ a: Int16, _ b: Int16, _ c: Int16, _ d: Int16) {
        emit(kind, entity: 0, a, b, c, d)
    }

    func emitPosition(_ kind: GameplayEventKind, at point: CGPoint, entity: UInt16 = 0, extra a: Int16 = 0, extra2 b: Int16 = 0) {
        let (x, y) = GameplayEvent.q(point)
        emit(kind, entity: entity, x, y, a, b)
    }

    func setFlowState(_ state: GameFlowState) {}
    func view(_ n: Int?) -> [GameplayEvent] { [] }
    func flush() {}
    func beginFrame() {}
    func beginTick(zone: Int) {}
    var isRecording: Bool { true }
    var emissionLevel: Int { 2 }
    var tick: UInt32 { 0 }
    var frame: UInt32 { 0 }
    var zone: UInt16 { 0 }
}

/// Default sink: anything constructed without injection behaves exactly as before this change.
final class NullGameplayEventSink: GameplayEventSink {
    static let shared = NullGameplayEventSink()
    private init() {}

    var isRecording: Bool { false }
    var emissionLevel: Int { 0 }
    var tick: UInt32 { 0 }
    var frame: UInt32 { 0 }
    var zone: UInt16 { 0 }

    func beginFrame() {}
    func beginTick(zone: Int) {}
    func emit(_ kind: GameplayEventKind, entity: UInt16, _ a: Int16, _ b: Int16, _ c: Int16, _ d: Int16) {}
    func setFlowState(_ state: GameFlowState) {}
    func view(_ n: Int?) -> [GameplayEvent] { [] }
    func flush() {}
}

/// The producer-side emission vocabulary: **one function per wire name**, taking semantic
/// arguments and owning the lane order, packing and truncation.
///
/// This is where the class defect the code review found lives fixed: four records
/// (`damage.player_hit`, `damage.player_blocked`, `state.checkpoint_saved`, `state.restart`) shipped
/// wrong lane order or a wrong bit offset, and no gate could see it because the call sites sit in
/// SpriteKit-bound files the Linux gate never compiles. So `GameScene`, `Player`, `TMXLevelRuntime`
/// and `FixedTickDriver` call *these* helpers and contain no raw lane arithmetic; `evidence/harness/`
/// compiles them and `lane_round_trip_is_exact` proves, for every wire name, that the values packed
/// here are the values the formatter unpacks. A checker rule forbids `events.emit(` in those files.
///
/// Every body is integer-only: no String, no collection, no closure, no I/O.
extension GameplayEventSink {
    // MARK: input

    func emitActionEdge(_ action: GameAction, source: InputSource, pressed: Bool, heldMilliseconds: Int) {
        emit(.inputActionEdge,
             entity: GameplayPack.edge(action: GameplayWire.code(action), source: GameplayWire.code(source)),
             Int16(truncatingIfNeeded: min(32_767, max(0, heldMilliseconds))),
             pressed ? 1 : 0)
    }

    /// `pending` is true by construction: the record exists only when the edge-triggered pause
    /// command was actually consumed (a per-step `false` poll would be a heartbeat in disguise).
    func emitPausePressConsumed() {
        emit(.inputPauseConsumed, 1)
    }

    func emitContextualConsume(_ kind: GameplayContextualAction, jumpSuppressed: Bool) {
        emit(.inputContextualConsumed, entity: kind.wireCode, jumpSuppressed ? 1 : 0)
    }

    // MARK: player

    func emitMotion(state: PlayerMotionState, grounded: Bool, facing: PlayerFacing, exoskeleton: Bool,
                    position: CGPoint, velocityX: CGFloat, velocityY: CGFloat) {
        let (x, y) = GameplayEvent.q(position)
        emit(.playerMotion,
             entity: GameplayPack.motion(state: GameplayWire.code(state), grounded: grounded,
                                         facing: GameplayWire.code(facing), exoskeleton: exoskeleton),
             x, y, GameplayEvent.q(velocityX), GameplayEvent.q(velocityY))
    }

    func emitJump(position: CGPoint, velocity: CGFloat, groundedBefore: Bool, afterTeleport: Bool) {
        let (x, y) = GameplayEvent.q(position)
        emit(.playerJump,
             entity: GameplayPack.jumpWitness(groundedBefore: groundedBefore, afterTeleport: afterTeleport),
             x, y, GameplayEvent.q(velocity))
    }

    func emitLand(position: CGPoint, fallSpeed: CGFloat, support: GameplaySupport) {
        let (x, y) = GameplayEvent.q(position)
        emit(.playerLand, entity: support.wireCode, x, y, GameplayEvent.q(fallSpeed))
    }

    func emitCrouchEdge(begins: Bool, position: CGPoint) {
        emitPosition(begins ? .playerCrouchBegin : .playerCrouchEnd, at: position)
    }

    func emitExoskeleton(enabled: Bool, cause: GameplayExoskeletonCause) {
        emit(.playerExoskeleton, entity: cause.wireCode, enabled ? 1 : 0)
    }

    func emitBlasterShot(origin: CGPoint, facing: PlayerFacing, double: Bool, ammoBefore: Int, ammoAfter: Int) {
        let (x, y) = GameplayEvent.q(origin)
        emit(.playerShootBlaster,
             entity: GameplayPack.blaster(facing: GameplayWire.code(facing), double: double),
             x, y, Int16(truncatingIfNeeded: ammoBefore), Int16(truncatingIfNeeded: ammoAfter))
    }

    func emitShootDenied(_ reason: GameplayShootDeniedReason, ammo: Int) {
        emit(.playerShootDenied, entity: reason.wireCode, Int16(truncatingIfNeeded: ammo))
    }

    func emitGrenadeThrow(origin: CGPoint, direction: PlayerFacing, grenadesBefore: Int, grenadesAfter: Int,
                          blockedByOneInFlight: Bool) {
        let (x, y) = GameplayEvent.q(origin)
        emit(.playerThrowGrenade,
             entity: GameplayPack.grenadeThrow(direction: GameplayWire.code(direction),
                                               blockedByOneInFlight: blockedByOneInFlight),
             x, y, Int16(truncatingIfNeeded: grenadesBefore), Int16(truncatingIfNeeded: grenadesAfter))
    }

    func emitTeleport(from: CGPoint, to: CGPoint, portalIndex: Int, jumpLatchHeld: Bool) {
        let (fromX, fromY) = GameplayEvent.q(from)
        let (toX, toY) = GameplayEvent.q(to)
        emit(.playerTeleport, entity: GameplayPack.teleport(portalIndex: portalIndex, jumpLatchHeld: jumpLatchHeld),
             fromX, fromY, toX, toY)
    }

    func emitDeathBegin(position: CGPoint, lives: Int, ammo: Int, grenades: Int) {
        let (x, y) = GameplayEvent.q(position)
        emit(.playerDeathBegin, entity: UInt16(truncatingIfNeeded: grenades), x, y,
             Int16(truncatingIfNeeded: lives), Int16(truncatingIfNeeded: ammo))
    }

    func emitDeathLanded(position: CGPoint, groundTicks: Int) {
        let (x, y) = GameplayEvent.q(position)
        emit(.playerDeathLanded, x, y, Int16(truncatingIfNeeded: groundTicks))
    }

    func emitDeathSettled(livesBefore: Int, livesAfter: Int, invulnerabilityTicks: Int, settleTicks: Int,
                          checkpointSaved: Bool) {
        emit(.playerDeathSettled, entity: GameplayPack.settled(checkpointSaved: checkpointSaved),
             Int16(truncatingIfNeeded: livesBefore), Int16(truncatingIfNeeded: livesAfter),
             Int16(truncatingIfNeeded: invulnerabilityTicks), Int16(truncatingIfNeeded: settleTicks))
    }

    // MARK: game / damage

    func emitGameOver(points: Int, highScore: Int, checkpointCleared: Bool) {
        let pointsSplit = GameplayEvent.split(points)
        let highSplit = GameplayEvent.split(highScore)
        emit(.gameGameOver, entity: GameplayPack.gameOver(checkpointCleared: checkpointCleared),
             pointsSplit.0, pointsSplit.1, highSplit.0, highSplit.1)
    }

    /// `cause` and `test_invulnerability` ride lane `c`, `invulnerability_us` the `a,b` i32 pair -
    /// the same map `x-encode` and `schemas[22]` declare.
    func emitBlockedHit(cause: GameplayDamageCause, invulnerabilityMicroseconds: Int, testInvulnerability: Bool) {
        let split = GameplayEvent.split(max(0, invulnerabilityMicroseconds))
        emit(.damagePlayerBlocked, split.0, split.1,
             GameplayEvent.lane(GameplayPack.blocked(cause: cause.wireCode, testInvulnerability: testInvulnerability)))
    }

    func emitPlayerHit(cause: GameplayDamageCause, position: CGPoint, flowBefore: GameFlowState,
                       flowAfter: GameFlowState, lives: Int) {
        let (x, y) = GameplayEvent.q(position)
        emit(.damagePlayerHit, x, y,
             GameplayEvent.lane(GameplayPack.hit(cause: cause.wireCode,
                                                 before: GameplayWire.code(flowBefore),
                                                 after: GameplayWire.code(flowAfter))),
             Int16(truncatingIfNeeded: lives))
    }

    // MARK: pickup / bonus / score

    func emitPickupCollected(_ kind: GameplayPickupKind, countBefore: Int, countAfter: Int, at origin: CGPoint) {
        let (x, y) = GameplayEvent.q(origin)
        emit(.pickupCollect, entity: kind.wireCode, x, y,
             Int16(truncatingIfNeeded: countBefore), Int16(truncatingIfNeeded: countAfter))
    }

    func emitDoubleLauncherBonus(points: Int, launcherObjectID: UInt16, at origin: CGPoint,
                                 launcherActiveAfter: Bool) {
        let (x, y) = GameplayEvent.q(origin)
        emit(.bonusDoubleLauncher, entity: launcherObjectID, Int16(truncatingIfNeeded: points), x, y,
             launcherActiveAfter ? 1 : 0)
    }

    func emitStageBoundaryPoints(points: Int, livesBefore: Int, livesAfter: Int, ammoReset: Bool) {
        let total = GameplayEvent.split(points)
        emit(.bonusStagePoints,
             entity: GameplayPack.stagePoints(livesBefore: livesBefore, livesAfter: livesAfter, ammoReset: ammoReset),
             total.0, total.1)
    }

    func emitStageAwardComponent(_ component: GameplayStageComponent, points: Int) {
        emit(.bonusStageComponent, entity: component.wireCode, Int16(truncatingIfNeeded: points))
    }

    func emitStageBoundarySuppressed(_ reason: GameplayStageSuppressionReason) {
        emit(.bonusStageBoundarySuppressed, entity: reason.wireCode)
    }

    /// `points_after` and `clamped` are derived by the formatter from `points_before + points` with
    /// the same clamp the product applies, so only three values cross the ring.
    func emitScoreAwarded(points: Int, pointsBefore: Int, reason: GameplayScoreReason) {
        let before = GameplayEvent.split(pointsBefore)
        emit(.scoreAwarded, entity: reason.wireCode, Int16(truncatingIfNeeded: points), before.0, before.1)
    }

    func emitHighScoreSaved(_ value: Int) {
        let split = GameplayEvent.split(value)
        emit(.scoreHighScoreSaved, split.0, split.1)
    }

    // MARK: state

    func emitFlowChange(from: GameFlowState, to: GameFlowState, cause: GameplayFlowCause) {
        setFlowState(to)
        emit(.stateFlow, GameplayEvent.lane(GameplayWire.code(from)),
             GameplayEvent.lane(GameplayWire.code(to)),
             GameplayEvent.lane(cause.wireCode))
    }

    func emitZoneLoad(_ cause: GameplayZoneLoadCause) {
        emit(.stateZoneLoad, entity: cause.wireCode)
    }

    func emitZoneLoaded(solidCount: Int, spawnCenter: CGPoint, groundY: CGFloat, invulnerabilityTicks: Int,
                        carriedY: Bool) {
        let (spawnX, spawnY) = GameplayEvent.q(spawnCenter)
        emit(.stateZoneLoaded,
             entity: GameplayPack.zoneLoaded(invulnerabilityTicks: invulnerabilityTicks, carriedY: carriedY),
             Int16(truncatingIfNeeded: solidCount), spawnX, spawnY, GameplayEvent.q(groundY))
    }

    func emitZoneExit(triggerX: CGFloat, playerX: CGFloat, hasPlayableNextLevel: Bool) {
        emit(.stateZoneExit, entity: hasPlayableNextLevel ? 1 : 0,
             GameplayEvent.q(triggerX), GameplayEvent.q(playerX))
    }

    func emitZoneTransition(toZone: Int, accumulatorMicroseconds: Int, pendingSteps: Int) {
        let split = GameplayEvent.split(accumulatorMicroseconds)
        emit(.stateZoneTransition, entity: UInt16(truncatingIfNeeded: toZone),
             split.0, split.1, Int16(truncatingIfNeeded: pendingSteps))
    }

    func emitContentComplete(points: Int, final: Bool, hasNextLevel: Bool) {
        let split = GameplayEvent.split(points)
        emit(.stateContentComplete,
             entity: GameplayPack.contentComplete(final: final, hasNextLevel: hasNextLevel),
             split.0, split.1)
    }

    func emitTitleEnter(highScore: Int, hasSavedCheckpoint: Bool) {
        let split = GameplayEvent.split(highScore)
        emit(.stateTitleEnter, entity: GameplayPack.titleEnter(hasSavedCheckpoint: hasSavedCheckpoint),
             split.0, split.1)
    }

    /// Lane map: points in the `b,c` i32 pair; `ammo` 0-6, `grenades` 7-11 and `lives` 12-15 packed
    /// into the subject lane - 16 bits exactly, and the formatter reads the same three offsets.
    func emitCheckpointSaved(ammo: Int, grenades: Int, lives: Int, points: Int) {
        let split = GameplayEvent.split(points)
        emit(.stateCheckpointSaved,
             entity: GameplayPack.checkpoint(ammo: ammo, grenades: grenades, lives: lives),
             0, split.0, split.1)
    }

    func emitCheckpointCleared(_ reason: GameplayCheckpointClearedReason) {
        emit(.stateCheckpointCleared, entity: reason.wireCode)
    }

    func emitPauseChanged(entering: Bool, stateBefore: GameFlowState, selectedIndex: Int) {
        let code = GameplayEvent.lane(GameplayWire.code(stateBefore))
        emit(entering ? .statePauseEnter : .statePauseExit, code, Int16(truncatingIfNeeded: selectedIndex))
    }

    func emitRunRestarted(discardedPoints: Int) {
        let split = GameplayEvent.split(discardedPoints)
        // `from_zone` is the record's zone lane, which the caller has not reassigned yet.
        emit(.stateRestart, split.0, split.1)
    }

    func emitCheatInvulnerability(enabled: Bool, menuIndex: Int) {
        emit(.stateCheatInvulnerability, enabled ? 1 : 0, Int16(truncatingIfNeeded: menuIndex))
    }

    // MARK: tick anomalies

    func emitFrameGapClamped(rawMicroseconds: Int) {
        let split = GameplayEvent.split(rawMicroseconds)
        emit(.tickFrameGapClamped, split.0, split.1)
    }

    func emitAccumulatorReset(reason: GameplayAccumulatorResetReason, discardedMicroseconds: Int,
                              discardedSteps: Int) {
        let split = GameplayEvent.split(discardedMicroseconds)
        emit(.tickAccumulatorReset, entity: reason.wireCode, split.0, split.1,
             Int16(truncatingIfNeeded: discardedSteps))
    }

    func emitSlowStep(stepMicroseconds: Int, stepsThisFrame: Int) {
        let split = GameplayEvent.split(stepMicroseconds)
        emit(.tickSlowStep, split.0, split.1, Int16(truncatingIfNeeded: stepsThisFrame))
    }

    // MARK: entity

    func emitLauncherFired(objectID: UInt16, at origin: CGPoint, muzzleY: CGFloat) {
        let (x, y) = GameplayEvent.q(origin)
        emit(.entityLauncherFire, entity: objectID, x, y, GameplayEvent.q(muzzleY))
    }
}

/// Wire labels for the existing product vocabularies. Codes are append-only; labels are read
/// from the product enum itself (`GameFlowState.rawValue`, `String(describing:)` of a case),
/// so there is no second vocabulary to drift (integration section 3).
enum GameplayWire {
    // MARK: Flow state
    static func code(_ state: GameFlowState) -> UInt16 {
        switch state {
        case .title: return 0
        case .playing: return 1
        case .paused: return 2
        case .playerDead: return 3
        case .respawning: return 4
        case .gameOver: return 5
        case .contentComplete: return 6
        }
    }

    static func flowState(_ bits: UInt16) -> GameFlowState? {
        switch bits {
        case 0: return .title
        case 1: return .playing
        case 2: return .paused
        case 3: return .playerDead
        case 4: return .respawning
        case 5: return .gameOver
        case 6: return .contentComplete
        default: return nil
        }
    }

    static func flowLabel(_ bits: UInt16) -> String {
        flowState(bits)?.rawValue ?? "unknown\(bits)"
    }

    // MARK: GameAction
    static func code(_ action: GameAction) -> UInt16 {
        switch action {
        case .moveLeft: return 0
        case .moveRight: return 1
        case .jump: return 2
        case .crouch: return 3
        case .fire: return 4
        case .grenade: return 5
        case .pause: return 6
        case .menuUp: return 7
        case .menuDown: return 8
        case .debugHitboxes: return 9
        }
    }

    /// Literals, not `String(describing:)`: reflection costs hundreds of nanoseconds per call and
    /// this runs on the drain path for every input edge. `labelVocabularyMatchesSwiftCases()`
    /// re-checks each literal against the real case name on the cold path, so the cheaper code
    /// cannot silently drift (integration section 3: one vocabulary, not two).
    static func actionLabel(_ bits: UInt16) -> String {
        switch bits {
        case 0: return "moveLeft"
        case 1: return "moveRight"
        case 2: return "jump"
        case 3: return "crouch"
        case 4: return "fire"
        case 5: return "grenade"
        case 6: return "pause"
        case 7: return "menuUp"
        case 8: return "menuDown"
        case 9: return "debugHitboxes"
        default: return "unknown" + String(bits)
        }
    }

    // MARK: InputSource
    static func code(_ source: InputSource) -> UInt16 {
        switch source {
        case .keyboard: return 0
        case .gamepadDPad: return 1
        case .gamepadStick: return 2
        case .gamepadButtons: return 3
        }
    }

    static func sourceLabel(_ bits: UInt16) -> String {
        switch bits {
        case 0: return "keyboard"
        case 1: return "gamepadDPad"
        case 2: return "gamepadStick"
        case 3: return "gamepadButtons"
        default: return "unknown" + String(bits)
        }
    }

    // MARK: Player motion
    static func code(_ state: PlayerMotionState) -> UInt16 {
        switch state {
        case .idle: return 0
        case .running: return 1
        case .jumping: return 2
        case .falling: return 3
        case .crouching: return 4
        case .dying: return 5
        }
    }

    static func motionLabel(_ bits: UInt16) -> String {
        switch bits & 0b111 {
        case 0: return "idle"
        case 1: return "running"
        case 2: return "jumping"
        case 3: return "falling"
        case 4: return "crouching"
        case 5: return "dying"
        default: return "unknown" + String(bits)
        }
    }

    static func code(_ facing: PlayerFacing) -> UInt16 { facing == .right ? 1 : 0 }

    static func facingLabel(_ bit: UInt16) -> String {
        switch bit {
        case 0: return "left"
        case 1: return "right"
        default: return "unknown" + String(bit)
        }
    }

    /// Cold-path drift guard: every literal label above must still be the Swift case name it
    /// stands for, and every flow label must still be `GameFlowState.rawValue`. The harness asserts
    /// this returns nothing.
    static func labelVocabularyMatchesSwiftCases() -> [String] {
        var problems: [String] = []
        let actions: [(UInt16, GameAction)] = [
            (0, .moveLeft), (1, .moveRight), (2, .jump), (3, .crouch), (4, .fire), (5, .grenade),
            (6, .pause), (7, .menuUp), (8, .menuDown), (9, .debugHitboxes)
        ]
        for (code, action) in actions where actionLabel(code) != String(describing: action) {
            problems.append("action \(code) -> \(actionLabel(code)) != \(String(describing: action))")
        }
        let sources: [(UInt16, InputSource)] = [(0, .keyboard), (1, .gamepadDPad), (2, .gamepadStick), (3, .gamepadButtons)]
        for (code, source) in sources where sourceLabel(code) != String(describing: source) {
            problems.append("source \(code) -> \(sourceLabel(code)) != \(String(describing: source))")
        }
        let motions: [(UInt16, PlayerMotionState)] = [(0, .idle), (1, .running), (2, .jumping), (3, .falling), (4, .crouching), (5, .dying)]
        for (code, state) in motions where motionLabel(code) != String(describing: state) {
            problems.append("motion \(code) -> \(motionLabel(code)) != \(String(describing: state))")
        }
        for (code, facing) in [(UInt16(0), PlayerFacing.left), (1, PlayerFacing.right)] where facingLabel(code) != String(describing: facing) {
            problems.append("facing \(code) -> \(facingLabel(code)) != \(String(describing: facing))")
        }
        for code in UInt16(0) ... UInt16(6) {
            guard let state = flowState(code) else { problems.append("flow \(code) is not decodable"); continue }
            if flowLabel(code) != state.rawValue {
                problems.append("flow \(code) -> \(flowLabel(code)) != \(state.rawValue)")
            }
        }
        for domain in GameplayLabelDomain.all {
            for code in domain.codes where domain.label(code).hasPrefix("unknown") {
                problems.append("\(domain.name) \(code) has no label")
            }
        }
        return problems
    }

    /// Level-relative resource name, derived from the 0-based zone exactly like
    /// `GameScene.zoneNumber(for:)` so no string ever crosses the producer path.
    static func resource(for zone: UInt16) -> String {
        let clamped = min(124, Int(zone))
        return String(format: "L%02dS%02d", clamped / 25 + 1, clamped % 25 + 1)
    }

    // MARK: Payload label domains (the closed value sets frozen in the schema)

    static func damageCauseLabel(_ bits: UInt16) -> String { GameplayDamageCause(rawValue: bits)?.label ?? "unknown\(bits)" }
    static func contextualLabel(_ bits: UInt16) -> String { GameplayContextualAction(rawValue: bits)?.label ?? "unknown\(bits)" }
    static func supportLabel(_ bits: UInt16) -> String { GameplaySupport(rawValue: bits)?.label ?? "unknown\(bits)" }
    static func exoskeletonCauseLabel(_ bits: UInt16) -> String { GameplayExoskeletonCause(rawValue: bits)?.label ?? "unknown\(bits)" }
    static func shootDeniedReasonLabel(_ bits: UInt16) -> String { GameplayShootDeniedReason(rawValue: bits)?.label ?? "unknown\(bits)" }
    static func pickupKindLabel(_ bits: UInt16) -> String { GameplayPickupKind(rawValue: bits)?.label ?? "unknown\(bits)" }
    static func scoreReasonLabel(_ bits: UInt16) -> String { GameplayScoreReason(rawValue: bits)?.label ?? "unknown\(bits)" }
    static func flowCauseLabel(_ bits: UInt16) -> String { GameplayFlowCause(rawValue: bits)?.label ?? "unknown\(bits)" }
    static func zoneLoadCauseLabel(_ bits: UInt16) -> String { GameplayZoneLoadCause(rawValue: bits)?.label ?? "unknown\(bits)" }
    static func checkpointClearedReasonLabel(_ bits: UInt16) -> String { GameplayCheckpointClearedReason(rawValue: bits)?.label ?? "unknown\(bits)" }
    static func accumulatorResetReasonLabel(_ bits: UInt16) -> String { GameplayAccumulatorResetReason(rawValue: bits)?.label ?? "unknown\(bits)" }
    static func stageComponentLabel(_ bits: UInt16) -> String { GameplayStageComponent(rawValue: bits)?.label ?? "unknown\(bits)" }
    static func stageSuppressionReasonLabel(_ bits: UInt16) -> String { GameplayStageSuppressionReason(rawValue: bits)?.label ?? "unknown\(bits)" }
    static func launcherKindLabel(_ bits: UInt16) -> String { GameplayLauncherKind(rawValue: bits)?.label ?? "unknown\(bits)" }
    static func logEndReasonLabel(_ bits: UInt16) -> String { GameplayLogEndReason(rawValue: bits)?.label ?? "unknown\(bits)" }

    /// The whole wire contract rendered as text, dumped by the Linux harness to `contract.txt`
    /// and diffed by `gameplay_log_check.py` against the frozen JSON schema. Because it walks the
    /// product types themselves, a renamed label or a renumbered kind cannot hide.
    static func contractDump() -> [String] {
        var lines: [String] = []
        for raw in UInt8(1) ... UInt8(48) {
            guard let kind = GameplayEventKind(rawValue: raw) else { continue }
            lines.append("kind\t\(raw)\t\(kind.label)\t\(kind.minimumLevel)\t\(kind.payloadSchema)")
        }
        lines.append("family\twave-a-active\tmeta,log,input,player,damage,bonus,state,tick,pickup,entity,game,score")
        lines.append("family\treserved-unused\tbullet,hud")
        for value in GameplayDamageCause.allCases { lines.append("domain\tdamage_cause\t\(value.rawValue)\t\(value.label)") }
        for value in GameplayContextualAction.allCases { lines.append("domain\tcontextual_kind\t\(value.rawValue)\t\(value.label)") }
        for value in GameplaySupport.allCases { lines.append("domain\tsupport\t\(value.rawValue)\t\(value.label)") }
        for value in GameplayExoskeletonCause.allCases { lines.append("domain\texoskeleton_cause\t\(value.rawValue)\t\(value.label)") }
        for value in GameplayShootDeniedReason.allCases { lines.append("domain\tshoot_denied_reason\t\(value.rawValue)\t\(value.label)") }
        for value in GameplayPickupKind.allCases { lines.append("domain\tpickup_kind\t\(value.rawValue)\t\(value.label)") }
        for value in GameplayScoreReason.allCases { lines.append("domain\tscore_reason\t\(value.rawValue)\t\(value.label)") }
        for value in GameplayFlowCause.allCases { lines.append("domain\tflow_cause\t\(value.rawValue)\t\(value.label)") }
        for value in GameplayZoneLoadCause.allCases { lines.append("domain\tzone_load_cause\t\(value.rawValue)\t\(value.label)") }
        for value in GameplayCheckpointClearedReason.allCases { lines.append("domain\tcheckpoint_cleared_reason\t\(value.rawValue)\t\(value.label)") }
        for value in GameplayAccumulatorResetReason.allCases { lines.append("domain\taccumulator_reset_reason\t\(value.rawValue)\t\(value.label)") }
        for value in GameplayStageComponent.allCases { lines.append("domain\tstage_component_id\t\(value.rawValue)\t\(value.label)") }
        for value in GameplayStageSuppressionReason.allCases { lines.append("domain\tstage_boundary_suppression_reason\t\(value.rawValue)\t\(value.label)") }
        for value in GameplayLauncherKind.allCases { lines.append("domain\tlauncher_kind\t\(value.rawValue)\t\(value.label)") }
        for value in GameplayLogEndReason.allCases { lines.append("domain\tlog_end_reason\t\(value.rawValue)\t\(value.label)") }
        for code in UInt16(0) ... UInt16(6) { lines.append("domain\tflow_state\t\(code)\t\(flowLabel(code))") }
        for code in UInt16(0) ... UInt16(9) { lines.append("domain\taction\t\(code)\t\(actionLabel(code))") }
        for code in UInt16(0) ... UInt16(3) { lines.append("domain\tsource\t\(code)\t\(sourceLabel(code))") }
        for code in UInt16(0) ... UInt16(5) { lines.append("domain\tmotion_state\t\(code)\t\(motionLabel(code))") }
        lines.append("domain\tfacing\t0\t\(facingLabel(0))")
        lines.append("domain\tfacing\t1\t\(facingLabel(1))")
        lines.append("scale\tquarter-pixel\t4\tvalue/4 px")
        lines.append("scale\tmicrosecond-from-steps\t60\tround(n*1000000/60)")
        lines.append("constant\tclamp_us\t250000")
        lines.append("constant\tbudget_us\t16667")
        lines.append("constant\tfixed_time_step\t1/60")
        lines.append("stride\tGameplayEvent\t\(MemoryLayout<GameplayEvent>.stride)")
        return lines
    }
}

/// Every closed label domain of the frozen contract, with how many codes it declares. Used by the
/// cold-path drift guard below: an enum case that lost its label, or a code that drifted past the
/// declared set, fails the harness instead of shipping as `unknown7` in the field.
struct GameplayLabelDomain {
    let name: String
    let codeCount: Int
    let label: (UInt16) -> String

    var codes: [UInt16] { Array(0 ..< UInt16(codeCount)) }

    static let all: [GameplayLabelDomain] = [
        GameplayLabelDomain(name: "damage_cause", codeCount: 8, label: GameplayWire.damageCauseLabel),
        GameplayLabelDomain(name: "contextual_kind", codeCount: 2, label: GameplayWire.contextualLabel),
        GameplayLabelDomain(name: "support", codeCount: 2, label: GameplayWire.supportLabel),
        GameplayLabelDomain(name: "exoskeleton_cause", codeCount: 4, label: GameplayWire.exoskeletonCauseLabel),
        GameplayLabelDomain(name: "shoot_denied_reason", codeCount: 1, label: GameplayWire.shootDeniedReasonLabel),
        GameplayLabelDomain(name: "pickup_kind", codeCount: 2, label: GameplayWire.pickupKindLabel),
        GameplayLabelDomain(name: "score_reason", codeCount: 8, label: GameplayWire.scoreReasonLabel),
        GameplayLabelDomain(name: "flow_cause", codeCount: 10, label: GameplayWire.flowCauseLabel),
        GameplayLabelDomain(name: "zone_load_cause", codeCount: 4, label: GameplayWire.zoneLoadCauseLabel),
        GameplayLabelDomain(name: "checkpoint_cleared_reason", codeCount: 3, label: GameplayWire.checkpointClearedReasonLabel),
        GameplayLabelDomain(name: "accumulator_reset_reason", codeCount: 4, label: GameplayWire.accumulatorResetReasonLabel),
        GameplayLabelDomain(name: "stage_component_id", codeCount: 3, label: GameplayWire.stageComponentLabel),
        GameplayLabelDomain(name: "stage_boundary_suppression_reason", codeCount: 2, label: GameplayWire.stageSuppressionReasonLabel),
        GameplayLabelDomain(name: "launcher_kind", codeCount: 1, label: GameplayWire.launcherKindLabel),
        GameplayLabelDomain(name: "log_end_reason", codeCount: 3, label: GameplayWire.logEndReasonLabel)
    ]
}

/// Closed payload value sets. Raw values are wire codes (append-only), `label` is the frozen
/// schema spelling, so neither the Swift vocabulary nor the JSON vocabulary is duplicated.
protocol GameplayWireEnum: CaseIterable {
    var wireCode: UInt16 { get }
    var label: String { get }
}

enum GameplayDamageCause: UInt16, CaseIterable {
    case bullet, mine, piston, forceField, sourceHazard, bubble, egg, missile
    var wireCode: UInt16 { rawValue }
    var label: String {
        switch self {
        case .bullet: return "bullet"
        case .mine: return "mine"
        case .piston: return "piston"
        case .forceField: return "force_field"
        case .sourceHazard: return "source_hazard"
        case .bubble: return "bubble"
        case .egg: return "egg"
        case .missile: return "missile"
        }
    }
}

enum GameplayContextualAction: UInt16, CaseIterable {
    case changingRoom, teleport
    var wireCode: UInt16 { rawValue }
    var label: String {
        switch self {
        case .changingRoom: return "changing_room"
        case .teleport: return "teleport"
        }
    }
}

enum GameplaySupport: UInt16, CaseIterable {
    case fallbackFloor, solid
    var wireCode: UInt16 { rawValue }
    var label: String {
        switch self {
        case .fallbackFloor: return "fallback_floor"
        case .solid: return "solid"
        }
    }
}

enum GameplayExoskeletonCause: UInt16, CaseIterable {
    case changingRoom, cheat, reset, stageBoundary
    var wireCode: UInt16 { rawValue }
    var label: String {
        switch self {
        case .changingRoom: return "changing_room"
        case .cheat: return "cheat"
        case .reset: return "reset"
        case .stageBoundary: return "stage_boundary"
        }
    }
}

enum GameplayShootDeniedReason: UInt16, CaseIterable {
    case noAmmo
    var wireCode: UInt16 { rawValue }
    var label: String {
        switch self {
        case .noAmmo: return "no_ammo"
        }
    }
}

enum GameplayPickupKind: UInt16, CaseIterable {
    case grenadePack, ammoPack
    var wireCode: UInt16 { rawValue }
    var label: String {
        switch self {
        case .grenadePack: return "grenade_pack"
        case .ammoPack: return "ammo_pack"
        }
    }
}

enum GameplayScoreReason: UInt16, CaseIterable {
    case blasterShotdown, bubble, egg, forceField, grenadeKill, guidance, launcher, stageBoundary
    var wireCode: UInt16 { rawValue }
    var label: String {
        switch self {
        case .blasterShotdown: return "blaster_shotdown"
        case .bubble: return "bubble"
        case .egg: return "egg"
        case .forceField: return "force_field"
        case .grenadeKill: return "grenade_kill"
        case .guidance: return "guidance"
        case .launcher: return "launcher"
        case .stageBoundary: return "stage_boundary"
        }
    }
}

enum GameplayFlowCause: UInt16, CaseIterable {
    case firePress, pausePress, resume, restart, death, respawnTimeout, zoneTransition, contentComplete, titleReturn, unspecified
    var wireCode: UInt16 { rawValue }
    var label: String {
        switch self {
        case .firePress: return "fire_press"
        case .pausePress: return "pause_press"
        case .resume: return "resume"
        case .restart: return "restart"
        case .death: return "death"
        case .respawnTimeout: return "respawn_timeout"
        case .zoneTransition: return "zone_transition"
        case .contentComplete: return "content_complete"
        case .titleReturn: return "title_return"
        case .unspecified: return "unspecified"
        }
    }
}

enum GameplayZoneLoadCause: UInt16, CaseIterable {
    case appLaunch, transition, checkpoint, restart
    var wireCode: UInt16 { rawValue }
    var label: String {
        switch self {
        case .appLaunch: return "app_launch"
        case .transition: return "transition"
        case .checkpoint: return "checkpoint"
        case .restart: return "restart"
        }
    }
}

enum GameplayCheckpointClearedReason: UInt16, CaseIterable {
    case newGame, gameOver, launch
    var wireCode: UInt16 { rawValue }
    var label: String {
        switch self {
        case .newGame: return "new_game"
        case .gameOver: return "game_over"
        case .launch: return "launch"
        }
    }
}

enum GameplayAccumulatorResetReason: UInt16, CaseIterable {
    case zoneTransition, newGame, pausedExit, explicit
    var wireCode: UInt16 { rawValue }
    var label: String {
        switch self {
        case .zoneTransition: return "zone_transition"
        case .newGame: return "new_game"
        case .pausedExit: return "paused_exit"
        case .explicit: return "explicit"
        }
    }
}

/// Wave A implements exactly one stage-boundary component. The ledger is a list of these so a
/// later wave can append bravery/timed components without touching the scene seam or the witness
/// plumbing (controller amendment, 2026-09-24). Append-only codes.
enum GameplayStageComponent: UInt16, CaseIterable {
    case livesTimes1000
    /// Wave D (`ORIGINAL_MECHANICS.md:142`): the stage was completed without taking the suit.
    case braveryNoExoskeleton
    /// Wave D (`:143` as an owner-approved deterministic tick ladder): the phase the stage ended in.
    case timedPhaseLadder
    var wireCode: UInt16 { rawValue }
    var label: String {
        switch self {
        case .livesTimes1000: return "lives_x1000"
        case .braveryNoExoskeleton: return "bravery_no_exoskeleton"
        case .timedPhaseLadder: return "timed_phase_ladder"
        }
    }
}

enum GameplayStageSuppressionReason: UInt16, CaseIterable {
    case alreadyAwarded, notStageEnd
    var wireCode: UInt16 { rawValue }
    var label: String {
        switch self {
        case .alreadyAwarded: return "already_awarded"
        case .notStageEnd: return "not_stage_end"
        }
    }
}

enum GameplayLauncherKind: UInt16, CaseIterable {
    case doubleLauncher
    var wireCode: UInt16 { rawValue }
    var label: String {
        switch self {
        case .doubleLauncher: return "double_launcher"
        }
    }
}

enum GameplayLogEndReason: UInt16, CaseIterable {
    case appQuit, error, harnessComplete
    var wireCode: UInt16 { rawValue }
    var label: String {
        switch self {
        case .appQuit: return "app_quit"
        case .error: return "error"
        case .harnessComplete: return "harness_complete"
        }
    }
}
