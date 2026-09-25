import CoreGraphics
import Foundation

enum PlayerFacing {
    case left
    case right
}

enum PlayerMotionState {
    case idle
    case running
    case jumping
    case falling
    case crouching
    case dying
}

final class Player {
    // Position is the visual centre of the 48x64 Vitorc sprite.
    private(set) var position = GameConstants.defaultSpawnCenter
    private(set) var velocity = CGVector.zero
    private(set) var isGrounded = true
    private(set) var facing: PlayerFacing = .right
    private(set) var motionState: PlayerMotionState = .idle
    private(set) var isDying = false
    private(set) var hasExoskeleton = false

    /// Gameplay event sink. `nil` (the default) means no emission and no behavior change, which is
    /// what keeps every existing construction site, including `didMove(to:)` ordering, intact.
    var events: (any GameplayEventSink)?

    /// Exposed for the `player.teleport{jump_latch_held}` witness: the latch is still held by a
    /// contextual consume, so a physically held UP cannot start a jump yet.
    var jumpLatchHeld: Bool { jumpWasPressed || contextHoldsJumpLatch }

    private let moveSpeed: CGFloat = 90
    private let jumpVelocity: CGFloat = 165
    private let deathJumpVelocity: CGFloat = 165
    private let gravity: CGFloat = -360
    private let maximumFallSpeed: CGFloat = -300

    private var jumpWasPressed = false
    /// P1-4 (audit 2026-09-20, issue #8): a contextual UP consume (teleport, changing room) or a
    /// teleport must keep the jump edge latch held until the physical key is released. Without it,
    /// `update` re-sampled `jumpWasPressed = input.jump` in the same step, so a held UP turned into
    /// a jump on the **next** tick - one fixed tick after the consume, in the old scene or the new
    /// one. Cleared by any step that observes `input.jump == false`.
    private var contextHoldsJumpLatch = false
    private var spawnCenter = GameConstants.defaultSpawnCenter
    private var fallbackGroundY = GameConstants.defaultGroundY

    init() {}

    func configure(spawnCenter: CGPoint, groundY: CGFloat) {
        self.spawnCenter = spawnCenter
        self.fallbackGroundY = groundY
        respawn()
    }

    private var spriteBottomY: CGFloat {
        position.y - GameConstants.playerSpriteSize.height * 0.5
    }

    var movementHitbox: CGRect {
        let crouched = motionState == .crouching && isGrounded
        let size = crouched
            ? GameConstants.playerCrouchingMovementSize
            : GameConstants.playerStandingMovementSize
        return CGRect(
            x: position.x - size.width * 0.5,
            y: spriteBottomY,
            width: size.width,
            height: size.height
        )
    }

    var damageHitbox: CGRect {
        // Movement and damage boxes are intentionally separate while ducking.
        // The 46x52 movement collider follows the reference remake; the 46x49
        // vulnerable body keeps the turret shot just above Vitorc, matching the
        // gameplay test fixed in Step 7.2.
        let crouched = motionState == .crouching && isGrounded
        let size = crouched
            ? GameConstants.playerCrouchingDamageSize
            : GameConstants.playerStandingDamageSize
        return CGRect(
            x: position.x - size.width * 0.5,
            y: spriteBottomY,
            width: size.width,
            height: size.height
        )
    }

    func update(input: InputSnapshot, dt: TimeInterval) {
        let step = CGFloat(dt)

        if isDying {
            velocity.dx = 0
            if !isGrounded {
                velocity.dy = max(velocity.dy + gravity * step, maximumFallSpeed)
                position.y += velocity.dy * step
            }
            landOnFallbackFloorIfNeeded()
            motionState = .dying
            return
        }

        let wantsLeft = input.moveLeft && !input.moveRight
        let wantsRight = input.moveRight && !input.moveLeft
        let isCrouching = input.crouch && isGrounded

        if isCrouching {
            velocity.dx = 0
        } else if wantsLeft {
            velocity.dx = -moveSpeed
            facing = .left
        } else if wantsRight {
            velocity.dx = moveSpeed
            facing = .right
        } else {
            velocity.dx = 0
        }

        let jumpJustPressed = input.jump && !jumpWasPressed
        let jumpedThroughContextHold = jumpJustPressed && contextHoldsJumpLatch
        if jumpJustPressed && isGrounded && !isCrouching {
            velocity.dy = jumpVelocity
            isGrounded = false
            emitJump(groundedBefore: true, afterContextConsume: jumpedThroughContextHold)
        }
        if contextHoldsJumpLatch, input.jump {
            // Physically still held after a contextual consume: the edge stays suppressed (P1-4).
            jumpWasPressed = true
        } else {
            // Either never suppressed, or the key is now released - which is the only edge that
            // re-arms a jump (architecture.md -> Decisions 1).
            jumpWasPressed = input.jump
            contextHoldsJumpLatch = false
        }

        if !isGrounded {
            velocity.dy = max(velocity.dy + gravity * step, maximumFallSpeed)
        }

        position.x += velocity.dx * step
        position.y += velocity.dy * step

        // Original screen transition happens around x=510.
        // Clamp by the visible 48 px sprite, not by the narrower collider.
        // Otherwise the x=0 TMX spawn can walk a few pixels off the left edge.
        // The named clamp bounds are what the P1-3 bullet culling bound
        // derives from, so the two can never drift apart.
        position.x = min(max(position.x, GameConstants.playerMinimumCenterX), GameConstants.playerMaximumCenterX)

        landOnFallbackFloorIfNeeded()
        updateMotionState(isCrouching: input.crouch && isGrounded)
    }

