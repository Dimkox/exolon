import CoreGraphics
import Foundation

struct TMXTileset {
    var firstGID: UInt32
    var name: String
    var tileWidth: Int
    var tileHeight: Int
    var imageSource: String = ""
    var imageWidth: Int = 0
    var imageHeight: Int = 0
}

struct TMXLayer {
    var name: String
    var width: Int
    var height: Int
    var gids: [UInt32]
}

struct TMXImageLayer {
    var name: String
    var imageSource: String
    var imageWidth: Int
    var imageHeight: Int
}

struct TMXObject {
    var name: String
    var gid: UInt32?
    var x: CGFloat
    var y: CGFloat
    var width: CGFloat
    var height: CGFloat
    var properties: [String: String] = [:]
}

struct TMXObjectGroup {
    var name: String
    var objects: [TMXObject]
}

struct TMXMapData {
    var width: Int
    var height: Int
    var tileWidth: Int
    var tileHeight: Int
    var properties: [String: String]
    var tilesets: [TMXTileset]
    var imageLayers: [TMXImageLayer]
    var layers: [TMXLayer]
    var objectGroups: [TMXObjectGroup]

    var pixelWidth: CGFloat { CGFloat(width * tileWidth) }
    var pixelHeight: CGFloat { CGFloat(height * tileHeight) }

    func object(named name: String) -> TMXObject? {
        for group in objectGroups {
            if let object = group.objects.first(where: { $0.name == name }) {
                return object
            }
        }
        return nil
    }

    func objects(named name: String) -> [TMXObject] {
        return objectGroups.flatMap { $0.objects }.filter { $0.name == name }
    }

    // The Exolon maps use Tiled's downward Y axis. For tile objects the y
    // coordinate denotes the ground/bottom line, so this returns the bottom-left
    // position in our SpriteKit (upward Y) coordinate system.
    func worldBottomLeft(for object: TMXObject) -> CGPoint {
        // Tile objects in Tiled use a bottom anchor; rectangle objects use a
        // top-left origin. Legacy generated maps retain the old bottom-anchor
        // convention unless explicitly marked as a real Tiled rectangle.
        if object.properties["coordinateMode"] == "tiledRect" {
            return CGPoint(x: object.x, y: pixelHeight - object.y - object.height)
        }
        return CGPoint(x: object.x, y: pixelHeight - object.y)
    }

    /// The shared SpriteKit-free Collision surface query. Spawn anchoring, the
    /// piston anchor and the tile map renderer's collision rects all read the
    /// Collision layer through this type, so "the ground at x" has exactly one
    /// definition in the product (wave B ruling 4).
    var surfaceQuery: TMXSurfaceQuery { TMXSurfaceQuery(map: self) }

    /// Spawn bottom-left resolved through the shared surface query (P1-2,
    /// AC-001 bounded per amendment 2 of 2026-09-24).
    ///
    /// The audited defect is exactly one tile: the corpus places the `vitorc`
    /// marker 0/+16/−16 px off the Collision surface (37/59/29 over 125 maps).
    /// The correction may therefore only act inside that defect: candidates are
    /// the Collision tops overlapping the feet span within ±one tile height of
    /// the marker line. Body-clear is a PREFERENCE inside that window — a
    /// clear candidate wins over a buried one; when every in-window top is
    /// inside solid geometry the nearest is still taken (that is where the
    /// shipped plane-snap already landed, so the spawn is never worse than
    /// base), and only a completely empty window leaves the marker UNMOVED
    /// (enumerated in the change evidence). Hard bound: no spawn moves more
    /// than one tile. Two variants were rejected by the audits: the unbounded
    /// nearest-body-clear rule relocated 91/125 spawns by up to 208 px, and
    /// wholesale deletion of the preference buried 48 spawns that it freed.
    func resolvedPlayerBottom(using query: TMXSurfaceQuery) -> CGPoint {
        guard let playerObject = object(named: "vitorc") else {
            return CGPoint(x: 0, y: GameConstants.defaultGroundY)
        }
        let marker = worldBottomLeft(for: playerObject)
        let centerX = marker.x + GameConstants.playerSpriteSize.width * 0.5
        let halfBody = GameConstants.playerStandingMovementSize.width * 0.5
        let inset = GameConstants.footSupportHorizontalInset
        let feet = query.boundedSurfaceY(
            x0: centerX - halfBody + inset,
            x1: centerX + halfBody - inset,
            around: marker.y,
            halfWindow: CGFloat(tileHeight),
            bodyX0: centerX - halfBody,
            bodyX1: centerX + halfBody,
            bodyHeight: GameConstants.playerStandingMovementSize.height
        ) ?? marker.y
        return CGPoint(x: marker.x, y: feet)
    }
}

