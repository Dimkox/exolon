import SpriteKit

/// Step 10: one runtime class for all Exolon screens.
///
/// Gameplay objects are created from TMX object names. Adding a new map no
/// longer requires a new Swift screen class; when the object types are already
/// known, dropping the TMX resource into the target is enough.
final class TMXLevelRuntime {
    let name: String
    let rootNode = SKNode()
    let map: TMXMapData
    let mapRenderer: TMXTileMapRenderer
    // The single Collision surface query shared by every ground derivation of
    // this level (spawn, pistons, renderer rects).
    let surfaceQuery: TMXSurfaceQuery
    let spawnCenter: CGPoint
    let groundY: CGFloat

    private(set) var turrets: [TurretObstacle] = []
    private(set) var destructibleObstacles: [DestructibleObstacle] = []
    private(set) var grenadePacks: [GrenadePackPickup] = []
    private(set) var ammoPacks: [AmmoPackPickup] = []
    private(set) var portals: [TeleportPortal] = []
    private(set) var pistons: [PistonHazard] = []
    private(set) var bubbleSpawners: [BubbleSpawner] = []
    private(set) var bubbles: [BubbleEnemy] = []
    private(set) var incubators: [IncubatorObstacle] = []
    private(set) var eggs: [EggEnemy] = []
    private(set) var doubleLaunchers: [DoubleLauncherObstacle] = []
    private(set) var mines: [MineHazard] = []
    private(set) var sourceHazards: [CGRect] = []
    private(set) var forceFields: [ForceFieldBarrier] = []
    // P1-5: one shared hit-point pool per beam field; `forceFields` holds the
    // visual sides and delegates hits/lethality to these entities. Gameplay
    // reads the fields only through their sides — this array is retained as
    // the owner-visible registry of whole fields (per-level fresh instance,
    // 25 HP each) for review and future field-level consumers (audit §Q6.7
    // disposition: intentional, documented).
    private(set) var beamFields: [BeamFieldModel] = []
    private(set) var stageExitMarkers: [CGRect] = []
    private(set) var changingRooms: [CGRect] = []
    // Changing rooms are pass-through scenery. The original action trigger lives
    // inside the booth, so any static no-walk cells emitted by its artwork must
    // be removed from player collision or Vitorc can never enter it.
    private var changingRoomCollisionExclusions: [CGRect] = []
    private(set) var missileGuidance: [GreenMissileGuidance] = []
    // The original beacon base is part of the static artwork/collision map,
    // but once the guidance tower is destroyed its blocking cells must stop
    // participating in player collision.  Keep the exact 4x3-tile base areas
    // separately so we can remove only those cells without touching the floor
    // or neighbouring platforms.
    private var missileGuidanceBaseCollisionRects: [CGRect] = []
    private(set) var homingMissiles: [HomingMissile] = []
    // Content-factory accounting. A source marker that cannot become a gameplay object without
    // inventing behaviour is recorded here as a labeled safe model, and a marker the matcher does
    // not recognize at all is recorded in `unmatchedSourceMarkers`. Both exist so that "the map
    // lost content" is impossible without leaving evidence. Neither array feeds physics, damage,
    // scoring or spawning: `safeModelMarkers` is consumed only by the hitbox debug overlay in
    // `GameScene`, and `unmatchedSourceMarkers` only by the coverage meter.
    private(set) var safeModelMarkers: [TMXSafeModelMarker] = []
    private(set) var unmatchedSourceMarkers: [String] = []

    /// Gameplay event sink, injected by `GameScene`. `nil` = no emission (harness/unit default).
    var events: (any GameplayEventSink)?
    /// Ordinal of the next object taken from `map.objectGroups.flatMap { $0.objects }`; assigned in
    /// `buildObjectsFromTMX`, which iterates that array exactly once (architect section 5.2).
    private var nextEntityID: UInt16 = 0

