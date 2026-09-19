import Foundation
import SpriteKit

final class GameScene: SKScene {
    let inputState = InputState()

    private let player = Player()
    private let playerNode = PlayerSpriteNode()
    private let gameState = GameState()
    private let hud = HUDNode()
    private var currentLevel: TMXLevelRuntime!
    private var currentLevelName = "L01S01"

    private let inputLabel = SKLabelNode(fontNamed: "Menlo")
    private let gamepadLabel = SKLabelNode(fontNamed: "Menlo")
    private let stepLabel = SKLabelNode(fontNamed: "Menlo-Bold")
    private let bannerLabel = SKLabelNode(fontNamed: "Menlo-Bold")
    private let debugOverlay = SKNode()
    private let pauseOverlay = SKNode()
    private let titleOverlay = SKNode()
    private let terminalOverlay = SKNode()
    private let testModeLabel = SKLabelNode(fontNamed: "Menlo-Bold")

    private let persistence = GamePersistence.shared

    private var bullets: [BlasterBullet] = []
    private var grenades: [Grenade] = []
    private var enemyBullets: [EnemyTurretBullet] = []
    private var explosions: [ExplosionEffect] = []
    private var grenadeTrailDots: [GrenadeTrailDot] = []
    private var grenadeTrailIndex = 0

    private var fireWasPressed = false
    private var grenadeWasPressed = false
    private var sceneJumpWasPressed = false
    private var debugWasPressed = false
    private var showHitboxes = false
    private var flowState: GameFlowState = .title
    private var stateBeforePause: GameFlowState = .playing
    private var pauseConfirmWasPressed = false
    private var pauseMenuUpWasPressed = false
    private var pauseMenuDownWasPressed = false
    private var pauseSelectedIndex = 0
    private var menuFireWasPressed = false
    private var testInvulnerabilityEnabled = false
    private var invulnerability: TimeInterval = 0
    private var deathGroundTimer: TimeInterval = 0
    private var hasSavedCheckpoint = false

    private var previousUpdateTime: TimeInterval = 0
    private var accumulator: TimeInterval = 0

    private let includedLevels: Set<String> = Set((1...5).flatMap { stage in (1...25).map { String(format: "L%02dS%02d", stage, $0) } })

    override func didMove(to view: SKView) {
        backgroundColor = .black
        anchorPoint = CGPoint(x: 0, y: 0)

        loadPersistentState()
        currentLevel = TMXLevelRuntime(resource: currentLevelName)
        addChild(currentLevel.rootNode)
        player.configure(spawnCenter: currentLevel.spawnCenter, groundY: currentLevel.groundY)
        syncPlayerNodePosition()
        addChild(playerNode)
        addChild(hud)

        stepLabel.text = "STEP 9 · ALL 125 ORIGINAL ZONES"
        stepLabel.fontSize = 7
        stepLabel.horizontalAlignmentMode = .center
        stepLabel.position = CGPoint(x: 256, y: 370)
        stepLabel.zPosition = 120
        addChild(stepLabel)
        stepLabel.isHidden = true

        inputLabel.fontSize = 5.5
        inputLabel.horizontalAlignmentMode = .left
        inputLabel.position = CGPoint(x: 8, y: 370)
        inputLabel.zPosition = 120
        addChild(inputLabel)
        inputLabel.isHidden = true

        gamepadLabel.text = "GAMEPAD: waiting / keyboard ready"
        gamepadLabel.fontSize = 5.5
        gamepadLabel.horizontalAlignmentMode = .right
        gamepadLabel.position = CGPoint(x: 504, y: 370)
        gamepadLabel.zPosition = 120
        addChild(gamepadLabel)
        gamepadLabel.isHidden = true

        bannerLabel.fontSize = 12
        bannerLabel.horizontalAlignmentMode = .center
        bannerLabel.position = CGPoint(x: 256, y: 205)
        bannerLabel.zPosition = 200
        addChild(bannerLabel)

        debugOverlay.zPosition = 500
        addChild(debugOverlay)

        buildPauseOverlay()
        addChild(pauseOverlay)
        buildTitleOverlay()
        addChild(titleOverlay)
        buildTerminalOverlay()
        addChild(terminalOverlay)

        testModeLabel.text = "TEST MODE · INVULNERABILITY"
        testModeLabel.fontSize = 6.5
        testModeLabel.fontColor = .yellow
        testModeLabel.horizontalAlignmentMode = .center
        testModeLabel.position = CGPoint(x: 256, y: 357)
        testModeLabel.zPosition = 121
        testModeLabel.isHidden = true
        addChild(testModeLabel)

        playerNode.update(from: player, dt: 0)
        gameState.zone = zoneNumber(for: currentLevelName)
        hud.update(state: gameState)
        updateTitleOverlayText()
        setGameplayNodesPaused(true)
        updateDebugText()
    }

    override func update(_ currentTime: TimeInterval) {
        if previousUpdateTime == 0 {
            previousUpdateTime = currentTime
            return
        }

        let frameTime = min(currentTime - previousUpdateTime, GameConstants.maximumFrameTime)
        previousUpdateTime = currentTime
        accumulator += frameTime

        while accumulator >= GameConstants.fixedTimeStep {
            fixedUpdate(dt: GameConstants.fixedTimeStep)
            accumulator -= GameConstants.fixedTimeStep
        }

        syncPlayerNodePosition()
        hud.update(state: gameState)
        updateDebugText()
        updateDebugOverlay()
    }