/// Solid Collision cells and every ground derivation built on them.
///
/// Coordinates are scene space: bottom-left origin, logical field
/// `GameConstants.logicalSize`, cell top = pixel Y of the cell's upper edge.
struct TMXSurfaceQuery {
    struct SolidCell {
        var x0: CGFloat
        var x1: CGFloat
        var top: CGFloat
    }

    let cells: [SolidCell]
    let tileHeight: CGFloat

    init(map: TMXMapData) {
        tileHeight = CGFloat(map.tileHeight)
        guard let collision = map.layers.first(where: { $0.name.lowercased() == "collision" }),
              collision.gids.count == collision.width * collision.height else {
            cells = []
            return
        }
        var built: [SolidCell] = []
        for row in 0..<collision.height {
            let top = map.pixelHeight - CGFloat(row * map.tileHeight)
            let base = row * collision.width
            for column in 0..<collision.width where collision.gids[base + column] & 0x1FFF_FFFF != 0 {
                built.append(SolidCell(
                    x0: CGFloat(column * map.tileWidth),
                    x1: CGFloat((column + 1) * map.tileWidth),
                    top: top
                ))
            }
        }
        cells = built
    }

    /// The original global safety floor: the top of the lowest solid cell in
    /// the map. Maps without any Collision data keep the default ground
    /// constant. This is the value `TMXLevelRuntime.groundY` has always
    /// published to the fallback-floor and grenade code paths.
    var fallbackPlaneY: CGFloat {
        cells.map(\.top).min() ?? GameConstants.defaultGroundY
    }

    /// Top of the highest solid cell overlapping [x0, x1) at or below
    /// `limitY`; the map fallback plane when the span holds no such cell.
    func groundY(x0: CGFloat, x1: CGFloat, atOrBelow limitY: CGFloat) -> CGFloat {
        var best: CGFloat?
        for cell in cells where cell.top <= limitY && cell.x0 < x1 && cell.x1 > x0 {
            if best == nil || cell.top > best! { best = cell.top }
        }
        return best ?? fallbackPlaneY
    }

    /// Collision cell tops overlapping [x0, x1), ascending, deduplicated.
    func surfaceTops(x0: CGFloat, x1: CGFloat) -> [CGFloat] {
        var tops: [CGFloat] = []
        for cell in cells where cell.x0 < x1 && cell.x1 > x0 && !tops.contains(cell.top) {
            tops.append(cell.top)
        }
        return tops.sorted()
    }

    /// The Collision top nearest `y` inside the closed window
    /// [y − halfWindow, y + halfWindow] over the span; equidistant candidates
    /// resolve to the lower Y. Nil when the window holds no surface.
    ///
    /// Body-clear over the body span is a PREFERENCE, not a filter (AC-001
    /// amendment 2): clear in-window candidates shadow buried ones; with none
    /// clear the nearest in-window top is still returned.
    func boundedSurfaceY(x0: CGFloat, x1: CGFloat, around y: CGFloat, halfWindow: CGFloat,
                         bodyX0: CGFloat, bodyX1: CGFloat, bodyHeight: CGFloat) -> CGFloat? {
        let bodyTops = surfaceTops(x0: bodyX0, x1: bodyX1)
        func isClear(_ top: CGFloat) -> Bool {
            !bodyTops.contains { $0 > top && $0 - tileHeight < top + bodyHeight }
        }
        var clearBest: CGFloat?
        var clearDistance = CGFloat.greatestFiniteMagnitude
        var anyBest: CGFloat?
        var anyDistance = CGFloat.greatestFiniteMagnitude
        for top in surfaceTops(x0: x0, x1: x1) {
            let distance = abs(top - y)
            guard distance <= halfWindow else { continue }
            if distance < anyDistance || (distance == anyDistance && top < anyBest!) {
                anyBest = top
                anyDistance = distance
            }
            if isClear(top),
               distance < clearDistance || (distance == clearDistance && top < clearBest!) {
                clearBest = top
                clearDistance = distance
            }
        }
        return clearBest ?? anyBest
    }

