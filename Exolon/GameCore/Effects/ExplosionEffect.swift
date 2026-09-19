import SpriteKit

final class ExplosionEffect: SKSpriteNode {
    enum Kind {
        case blaster
        case circular
    }

    private let frames: [SKTexture]
    private let frameDuration: TimeInterval
    private var elapsed: TimeInterval = 0
    private var frameIndex = 0

    private init(kind: Kind, position: CGPoint) {
        let imageName: String
        let frameCount: Int
        let frameSize: CGSize
        let duration: TimeInterval

        switch kind {
        case .blaster:
            imageName = "blaster_explosion"
            frameCount = 5
            frameSize = CGSize(width: 16, height: 16)
            duration = 1.0 / 22.0
        case .circular:
            imageName = "circular_explosion"
            frameCount = 10
            frameSize = CGSize(width: 32, height: 32)
            duration = 1.0 / 18.0
        }

        let sheet = SKTexture(imageNamed: imageName)
        sheet.filteringMode = .nearest

        var textures: [SKTexture] = []
        let normalizedWidth = 1.0 / CGFloat(frameCount)
        for index in 0..<frameCount {
            let rect = CGRect(x: CGFloat(index) * normalizedWidth, y: 0, width: normalizedWidth, height: 1)
            let texture = SKTexture(rect: rect, in: sheet)
            texture.filteringMode = .nearest
            textures.append(texture)
        }

        frames = textures
        frameDuration = duration

        super.init(texture: textures[0], color: .clear, size: frameSize)
        self.position = position
        zPosition = 30
    }

    required init?(coder aDecoder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    static func blaster(at position: CGPoint) -> ExplosionEffect {
        return ExplosionEffect(kind: .blaster, position: position)
    }

    static func circular(at position: CGPoint) -> ExplosionEffect {
        return ExplosionEffect(kind: .circular, position: position)
    }

    // Returns true while the animation is alive.
    func fixedUpdate(dt: TimeInterval) -> Bool {
        elapsed += dt

        while elapsed >= frameDuration {
            elapsed -= frameDuration
            frameIndex += 1
            if frameIndex >= frames.count {
                removeFromParent()
                return false
            }
            texture = frames[frameIndex]
        }

        return true
    }
}
