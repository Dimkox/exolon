import Foundation

/// Linux execution gate for wave A (change
/// 20260924-implement-a-structured-gameplay-event-log-for-ev-32f59c).
///
/// It compiles and runs **real product sources** (`GameConstants`, `InputState`, `GameState`,
/// `Player` and everything under `GameCore/Diagnostics/`) behind a four-line `CGVector` shim and
/// writes JSON-lines streams that `../gameplay_log_check.py` evaluates. SpriteKit is never shimmed
/// (integration_architect section 1: a fake SpriteKit would let a test pass on a fiction), so what
/// runs here is the Foundation-only half of the design, and every decision under test - stepping,
/// the accumulator reset, the jump latch, the stage-boundary award, the launcher payout - is taken
/// by product types, not by a copy of `GameScene`'s logic.
///
/// The scene's *emission* calls (`player.motion`, `state.zone_transition`, ...) are reproduced here
/// because the only SpriteKit-free place they can be driven from is this file; their payloads come
/// from the same product getters `GameScene` reads.
///
/// Environment:
///   EXOLON_HARNESS_OUT   artifact directory, absolute and outside the clone (required)
///   EXOLON_REVERT        `p1_9` | `p1_8` - build the fix-reverted control variant (AC-002/AC-003)
///   EXOLON_SCENARIO      optional: run only this scenario name

// MARK: - Harness plumbing

/// Discards whatever it is given but keeps byte accounting, so the cost probe measures the real
/// format-and-write path without growing memory or touching a device.
final class DiscardWriter: GameplayEventWriter {
    private(set) var bytes = 0
    private(set) var rotation = 0
    var opened = false

    var bytesInCurrentFile: Int { bytes }
    var rotationIndex: Int { rotation }
    var currentPath: String { "discard://\(rotation)" }
    func nextFilePath() -> String { "discard://\(rotation + 1)" }
    func openFirstFile() -> Bool { opened = true; return true }
    func write(_ text: String) { bytes += text.utf8.count }
    func synchronize() {}
    func rotateToNextFile() -> Bool { rotation += 1; bytes = 0; return true }
    func closeFile() {}
}

enum Harness {
    static let out = ProcessInfo.processInfo.environment["EXOLON_HARNESS_OUT"] ?? ""
    static let revert = ProcessInfo.processInfo.environment["EXOLON_REVERT"] ?? "none"
    static let only = ProcessInfo.processInfo.environment["EXOLON_SCENARIO"]

    static var failures: [String] = []
    static var warnings: [String] = []
    static var manifest: [String: [String]] = [:]
    static var notes: [String] = []
    static var ran: [String] = []

    static func check(_ condition: Bool, _ label: String, line: UInt = #line) {
        if !condition {
            failures.append("line \(line): \(label)")
            print("FAIL \(label)")
        }
    }

    /// Load-sensitive bands report through this instead of `check`: a WARNING carrying the
    /// measured value, never a failure. The deterministic twins of every soft band stay in
    /// `check` (wave E1, issue #22 item 5 - M3 tripped twice under host load 16-18, passed 3/3
    /// clean; a shared host must not be able to make the gate lie in either direction).
    static func warn(_ condition: Bool, _ label: String, line: UInt = #line) {
        if !condition {
            warnings.append("line \(line): \(label)")
            notes.append("WARNING soft-band \(label)")
            print("WARNING \(label)")
        }
    }

    static func register(_ scenario: String, files: [String] = [], extras: [String] = []) {
        manifest[scenario, default: []].append(contentsOf: files + extras)
    }

    static func scenario(_ name: String, _ body: () -> Void) {
        if let only = only, only != name { return }
        print("== scenario \(name) ==")
        ran.append(name)
        body()
    }

    static func path(_ name: String) -> String { "\(out)/\(name)" }

    /// A file-backed log. `.synchronous` creates no queue and no timer, so the artifact is complete
    /// the moment the scenario returns (architect section 4 mode rules).
    static func fileLog(_ stem: String,
                        level: Int = 2,
                        mode: GameplayEventWriterMode = .synchronous,
                        maxFileBytes: Int = 8_388_608,
                        keptFiles: Int = 8,
                        ringCapacity: Int = 65_536,
                        drainBatchEvents: Int = 512) -> GameplayEventLog {
        var configuration = GameplayEventLog.Configuration()
        configuration.mode = mode
        configuration.level = level
        configuration.directoryPath = out
        configuration.filePrefix = stem
        configuration.build = "harness"
        configuration.seed = "nondeterministic"
        configuration.runToken = runToken(for: stem)
        var limits = GameplayEventLog.Limits()
        limits.ringCapacity = ringCapacity
        limits.drainBatchEvents = drainBatchEvents
        limits.maxFileBytes = maxFileBytes
        limits.keptFiles = keptFiles
        limits.drainInterval = mode == .asynchronous ? 0.05 : 0.25
        configuration.limits = limits
        return GameplayEventLog(configuration: configuration)
    }

    /// A stable per-scenario run token keeps `run_id` in the frozen 8-32 lowercase-hex shape while
    /// still separating concurrent runs.
    static func runToken(for stem: String) -> String {
        let alphabet = Array("0123456789abcdef")
        let seed = stem.unicodeScalars.reduce(17) { (($0 &* 31) &+ Int($1.value)) & 0x7fffffff }
        var token = ""
        var value = UInt64(seed) &+ UInt64(getpid())
        for _ in 0..<16 {
            value = value &* 6_364_136_223_846_793_005 &+ 1_442_695_040_888_963_407
            token.append(alphabet[Int((value >> 32) & 0xF)])
        }
        return token
    }

    static func files(matching stem: String) -> [String] {
        let names = (try? FileManager.default.contentsOfDirectory(atPath: out)) ?? []
        return names.filter { $0.hasPrefix(stem) && $0.hasSuffix(".jsonl") }.sorted()
    }

    static func text(_ name: String) -> String {
        ((try? String(contentsOfFile: "\(out)/\(name)", encoding: .utf8)) ?? "")
    }

    static func finish() -> Int {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let payload: [String: Any] = [
            "harness": "exolon-wave-a-gameplay-log",
            "revert": revert,
            "artifacts": out,
            "scenarios": manifest,
            "ran": ran,
            "notes": notes,
            "failures": failures
        ]
        if let data = try? JSONSerialization.data(withJSONObject: payload, options: [.prettyPrinted, .sortedKeys]) {
            try? data.write(to: URL(fileURLWithPath: "\(out)/manifest.json"))
        }
        if failures.isEmpty {
            print("HARNESS OK scenarios=\(ran.count) revert=\(revert)")
            return 0
        }
        print("HARNESS FAILURES \(failures.count)")
        for failure in failures { print(" - \(failure)") }
        return 1
    }
}

// MARK: - The scene's per-step emission shape, on real types

/// Mirrors the emission structure of `GameScene.fixedUpdate` (`edges -> player.update -> motion ->
/// checkScreenExit`) using the real `FixedTickDriver`, `Player`, `InputState` and
/// `StageBoundaryLedger`. `GameScene` itself imports SpriteKit and cannot be compiled here; that is
/// exactly why the four wave-A decisions were extracted into these Foundation-only types.
final class Loop {
    let events: GameplayEventLog
    let driver: FixedTickDriver
    let player = Player()
    let input = InputState()
    let boundaries: StageBoundaryLedger

    var zone = 0
    var lives = GameState.startingLives
    var ammo = GameState.startingAmmo
    var grenades = GameState.startingGrenades
    var points = 0
    var highScore = 0
    var nextLevelName = "L01S02"
    var spawnPoint = CGPoint(x: 88, y: 128)
    var previousInput: InputSnapshot?

    /// When set, the screen-exit trigger arms on the next step instead of on geometry, so a scenario
    /// can place the crossing exactly where it needs it (the audit's `x > 510` first-step case).
    /// When false the screen-exit trigger fires purely on geometry (the production rule); when true
    /// a scenario can arm it for one step without moving the player.
    var armedExit = false
    /// Geometry-only triggering: pace it with `exitStride` instead.
    var exitEveryStep = true
    var exitStride = 48
    private var stepCount = 0
    /// Portal simulation for the P1-4 scenario (the real scene asks `TMXLevelRuntime`, which is
    /// SpriteKit-bound; the latch state it reports comes from the real `Player`).
    var simulatePortal = false
    /// One-shot so the release/re-press that follows the consume really reaches `Player.update`.
    var portalSpent = false
    private var contextEdgeLatch = false

    var boundaryAwards = 0
    var boundarySuppressions = 0
    var zoneTransitions = 0
    var stepsRun = 0
    var exitThresholdX: CGFloat = 510

