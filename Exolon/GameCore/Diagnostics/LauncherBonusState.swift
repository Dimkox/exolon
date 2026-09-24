import Foundation

/// P1-6 (audit 2026-09-20, issue #10; `analysis-repo_explorer.md` section 3):
/// `DoubleLauncherObstacle.collectBonusIfTouched` was the only writer of `isActive` besides init,
/// and `isActive` is the fire gate - so collecting the invisible-region bonus paid 1000 points once
/// and permanently silenced that launcher for the rest of the zone instance, with no restore path
/// (only a rebuilt `TMXLevelRuntime` ever brought it back).
///
/// Ruling (architecture.md -> Decisions 2): the **bonus payout** and the **fire gate** are two
/// different facts.
/// * `bonusCollected` - pays 1000 exactly once per launcher per zone instantiation;
/// * `isActive` - stays the fire gate, so after the payout the launcher keeps firing under the
///   existing proximity rule (it stops only when Vitorc closes to 110 px or less).
///
/// A pure value type, so the Linux gate compiles and runs the real product semantics and the
/// `bonus.double_launcher{launcher_active_after}` / `entity.launcher_fire` witness pair is produced
/// by the same code the game runs.
///
/// The payout result is returned as `DoubleLauncherPayout` by `TMXLevelRuntime`, which is what lets
/// the witness record name the launcher object and the fire-gate state without a second lookup.
struct LauncherBonusState: Equatable {
    /// Fire gate. `false` only when the launcher is destroyed by level logic, never by the payout.
    private(set) var isActive: Bool
    /// Has this launcher already paid its region bonus in this zone instantiation?
    private(set) var bonusCollected: Bool

    init(isActive: Bool = true, bonusCollected: Bool = false) {
        self.isActive = isActive
        self.bonusCollected = bonusCollected
    }

    /// Whether the launcher may produce a shot right now. The payout does not change it.
    var canFire: Bool { isActive }

    /// Attempts the payout for one fixed step.
    ///
    /// - Parameter touchesBonusRegion: the caller's geometry decision (hitbox overlap); this type
    ///   owns only the once-semantics, so the invisible-region rule stays where it is.
    /// - Returns: `true` exactly once per launcher, on the step that pays.
    mutating func payBonus(touchesBonusRegion: Bool) -> Bool {
        guard isActive, !bonusCollected, touchesBonusRegion else { return false }
        bonusCollected = true
        return true
    }

    /// Destroys the launcher as a firing entity (level logic only; the bonus never calls this).
    mutating func deactivate() {
        isActive = false
    }
}

/// What one zone step paid out, as the record must report it (P1-6).
struct DoubleLauncherPayout: Equatable {
    let points: Int
    let objectID: UInt16
    let launcherActiveAfter: Bool
}