    /// Piston anchor (P1-1): the Collision surface the piston must emerge from
    /// is the one directly under its fully raised tread. The marker's own row
    /// is not that surface — it leaves the world bottom 64 px below the floor
    /// on 40 of 46 pistons and 48 px below on 3 more (only 3 are anchored on
    /// the surface already; edge-grazing hits under the fallback plane make
    /// 6/46 lethal with the old anchor). Three pistons (L01S15 x128,
    /// L02S23/L05S23 x400) sit at y=pixelHeight: their hit spans DO carry
    /// Collision cells (tops 160/192 and 272) but NONE at or below the raised
    /// tread (anchor+travel = 64), so the query resolves to the GLOBAL
    /// `fallbackPlaneY` — the map's lowest cell top (48 on all three maps),
    /// not any local floor.
    func pistonGroundY(markerX: CGFloat, markerBottomY: CGFloat) -> CGFloat {
        let x0 = markerX + GameConstants.pistonHitXInset
        return groundY(x0: x0, x1: x0 + GameConstants.pistonHitWidth,
                       atOrBelow: markerBottomY + GameConstants.pistonTravel)
    }

    /// Horizontal run merges per row, one tile tall — the exact geometry the
    /// tile map renderer published before the query existed. Rows are emitted
    /// top to bottom and runs left to right so consumers see a byte-stable
    /// order.
    var collisionRects: [CGRect] {
        guard !cells.isEmpty else { return [] }
        var tops: [CGFloat] = []
        for cell in cells where !tops.contains(cell.top) { tops.append(cell.top) }
        tops.sort(by: >)
        var rects: [CGRect] = []
        for top in tops {
            let rowCells = cells.filter { $0.top == top }.sorted { $0.x0 < $1.x0 }
            var run = rowCells[0]
            for cell in rowCells.dropFirst() {
                if cell.x0 == run.x1 {
                    run.x1 = cell.x1
                } else {
                    rects.append(CGRect(x: run.x0, y: run.top - tileHeight, width: run.x1 - run.x0, height: tileHeight))
                    run = cell
                }
            }
            rects.append(CGRect(x: run.x0, y: run.top - tileHeight, width: run.x1 - run.x0, height: tileHeight))
        }
        return rects
    }
}

/// P1-5: one beam field entity. Every visual side of a beam (the imported
/// `blk_beam_up`/`blk_beam_down` marker pair) shares this single hit-point
/// pool and the field is destroyed as a unit — issue #9: 25 hits per beam,
/// not 25 per side. SpriteKit-free so the Linux harness can execute the pool.
final class BeamFieldModel {
    static let sharedHitPoints = 25

    private(set) var remainingHitPoints = BeamFieldModel.sharedHitPoints
    private var destructionNotified = false
    private var destructionHandlers: [() -> Void] = []

    var isActive: Bool { remainingHitPoints > 0 }

    /// Register a destruction side effect. Handlers must capture their subject
    /// WEAKLY: the field owns the handler list, so a handler holding a strong
    /// reference to a side would close a field ↔ side retain cycle and leak
    /// every beam of every visited level.
    func onDestroyed(_ handler: @escaping () -> Void) {
        destructionHandlers.append(handler)
    }

    /// Returns true exactly once: on the hit that empties the shared pool.
    @discardableResult
    func registerHit() -> Bool {
        guard isActive else { return false }
        remainingHitPoints -= 1
        guard remainingHitPoints <= 0, !destructionNotified else { return false }
        destructionNotified = true
        for handler in destructionHandlers { handler() }
        return true
    }
}

/// Groups beam marker boxes into fields: boxes whose x intervals strictly
/// overlap belong to the same beam (an up/down pair is one beam). SpriteKit-
/// free so both the level runtime and the measurement harness share it.
enum TMXBeamGrouping {
    static func groups(for boxes: [CGRect]) -> [[Int]] {
        // Deterministic total order: minX first, original marker index as
        // tie-break (Swift's sort is unstable; the measurement mirror keys
        // (minX, index) and compares groups byte-exact).
        let indexed = boxes.enumerated().sorted { a, b in
            if a.element.minX != b.element.minX { return a.element.minX < b.element.minX }
            return a.offset < b.offset
        }
        var groups: [[Int]] = []
        var current: [Int] = []
        var currentMaxX: CGFloat = 0
        for (index, box) in indexed {
            if !current.isEmpty, box.minX >= currentMaxX {
                groups.append(current)
                current = []
            }
            current.append(index)
            currentMaxX = max(currentMaxX, box.maxX)
        }
        if !current.isEmpty { groups.append(current) }
        return groups
    }
}