    init(events: GameplayEventLog,
         resetAccumulatorOnZoneTransition: Bool = true,
         awardsPerComponentPerZone: Int = 1) {
        self.events = events
        self.driver = FixedTickDriver(events: events,
                                      resetAccumulatorOnZoneTransition: resetAccumulatorOnZoneTransition)
        self.boundaries = StageBoundaryLedger(awardsPerComponentPerZone: awardsPerComponentPerZone)
        self.player.events = events
        self.player.configure(spawnCenter: spawnPoint, groundY: GameConstants.defaultGroundY)
    }

    func beginPlaythrough() { boundaries.beginPlaythrough() }

    /// Moves the real `Player` (via its own teleport) so a scenario can park it past the exit
    /// threshold and let `state.zone_exit.player_x` carry production geometry.
    func placeAtSpawn() { player.teleport(to: spawnPoint) }

    func update(_ currentTime: TimeInterval) {
        guard driver.beginFrame(currentTime: currentTime) else { return }
        events.beginFrame()
        while driver.beginStep(zone: zone) {
            stepsRun += 1
            fixedStep()
        }
    }

    func fixedStep() {
        stepCount += 1
        let rawInput = input.snapshot()
        emitEdges(current: rawInput)
        previousInput = rawInput

        var consumed = false
        if rawInput.jump, !contextEdgeLatch {
            contextEdgeLatch = true
            if simulatePortal, !portalSpent {
                portalSpent = true
                let departure = player.position
                player.teleport(to: CGPoint(x: departure.x, y: departure.y))
                consumed = true
                // Same witness the scene reports: the physically held UP at the consume.
                emitTeleport(from: departure, to: player.position,
                             jumpLatchHeld: rawInput.jump, jumpSuppressed: rawInput.jump)
            }
        } else if !rawInput.jump {
            contextEdgeLatch = false
        }
        if consumed {
            player.consumeContextualJumpPress()
        }

        // Same as the scene after the P1-4 fix: the real snapshot goes through, and Player's
        // contextual hold is what suppresses the edge.
        player.update(input: rawInput, dt: GameConstants.fixedTimeStep)
        emitMotion()
        checkScreenExit()
    }

    /// Mirrors `GameScene.emitInputEdges`, and - like the scene - emits only through the sink's
    /// producer helpers, so the lane maps under test are the ones the game runs.
    func emitEdges(current: InputSnapshot) {
        guard let previous = previousInput else { return }
        let all: [(GameAction, (InputSnapshot) -> Bool)] = [
            (.moveLeft, { $0.moveLeft }), (.moveRight, { $0.moveRight }), (.jump, { $0.jump }),
            (.crouch, { $0.crouch }), (.fire, { $0.fire }), (.grenade, { $0.grenade }),
            (.pause, { $0.pause }), (.menuUp, { $0.menuUp }), (.menuDown, { $0.menuDown }),
            (.debugHitboxes, { $0.debugHitboxes })
        ]
        for (action, projection) in all where projection(previous) != projection(current) {
            events.emitActionEdge(action, source: input.source(for: action) ?? .keyboard,
                                  pressed: projection(current),
                                  heldMilliseconds: projection(previous) ? 16_000 : 0)
        }
    }

    func emitMotion() {
        events.emitMotion(state: player.motionState, grounded: player.isGrounded, facing: player.facing,
                          exoskeleton: player.hasExoskeleton, position: player.position,
                          velocityX: player.velocity.dx, velocityY: player.velocity.dy)
    }

    func emitTeleport(from: CGPoint, to: CGPoint, jumpLatchHeld: Bool, jumpSuppressed: Bool) {
        events.emitTeleport(from: from, to: to, portalIndex: 0, jumpLatchHeld: jumpLatchHeld)
        events.emitContextualConsume(.teleport, jumpSuppressed: jumpSuppressed)
    }

    func checkScreenExit() {
        if exitEveryStep {
            guard armedExit || player.position.x > exitThresholdX else { return }
            armedExit = false
        } else {
            // One geometry trigger per FIRE cycle: the player is parked past the threshold, and the
            // original farm fires once per content-complete -> title -> continue round.
            guard stepCount % exitStride == 0, player.position.x > exitThresholdX else { return }
        }
        let playableNext = !nextLevelName.isEmpty
        events.emitZoneExit(triggerX: exitThresholdX, playerX: player.position.x,
                            hasPlayableNextLevel: playableNext)

        let outcome = boundaries.outcome(zone: zone, lives: lives, startingLives: GameState.startingLives,
                                         startingAmmo: GameState.startingAmmo,
                                         startingGrenades: GameState.startingGrenades)
        switch outcome {
        case .notApplicable:
            break
        case let .suppressed(_, reason):
            boundarySuppressions += 1
            events.emitStageBoundarySuppressed(reason)
        case let .awarded(award):
            boundaryAwards += 1
            awardPoints(award.points, reason: .stageBoundary)
            lives = award.livesAfter
            ammo = award.startingAmmo
            grenades = award.startingGrenades
            events.emitStageBoundaryPoints(points: award.points, livesBefore: award.livesBefore,
                                           livesAfter: award.livesAfter,
                                           ammoReset: award.refillsAmmoAndGrenades)
            for component in award.components {
                events.emitStageAwardComponent(component.id, points: component.points)
            }
        }

        guard playableNext else {
            enterContentComplete()
            return
        }
        transition(to: nextLevelName)
    }

    func enterContentComplete() {
        events.emitContentComplete(points: points, final: zone >= 124 && nextLevelName.isEmpty, hasNextLevel: false)
        emitFlow(from: .playing, to: .contentComplete, cause: .contentComplete)
    }

    /// The zone-124 FIRE cycle from the audit: contentComplete -> title -> continue, with the player
    /// parked past the exit threshold and the score, lives and zone carried across it.
    func returnToTitleAndRestart() {
        emitFlow(from: .contentComplete, to: .title, cause: .titleReturn)
        // `has_saved_checkpoint: true` is the audit's point: the title return continues the same
        // run, so it must not arm a fresh playthrough.
        events.emitTitleEnter(highScore: highScore, hasSavedCheckpoint: true)
        emitFlow(from: .title, to: .playing, cause: .firePress)
    }

    func emitFlow(from: GameFlowState, to: GameFlowState, cause: GameplayFlowCause) {
        events.emitFlowChange(from: from, to: to, cause: cause)
    }

    func awardPoints(_ value: Int, reason: GameplayScoreReason) {
        guard value > 0 else { return }
        let before = points
        points = min(999_999, points + value)
        events.emitScoreAwarded(points: value, pointsBefore: before, reason: reason)
        if points > highScore {
            highScore = points
            events.emitHighScoreSaved(highScore)
        }
    }

    func transition(to levelName: String) {
        let toZone = Loop.zone(for: levelName)
        events.emitZoneTransition(toZone: toZone,
                                  accumulatorMicroseconds: driver.accumulatorMicroseconds,
                                  pendingSteps: driver.pendingSteps)
        driver.reset(reason: .zoneTransition)
        zoneTransitions += 1
        events.emitZoneLoad(.transition)
        zone = toZone
        nextLevelName = toZone >= 124 ? "" : "L\(String(format: "%02d", toZone / 25 + 1))S\(String(format: "%02d", toZone % 25 + 2))"
        player.configure(spawnCenter: spawnPoint, groundY: GameConstants.defaultGroundY)
        events.emitZoneLoaded(solidCount: 12, spawnCenter: spawnPoint,
                              groundY: GameConstants.defaultGroundY, invulnerabilityTicks: 0, carriedY: false)
        events.setFlowState(.playing)
    }

    static func zone(for levelName: String) -> Int {
        let body = levelName.replacingOccurrences(of: "L", with: "").replacingOccurrences(of: "S", with: "")
        let stage = Int(body.prefix(2)) ?? 1
        let screen = Int(body.dropFirst(2)) ?? 1
        return max(0, min(124, (stage - 1) * 25 + (screen - 1)))
    }
}

extension StageBoundaryOutcome {
    var isAward: Bool { if case .awarded = self { return true }; return false }
    var isNotApplicable: Bool { if case .notApplicable = self { return true }; return false }
    func isSuppressed(with reason: GameplayStageSuppressionReason) -> Bool {
        if case let .suppressed(_, actual) = self { return actual == reason }
        return false
    }
}

// MARK: - Scenarios

