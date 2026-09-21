// P1-1 зонд: какой `groundY` реально выдаёт ПОДОВЫЙ загрузчик для каждого
// объекта `piston` во всех 125 картах. Файл продуктового кода не правится —
// собирается его копия с ровно одной добавленной строкой импорта (см. run.sh),
// поэтому числа ниже — вывод настоящего `TMXMapLoader.worldBottomLeft(for:)`,
// а не python-реплики.
import Foundation

let env = ProcessInfo.processInfo.environment
let resourcesDir = env["TMX_RESOURCES"] ?? "Exolon/Resources"
let bundle = Bundle(path: resourcesDir)!
let files = (try? FileManager.default.contentsOfDirectory(atPath: resourcesDir))?.sorted() ?? []
var ok = 0
var failed = 0
for file in files where file.hasSuffix(".tmx") {
    let name = String(file.dropLast(4))
    do {
        let map = try TMXMapLoader.load(resource: name, bundle: bundle)
        ok += 1
        for group in map.objectGroups {
            for object in group.objects where object.name == "piston" {
                let bottom = map.worldBottomLeft(for: object)
                print("PISTON \(file) x=\(object.x) y=\(object.y) w=\(object.width) "
                    + "h=\(object.height) PH=\(map.pixelHeight) groundY=\(bottom.y) "
                    + "mode=\(object.properties["coordinateMode"] ?? "-")")
            }
        }
    } catch {
        failed += 1
        print("LOAD-FAIL \(file) \(error)")
    }
}
print("SUMMARY maps_ok=\(ok) maps_failed=\(failed)")

// Семантика `CGRect.intersects` на нулевой площади: именно от неё зависит, убивает
// ли поршень, у которого верх блока в полностью выпущенном состоянии совпадает с
// поверхностью пола (42 объекта из 46). На Linux это значение — только указатель:
// решающим является поведение CoreGraphics на macOS (см. macOS-контур).
// Контроль обязан перевернуться:overlap в 1 px должен считаться, иначе вся модель
// классов ниже неразумна.
let base = CGRect(x: 0, y: 0, width: 42, height: 64)
let flush = CGRect(x: 0, y: 64, width: 46, height: 63)
let onePx = CGRect(x: 0, y: 63, width: 46, height: 63)
let deep = CGRect(x: 0, y: 32, width: 46, height: 63)
print("SEMANTICS flush=\(base.intersects(flush)) onePx=\(base.intersects(onePx)) deep=\(base.intersects(deep))")
