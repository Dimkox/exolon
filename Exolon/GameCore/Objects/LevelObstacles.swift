import Foundation
import SpriteKit

final class CocoonObstacle {
    let node: SKSpriteNode
    private(set) var isActive = true
    let hitbox: CGRect

    init(leftX: CGFloat, groundY: CGFloat) {
        let texture = SKTexture(imageNamed: "cocoon")
        texture.filteringMode = .nearest
        node = SKSpriteNode(texture: texture, size: CGSize(width: 80, height: 128))
        node.anchorPoint = CGPoint(x: 0, y: 0)
        node.position = CGPoint(x: leftX, y: groundY)
        node.zPosition = 8
        hitbox = CGRect(x: leftX, y: groundY, width: 80, height: 128)
    }

    var center: CGPoint { CGPoint(x: hitbox.midX, y: hitbox.midY) }

    func destroy() {
        guard isActive else { return }
        isActive = false
        node.removeFromParent()
    }
}

final class TurretObstacle {
    let node = SKNode()
    private let bodyNode: SKSpriteNode
    private let tubeNode: SKSpriteNode
    private let tubeFrames: [SKTexture]

    private(set) var isActive = true
    let hitbox: CGRect
    private var fireTimer: TimeInterval = 1.25
    private var animationTimer: TimeInterval = 0
    private var animationIndex = 0

    init(leftX: CGFloat, groundY: CGFloat) {
        hitbox = CGRect(x: leftX, y: groundY, width: 96, height: 80)
        node.position = .zero
        node.zPosition = 8

        let bodyTexture = SKTexture(imageNamed: "turret_body")
        bodyTexture.filteringMode = .nearest
        bodyNode = SKSpriteNode(texture: bodyTexture, size: CGSize(width: 64, height: 80))
        bodyNode.anchorPoint = CGPoint(x: 0, y: 0)
        bodyNode.position = CGPoint(x: leftX + 32, y: groundY)
        node.addChild(bodyNode)

        let tubeSheet = SKTexture(imageNamed: "turret_tube")
        tubeSheet.filteringMode = .nearest
        var frames: [SKTexture] = []
        for index in 0..<8 {
            let rect = CGRect(x: CGFloat(index) / 8.0, y: 0, width: 1.0 / 8.0, height: 1)
            let frame = SKTexture(rect: rect, in: tubeSheet)
            frame.filteringMode = .nearest
            frames.append(frame)
        }
        tubeFrames = frames
        tubeNode = SKSpriteNode(texture: frames[0], size: CGSize(width: 32, height: 16))
        // Frame 0 must reproduce the original composite turret.gif exactly.
        // Comparing the source composite against turret_body + turret_tube puts
        // the 32x16 tube 48 px above the base in our bottom-left coordinates.
        tubeNode.anchorPoint = CGPoint(x: 0, y: 0)
        tubeNode.position = CGPoint(x: leftX, y: groundY + 48)
        node.addChild(tubeNode)
    }

    var center: CGPoint { CGPoint(x: hitbox.midX, y: hitbox.midY) }

    // Reference createBullet(): x = tube.x - 4, y = tube.y + 10.
    // turret_bullet.gif is 4x4. Converted to SpriteKit centre coordinates,
    // the projectile centre sits at x-2 and y+52 from the turret base.
    var muzzle: CGPoint {
        // Original actions_gun_machine.asm places a shot at the action cell's
        // horizontal origin and at y*8+3. In our 2x SpriteKit coordinates the
        // 4x4 bullet centre is 2 px inside X and 56 px above the turret base.
        // The previous -2/+52 conversion was visibly low and left of the bore.
        CGPoint(x: hitbox.minX + 2, y: hitbox.minY + 56)
    }