/// AC-001: a realtime-shaped level-2 session - at least one `player.motion` per simulated tick,
/// every line `json.loads`-able, `log.events_dropped` absent. Also pins the record stride, the
/// tick base and the sink's `view(_:)`.
func scenarioLevel2Session() {
    let stem = "session-level2-"
    let log = Harness.fileLog(stem, level: 2, drainBatchEvents: 256)
    let loop = Loop(events: log)
    Harness.check(MemoryLayout<GameplayEvent>.stride == 24,
                  "record stride stays 24 bytes, got \(MemoryLayout<GameplayEvent>.stride)")
    Harness.check(log.emissionLevel == 2, "the session runs at emission level 2")

    var clock = 0.0
    loop.update(clock)                       // the reference frame: `frame` 0, no step
    for frame in 0..<1_300 {
        clock += 1.0 / 60.0
        switch frame {
        case 20: loop.input.set(.moveRight, pressed: true, source: .keyboard)
        case 40: loop.input.set(.jump, pressed: true, source: .keyboard)
        case 46: loop.input.set(.jump, pressed: false, source: .keyboard)
        case 60: loop.input.set(.fire, pressed: true, source: .gamepadButtons)
        case 61: loop.input.set(.fire, pressed: false, source: .gamepadButtons)
        case 90: loop.input.set(.grenade, pressed: true, source: .keyboard)
        case 92: loop.input.set(.grenade, pressed: false, source: .keyboard)
        case 120: loop.input.set(.moveRight, pressed: false, source: .keyboard)
        case 150: loop.input.set(.crouch, pressed: true, source: .gamepadDPad)
        case 170: loop.input.set(.crouch, pressed: false, source: .gamepadDPad)
        case 200: loop.armedExit = true                      // one zone transition
        case 600:
            // A stage end on the way: the boundary award is the only score funnel in the game, so
            // the session must show `score.awarded` next to `bonus.stage_points`.
            loop.zone = 24
            loop.nextLevelName = "L02S01"
            loop.armedExit = true
        default: break
        }
        loop.update(clock)
    }
    let ticks = log.tick
    log.shutdown(reason: .harnessComplete)

    let files = Harness.files(matching: stem)
    Harness.check(files.count == 1, "the session produced exactly one file, got \(files.count)")
    let lines = Harness.text(files.first ?? "").split(separator: "\n", omittingEmptySubsequences: true).map(String.init)
    let motion = lines.filter { $0.contains("\"name\":\"player.motion\"") }.count
    Harness.check(motion >= Int(ticks), "at least one player.motion per tick (motion=\(motion) ticks=\(ticks))")
    Harness.check(!lines.contains { $0.contains("\"name\":\"log.events_dropped\"") }, "a realtime level-2 session drops nothing")
    Harness.check(!lines.contains { $0.contains("\"name\":\"log.events_dropped\"") },
                  "a realtime level-2 session drops nothing")
    Harness.check(log.stats.dropped == 0, "the drop counter is zero, got \(log.stats.dropped)")
    // The identity, not just the floor: one motion per executed step, so a missing emission on any
    // tick reddens the harness as well as the checker (review R-2).
    let motionLines = lines.filter { $0.contains("\"name\":\"player.motion\"") }.count
    Harness.check(motionLines == Int(ticks),
                  "exactly one player.motion per simulated tick (motion=\(motionLines) ticks=\(Int(ticks)))")
    Harness.check(lines.first?.contains("\"name\":\"log.begin\"") == true, "the first line of the file is log.begin")
    Harness.check(lines.last?.contains("\"name\":\"log.end\"") == true, "the last line of the file is log.end")
    Harness.check(lines.contains { $0.contains("\"name\":\"tick.heartbeat\"") }, "tick.heartbeat is present")
    Harness.check(!lines.contains { $0.contains("\"name\":\"tick.frame_begin\"") }, "no per-frame heartbeat record exists")
    Harness.register("harness_level2_complete", files: files, extras: ["ticks=\(ticks)", "lines=\(lines.count)"])
}

/// AC-002 / FORBID-002: the scripted worst case - the zone exit fires on the first executed step of
/// a clamped 250 ms frame, so the whole 15-step budget is still charged when `transition` runs.
/// Fixed: 1 step before the swap, 0 after. Reverted: 1 before, 14 after.
func scenarioP19FrameGap() {
    let reverted = Harness.revert == "p1_9"
    let stem = reverted ? "p1-9-reverted-" : "p1-9-fixed-"
    let log = Harness.fileLog(stem, level: 2, drainBatchEvents: 64)
    let loop = Loop(events: log, resetAccumulatorOnZoneTransition: !reverted)
    loop.nextLevelName = "L01S02"

    var clock = 0.0
    loop.update(clock)                          // reference frame
    clock += 1.0 / 60.0
    loop.update(clock)                          // one clean step
    loop.armedExit = true                        // x crosses 510 on the next executed step
    clock += 0.5                                 // a 500 ms stall, clamped to the 250 ms budget
    loop.update(clock)
    clock += 1.0 / 60.0
    loop.update(clock)
    log.shutdown(reason: .harnessComplete)

    Harness.check(loop.zoneTransitions == 1, "exactly one transition ran, got \(loop.zoneTransitions)")
    Harness.register(reverted ? "p1_9_reverted" : "p1_9_fixed", files: Harness.files(matching: stem),
                     extras: ["steps=\(loop.stepsRun)", "ticks=\(Int(log.tick))", "revert=\(reverted)"])
    print("p1_9: revert=\(reverted) steps=\(loop.stepsRun) ticks=\(Int(log.tick)) zone=\(loop.zone)")
}

/// AC-004: UP held across a teleport, driven on the real `Player.swift`.
func scenarioP14Latch() {
    let log = Harness.fileLog("p1-4-", level: 2, drainBatchEvents: 64)
    let loop = Loop(events: log)
    loop.simulatePortal = true

    var clock = 0.0
    loop.update(clock)
    loop.input.set(.moveRight, pressed: true, source: .keyboard)
    for _ in 0..<5 {
        clock += 1.0 / 60.0
        loop.update(clock)
    }
    // The press the portal consumes; UP stays physically held afterwards.
    loop.input.set(.jump, pressed: true, source: .keyboard)
    clock += 1.0 / 60.0
    loop.update(clock)
    let teleportTick = Int(log.tick)
    for _ in 0..<12 {
        clock += 1.0 / 60.0
        loop.update(clock)                     // held UP across a dozen steps: P1-4 window
    }
    // Release, then a fresh press: the jump must come back (control for over-suppression).
    loop.input.set(.jump, pressed: false, source: .keyboard)
    clock += 1.0 / 60.0
    loop.update(clock)
    loop.input.set(.jump, pressed: true, source: .keyboard)
    for _ in 0..<3 {
        clock += 1.0 / 60.0
        loop.update(clock)
    }
    log.shutdown(reason: .harnessComplete)
    Harness.register("p1_4_latch", files: Harness.files(matching: "p1-4-"), extras: ["teleportTick=\(teleportTick)"])

    let jumps = log.view(nil).filter { $0.kind == GameplayEventKind.playerJump.rawValue }
    print("p1_4: teleportTick=\(teleportTick) bufferedJumps=\(jumps.count)")
}

/// The forbidden P1-4 shape, written directly (no `Player`), so the checker is proved able to fail
/// predicate C instead of passing for lack of data.
func scenarioP14NegativeControl() {
    let log = Harness.fileLog("p1-4-negative-control-", level: 2, drainBatchEvents: 64)
    log.beginFrame()
    log.beginTick(zone: 0)
    // teleport with the latch held, then a jump two ticks later with no release edge in between.
    log.emit(.playerTeleport, entity: GameplayPack.teleport(portalIndex: 0, jumpLatchHeld: true), 352, 512, 512, 512)
    log.emit(.inputContextualConsumed, entity: GameplayContextualAction.teleport.wireCode, 1)
    log.beginTick(zone: 0)
    log.beginTick(zone: 0)
    log.emit(.playerJump, entity: GameplayPack.jumpWitness(groundedBefore: true, afterTeleport: true), 352, 512, 660)
    log.beginTick(zone: 0)
    log.shutdown(reason: .harnessComplete)
    Harness.register("p1_4_negative_control", files: Harness.files(matching: "p1-4-negative-control-"))
}

