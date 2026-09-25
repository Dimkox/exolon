import CoreGraphics
import SpriteKit

final class BlasterBullet {
    private(set) var position: CGPoint
    private(set) var isAlive = true
    private var travelledDistance: CGFloat = 0

    let direction: PlayerFacing
    let node: SKSpriteNode

    // The HTML5 remake uses 6 pixels/tick and a 210 pixel range.
    // At our fixed 60 Hz update this is 360 logical pixels/second.
    private let speed: CGFloat = 360
    private let maximumRange: CGFloat = 210

    init(position: CGPoint, direction: PlayerFacing) {
        self.position = position
        self.direction = direction

        let texture = SKTexture(imageNamed: "blaster_bullet")
        texture.filteringMode = .nearest
        node = SKSpriteNode(texture: texture, size: GameConstants.blasterBulletSize)
        node.zPosition = 20
        node.xScale = direction == .left ? -1 : 1
        node.position = position
    }

    var hitbox: CGRect {
        return CGRect(x: position.x - GameConstants.blasterBulletSize.width * 0.5,
                      y: position.y - GameConstants.blasterBulletSize.height * 0.5,
                      width: GameConstants.blasterBulletSize.width,
                      height: GameConstants.blasterBulletSize.height)
    }

    func update(dt: TimeInterval) {
        guard isAlive else { return }

        let signedSpeed = direction == .right ? speed : -speed
        let dx = signedSpeed * CGFloat(dt)
        position.x += dx
        travelledDistance += abs(dx)
        node.position = position

        // P1-3: the cull bounds derive from the player clamp plus one bullet
        // width, so a shot never disappears while it is still entirely inside
        // the reachable field (the old logicalSize.width + 16 bound culled at
        // x>528 while the player can stand to x=544 and 61 maps carry
        // Collision right of x=512). The screen-transition trigger (x>510 in
        // GameScene.checkScreenExit) is unchanged.
        if travelledDistance >= maximumRange
            || position.x < GameConstants.blasterCullMinimumX
            || position.x > GameConstants.blasterCullMaximumX {
            isAlive = false
        }
    }

    func destroy() {
        isAlive = false
    }
}
