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

    private let moveSpeed: CGFloat = 90
    private let jumpVelocity: CGFloat = 165
    private let deathJumpVelocity: CGFloat = 165
    private let gravity: CGFloat = -360
    private let maximumFallSpeed: CGFloat = -300

    private var jumpWasPressed = false
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
        if jumpJustPressed && isGrounded && !isCrouching {
            velocity.dy = jumpVelocity
            isGrounded = false
        }
        jumpWasPressed = input.jump

        if !isGrounded {
            velocity.dy = max(velocity.dy + gravity * step, maximumFallSpeed)
        }

        position.x += velocity.dx * step
        position.y += velocity.dy * step

        // Original screen transition happens around x=510.
        // Clamp by the visible 48 px sprite, not by the narrower collider.
        // Otherwise the x=0 TMX spawn can walk a few pixels off the left edge.
        let visualHalfWidth = GameConstants.playerSpriteSize.width * 0.5
        position.x = min(max(position.x, visualHalfWidth), GameConstants.logicalSize.width + 32)

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
            position.y = solid.maxY + GameConstants.playerSpriteSize.height * 0.5
            velocity.dy = 0
            isGrounded = true
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
        let horizontalInset: CGFloat = 3
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
    }


    func toggleExoskeleton() {
        guard !isDying else { return }
        hasExoskeleton.toggle()
    }

    func setExoskeleton(_ enabled: Bool) {
        hasExoskeleton = enabled
    }

    /// UP is also the contextual action key for teleports and changing rooms.
    /// When the scene consumes that press, keep Player's edge latch held until
    /// the physical key/button is released so the next fixed step cannot turn
    /// the same press into an accidental jump.
    func consumeContextualJumpPress() {
        jumpWasPressed = true
    }

    func blasterOrigin() -> CGPoint {
        // Reference VitorcEntity: BLASTER_BULLET_OFFSET_X=2,
        // BLASTER_BULLET_OFFSET_Y=30, DUCK_OFFSET=10. Converted from the
        // original top-left entity coordinates to our centre-based SpriteKit
        // coordinates, including the 16x2 bullet size.
        let xOffset: CGFloat = facing == .right ? 34 : -34
        let yOffset: CGFloat = motionState == .crouching ? -9 : 1
        return CGPoint(x: position.x + xOffset, y: position.y + yOffset)
    }

    func grenadeOrigin() -> CGPoint {
        // Reference offsets: GRENADE_OFFSET_X=20, GRENADE_OFFSET_Y=12,
        // DUCK_OFFSET=10. The grenade sheet is 16x16.
        let xOffset: CGFloat = facing == .right ? 4 : -4
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
            position.y = standingCenterY
            velocity.dy = 0
            isGrounded = true
        }
    }

    private func updateMotionState(isCrouching: Bool) {
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