    func setGamepadStatus(_ text: String) {
        gamepadLabel.text = text
    }

    private func fixedUpdate(dt: TimeInterval) {
        let rawInput = inputState.snapshot()

        if inputState.consumePausePress() {
            if flowState == .playing || flowState == .respawning {
                enterPause(currentInput: rawInput)
            } else if flowState == .paused {
                leavePause(currentInput: rawInput)
            }
            return
        }

        switch flowState {
        case .title:
            let startJustPressed = rawInput.fire && !menuFireWasPressed
            menuFireWasPressed = rawInput.fire
            if startJustPressed {
                beginFromTitle(currentInput: rawInput)
            }
            return

        case .paused:
            let upJustPressed = rawInput.menuUp && !pauseMenuUpWasPressed
            let downJustPressed = rawInput.menuDown && !pauseMenuDownWasPressed
            pauseMenuUpWasPressed = rawInput.menuUp
            pauseMenuDownWasPressed = rawInput.menuDown

            if upJustPressed || downJustPressed {
                pauseSelectedIndex = pauseSelectedIndex == 0 ? 1 : 0
                updatePauseMenuText()
            }

            let confirmJustPressed = rawInput.fire && !pauseConfirmWasPressed
            pauseConfirmWasPressed = rawInput.fire
            if confirmJustPressed {
                if pauseSelectedIndex == 0 {
                    restartFromBeginning(currentInput: rawInput)
                } else {
                    testInvulnerabilityEnabled.toggle()
                    testModeLabel.isHidden = !testInvulnerabilityEnabled
                    updatePauseMenuText()
                }
            }
            return

        case .gameOver:
            let restartJustPressed = rawInput.fire && !menuFireWasPressed
            menuFireWasPressed = rawInput.fire
            if restartJustPressed {
                restartFromBeginning(currentInput: rawInput)
            }
            return

        case .contentComplete:
            let titleJustPressed = rawInput.fire && !menuFireWasPressed
            menuFireWasPressed = rawInput.fire
            if titleJustPressed {
                showTitleAfterContentComplete(currentInput: rawInput)
            }
            return

        case .playing, .playerDead, .respawning:
            break
        }

        if invulnerability > 0 {
            invulnerability = max(0, invulnerability - dt)
            if invulnerability == 0, flowState == .respawning {
                flowState = .playing
            }
        }

        let debugJustPressed = rawInput.debugHitboxes && !debugWasPressed
        debugWasPressed = rawInput.debugHitboxes
        if debugJustPressed {
            showHitboxes.toggle()
            stepLabel.isHidden = !showHitboxes
            inputLabel.isHidden = !showHitboxes
            gamepadLabel.isHidden = !showHitboxes
        }

        let jumpJustPressed = rawInput.jump && !sceneJumpWasPressed
        sceneJumpWasPressed = rawInput.jump
        var consumedUpInteraction = false

        if jumpJustPressed, !player.isDying {
            if currentLevel.changingRooms.contains(where: { $0.intersects(player.movementHitbox) }) {
                player.toggleExoskeleton()
                playerNode.update(from: player, dt: 0)
                showBanner(player.hasExoskeleton ? "EXOSKELETON ON" : "EXOSKELETON OFF")
                consumedUpInteraction = true
            } else if let destination = currentLevel.teleportDestination(for: player.movementHitbox) {
                let departure = player.position
                player.teleport(to: destination)
                createTeleportFlash(at: departure)
                createTeleportFlash(at: destination)
                consumedUpInteraction = true
            }
        }

        // UP is contextual in the original game. When a changing room or
        // teleport consumes it, do not also start a normal jump on the same
        // fixed step.
        if consumedUpInteraction {
            player.consumeContextualJumpPress()
        }

        let playerInput = consumedUpInteraction ? InputSnapshot(
            moveLeft: rawInput.moveLeft,
            moveRight: rawInput.moveRight,
            jump: false,
            crouch: rawInput.crouch,
            fire: rawInput.fire,
            grenade: rawInput.grenade,
            pause: rawInput.pause,
            menuUp: rawInput.menuUp,
            menuDown: rawInput.menuDown,
            debugHitboxes: rawInput.debugHitboxes
        ) : rawInput

        let previousPosition = player.position
        player.update(input: playerInput, dt: dt)

        let solids = currentLevel.solidRects
        for solid in solids where player.movementHitbox.intersects(solid) {
            player.resolveSolidCollision(previousPosition: previousPosition, solid: solid)
        }
        player.refreshGroundSupport(solids: solids)
        player.finalizeMotionState(input: playerInput)
        playerNode.update(from: player, dt: dt)

        if player.isDying {
            fireWasPressed = rawInput.fire
            grenadeWasPressed = rawInput.grenade
            updateDeathSequence(dt: dt)
        } else {
            deathGroundTimer = 0
            updateWeapons(input: rawInput)
        }

        updateBullets(dt: dt)
        updateGrenades(dt: dt)

        let newShots = currentLevel.fixedUpdate(dt: dt, player: player)
        for shot in newShots {
            enemyBullets.append(shot)
            addChild(shot.node)
        }

        updateEnemyBullets(dt: dt)
        updatePickups()
        let launcherBonus = currentLevel.collectDoubleLauncherBonus(playerBox: player.movementHitbox)
        if launcherBonus > 0 {
            awardPoints(launcherBonus)
            showBanner("+1000")
        }
        updateLethalEntities()
        updateExplosions(dt: dt)
        updateGrenadeTrail(dt: dt)

        if !player.isDying { checkScreenExit() }
    }

