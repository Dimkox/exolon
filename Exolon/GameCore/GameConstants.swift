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

    // Player horizontal clamp bounds (centre of the 48x64 sprite). Player.update
    // clamps to this range and the bullet culling bound is derived from it, so
    // no shot can disappear while it is still entirely inside the reachable
    // field (P1-3). The screen-transition trigger (x > 510) is separate and
    // unchanged.
    static let playerMinimumCenterX: CGFloat = playerSpriteSize.width * 0.5
    static let playerMaximumCenterX: CGFloat = logicalSize.width + 32

    // Horizontal inset Player.refreshGroundSupport applies to the movement box
    // when it looks for ground support under the feet. The spawn surface query
    // (TMXSurfaceQuery) uses the same inset, so it is named here once.
    static let footSupportHorizontalInset: CGFloat = 3

    static let blasterBulletSize = CGSize(width: 16, height: 2)
    // P1-3/AC-004 (amended): a shot must never be born outside its own cull
    // bound at any reachable player position, and it must survive past the
    // whole reachable field. The reachable firing reach is the player clamp
    // plus the muzzle offset plus one full bullet width; the lower bound
    // mirrors the muzzle reach plus bullet width around the visible field's
    // left edge (x = 0). Both cull bounds are therefore DERIVED; nothing here
    // re-pins the old 528.
    static let blasterMuzzleOffsetX: CGFloat = 34
    static let blasterCullMaximumX: CGFloat =
        playerMaximumCenterX + blasterMuzzleOffsetX + blasterBulletSize.width
    static let blasterCullMinimumX: CGFloat =
        -(blasterMuzzleOffsetX + blasterBulletSize.width)

    static let grenadeSize = CGSize(width: 16, height: 16)
    static let grenadeThrowOffsetX: CGFloat = 4
    // Same x-bound policy as the blaster (no inline literals survive in
    // Grenade.swift): firing reach up to the clamp, mirrored reach on the left.
    static let grenadeCullMaximumX: CGFloat =
        playerMaximumCenterX + grenadeThrowOffsetX + grenadeSize.width
    static let grenadeCullMinimumX: CGFloat =
        -(grenadeThrowOffsetX + grenadeSize.width)

    static let pistonNodeSize = CGSize(width: 48, height: 64)
    // The piston rises from hiddenY = groundY - travel up to exposedY = groundY,
    // so the travel equals the node height. The hitbox is the visible core.
    static let pistonTravel: CGFloat = pistonNodeSize.height
    static let pistonHitXInset: CGFloat = 3
    static let pistonHitWidth: CGFloat = 42

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

    // MARK: Stage-end sequence (`ORIGINAL_MECHANICS.md:138-146`, wave D / audit P1-10)

    /// Hard cap on lives. The stage boundary used to borrow `GameState.startingLives` for this,
    /// which conflated "what a new game starts with" with "what the boundary award may not
    /// exceed"; the two only coincide by accident. The norm says "Add one life, capped at 9".
    static let maxLives = 9

    /// The bravery award for completing a stage without having taken the exoskeleton (`:142`).
    static let braveryBonus = 10_000

    /// Fixed steps per timed-bonus phase. **OWNER-APPROVED DEVIATION - NOT CANONICAL.**
    /// `ORIGINAL_MECHANICS.md:143` describes a bonus *cursor* whose *selected phase* picks one of
    /// `0/1000/3000/5000/7000`: an interactive minigame this remake does not implement and that no
    /// source in or outside the tree dates (docs_researcher §1.3 ruled it SILENT on cadence, slot
    /// order, input and units). The norm names the five values and no cadence; the only timing hint
    /// in the document (`:131-136`, the 700-loop pursuer at "roughly 20-30 seconds") belongs to a
    /// different mechanic and was deliberately not reused as a derivation. The owner chose a
    /// deterministic tick ladder over deferring the clause (change 20260924-...-8341b7, gate
    /// ruling 2), giving `phase = min(4, elapsed / phaseTicks)` at one phase per 30 s of
    /// simulation on the canonical 60 Hz step. UNCONFIRMED vs original: a future interactive cursor
    /// re-targets this constant's meaning and must not have to move the code. What the norm fixes -
    /// and what `stage_boundary_check.py` asserts - is the *shape* below: five phases, exactly
    /// these values, monotonically non-increasing in elapsed steps, saturating at the last phase.
    static let phaseTicks = 1_800

    /// Timed bonus per phase, best first (the five canonical values of `:143`). Index with
    /// `GameplayStageComponentSequence.phase(in:)`.
    static let timedBonusLadder = [7_000, 5_000, 3_000, 1_000, 0]
}