    init(resource name: String) {
        // IMPORTANT: resolve everything needed by immutable stored properties
        // into local values first. Swift does not allow a closure to capture
        // `self` until every stored property has been initialized.
        let loadedMap: TMXMapData
        do {
            loadedMap = try TMXMapLoader.load(resource: name)
        } catch {
            fatalError("Unable to load TMX map \(name): \(error)")
        }

        // Build the shared surface query exactly once per load and hand it to
        // every consumer (renderer rects, spawn resolver, piston anchors) —
        // the Collision layer is parsed a single time.
        let query = loadedMap.surfaceQuery
        let renderer = TMXTileMapRenderer(map: loadedMap, surfaceQuery: query)

        // P1-2 (bounded as amended after the 2026-09-24 audit): the vitorc
        // marker line sits 0/+16/−16 px off the Collision surface across the
        // corpus (37/59/29). The feet re-anchor to the nearest surface inside
        // that one-tile window only; markers with no surface in the window
        // stay UNMOVED and are enumerated in the change evidence, so no spawn
        // ever moves more than one tile.
        let playerBottom = loadedMap.resolvedPlayerBottom(using: query)

        let resolvedSpawnCenter = CGPoint(
            x: playerBottom.x + GameConstants.playerSpriteSize.width * 0.5,
            y: playerBottom.y + GameConstants.playerSpriteSize.height * 0.5
        )

        // The grenade fallback floor must be the lowest traversable surface,
        // not the player's spawn platform. Elevated spawns appear from L01S04.
        // Same value the renderer rects used to produce (min rect maxY), now
        // read from the shared query instead of a second ad-hoc computation.
        let resolvedGroundY = query.fallbackPlaneY

        self.name = name
        self.map = loadedMap
        self.mapRenderer = renderer
        self.surfaceQuery = query
        self.spawnCenter = resolvedSpawnCenter
        self.groundY = resolvedGroundY

        rootNode.name = name
        rootNode.zPosition = 0
        rootNode.addChild(renderer.node)

        // All stored properties are initialized at this point, so calling
        // instance methods is now safe.
        addBackdrop()
        buildObjectsFromTMX()
    }

    var nextLevelName: String { map.properties["nextLevel"] ?? "" }
    var terrainRects: [CGRect] {
        var rects = mapRenderer.collisionRects

        // Zone 008 exposed a subtle but important difference between the TMX
        // collision layer and the original runtime: destroying the green
        // guidance tower opens the route.  The old implementation only hid the
        // green top visually, leaving blk_beacon_base's 4x3 collision cells in
        // the immutable TMX layer, so Vitorc hit an invisible 80-pixel-high
        // wall.  Remove exactly the base cells after the guidance is gone.
        if !missileGuidance.isEmpty,
           !missileGuidance.contains(where: { $0.isActive }) {
            for exclusion in missileGuidanceBaseCollisionRects {
                rects = rects.flatMap { Self.subtract(rect: $0, removing: exclusion) }
            }
        }

        // A changing room is not a solid wall. In the original game Vitorc
        // can walk into the booth and press UP. Some compiled scenery cells
        // carry no-walk flags because they draw the frame; strip only the booth
        // volume while preserving the supporting platform below it.
        for exclusion in changingRoomCollisionExclusions {
            rects = rects.flatMap { Self.subtract(rect: $0, removing: exclusion) }
        }

        return rects
    }

    var solidRects: [CGRect] {
        var result = terrainRects
        for turret in turrets where turret.isActive { result.append(turret.hitbox) }
        for obstacle in destructibleObstacles where obstacle.isActive { result.append(obstacle.hitbox) }
        for incubator in incubators where incubator.isActive { result.append(incubator.hitbox) }
        return result
    }