    private func updateDeathSequence(dt: TimeInterval) {
        guard player.isDying else { return }
        guard player.isGrounded else {
            deathGroundTimer = 0
            return
        }

        deathGroundTimer += dt
        guard deathGroundTimer >= 70.0 / 60.0 else { return }
        deathGroundTimer = 0

        gameState.lives = max(0, gameState.lives - 1)
        if gameState.lives == 0 {
            enterGameOver()
            return
        }

        // Original Exolon refills ammunition after a death and returns Vitorc
        // to the current screen entry point. Destroyed objects remain destroyed.
        gameState.ammo = GameState.startingAmmo
        gameState.grenades = GameState.startingGrenades
        player.finishDeathAndRespawn()
        invulnerability = GameConstants.postDeathProtectionDuration
        flowState = .respawning
        saveCheckpoint()
    }

    private func updateWeapons(input: InputSnapshot) {
        // User-selected modern scheme: FIRE and GRENADE are always separate.
        let fireJustPressed = input.fire && !fireWasPressed
        if fireJustPressed && gameState.ammo > 0 {
            let origin = player.blasterOrigin()
            let bullet = BlasterBullet(position: origin, direction: player.facing)
            bullets.append(bullet)
            addChild(bullet.node)
            if player.hasExoskeleton {
                let second = BlasterBullet(position: CGPoint(x: origin.x, y: origin.y + 12), direction: player.facing)
                bullets.append(second)
                addChild(second.node)
            }
            gameState.ammo -= 1
        }

        let grenadeJustPressed = input.grenade && !grenadeWasPressed
        if grenadeJustPressed && gameState.grenades > 0 && grenades.isEmpty {
            let grenade = Grenade(position: player.grenadeOrigin(), direction: player.facing, groundY: currentLevel.groundY)
            grenades.append(grenade)
            addChild(grenade.node)
            gameState.grenades -= 1
        }

        fireWasPressed = input.fire
        grenadeWasPressed = input.grenade
    }

    private func updateBullets(dt: TimeInterval) {
        for bullet in bullets {
            bullet.update(dt: dt)
            guard bullet.isAlive else { continue }

            // Double-launcher projectiles are destroyable by the blaster in
            // the original/reference game. Ordinary 4x4 turret shots are not.
            if let hostile = enemyBullets.first(where: {
                $0.isAlive && $0.canBeShotDown && bullet.hitbox.intersects($0.hitbox)
            }) {
                bullet.destroy()
                hostile.destroy()
                createBlasterExplosion(at: hostile.position)
                awardPoints(hostile.pointsWhenShotDown)
                continue
            }

            if let bubble = currentLevel.bubbles.first(where: { $0.isAlive && bullet.hitbox.intersects($0.hitbox) }) {
                bullet.destroy()
                bubble.destroy()
                awardPoints(bubble.points)
                createCircularExplosion(at: bubble.position)
                continue
            }

            if let egg = currentLevel.eggs.first(where: { $0.isAlive && bullet.hitbox.intersects($0.hitbox) }) {
                bullet.destroy()
                egg.destroy()
                awardPoints(egg.points)
                createBlasterExplosion(at: egg.position)
                continue
            }

            if let field = currentLevel.forceFields.first(where: { $0.isActive && bullet.hitbox.intersects($0.hitbox) }) {
                bullet.destroy()
                let destroyed = field.hitByBlaster()
                createBlasterExplosion(at: bullet.position)
                if destroyed { awardPoints(1_000) }
                continue
            }

            let hitIndestructible = currentLevel.turrets.contains {
                $0.isActive && bullet.hitbox.intersects($0.hitbox)
            } || currentLevel.destructibleObstacles.contains {
                $0.isActive && bullet.hitbox.intersects($0.hitbox)
            } || currentLevel.incubators.contains {
                $0.isActive && bullet.hitbox.intersects($0.hitbox)
            }

            if hitIndestructible || currentLevel.terrainRects.contains(where: { bullet.hitbox.intersects($0) }) {
                bullet.destroy()
                createBlasterExplosion(at: bullet.position)
            }
        }

        bullets = bullets.filter { bullet in
            if !bullet.isAlive { bullet.node.removeFromParent() }
            return bullet.isAlive
        }
    }