/// AC-003 / FORBID-001: zone 124 parked past the exit threshold, cycling content-complete -> title
/// -> continue the way the audit reproduced it (one FIRE cycle per ~48 steps, i.e. 750 cycles in
/// 600 s). Reverted = unlimited awards (the audited baseline); fixed = 1 award + witnesses.
func scenarioP18StageFarm() {
    let reverted = Harness.revert == "p1_8"
    let stem = reverted ? "p1-8-reverted-" : "p1-8-fixed-"
    let log = Harness.fileLog(stem, level: 2, drainBatchEvents: 256)
    let loop = Loop(events: log, awardsPerComponentPerZone: reverted ? 0 : 1)
    loop.nextLevelName = ""                     // L05S25 carries no nextLevel: the terminal loop
    loop.zone = 124
    // Parked past the real exit threshold, exactly as the audit reproduced it: the trigger is
    // geometry (`player.position.x > 510`), so `state.zone_exit.player_x` is a production value and
    // predicate B's trigger/witness anchor can actually be evaluated (review R-4).
    loop.spawnPoint = CGPoint(x: 520, y: 128)
    loop.exitEveryStep = false
    loop.beginPlaythrough()
    loop.placeAtSpawn()
    Harness.check(loop.player.position.x > loop.exitThresholdX,
                  "the terminal zone is parked past the real exit threshold")

    var clock = 0.0
    loop.update(clock)
    for frame in 1...36_000 {
        clock += 1.0 / 60.0
        if frame % 48 == 0 {
            loop.armedExit = true               // one boundary trigger per FIRE cycle
            loop.returnToTitleAndRestart()      // contentComplete -> title -> continue
        }
        loop.update(clock)
    }
    log.shutdown(reason: .harnessComplete)

    Harness.register(reverted ? "p1_8_reverted" : "p1_8_fixed", files: Harness.files(matching: stem),
                     extras: ["awards=\(loop.boundaryAwards)", "suppressed=\(loop.boundarySuppressions)"])
    print("p1_8: revert=\(reverted) awards=\(loop.boundaryAwards) suppressed=\(loop.boundarySuppressions) points=\(loop.points)")
    Harness.check(loop.boundaryAwards + loop.boundarySuppressions >= 700,
                  "the scenario reproduces the audited repeat rate, got \(loop.boundaryAwards)+\(loop.boundarySuppressions)")
    if reverted {
        Harness.check(loop.boundaryAwards > 1, "the reverted control must award repeatedly, got \(loop.boundaryAwards)")
    } else {
        Harness.check(loop.boundaryAwards == 1, "the fixed ledger awards exactly once per playthrough, got \(loop.boundaryAwards)")
    }
}

/// AC-005: `LauncherBonusState` is the product decision - pay once, keep firing. The baseline
/// control reproduces the audited single-flag behavior so predicate D can be proved to flip.
func scenarioP16Launcher() {
    for (stem, legacySilence) in [("p1-6-fixed-", false), ("p1-6-baseline-control-", true)] {
        let log = Harness.fileLog(stem, level: 1, drainBatchEvents: 64)
        var state = LauncherBonusState()
        let objectID: UInt16 = 41
        let launcherBox = CGRect(x: 400, y: 96, width: 64, height: 48)
        let (x, y) = GameplayEvent.q(launcherBox.origin)
        log.beginFrame()

        log.beginTick(zone: 6)
        Harness.check(state.payBonus(touchesBonusRegion: true), "first touch pays the bonus (\(stem))")
        if legacySilence {
            state.deactivate()                  // what the pre-fix code did on the same flag
        }
        log.emit(.bonusDoubleLauncher, entity: objectID, Int16(truncatingIfNeeded: 1_000), x, y, state.isActive ? 1 : 0)

        log.beginTick(zone: 6)
        Harness.check(!state.payBonus(touchesBonusRegion: true), "the region pays exactly once (\(stem))")

        var sameZoneFires = 0
        for _ in 0..<20 {
            log.beginTick(zone: 6)
            guard state.canFire else { continue }
            sameZoneFires += 1
            log.emitLauncherFired(objectID: objectID, at: launcherBox.origin, muzzleY: launcherBox.minY + 40)
        }
        // AC-005 asks for "a subsequent zone load" firing the same object, so cross a real zone
        // boundary before the second half of the fire sweep (review R-6).
        log.emitZoneTransition(toZone: 7, accumulatorMicroseconds: 0, pendingSteps: 0)
        log.emitAccumulatorReset(reason: .zoneTransition, discardedMicroseconds: 0, discardedSteps: 0)
        log.emitZoneLoad(.transition)
        log.emitZoneLoaded(solidCount: 14, spawnCenter: CGPoint(x: 88, y: 128), groundY: 96,
                           invulnerabilityTicks: 0, carriedY: false)
        var laterZoneFires = 0
        for _ in 0..<20 {
            log.beginTick(zone: 7)
            guard state.canFire else { continue }
            laterZoneFires += 1
            log.emitLauncherFired(objectID: objectID, at: launcherBox.origin, muzzleY: launcherBox.minY + 40)
        }
        let fires = sameZoneFires + laterZoneFires
        log.shutdown(reason: .harnessComplete)
        Harness.check(sameZoneFires + laterZoneFires == (legacySilence ? 0 : 40),
                      "fire gate after the payout: \(sameZoneFires)+\(laterZoneFires) shots "
                      + "(\(legacySilence ? "silenced control" : "fixed"))")
        Harness.check(laterZoneFires == (legacySilence ? 0 : 20), "the launcher still fires in a later zone")
        Harness.register(legacySilence ? "p1_6_baseline_control" : "p1_6_fixed",
                         files: Harness.files(matching: stem),
                         extras: ["fires=\(fires)", "same_zone_fires=\(sameZoneFires)",
                                  "later_zone_fires=\(laterZoneFires)", "active_after=\(state.isActive)"])
    }
}

/// FORBID-004: a starved writer laps the ring, and the loss is counted and visible.
func scenarioDrops() {
    let log = Harness.fileLog("drops-", level: 2, ringCapacity: 512, drainBatchEvents: 4_096)
    // A surviving tail first: a loss that happens after records are already in the file is the case
    // the bracket fields exist for, and the only one where a fabricated window differs from a real
    // one. Then the producer outruns the ring without an intervening drain.
    for index in 0..<300 {
        log.beginTick(zone: index % 125)
        log.emit(.playerMotion, entity: 0, Int16(truncatingIfNeeded: index % 2_000), 512, 0, 0)
    }
    log.flush()
    let writtenBefore = log.seqsIssued
    for index in 300..<5_300 {
        log.beginTick(zone: index % 125)
        log.emit(.playerMotion, entity: 0, Int16(truncatingIfNeeded: index % 2_000), 512, 0, 0)
    }
    let dropped = log.stats.dropped
    Harness.check(dropped > 0, "a starved writer must report counted drops, got \(dropped)")
    Harness.check(writtenBefore > 1, "the loss must happen mid-stream so the bracket names a real record")
    log.flush()
    log.shutdown(reason: .harnessComplete)

    let files = Harness.files(matching: "drops-")
    let body = files.map { Harness.text($0) }.joined()
    Harness.check(body.contains("\"name\":\"log.events_dropped\""), "a log.events_dropped record exists")
    Harness.check(body.contains("# dropped"), "the human-readable drop marker is present")
    Harness.register("drops_counted", files: files,
                     extras: ["dropped=\(dropped)", "written_before_loss=\(writtenBefore)"])
}

/// Brief ruling 7: rotation is exercised, not dead code. Each file starts with log.begin, files are
/// linked by log.rotate and `seq` continues.
func scenarioRotation() {
    let log = Harness.fileLog("rotation-", level: 2, maxFileBytes: 4_096, keptFiles: 3, drainBatchEvents: 32)
    for index in 0..<4_000 {
        log.beginTick(zone: index % 125)
        if index % 400 == 0 {
            log.emit(.stateZoneExit, entity: 1, 2_040, Int16(truncatingIfNeeded: index % 512))
        } else {
            log.emit(.playerMotion, entity: 0, Int16(truncatingIfNeeded: index % 512), 512, 0, 0)
        }
    }
    log.shutdown(reason: .harnessComplete)
    let files = Harness.files(matching: "rotation-")
    Harness.check(files.count > 1, "rotation produced several files, got \(files.count)")
    Harness.check(files.count <= 3, "the kept-files cap is enforced: \(files.count) <= 3")
    Harness.register("rotation", files: files, extras: ["files=\(files.count)"])
}

