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