    func fixedUpdate(dt: TimeInterval, player: Player) -> [EnemyTurretBullet] {
        for portal in portals { portal.fixedUpdate(dt: dt) }
        for piston in pistons { piston.fixedUpdate(dt: dt) }

        var shots: [EnemyTurretBullet] = []
        for turret in turrets {
            if let shot = turret.fixedUpdate(dt: dt) { shots.append(shot) }
        }

        for launcher in doubleLaunchers {
            guard let shot = launcher.fixedUpdate(dt: dt, player: player) else { continue }
            shots.append(shot)
            // P1-6 witness: the launcher still produces shots after its bonus has been paid.
            guard let events = events, shot.kind == .doubleLauncher else { continue }
            events.emitLauncherFired(objectID: launcher.entityID, at: launcher.hitbox.origin,
                                     muzzleY: shot.position.y)
        }

        for spawner in bubbleSpawners {
            if let bubble = spawner.fixedUpdate(dt: dt, player: player) {
                bubbles.append(bubble)
                rootNode.addChild(bubble.node)
            }
        }

        for bubble in bubbles { bubble.fixedUpdate(dt: dt) }
        bubbles = bubbles.filter { bubble in
            if !bubble.isAlive { bubble.node.removeFromParent() }
            return bubble.isAlive
        }

        for egg in eggs {
            egg.fixedUpdate(dt: dt, terrainRects: terrainRects)
        }
        eggs = eggs.filter { egg in
            if !egg.isAlive { egg.node.removeFromParent() }
            return egg.isAlive
        }

        // Original green guidance station: only one homing missile is alive
        // at a time. The missile is not blaster-destroyable; removing the
        // guidance station with a grenade removes the active missile.
        if missileGuidance.contains(where: { $0.isActive }) && homingMissiles.isEmpty && !player.isDying {
            let originalTopY = Int.random(in: 32...159)
            let worldY = max(48, min(GameConstants.logicalSize.height - 48,
                                     GameConstants.logicalSize.height - CGFloat(originalTopY * 2) - 16))
            let missile = HomingMissile(startY: worldY)
            homingMissiles.append(missile)
            rootNode.addChild(missile.node)
        }

        for missile in homingMissiles {
            missile.fixedUpdate(dt: dt, targetY: player.position.y)
        }
        homingMissiles = homingMissiles.filter { missile in
            if !missile.isAlive { missile.node.removeFromParent() }
            return missile.isAlive
        }

        return shots
    }


    /// Returns the destroyed beacon centre, missile explosion positions and
    /// the exact original score consequence (150 for the block + 850 if an
    /// active guided missile is removed at that moment).
    func destroyMissileGuidanceIfHit(by grenadeBox: CGRect) -> (center: CGPoint, missilePositions: [CGPoint], points: Int)? {
        guard let guidance = missileGuidance.first(where: { $0.isActive && grenadeBox.intersects($0.hitbox) }) else {
            return nil
        }
        guidance.destroy()
        let activeMissiles = homingMissiles.filter { $0.isAlive }
        let positions = activeMissiles.map { $0.position }
        for missile in activeMissiles {
            missile.destroy()
            missile.node.removeFromParent()
        }
        homingMissiles.removeAll()
        return (guidance.center, positions, 150 + (positions.isEmpty ? 0 : 850))
    }

    func consumeGuidedMissileHit(playerBox: CGRect) -> CGPoint? {
        guard let missile = homingMissiles.first(where: { $0.isAlive && $0.hitbox.intersects(playerBox) }) else {
            return nil
        }
        let p = missile.position
        missile.destroy()
        missile.node.removeFromParent()
        homingMissiles.removeAll { !$0.isAlive }
        return p
    }

    /// P1-6: the payout carries its own identity **and** the fire-gate state, so the witness record
    /// cannot be skipped by a second lookup that might fail. `nil` means nothing was paid this step.
    /// The ordinal is per zone instance, so the join key of `bonus.double_launcher` and
    /// `entity.launcher_fire` is `(record zone, object_id)`.
    func collectDoubleLauncherBonus(playerBox: CGRect) -> DoubleLauncherPayout? {
        guard let launcher = doubleLaunchers.first(where: { $0.collectBonusIfTouched(playerBox: playerBox) }) else {
            return nil
        }
        return DoubleLauncherPayout(points: 1_000, objectID: launcher.entityID,
                                    launcherActiveAfter: launcher.isActive)
    }

    /// Geometry of a launcher by its map ordinal, for the `bonus.double_launcher` payload.
    func doubleLauncherOrigin(withEntityID entityID: UInt16) -> CGPoint? {
        doubleLaunchers.first { $0.entityID == entityID }?.hitbox.origin
    }

    /// Also returns which portal pair member the player is standing in, because the
    /// `player.teleport{portal_index}` witness cannot be recovered from the destination alone.
    func teleportDestination(for playerBox: CGRect) -> (center: CGPoint, portalIndex: Int)? {
        guard portals.count >= 2 else { return nil }
        for (index, portal) in portals.enumerated() where portal.fullyContains(playerBox: playerBox) {
            let other = portals[(index + 1) % portals.count]
            return (other.destinationCenter, index)
        }
        return nil
    }