    func fixedUpdate(dt: TimeInterval) -> EnemyTurretBullet? {
        guard isActive else { return nil }

        if animationTimer > 0 {
            animationTimer -= dt
            let elapsed = max(0, 0.18 - animationTimer)
            animationIndex = min(7, Int(elapsed / 0.0225))
            tubeNode.texture = tubeFrames[7 - animationIndex]
            if animationTimer <= 0 {
                tubeNode.texture = tubeFrames[0]
            }
        }

        fireTimer -= dt
        guard fireTimer <= 0 else { return nil }

        // Reference remake randomizes between 50 and 300 ticks. We use the
        // same range at 60 Hz and start with a short deterministic first shot.
        fireTimer = TimeInterval(Int.random(in: 50...300)) / 60.0
        animationTimer = 0.18
        animationIndex = 0
        return EnemyTurretBullet(position: muzzle)
    }

    func destroy() {
        guard isActive else { return }
        isActive = false
        node.removeFromParent()
    }
}

final class EnemyTurretBullet {
    enum Kind: Equatable {
        case turret
        case doubleLauncher
    }

    private(set) var position: CGPoint
    private(set) var isAlive = true
    let node: SKSpriteNode
    let kind: Kind
    let canBeShotDown: Bool
    let pointsWhenShotDown: Int

    private let speed: CGFloat
    private let projectileSize: CGSize

    init(position: CGPoint, kind: Kind = .turret) {
        self.position = position
        self.kind = kind

        let imageName: String
        switch kind {
        case .turret:
            imageName = "turret_bullet"
            projectileSize = CGSize(width: 4, height: 4)
            speed = -300 // original remake: -5 px/tick at 60 Hz
            canBeShotDown = false
            pointsWhenShotDown = 0

        case .doubleLauncher:
            // The double-barrel launcher uses a separate 16x16 rocket-like
            // projectile. The reference implementation moves it at -3 px/tick
            // and explicitly allows a blaster round to destroy it for 50 points.
            imageName = "double_launcher_bullet"
            projectileSize = CGSize(width: 16, height: 16)
            speed = -180
            canBeShotDown = true
            pointsWhenShotDown = 50
        }

        let texture = SKTexture(imageNamed: imageName)
        texture.filteringMode = .nearest
        node = SKSpriteNode(texture: texture, size: projectileSize)
        node.position = position
        node.zPosition = 20
    }

    var hitbox: CGRect {
        CGRect(
            x: position.x - projectileSize.width * 0.5,
            y: position.y - projectileSize.height * 0.5,
            width: projectileSize.width,
            height: projectileSize.height
        )
    }

    func update(dt: TimeInterval) {
        guard isAlive else { return }
        position.x += speed * CGFloat(dt)
        node.position = position
        if position.x < -projectileSize.width { isAlive = false }
    }

    func destroy() { isAlive = false }
}

final class DestructibleObstacle {
    let name: String
    let node: SKSpriteNode
    let hitbox: CGRect
    private(set) var isActive = true

    init(name: String, imageName: String, size: CGSize, bottomLeft: CGPoint, hitbox: CGRect) {
        self.name = name
        self.hitbox = hitbox

        let texture = SKTexture(imageNamed: imageName)
        texture.filteringMode = .nearest
        node = SKSpriteNode(texture: texture, size: size)
        node.anchorPoint = CGPoint(x: 0, y: 0)
        node.position = bottomLeft
        node.zPosition = 8
    }

    var center: CGPoint { CGPoint(x: hitbox.midX, y: hitbox.midY) }

    func destroy() {
        guard isActive else { return }
        isActive = false
        node.removeFromParent()
    }
}

final class GrenadePackPickup {
    let node: SKSpriteNode
    let hitbox: CGRect
    private(set) var isActive = true

    init(bottomLeft: CGPoint) {
        let texture = SKTexture(imageNamed: "grenade_pack")
        texture.filteringMode = .nearest
        node = SKSpriteNode(texture: texture, size: CGSize(width: 32, height: 32))
        node.anchorPoint = CGPoint(x: 0, y: 0)
        node.position = bottomLeft
        node.zPosition = 7
        hitbox = CGRect(x: bottomLeft.x + 2, y: bottomLeft.y + 2, width: 28, height: 30)
    }

    func collect() {
        guard isActive else { return }
        isActive = false
        node.removeFromParent()
    }
}