enum TMXMapLoaderError: Error, CustomStringConvertible {
    case resourceNotFound(String)
    case unreadableResource(String)
    case invalidXML(String)
    case unsupportedEncoding(String)
    case unsupportedCompression(String)
    case invalidLayerData(String)

    var description: String {
        switch self {
        case .resourceNotFound(let name): return "TMX resource not found: \(name)"
        case .unreadableResource(let name): return "TMX resource unreadable: \(name)"
        case .invalidXML(let message): return "TMX XML error: \(message)"
        case .unsupportedEncoding(let value): return "Unsupported TMX encoding: \(value)"
        case .unsupportedCompression(let value): return "Unsupported TMX compression: \(value)"
        case .invalidLayerData(let name): return "Invalid TMX layer data: \(name)"
        }
    }
}

final class TMXMapLoader {
    static func load(resource name: String, bundle: Bundle = .main) throws -> TMXMapData {
        guard let url = bundle.url(forResource: name, withExtension: "tmx") else {
            throw TMXMapLoaderError.resourceNotFound(name)
        }
        guard let data = try? Data(contentsOf: url) else {
            throw TMXMapLoaderError.unreadableResource(name)
        }

        let delegate = TMXParserDelegate()
        let parser = XMLParser(data: data)
        parser.delegate = delegate
        let ok = parser.parse()
        if let error = delegate.error {
            throw error
        }
        if !ok {
            throw TMXMapLoaderError.invalidXML(parser.parserError?.localizedDescription ?? "unknown parser error")
        }
        return delegate.makeMap()
    }
}

private final class TMXParserDelegate: NSObject, XMLParserDelegate {
    private var mapWidth = 0
    private var mapHeight = 0
    private var mapTileWidth = 0
    private var mapTileHeight = 0
    private var mapProperties: [String: String] = [:]

    private var tilesets: [TMXTileset] = []
    private var imageLayers: [TMXImageLayer] = []
    private var layers: [TMXLayer] = []
    private var objectGroups: [TMXObjectGroup] = []

    private var currentTileset: TMXTileset?
    private var currentImageLayer: TMXImageLayer?
    private var currentLayerName: String?
    private var currentLayerWidth = 0
    private var currentLayerHeight = 0
    private var currentDataEncoding = ""
    private var currentDataCompression = ""
    private var currentDataText = ""
    private var collectingData = false

    private var currentObjectGroupName: String?
    private var currentObjects: [TMXObject] = []
    private var currentObject: TMXObject?

    private(set) var error: Error?

    func makeMap() -> TMXMapData {
        return TMXMapData(
            width: mapWidth,
            height: mapHeight,
            tileWidth: mapTileWidth,
            tileHeight: mapTileHeight,
            properties: mapProperties,
            tilesets: tilesets,
            imageLayers: imageLayers,
            layers: layers,
            objectGroups: objectGroups
        )
    }

    func parser(_ parser: XMLParser, didStartElement elementName: String,
                namespaceURI: String?, qualifiedName qName: String?,
                attributes attributeDict: [String : String] = [:]) {
        switch elementName {
        case "map":
            mapWidth = int(attributeDict["width"])
            mapHeight = int(attributeDict["height"])
            mapTileWidth = int(attributeDict["tilewidth"])
            mapTileHeight = int(attributeDict["tileheight"])

        case "tileset":
            currentTileset = TMXTileset(
                firstGID: uint(attributeDict["firstgid"]),
                name: attributeDict["name"] ?? "tileset",
                tileWidth: int(attributeDict["tilewidth"]),
                tileHeight: int(attributeDict["tileheight"])
            )

        case "imagelayer":
            currentImageLayer = TMXImageLayer(
                name: attributeDict["name"] ?? "image",
                imageSource: "",
                imageWidth: 0,
                imageHeight: 0
            )

        case "image":
            if currentTileset != nil {
                currentTileset?.imageSource = attributeDict["source"] ?? ""
                currentTileset?.imageWidth = int(attributeDict["width"])
                currentTileset?.imageHeight = int(attributeDict["height"])
            } else if currentImageLayer != nil {
                currentImageLayer?.imageSource = attributeDict["source"] ?? ""
                currentImageLayer?.imageWidth = int(attributeDict["width"])
                currentImageLayer?.imageHeight = int(attributeDict["height"])
            }

        case "layer":
            currentLayerName = attributeDict["name"] ?? "layer"
            currentLayerWidth = int(attributeDict["width"])
            currentLayerHeight = int(attributeDict["height"])

        case "data":
            currentDataEncoding = attributeDict["encoding"] ?? ""
            currentDataCompression = attributeDict["compression"] ?? ""
            currentDataText = ""
            collectingData = true

        case "objectgroup":
            currentObjectGroupName = attributeDict["name"] ?? "objects"
            currentObjects = []

        case "object":
            currentObject = TMXObject(
                name: attributeDict["name"] ?? "",
                gid: attributeDict["gid"].map { uint($0) },
                x: cgfloat(attributeDict["x"]),
                y: cgfloat(attributeDict["y"]),
                width: cgfloat(attributeDict["width"]),
                height: cgfloat(attributeDict["height"])
            )

        case "property":
            let name = attributeDict["name"] ?? ""
            let value = attributeDict["value"] ?? ""
            if currentObject != nil {
                currentObject?.properties[name] = value
            } else if currentLayerName == nil && currentTileset == nil {
                mapProperties[name] = value
            }

        default:
            break
        }
    }

