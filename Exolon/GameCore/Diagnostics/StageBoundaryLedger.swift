import Foundation

/// What a boundary knew at the moment it was evaluated. Wave A's single component needs only
/// `lives`; wave D's two appended components need the simulation coordinate and the exoskeleton
/// latch, so the component rule takes this instead of reading global state - which is what keeps
/// the whole sequence a pure function of its inputs (`stage_boundary_check.py` re-derives the
/// table on Linux, and `analysis-architect.md` section 6 forbids a wall clock here).
struct StageBoundaryContext: Equatable {
    /// Fixed steps elapsed since the current stage started (`stepCount - stageStartStep`).
    /// It is a *relative* coordinate on purpose: the auditor recomputes it from `tick`/`ts_us`
    /// deltas in the log, never from an absolute value it would have to trust.
    /// `nil` means "this caller never observed the clock", and the ladder then pays **zero** -
    /// an unobserved phase must never be silently read as the fastest, best one.
    let stageElapsedSteps: Int?
    /// Activation latch, `ORIGINAL_MECHANICS.md:142` read as "was taken during the stage"
    /// (owner ruling, wave D): arming the suit in any changing room of the stage forfeits the
    /// bravery award at that stage's boundary even if it is switched back off before the exit.
    /// The `:118` "having it on" reading is falsified by `bravery_latch_distinguishes`.
    let tookExoskeletonInStage: Bool

    /// Wave A's shape: no clock observation, suit taken. It therefore pays exactly the
    /// `lives * 1000` clause it always paid, and nothing else.
    static let waveA = StageBoundaryContext(stageElapsedSteps: nil, tookExoskeletonInStage: true)
}

/// A stage-boundary award component. Wave A implements exactly one: the original
/// `lives * 1000` bonus. The sequence is a list so a later wave can append the bravery award and
/// the timed-travel ladder as further components **without touching the `GameScene` seam, the
/// witness events or the once-key logic** (controller amendment, 2026-09-24).
///
/// Append-only: a new component needs a new `GameplayStageComponent` code, a case here and a
/// branch in `points(for:lives:context:)`; nothing else.
enum GameplayStageComponentSequence {
    /// The ordered award sequence for one completed stage boundary.
    static let waveA: [GameplayStageComponent] = [.livesTimes1000]

    /// The full `ORIGINAL_MECHANICS.md:140-146` award sequence (wave D, owner gate ruling 2):
    /// lives, bravery, then the deterministic timed ladder. The order is the norm's own order and
    /// `points` is still the sum, so wave A's predicate B keeps holding unchanged.
    static let waveD: [GameplayStageComponent] = [.livesTimes1000, .braveryNoExoskeleton,
                                                  .timedPhaseLadder]

    /// Points this component contributes given the state at the boundary. Exhaustive on purpose:
    /// a new component cannot silently contribute zero.
    static func points(for component: GameplayStageComponent, lives: Int,
                       context: StageBoundaryContext = .waveA) -> Int {
        switch component {
        case .livesTimes1000:
            return lives * 1_000
        case .braveryNoExoskeleton:
            return context.tookExoskeletonInStage ? 0 : GameConstants.braveryBonus
        case .timedPhaseLadder:
            guard let phase = phase(in: context) else { return 0 }
            return GameConstants.timedBonusLadder[phase]
        }
    }

    /// The timed ladder's phase for a context: `min(4, elapsed / PHASE_TICKS)`, index 0 being the
    /// fastest (best) phase. Integer division, so the boundary is a step grid, not a clock.
    /// `nil` when the caller observed no clock: an unmeasured phase must not silently become the
    /// 7 000-point one.
    static func phase(in context: StageBoundaryContext) -> Int? {
        guard let elapsed = context.stageElapsedSteps, GameConstants.phaseTicks > 0 else { return nil }
        return min(GameConstants.timedBonusLadder.count - 1, max(0, elapsed) / GameConstants.phaseTicks)
    }
}

/// One component of an awarded boundary, as it must appear on the wire.
struct StageAwardComponent: Equatable {
    let id: GameplayStageComponent
    let points: Int
}

