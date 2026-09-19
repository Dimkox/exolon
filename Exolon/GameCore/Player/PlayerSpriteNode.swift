import SpriteKit

final class PlayerSpriteNode: SKSpriteNode {
    private static let frameCount = 11
    private static let frameSize = CGSize(width: 48, height: 64)

    private let frames: [SKTexture]
    private var displayedState: PlayerMotionState?
    private var animationTimer: TimeInterval = 0
    private var animationIndex = 0

    // Animation layout taken from the Vitorc sprite sheet used by the
    // HTML5 Exolon remake: stand 0, walk 0-8, jump 3, duck 9, fall 8.
    private let runSequence = [0, 1, 2, 3, 4, 0, 5, 6, 7, 8]
    private let runFrameDuration: TimeInterval = 1.0 / 12.0

    init() {
        let sheet = SKTexture(imageNamed: "vitorc")
        sheet.filteringMode = .nearest

        var textures: [SKTexture] = []
        let width = 1.0 / CGFloat(PlayerSpriteNode.frameCount)
        for index in 0..<PlayerSpriteNode.frameCount {
            let rect = CGRect(x: CGFloat(index) * width, y: 0, width: width, height: 1)
            let texture = SKTexture(rect: rect, in: sheet)
            texture.filteringMode = .nearest
            textures.append(texture)
        }
        frames = textures

        super.init(texture: textures[0], color: .clear, size: PlayerSpriteNode.frameSize)
        name = "vitorc"
        anchorPoint = CGPoint(x: 0.5, y: 0.5)
        zPosition = 10
    }

    required init?(coder aDecoder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    func update(from player: Player, dt: TimeInterval) {
        xScale = player.facing == .left ? -1 : 1
        // Temporary visual cue until the original exoskeleton frames are wired
        // as a second sheet: mechanics are already exact and data-driven.
        color = player.hasExoskeleton ? .cyan : .white
        colorBlendFactor = player.hasExoskeleton ? 0.35 : 0

        if displayedState != player.motionState {
            displayedState = player.motionState
            animationTimer = 0
            animationIndex = 0
            applyFirstFrame(for: player.motionState)
        }

        guard player.motionState == .running else { return }

        animationTimer += dt
        while animationTimer >= runFrameDuration {
            animationTimer -= runFrameDuration
            animationIndex = (animationIndex + 1) % runSequence.count
            texture = frames[runSequence[animationIndex]]
        }
    }

    private func applyFirstFrame(for state: PlayerMotionState) {
        switch state {
        case .idle:
            texture = frames[0]
        case .running:
            texture = frames[runSequence[0]]
        case .jumping:
            texture = frames[3]
        case .falling:
            texture = frames[8]
        case .crouching:
            texture = frames[9]
        case .dying:
            texture = frames[10]
        }
    }
}