    private func updateGrenades(dt: TimeInterval) {
        for grenade in grenades {
            if let trailPosition = grenade.update(dt: dt) {
                let dot = GrenadeTrailDot(position: trailPosition, index: grenadeTrailIndex)
                grenadeTrailIndex += 1
                grenadeTrailDots.append(dot)
                addChild(dot)
            }
            guard grenade.isAlive else { continue }

            if let turret = currentLevel.turrets.first(where: {
                $0.isActive && grenade.hitbox.intersects($0.hitbox)
            }) {
                destroyWithGrenade(grenade, center: turret.center) { turret.destroy() }
                continue
            }

            if let obstacle = currentLevel.destructibleObstacles.first(where: {
                $0.isActive && grenade.hitbox.intersects($0.hitbox)
            }) {
                destroyWithGrenade(grenade, center: obstacle.center) { obstacle.destroy() }
                continue
            }

            if let incubator = currentLevel.incubators.first(where: {
                $0.isActive && grenade.hitbox.intersects($0.hitbox)
            }) {
                destroyWithGrenade(grenade, center: incubator.center) { incubator.destroy() }
                continue
            }

            if let guidanceHit = currentLevel.destroyMissileGuidanceIfHit(by: grenade.hitbox) {
                grenade.destroy()
                createCircularExplosion(at: grenade.position)
                createCircularExplosion(at: guidanceHit.center)
                for missilePosition in guidanceHit.missilePositions {
                    createCircularExplosion(at: missilePosition)
                }
                awardPoints(guidanceHit.points)
                continue
            }

            if currentLevel.terrainRects.contains(where: { grenade.hitbox.intersects($0) }) || grenade.hasHitGround() {
                grenade.destroy()
                createCircularExplosion(at: grenade.position)
            }
        }

        grenades = grenades.filter { grenade in
            if !grenade.isAlive { grenade.node.removeFromParent() }
            return grenade.isAlive
        }
    }

    private func destroyWithGrenade(_ grenade: Grenade, center: CGPoint, destroy: () -> Void) {
        guard grenade.isAlive else { return }
        grenade.destroy()
        createCircularExplosion(at: grenade.position)
        destroy()
        awardPoints(150)
        createCircularExplosion(at: center)
    }

    private func updateEnemyBullets(dt: TimeInterval) {
        for bullet in enemyBullets {
            bullet.update(dt: dt)
            guard bullet.isAlive else { continue }

            if currentLevel.destructibleObstacles.contains(where: {
                $0.isActive && bullet.hitbox.intersects($0.hitbox)
            }) {
                bullet.destroy()
                if bullet.kind == .doubleLauncher { createBlasterExplosion(at: bullet.position) }
                continue
            }

            if currentLevel.terrainRects.contains(where: { bullet.hitbox.intersects($0) }) {
                bullet.destroy()
                if bullet.kind == .doubleLauncher { createBlasterExplosion(at: bullet.position) }
                continue
            }

            if invulnerability <= 0 && !player.isDying && bullet.hitbox.intersects(player.damageHitbox) {
                bullet.destroy()
                if bullet.kind == .doubleLauncher { createBlasterExplosion(at: bullet.position) }
                hitPlayer()
            }
        }

        enemyBullets = enemyBullets.filter { bullet in
            if !bullet.isAlive { bullet.node.removeFromParent() }
            return bullet.isAlive
        }
    }

    private func updatePickups() {
        for pickup in currentLevel.grenadePacks where pickup.isActive {
            if player.movementHitbox.intersects(pickup.hitbox) {
                pickup.collect()
                gameState.grenades = 10
            }
        }

        for pickup in currentLevel.ammoPacks where pickup.isActive {
            if player.movementHitbox.intersects(pickup.hitbox) {
                pickup.collect()
                gameState.ammo = 99
            }
        }
    }

    private func updateLethalEntities() {
        if let missileHit = currentLevel.consumeGuidedMissileHit(playerBox: player.damageHitbox) {
            createCircularExplosion(at: missileHit)
            hitPlayer()
            if player.isDying { return }
        }

        for mine in currentLevel.mines where mine.isArmed {
            if player.hasExoskeleton { continue }
            if mine.triggerIfPlayerEnters(playerBox: player.movementHitbox) {
                createCircularExplosion(at: mine.center)
                if invulnerability <= 0 && !player.isDying {
                    hitPlayer()
                    return
                }
            }
        }

        for piston in currentLevel.pistons {
            if player.hasExoskeleton { continue }
            let box = piston.hitbox
            if box.width > 0,
               invulnerability <= 0,
               !player.isDying,
               player.damageHitbox.intersects(box) {
                hitPlayer()
                return
            }
        }

        if invulnerability <= 0, !player.isDying,
           currentLevel.forceFields.contains(where: { $0.isActive && $0.hitbox.intersects(player.damageHitbox) }) {
            hitPlayer()
            return
        }

        if invulnerability <= 0, !player.isDying,
           currentLevel.sourceHazards.contains(where: { !$0.isEmpty && $0.intersects(player.damageHitbox) }) {
            hitPlayer()
            return
        }

        for bubble in currentLevel.bubbles where bubble.isAlive {
            if player.damageHitbox.intersects(bubble.hitbox) {
                bubble.destroy()
                awardPoints(bubble.points)
                createCircularExplosion(at: bubble.position)
                hitPlayer()
                return
            }
        }

        for egg in currentLevel.eggs where egg.isAlive {
            if player.damageHitbox.intersects(egg.hitbox) {
                egg.destroy()
                awardPoints(egg.points)
                createBlasterExplosion(at: egg.position)
                hitPlayer()
                return
            }
        }
    }

    private func hitPlayer() {
        guard !testInvulnerabilityEnabled else { return }
        guard !player.isDying, invulnerability <= 0 else { return }
        player.beginDeath()
        flowState = .playerDead
        deathGroundTimer = 0
    }

    private func checkScreenExit() {
        guard player.position.x > 510 else { return }
        let next = currentLevel.nextLevelName
        applyOriginalStageBoundaryIfNeeded(completedZone: gameState.zone)

        guard !next.isEmpty, includedLevels.contains(next) else {
            enterContentComplete(nextLevelName: next)
            return
        }

        transition(to: next)
    }