/// Everything the scene has to apply for one awarded boundary.
struct StageBoundaryAward: Equatable {
    let completedZone: Int
    /// The ordered components. `points` is their sum by construction, which is what predicate B
    /// checks (`bonus.stage_points.points == sum(bonus.stage_component.points)`).
    let components: [StageAwardComponent]
    let livesBefore: Int
    let livesAfter: Int
    /// The original boundary also refills ammunition; a wave-D component does not change that.
    let refillsAmmoAndGrenades: Bool
    let startingAmmo: Int
    let startingGrenades: Int
    /// `ORIGINAL_MECHANICS.md:145` and `:117`: reaching the stage end clears the exoskeleton.
    /// The scene applies it through `Player.setExoskeleton(false, cause: .stageBoundary)`, so the
    /// clear is a witnessed transition and not a silent field write.
    let clearsExoskeleton: Bool
    /// The timed ladder phase this award was computed at (`0` = fastest/best), or `nil` when the
    /// caller supplied no clock observation. Diagnostic identity only: the wire carries the
    /// component's points, and the auditor re-derives the phase from the stage-relative step delta,
    /// so a wrong phase here cannot hide.
    let timedPhase: Int?

    var points: Int { components.reduce(0) { $0 + $1.points } }

    /// Component points by id, for the identity table and for per-component mutation controls.
    func points(of component: GameplayStageComponent) -> Int {
        components.filter { $0.id == component }.reduce(0) { $0 + $1.points }
    }
}

/// The outcome of one boundary trigger. `suppressed` is never silent (brief ruling 7, AC-003).
enum StageBoundaryOutcome: Equatable {
    case awarded(StageBoundaryAward)
    /// A repeat trigger at a stage-end zone. The scene must emit
    /// `bonus.stage_boundary_suppressed`; the probe measured 524 of these against 1 award.
    case suppressed(zone: Int, reason: GameplayStageSuppressionReason)
    /// Not a stage-end zone at all: no state change, therefore no record (INV-003).
    case notApplicable
}

/// P1-8 idempotency ledger (audit 2026-09-20, issue #12; reproduction in
/// `analysis-repo_explorer.md` section 4): zone 124 has an empty `nextLevel`, so the player parks
/// past x=510 and the `contentComplete -> title -> beginFromTitle` FIRE loop re-awarded
/// `lives * 1000` on every cycle - 750 awards in a 600 s run, persisted through `saveCheckpoint`.
///
/// Ruling (architecture.md -> Decisions 3): a playthrough runs from a new game / restart to the
/// next new game or game over, and **each `completed_zone` may award at most once per
/// playthrough**. `enterContentComplete` and the title return that follows it do *not* arm a new
/// playthrough, because the score, lives and player position all carry across it - that is exactly
/// the loop that made the farm possible.
///
/// The ledger is Foundation-only, so the award logic itself runs in the Linux gate as a real
/// product type.
final class StageBoundaryLedger {
    /// Zones that end a stage: the 25th screen of each of the five stages (0-based zone numbers).
    let stageEndZones: [Int]
    /// The ordered award sequence evaluated for each boundary.
    let awardSequence: [GameplayStageComponent]
    /// Once-key allowance. The fixed behavior is 1 per component per zone per playthrough.
    /// `0` reproduces the audited defect for the AC-003 reverted control and is never passed by
    /// product code - `p1_8_fixed_passes_and_revert_fails` greps for that.
    let awardsPerComponentPerZone: Int

    private(set) var playthroughIndex = 1
    private var awardedCounts: [String: Int] = [:]

    /// Wave D (`ORIGINAL_MECHANICS.md:142` as an activation latch): armed by any changing-room
    /// activation inside the current stage and **never cleared by switching the suit back off**,
    /// which is exactly what makes the `:142` and `:118` readings distinguishable. Cleared when a
    /// new stage begins and when a playthrough is armed or closed.
    private(set) var tookExoskeletonInStage = false
    /// The fixed-step coordinate at which the current stage began. Relative deltas against it are
    /// what the timed ladder consumes, because the log's `ts_us` is derived from the step counter.
    private(set) var stageStartStep = 0
    /// The step of the first suit activation inside the current stage, when there was one. Kept so
    /// the latch can be shown to be an *event*, not a polled state (`bravery_latch_distinguishes`).
    private(set) var exoskeletonActivatedAtStep: Int?

    /// Wave A's single-clause sequence stays the constructed default, so wave A's certified
    /// harness and auditor replay unchanged; the product seam names `waveD` explicitly.
    init(stageEndZones: [Int] = [24, 49, 74, 99, 124],
         awardSequence: [GameplayStageComponent] = GameplayStageComponentSequence.waveA,
         awardsPerComponentPerZone: Int = 1) {
        self.stageEndZones = stageEndZones
        self.awardSequence = awardSequence
        self.awardsPerComponentPerZone = max(0, awardsPerComponentPerZone)
    }

    /// Arms a fresh playthrough: a new game, `restartFromBeginning`, or the first step of a
    /// checkpoint-free title start.
    func beginPlaythrough() {
        awardedCounts.removeAll(keepingCapacity: true)
        tookExoskeletonInStage = false
        playthroughIndex += 1
    }