    func parser(_ parser: XMLParser, foundCharacters string: String) {
        if collectingData {
            currentDataText += string
        }
    }

    func parser(_ parser: XMLParser, didEndElement elementName: String,
                namespaceURI: String?, qualifiedName qName: String?) {
        switch elementName {
        case "tileset":
            if let tileset = currentTileset {
                tilesets.append(tileset)
            }
            currentTileset = nil

        case "imagelayer":
            if let imageLayer = currentImageLayer, !imageLayer.imageSource.isEmpty {
                imageLayers.append(imageLayer)
            }
            currentImageLayer = nil

        case "data":
            collectingData = false

        case "layer":
            guard error == nil, let name = currentLayerName else { return }
            do {
                let gids = try decodeLayerData(
                    currentDataText,
                    encoding: currentDataEncoding,
                    compression: currentDataCompression,
                    expectedCount: currentLayerWidth * currentLayerHeight,
                    layerName: name
                )
                layers.append(TMXLayer(name: name, width: currentLayerWidth, height: currentLayerHeight, gids: gids))
            } catch {
                self.error = error
                parser.abortParsing()
            }
            currentLayerName = nil
            currentDataText = ""

        case "object":
            if let object = currentObject {
                currentObjects.append(object)
            }
            currentObject = nil

        case "objectgroup":
            if let name = currentObjectGroupName {
                objectGroups.append(TMXObjectGroup(name: name, objects: currentObjects))
            }
            currentObjectGroupName = nil
            currentObjects = []

        default:
            break
        }
    }

    private func decodeLayerData(_ text: String, encoding: String, compression: String,
                                 expectedCount: Int, layerName: String) throws -> [UInt32] {
        if !compression.isEmpty {
            throw TMXMapLoaderError.unsupportedCompression(compression)
        }

        if encoding == "base64" {
            let compact = text.components(separatedBy: .whitespacesAndNewlines).joined()
            guard let data = Data(base64Encoded: compact) else {
                throw TMXMapLoaderError.invalidLayerData(layerName)
            }
            guard data.count >= expectedCount * 4 else {
                throw TMXMapLoaderError.invalidLayerData(layerName)
            }

            var result: [UInt32] = []
            result.reserveCapacity(expectedCount)
            for i in 0..<expectedCount {
                let offset = i * 4
                let value = UInt32(data[offset])
                    | (UInt32(data[offset + 1]) << 8)
                    | (UInt32(data[offset + 2]) << 16)
                    | (UInt32(data[offset + 3]) << 24)
                result.append(value)
            }
            return result
        }

        if encoding == "csv" {
            let values = text
                .split { $0 == "," || $0 == "\n" || $0 == "\r" || $0 == "\t" || $0 == " " }
                .compactMap { UInt32($0) }
            guard values.count == expectedCount else {
                throw TMXMapLoaderError.invalidLayerData(layerName)
            }
            return values
        }

        throw TMXMapLoaderError.unsupportedEncoding(encoding)
    }

    private func int(_ value: String?) -> Int { Int(value ?? "") ?? 0 }
    private func uint(_ value: String?) -> UInt32 { UInt32(value ?? "") ?? 0 }
    private func cgfloat(_ value: String?) -> CGFloat {
        guard let value = value, let number = Double(value) else { return 0 }
        return CGFloat(number)
    }
}

