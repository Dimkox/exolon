import Foundation

/// A stage-boundary award component. Wave A implements exactly one: the original
/// `lives * 1000` bonus. The sequence is a list so a later wave can append the bravery award and
/// the timed-travel ladder as further components **without touching the `GameScene` seam, the
/// witness events or the once-key logic** (controller amendment, 2026-09-24).
///
/// Append-only: a new component needs a new `GameplayStageComponent` code, a case here and a
/// branch in `points(for:lives:)`; nothing else.
enum GameplayStageComponentSequence {
    /// The ordered award sequence for one completed stage boundary.
    static let waveA: [GameplayStageComponent] = [.livesTimes1000]

    /// Points this component contributes given the state at the boundary. Exhaustive on purpose:
    /// a new component cannot silently contribute zero.
    static func points(for component: GameplayStageComponent, lives: Int) -> Int {
        switch component {
        case .livesTimes1000:
            return lives * 1_000
        }
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

    var points: Int { components.reduce(0) { $0 + $1.points } }
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
        playthroughIndex += 1
    }

    /// Closes the current playthrough. The next `beginPlaythrough` clears the once-keys, so a
    /// game over followed by a new game can award the same zones again.
    func endPlaythrough() {
        awardedCounts.removeAll(keepingCapacity: true)
    }

    /// Evaluates one boundary trigger for `zone` under the lives the player holds at that moment.
    /// Pure: the scene applies the returned award and emits the witness records.
    func outcome(zone: Int, lives: Int, startingLives: Int, startingAmmo: Int, startingGrenades: Int) -> StageBoundaryOutcome {
        guard stageEndZones.contains(zone) else { return .notApplicable }

        var accepted: [StageAwardComponent] = []
        for component in awardSequence {
            let key = onceKey(zone: zone, component: component)
            let already = awardedCounts[key] ?? 0
            if awardsPerComponentPerZone > 0, already >= awardsPerComponentPerZone {
                return .suppressed(zone: zone, reason: .alreadyAwarded)
            }
            accepted.append(StageAwardComponent(id: component,
                                                points: GameplayStageComponentSequence.points(for: component, lives: lives)))
        }
        for component in accepted {
            let key = onceKey(zone: zone, component: component.id)
            awardedCounts[key, default: 0] += 1
        }
        guard !accepted.isEmpty else { return .suppressed(zone: zone, reason: .notStageEnd) }

        return .awarded(StageBoundaryAward(completedZone: zone,
                                           components: accepted,
                                           livesBefore: lives,
                                           livesAfter: min(startingLives, lives + 1),
                                           refillsAmmoAndGrenades: true,
                                           startingAmmo: startingAmmo,
                                           startingGrenades: startingGrenades))
    }

    /// Test/telemetry view of the ledger state; the harness asserts on it directly.
    var awardedZonesInPlaythrough: [Int] {
        Set(awardedCounts.keys.compactMap { Int($0.split(separator: ":").first ?? "") }).sorted()
    }

    private func onceKey(zone: Int, component: GameplayStageComponent) -> String {
        "\(zone):\(component.rawValue)"
    }
}