final class AmmoPackPickup {
    let node: SKSpriteNode
    let hitbox: CGRect
    private(set) var isActive = true

    init(bottomLeft: CGPoint) {
        let texture = SKTexture(imageNamed: "ammo_pack")
        texture.filteringMode = .nearest
        node = SKSpriteNode(texture: texture, size: CGSize(width: 32, height: 32))
        node.anchorPoint = CGPoint(x: 0, y: 0)
        node.position = bottomLeft
        node.zPosition = 9
        hitbox = CGRect(x: bottomLeft.x + 2, y: bottomLeft.y + 2, width: 28, height: 30)
    }

    func collect() {
        guard isActive else { return }
        isActive = false
        node.removeFromParent()
    }
}

final class TeleportPortal {
    let node: SKSpriteNode
    let visualBounds: CGRect
    let interactionRect: CGRect
    let destinationCenter: CGPoint

    private let frames: [SKTexture]
    private var animationTimer: TimeInterval = 0
    private var frameIndex = 0
    private let frameDuration: TimeInterval = 0.08

    init(bottomLeft: CGPoint) {
        let sheet = SKTexture(imageNamed: "teleport")
        sheet.filteringMode = .nearest

        var builtFrames: [SKTexture] = []
        for index in 0..<8 {
            let rect = CGRect(x: CGFloat(index) / 8.0, y: 0, width: 1.0 / 8.0, height: 1)
            let frame = SKTexture(rect: rect, in: sheet)
            frame.filteringMode = .nearest
            builtFrames.append(frame)
        }
        frames = builtFrames

        node = SKSpriteNode(texture: builtFrames[0], size: CGSize(width: 64, height: 96))
        node.anchorPoint = CGPoint(x: 0, y: 0)
        node.position = bottomLeft
        node.zPosition = 7

        visualBounds = CGRect(x: bottomLeft.x, y: bottomLeft.y, width: 64, height: 96)

        // Original remake: updateColRect(16, 32, 32, 48). melonJS uses a
        // top-left Y axis, so in our bottom-left system this becomes y+16...64.
        interactionRect = CGRect(x: bottomLeft.x + 16, y: bottomLeft.y + 16,
                                 width: 32, height: 48)

        // Original teleport places Vitorc with his 48 px sprite left edge at
        // the portal's left edge and his feet on the portal floor.
        destinationCenter = CGPoint(x: bottomLeft.x + 24, y: bottomLeft.y + 32)
    }

    /// A teleport is considered entered only when Vitorc's whole movement
    /// collider is inside the visible 64x96 portal. Merely touching an edge
    /// with a foot is deliberately not enough.
    func fullyContains(playerBox: CGRect) -> Bool {
        guard visualBounds.contains(playerBox) else { return false }
        return interactionRect.contains(CGPoint(x: playerBox.midX, y: playerBox.midY))
    }

    func fixedUpdate(dt: TimeInterval) {
        animationTimer += dt
        while animationTimer >= frameDuration {
            animationTimer -= frameDuration
            frameIndex = (frameIndex + 1) % frames.count
            node.texture = frames[frameIndex]
        }
    }
}

final class PistonHazard {
    enum Phase {
        case waiting
        case rising
        case exposed
        case falling
    }

    let node: SKSpriteNode
    private let groundY: CGFloat
    private let hiddenY: CGFloat
    private let exposedY: CGFloat
    private(set) var phase: Phase = .waiting
    private var phaseTimer: TimeInterval = 0
    private var waitDuration: TimeInterval

    init(leftX: CGFloat, groundY: CGFloat) {
        self.groundY = groundY
        hiddenY = groundY - 64
        exposedY = groundY
        waitDuration = TimeInterval(Int.random(in: 60...300)) / 60.0

        let texture = SKTexture(imageNamed: "piston")
        texture.filteringMode = .nearest
        node = SKSpriteNode(texture: texture, size: CGSize(width: 48, height: 64))
        node.anchorPoint = CGPoint(x: 0, y: 0)
        node.position = CGPoint(x: leftX, y: hiddenY)
        node.zPosition = 10
    }

