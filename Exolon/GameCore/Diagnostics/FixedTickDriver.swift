import Foundation

/// The fixed-step accumulator loop, extracted from `GameScene.update` (`GameScene.swift:123-146`)
/// so the P1-9 defect and its regression test are executable on Linux as real product code
/// (architecture.md -> "Testability": a GameScene-logic replica in the harness is never an
/// assertion source).
///
/// P1-9 (audit 2026-09-20, issue #13): `transition(to:)` swapped the level but left the
/// accumulator charged, so up to `floor(maximumFrameTime / fixedTimeStep) = 15` catch-up steps ran
/// **in the new zone inside the render frame that transitioned**. The probe measured 14 of 15
/// steps after the transition; this type discards the remainder instead (`tick.accumulator_reset`).
///
/// The tick and frame counters are **never** reset here or anywhere else in this type: they are
/// process-global (INV-003). Only the accumulator is discardable.
final class FixedTickDriver {
    let fixedTimeStep: TimeInterval
    let maximumFrameTime: TimeInterval
    /// `floor(0.25 / (1/60)) = 15`: the most steps one rendered frame may simulate (SIG-003).
    let stepBudget: Int
    /// Characterization switch for the AC-002 reverted control, see `init`.
    let resetAccumulatorOnZoneTransition: Bool

    /// Mutable only so the composition root can bind the sink after the scene exists (see
    /// `useSink`); the render thread is the sole accessor.
    private var events: GameplayEventSink?

    private(set) var accumulator: TimeInterval = 0
    private(set) var previousUpdateTime: TimeInterval = 0
    private(set) var stepsThisFrame = 0
    private(set) var hasReferenceTime = false

    /// The driver never mutates gameplay; it only decides when a step runs and what the log says
    /// about it. `events` may be nil (no emission, identical stepping), bound at init or later.
    ///
    /// - Parameter resetAccumulatorOnZoneTransition: the **fixed** behavior is `true`, which is
    ///   what every product call site uses. `false` reproduces the audited defect so the Linux
    ///   gate can prove predicate A actually flips; passing `false` from product code would
    ///   re-introduce P1-9 and is what `p1_9_fixed_passes_and_revert_fails` greps for.
    init(events: GameplayEventSink? = nil,
         fixedTimeStep: TimeInterval = GameConstants.fixedTimeStep,
         maximumFrameTime: TimeInterval = GameConstants.maximumFrameTime,
         resetAccumulatorOnZoneTransition: Bool = true) {
        self.events = events
        self.fixedTimeStep = fixedTimeStep
        self.maximumFrameTime = maximumFrameTime
        self.resetAccumulatorOnZoneTransition = resetAccumulatorOnZoneTransition
        self.stepBudget = max(1, Int(maximumFrameTime / fixedTimeStep))
    }

    /// Binds (or rebinds) the sink. `GameScene.events` is injected by the composition root after
    /// `init`, so a driver that snapshotted the sink at property-initialization time could keep
    /// stepping into a null sink while every other record logged - which is what made `tick` stick
    /// at 0 in a non-empty file. Called from the render thread only.
    func useSink(_ sink: GameplayEventSink?) {
        events = sink
    }

    /// Microseconds still charged in the accumulator, for `state.zone_transition`.
    var accumulatorMicroseconds: Int {
        Int(max(0, accumulator * 1_000_000).rounded())
    }

    /// How many steps the charged accumulator would still buy this frame.
    var pendingSteps: Int {
        guard accumulator >= fixedTimeStep else { return 0 }
        return min(stepBudget, Int(accumulator / fixedTimeStep))
    }

    /// Opens a rendered frame. Returns `false` for the very first `update(_:)` call - the one that
    /// only records the reference time, which is why `frame` 0 carries no simulated step.
    @discardableResult
    func beginFrame(currentTime: TimeInterval) -> Bool {
        // The previous frame's step count is final now, so that is when its catch-up record goes
        // out - before this frame's counters are cleared.
        reportSlowFrame()
        guard hasReferenceTime, currentTime.isFinite else {
            if !currentTime.isFinite { return false }
            previousUpdateTime = currentTime
            hasReferenceTime = true
            stepsThisFrame = 0
            return false
        }
        let rawDelta = currentTime - previousUpdateTime
        previousUpdateTime = currentTime
        stepsThisFrame = 0
        if rawDelta < 0 || !rawDelta.isFinite { return false }

        let clamped = min(rawDelta, maximumFrameTime)
        if rawDelta > maximumFrameTime {
            emitFrameGapClamped(rawDelta: rawDelta)
        }
        accumulator += clamped
        return true
    }

    /// Consumes one fixed step if the accumulator can pay for it. When it returns `true` the tick
    /// counter has advanced (the first executed step is tick 1) and the caller must run exactly one
    /// fixed update with `fixedTimeStep`.
    func beginStep(zone: Int) -> Bool {
        guard accumulator >= fixedTimeStep, stepsThisFrame < stepBudget else { return false }
        accumulator -= fixedTimeStep
        stepsThisFrame += 1
        events?.beginTick(zone: zone)
        return true
    }

    /// Discards the charged remainder, which is what keeps a step from running in the new zone
    /// inside the frame that transitioned (decision 4 in architecture.md).
    ///
    /// `previousUpdateTime` is deliberately untouched: zeroing it would make the next frame see the
    /// whole paused interval as its delta and immediately run a clamped 15-step burst in the new
    /// zone. Neither `tick` nor `frame` is affected.
    func reset(reason: GameplayAccumulatorResetReason) {
        guard resetAccumulatorOnZoneTransition else { return }
        let discarded = accumulator
        let discardedSteps = Int(discarded / fixedTimeStep)
        accumulator = 0
        stepsThisFrame = 0
        emitAccumulatorReset(reason: reason, discarded: discarded, discardedSteps: discardedSteps)
    }

    // MARK: Emission (integer lanes only)

    /// Emission goes through the shared producer helpers, so a lane map stays one fact instead of
    /// being re-derived at every call site (that re-derivation is what shipped four wire lies).
    private func emitFrameGapClamped(rawDelta: TimeInterval) {
        events?.emitFrameGapClamped(rawMicroseconds: Int((rawDelta * 1_000_000).rounded()))
    }

    private func emitAccumulatorReset(reason: GameplayAccumulatorResetReason, discarded: TimeInterval, discardedSteps: Int) {
        events?.emitAccumulatorReset(reason: reason,
                                     discardedMicroseconds: Int((discarded * 1_000_000).rounded()),
                                     discardedSteps: discardedSteps)
    }

    /// `tick.slow_step` describes a frame that had to catch up. Reported at the start of the next
    /// frame, when this frame's step count is final.
    private func reportSlowFrame() {
        guard stepsThisFrame > 1, let events = events else { return }
        events.emitSlowStep(stepMicroseconds: Int((Double(stepsThisFrame) * fixedTimeStep * 1_000_000).rounded()),
                            stepsThisFrame: stepsThisFrame)
    }
}