    private func buildObjectsFromTMX() {
        let objects = map.objectGroups.flatMap { $0.objects }
        // P1-5: beam sides are collected first so each x-overlapping group of
        // segments can become one field entity with a single shared 25-hit pool.
        var beamBoxes: [CGRect] = []

        for object in objects {
            let bottom = map.worldBottomLeft(for: object)
            let entityID = nextEntityID
            nextEntityID = nextEntityID &+ 1

            switch object.name {
            case "vitorc":
                break

            case "turret":
                let entity = TurretObstacle(leftX: bottom.x, groundY: bottom.y)
                turrets.append(entity)
                rootNode.addChild(entity.node)

            case "cocoon":
                addDestructible(
                    name: "cocoon", image: "cocoon", size: CGSize(width: 80, height: 128),
                    bottom: bottom,
                    hitbox: CGRect(x: bottom.x, y: bottom.y, width: 80, height: 128)
                )

            case "radar":
                addDestructible(
                    name: "radar", image: "radar", size: CGSize(width: 80, height: 128),
                    bottom: bottom,
                    hitbox: CGRect(x: bottom.x + 6, y: bottom.y, width: 68, height: 128)
                )

            case "rocket":
                addDestructible(
                    name: "rocket", image: "rocket", size: CGSize(width: 64, height: 96),
                    bottom: bottom,
                    hitbox: CGRect(x: bottom.x + 12, y: bottom.y + 10, width: 52, height: 86)
                )

            case "grenade_pack":
                let pickup = GrenadePackPickup(bottomLeft: bottom)
                grenadePacks.append(pickup)
                rootNode.addChild(pickup.node)

            case "ammo_pack":
                let pickup = AmmoPackPickup(bottomLeft: bottom)
                ammoPacks.append(pickup)
                rootNode.addChild(pickup.node)

            case "teleport":
                let portal = TeleportPortal(bottomLeft: bottom)
                portals.append(portal)
                rootNode.addChild(portal.node)

            case "piston":
                // P1-1: the piston emerges from the Collision surface directly
                // under its fully raised tread (query.pistonGroundY), not from
                // the marker's own tile row — the marker row leaves the world
                // bottom 64 px below that surface on 40 of 46 pistons and
                // 48 px below on 3 shaft pistons (only 3 are anchored on the
                // surface already).
                let piston = PistonHazard(
                    leftX: bottom.x,
                    groundY: surfaceQuery.pistonGroundY(markerX: bottom.x, markerBottomY: bottom.y)
                )
                pistons.append(piston)
                rootNode.addChild(piston.node)

            case "capsule":
                let width = object.width > 0 ? object.width : 32
                let height = object.height > 0 ? object.height : 80
                let trigger = CGRect(x: bottom.x, y: bottom.y, width: width, height: height)
                changingRooms.append(trigger)

                // The 32x80 TMX rectangle is the interaction trigger, not the
                // physical width of the booth. Clear enough room for Vitorc's
                // 46 px movement collider to enter from either side, but start
                // 16 px above the supporting platform so the floor stays solid.
                changingRoomCollisionExclusions.append(CGRect(
                    x: trigger.minX - 16,
                    y: max(0, trigger.minY - 16),
                    width: max(96, trigger.width + 64),
                    height: trigger.height + 32
                ))

            case "bubble_creator":
                let delay = Double(object.properties["delay"] ?? "") ?? 1.0
                let behavior = object.properties["behavior"] ?? "swing"
                bubbleSpawners.append(BubbleSpawner(delay: delay, behavior: behavior))

            case "incubator":
                let incubator = IncubatorObstacle(bottomLeft: bottom)
                incubators.append(incubator)
                rootNode.addChild(incubator.node)
                for egg in incubator.eggs {
                    eggs.append(egg)
                    rootNode.addChild(egg.node)
                }

            case "double_launcher":
                let launcher = DoubleLauncherObstacle(bottomLeft: bottom, entityID: entityID)
                doubleLaunchers.append(launcher)
                rootNode.addChild(launcher.node)

            case "mine":
                let mine = MineHazard(bottomLeft: bottom)
                mines.append(mine)
                rootNode.addChild(mine.node)

            case "ship":
                addStaticSprite(image: "ship", size: CGSize(width: 176, height: 128), bottom: bottom, z: 1)

            case "gate":
                addDestructible(
                    name: "gate", image: "gate", size: CGSize(width: 176, height: 144),
                    bottom: bottom,
                    hitbox: CGRect(x: bottom.x + 8, y: bottom.y, width: 160, height: 144)
                )

            case "ship_fire":
                addStaticSprite(image: "ship_fire_frame", size: CGSize(width: 16, height: 32), bottom: bottom, z: 2)

            case "light_floor":
                addStaticSprite(image: "light_floor", size: CGSize(width: 16, height: 16), bottom: bottom, z: 3)

            case "light_ceiling":
                addStaticSprite(image: "light_ceiling", size: CGSize(width: 16, height: 16), bottom: bottom, z: 3)

            case "source_marker":
                let source = object.properties["sourceBlock"] ?? ""
                let sx = CGFloat(Int(object.properties["sourceX"] ?? "") ?? 0) * 16
                let syTop = CGFloat(Int(object.properties["sourceY"] ?? "") ?? 0) * 16
                let bottomY = map.pixelHeight - syTop - 32
                // Exhaustive over TMXSourceMarkerKind with no `default:` arm: a marker that
                // resolves to nothing lands in the `nil` case and is recorded, never dropped.
                switch TMXSourceMarkerKind.classify(sourceBlock: source) {
                case .forceField:
                    let box = CGRect(x: sx, y: max(0, bottomY - 240), width: 48, height: 272)
                    beamBoxes.append(box)
                case .highVoltage:
                    // High-voltage is animated from the action table. The
                    // original update routine does not call KillPlayer; do not
                    // turn the visual marker into a blanket lethal rectangle.
                    break
                case .blinker:
                    // Blinker is an attribute-flash action, not a damage zone.
                    break
                case .stageEnd:
                    stageExitMarkers.append(CGRect(x: sx, y: max(0, bottomY - 64), width: 96, height: 128))
                case .changingRoom:
                    let trigger = CGRect(x: sx, y: max(0, bottomY - 64), width: 80, height: 96)
                    changingRooms.append(trigger)
                    changingRoomCollisionExclusions.append(CGRect(
                        x: max(0, trigger.minX - 16),
                        y: max(0, trigger.minY - 16),
                        width: trigger.width + 32,
                        height: trigger.height + 32
                    ))
                case .beaconBase:
                    // blk_beacon_base is exactly four character cells wide and
                    // three cells high in the imported collision layer.  It is
                    // solid while the guidance tower exists, then becomes
                    // passable when the tower is destroyed by a grenade.
                    let sourceX = CGFloat(Int(object.properties["sourceX"] ?? "") ?? 0)
                    let sourceY = CGFloat(Int(object.properties["sourceY"] ?? "") ?? 0)
                    let baseRect = CGRect(
                        x: sourceX * 16,
                        y: map.pixelHeight - (sourceY + 3) * 16,
                        width: 64,
                        height: 48
                    )
                    missileGuidanceBaseCollisionRects.append(baseRect)
                case .controlBeacon:
                    // Original DestroyableBlockSizeTable entry for block 31:
                    // x = sourceX-1 for 6 chars, y = sourceY-2 for 6 chars.
                    let sourceY = CGFloat(Int(object.properties["sourceY"] ?? "") ?? 0)
                    let box = CGRect(
                        x: max(0, sx - 16),
                        y: max(0, map.pixelHeight - (sourceY + 4) * 16),
                        width: 96,
                        height: 96
                    )
                    let guidance = GreenMissileGuidance(hitbox: box)
                    missileGuidance.append(guidance)
                    rootNode.addChild(guidance.coverNode)
                case .inertScenery:
                    // blk_mushroom and blk_waggon are imported static scenery: already solid in
                    // the Collision layer at their own cell and already drawn by the baked
                    // Original Static Scenery image layer. The source table records no action at
                    // any of the 33 cells, so the factory must not invent behaviour here; the
                    // defect being fixed is that the marker used to vanish without a trace.
                    // The record is read only by the debug overlay, so no gameplay path changes.
                    appendSafeModelMarker(kind: .inertScenery, sourceBlock: source,
                                          sx: sx, bottomY: bottomY)
                case .unconfirmedAction:
                    // blk_gunMachine_BOTTOM is the only formerly-dropped family with a positive
                    // action record (type 11 at its own cell), but the type cannot be identified
                    // from anything in this repository: 56 type-11 actions exist and only 18 are
                    // exported here, and the other 38 sit in maps with no BOTTOM marker at all.
                    // So the marker is recorded and labeled, and deliberately not armed.
                    appendSafeModelMarker(kind: .unconfirmedAction, sourceBlock: source,
                                          sx: sx, bottomY: bottomY)
                case nil:
                    // The matcher met nothing. Record the name so the coverage meter fails on it
                    // instead of the map silently losing content.
                    unmatchedSourceMarkers.append(source)
                }

            default:
                // Unknown objects are intentionally ignored instead of being
                // guessed. Their names will become factory cases as we reach
                // later screens.
                break
            }
        }

        // P1-5 (issue #9): the imported `blk_beam_up`/`blk_beam_down` markers
        // are the two halves of one beam. Boxes with overlapping x intervals
        // form a single field entity with one shared 25-hit-point pool; both
        // visual sides stay and the field is destroyed as a unit. The old code
        // gave every side its own 25-point field, doubling the shots to clear.
        // Provenance: ORIGINAL_MECHANICS.md:26/:121-127 words ONE field per
        // source marker (25 hits, 1000 points on destruction). The pair
        // reading here is ruled by issue #9 ("ожидаемое суммарное поведение —
        // 25") plus the corpus data (10/10 maps carry exactly one up+down pair
        // in adjacent columns whose 48-px boxes overlap by 32 px — one beam
        // slit); it also restores the documented single 1000-point award per
        // destroyed beam, where the old per-side model paid up to 2000.
        for group in TMXBeamGrouping.groups(for: beamBoxes) {
            let field = BeamFieldModel()
            var sides: [ForceFieldBarrier] = []
            for index in group {
                let side = ForceFieldBarrier(hitbox: beamBoxes[index], field: field)
                // Weak capture: the field owns the handler list; a strong
                // handler reference would close a field ↔ side retain cycle.
                field.onDestroyed { [weak side] in side?.coverDestroyed() }
                sides.append(side)
            }
            for side in sides {
                forceFields.append(side)
                rootNode.addChild(side.node)
            }
            beamFields.append(field)
        }

        // L01S01's reference artwork contains the gate directly under the ship.
        // The Step-7 TMX stores the ship as an object, so keep the original gate
        // asset data-driven by the map name rather than by a separate screen class.
        if name == "L01S01" {
            let gate = SKTexture(imageNamed: "gate")
            gate.filteringMode = .nearest
            let sprite = SKSpriteNode(texture: gate, size: CGSize(width: 176, height: 144))
            sprite.anchorPoint = CGPoint(x: 0, y: 0)
            sprite.position = CGPoint(x: 0, y: GameConstants.defaultGroundY)
            sprite.zPosition = 0.5
            rootNode.addChild(sprite)
        }
    }

