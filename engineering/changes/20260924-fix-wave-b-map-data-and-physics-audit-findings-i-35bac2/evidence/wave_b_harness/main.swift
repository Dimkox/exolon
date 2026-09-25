// Wave B зонд: исполняет НАСТОЯЩИЙ продуктовый SpriteKit-free код
// (TMXMapLoader.swift + GameConstants.swift) на всех 125 картах и печатает
// числа, которые python-измеритель `wave_b_check.py` сверяет со своей
// зеркальной формулой:
//   *Spawn: TMXMapData.resolvedPlayerBottom(using:) — опора спавна (P1-2);
//   *Piston: TMXSurfaceQuery.pistonGroundY — якорь поршня от Collision-
//     поверхности под поднятым протектором (P1-1);
//   *Beam:   TMXBeamGrouping.groups + BeamFieldModel — одна общая база 25 хитов
//     на поле (P1-5);
//   *Cull:   константыderived-cull границы пули от clamp-константы игрока (P1-3).
//
// Продуктовый исходник не правится: в сборочный каталог кладётся копия
// TMXMapLoader.swift с ровно одной добавленной строкой `import FoundationXML`
// (дельта проверяется байт-в-байт в run.sh, как в закоммиченном
// piston-anchor-harness пакета 20260921-...-2e7698).
import Foundation

let env = ProcessInfo.processInfo.environment
let resourcesDir = env["TMX_RESOURCES"] ?? "Exolon/Resources"
let bundle = Bundle(path: resourcesDir)!
let files = (try? FileManager.default.contentsOfDirectory(atPath: resourcesDir))?.sorted() ?? []

// MARK: - закреплённая геометрия (P1-3 / INV-002)
print("GEOMETRY logicalWidth=\(GameConstants.logicalSize.width) logicalHeight=\(GameConstants.logicalSize.height) "
    + "playerMinX=\(GameConstants.playerMinimumCenterX) playerMaxX=\(GameConstants.playerMaximumCenterX) "
    + "bulletW=\(GameConstants.blasterBulletSize.width) bulletH=\(GameConstants.blasterBulletSize.height) "
    + "muzzleX=\(GameConstants.blasterMuzzleOffsetX) cullMaxX=\(GameConstants.blasterCullMaximumX) "
    + "cullMinX=\(GameConstants.blasterCullMinimumX) "
    + "grenadeW=\(GameConstants.grenadeSize.width) grenadeThrowX=\(GameConstants.grenadeThrowOffsetX) "
    + "grenadeCullMaxX=\(GameConstants.grenadeCullMaximumX) grenadeCullMinX=\(GameConstants.grenadeCullMinimumX) "
    + "footInset=\(GameConstants.footSupportHorizontalInset) defaultGroundY=\(GameConstants.defaultGroundY) "
    + "pistonTravel=\(GameConstants.pistonTravel) pistonHitXInset=\(GameConstants.pistonHitXInset) "
    + "pistonHitWidth=\(GameConstants.pistonHitWidth) pistonNodeH=\(GameConstants.pistonNodeSize.height)")

// MARK: - P1-5: общий пул хит-поинтов (исполняемый)
let pool = BeamFieldModel()
var aliveAfter24 = true
var destroyHitIndex = 0
var notifyCount = 0
pool.onDestroyed { notifyCount += 1 }
for i in 1...26 {
    let destroyedNow = pool.registerHit()
    if i <= 24 { aliveAfter24 = aliveAfter24 && pool.isActive && !destroyedNow }
    if destroyedNow, destroyHitIndex == 0 { destroyHitIndex = i }
}
let extraHitAfterDestroy = pool.registerHit()
print("BEAMPOOL sharedHitPoints=\(BeamFieldModel.sharedHitPoints) aliveAfter24=\(aliveAfter24) "
    + "destroyHitIndex=\(destroyHitIndex) notifyCount=\(notifyCount) isActiveAfter=\(pool.isActive) "
    + "extraHit=\(extraHitAfterDestroy) remaining=\(pool.remainingHitPoints)")