    private func applyOriginalStageBoundaryIfNeeded(completedZone: Int) {
        // Original Exolon awards the lives bonus at the five 25-zone stage ends.
        // Our current content is still being extended through Step 9, so this is deliberately dormant
        // until later steps add Zones 024/049/074/099/124.
        guard [24, 49, 74, 99, 124].contains(completedZone) else { return }
        awardPoints(gameState.lives * 1_000)
        if gameState.lives < GameState.startingLives { gameState.lives += 1 }
        gameState.ammo = GameState.startingAmmo
        gameState.grenades = GameState.startingGrenades
    }

    private func transition(to levelName: String) {
        clearTransientObjects()
        currentLevel.rootNode.removeFromParent()

        currentLevelName = levelName
        let carriedY = player.position.y
        currentLevel = TMXLevelRuntime(resource: levelName)
        addChild(currentLevel.rootNode)
        gameState.zone = zoneNumber(for: levelName)
        let isStageStart = [0, 25, 50, 75, 100].contains(gameState.zone)
        let targetSpawn = isStageStart
            ? currentLevel.spawnCenter
            : CGPoint(x: currentLevel.spawnCenter.x, y: max(currentLevel.groundY + GameConstants.playerSpriteSize.height * 0.5, carriedY))
        player.configure(spawnCenter: targetSpawn, groundY: currentLevel.groundY)

        // Normal screen entry is not invulnerable in the original game.
        invulnerability = 0
        flowState = .playing
        deathGroundTimer = 0
        sceneJumpWasPressed = false
        fireWasPressed = inputState.snapshot().fire
        grenadeWasPressed = inputState.snapshot().grenade
        bannerLabel.text = ""
        stepLabel.text = "STEP 9 · \(levelName) · ZONE \(String(format: "%03d", gameState.zone))"
        saveCheckpoint()
    }

    private func awardPoints(_ value: Int) {
        guard value > 0 else { return }
        gameState.points = min(999_999, gameState.points + value)
        if gameState.points > gameState.highScore {
            gameState.highScore = gameState.points
            persistence.saveHighScore(gameState.highScore)
        }
    }

    private func showBanner(_ text: String) {
        bannerLabel.removeAllActions()
        bannerLabel.alpha = 1
        bannerLabel.text = text
        bannerLabel.run(.sequence([
            .wait(forDuration: 0.75),
            .fadeOut(withDuration: 0.20),
            .run { [weak self] in
                self?.bannerLabel.text = ""
                self?.bannerLabel.alpha = 1
            }
        ]))
    }

    // MARK: - Persistent checkpoint / flow

    private func loadPersistentState() {
        // Test-build policy: every new application launch starts at Zone 000.
        // High Score remains persistent, but a checkpoint from a previous process
        // is deliberately discarded. In-session respawn/progression is unchanged.
        gameState.highScore = persistence.loadHighScore()
        persistence.clearCheckpoint()
        hasSavedCheckpoint = false
        currentLevelName = "L01S01"
        gameState.resetForNewGame()
    }

    private func saveCheckpoint() {
        let checkpoint = GameCheckpoint(
            levelName: currentLevelName,
            ammo: gameState.ammo,
            grenades: gameState.grenades,
            points: gameState.points,
            lives: gameState.lives
        )
        persistence.saveCheckpoint(checkpoint)
        hasSavedCheckpoint = true
    }

    private func beginFromTitle(currentInput: InputSnapshot) {
        titleOverlay.isHidden = true
        flowState = .playing
        setGameplayNodesPaused(false)
        menuFireWasPressed = currentInput.fire
        fireWasPressed = currentInput.fire
        grenadeWasPressed = currentInput.grenade
        sceneJumpWasPressed = currentInput.jump
        if !hasSavedCheckpoint { saveCheckpoint() }
    }

    private func enterGameOver() {
        flowState = .gameOver
        invulnerability = 0
        persistence.clearCheckpoint()
        hasSavedCheckpoint = false
        if gameState.points > gameState.highScore {
            gameState.highScore = gameState.points
            persistence.saveHighScore(gameState.highScore)
        }
        setGameplayNodesPaused(true)
        showTerminalOverlay(
            title: "GAME OVER",
            line1: String(format: "SCORE %06d", gameState.points),
            line2: String(format: "HIGH SCORE %06d", gameState.highScore),
            hint: "SPACE / □ — RESTART"
        )
        menuFireWasPressed = inputState.snapshot().fire
    }

    private func enterContentComplete(nextLevelName: String) {
        flowState = .contentComplete
        saveCheckpoint()
        setGameplayNodesPaused(true)
        let nextText = nextLevelName.isEmpty ? "NEXT ZONE" : nextLevelName
        if gameState.zone >= 124 && nextLevelName.isEmpty {
            showTerminalOverlay(
                title: "FULL COMBAT ABILITY",
                line1: String(format: "SCORE %06d", gameState.points),
                line2: "ALL 125 ZONES COMPLETE",
                hint: "SPACE / □ — TITLE"
            )
        } else {
            showTerminalOverlay(
                title: "CONTENT COMPLETE",
                line1: String(format: "ZONE %03d", gameState.zone),
                line2: "CONTINUES WITH \(nextText)",
                hint: "SPACE / □ — TITLE"
            )
        }
        menuFireWasPressed = inputState.snapshot().fire
    }