    var hitbox: CGRect {
        let top = node.position.y + 64
        let visibleHeight = max(0, top - groundY)
        guard visibleHeight > 0 else { return .zero }
        return CGRect(x: node.position.x + 3, y: groundY, width: 42, height: visibleHeight)
    }

    func fixedUpdate(dt: TimeInterval) {
        phaseTimer += dt

        switch phase {
        case .waiting:
            node.position.y = hiddenY
            if phaseTimer >= waitDuration {
                phase = .rising
                phaseTimer = 0
            }

        case .rising:
            let duration: TimeInterval = 0.30
            let t = min(1, phaseTimer / duration)
            node.position.y = hiddenY + (exposedY - hiddenY) * CGFloat(t)
            if t >= 1 {
                phase = .exposed
                phaseTimer = 0
                node.position.y = exposedY
            }

        case .exposed:
            node.position.y = exposedY
            if phaseTimer >= 1.0 {
                phase = .falling
                phaseTimer = 0
            }

        case .falling:
            let duration: TimeInterval = 0.30
            let t = min(1, phaseTimer / duration)
            node.position.y = exposedY + (hiddenY - exposedY) * CGFloat(t)
            if t >= 1 {
                phase = .waiting
                phaseTimer = 0
                waitDuration = TimeInterval(Int.random(in: 60...300)) / 60.0
                node.position.y = hiddenY
            }
        }
    }
}

// MARK: - L01S04 bubble kamikaze

final class BubbleSpawner {
    private let delay: TimeInterval
    private let behavior: String
    private var timer: TimeInterval = 0

    init(delay: TimeInterval = 1.0, behavior: String = "swing") {
        self.delay = max(0.05, delay)
        self.behavior = behavior
    }

    func fixedUpdate(dt: TimeInterval, player: Player) -> BubbleEnemy? {
        if player.isDying {
            timer = 0
            return nil
        }

        timer += dt
        guard timer >= delay else { return nil }
        timer = 0

        // Reference KamikazeCreator only launches while Vitorc is in the
        // left portion of the screen. Bubbles always enter from x=512.
        guard player.position.x <= 320 else { return nil }

        let spawn = CGPoint(
            // Reference creator starts at x=512; the 32 px SpriteKit sprite
            // is centre-anchored, hence +16. Swing behavior then adds 0...32.
            x: 528 + CGFloat(Double.random(in: 0...32)),
            // Old engine Y grows downward. BubbleEntity starts roughly at
            // Vitorc centre+2 and SwingMovementBehavior shifts it up 0...16.
            y: player.position.y + 2 - CGFloat(Double.random(in: 0...16))
        )
        return BubbleEnemy(position: spawn, behavior: behavior)
    }
}

final class BubbleEnemy {
    private(set) var position: CGPoint
    private(set) var isAlive = true
    let node: SKSpriteNode
    let points = 150

    private let frames: [SKTexture]
    private var frameIndex = 0
    private var animationTimer: TimeInterval = 0
    private let behavior: String
    private var phase: CGFloat = 0

    init(position: CGPoint, behavior: String) {
        self.position = position
        self.behavior = behavior

        let sheet = SKTexture(imageNamed: "bubble")
        sheet.filteringMode = .nearest

        // bubble.png is 3 columns x 6 colour rows. Each original animation
        // selects one colour row and cycles its three 32x32 frames.
        let colourRow = Int.random(in: 0..<6)
        var built: [SKTexture] = []
        for column in 0..<3 {
            let rect = CGRect(
                x: CGFloat(column) / 3.0,
                y: 1.0 - CGFloat(colourRow + 1) / 6.0,
                width: 1.0 / 3.0,
                height: 1.0 / 6.0
            )
            let texture = SKTexture(rect: rect, in: sheet)
            texture.filteringMode = .nearest
            built.append(texture)
        }
        frames = built

        node = SKSpriteNode(texture: built[0], size: CGSize(width: 32, height: 32))
        node.position = position
        node.zPosition = 18
    }