    /// Record a source marker that the factory can only express as a labeled safe model. The
    /// footprint is the measured cell box converted to pixels the same way `beaconBase` converts
    /// its own (4x3 cells -> 64x48 pt), anchored so its top edge sits at the marker's source row.
    private func appendSafeModelMarker(kind: TMXSourceMarkerKind, sourceBlock: String,
                                       sx: CGFloat, bottomY: CGFloat) {
        let cells = TMXSourceMarkerKind.safeModelFootprintCells(sourceBlock: sourceBlock)
        let width = CGFloat(cells.width) * 16
        let height = CGFloat(cells.height) * 16
        safeModelMarkers.append(TMXSafeModelMarker(
            kind: kind,
            sourceBlock: sourceBlock,
            label: kind.safeModelLabel,
            rect: CGRect(x: sx, y: max(0, bottomY - height), width: width, height: height),
            mapResource: name
        ))
    }

    private func addDestructible(name: String, image: String, size: CGSize, bottom: CGPoint, hitbox: CGRect) {
        let obstacle = DestructibleObstacle(
            name: name,
            imageName: image,
            size: size,
            bottomLeft: bottom,
            hitbox: hitbox
        )
        destructibleObstacles.append(obstacle)
        rootNode.addChild(obstacle.node)
    }