/// INV-001..004 corners plus the unit asserts on the extracted pure state.
func scenarioContract() {
    let log = Harness.fileLog("contract-", level: 2, drainBatchEvents: 64)
    log.beginFrame()
    log.beginTick(zone: 0)
    Harness.check(log.tick == 1, "the first executed step is tick 1, got \(log.tick)")
    // A kind no build may assign: it must format as unknown<N>, never a real name.
    log.appendRawKind(200, entity: 0, 0, 0, 0, 0)
    log.appendRawKind(255, entity: 0, 0, 0, 0, 0)
    // A sweep over every declared kind, so each name appears in a real file.
    for raw in UInt8(1) ... UInt8(48) {
        guard let kind = GameplayEventKind(rawValue: raw) else { continue }
        switch kind {
        case .logBegin, .logRotate, .logEventsDropped, .logEnd: continue
        default: break
        }
        log.beginTick(zone: Int(raw) % 125)
        log.emit(kind, entity: 0, 1, 1, 1, 1)
    }
    let before = log.tick
    log.beginTick(zone: 12)
    Harness.check(log.tick > before, "tick keeps growing across zones (\(before) -> \(log.tick))")
    let tail = log.view(8).count
    Harness.check(tail > 0 && tail <= 8, "view(8) serves at most 8 records, got \(tail)")
    Harness.check(!log.describe(4).isEmpty, "describe(_:) renders the same records for the F1 tail")
    log.shutdown(reason: .harnessComplete)
    Harness.register("contract_sweep", files: Harness.files(matching: "contract-"), extras: ["firstTick=1", "unknown=200,255"])

    let level0 = Harness.fileLog("level0-", level: 0, drainBatchEvents: 64)
    level0.beginFrame()
    level0.beginTick(zone: 0)
    level0.emit(.playerMotion, entity: 0, 1, 2, 3, 4)
    level0.emit(.stateFlow, 0, 1, 0)
    level0.emit(.damagePlayerHit, 0, 1, 2, 3)
    level0.shutdown(reason: .harnessComplete)
    let level0Body = Harness.text((Harness.files(matching: "level0-").first) ?? "")
    Harness.check(!level0Body.contains("\"player.motion\""), "level 0 emits no player.motion")
    Harness.check(!level0Body.contains("\"damage.player_hit\""), "level 0 emits no damage records")
    Harness.check(level0Body.contains("\"state.flow\""), "level 0 still emits state.*")
    Harness.register("level_gating", files: Harness.files(matching: "level0-"))

    let off = Harness.fileLog("off-", level: 0, mode: .off)
    off.beginFrame()
    off.beginTick(zone: 0)
    off.emit(.stateFlow, 0, 1, 0)
    off.flush()
    off.shutdown(reason: .appQuit)
    let offFiles = Harness.files(matching: "off-")
    Harness.check(offFiles.isEmpty, "the off switch creates no file at all: \(offFiles)")
    Harness.register("kill_switch_off", files: [], extras: ["offFiles=\(offFiles.count)"])

    // Shipped configuration rules, on the pure resolver.
    let temporary = "/tmp/exolon-default"
    let debugDefault = GameplayEventLog.Configuration.resolved(environment: [:], defaultLevel: 1, temporaryDirectory: temporary, build: "1.0+1")
    Harness.check(debugDefault.mode == .asynchronous && debugDefault.level == 1, "Debug default = level 1, asynchronous")
    Harness.check(debugDefault.directoryPath == "/tmp/exolon-default/exolon", "the default directory is outside the clone: \(debugDefault.directoryPath)")
    let releaseDefault = GameplayEventLog.Configuration.resolved(environment: [:], defaultLevel: 0, temporaryDirectory: temporary, build: "1.0+1")
    Harness.check(releaseDefault.mode == .off, "Release default = off")
    Harness.check(GameplayEventLog.Configuration.resolved(environment: ["EXOLON_EVENT_LOG": "off"], defaultLevel: 2, temporaryDirectory: temporary, build: "harness").mode == .off,
                  "EXOLON_EVENT_LOG=off beats a level-2 default")
    Harness.check(GameplayEventLog.Configuration.resolved(environment: ["EXOLON_EVENT_LOG": "2"], defaultLevel: 0, temporaryDirectory: temporary, build: "harness").level == 2,
                  "EXOLON_EVENT_LOG=2 raises the level")
    let custom = GameplayEventLog.Configuration.resolved(environment: ["EXOLON_EVENT_LOG": "/tmp/exolon-custom-dir"], defaultLevel: 1, temporaryDirectory: temporary, build: "harness")
    Harness.check(custom.directoryPath == "/tmp/exolon-custom-dir", "EXOLON_EVENT_LOG=<path> overrides the directory")

    // Unit asserts: FixedTickDriver (clamp, budget, reset).
    let silentConfiguration = GameplayEventLog.Configuration()
    let driverLog = GameplayEventLog(configuration: silentConfiguration, writer: GameplayEventMemoryWriter())
    let driver = FixedTickDriver(events: driverLog)
    Harness.check(driver.stepBudget == 15, "the catch-up budget is floor(0.25/(1/60))=15, got \(driver.stepBudget)")
    _ = driver.beginFrame(currentTime: 0)
    _ = driver.beginFrame(currentTime: 0.5)
    var steps = 0
    while driver.beginStep(zone: 0) { steps += 1 }
    Harness.check(steps == 15, "a 0.5 s frame runs exactly the 15-step budget, got \(steps)")
    Harness.check(driver.accumulator < GameConstants.fixedTimeStep, "the accumulator is drained below one step")
    _ = driver.beginFrame(currentTime: 0.6)
    Harness.check(driver.pendingSteps >= 5, "the remainder stays charged for the next frame, got \(driver.pendingSteps)")
    driver.reset(reason: .zoneTransition)
    Harness.check(driver.accumulator == 0, "reset discards the remainder")
    Harness.check(driver.pendingSteps == 0, "no step is pending after a reset")
    Harness.check(driverLog.tick == UInt32(steps), "reset does not invent or rewind ticks, got \(driverLog.tick)")
    let frameBefore = driverLog.frame
    driver.reset(reason: .newGame)
    Harness.check(driverLog.frame == frameBefore, "reset never rewinds the frame counter")
    Harness.register("fixed_tick_driver_units", extras: ["steps=\(steps)"])

    // Unit asserts: StageBoundaryLedger (once + suppression + playthrough boundary).
    let ledger = StageBoundaryLedger()
    Harness.check(ledger.outcome(zone: 24, lives: 9, startingLives: 9, startingAmmo: 99, startingGrenades: 10).isAward,
                  "zone 24 awards once")
    Harness.check(ledger.outcome(zone: 24, lives: 9, startingLives: 9, startingAmmo: 99, startingGrenades: 10)
                    .isSuppressed(with: .alreadyAwarded), "a repeat of zone 24 is suppressed with a witness")
    Harness.check(ledger.outcome(zone: 25, lives: 9, startingLives: 9, startingAmmo: 99, startingGrenades: 10).isNotApplicable,
                  "a non stage-end zone produces no record at all")
    ledger.beginPlaythrough()
    Harness.check(ledger.outcome(zone: 24, lives: 9, startingLives: 9, startingAmmo: 99, startingGrenades: 10).isAward,
                  "a new playthrough may award the same zone again")
    if case let .awarded(award) = ledger.outcome(zone: 49, lives: 4, startingLives: 9, startingAmmo: 99, startingGrenades: 10) {
        Harness.check(award.points == 4_000, "the lives x 1000 identity holds, got \(award.points)")
        Harness.check(award.livesAfter == 5, "the boundary returns one life, capped at the start")
        Harness.check(award.components.reduce(0) { $0 + $1.points } == award.points, "the total is the sum of its components")
    } else {
        Harness.check(false, "zone 49 must award in a fresh playthrough")
    }
    // Zero lives still *awards* (points 0), exactly as the pre-fix code did; the guard that keeps a
    // zero award out of `score.awarded` lives in GameScene.awardPoints, not in the ledger.
    Harness.check(ledger.awardedZonesInPlaythrough.contains(24), "the ledger remembers what it awarded")
    Harness.register("stage_boundary_ledger_units")

    // Unit asserts: LauncherBonusState (pay once vs active).
    var bonus = LauncherBonusState()
    Harness.check(bonus.payBonus(touchesBonusRegion: true), "the region pays on first touch")
    Harness.check(bonus.isActive, "the payout leaves the launcher firing (ruling 2)")
    Harness.check(!bonus.payBonus(touchesBonusRegion: true), "the payout is once per zone instantiation")
    bonus.deactivate()
    Harness.check(!bonus.canFire, "deactivate is the only path that stops firing")
    Harness.check(!bonus.payBonus(touchesBonusRegion: true), "a destroyed launcher cannot pay")
    Harness.register("launcher_bonus_state_units")

    // Unit asserts: the P1-4 latch on the real Player.
    let latchedPlayer = Player()
    latchedPlayer.configure(spawnCenter: CGPoint(x: 88, y: 128), groundY: GameConstants.defaultGroundY)
    let held = InputSnapshot(moveLeft: false, moveRight: false, jump: true, crouch: false, fire: false,
                             grenade: false, pause: false, menuUp: false, menuDown: false, debugHitboxes: false)
    let released = InputSnapshot(moveLeft: false, moveRight: false, jump: false, crouch: false, fire: false,
                                 grenade: false, pause: false, menuUp: false, menuDown: false, debugHitboxes: false)
    latchedPlayer.teleport(to: CGPoint(x: 200, y: 128))
    latchedPlayer.consumeContextualJumpPress()
    Harness.check(latchedPlayer.jumpLatchHeld, "a teleport reports the held latch to player.teleport")
    var jumpedWhileHeld = false
    for _ in 0..<8 {
        latchedPlayer.update(input: held, dt: GameConstants.fixedTimeStep)
        if latchedPlayer.velocity.dy > 100 { jumpedWhileHeld = true }
    }
    Harness.check(!jumpedWhileHeld, "P1-4: a held UP cannot jump after a contextual consume")
    latchedPlayer.update(input: released, dt: GameConstants.fixedTimeStep)
    latchedPlayer.update(input: held, dt: GameConstants.fixedTimeStep)
    Harness.check(latchedPlayer.velocity.dy > 100, "a release followed by a fresh press still jumps (no over-suppression)")
    Harness.register("player_latch_units")
}

