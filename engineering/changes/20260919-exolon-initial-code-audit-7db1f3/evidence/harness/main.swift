import FoundationXML
import Foundation
let env = ProcessInfo.processInfo.environment
let fixturesDir = env["TMX_FIXTURES"] ?? "fixtures"
let resourcesDir = env["TMX_RESOURCES"] ?? "Exolon/Resources"
let bundle = Bundle(path: fixturesDir)!
func dump(_ name: String) {
    do {
        let m = try TMXMapLoader.load(resource: name, bundle: bundle)
        var s = "OK w=\(m.width) h=\(m.height) tw=\(m.tileWidth) layers=\(m.layers.count) tilesets=\(m.tilesets.count) ogs=\(m.objectGroups.count) props=\(m.properties.sorted { $0.key < $1.key }.map{ "\($0)=\($1)" })"
        for g in m.objectGroups { for o in g.objects {
            s += " | obj(\(o.name)) gid=\(o.gid.map(String.init) ?? "nil") x=\(o.x) y=\(o.y) w=\(o.width) h=\(o.height) props=\(o.properties.sorted { $0.key < $1.key }.map{ "\($0)=\($1)" }) bl=\(m.worldBottomLeft(for: o))" } }
        for l in m.layers { s += " | layer(\(l.name)) \(l.width)x\(l.height) gids=\(l.gids.count)" }
        print("[\(name)] \(s)")
    } catch {
        print("[\(name)] THREW \((error as? TMXMapLoaderError)?.description ?? String(describing: error))")
    }
}
let fixtures = ["f01_foreign_root","f02_empty_map","f03_gzip","f04_zlib","f05_typo_coord","f06_prop_scope","f08_csv_short","f09_b64_trunc","f10_b64_extra","f11_enc_xml","f12_firstgid_far","f13_no_layers","f14_unclosed","f15_empty","f16_neg_float","f17_huge_dims","f18_zero_layer"]
for f in fixtures { dump(f) }
// real corpus aggregate
let fm = try! FileManager.default.contentsOfDirectory(atPath: resourcesDir).filter { $0.hasSuffix(".tmx") }.sorted()
var ok = 0, bad = [String]()
for f in fm {
    let name = String(f.dropLast(4))
    do { _ = try TMXMapLoader.load(resource: name, bundle: Bundle(path: resourcesDir)!); ok += 1 }
    catch { bad.append("\(f): \(error)") }
}
print("REAL MAPS ok=\(ok)/\(fm.count) failures=\(bad.count) \(bad.prefix(5))")
// L01S10 capsule claim
let z9 = try! TMXMapLoader.load(resource: "L01S10", bundle: Bundle(path: resourcesDir)!)
for o in z9.objects(named: "capsule") + z9.objects(named: "piston") {
    print("L01S10 obj \(o.name) x=\(o.x) y=\(o.y) w=\(o.width) h=\(o.height) mode=\(o.properties["coordinateMode"] ?? "-") bottomLeft=\(z9.worldBottomLeft(for: o)) pixelH=\(z9.pixelHeight)")
}