    /// Subtract one axis-aligned rectangle from another, preserving all
    /// neighbouring collision geometry.  A merged TMX collision run can span
    /// beyond the beacon, so simply dropping an intersecting rectangle would
    /// also delete unrelated floor/platform cells.
    private static func subtract(rect: CGRect, removing cut: CGRect) -> [CGRect] {
        let overlap = rect.intersection(cut)
        guard !overlap.isNull, overlap.width > 0, overlap.height > 0 else {
            return [rect]
        }

        var pieces: [CGRect] = []

        if overlap.minY > rect.minY {
            pieces.append(CGRect(x: rect.minX, y: rect.minY,
                                 width: rect.width, height: overlap.minY - rect.minY))
        }
        if overlap.maxY < rect.maxY {
            pieces.append(CGRect(x: rect.minX, y: overlap.maxY,
                                 width: rect.width, height: rect.maxY - overlap.maxY))
        }

        let middleMinY = max(rect.minY, overlap.minY)
        let middleMaxY = min(rect.maxY, overlap.maxY)
        let middleHeight = middleMaxY - middleMinY
        if middleHeight > 0 {
            if overlap.minX > rect.minX {
                pieces.append(CGRect(x: rect.minX, y: middleMinY,
                                     width: overlap.minX - rect.minX, height: middleHeight))
            }
            if overlap.maxX < rect.maxX {
                pieces.append(CGRect(x: overlap.maxX, y: middleMinY,
                                     width: rect.maxX - overlap.maxX, height: middleHeight))
            }
        }

        return pieces.filter { $0.width > 0 && $0.height > 0 }
    }