/// INV-001/§3 class closure (code review R1-1..R1-4): **every** wire-reachable record is packed by
/// its production helper from `GameplayEventSink.swift` with distinctive values, formatted, written,
/// read back and compared field by field. A swapped lane, a wrong bit offset or a misread lane pair
/// fails here - which is precisely the class that shipped four wire lies while the gate stayed green.
///
/// Expectations are literal numbers, not recomputed from the encoder, so a wrong derivation fails
/// too (`lane-roundtrip.tsv` carries them for `gameplay_log_check.py::lane_round_trip_is_exact`).
func scenarioLaneRoundTrip() {
    let stem = "lane-roundtrip-"
    let log = Harness.fileLog(stem, level: 2, drainBatchEvents: 512)
    var expectations: [(String, [(String, String)])] = []

    func expect(_ name: String, _ fields: [(String, String)]) { expectations.append((name, fields)) }
    func num(_ value: Int) -> String { String(value) }
    func flag(_ value: Bool) -> String { value ? "true" : "false" }

    log.beginFrame()
    log.beginTick(zone: 7)

    // input
    log.emitActionEdge(.jump, source: .gamepadDPad, pressed: true, heldMilliseconds: 250)
    expect("input.action_edge", [("action", "jump"), ("pressed", "true"), ("source", "gamepadDPad"),
                                 ("held_us", "250000")])
    log.emitPausePressConsumed()
    expect("input.pause_consumed", [("pending", "true")])
    log.emitContextualConsume(.teleport, jumpSuppressed: true)
    expect("input.contextual_consumed", [("kind", "teleport"), ("jump_suppressed", "true")])

    // player
    log.emitMotion(state: .running, grounded: true, facing: .right, exoskeleton: true,
                   position: CGPoint(x: 300.25, y: 128.5), velocityX: 90, velocityY: -300)
    expect("player.motion", [("zone", "7"), ("x", "1201"), ("y", "514"), ("vx", "360"), ("vy", "-1200"),
                             ("grounded", "true"), ("motion_state", "running"), ("facing", "right"),
                             ("exoskeleton", "true")])
    log.emitJump(position: CGPoint(x: 100.5, y: 200.25), velocity: 165, groundedBefore: true, afterTeleport: false)
    expect("player.jump", [("x", "402"), ("y", "801"), ("velocity", "660"), ("grounded_before", "true"),
                           ("after_teleport", "false")])
    log.emitLand(position: CGPoint(x: 64.75, y: 128), fallSpeed: -250, support: .solid)
    expect("player.land", [("x", "259"), ("y", "512"), ("vy_before", "-1000"), ("support", "solid")])
    log.emitCrouchEdge(begins: true, position: CGPoint(x: 48.5, y: 160))
    expect("player.crouch_begin", [("x", "194"), ("y", "640")])
    log.emitCrouchEdge(begins: false, position: CGPoint(x: 48.5, y: 160))
    expect("player.crouch_end", [("x", "194"), ("y", "640")])
    log.emitExoskeleton(enabled: true, cause: .cheat)
    expect("player.exoskeleton", [("enabled", "true"), ("cause", "cheat")])
    log.emitBlasterShot(origin: CGPoint(x: 122.25, y: 96.5), facing: .left, double: true,
                        ammoBefore: 99, ammoAfter: 98)
    expect("player.shoot_blaster", [("x", "489"), ("y", "386"), ("facing", "left"), ("double", "true"),
                                    ("ammo_before", "99"), ("ammo_after", "98")])
    log.emitShootDenied(.noAmmo, ammo: 0)
    expect("player.shoot_denied", [("reason", "no_ammo"), ("ammo", "0")])
    log.emitGrenadeThrow(origin: CGPoint(x: 200, y: 140.25), direction: .right, grenadesBefore: 10,
                         grenadesAfter: 9, blockedByOneInFlight: false)
    expect("player.throw_grenade", [("x", "800"), ("y", "561"), ("direction", "right"),
                                    ("grenades_before", "10"), ("grenades_after", "9"),
                                    ("blocked_by", "none")])
    log.emitGrenadeThrow(origin: CGPoint(x: 200, y: 140.25), direction: .left, grenadesBefore: 7,
                         grenadesAfter: 7, blockedByOneInFlight: true)
    expect("player.throw_grenade", [("x", "800"), ("y", "561"), ("direction", "left"),
                                    ("grenades_before", "7"), ("grenades_after", "7"),
                                    ("blocked_by", "one_in_flight")])
    log.emitTeleport(from: CGPoint(x: 96, y: 128.5), to: CGPoint(x: 400.25, y: 224), portalIndex: 3,
                     jumpLatchHeld: true)
    expect("player.teleport", [("from.x", "384"), ("from.y", "514"), ("to.x", "1601"), ("to.y", "896"),
                              ("portal_index", "3"), ("jump_latch_held", "true")])
    log.emitDeathBegin(position: CGPoint(x: 150.5, y: 130), lives: 9, ammo: 42, grenades: 8)
    expect("player.death_begin", [("x", "602"), ("y", "520"), ("lives", "9"), ("ammo", "42"),
                                  ("grenades", "8")])
    log.emitDeathLanded(position: CGPoint(x: 150.5, y: 96), groundTicks: 5)
    expect("player.death_landed", [("x", "602"), ("y", "384"), ("ground_ticks", "5")])
    log.emitDeathSettled(livesBefore: 4, livesAfter: 3, invulnerabilityTicks: 24, settleTicks: 70,
                         checkpointSaved: true)
    expect("player.death_settled", [("delay_us", "1166667"), ("lives_before", "4"), ("lives_after", "3"),
                                     ("invulnerability_us", "400000"), ("checkpoint_saved", "true")])

    // game / damage
    log.beginTick(zone: 12)
    log.emitGameOver(points: 123456, highScore: 654321, checkpointCleared: true)
    expect("game.game_over", [("points", "123456"), ("high_score", "654321"), ("zone", "12"),
                              ("checkpoint_cleared", "true")])
    log.emitBlockedHit(cause: .forceField, invulnerabilityMicroseconds: 321_000, testInvulnerability: true)
    expect("damage.player_blocked", [("cause", "force_field"), ("invulnerability_us", "321000"),
                                     ("test_invulnerability", "true")])
    log.beginTick(zone: 30)
    log.emitPlayerHit(cause: .missile, position: CGPoint(x: 510.75, y: 200), flowBefore: .playing,
                      flowAfter: .playerDead, lives: 2)
    expect("damage.player_hit", [("cause", "missile"), ("x", "2043"), ("y", "800"),
                                 ("flow_state_before", "playing"), ("flow_state_after", "playerDead"),
                                 ("lives", "2")])

    // pickup / bonus / score
    log.emitPickupCollected(.grenadePack, countBefore: 3, countAfter: 10, at: CGPoint(x: 64, y: 96))
    expect("pickup.collect", [("kind", "grenade_pack"), ("count_before", "3"), ("count_after", "10"),
                              ("x", "256"), ("y", "384")])
    log.emitPickupCollected(.ammoPack, countBefore: 12, countAfter: 99, at: CGPoint(x: 320.5, y: 160))
    expect("pickup.collect", [("kind", "ammo_pack"), ("count_before", "12"), ("count_after", "99"),
                              ("x", "1282"), ("y", "640")])
    log.emitDoubleLauncherBonus(points: 1000, launcherObjectID: 41, at: CGPoint(x: 400, y: 96),
                               launcherActiveAfter: true)
    expect("bonus.double_launcher", [("points", "1000"), ("completed_zone", "30"),
                                     ("launcher_object_id", "41"), ("x", "1600"), ("y", "384"),
                                     ("launcher_active_after", "true")])
    log.emitStageBoundaryPoints(points: 9000, livesBefore: 9, livesAfter: 9, ammoReset: true)
    expect("bonus.stage_points", [("completed_zone", "30"), ("points", "9000"), ("lives_before", "9"),
                                  ("lives_after", "9"), ("ammo_reset", "true")])
    log.emitStageAwardComponent(.livesTimes1000, points: 9000)
    expect("bonus.stage_component", [("completed_zone", "30"), ("component_id", "lives_x1000"),
                                      ("points", "9000")])
    log.emitStageBoundarySuppressed(.alreadyAwarded)
    expect("bonus.stage_boundary_suppressed", [("completed_zone", "30"), ("reason", "already_awarded")])
    log.emitScoreAwarded(points: 1000, pointsBefore: 998_500, reason: .guidance)
    expect("score.awarded", [("points", "1000"), ("reason", "guidance"), ("points_before", "998500"),
                             ("points_after", "999500"), ("clamped", "false")])
    log.emitScoreAwarded(points: 9000, pointsBefore: 995_000, reason: .stageBoundary)
    expect("score.awarded", [("points", "9000"), ("reason", "stage_boundary"), ("points_before", "995000"),
                             ("points_after", "999999"), ("clamped", "true")])
    log.emitHighScoreSaved(654321)
    expect("score.high_score_saved", [("value", "654321")])

    // state
    log.emitFlowChange(from: .title, to: .playing, cause: .firePress)
    expect("state.flow", [("from", "title"), ("to", "playing"), ("cause", "fire_press")])
    log.beginTick(zone: 25)
    log.emitZoneLoad(.checkpoint)
    expect("state.zone_load", [("resource", "L02S01"), ("zone", "25"), ("cause", "checkpoint")])
    log.emitZoneLoaded(solidCount: 240, spawnCenter: CGPoint(x: 88.25, y: 128), groundY: 96.5,
                       invulnerabilityTicks: 24, carriedY: true)
    expect("state.zone_loaded", [("resource", "L02S01"), ("zone", "25"), ("solid_count", "240"),
                                 ("spawn_x", "353"), ("spawn_y", "512"), ("ground_y", "386"),
                                 ("invulnerability_us", "400000"), ("carried_y", "true")])
    log.emitZoneExit(triggerX: 510, playerX: 544, hasPlayableNextLevel: true)
    expect("state.zone_exit", [("zone", "25"), ("trigger_x", "2040"), ("player_x", "2176"),
                               ("next_level", "L02S02")])
    log.emitZoneExit(triggerX: 510, playerX: 512.25, hasPlayableNextLevel: false)
    expect("state.zone_exit", [("zone", "25"), ("trigger_x", "2040"), ("player_x", "2049"),
                               ("next_level", "")])
    log.beginTick(zone: 26)
    log.emitZoneTransition(toZone: 27, accumulatorMicroseconds: 233_333, pendingSteps: 14)
    expect("state.zone_transition", [("from_zone", "26"), ("to_zone", "27"),
                                     ("accumulator_us", "233333"), ("pending_steps", "14")])
    log.beginTick(zone: 124)
    log.emitContentComplete(points: 250_000, final: true, hasNextLevel: false)
    expect("state.content_complete", [("zone", "124"), ("next_level", ""), ("points", "250000"),
                                      ("final", "true")])
    log.emitTitleEnter(highScore: 999_999, hasSavedCheckpoint: false)
    expect("state.title_enter", [("high_score", "999999"), ("has_saved_checkpoint", "false")])
    log.emitCheckpointSaved(ammo: 99, grenades: 10, lives: 3, points: 456_789)
    expect("state.checkpoint_saved", [("resource", "L05S25"), ("ammo", "99"), ("grenades", "10"),
                                      ("points", "456789"), ("lives", "3")])
    log.emitCheckpointCleared(.gameOver)
    expect("state.checkpoint_cleared", [("reason", "game_over")])
    log.emitPauseChanged(entering: true, stateBefore: .respawning, selectedIndex: 1)
    expect("state.pause_enter", [("state_before", "respawning"), ("selected_index", "1")])
    log.emitPauseChanged(entering: false, stateBefore: .playing, selectedIndex: 0)
    expect("state.pause_exit", [("state_before", "playing"), ("selected_index", "0")])
    log.emitRunRestarted(discardedPoints: 123_456)
    expect("state.restart", [("from_zone", "124"), ("points", "123456")])
    log.emitCheatInvulnerability(enabled: true, menuIndex: 1)
    expect("state.cheat_invulnerability", [("enabled", "true"), ("menu_index", "1")])

    // tick anomalies + entity
    log.emitFrameGapClamped(rawMicroseconds: 481_234)
    expect("tick.frame_gap_clamped", [("raw_frame_time_us", "481234"), ("clamp_us", "250000"),
                                      ("lost_us", "231234")])
    log.emitAccumulatorReset(reason: .pausedExit, discardedMicroseconds: 8_333, discardedSteps: 0)
    expect("tick.accumulator_reset", [("reason", "paused_exit"), ("discarded_us", "8333"),
                                      ("discarded_steps", "0")])
    log.emitSlowStep(stepMicroseconds: 33_334, stepsThisFrame: 2)
    expect("tick.slow_step", [("step_us", "33334"), ("budget_us", "16667"), ("steps_this_frame", "2")])
    log.emitLauncherFired(objectID: 41, at: CGPoint(x: 400, y: 96), muzzleY: 136.25)
    expect("entity.launcher_fire", [("object_id", "41"), ("kind", "double_launcher"), ("x", "1600"),
                                    ("y", "384"), ("muzzle_y", "545")])

    // unknown raw value: never aliases a real name, and carries no payload
    log.appendRawKind(200, entity: 0, 7, 7, 7, 7)
    expect("unknown200", [])
    log.appendRawKind(255, entity: 0, 0, 0, 0, 0)
    expect("unknown255", [])

    // tick.heartbeat is writer/composer-built: exercise it through beginTick (every 600 steps)
    while Int(log.tick) % 600 != 0 { log.beginTick(zone: 124) }
    log.shutdown(reason: .harnessComplete)

    var tsv = "kind\tfield=value\n"
    for (name, fields) in expectations {
        tsv += name + "\t" + fields.map { "\($0)=\($1)" }.joined(separator: "\t") + "\n"
    }
    try? tsv.write(to: URL(fileURLWithPath: Harness.path("lane-roundtrip.tsv")), atomically: true,
                   encoding: .utf8)
    let files = Harness.files(matching: stem)
    Harness.check(files.count >= 1, "the lane round-trip stream exists")
    let heartbeat = expectations.filter { $0.0 == "tick.heartbeat" }.count
    Harness.check(heartbeat == 0, "heartbeat is asserted from the stream, not the expectation table")
    Harness.register("lane_round_trip", files: files + ["lane-roundtrip.tsv"],
                     extras: ["records=\(expectations.count)", "heartbeat_expected=true"])
}

