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

    /// Gameplay event sink. Injected by the composition root (`AppDelegate`); the default
    /// `NullGameplayEventSink` keeps every construction path that does not inject behave exactly
    /// as before this change (architect ruling D3).
    var events: any GameplayEventSink = NullGameplayEventSink.shared {
        didSet {
            currentLevel?.events = events
            player.events = events
            // The driver owns tick/frame/heartbeat numbering; binding it here (rather than
            // snapshotting at init) is what keeps `tick` from sticking at 0 in a non-empty file.
            tickDriver.useSink(events)
        }
    }

    /// Fixed-step accumulator loop, P1-9 (extracted so the Linux gate runs the real arithmetic).
    /// Created eagerly and bound through `events.didSet`, never lazily against a stale sink.
    private let tickDriver = FixedTickDriver()

    /// P1-8: one stage-boundary award per completed zone per playthrough, with a visible witness
    /// for every suppressed repeat.
    private let stageBoundaries = StageBoundaryLedger()

    /// Per-tick input snapshot, diffed to emit `input.action_edge` from inside the loop.
    private var previousTickInput: InputSnapshot?
    /// Held duration per action in fixed steps, indexed by `GameplayWire.code(action)`. The array
    /// is allocated once; updating it never allocates, which keeps the tick path cheap.
    private var heldStepsByAction = [Int32](repeating: 0, count: 10)
    private static let trackedActions: [GameAction] = GameAction.allCases
    private static let actionProjections: [(InputSnapshot) -> Bool] = [
        { $0.moveLeft }, { $0.moveRight }, { $0.jump }, { $0.crouch }, { $0.fire },
        { $0.grenade }, { $0.pause }, { $0.menuUp }, { $0.menuDown }, { $0.debugHitboxes }
    ]

    /// Cause carried to the `flowState` observer, which is the single emission site for
    /// `state.flow` (integration section 11-2: one edit, cannot drift from the 11 assignment sites).
    private var pendingFlowCause: GameplayFlowCause = .unspecified
    /// Reused F1 hitbox-window node (task 10): never rebuilt per frame.
    private var eventTailLabel: SKLabelNode?
    private var renderedFramesSinceTailUpdate = 0

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
    private var flowState: GameFlowState = .title {
        didSet {
            guard flowState != oldValue else { return }
            let cause = pendingFlowCause
            pendingFlowCause = .unspecified
            emitFlow(from: oldValue, to: flowState, cause: cause)
        }
    }
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

    // P1-9 note: the frame-time reference and the accumulator used to live here and were never
    // reset on a zone swap. They are `FixedTickDriver` state now.

    private let includedLevels: Set<String> = Set((1...5).flatMap { stage in (1...25).map { String(format: "L%02dS%02d", stage, $0) } })

    override func didMove(to view: SKView) {
        backgroundColor = .black
        anchorPoint = CGPoint(x: 0, y: 0)

        player.events = events
        loadPersistentState()
        emitCheckpointCleared(reason: .launch)
        emitZoneLoad(cause: .appLaunch)
        currentLevel = TMXLevelRuntime(resource: currentLevelName)
        currentLevel.events = events
        addChild(currentLevel.rootNode)
        player.configure(spawnCenter: currentLevel.spawnCenter, groundY: currentLevel.groundY)
        emitZoneLoaded(carriedY: false)
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

        // One reused label for the log tail (architect section 5.3): never a node per event, and
        // never rebuilt - only its text changes, at most every 10th rendered frame.
        let tail = SKLabelNode(fontNamed: "Menlo")
        tail.fontSize = 5
        tail.lineSpacing = 1
        tail.horizontalAlignmentMode = .left
        tail.verticalAlignmentMode = .top
        tail.position = CGPoint(x: 8, y: 364)
        tail.zPosition = 120
        tail.isHidden = true
        addChild(tail)
        eventTailLabel = tail

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
        emitTitleEnter()
        setGameplayNodesPaused(true)
        updateDebugText()
        #if DEBUG
        applyDebugWarpIfNeeded(environment: ProcessInfo.processInfo.environment)
        #endif
    }

    #if DEBUG
    /// Owner gate ruling 4 of change 20260924-...-8341b7: a **bounded** debug warp that puts the
    /// player at a named zone so a stage-end observation (probe item E16, the bravery latch, the
    /// timed ladder) does not cost an 11-minute real walk on a machine the project does not own.
    ///
    /// Three properties, each of them checked by `stage_boundary_check.py::warp_debug_only`:
    ///  * **Debug-only by compilation.** The whole feature - declaration, call site and parsing -
    ///    lives inside `#if DEBUG`, so it is absent from a Release binary rather than merely
    ///    disabled at runtime. `SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG` is declared in the
    ///    project-level Debug configuration, because the absence of that line would make the gate
    ///    accidental rather than stated.
    ///  * **Inert when unset.** No variable, no jump, no output.
    ///  * **Bounded target.** The value must be exactly one of the 125 level names the game itself
    ///    ships (`includedLevels`), so a typo is reported and ignored, and no caller-supplied
    ///    string can ever reach `TMXLevelRuntime(resource:)`. Anything else is refused on stderr.
    ///
    /// The jump goes through the real `transition(to:)`, which is what makes it a valid
    /// observation: P1-9's accumulator discard, the zone record, the checkpoint write, the
    /// `isStageStart` spawn rule and - since wave D - the stage clock the timed ladder measures
    /// against are all the production ones. The scene is then restored to exactly the state the
    /// launch code produced (title up, gameplay paused), because the warp is an observation aid
    /// and not a flow change: pressing FIRE continues from the warped zone.
    static func debugWarpTarget(environment: [String: String], allowed: Set<String>) -> String? {
        guard let raw = environment["EXOLON_DEBUG_WARP"] else { return nil }
        let target = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard target.count == 6, target.hasPrefix("L"),
              allowed.contains(target) else { return nil }
        return target
    }

    private func applyDebugWarpIfNeeded(environment: [String: String]) {
        guard environment["EXOLON_DEBUG_WARP"] != nil else { return }
        guard let target = GameScene.debugWarpTarget(environment: environment,
                                                    allowed: includedLevels) else {
            fputs("EXOLON_DEBUG_WARP ignored: the value must be one of the shipped level "
                  + "names, format LxxSyy\n", stderr)
            return
        }
        let flowBefore = flowState
        fputs("EXOLON_DEBUG_WARP=\(target) at step \(tickDriver.stepCount) via transition(to:)\n",
              stderr)
        transition(to: target)
        flowState = flowBefore
        setGameplayNodesPaused(true)
        stepLabel.text = "STEP 9 · \(target) · ZONE \(String(format: "%03d", gameState.zone))"
        hud.update(state: gameState)
        updateTitleOverlayText()
        updateDebugText()
    }
    #endif

    override func update(_ currentTime: TimeInterval) {
        // P1-9: the clamp, the accumulator, the 15-step budget and the catch-up loop now live in
        // `FixedTickDriver`, which is SpriteKit-free and therefore regression-testable on Linux.
        // The first call only records the reference time, so `frame` 0 carries no simulated step.
        guard tickDriver.beginFrame(currentTime: currentTime) else { return }
        events.beginFrame()

        while tickDriver.beginStep(zone: gameState.zone) {
            fixedUpdate(dt: GameConstants.fixedTimeStep)
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
        // Edges come from the per-tick snapshot diff, never from `InputState.set`: a press that
        // opens and closes between two steps would otherwise be stamped with the wrong tick
        // (integration section 9).
        emitInputEdges(current: rawInput)

        if inputState.consumePausePress() {
            // Only the consumption itself is a fact worth a record; polling `false` every step
            // would be a per-frame heartbeat by another name.
            events.emitPausePressConsumed()
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
                    events.emitCheatInvulnerability(enabled: testInvulnerabilityEnabled,
                                                   menuIndex: pauseSelectedIndex)
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
            if invulnerability == 0 {
                if flowState == .respawning {
                    changeFlow(to: .playing, cause: .respawnTimeout)
                }
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
                player.toggleExoskeleton(cause: .changingRoom)
                // P1-10 bravery latch (`ORIGINAL_MECHANICS.md:142`, owner ruling): this is the one
                // activation site, so the edge is recorded here rather than polled from
                // `hasExoskeleton` at the boundary - polling cannot see a suit that was put on and
                // taken off again inside the same stage, and the norm is about *having taken* it.
                if player.hasExoskeleton {
                    stageBoundaries.noteExoskeletonActivated(atStep: tickDriver.stepCount)
                }
                playerNode.update(from: player, dt: 0)
                showBanner(player.hasExoskeleton ? "EXOSKELETON ON" : "EXOSKELETON OFF")
                consumedUpInteraction = true
                emitContextualConsumed(kind: .changingRoom, jumpSuppressed: rawInput.jump)
            } else if let destination = currentLevel.teleportDestination(for: player.movementHitbox) {
                let departure = player.position
                // `jump_latch_held` is the physically-held UP at the consume: the precondition
                // P1-4 needs. `Player.teleport` then arms the latch, which is what
                // `input.contextual_consumed.jump_suppressed` reports as suppressed.
                let upHeldThroughTeleport = rawInput.jump
                player.teleport(to: destination.center)
                events.emitTeleport(from: departure, to: destination.center,
                                    portalIndex: destination.portalIndex, jumpLatchHeld: upHeldThroughTeleport)
                createTeleportFlash(at: departure)
                createTeleportFlash(at: destination.center)
                consumedUpInteraction = true
                emitContextualConsumed(kind: .teleport, jumpSuppressed: upHeldThroughTeleport)
            }
        }

        // UP is contextual in the original game. When a changing room or
        // teleport consumes it, do not also start a normal jump on the same
        // fixed step. P1-4: the consume now also holds the Player-side edge latch
        // until the key is physically released, so the *next* step cannot turn the
        // same press into a jump.
        if consumedUpInteraction {
            player.consumeContextualJumpPress()
        }

        // P1-4: the scene used to hand Player a one-step `jump: false` mask. That mask is what
        // made the leak possible - Player re-sampled the physical state on the *next* step and
        // turned the same press into a jump. `Player.consumeContextualJumpPress()` now holds the
        // edge until the key is actually released, so the real snapshot goes through unchanged and
        // the same step is still guarded (the latch was set before this call).
        let previousPosition = player.position
        player.update(input: rawInput, dt: dt)

        let solids = currentLevel.solidRects
        for solid in solids where player.movementHitbox.intersects(solid) {
            player.resolveSolidCollision(previousPosition: previousPosition, solid: solid)
        }
        player.refreshGroundSupport(solids: solids)
        player.finalizeMotionState(input: rawInput)
        playerNode.update(from: player, dt: dt)
        emitMotion()

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
        if let payout = currentLevel.collectDoubleLauncherBonus(playerBox: player.movementHitbox) {
            awardPoints(payout.points, reason: .launcher)
            events.emitDoubleLauncherBonus(points: payout.points, launcherObjectID: payout.objectID,
                                           at: launcherOrigin(of: payout), launcherActiveAfter: payout.launcherActiveAfter)
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

        if deathGroundTimer == 0 {
            // First grounded step of the death slide: the record the settle delay counts from.
            emitDeathLanded(groundTicks: 0)
        }
        deathGroundTimer += dt
        guard deathGroundTimer >= GameConstants.deathSettleDelay else { return }
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
        changeFlow(to: .respawning, cause: .death)
        saveCheckpoint()
        // After the save, so `checkpoint_saved` reports what the settle actually persisted.
        emitDeathSettled(livesBefore: gameState.lives + 1, livesAfter: gameState.lives)
    }

    private func updateWeapons(input: InputSnapshot) {
        // User-selected modern scheme: FIRE and GRENADE are always separate.
        // No early `return` anywhere below: the fire/grenade latches at the end of this function
        // must update on every step, exactly as before the log existed.
        let fireJustPressed = input.fire && !fireWasPressed
        if fireJustPressed {
            if gameState.ammo > 0 {
                let ammoBefore = gameState.ammo
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
                events.emitBlasterShot(origin: origin, facing: player.facing, double: player.hasExoskeleton,
                                       ammoBefore: ammoBefore, ammoAfter: gameState.ammo)
            } else {
                events.emitShootDenied(.noAmmo, ammo: gameState.ammo)
            }
        }

        let grenadeJustPressed = input.grenade && !grenadeWasPressed
        if grenadeJustPressed, gameState.grenades > 0 {
            // `blocked_by` is the one-in-flight rule of the original, which the pre-change guard
            // expressed as a single condition. Splitting it keeps the behavior and names the cause.
            let blocked = !grenades.isEmpty
            let grenadesBefore = gameState.grenades
            if blocked {
                events.emitGrenadeThrow(origin: player.grenadeOrigin(), direction: player.facing,
                                        grenadesBefore: grenadesBefore, grenadesAfter: grenadesBefore,
                                        blockedByOneInFlight: true)
            } else {
                let grenade = Grenade(position: player.grenadeOrigin(), direction: player.facing, groundY: currentLevel.groundY)
                grenades.append(grenade)
                addChild(grenade.node)
                gameState.grenades -= 1
                events.emitGrenadeThrow(origin: grenade.position, direction: player.facing,
                                        grenadesBefore: grenadesBefore, grenadesAfter: gameState.grenades,
                                        blockedByOneInFlight: false)
            }
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
                awardPoints(hostile.pointsWhenShotDown, reason: .blasterShotdown)
                continue
            }

            if let bubble = currentLevel.bubbles.first(where: { $0.isAlive && bullet.hitbox.intersects($0.hitbox) }) {
                bullet.destroy()
                bubble.destroy()
                awardPoints(bubble.points, reason: .bubble)
                createCircularExplosion(at: bubble.position)
                continue
            }

            if let egg = currentLevel.eggs.first(where: { $0.isAlive && bullet.hitbox.intersects($0.hitbox) }) {
                bullet.destroy()
                egg.destroy()
                awardPoints(egg.points, reason: .egg)
                createBlasterExplosion(at: egg.position)
                continue
            }

            if let field = currentLevel.forceFields.first(where: { $0.isActive && bullet.hitbox.intersects($0.hitbox) }) {
                bullet.destroy()
                let destroyed = field.hitByBlaster()
                createBlasterExplosion(at: bullet.position)
                if destroyed { awardPoints(1_000, reason: .forceField) }
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
                awardPoints(guidanceHit.points, reason: .guidance)
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
        awardPoints(150, reason: .grenadeKill)
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
                hitPlayer(cause: .bullet, at: bullet.position)
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
                let before = gameState.grenades
                // `ORIGINAL_MECHANICS.md:107-109`: a refill to exactly 10, not an additive pickup.
                // The same number is restored at death and at the stage boundary, so it lives in
                // `GameState` once; a literal here was free to drift from the two other sites
                // (wave D / P1-10 shared-constant ruling).
                gameState.grenades = GameState.startingGrenades
                emitPickup(kind: .grenadePack, countBefore: before, countAfter: gameState.grenades,
                           at: pickup.hitbox.origin)
            }
        }

        for pickup in currentLevel.ammoPacks where pickup.isActive {
            if player.movementHitbox.intersects(pickup.hitbox) {
                pickup.collect()
                let before = gameState.ammo
                gameState.ammo = GameState.startingAmmo
                emitPickup(kind: .ammoPack, countBefore: before, countAfter: gameState.ammo, at: pickup.hitbox.origin)
            }
        }
    }

    private func updateLethalEntities() {
        if let missileHit = currentLevel.consumeGuidedMissileHit(playerBox: player.damageHitbox) {
            createCircularExplosion(at: missileHit)
            hitPlayer(cause: .missile, at: missileHit)
            if player.isDying { return }
        }

        for mine in currentLevel.mines where mine.isArmed {
            if player.hasExoskeleton { continue }
            if mine.triggerIfPlayerEnters(playerBox: player.movementHitbox) {
                createCircularExplosion(at: mine.center)
                if invulnerability <= 0 && !player.isDying {
                    hitPlayer(cause: .mine, at: mine.center)
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
                hitPlayer(cause: .piston, at: CGPoint(x: box.midX, y: box.midY))
                return
            }
        }

        if invulnerability <= 0, !player.isDying,
           currentLevel.forceFields.contains(where: { $0.isActive && $0.hitbox.intersects(player.damageHitbox) }) {
            hitPlayer(cause: .forceField, at: player.position)
            return
        }

        if invulnerability <= 0, !player.isDying,
           currentLevel.sourceHazards.contains(where: { !$0.isEmpty && $0.intersects(player.damageHitbox) }) {
            hitPlayer(cause: .sourceHazard, at: player.position)
            return
        }

        for bubble in currentLevel.bubbles where bubble.isAlive {
            if player.damageHitbox.intersects(bubble.hitbox) {
                bubble.destroy()
                awardPoints(bubble.points, reason: .bubble)
                createCircularExplosion(at: bubble.position)
                hitPlayer(cause: .bubble, at: bubble.position)
                return
            }
        }

        for egg in currentLevel.eggs where egg.isAlive {
            if player.damageHitbox.intersects(egg.hitbox) {
                egg.destroy()
                awardPoints(egg.points, reason: .egg)
                createBlasterExplosion(at: egg.position)
                hitPlayer(cause: .egg, at: egg.position)
                return
            }
        }
    }

    /// Every lethal path funnels through here, so this is where the hit and the swallowed hit
    /// become records (architect section 5: `hitPlayer` is a choke point).
    private func hitPlayer(cause: GameplayDamageCause, at position: CGPoint) {
        if testInvulnerabilityEnabled {
            emitBlockedHit(cause: cause, testInvulnerability: true)
            return
        }
        if player.isDying || invulnerability > 0 {
            emitBlockedHit(cause: cause, testInvulnerability: false)
            return
        }
        emitPlayerHit(cause: cause, at: position, stateBefore: flowState)
        player.beginDeath()
        changeFlow(to: .playerDead, cause: .death)
        emitDeathBegin()
        deathGroundTimer = 0
    }

    private func checkScreenExit() {
        guard player.position.x > 510 else { return }
        let next = currentLevel.nextLevelName
        let playableNext = !next.isEmpty && includedLevels.contains(next)
        events.emitZoneExit(triggerX: GameConstants.screenExitX, playerX: player.position.x,
                            hasPlayableNextLevel: playableNext)
        applyOriginalStageBoundaryIfNeeded(completedZone: gameState.zone)

        guard playableNext else {
            enterContentComplete(nextLevelName: next)
            return
        }

        transition(to: next)
    }

    /// P1-8 (audit 2026-09-20, issue #12; architecture.md -> Decisions 3).
    ///
    /// The old body had no idempotency flag, and because `enterContentComplete` keeps the player
    /// parked past x=510 with the checkpoint persisted, the zone-124 title loop re-awarded
    /// `lives * 1000` on every FIRE cycle (750 awards in the 600 s probe). `StageBoundaryLedger`
    /// now owns the once-per-playthrough rule per award component, and every suppressed repeat is
    /// witnessed by `bonus.stage_boundary_suppressed` instead of being silent.
    ///
    /// The old "deliberately dormant until later steps add Zones 024/049/074/099/124" comment was
    /// stale: all 125 zones ship since Step 9, so the guard was live and farmable.
    ///
    /// Wave D (P1-10, owner gate rulings 2/3/4) completes the clause list in the **ledger**, not
    /// here: the scene still only samples the trigger, applies what the ledger decided and
    /// witnesses it. The two things this function owns are the observation the ledger cannot have -
    /// the fixed-step coordinate the timed ladder is measured against - and the exoskeleton clear,
    /// which is a player mutation and therefore must not move into a Foundation-only ledger.
    private func applyOriginalStageBoundaryIfNeeded(completedZone: Int) {
        let outcome = stageBoundaries.outcome(zone: completedZone,
                                             lives: gameState.lives,
                                             maxLives: GameConstants.maxLives,
                                             startingAmmo: GameState.startingAmmo,
                                             startingGrenades: GameState.startingGrenades,
                                             context: stageBoundaries.context(atStep: tickDriver.stepCount),
                                             awardSequence: GameplayStageComponentSequence.waveD)
        switch outcome {
        case .notApplicable:
            return
        case .suppressed(_, let reason):
            events.emitStageBoundarySuppressed(reason)
        case let .awarded(award):
            // Award is computed against the lives the player still holds; the +1 is applied after,
            // which is the order `ORIGINAL_MECHANICS.md:141-144` lists and the order the
            // lives_x1000 identity is asserted in (`stage_boundary_check.py`).
            awardPoints(award.points, reason: .stageBoundary)
            if award.refillsAmmoAndGrenades {
                gameState.lives = award.livesAfter
                gameState.ammo = award.startingAmmo
                gameState.grenades = award.startingGrenades
            }
            if award.clearsExoskeleton {
                // `:145`/`:117`. A cause-carrying transition, so the clear is on the wire and is
                // distinguishable from a restart or a cheat; the bravery latch survives it (the
                // latch is cleared only when the next stage begins).
                player.setExoskeleton(false, cause: .stageBoundary)
                playerNode.update(from: player, dt: 0)
            }
            emitStageBoundary(award: award)
        }
    }

    private func transition(to levelName: String) {
        // P1-9 witness, recorded while the log's zone lane still names the outgoing zone.
        emitZoneTransition(to: levelName)
        // P1-9 fix: discard the accumulator remainder so no step of the catch-up budget can run
        // in the new zone inside the render frame that transitioned (architecture.md -> Decisions 4).
        // `tick`/`frame` are process-global and are deliberately not touched; neither is the
        // driver's frame reference, because zeroing it would hand the next frame a paused-size delta.
        tickDriver.reset(reason: .zoneTransition)

        clearTransientObjects()
        currentLevel.rootNode.removeFromParent()

        currentLevelName = levelName
        let carriedY = player.position.y
        emitZoneLoad(cause: .transition)
        currentLevel = TMXLevelRuntime(resource: levelName)
        currentLevel.events = events
        addChild(currentLevel.rootNode)
        gameState.zone = zoneNumber(for: levelName)
        let isStageStart = [0, 25, 50, 75, 100].contains(gameState.zone)
        if isStageStart {
            // P1-10: the timed ladder and the bravery latch are both measured from here, so the
            // coordinate is the *stage*, not the playthrough (the suit persists through deaths
            // until the stage end, `ORIGINAL_MECHANICS.md:115`). Recorded after the outgoing
            // boundary was already awarded and witnessed by `checkScreenExit`, so a stage-end
            // trigger can never consume the next stage's clock.
            stageBoundaries.noteStageStarted(atStep: tickDriver.stepCount)
        }
        let targetSpawn = isStageStart
            ? currentLevel.spawnCenter
            : CGPoint(x: currentLevel.spawnCenter.x, y: max(currentLevel.groundY + GameConstants.playerSpriteSize.height * 0.5, carriedY))
        player.configure(spawnCenter: targetSpawn, groundY: currentLevel.groundY)
        emitZoneLoaded(carriedY: !isStageStart)

        // Normal screen entry is not invulnerable in the original game.
        invulnerability = 0
        changeFlow(to: .playing, cause: .zoneTransition)
        deathGroundTimer = 0
        sceneJumpWasPressed = false
        fireWasPressed = inputState.snapshot().fire
        grenadeWasPressed = inputState.snapshot().grenade
        bannerLabel.text = ""
        stepLabel.text = "STEP 9 · \(levelName) · ZONE \(String(format: "%03d", gameState.zone))"
        saveCheckpoint()
    }

    /// The only points funnel in the game (10 call sites), so `score.awarded` has one emission
    /// site and cannot disagree with the score.
    private func awardPoints(_ value: Int, reason: GameplayScoreReason = .blasterShotdown) {
        guard value > 0 else { return }
        let before = gameState.points
        gameState.points = min(999_999, gameState.points + value)
        events.emitScoreAwarded(points: value, pointsBefore: before, reason: reason)
        if gameState.points > gameState.highScore {
            gameState.highScore = gameState.points
            persistence.saveHighScore(gameState.highScore)
            emitHighScoreSaved(gameState.highScore)
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
        emitCheckpointSaved(checkpoint)
    }

    private func beginFromTitle(currentInput: InputSnapshot) {
        titleOverlay.isHidden = true
        if !hasSavedCheckpoint {
            // A title start with no checkpoint is a new playthrough; continuing from a saved
            // checkpoint keeps the current one, which is what makes the P1-8 farm impossible.
            stageBoundaries.beginPlaythrough()
            // A new playthrough always begins at zone 000, i.e. at the start of a stage, so the
            // timed ladder and the bravery latch are armed from the same step (P1-10). The
            // checkpoint cannot carry a stage-relative clock - `GameCheckpoint` stores no step -
            // and this branch is the only reachable start, because startup clears the checkpoint.
            stageBoundaries.noteStageStarted(atStep: tickDriver.stepCount)
        }
        changeFlow(to: .playing, cause: .firePress)
        setGameplayNodesPaused(false)
        menuFireWasPressed = currentInput.fire
        fireWasPressed = currentInput.fire
        grenadeWasPressed = currentInput.grenade
        sceneJumpWasPressed = currentInput.jump
        if !hasSavedCheckpoint { saveCheckpoint() }
    }

    private func enterGameOver() {
        changeFlow(to: .gameOver, cause: .death)
        invulnerability = 0
        persistence.clearCheckpoint()
        hasSavedCheckpoint = false
        stageBoundaries.endPlaythrough()
        emitCheckpointCleared(reason: .gameOver)
        if gameState.points > gameState.highScore {
            gameState.highScore = gameState.points
            persistence.saveHighScore(gameState.highScore)
            emitHighScoreSaved(gameState.highScore)
        }
        events.emitGameOver(points: gameState.points, highScore: gameState.highScore, checkpointCleared: true)
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
        changeFlow(to: .contentComplete, cause: .contentComplete)
        let playableNext = !nextLevelName.isEmpty && includedLevels.contains(nextLevelName)
        events.emitContentComplete(points: gameState.points,
                                   final: gameState.zone >= 124 && nextLevelName.isEmpty,
                                   hasNextLevel: playableNext)
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
        changeFlow(to: .title, cause: .titleReturn)
        updateTitleOverlayText()
        emitTitleEnter()
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
        changeFlow(to: .paused, cause: .pausePress)
        emitPause(entering: true, stateBefore: stateBeforePause)
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
        emitPause(entering: false, stateBefore: stateBeforePause)
        changeFlow(to: stateBeforePause, cause: .resume)
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
        events.emitRunRestarted(discardedPoints: gameState.points)
        persistence.clearCheckpoint()
        hasSavedCheckpoint = false
        emitCheckpointCleared(reason: .newGame)
        stageBoundaries.beginPlaythrough()
        stageBoundaries.noteStageStarted(atStep: tickDriver.stepCount)
        clearTransientObjects()
        currentLevel.rootNode.removeFromParent()
        // Same defect class as P1-9 (repo_explorer section 8-4): this also swaps `currentLevel`
        // inside a rendered frame, so the accumulator is discarded here too.
        tickDriver.reset(reason: .newGame)

        currentLevelName = "L01S01"
        emitZoneLoad(cause: .restart)
        currentLevel = TMXLevelRuntime(resource: currentLevelName)
        currentLevel.events = events
        addChild(currentLevel.rootNode)
        emitZoneLoaded(carriedY: false)

        gameState.resetForNewGame()
        gameState.highScore = persistence.loadHighScore()

        player.setExoskeleton(false, cause: .reset)
        player.configure(spawnCenter: currentLevel.spawnCenter, groundY: currentLevel.groundY)
        playerNode.update(from: player, dt: 0)
        invulnerability = 0
        deathGroundTimer = 0
        changeFlow(to: .playing, cause: .restart)
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

    // MARK: - Gameplay event emission
    //
    // Every record leaves through a `GameplayEventSink.emit…` helper: the lane maps live once, in
    // `GameCore/Diagnostics/GameplayEventSink.swift`, which `evidence/harness/run.sh` compiles and
    // which `lane_round_trip_is_exact` proves field by field. Nothing in this file may pack a lane
    // by hand - the code review's four wire lies were all hand-ordered lanes or hand-picked bit
    // offsets at these sites. The frozen contract is
    // `engineering/contracts/schemas/gameplay-event-v1.schema.json`.

    /// The only `flowState` mutation path that names a cause, so `state.flow` cannot drift from the
    /// assignment sites (integration section 11-2).
    private func changeFlow(to next: GameFlowState, cause: GameplayFlowCause) {
        pendingFlowCause = cause
        flowState = next
    }

    private func emitFlow(from: GameFlowState, to: GameFlowState, cause: GameplayFlowCause) {
        events.emitFlowChange(from: from, to: to, cause: cause)
    }

    /// Once per executed fixed step at emission level 2; the log drops it silently below that.
    private func emitMotion() {
        events.emitMotion(state: player.motionState, grounded: player.isGrounded, facing: player.facing,
                          exoskeleton: player.hasExoskeleton, position: player.position,
                          velocityX: player.velocity.dx, velocityY: player.velocity.dy)
    }

    /// Diffed against the previous tick's snapshot inside the loop: one comparison per step, edges
    /// stamped with the tick that actually saw them, and `held_us` derived from a fixed-step count
    /// so no wall clock enters the stream (integration section 9).
    private func emitInputEdges(current: InputSnapshot) {
        defer { previousTickInput = current }
        guard let previous = previousTickInput else { return }
        for (index, action) in Self.trackedActions.enumerated() {
            let projection = Self.actionProjections[index]
            let wasPressed = projection(previous)
            let isPressed = projection(current)
            let heldBefore = heldStepsByAction[index]
            if isPressed {
                // Saturating: a long hold must not wrap the 16-bit millisecond lane.
                heldStepsByAction[index] = heldBefore < 1_000_000 ? heldBefore + 1 : heldBefore
            } else {
                heldStepsByAction[index] = 0
            }
            guard wasPressed != isPressed else { continue }
            // A press edge has held nothing yet; a release edge reports the run that just ended.
            let heldSteps = isPressed ? 0 : Int(heldBefore)
            events.emitActionEdge(action, source: inputState.source(for: action) ?? .keyboard,
                                  pressed: isPressed,
                                  heldMilliseconds: GameplayEvent.microseconds(fromSteps: heldSteps) / 1_000)
        }
    }

    /// `jump_suppressed` is the P1-4 witness: the UP key is still physically down while Player
    /// carries the contextual latch - the exact state the audited defect leaked through on the next
    /// fixed step.
    private func emitContextualConsumed(kind: GameplayContextualAction, jumpSuppressed: Bool) {
        events.emitContextualConsume(kind, jumpSuppressed: jumpSuppressed)
    }

    private func emitPickup(kind: GameplayPickupKind, countBefore: Int, countAfter: Int, at origin: CGPoint) {
        events.emitPickupCollected(kind, countBefore: countBefore, countAfter: countAfter, at: origin)
    }

    /// P1-8: the boundary total plus one component record each, so a later wave can add award
    /// components without changing the total's name or the witness plumbing.
    private func emitStageBoundary(award: StageBoundaryAward) {
        events.emitStageBoundaryPoints(points: award.points, livesBefore: award.livesBefore,
                                       livesAfter: award.livesAfter,
                                       ammoReset: award.refillsAmmoAndGrenades)
        for component in award.components {
            events.emitStageAwardComponent(component.id, points: component.points)
        }
    }

    private func emitZoneLoad(cause: GameplayZoneLoadCause) {
        events.emitZoneLoad(cause)
    }

    private func emitZoneLoaded(carriedY: Bool) {
        events.emitZoneLoaded(solidCount: currentLevel.solidRects.count,
                              spawnCenter: currentLevel.spawnCenter,
                              groundY: currentLevel.groundY,
                              invulnerabilityTicks: ticks(invulnerability),
                              carriedY: carriedY)
    }

    /// P1-9 witness: the accumulator still charged at the swap plus the steps it would have bought.
    private func emitZoneTransition(to levelName: String) {
        events.emitZoneTransition(toZone: zoneNumber(for: levelName),
                                  accumulatorMicroseconds: tickDriver.accumulatorMicroseconds,
                                  pendingSteps: tickDriver.pendingSteps)
    }

    private func emitCheckpointSaved(_ checkpoint: GameCheckpoint) {
        events.emitCheckpointSaved(ammo: checkpoint.ammo, grenades: checkpoint.grenades,
                                   lives: checkpoint.lives, points: checkpoint.points)
    }

    private func emitCheckpointCleared(reason: GameplayCheckpointClearedReason) {
        events.emitCheckpointCleared(reason)
    }

    private func emitTitleEnter() {
        events.emitTitleEnter(highScore: gameState.highScore, hasSavedCheckpoint: hasSavedCheckpoint)
    }

    private func emitPause(entering: Bool, stateBefore: GameFlowState) {
        events.emitPauseChanged(entering: entering, stateBefore: stateBefore, selectedIndex: pauseSelectedIndex)
    }

    private func emitHighScoreSaved(_ value: Int) {
        events.emitHighScoreSaved(value)
    }

    private func emitPlayerHit(cause: GameplayDamageCause, at position: CGPoint, stateBefore: GameFlowState) {
        events.emitPlayerHit(cause: cause, position: position, flowBefore: stateBefore,
                             flowAfter: .playerDead, lives: gameState.lives)
    }

    private func emitBlockedHit(cause: GameplayDamageCause, testInvulnerability: Bool) {
        events.emitBlockedHit(cause: cause,
                              invulnerabilityMicroseconds: Int((max(0, invulnerability) * 1_000_000).rounded()),
                              testInvulnerability: testInvulnerability)
    }

    private func emitDeathBegin() {
        events.emitDeathBegin(position: player.position, lives: gameState.lives, ammo: gameState.ammo,
                              grenades: gameState.grenades)
    }

    private func emitDeathLanded(groundTicks: Int) {
        events.emitDeathLanded(position: player.position, groundTicks: groundTicks)
    }

    private func emitDeathSettled(livesBefore: Int, livesAfter: Int) {
        events.emitDeathSettled(livesBefore: livesBefore, livesAfter: livesAfter,
                                invulnerabilityTicks: ticks(GameConstants.postDeathProtectionDuration),
                                settleTicks: ticks(GameConstants.deathSettleDelay),
                                checkpointSaved: hasSavedCheckpoint)
    }

    /// The launcher's own box origin, reported by `bonus.double_launcher` as `x`/`y`. Looking the
    /// object up by identity is safe here: the payout just named it, and `nil` (a runtime rebuilt
    /// mid-step, which cannot happen on this path) degrades to the player's position rather than
    /// dropping the witness.
    private func launcherOrigin(of payout: DoubleLauncherPayout) -> CGPoint {
        currentLevel.doubleLauncherOrigin(withEntityID: payout.objectID) ?? player.position
    }

    /// Seconds of gameplay in fixed steps, so every `*_us` duration in the stream is derived from
    /// the simulation clock rather than measured.
    private func ticks(_ seconds: TimeInterval) -> Int {
        Int((seconds / GameConstants.fixedTimeStep).rounded())
    }

    /// The F1 tail: the newest records of the same ring, in the same wire format.
    private func updateEventTail() {
        renderedFramesSinceTailUpdate += 1
        guard renderedFramesSinceTailUpdate >= 10 else { return }
        renderedFramesSinceTailUpdate = 0
        guard let label = eventTailLabel else { return }
        guard showHitboxes, events.isRecording else {
            if !label.isHidden { label.isHidden = true }
            return
        }
        label.text = ((events as? GameplayEventLog)?.describe(8) ?? []).joined(separator: "\n")
        label.isHidden = false
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
        updateEventTail()
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

        // Content-factory safe models: imported scenery or unconfirmed actions that the factory
        // records instead of dropping. They are outlined here and nowhere else — no sprite and no
        // texture is created for them, because their artwork is already baked into the map's
        // static scenery layer. The node name carries the reason label.
        for marker in currentLevel.safeModelMarkers {
            addDebugRect(marker.rect, color: .yellow, alpha: 0.5,
                         label: "\(marker.label) [\(marker.sourceBlock) @ \(marker.mapResource)]")
        }
    }

    private func addDebugRect(_ rect: CGRect, color: SKColor, alpha: CGFloat = 0.9, label: String = "") {
        guard rect.width > 0, rect.height > 0 else { return }
        let path = CGPath(rect: rect, transform: nil)
        let node = SKShapeNode(path: path)
        node.strokeColor = color
        node.lineWidth = 1
        node.alpha = alpha
        node.fillColor = .clear
        if !label.isEmpty {
            node.name = label
        }
        debugOverlay.addChild(node)
    }
}
