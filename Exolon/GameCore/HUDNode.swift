import Foundation
import SpriteKit

final class HUDNode: SKNode {
    private let ammoValue = SKLabelNode(fontNamed: "Menlo-Bold")
    private let grenadeValue = SKLabelNode(fontNamed: "Menlo-Bold")
    private let pointsValue = SKLabelNode(fontNamed: "Menlo-Bold")
    private let livesValue = SKLabelNode(fontNamed: "Menlo-Bold")
    private let zoneValue = SKLabelNode(fontNamed: "Menlo-Bold")

    override init() {
        super.init()
        zPosition = 100

        let background = SKSpriteNode(color: .black,
                                      size: CGSize(width: GameConstants.logicalSize.width,
                                                   height: GameConstants.hudHeight))
        background.anchorPoint = CGPoint(x: 0, y: 0)
        background.position = .zero
        background.zPosition = -1
        addChild(background)

        // The original HUD is a separate black two-line panel, not text laid
        // over the terrain.  Keep the five columns centred and large enough to
        // read like the Spectrum status strip.
        let items: [(String, CGFloat, SKLabelNode, SKColor, SKColor)] = [
            ("AMMO", 48, ammoValue, .cyan, .cyan),
            ("GRENADES", 145, grenadeValue, .yellow, .magenta),
            ("POINTS", 266, pointsValue, .green, .cyan),
            ("LIVES", 382, livesValue, .white, .yellow),
            ("ZONES", 470, zoneValue, .magenta, .magenta)
        ]

        for item in items {
            let title = SKLabelNode(fontNamed: "Menlo-Bold")
            title.text = item.0
            title.fontSize = 11
            title.fontColor = item.3
            title.horizontalAlignmentMode = .center
            title.verticalAlignmentMode = .center
            title.position = CGPoint(x: item.1, y: 32)
            addChild(title)

            item.2.fontSize = 12
            item.2.fontColor = item.4
            item.2.horizontalAlignmentMode = .center
            item.2.verticalAlignmentMode = .center
            item.2.position = CGPoint(x: item.1, y: 13)
            addChild(item.2)
        }
    }

    required init?(coder aDecoder: NSCoder) {
        fatalError("init(coder:) has not been implemented")
    }

    func update(state: GameState) {
        ammoValue.text = String(format: "%02d", max(0, state.ammo))
        grenadeValue.text = String(format: "%02d", max(0, state.grenades))
        pointsValue.text = String(format: "%06d", max(0, state.points))
        livesValue.text = String(max(0, state.lives))
        zoneValue.text = String(format: "%03d", max(0, state.zone))
    }
}