// MARK: - Source-marker classification

/// Every `source_marker.sourceBlock` family the level runtime knows how to resolve.
///
/// This enum, not a chain of string tests, is the level content factory's marker table.
/// `TMXLevelRuntime` switches over it exhaustively with no `default:` arm, so adding a family
/// here without teaching the runtime about it is a compile error rather than a silently dropped
/// marker. `classify(sourceBlock:)` returns `nil` when nothing matches and the runtime records
/// that as an observable unmatched marker: "silently ignored" is not a representable outcome
/// anywhere on this path.
enum TMXSourceMarkerKind: String, CaseIterable {
    case forceField
    case highVoltage
    case blinker
    case stageEnd
    case changingRoom
    case beaconBase
    case controlBeacon
    /// Imported static artwork: already solid in the Collision layer and already drawn by the
    /// baked `Original Static Scenery` image layer. The source table records no action here, so
    /// the runtime records it and deliberately adds no behaviour.
    case inertScenery
    /// A distinct action cell exists in the source data but its type cannot be identified from
    /// anything in this repository. Recorded and labeled, never armed and never guessed.
    case unconfirmedAction

    /// A safe model is a recorded, labeled substitution for content the factory cannot express
    /// as a gameplay object without inventing behaviour. It is never a silent visual drop.
    var isSafeModel: Bool {
        switch self {
        case .inertScenery, .unconfirmedAction:
            return true
        case .forceField, .highVoltage, .blinker, .stageEnd, .changingRoom, .beaconBase, .controlBeacon:
            return false
        }
    }

    /// The label every safe model must carry in the coverage meter and in debug rendering; an
    /// unlabeled placeholder is prohibited.
    var safeModelLabel: String {
        switch self {
        case .inertScenery:
            return "SAFE-MODEL inert-scenery: imported static artwork, no action in the source table"
        case .unconfirmedAction:
            return "SAFE-MODEL unconfirmed-action: a distinct source action cell exists but its type is not identifiable in-tree; behaviour deliberately NOT implemented"
        case .forceField, .highVoltage, .blinker, .stageEnd, .changingRoom, .beaconBase, .controlBeacon:
            return ""
        }
    }

    /// The matcher. The seven original tests keep their historical order: no shipped value
    /// currently matches two of them, but that is a property of today's data and this is not the
    /// place to silently change the assumption.
    static func classify(sourceBlock: String) -> TMXSourceMarkerKind? {
        if sourceBlock.isEmpty { return nil }
        if sourceBlock.contains("beam_") { return .forceField }
        if sourceBlock.contains("topdown_electro") { return .highVoltage }
        if sourceBlock.contains("blinker") { return .blinker }
        if sourceBlock.contains("stage_end") { return .stageEnd }
        if sourceBlock.contains("changing_room") { return .changingRoom }
        if sourceBlock.contains("beacon_base") { return .beaconBase }
        if sourceBlock.contains("control_beacon") { return .controlBeacon }
        if sourceBlock.contains("mushroom") { return .inertScenery }
        if sourceBlock.contains("waggon") { return .inertScenery }
        if sourceBlock.contains("gunMachine_BOTTOM") { return .unconfirmedAction }
        return nil
    }

    /// Footprint in source cells, measured from the shipped Collision layer rather than assumed:
    /// `blk_mushroom` is a uniform 4x3 (9/9); the `blk_waggon` unit block is 5x3 (21/24, the
    /// 10- and 15-wide readings are adjacent waggons merged into one solid run); `blk_gunMachine_BOTTOM`
    /// is 4 wide on 18/18 with a height that bleeds into the terrain it stands on, so 3 cells is a
    /// bounded placeholder, not a claim about the original artwork.
    static func safeModelFootprintCells(sourceBlock: String) -> (width: Int, height: Int) {
        if sourceBlock.contains("waggon") { return (5, 3) }
        if sourceBlock.contains("mushroom") { return (4, 3) }
        if sourceBlock.contains("gunMachine_BOTTOM") { return (4, 3) }
        return (4, 3)
    }
}

/// A source marker the factory resolved to a safe model: an observable, labeled record carrying
/// its bounded footprint. `TMXLevelRuntime.safeModelMarkers` and the debug nodes derived from it
/// do not participate in physics, damage, scoring or spawning.
struct TMXSafeModelMarker {
    let kind: TMXSourceMarkerKind
    let sourceBlock: String
    let label: String
    let rect: CGRect
    let mapResource: String
}