    private func showTitleAfterContentComplete(currentInput: InputSnapshot) {
        terminalOverlay.isHidden = true
        titleOverlay.isHidden = false
        flowState = .title
        updateTitleOverlayText()
        menuFireWasPressed = currentInput.fire
    }

    // MARK: - Pause / restart / menus

    private func buildPauseOverlay() {
        pauseOverlay.zPosition = 1000
        pauseOverlay.isHidden = true

        addMenuShade(to: pauseOverlay)

        let panel = SKShapeNode(rectOf: CGSize(width: 300, height: 176), cornerRadius: 2)
        panel.position = CGPoint(x: 256, y: 200)
        panel.fillColor = .black
        panel.strokeColor = .white
        panel.lineWidth = 2
        panel.zPosition = 1
        pauseOverlay.addChild(panel)

        addMenuLabel("PAUSE", font: "Menlo-Bold", size: 19, color: .white, y: 254, to: pauseOverlay)

        let restart = SKLabelNode(fontNamed: "Menlo-Bold")
        restart.name = "pause-restart"
        restart.fontSize = 14
        restart.horizontalAlignmentMode = .center
        restart.verticalAlignmentMode = .center
        restart.position = CGPoint(x: 256, y: 213)
        restart.zPosition = 2
        pauseOverlay.addChild(restart)

        let invulnerable = SKLabelNode(fontNamed: "Menlo-Bold")
        invulnerable.name = "pause-invulnerability"
        invulnerable.fontSize = 12
        invulnerable.horizontalAlignmentMode = .center
        invulnerable.verticalAlignmentMode = .center
        invulnerable.position = CGPoint(x: 256, y: 184)
        invulnerable.zPosition = 2
        pauseOverlay.addChild(invulnerable)

        addMenuLabel("↑ / ↓  D-PAD — SELECT", font: "Menlo", size: 7, color: .white, y: 151, to: pauseOverlay)
        addMenuLabel("SPACE / □ — ACTIVATE", font: "Menlo", size: 7, color: .white, y: 137, to: pauseOverlay)
        addMenuLabel("P / OPTIONS — RESUME", font: "Menlo", size: 7, color: .white, y: 123, to: pauseOverlay)

        updatePauseMenuText()
    }

    private func updatePauseMenuText() {
        let restart = pauseOverlay.childNode(withName: "pause-restart") as? SKLabelNode
        let invulnerable = pauseOverlay.childNode(withName: "pause-invulnerability") as? SKLabelNode

        restart?.text = pauseSelectedIndex == 0 ? "> RESTART <" : "RESTART"
        restart?.fontColor = pauseSelectedIndex == 0 ? .yellow : .white

        let status = testInvulnerabilityEnabled ? "ON" : "OFF"
        invulnerable?.text = pauseSelectedIndex == 1
            ? "> INVULNERABILITY: \(status) <"
            : "INVULNERABILITY: \(status)"
        invulnerable?.fontColor = pauseSelectedIndex == 1 ? .yellow : .white
    }

    private func buildTitleOverlay() {
        titleOverlay.zPosition = 900
        titleOverlay.isHidden = false
        addMenuShade(to: titleOverlay)

        addMenuLabel("EXOLON", font: "Menlo-Bold", size: 30, color: .white, y: 244, to: titleOverlay)
        addMenuLabel("STEP 10", font: "Menlo-Bold", size: 11, color: .cyan, y: 214, to: titleOverlay)

        let status = SKLabelNode(fontNamed: "Menlo-Bold")
        status.name = "title-status"
        status.fontSize = 10
        status.fontColor = .yellow
        status.horizontalAlignmentMode = .center
        status.position = CGPoint(x: 256, y: 179)
        status.zPosition = 2
        titleOverlay.addChild(status)

        let high = SKLabelNode(fontNamed: "Menlo")
        high.name = "title-high-score"
        high.fontSize = 8
        high.fontColor = .white
        high.horizontalAlignmentMode = .center
        high.position = CGPoint(x: 256, y: 158)
        high.zPosition = 2
        titleOverlay.addChild(high)

        addMenuLabel("SPACE / □ — START", font: "Menlo", size: 8, color: .white, y: 128, to: titleOverlay)
    }

    private func buildTerminalOverlay() {
        terminalOverlay.zPosition = 950
        terminalOverlay.isHidden = true
        addMenuShade(to: terminalOverlay)

        for (name, y, font, size) in [
            ("terminal-title", CGFloat(226), "Menlo-Bold", CGFloat(20)),
            ("terminal-line1", CGFloat(190), "Menlo-Bold", CGFloat(10)),
            ("terminal-line2", CGFloat(170), "Menlo", CGFloat(8)),
            ("terminal-hint", CGFloat(132), "Menlo", CGFloat(8))
        ] {
            let label = SKLabelNode(fontNamed: font)
            label.name = name
            label.fontSize = size
            label.fontColor = name == "terminal-title" ? .white : (name == "terminal-line1" ? .yellow : .white)
            label.horizontalAlignmentMode = .center
            label.position = CGPoint(x: 256, y: y)
            label.zPosition = 2
            terminalOverlay.addChild(label)
        }
    }