    var hitbox: CGRect {
        CGRect(x: position.x - 14, y: position.y - 14, width: 28, height: 28)
    }

    func fixedUpdate(dt: TimeInterval) {
        guard isAlive else { return }
        let tickScale = CGFloat(dt / GameConstants.fixedTimeStep)

        switch behavior {
        case "circular":
            phase += 0.07 * tickScale
            position.x -= 1.7 * tickScale
            position.y += CGFloat(cos(Double(phase))) * 2.0 * tickScale

        case "zig_zag":
            phase += 0.11 * tickScale
            position.x -= 1.7 * tickScale
            position.y += (sin(Double(phase)) >= 0 ? 1.8 : -1.8) * tickScale

        default:
            // SwingMovementBehavior.SPEED = 1.7 px/tick. The original engine
            // has a downward-positive Y axis, so the vertical term is inverted
            // for SpriteKit's upward-positive coordinates.
            position.x -= 1.7 * tickScale
            let swing = CGFloat(Double.random(in: 1...3)) * CGFloat(sin(Double(position.x / 20.0)))
            position.y -= swing * tickScale
        }

        node.position = position

        animationTimer += dt
        if animationTimer >= 0.08 {
            animationTimer -= 0.08
            frameIndex = (frameIndex + 1) % frames.count
            node.texture = frames[frameIndex]
        }

        if position.x < -24 || position.y < -32 || position.y > GameConstants.logicalSize.height + 32 {
            destroy()
        }
    }

    func destroy() {
        isAlive = false
    }
}

// MARK: - L01S06 incubator and eggs

final class IncubatorObstacle {
    let node: SKSpriteNode
    let hitbox: CGRect
    private(set) var isActive = true
    private(set) var eggs: [EggEnemy] = []

    init(bottomLeft: CGPoint) {
        let texture = SKTexture(imageNamed: "incubator")
        texture.filteringMode = .nearest
        node = SKSpriteNode(texture: texture, size: CGSize(width: 64, height: 96))
        node.anchorPoint = CGPoint(x: 0, y: 0)
        node.position = bottomLeft
        node.zPosition = 9

        hitbox = CGRect(x: bottomLeft.x, y: bottomLeft.y, width: 64, height: 96)

        // Reference IncubatorEntity creates eight eggs in a 32x32 chamber
        // offset 16 px horizontally inside the 64x96 incubator. Converting
        // the old top-left coordinates to our bottom-left system places the
        // chamber 48...80 px above the base.
        let chamber = CGRect(x: bottomLeft.x + 16, y: bottomLeft.y + 48, width: 32, height: 32)
        for index in 0..<8 {
            let x = chamber.minX + 8 + CGFloat((index % 4) * 5)
            let y = chamber.minY + 8 + CGFloat((index / 4) * 10)
            eggs.append(EggEnemy(position: CGPoint(x: x, y: y), confinement: chamber))
        }
    }

    var center: CGPoint { CGPoint(x: hitbox.midX, y: hitbox.midY) }

    func destroy() {
        guard isActive else { return }
        isActive = false
        node.removeFromParent()
        for egg in eggs where egg.isAlive {
            egg.releaseFromIncubator()
        }
    }
}

final class EggEnemy {
    private(set) var position: CGPoint
    private(set) var isAlive = true
    let node: SKSpriteNode
    let points = 50

    private var confinement: CGRect?
    private var velocity: CGVector
    private let frames: [SKTexture]
    private var frameIndex = 0
    private var animationTimer: TimeInterval = 0
    private var jitterSeed: UInt64

