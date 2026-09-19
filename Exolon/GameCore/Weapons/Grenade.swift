import CoreGraphics
import SpriteKit

final class Grenade {
    private enum FlightPhase {
        case rising
        case glide
        case dive
    }

    private(set) var position: CGPoint
    private(set) var isAlive = true

    let node: SKSpriteNode

    private let directionSign: CGFloat
    private let groundY: CGFloat
    private var phase: FlightPhase = .rising

    // Reference remake values are expressed as pixels per 60 Hz update:
    // VEL_Y 3.3, UP_VEL_X 1.5, UP_GRAVITY 0.2,
    // DOWN_VEL_X 5.5, DOWN_GRAVITY 0.1 and 30 glide ticks.
    private var velocityPerTick = CGVector(dx: 1.5, dy: 3.3)
    private var glideTicks = 0
    private var trailTicks = 0

    init(position: CGPoint, direction: PlayerFacing, groundY: CGFloat) {
        self.position = position
        self.groundY = groundY
        directionSign = direction == .right ? 1 : -1
        velocityPerTick.dx *= directionSign

        let texture = SKTexture(imageNamed: "grenade")
        texture.filteringMode = .nearest
        node = SKSpriteNode(texture: texture, size: CGSize(width: 16, height: 16))
        node.zPosition = 19
        node.xScale = direction == .left ? -1 : 1
        node.position = position
    }

    var hitbox: CGRect {
        return CGRect(x: position.x - 5, y: position.y - 5, width: 10, height: 10)
    }

    // Returns a position at which the scene can leave a short-lived coloured
    // exhaust pixel. This recreates the conspicuous backpack grenade trail.
    func update(dt: TimeInterval) -> CGPoint? {
        guard isAlive else { return nil }

        let oldPosition = position
        let tickScale = CGFloat(dt / GameConstants.fixedTimeStep)

        switch phase {
        case .rising:
            velocityPerTick.dx = 1.5 * directionSign
            velocityPerTick.dy -= 0.2 * tickScale
            if velocityPerTick.dy <= 0 {
                phase = .glide
                glideTicks = 0
            }

        case .glide:
            velocityPerTick.dx = 1.5 * directionSign
            // The reference behaviour deliberately suspends gravity briefly,
            // producing the characteristic shallow middle section of the lob.
            glideTicks += 1
            if glideTicks > 30 {
                phase = .dive
            }

        case .dive:
            velocityPerTick.dx = 5.5 * directionSign
            velocityPerTick.dy -= 0.1 * tickScale
        }

        position.x += velocityPerTick.dx * tickScale
        position.y += velocityPerTick.dy * tickScale
        node.position = position

        if position.x < -24 || position.x > GameConstants.logicalSize.width + 24 || position.y > GameConstants.logicalSize.height + 40 {
            isAlive = false
        }

        trailTicks += 1
        return trailTicks % 2 == 0 ? oldPosition : nil
    }

    func hasHitGround() -> Bool {
        return position.y - 5 <= groundY + 2 && velocityPerTick.dy <= 0
    }

    func destroy() {
        isAlive = false
    }
}

final class GrenadeTrailDot: SKSpriteNode {
    private var life: TimeInterval = 0.20

    init(position: CGPoint, index: Int) {
        let palette: [SKColor] = [.cyan, .yellow, .magenta, .white]
        super.init(texture: nil, color: palette[index % palette.count], size: CGSize(width: 2, height: 2))
        self.position = position
        zPosition = 18
    }

    required init?(coder aDecoder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    func fixedUpdate(dt: TimeInterval) -> Bool {
        life -= dt
        alpha = CGFloat(max(0, life / 0.20))
        if life <= 0 {
            removeFromParent()
            return false
        }
        return true
    }
}