    private func addMenuShade(to node: SKNode) {
        let shade = SKShapeNode(rectOf: GameConstants.logicalSize)
        shade.position = CGPoint(x: GameConstants.logicalSize.width * 0.5,
                                 y: GameConstants.logicalSize.height * 0.5)
        shade.fillColor = SKColor(calibratedWhite: 0.0, alpha: 0.82)
        shade.strokeColor = .clear
        shade.zPosition = 0
        node.addChild(shade)
    }

    private func addMenuLabel(_ text: String, font: String, size: CGFloat, color: SKColor, y: CGFloat, to node: SKNode) {
        let label = SKLabelNode(fontNamed: font)
        label.text = text
        label.fontSize = size
        label.fontColor = color
        label.horizontalAlignmentMode = .center
        label.verticalAlignmentMode = .center
        label.position = CGPoint(x: 256, y: y)
        label.zPosition = 2
        node.addChild(label)
    }

    private func updateTitleOverlayText() {
        let status = titleOverlay.childNode(withName: "title-status") as? SKLabelNode
        status?.text = hasSavedCheckpoint
            ? String(format: "CONTINUE · ZONE %03d", gameState.zone)
            : "NEW GAME · ZONE 000"

        let high = titleOverlay.childNode(withName: "title-high-score") as? SKLabelNode
        high?.text = String(format: "HIGH SCORE %06d", gameState.highScore)
    }

    private func showTerminalOverlay(title: String, line1: String, line2: String, hint: String) {
        terminalOverlay.childNode(withName: "terminal-title").map { ($0 as? SKLabelNode)?.text = title }
        terminalOverlay.childNode(withName: "terminal-line1").map { ($0 as? SKLabelNode)?.text = line1 }
        terminalOverlay.childNode(withName: "terminal-line2").map { ($0 as? SKLabelNode)?.text = line2 }
        terminalOverlay.childNode(withName: "terminal-hint").map { ($0 as? SKLabelNode)?.text = hint }
        terminalOverlay.isHidden = false
    }

    private func enterPause(currentInput: InputSnapshot) {
        guard flowState == .playing || flowState == .respawning else { return }
        stateBeforePause = flowState
        flowState = .paused
        pauseOverlay.isHidden = false
        pauseSelectedIndex = 0
        pauseConfirmWasPressed = currentInput.fire
        pauseMenuUpWasPressed = currentInput.menuUp
        pauseMenuDownWasPressed = currentInput.menuDown
        updatePauseMenuText()
        setGameplayNodesPaused(true)
    }

    private func leavePause(currentInput: InputSnapshot) {
        guard flowState == .paused else { return }
        flowState = stateBeforePause
        pauseOverlay.isHidden = true
        setGameplayNodesPaused(false)

        fireWasPressed = currentInput.fire
        grenadeWasPressed = currentInput.grenade
        sceneJumpWasPressed = currentInput.jump
        pauseConfirmWasPressed = currentInput.fire
        pauseMenuUpWasPressed = currentInput.menuUp
        pauseMenuDownWasPressed = currentInput.menuDown
    }

    private func setGameplayNodesPaused(_ paused: Bool) {
        for child in children where child !== pauseOverlay && child !== titleOverlay && child !== terminalOverlay {
            child.isPaused = paused
        }
    }

    private func restartFromBeginning(currentInput: InputSnapshot) {
        persistence.clearCheckpoint()
        hasSavedCheckpoint = false
        clearTransientObjects()
        currentLevel.rootNode.removeFromParent()

        currentLevelName = "L01S01"
        currentLevel = TMXLevelRuntime(resource: currentLevelName)
        addChild(currentLevel.rootNode)

        gameState.resetForNewGame()
        gameState.highScore = persistence.loadHighScore()

        player.setExoskeleton(false)
        player.configure(spawnCenter: currentLevel.spawnCenter, groundY: currentLevel.groundY)
        playerNode.update(from: player, dt: 0)
        invulnerability = 0
        deathGroundTimer = 0
        flowState = .playing
        stateBeforePause = .playing
        bannerLabel.text = ""

        pauseOverlay.isHidden = true
        titleOverlay.isHidden = true
        terminalOverlay.isHidden = true
        setGameplayNodesPaused(false)
        pauseConfirmWasPressed = currentInput.fire
        pauseMenuUpWasPressed = currentInput.menuUp
        pauseMenuDownWasPressed = currentInput.menuDown
        menuFireWasPressed = currentInput.fire
        fireWasPressed = currentInput.fire
        grenadeWasPressed = currentInput.grenade
        sceneJumpWasPressed = currentInput.jump
        debugWasPressed = currentInput.debugHitboxes
        stepLabel.text = "STEP 9 · L01S01 · ZONE 000"
        saveCheckpoint()
    }

    private func zoneNumber(for levelName: String) -> Int {
        // L01S01...L05S25 map exactly to original zones 000...124.
        let pattern = #"^L(\d{2})S(\d{2})$"#
        guard let regex = try? NSRegularExpression(pattern: pattern),
              let match = regex.firstMatch(in: levelName, range: NSRange(levelName.startIndex..., in: levelName)),
              let stageRange = Range(match.range(at: 1), in: levelName),
              let screenRange = Range(match.range(at: 2), in: levelName),
              let stage = Int(levelName[stageRange]), let screen = Int(levelName[screenRange]) else { return 0 }
        return max(0, min(124, (stage - 1) * 25 + (screen - 1)))
    }