    private func addStaticSprite(image: String, size: CGSize, bottom: CGPoint, z: CGFloat) {
        let texture = SKTexture(imageNamed: image)
        texture.filteringMode = .nearest
        let sprite = SKSpriteNode(texture: texture, size: size)
        sprite.anchorPoint = CGPoint(x: 0, y: 0)
        sprite.position = bottom
        sprite.zPosition = z
        rootNode.addChild(sprite)
    }

    // MARK: - Backdrop retained while source TMX background layers are imported

    private func addBackdrop() {
        // Step 9 fixed: do not reconstruct planets/structures by hand here.
        // Earlier versions added atlas fragments on top of the TMX map and
        // those fragments became wrong as soon as the tileset layout changed.
        // Keep only a sparse star field; all substantial scenery must come
        // from the TMX visual layers themselves.
        let patterns: [String: [(CGFloat, CGFloat, SKColor)]] = [
            "L01S01": [(28,344,.white),(54,306,.cyan),(112,334,.magenta),(194,356,.yellow),(236,286,.white),(276,330,.red),(348,350,.cyan),(402,300,.magenta),(468,342,.yellow)],
            "L01S02": [(30,340,.cyan),(78,316,.white),(126,354,.magenta),(184,326,.yellow),(238,348,.red),(286,304,.cyan),(346,356,.white),(398,320,.magenta),(462,344,.yellow)],
            "L01S03": [(24,348,.white),(58,312,.cyan),(104,336,.magenta),(158,360,.yellow),(204,300,.red),(268,348,.cyan),(316,314,.white),(374,354,.magenta),(426,324,.yellow)],
            "L01S04": [(18,350,.cyan),(62,322,.white),(108,354,.yellow),(158,310,.magenta),(214,344,.red),(262,286,.white),(314,350,.cyan),(370,318,.yellow),(426,356,.magenta)],
            "L01S05": [(20,344,.white),(66,318,.cyan),(116,354,.magenta),(170,326,.yellow),(226,348,.red),(278,304,.white),(334,356,.cyan),(392,322,.magenta),(450,348,.yellow)],
            "L01S06": [(24,350,.cyan),(72,326,.white),(124,356,.yellow),(184,312,.magenta),(236,346,.red),(292,300,.white),(346,354,.cyan),(404,318,.yellow),(462,350,.magenta)]
        ]

        let stars: [(CGFloat, CGFloat, SKColor)]
        if let known = patterns[name] {
            stars = known
        } else {
            // Deterministic sparse stars for imported original zones.
            let seed = name.unicodeScalars.reduce(17) { (($0 &* 31) &+ Int($1.value)) & 0x7fffffff }
            stars = (0..<10).map { i in
                let x = CGFloat((seed &+ i * 97) % 500 + 6)
                let y = CGFloat((seed / 7 &+ i * 53) % 286 + 82)
                let colors: [SKColor] = [.white, .cyan, .magenta, .yellow, .red]
                return (x, y, colors[(seed + i) % colors.count])
            }
        }
        for star in stars {
            let dot = SKSpriteNode(color: star.2, size: CGSize(width: 2, height: 2))
            dot.position = CGPoint(x: star.0, y: star.1)
            dot.zPosition = -10
            rootNode.addChild(dot)
        }

        // Full-screen original scenery, when present, is now a real TMX
        // image layer rendered by TMXTileMapRenderer. No screen-specific Swift
        // scenery branch remains here.
    }

}