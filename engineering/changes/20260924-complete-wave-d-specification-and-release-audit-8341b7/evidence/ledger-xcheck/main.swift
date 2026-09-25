// Wave D cross-check: execute the REAL StageBoundaryLedger (Foundation-only, same file the
// product builds) and print the waveD table, so stage_boundary_check.py's modelled numbers can
// be diffed against executed ones instead of being trusted.
import Foundation

var out = ""; let start = FileHandle.standardOutput
func emit(_ s: String) { out += s + "\n" }

// One boundary in a fresh playthrough per row: a new ledger each time, exactly the situation
// stage_boundary_check.py models. Reusing one ledger would answer "already awarded" for every
// row after the first and compare nothing.
let livesCases = [0, 1, 4, 8, 9]
let elapsedCases = [0, 1, 1799, 1800, 3599, 3600, 5400, 7199, 7200, 108000]
for lives in livesCases {
  for elapsed in elapsedCases {
    for took in [false, true] {
      let ctx = StageBoundaryContext(stageElapsedSteps: elapsed, tookExoskeletonInStage: took)
      let ledger = StageBoundaryLedger(awardSequence: GameplayStageComponentSequence.waveD)
      ledger.noteStageStarted(atStep: 0)
      switch ledger.outcome(zone: 24, lives: lives, maxLives: GameConstants.maxLives,
                             startingAmmo: GameState.startingAmmo,
                             startingGrenades: GameState.startingGrenades,
                             context: ctx, awardSequence: GameplayStageComponentSequence.waveD) {
      case .notApplicable: emit("row \(lives) \(elapsed) \(took) NOT_APPLICABLE")
      case .suppressed(_, let reason): emit("row \(lives) \(elapsed) \(took) SUPPRESSED \(reason.label)")
      case .awarded(let a):
        let b = a.points(of: .braveryNoExoskeleton)
        let t = a.points(of: .timedPhaseLadder)
        let l = a.points(of: .livesTimes1000)
        emit("row \(lives) \(elapsed) \(took) AWARDED total=\(a.points) lives=\(l) bravery=\(b) timed=\(t) phase=\(a.timedPhase ?? -1) livesAfter=\(a.livesAfter) sum=\(a.components.reduce(0){$0+$1.points}) clear=\(a.clearsExoskeleton)")
      }
    }
  }
}
// once-key and latch behaviour, executed
let probe = StageBoundaryLedger(awardSequence: GameplayStageComponentSequence.waveD)
probe.noteStageStarted(atStep: 0)
let first = probe.outcome(zone: 49, lives: 3, maxLives: GameConstants.maxLives, startingAmmo: 99,
                           startingGrenades: 10,
                           context: StageBoundaryContext(stageElapsedSteps: 2000, tookExoskeletonInStage: false))
let second = probe.outcome(zone: 49, lives: 3, maxLives: GameConstants.maxLives, startingAmmo: 99,
                           startingGrenades: 10,
                           context: StageBoundaryContext(stageElapsedSteps: 2000, tookExoskeletonInStage: false))
emit("once first=\(first.isAwardText) second=\(second.isAwardText)")
probe.noteExoskeletonActivated(atStep: 10)
probe.toggleNothing()
emit("latch after activation=\(probe.tookExoskeletonInStage) activatedAt=\(probe.exoskeletonActivatedAtStep ?? -1)")
let paid = probe.outcome(zone: 74, lives: 9, maxLives: GameConstants.maxLives, startingAmmo: 99,
                         startingGrenades: 10,
                         context: probe.context(atStep: 100))
switch paid {
case .awarded(let a): emit("latch forfeits bravery: bravery=\(a.points(of: .braveryNoExoskeleton)) total=\(a.points)")
default: emit("latch case did not award")
}
probe.noteStageStarted(atStep: 200)
emit("latch after new stage=\(probe.tookExoskeletonInStage)")
let clean = probe.outcome(zone: 99, lives: 9, maxLives: GameConstants.maxLives, startingAmmo: 99,
                          startingGrenades: 10, context: probe.context(atStep: 210))
switch clean {
case .awarded(let a): emit("clean stage pays bravery=\(a.points(of: .braveryNoExoskeleton)) timed=\(a.points(of: .timedPhaseLadder)) total=\(a.points)")
default: emit("clean case did not award")
}
let atCap = probe.outcome(zone: 124, lives: 9, maxLives: GameConstants.maxLives, startingAmmo: 99,
                          startingGrenades: 10,
                          context: StageBoundaryContext(stageElapsedSteps: 100000, tookExoskeletonInStage: true))
switch atCap {
case .awarded(let a): emit("at cap livesAfter=\(a.livesAfter) bravery=\(a.points(of: .braveryNoExoskeleton)) timed=\(a.points(of: .timedPhaseLadder))")
default: emit("cap case did not award")
}
let unobserved = StageBoundaryLedger().outcome(zone: 24, lives: 4, startingLives: 9,
                                              startingAmmo: 99, startingGrenades: 10)
switch unobserved {
case .awarded(let a): emit("waveA shim total=\(a.points) components=\(a.components.count) timed=\(a.points(of: .timedPhaseLadder))")
default: emit("waveA shim did not award")
}
_ = start
FileHandle.standardOutput.write(out.data(using: .utf8)!)

extension StageBoundaryOutcome {
    var isAwardText: String {
        switch self {
        case .awarded: return "awarded"
        case .suppressed(_, let r): return "suppressed:\(r.label)"
        case .notApplicable: return "notApplicable"
        }
    }
}
extension StageBoundaryLedger {
    func toggleNothing() {}
}