    private func clearTransientObjects() {
        for bullet in bullets { bullet.node.removeFromParent() }
        for grenade in grenades { grenade.node.removeFromParent() }
        for bullet in enemyBullets { bullet.node.removeFromParent() }
        for explosion in explosions { explosion.removeFromParent() }
        for dot in grenadeTrailDots { dot.removeFromParent() }
        bullets.removeAll()
        grenades.removeAll()
        enemyBullets.removeAll()
        explosions.removeAll()
        grenadeTrailDots.removeAll()
    }

    private func createBlasterExplosion(at position: CGPoint) {
        let effect = ExplosionEffect.blaster(at: position)
        explosions.append(effect)
        addChild(effect)
    }

    private func createCircularExplosion(at position: CGPoint) {
        let effect = ExplosionEffect.circular(at: position)
        explosions.append(effect)
        addChild(effect)
    }

    private func createTeleportFlash(at position: CGPoint) {
        let flash = SKShapeNode(circleOfRadius: 18)
        flash.position = position
        flash.strokeColor = .cyan
        flash.lineWidth = 3
        flash.fillColor = .clear
        flash.zPosition = 180
        flash.setScale(0.35)
        addChild(flash)

        let grow = SKAction.scale(to: 1.6, duration: 0.16)
        let fade = SKAction.fadeOut(withDuration: 0.16)
        flash.run(SKAction.sequence([SKAction.group([grow, fade]), SKAction.removeFromParent()]))
    }

    private func updateExplosions(dt: TimeInterval) {
        var active: [ExplosionEffect] = []
        for explosion in explosions where explosion.fixedUpdate(dt: dt) {
            active.append(explosion)
        }
        explosions = active
    }

    private func updateGrenadeTrail(dt: TimeInterval) {
        var active: [GrenadeTrailDot] = []
        for dot in grenadeTrailDots where dot.fixedUpdate(dt: dt) {
            active.append(dot)
        }
        grenadeTrailDots = active
    }

    private func syncPlayerNodePosition() {
        playerNode.position = player.position
        // The original post-death protection timer is not used by the sprite
        // renderer, so it should not create artificial alpha blinking.
        playerNode.alpha = 1.0
    }

    private func updateDebugText() {
        let state = inputState.snapshot()
        var active: [String] = []
        if state.moveLeft { active.append("LEFT") }
        if state.moveRight { active.append("RIGHT") }
        if state.jump { active.append("JUMP") }
        if state.crouch { active.append("CROUCH") }
        if state.fire { active.append("FIRE") }
        if state.grenade { active.append("GRENADE") }
        let inputText = active.isEmpty ? "INPUT: —" : "INPUT: " + active.joined(separator: "+")
        inputLabel.text = inputText + " · STATE: " + flowState.rawValue.uppercased()
    }

    private func updateDebugOverlay() {
        debugOverlay.removeAllChildren()
        guard showHitboxes else { return }

        addDebugRect(player.movementHitbox, color: .green)
        addDebugRect(player.damageHitbox, color: .red)
        for rect in currentLevel.terrainRects { addDebugRect(rect, color: .blue, alpha: 0.25) }

        for turret in currentLevel.turrets where turret.isActive {
            addDebugRect(turret.hitbox, color: .cyan)
            let dot = SKShapeNode(circleOfRadius: 2)
            dot.fillColor = .yellow
            dot.strokeColor = .yellow
            dot.position = turret.muzzle
            debugOverlay.addChild(dot)
        }

        for obstacle in currentLevel.destructibleObstacles where obstacle.isActive {
            addDebugRect(obstacle.hitbox, color: .cyan, alpha: 0.6)
        }
        for portal in currentLevel.portals {
            addDebugRect(portal.visualBounds, color: .cyan, alpha: 0.45)
            addDebugRect(portal.interactionRect, color: .magenta)
        }
        for field in currentLevel.forceFields where field.isActive {
            addDebugRect(field.hitbox, color: .cyan, alpha: 0.35)
        }
        for piston in currentLevel.pistons {
            let box = piston.hitbox
            if box.width > 0 { addDebugRect(box, color: .orange) }
        }
        for bubble in currentLevel.bubbles where bubble.isAlive {
            addDebugRect(bubble.hitbox, color: .yellow)
        }
        for incubator in currentLevel.incubators where incubator.isActive {
            addDebugRect(incubator.hitbox, color: .cyan, alpha: 0.7)
        }
        for egg in currentLevel.eggs where egg.isAlive {
            addDebugRect(egg.hitbox, color: .magenta)
        }
        for bullet in enemyBullets where bullet.isAlive { addDebugRect(bullet.hitbox, color: .yellow) }
        for bullet in bullets where bullet.isAlive { addDebugRect(bullet.hitbox, color: .magenta) }
        for grenade in grenades where grenade.isAlive { addDebugRect(grenade.hitbox, color: .white) }
    }

    private func addDebugRect(_ rect: CGRect, color: SKColor, alpha: CGFloat = 0.9) {
        guard rect.width > 0, rect.height > 0 else { return }
        let path = CGPath(rect: rect, transform: nil)
        let node = SKShapeNode(path: path)
        node.strokeColor = color
        node.lineWidth = 1
        node.alpha = alpha
        node.fillColor = .clear
        debugOverlay.addChild(node)
    }
}