/// The shipped Debug posture is `.asynchronous` (one serial queue + drain timer). Nothing else on
/// this host ever builds it, so the queue/timer path is executed here: level 2, realtime-shaped
/// emission, and the drain must lose nothing.
func scenarioAsyncWriter() {
    let stem = "async-"
    var configuration = GameplayEventLog.Configuration()
    configuration.mode = .asynchronous
    configuration.level = 2
    configuration.directoryPath = Harness.out
    configuration.filePrefix = stem
    configuration.build = "harness"
    configuration.seed = "nondeterministic"
    configuration.runToken = Harness.runToken(for: stem)
    var limits = GameplayEventLog.Limits()
    limits.drainInterval = 0.02
    limits.drainBatchEvents = 128
    limits.heartbeatSteps = 600
    configuration.limits = limits
    // `GameplayEventLog(configuration:)` is the production convenience initializer: it builds the
    // real file writer, so this scenario exercises the shipped queue + timer + file path.
    let log = GameplayEventLog(configuration: configuration)
    log.beginFrame()
    let perFrame = 12
    for frame in 0..<1_300 {
        log.beginTick(zone: frame % 125)
        for lane in 0..<perFrame {
            log.emitMotion(state: .idle, grounded: true, facing: .right, exoskeleton: false,
                           position: CGPoint(x: 88, y: 128), velocityX: 0, velocityY: CGFloat(lane))
        }
        if frame % 97 == 0 { log.requestDrain() }
    }
    log.flush()
    let stats = log.stats
    log.shutdown(reason: .harnessComplete)
    Harness.check(stats.dropped == 0, "the asynchronous drain lost nothing: dropped=\(stats.dropped)")
    Harness.check(stats.pending == 0, "the final flush drained the ring: pending=\(stats.pending)")
    let files = Harness.files(matching: stem)
    let records = files.flatMap { name in
        Harness.text(name).split(separator: "\n", omittingEmptySubsequences: true).compactMap {
            line in try? JSONSerialization.jsonObject(with: Data(line.utf8)) as? [String: Any]
        }
    }
    let motions = records.filter { ($0["name"] as? String) == "player.motion" }.count
    let heartbeats = records.filter { ($0["name"] as? String) == "tick.heartbeat" }.count
    Harness.check(motions == 1_300 * perFrame, "async stream carries every motion: \(motions)")
    Harness.check(heartbeats >= 2, "async stream carries \(heartbeats) heartbeats (600-tick period)")
    Harness.register("async_writer", files: files,
                     extras: ["motions=\(motions)", "dropped=\(stats.dropped)", "ticks=1300"])
}