    // Step 7: full axis-aware collision resolution.  This lets the TMX
    // collision layer support elevated platforms, ceilings and walls instead
    // of treating every solid only as a horizontal blocker.
    func resolveSolidCollision(previousPosition: CGPoint, solid: CGRect) {
        guard movementHitbox.intersects(solid) else { return }

        let currentBox = movementHitbox
        let previousBox = movementHitbox(at: previousPosition)

        // Falling onto the top of a platform.
        if velocity.dy <= 0,
           previousBox.minY >= solid.maxY - 1.0,
           currentBox.minY < solid.maxY {
            let wasAirborne = !isGrounded
            let fallSpeed = velocity.dy
            position.y = solid.maxY + GameConstants.playerSpriteSize.height * 0.5
            velocity.dy = 0
            isGrounded = true
            if wasAirborne { emitLand(support: .solid, vyBefore: fallSpeed) }
            return
        }

        // Hitting the underside of a platform/ceiling.
        if velocity.dy > 0,
           previousBox.maxY <= solid.minY + 1.0,
           currentBox.maxY > solid.minY {
            let standingHeight = GameConstants.playerStandingMovementSize.height
            let topOffset = standingHeight - GameConstants.playerSpriteSize.height * 0.5
            position.y = solid.minY - topOffset
            velocity.dy = 0
            isGrounded = false
            return
        }

        // Side collision.
        let halfWidth = currentBox.width * 0.5
        if previousBox.maxX <= solid.minX + 1.0 && currentBox.maxX > solid.minX {
            position.x = solid.minX - halfWidth
            velocity.dx = 0
        } else if previousBox.minX >= solid.maxX - 1.0 && currentBox.minX < solid.maxX {
            position.x = solid.maxX + halfWidth
            velocity.dx = 0
        } else if !isDying {
            // Safe fallback for deep overlaps after a large frame gap.
            position.x = previousPosition.x
            velocity.dx = 0
        }
    }

    // Call after all collision resolution. If Vitorc has walked off an
    // elevated platform, gravity must start on the next fixed step.
    func refreshGroundSupport(solids: [CGRect]) {
        guard isGrounded else { return }

        let box = movementHitbox
        let footY = box.minY
        let horizontalInset = GameConstants.footSupportHorizontalInset
        let left = box.minX + horizontalInset
        let right = box.maxX - horizontalInset

        let supported = solids.contains { solid in
            abs(solid.maxY - footY) <= 1.5 &&
            right > solid.minX && left < solid.maxX
        }

        // The fallback floor remains a safety net for maps with incomplete
        // collision data. Elevated platforms, however, require a solid below.
        if !supported && footY > fallbackGroundY + 1.5 {
            isGrounded = false
        }
    }

    func finalizeMotionState(input: InputSnapshot) {
        updateMotionState(isCrouching: input.crouch && isGrounded)
    }

    func teleport(to center: CGPoint) {
        guard !isDying else { return }
        position = center
        velocity = .zero
        isGrounded = true
        motionState = .idle
        jumpWasPressed = true
        contextHoldsJumpLatch = true
    }

    // Original remake behaviour: death changes to frame 10 and force-jumps
    // Vitorc. Input is ignored until he lands and the scene's death delay ends.
    func beginDeath() {
        guard !isDying else { return }
        isDying = true
        motionState = .dying
        velocity = CGVector(dx: 0, dy: deathJumpVelocity)
        isGrounded = false
        jumpWasPressed = false
        contextHoldsJumpLatch = false
    }

    func finishDeathAndRespawn() {
        isDying = false
        respawn()
    }

    func respawn() {
        isDying = false
        position = spawnCenter
        velocity = .zero
        isGrounded = true
        facing = .right
        motionState = .idle
        jumpWasPressed = false
        contextHoldsJumpLatch = false
    }