    init(position: CGPoint, confinement: CGRect?) {
        self.position = position
        self.confinement = confinement
        self.jitterSeed = UInt64.random(in: 1...UInt64.max)

        // Reference EggEntity starts with roughly -3...+3 px/tick horizontal
        // and -1...+1 px/tick vertical motion.
        var vx = CGFloat(Double.random(in: -3.0...3.0))
        if abs(vx) < 0.7 { vx = vx < 0 ? -0.7 : 0.7 }
        var vy = CGFloat(Double.random(in: -1.0...1.0))
        if abs(vy) < 0.25 { vy = vy < 0 ? -0.25 : 0.25 }
        velocity = CGVector(dx: vx, dy: vy)

        let sheet = SKTexture(imageNamed: "egg")
        sheet.filteringMode = .nearest
        var built: [SKTexture] = []
        for column in 0..<2 {
            let rect = CGRect(x: CGFloat(column) * 0.5, y: 0, width: 0.5, height: 1)
            let texture = SKTexture(rect: rect, in: sheet)
            texture.filteringMode = .nearest
            built.append(texture)
        }
        frames = built

        node = SKSpriteNode(texture: built[0], size: CGSize(width: 16, height: 16))
        node.position = position
        node.zPosition = 19
    }

    var hitbox: CGRect {
        CGRect(x: position.x - 7, y: position.y - 7, width: 14, height: 14)
    }

    func releaseFromIncubator() {
        confinement = nil
    }

    func fixedUpdate(dt: TimeInterval, terrainRects: [CGRect]) {
        guard isAlive else { return }
        let tickScale = CGFloat(dt / GameConstants.fixedTimeStep)
        let previous = position

        // A tiny deterministic-looking shake reproduces the jittery motion
        // of the original EggEntity without changing its average velocity.
        jitterSeed = jitterSeed &* 6364136223846793005 &+ 1442695040888963407
        let jitterBits = Int((jitterSeed >> 32) & 0xFF)
        let jitter = (CGFloat(jitterBits) / 255.0 - 0.5) * 0.45

        position.x += velocity.dx * tickScale
        position.y += (velocity.dy + jitter) * tickScale

        if let box = confinement {
            if position.x - 8 < box.minX || position.x + 8 > box.maxX {
                position.x = previous.x
                velocity.dx = -velocity.dx
            }
            if position.y - 8 < box.minY || position.y + 8 > box.maxY {
                position.y = previous.y
                velocity.dy = -velocity.dy
            }
        } else {
            let currentBox = hitbox
            if let solid = terrainRects.first(where: { currentBox.intersects($0) }) {
                position = previous
                let previousBox = CGRect(x: previous.x - 7, y: previous.y - 7, width: 14, height: 14)
                if previousBox.maxY <= solid.minY || previousBox.minY >= solid.maxY {
                    velocity.dy = -velocity.dy
                } else {
                    velocity.dx = -velocity.dx
                }
            }

            if position.x - 8 < 0 {
                position.x = 8
                velocity.dx = abs(velocity.dx)
            } else if position.x + 8 > GameConstants.logicalSize.width {
                position.x = GameConstants.logicalSize.width - 8
                velocity.dx = -abs(velocity.dx)
            }

            // Keep released eggs in the gameplay area above the HUD.
            if position.y - 8 < GameConstants.hudHeight {
                position.y = GameConstants.hudHeight + 8
                velocity.dy = abs(velocity.dy)
            } else if position.y + 8 > GameConstants.logicalSize.height {
                position.y = GameConstants.logicalSize.height - 8
                velocity.dy = -abs(velocity.dy)
            }
        }

        node.position = position
        animationTimer += dt
        if animationTimer >= 0.09 {
            animationTimer -= 0.09
            frameIndex = (frameIndex + 1) % frames.count
            node.texture = frames[frameIndex]
        }

        // Reference occasionally flips one velocity component. Keep the same
        // restless behaviour at a low probability per 60 Hz tick.
        if Int.random(in: 0..<360) == 0 { velocity.dx = -velocity.dx }
        if Int.random(in: 0..<360) == 1 { velocity.dy = -velocity.dy }
    }

    func destroy() {
        isAlive = false
    }
}

// MARK: - Original Zone 006 double-barrel launcher