    /// Closes the current playthrough. The next `beginPlaythrough` clears the once-keys, so a
    /// game over followed by a new game can award the same zones again.
    func endPlaythrough() {
        awardedCounts.removeAll(keepingCapacity: true)
        tookExoskeletonInStage = false
    }

    /// The single activation edge the scene reports (a changing room that put the suit ON).
    /// Calling this from that site - never by polling `hasExoskeleton` - is what makes the
    /// ON-then-OFF-before-boundary case forfeit bravery, per `analysis-architect.md` section 5.
    func noteExoskeletonActivated(atStep step: Int) {
        if exoskeletonActivatedAtStep == nil {
            exoskeletonActivatedAtStep = max(0, step)
        }
        tookExoskeletonInStage = true
    }

    /// A new stage began (entry to zone 000/025/050/075/100, title start or restart): the bravery
    /// latch and the timed reference both start over here.
    func noteStageStarted(atStep step: Int) {
        stageStartStep = max(0, step)
        tookExoskeletonInStage = false
        exoskeletonActivatedAtStep = nil
    }

    /// Steps elapsed inside the current stage, never negative.
    func stageElapsedSteps(atStep step: Int) -> Int {
        max(0, step - stageStartStep)
    }

    /// The context a boundary trigger is evaluated under.
    func context(atStep step: Int) -> StageBoundaryContext {
        StageBoundaryContext(stageElapsedSteps: stageElapsedSteps(atStep: step),
                             tookExoskeletonInStage: tookExoskeletonInStage)
    }

    /// Wave A's shape, kept for existing callers and for the Linux harness that compiled it
    /// before wave D: the lives-only sequence, capped by the starting-lives value.
    func outcome(zone: Int, lives: Int, startingLives: Int, startingAmmo: Int, startingGrenades: Int) -> StageBoundaryOutcome {
        outcome(zone: zone, lives: lives, maxLives: startingLives, startingAmmo: startingAmmo,
                startingGrenades: startingGrenades, context: .waveA)
    }

    /// Evaluates one boundary trigger for `zone` under the lives the player holds at that moment.
    /// Pure: the scene applies the returned award and emits the witness records; nothing in here
    /// reads a clock, the player or the scene.
    ///
    /// `awardSequence` defaults to the ledger's own (wave A's single clause). Product code names
    /// `GameplayStageComponentSequence.waveD` at the seam, so the full norm is visible where the
    /// boundary is decided and the ledger keeps no hidden mutable mode - and wave A's merged
    /// auditor, whose component rules only know `lives_x1000`, keeps replaying exactly the stream
    /// it was certified on.
    func outcome(zone: Int, lives: Int, maxLives: Int, startingAmmo: Int, startingGrenades: Int,
                 context: StageBoundaryContext,
                 awardSequence: [GameplayStageComponent]? = nil) -> StageBoundaryOutcome {
        guard stageEndZones.contains(zone) else { return .notApplicable }

        var accepted: [StageAwardComponent] = []
        for component in awardSequence ?? self.awardSequence {
            let key = onceKey(zone: zone, component: component)
            let already = awardedCounts[key] ?? 0
            if awardsPerComponentPerZone > 0, already >= awardsPerComponentPerZone {
                return .suppressed(zone: zone, reason: .alreadyAwarded)
            }
            accepted.append(StageAwardComponent(
                id: component,
                points: GameplayStageComponentSequence.points(for: component, lives: lives,
                                                              context: context)))
        }
        for component in accepted {
            let key = onceKey(zone: zone, component: component.id)
            awardedCounts[key, default: 0] += 1
        }
        guard !accepted.isEmpty else { return .suppressed(zone: zone, reason: .notStageEnd) }

        return .awarded(StageBoundaryAward(completedZone: zone,
                                           components: accepted,
                                           livesBefore: lives,
                                           livesAfter: min(maxLives, lives + 1),
                                           refillsAmmoAndGrenades: true,
                                           startingAmmo: startingAmmo,
                                           startingGrenades: startingGrenades,
                                           clearsExoskeleton: true,
                                           timedPhase: GameplayStageComponentSequence.phase(in: context)))
    }

    /// Test/telemetry view of the ledger state; the harness asserts on it directly.
    var awardedZonesInPlaythrough: [Int] {
        Set(awardedCounts.keys.compactMap { Int($0.split(separator: ":").first ?? "") }).sorted()
    }

    private func onceKey(zone: Int, component: GameplayStageComponent) -> String {
        "\(zone):\(component.rawValue)"
    }
}
