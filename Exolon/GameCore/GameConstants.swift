import CoreGraphics
import Foundation

enum GameConstants {
    static let logicalSize = CGSize(width: 512, height: 384)
    static let fixedTimeStep: TimeInterval = 1.0 / 60.0
    static let maximumFrameTime: TimeInterval = 0.25
    // Original dead_sprite_delay2 retains 20 protection ticks after the 46-tick death animation.
    // The remake's canonical simulation rate is 60 Hz (`fixedTimeStep` above), so the window is
    // expressed in seconds against that clock: 0.4 s = 24 fixed steps. The 50 Hz figure that used
    // to be quoted here was the ZX Spectrum's own frame rate, not this loop's - audit TC-05 was
    // closed by ruling (change 20260924 wave A, decision 5).
    static let postDeathProtectionDuration: TimeInterval = 0.4

    static let defaultGroundY: CGFloat = 96
    static let defaultSpawnCenter = CGPoint(x: 88, y: 128)

    static let playerSpriteSize = CGSize(width: 48, height: 64)

    // Exact Vitorc collision rectangles from the reference remake:
    // stand updateColRect(1, 46, 1, 63)
    // duck  updateColRect(1, 46, 12, 52)
    // In our bottom-left coordinate system both rectangles sit on the feet.
    static let playerStandingMovementSize = CGSize(width: 46, height: 63)
    static let playerCrouchingMovementSize = CGSize(width: 46, height: 52)
    static let playerStandingDamageSize = CGSize(width: 46, height: 63)

    // Damage is intentionally lower than the 46x52 movement collider while
    // ducking. The turret bullet travels with its lower edge at ground+50; a
    // 52 px damage box overlaps that trajectory by two pixels and makes ducking
    // useless. Keeping the vulnerable crouch body at 49 px preserves solid
    // collision with the full duck sprite while allowing the turret shot to
    // pass safely above Vitorc, matching the original gameplay behaviour.
    static let playerCrouchingDamageSize = CGSize(width: 46, height: 49)

    static let hudHeight: CGFloat = 48

    /// Original screen-exit trigger: crossing this x leaves the zone (`GameScene.checkScreenExit`).
    /// Named because the event contract reports it as `state.zone_exit.trigger_x`.
    static let screenExitX: CGFloat = 510

    /// Original death animation settle: 70 fixed steps on the ground before a life is paid.
    /// Named because `player.death_settled.delay_us` must not be restated at the call site, where a
    /// silent change would make the record lie.
    static let deathSettleDelay: TimeInterval = 70.0 / 60.0
}