/// AC-006: what the fixed step actually pays for emission, plus the two measurements that make the
/// number meaningful - the rejected design's cost and the writer's throughput.
///
/// In production the format-and-write work runs on the drain queue, so the only cost that can drop
/// a frame is the locked append. `.synchronous` mode puts that work on the caller thread - which is
/// what the harness does - so measuring only that would misstate the design, and measuring only the
/// append would hide a writer that cannot keep up.
func scenarioCostBudget() {
    func configuration(_ mode: GameplayEventWriterMode, prefix: String) -> GameplayEventLog.Configuration {
        var configuration = GameplayEventLog.Configuration()
        configuration.mode = mode
        configuration.level = 2
        configuration.directoryPath = Harness.out
        configuration.filePrefix = prefix
        configuration.runToken = Harness.runToken(for: prefix)
        var limits = GameplayEventLog.Limits()
        limits.drainBatchEvents = 4_096
        limits.ringCapacity = 65_536
        configuration.limits = limits
        return configuration
    }
    let eventsPerTick = 60
    let ticks = 50_000

    // 1. The hot path: beginTick plus 60 locked appends. No I/O, no formatting (production shape).
    let producer = GameplayEventLog(configuration: configuration(.off, prefix: "cost-producer-"), writer: DiscardWriter())
    producer.beginFrame()
    let start = DispatchTime.now().uptimeNanoseconds
    for index in 0..<ticks {
        producer.beginTick(zone: index % 125)
        for lane in 0..<eventsPerTick {
            producer.emit(.playerMotion, entity: 0, 352, 512, Int16(truncatingIfNeeded: lane), 6)
        }
    }
    let producerNs = Double(DispatchTime.now().uptimeNanoseconds - start) / Double(ticks * eventsPerTick)
    let percentOfTick = producerNs * Double(eventsPerTick) / 16_667_000 * 100

    // 2. Control: per-event String formatting on the same path - the design M4 rejected at 28x the
    //    append. A dead clock, or a probe that measured nothing, cannot land >5x away.
    let controlTicks = 20_000
    let controlStart = DispatchTime.now().uptimeNanoseconds
    var bytes = 0
    for index in 0..<controlTicks {
        let line = "{\"schema_version\":1,\"seq\":\(index),\"tick\":\(index),\"frame\":\(index / 60),\"rot\":0,"
            + "\"ts_us\":\(index * 16667),\"name\":\"player.motion\",\"zone\":\(index % 125),\"x\":352,"
            + "\"y\":512,\"vx\":0,\"vy\":6,\"grounded\":true}\n"
        bytes += line.utf8.count
    }
    let controlNs = Double(DispatchTime.now().uptimeNanoseconds - controlStart) / Double(controlTicks)
    Harness.check(bytes > controlTicks * 120, "the control actually formatted records, bytes=\(bytes)")
    Harness.check(controlNs > producerNs * 5,
                  "per-event formatting must cost >5x the locked append (\(controlNs) vs \(producerNs))")

    // 3. The writer's throughput: format + buffer + write, off the frame path in production.
    let pipeline = GameplayEventLog(configuration: configuration(.synchronous, prefix: "cost-pipeline-"), writer: DiscardWriter())
    pipeline.beginFrame()
    let drainStart = DispatchTime.now().uptimeNanoseconds
    for index in 0..<10_000 {
        pipeline.beginTick(zone: index % 125)
        for lane in 0..<eventsPerTick {
            pipeline.emit(.playerMotion, entity: 0, 352, 512, Int16(truncatingIfNeeded: lane), 6)
        }
    }
    let drainNs = Double(DispatchTime.now().uptimeNanoseconds - drainStart) / Double(10_000 * eventsPerTick)
    let eventsPerSecond = 1_000_000_000 / drainNs
    pipeline.shutdown(reason: .harnessComplete)

    // 60 events per step at 60 Hz = 3 600 ev/s, the worst credible realtime rate (M11 arithmetic).
    Harness.check(eventsPerSecond > 3_600 * 8,
                  "the drain must clear >= 8x the worst realtime rate, got \(Int(eventsPerSecond)) ev/s")
    // `.off` performs no drain at all (that is what makes it the kill switch), so this ring
    // laps by construction in the probe; the pipeline probe below is the one that must keep up.
    Harness.check(pipeline.stats.dropped == 0, "the pipeline probe did not overflow its ring: \(pipeline.stats.dropped)")
    // Wave E1 (issue #22 item 5): the four absolute timing bands below measure wall-clock cost on
    // whatever host runs the harness, so they are reported as WARNINGs with the measured value -
    // they tripped under load 16-18 while the code was unchanged. Everything deterministic stays
    // a hard `check`: the clock-measured-something floor, the >5x formatting-control RELATION two
    // lines above, the 8x realtime drain floor, and the static allocation scan in the Python gate.
    Harness.check(producerNs > 1,
                  "the append clock must measure a real cost (sanity floor, not a budget), got \(producerNs) ns")
    Harness.warn(producerNs * 60 < 5_000,
                 "60 locked appends near 4 us (M3) is a load-sensitive band, got \(producerNs * 60) ns")
    Harness.warn(percentOfTick <= 0.5,
                 "level-2 emission under 0.5 % of a tick (spec budget 5 %) is load-sensitive, got \(percentOfTick) %")
    Harness.warn(percentOfTick <= 5,
                 "level-2 emission cost <= 5 % of a 16.67 ms tick is load-sensitive, measured \(percentOfTick) %")
    Harness.warn(producerNs > 0.5 && producerNs < 1_000,
                 "the append landing in the sizing band (M2/M3: 55-70 ns) is load-sensitive, got \(producerNs) ns")
    Harness.register("emission_cost", files: [], extras: [
        "producer_ns_per_event=\(String(format: "%.2f", producerNs))",
        "percent_of_tick=\(String(format: "%.4f", percentOfTick))",
        "formatting_control_ns_per_event=\(String(format: "%.2f", controlNs))",
        "drain_ns_per_event=\(String(format: "%.2f", drainNs))",
        "drain_capacity_ev_per_s=\(Int(eventsPerSecond))"
    ])
    print(String(format: "COST hot-path=%.1f ns/event (%.4f %% of a tick at 60 ev/step); formatting=%.1f ns; drain=%.0f ev/s",
                 producerNs, percentOfTick, controlNs, eventsPerSecond))
}

/// The frozen contract as text: kinds, labels, levels, lane maps and every label domain.
/// `gameplay_log_check.py` diffs this against the JSON schema, so a renamed label or a renumbered
/// raw value fails on Linux instead of on somebody's Mac.
func scenarioContractDump() {
    let lines = GameplayWire.contractDump()
    let url = URL(fileURLWithPath: Harness.path("contract.txt"))
    try? lines.joined(separator: "\n").write(to: url, atomically: true, encoding: .utf8)
    Harness.check(lines.contains { $0.hasPrefix("stride\tGameplayEvent\t24") }, "the record stays a 24-byte struct")
    let drift = GameplayWire.labelVocabularyMatchesSwiftCases()
    Harness.check(drift.isEmpty, "wire labels still equal the Swift vocabulary: \(drift)")
    Harness.check(lines.contains { $0.hasPrefix("kind\t48\tentity.launcher_fire") }, "entity.launcher_fire is kind 48")
    Harness.register("contract_dump", files: ["contract.txt"], extras: ["lines=\(lines.count)"])
}

// MARK: - Entry point

if Harness.out.isEmpty || !Harness.out.hasPrefix("/") {
    FileHandle.standardError.write(Data("EXOLON_HARNESS_OUT must be an absolute directory outside the clone\n".utf8))
    exit(66)
}
let manager = FileManager.default
if manager.fileExists(atPath: Harness.out) {
    try? manager.removeItem(atPath: Harness.out)
}
try? manager.createDirectory(atPath: Harness.out, withIntermediateDirectories: true, attributes: nil)

Harness.scenario("level2", scenarioLevel2Session)
Harness.scenario("p1_9", scenarioP19FrameGap)
Harness.scenario("p1_4", scenarioP14Latch)
Harness.scenario("p1_4_control", scenarioP14NegativeControl)
Harness.scenario("p1_8", scenarioP18StageFarm)
Harness.scenario("p1_6", scenarioP16Launcher)
Harness.scenario("drops", scenarioDrops)
Harness.scenario("rotation", scenarioRotation)
Harness.scenario("lane_round_trip", scenarioLaneRoundTrip)
Harness.scenario("async_writer", scenarioAsyncWriter)
Harness.scenario("contract", scenarioContract)
Harness.scenario("cost", scenarioCostBudget)
Harness.scenario("contract_dump", scenarioContractDump)
exit(Int32(Harness.finish()))