    func toggleExoskeleton(cause: GameplayExoskeletonCause = .changingRoom) {
        guard !isDying else { return }
        hasExoskeleton.toggle()
        events?.emitExoskeleton(enabled: hasExoskeleton, cause: cause)
    }

    func setExoskeleton(_ enabled: Bool, cause: GameplayExoskeletonCause = .reset) {
        guard hasExoskeleton != enabled else { return }
        hasExoskeleton = enabled
        events?.emitExoskeleton(enabled: enabled, cause: cause)
    }

    /// UP is also the contextual action key for teleports and changing rooms.
    /// When the scene consumes that press, keep Player's edge latch held until
    /// the physical key/button is released so the next fixed step cannot turn
    /// the same press into an accidental jump.
    func consumeContextualJumpPress() {
        jumpWasPressed = true
        contextHoldsJumpLatch = true
    }

    func blasterOrigin() -> CGPoint {
        // Reference VitorcEntity: BLASTER_BULLET_OFFSET_X=2,
        // BLASTER_BULLET_OFFSET_Y=30, DUCK_OFFSET=10. Converted from the
        // original top-left entity coordinates to our centre-based SpriteKit
        // coordinates, including the 16x2 bullet size. The named muzzle offset
        // is the same constant the P1-3 cull bounds are derived from, so a
        // shot can never be born outside its own cull bound (AC-004).
        let xOffset: CGFloat = facing == .right
            ? GameConstants.blasterMuzzleOffsetX : -GameConstants.blasterMuzzleOffsetX
        let yOffset: CGFloat = motionState == .crouching ? -9 : 1
        return CGPoint(x: position.x + xOffset, y: position.y + yOffset)
    }

    func grenadeOrigin() -> CGPoint {
        // Reference offsets: GRENADE_OFFSET_X=20, GRENADE_OFFSET_Y=12,
        // DUCK_OFFSET=10. The grenade sheet is 16x16. The named throw offset
        // feeds the shared cull-bound derivation like the blaster muzzle.
        let xOffset: CGFloat = facing == .right
            ? GameConstants.grenadeThrowOffsetX : -GameConstants.grenadeThrowOffsetX
        let yOffset: CGFloat = motionState == .crouching ? 2 : 12
        return CGPoint(x: position.x + xOffset, y: position.y + yOffset)
    }

    private func movementHitbox(at centre: CGPoint) -> CGRect {
        let crouched = motionState == .crouching && isGrounded
        let size = crouched
            ? GameConstants.playerCrouchingMovementSize
            : GameConstants.playerStandingMovementSize
        return CGRect(
            x: centre.x - size.width * 0.5,
            y: centre.y - GameConstants.playerSpriteSize.height * 0.5,
            width: size.width,
            height: size.height
        )
    }

    private func landOnFallbackFloorIfNeeded() {
        let standingCenterY = fallbackGroundY + GameConstants.playerSpriteSize.height * 0.5
        if position.y <= standingCenterY {
            let wasAirborne = !isGrounded
            let fallSpeed = velocity.dy
            position.y = standingCenterY
            velocity.dy = 0
            isGrounded = true
            if wasAirborne { emitLand(support: .fallbackFloor, vyBefore: fallSpeed) }
        }
    }

    /// Lanes are packed by the sink's producer helpers (see the note in
    /// Diagnostics/GameplayEventSink.swift): this file is in the Linux-compiled subset, but keeping
    /// every lane map in one place is what lets one table test cover every record type.
    private func emitJump(groundedBefore: Bool, afterContextConsume: Bool) {
        events?.emitJump(position: position, velocity: velocity.dy, groundedBefore: groundedBefore,
                         afterTeleport: afterContextConsume)
    }

    private func emitLand(support: GameplaySupport, vyBefore: CGFloat? = nil) {
        events?.emitLand(position: position, fallSpeed: vyBefore ?? velocity.dy, support: support)
    }

    private func updateMotionState(isCrouching: Bool) {
        let previousState = motionState
        defer {
            if previousState != .crouching, motionState == .crouching {
                events?.emitCrouchEdge(begins: true, position: position)
            } else if previousState == .crouching, motionState != .crouching {
                events?.emitCrouchEdge(begins: false, position: position)
            }
        }
        if isDying {
            motionState = .dying
        } else if !isGrounded {
            motionState = velocity.dy >= 0 ? .jumping : .falling
        } else if isCrouching {
            motionState = .crouching
        } else if abs(velocity.dx) > 0.01 {
            motionState = .running
        } else {
            motionState = .idle
        }
    }
}
