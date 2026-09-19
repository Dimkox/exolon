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
        node = SKSpriteNode(texture: texture, size: CGSize(width: 16, height: 2))
        node.zPosition = 20
        node.xScale = direction == .left ? -1 : 1
        node.position = position
    }

    var hitbox: CGRect {
        return CGRect(x: position.x - 8, y: position.y - 1, width: 16, height: 2)
    }

    func update(dt: TimeInterval) {
        guard isAlive else { return }

        let signedSpeed = direction == .right ? speed : -speed
        let dx = signedSpeed * CGFloat(dt)
        position.x += dx
        travelledDistance += abs(dx)
        node.position = position

        if travelledDistance >= maximumRange || position.x < -16 || position.x > GameConstants.logicalSize.width + 16 {
            isAlive = false
        }
    }

    func destroy() {
        isAlive = false
    }
}