// MARK: - обход корпуса
func fmt(_ v: CGFloat) -> String {
    // числа целые (тайловая сетка); печатаем без разделителя разрядов
    return String(format: "%.0f", v)
}

var ok = 0
var failed = 0
for file in files where file.hasSuffix(".tmx") {
    let name = String(file.dropLast(4))
    do {
        let map = try TMXMapLoader.load(resource: name, bundle: bundle)
        ok += 1
        let query = map.surfaceQuery
        let plane = query.fallbackPlaneY
        print("PLANESRC map=\(file) cells=\(query.cells.count) plane=\(fmt(plane))")

        // R1-1: геометрия terrainRects исполненным продуктом — сверяется в
        // python-измерителе с портировкой base-коммитного buildCollisionRects
        // (порядок+число+координаты). Мутация продуктовой формулы краснит INV-002.
        let rects = query.collisionRects
        let ser = rects.map {
            String(format: "%.1f,%.1f,%.1f,%.1f", $0.minX, $0.minY, $0.width, $0.height)
        }.joined(separator: ";")
        print("RECTS map=\(file) count=\(rects.count) coords=\(ser)")

        // P1-2: спавн через общий запрос поверхности (bounded ±one tile)
        if let vitorc = map.object(named: "vitorc") {
            let marker = map.worldBottomLeft(for: vitorc)
            let centerX = marker.x + GameConstants.playerSpriteSize.width * 0.5
            let halfBody = GameConstants.playerStandingMovementSize.width * 0.5
            let inset = GameConstants.footSupportHorizontalInset
            let allTops = query.surfaceTops(x0: centerX - halfBody + inset,
                                            x1: centerX + halfBody - inset)
            let window = allTops.filter { abs($0 - marker.y) <= CGFloat(map.tileHeight) }
            let bottom = map.resolvedPlayerBottom(using: query)
            let list = window.map { fmt($0) }.joined(separator: ";")
            print("SPAWN map=\(file) markerX=\(fmt(marker.x)) markerFeet=\(fmt(marker.y)) "
                + "spawnFeet=\(fmt(bottom.y)) plane=\(fmt(query.fallbackPlaneY)) windowTops=[\(list)]")
        }

        // P1-1: якорь поршня
        for object in map.objects(named: "piston") {
            let bottom = map.worldBottomLeft(for: object)
            let g = query.pistonGroundY(markerX: bottom.x, markerBottomY: bottom.y)
            print("PISTON map=\(file) x=\(fmt(bottom.x)) markerY=\(fmt(bottom.y)) groundY=\(fmt(g))")
        }

        // P1-5: группировка сторон луча (коробки — дословная арифметика
        // TMXLevelRuntime, закреплена измерителем regex'ом)
        var boxes: [CGRect] = []
        for group in map.objectGroups {
            for object in group.objects where object.name == "source_marker" {
                let source = object.properties["sourceBlock"] ?? ""
                guard source.contains("beam_") else { continue }
                let sx = CGFloat(Int(object.properties["sourceX"] ?? "") ?? 0) * 16
                let syTop = CGFloat(Int(object.properties["sourceY"] ?? "") ?? 0) * 16
                let bottomY = map.pixelHeight - syTop - 32
                boxes.append(CGRect(x: sx, y: max(0, bottomY - 240), width: 48, height: 272))
            }
        }
        if !boxes.isEmpty {
            let groups = TMXBeamGrouping.groups(for: boxes)
            let desc = groups.map { g in g.map { String($0) }.joined(separator: "+") }.joined(separator: ",")
            print("BEAM map=\(file) boxes=\(boxes.count) fields=\(groups.count) groups=[\(desc)]")
        }
    } catch {
        failed += 1
        print("LOADFAIL map=\(file) error=\(error)")
    }
}
print("SUMMARY maps_ok=\(ok) failed=\(failed)")
if failed != 0 || ok != 125 {
    exit(1)
}