final class DoubleLauncherObstacle {
    let node: SKSpriteNode
    let hitbox: CGRect
    /// P1-6 (audit 2026-09-20, issue #10; architecture.md -> Decisions 2): the fire gate and the
    /// bonus payout used to be the same flag, so collecting the invisible-region bonus paid 1000
    /// points once and permanently silenced the launcher. `bonusState` now owns both facts
    /// separately; `isActive` stays the fire gate and the payout never clears it.
    private var bonusState = LauncherBonusState()
    /// Ordinal of the `double_launcher` object in `map.objectGroups.flatMap { $0.objects }`, so a
    /// `bonus.double_launcher` line can be joined to the map and to its `entity.launcher_fire`
    /// records (architect section 5.2).
    let entityID: UInt16
    private var fireTimer: TimeInterval = TimeInterval(Int.random(in: 20...160)) / 60.0

    /// Fire gate: unchanged for every existing reader of `isActive`; the query goes through
    /// `LauncherBonusState.canFire` so the value the launcher fires on and the value
    /// `launcher_active_after` reports are the same read.
    var isActive: Bool { bonusState.canFire }
    /// Reported as `launcher_active_after`: the payout must leave the launcher firing.
    var bonusWasCollected: Bool { bonusState.bonusCollected }

    init(bottomLeft: CGPoint, entityID: UInt16) {
        let texture = SKTexture(imageNamed: "double_launcher")
        texture.filteringMode = .nearest
        node = SKSpriteNode(texture: texture, size: CGSize(width: 64, height: 48))
        node.anchorPoint = CGPoint(x: 0, y: 0)
        node.position = bottomLeft
        node.zPosition = 9
        hitbox = CGRect(x: bottomLeft.x, y: bottomLeft.y, width: 64, height: 48)
    }

    func fixedUpdate(dt: TimeInterval, player: Player) -> EnemyTurretBullet? {
        guard isActive, !player.isDying else { return nil }

        // Reference behaviour: stop firing when Vitorc comes within 110 px
        // of the launcher. This also prevents it firing through/behind him.
        let distance = hitbox.minX - player.movementHitbox.minX
        guard distance > 110 else { return nil }

        fireTimer -= dt
        guard fireTimer <= 0 else { return nil }
        fireTimer = TimeInterval(Int.random(in: 20...160)) / 60.0

        // The two green barrels occupy the upper 32 pixels of the 64x48
        // sprite. A 16x16 projectile must be centred at +40 or +24 so its
        // right edge begins exactly at the two left muzzle openings.
        let barrelY: CGFloat = Bool.random() ? 40 : 24
        let muzzle = CGPoint(x: hitbox.minX - 8, y: hitbox.minY + barrelY)
        return EnemyTurretBullet(position: muzzle, kind: .doubleLauncher)
    }

    /// Pays the region bonus exactly once per launcher per zone instantiation and leaves the
    /// fire gate alone. The dimmed sprite keeps marking the spent region.
    func collectBonusIfTouched(playerBox: CGRect) -> Bool {
        guard bonusState.payBonus(touchesBonusRegion: playerBox.intersects(hitbox)) else { return false }
        node.alpha = 0.45
        return true
    }
}


// MARK: - Original land mine (introduced in Zone 007)

final class MineHazard {
    let node: SKSpriteNode
    let hitbox: CGRect
    private(set) var isArmed = true

    init(bottomLeft: CGPoint) {
        let texture = SKTexture(imageNamed: "mine")
        texture.filteringMode = .nearest
        node = SKSpriteNode(texture: texture, size: CGSize(width: 32, height: 16))
        node.anchorPoint = CGPoint(x: 0, y: 0)
        node.position = bottomLeft
        node.zPosition = 10
        hitbox = CGRect(x: bottomLeft.x, y: bottomLeft.y, width: 32, height: 16)
    }

    var center: CGPoint { CGPoint(x: hitbox.midX, y: hitbox.midY) }

    func triggerIfPlayerEnters(playerBox: CGRect) -> Bool {
        guard isArmed else { return false }
        // The original checks the soldier's feet against the mine row and a
        // narrow horizontal proximity window; this reproduces that behavior
        // rather than requiring pixel-perfect sprite overlap.
        let trigger = CGRect(x: hitbox.minX - 10, y: hitbox.minY, width: hitbox.width + 20, height: 28)
        guard playerBox.intersects(trigger) else { return false }
        isArmed = false
        node.removeFromParent()
        return true
    }
}


