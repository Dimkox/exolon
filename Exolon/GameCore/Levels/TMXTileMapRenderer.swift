import Foundation
import SpriteKit

final class TMXTileMapRenderer {
    let node = SKNode()
    let collisionRects: [CGRect]

    private let map: TMXMapData
    private var sheetTextures: [String: SKTexture] = [:]

    init(map: TMXMapData, surfaceQuery: TMXSurfaceQuery) {
        self.map = map
        // P1-2/P1-1 (wave B): the renderer no longer owns a private Collision
        // interpretation. The shared SpriteKit-free surface query (built once
        // per load by the level runtime) produces the exact same merged
        // horizontal runs — one tile tall, rows top to bottom, runs left to
        // right — that spawn and piston anchoring read their ground from.
        self.collisionRects = surfaceQuery.collisionRects
        node.name = "tmx-map"
        node.zPosition = 0
        renderImageLayers()
        renderVisibleLayers()
    }

    private func renderImageLayers() {
        var z: CGFloat = -5
        for layer in map.imageLayers {
            let imageName = URL(fileURLWithPath: layer.imageSource)
                .deletingPathExtension().lastPathComponent
            let texture = SKTexture(imageNamed: imageName)
            texture.filteringMode = .nearest

            let width = layer.imageWidth > 0 ? CGFloat(layer.imageWidth) : map.pixelWidth
            let height = layer.imageHeight > 0 ? CGFloat(layer.imageHeight) : map.pixelHeight
            let sprite = SKSpriteNode(texture: texture, size: CGSize(width: width, height: height))
            sprite.name = layer.name
            sprite.anchorPoint = CGPoint(x: 0, y: 0)
            sprite.position = .zero
            sprite.zPosition = z
            node.addChild(sprite)
            z += 0.1
        }
    }

    private func renderVisibleLayers() {
        var z: CGFloat = 0
        for layer in map.layers where layer.name.lowercased() != "collision" {
            render(layer: layer, zPosition: z)
            z += 1
        }
    }

    private func render(layer: TMXLayer, zPosition: CGFloat) {
        guard layer.gids.count == layer.width * layer.height else { return }

        for row in 0..<layer.height {
            for column in 0..<layer.width {
                let rawGID = layer.gids[row * layer.width + column]
                let gid = rawGID & 0x1FFF_FFFF // remove Tiled flip flags
                guard gid != 0, let tileset = tileset(for: gid) else { continue }
                let localIndex = Int(gid - tileset.firstGID)
                guard let texture = tileTexture(tileset: tileset, localIndex: localIndex) else { continue }

                let sprite = SKSpriteNode(
                    texture: texture,
                    size: CGSize(width: tileset.tileWidth, height: tileset.tileHeight)
                )
                sprite.anchorPoint = CGPoint(x: 0, y: 0)
                sprite.position = CGPoint(
                    x: CGFloat(column * map.tileWidth),
                    y: map.pixelHeight - CGFloat((row + 1) * map.tileHeight)
                )
                sprite.zPosition = zPosition
                node.addChild(sprite)
            }
        }
    }

    private func tileset(for gid: UInt32) -> TMXTileset? {
        return map.tilesets
            .filter { $0.firstGID <= gid }
            .max { $0.firstGID < $1.firstGID }
    }

    private func tileTexture(tileset: TMXTileset, localIndex: Int) -> SKTexture? {
        guard tileset.imageWidth > 0, tileset.imageHeight > 0,
              tileset.tileWidth > 0, tileset.tileHeight > 0 else { return nil }

        let imageName = URL(fileURLWithPath: tileset.imageSource)
            .deletingPathExtension().lastPathComponent
        let sheet: SKTexture
        if let cached = sheetTextures[imageName] {
            sheet = cached
        } else {
            let loaded = SKTexture(imageNamed: imageName)
            loaded.filteringMode = .nearest
            sheetTextures[imageName] = loaded
            sheet = loaded
        }

        let columns = max(1, tileset.imageWidth / tileset.tileWidth)
        let rows = max(1, tileset.imageHeight / tileset.tileHeight)
        // Never let a GID spill into a wrong texture. Later Exolon maps change
        // firstgid values and even the dimensions used for the same source image.
        guard localIndex >= 0, localIndex < columns * rows else { return nil }
        let column = localIndex % columns
        let rowFromTop = localIndex / columns

        let rect = CGRect(
            x: CGFloat(column * tileset.tileWidth) / CGFloat(tileset.imageWidth),
            y: 1.0 - CGFloat((rowFromTop + 1) * tileset.tileHeight) / CGFloat(tileset.imageHeight),
            width: CGFloat(tileset.tileWidth) / CGFloat(tileset.imageWidth),
            height: CGFloat(tileset.tileHeight) / CGFloat(tileset.imageHeight)
        )
        let texture = SKTexture(rect: rect, in: sheet)
        texture.filteringMode = .nearest
        return texture
    }
}