// MARK: - Original electric force field

final class ForceFieldBarrier {
    let hitbox: CGRect
    let node: SKShapeNode
    private(set) var isActive = true
    private var hitPoints = 25

    init(hitbox: CGRect) {
        self.hitbox = hitbox
        node = SKShapeNode(rect: hitbox)
        node.fillColor = .clear
        node.strokeColor = .clear
        node.zPosition = 6
    }

    @discardableResult
    func hitByBlaster() -> Bool {
        guard isActive else { return false }
        hitPoints -= 1
        if hitPoints <= 0 {
            isActive = false
            // The imported beam is part of the tile layer. Cover its former
            // area when destroyed so the visual state follows gameplay.
            node.fillColor = .black
            node.strokeColor = .black
            return true
        }
        return false
    }
}


// MARK: - Green missile guidance / homing missile

final class GreenMissileGuidance {
    let hitbox: CGRect
    let coverNode: SKShapeNode
    private(set) var isActive = true

    init(hitbox: CGRect) {
        self.hitbox = hitbox
        coverNode = SKShapeNode(rect: hitbox)
        coverNode.fillColor = .clear
        coverNode.strokeColor = .clear
        coverNode.zPosition = 7.5
    }

    var center: CGPoint { CGPoint(x: hitbox.midX, y: hitbox.midY) }

    func destroy() {
        guard isActive else { return }
        isActive = false
        // The restored original screen is a single backdrop image. Cover only
        // the original destroyable beacon region; the separate pedestal below
        // remains visible, matching the block split in data_zone_data.asm.
        coverNode.fillColor = .black
        coverNode.strokeColor = .black
    }
}

final class HomingMissile {
    private(set) var position: CGPoint
    private(set) var isAlive = true
    let node: SKSpriteNode

    private let normalFrame: SKTexture
    private let fastFrame: SKTexture
    private var isFast = false

    // The 512-wide reference conversion of the original uses 1.5 px/tick,
    // then 3 px/tick after x <= 280, and 1 px/tick vertical tracking.
    private let normalSpeed: CGFloat = 90
    private let fastSpeed: CGFloat = 180
    private let verticalSpeed: CGFloat = 60

    init(startY: CGFloat) {
        let sheet = SKTexture(imageNamed: "missile")
        sheet.filteringMode = .nearest
        normalFrame = SKTexture(rect: CGRect(x: 0, y: 0, width: 0.5, height: 1), in: sheet)
        fastFrame = SKTexture(rect: CGRect(x: 0.5, y: 0, width: 0.5, height: 1), in: sheet)
        normalFrame.filteringMode = .nearest
        fastFrame.filteringMode = .nearest

        // Reference image uses top-left x=512 for a 32px missile; SpriteKit
        // positions sprites by centre, so 528 starts fully just off-screen.
        position = CGPoint(x: GameConstants.logicalSize.width + 16, y: startY)
        node = SKSpriteNode(texture: normalFrame, size: CGSize(width: 32, height: 32))
        node.position = position
        node.zPosition = 20
    }

    var hitbox: CGRect {
        CGRect(x: position.x - 14, y: position.y - 12, width: 28, height: 24)
    }

    func fixedUpdate(dt: TimeInterval, targetY: CGFloat) {
        guard isAlive else { return }

        if !isFast && position.x <= 280 {
            isFast = true
            node.texture = fastFrame
        }

        position.x -= (isFast ? fastSpeed : normalSpeed) * CGFloat(dt)

        let step = verticalSpeed * CGFloat(dt)
        if position.y > targetY {
            position.y = max(targetY, position.y - step)
        } else if position.y < targetY {
            position.y = min(targetY, position.y + step)
        }

        node.position = position
        if position.x < -20 { destroy() }
    }

    func destroy() {
        isAlive = false
    }
}
