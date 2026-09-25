#!/usr/bin/env python3
"""v3-измеритель аудита Exolon: каждое число отчёта v3 = вывод этой программы.

FROZEN-HISTORICAL (wave E1, 2026-09-25; issue #22 item 2). Это зеркало аудита 2026-09-20:
его вывод описывает ДОФИКСОВОЕ дерево - 76 разобранных маркеров из 127, 51 потерянный, 32
карты с потерей, 125 карт корпуса. В дереве после wave A-D эти числа не являются текущим
состоянием продукта: поддерживаемая истина живёт в evidence/wave_c_check.py пакета
20260924-close-wave-c-content-and-factory-audit-findings-f2d90a (он же печатает об этом
WARNING), а не здесь. Поведение этого файла намеренно не менялось (no behavior change,
заголовок - единственная правка): на этих байтах держится отчёт v3 и пин legacy-базлайна
wave C. Ограничение заморозки измерено в wave E1: после wave B программа до вывода 76/51
не доходит - она abort'ится с rc=1 на пине BlasterBullet (из продукта убрана формулировка
"logicalSize.width + 16", которую зеркало ищет regex'ом); до wave B она печатала 76/127
с rc=0. И то, и другое - описание прошлого дерева, а не утверждение о текущем продукте.

rc=0 ⇔ все замеры совпали с EXPECTED (то есть с цифрами в
engineering/reports/exolon-full-audit-20260920-v3.md). Каждый зонд имеет контроль,
который обязан дать другое число; если контроль не переворачивается — итог rc=1.

Разбор TMX — только через xml.etree. Regex-разбор object-элементов в этом репозитории
НЕприменим: самозакрывающиеся <object/> и соседние объекты смещают атрибуты
(проверено: regex даёт 97 маркеров вместо 127, а `h=` вместо `height=` даёт
«3 летальных поршня» вместо 1+2).

Запуск: python3 evidence/v3_measurements.py [--root <путь>] [--json]
"""
from __future__ import annotations

import argparse
import base64
import collections
import hashlib
import json
import pathlib
import re
import struct
import sys
import xml.etree.ElementTree as ET

FEET_BOX_INSET = 20        # movementHitbox 46 px ± врез по 3 px => [cx-20, cx+20]
SPAWN_HALF_W = 24          # spawnCenter.x = bottom.x + playerSpriteSize.width/2 (48/2)
PISTON_TRAVEL = 64         # exposedY = groundY, высота ноды 64
PLAYER_DAMAGE_H = 63       # playerStandingDamageSize.height
SUPPORTED_TOL = 1.5        # Player.swift:192
LANDING_TOL = 1.5          # Player.swift:145

EXPECTED: dict[str, object] = {
    "maps_total": 125,
    "maps_geometry": "35x24@16",
    "objects_total": 680,
    "unique_levels": 101,
    "redundant_copies": 24,
    "reskin_pairs_L02_L05": 23,
    "other_dup_groups": 1,
    "markers_total": 127,
    "markers_read": 76,
    "markers_lost": 51,
    "markers_lost_maps": 32,
    "markers_lost_kinds": {"blk_waggon": 24, "blk_gunMachine_BOTTOM": 18, "blk_mushroom": 9},
    "markers_control_drop_beam": 71,
    "pistons_objects": 46,
    "pistons_maps": 27,
    "pistons_lethal_area": 1,
    "pistons_edge": 2,
    "pistons_below_feet": 43,
    "pistons_bottom_hist": {"96": 1, "0": 2, "-32": 12, "-48": 15, "-64": 16},
    "spawn_legacy_exact": 35,
    "spawn_clean": 37,
    "spawn_lift": 59,
    "spawn_drop": 29,
    "spawn_zero_delta_total": 125,
    "logical_width": 512,
    "bullet_kill_bound": 528,
    "player_clamp": 544,
    "maps_solid_at_or_beyond_512": 61,
    "beam_maps_up": 10,
    "beam_maps_down": 10,
    "beam_maps_both": 10,
    "beam_hit_points": 25,
    "beam_total_hits": 50,
    "double_launcher_objects": 19,
    "double_launcher_maps": 18,
    "texture_sites": 23,
    "texture_literal_names": 17,
    "texture_computed_sites": 6,
    "texture_union_names": 21,
    "texture_names_missing_on_disk": 0,
    "gen_terrain_declared": 117,
    "gen_terrain_used": 0,
    "gen_terrain_in_resources_phase": 1,
    "l01s04_dangling_gif": 2,
    "images_dir_exists": 0,
    "product_log_calls": 0,
    "loadcheckpoint_calls": 0,
    "clearcheckpoint_calls": 3,
    "shared_xcschemes": 0,
    "test_targets": 0,
    "product_xctest_files": 0,
}

HANDLED = ("beam_", "blinker", "changing_room", "stage_end", "beacon_base", "control_beacon", "topdown_electro")


def find_root(explicit: str | None) -> pathlib.Path:
    if explicit:
        return pathlib.Path(explicit).resolve()
    here = pathlib.Path(__file__).resolve()
    for cand in [here.parent, *here.parents]:
        if (cand / "Exolon" / "Resources").is_dir() and (cand / ".git").exists():
            return cand
    raise SystemExit("репозиторий не найден — передай --root")


def decode_layer(data: ET.Element) -> list[int]:
    text = (data.text or "").strip()
    if (data.get("encoding") or "") == "csv":
        return [int(x) for x in re.split(r"[,\s]+", text) if x]
    raw = base64.b64decode(re.sub(r"\s+", "", text))
    return list(struct.unpack("<%dI" % (len(raw) // 4), raw))


def load_map(path: pathlib.Path) -> dict:
    root = ET.parse(path).getroot()
    W, H = int(root.get("width")), int(root.get("height"))
    TW, TH = int(root.get("tilewidth")), int(root.get("tileheight"))
    PH = H * TH
    cells: list[tuple[float, float, float]] = []
    tiles_sig: list[tuple[str, tuple[int, ...]]] = []
    for lay in root.iter("layer"):
        d = lay.find("data")
        if d is None:
            continue
        g = decode_layer(d)
        tiles_sig.append((lay.get("name") or "", tuple(g)))
        if "Collision" not in (lay.get("name") or ""):
            continue
        for i, v in enumerate(g):
            if v:
                row, col = divmod(i, W)
                if row < H:
                    cells.append((col * TW, PH - (row + 1) * TH, PH - row * TH))
    objects: list[dict] = []
    for og in root.iter("objectgroup"):
        for o in og.findall("object"):
            props = tuple(sorted((p.get("name") or "", p.get("value") or "") for p in o.iter("property")))
            objects.append({"name": o.get("name") or "", "x": float(o.get("x") or 0),
                            "y": float(o.get("y") or 0), "w": float(o.get("width") or 0),
                            "h": float(o.get("height") or 0), "props": props, "PH": PH})
    return {"file": path.name, "W": W, "H": H, "TW": TW, "TH": TH, "PH": PH,
            "cells": cells, "objects": objects, "tiles_sig": tiles_sig,
            "text": path.read_text(encoding="utf-8")}


def canon_map(mp: dict) -> str:
    objs = sorted((o["name"], o["x"], o["y"], o["w"], o["h"], o["props"]) for o in mp["objects"])
    return hashlib.sha256(repr((mp["tiles_sig"], objs)).encode()).hexdigest()


def world_bottom(o: dict) -> float:
    return o["PH"] - (o["y"] + o["h"])


def source_block(o: dict) -> str:
    return dict(o["props"]).get("sourceBlock", "")


def stable_feet(mp: dict) -> float | None:
    """Ноги игрока после первого фикс-шага: правило опоры + посадка на плоскость."""
    v = next((o for o in mp["objects"] if o["name"] == "vitorc"), None)
    if v is None:
        return None
    feet = world_bottom(v)
    if not mp["cells"]:
        return None
    cx = v["x"] + SPAWN_HALF_W
    L, R = cx - FEET_BOX_INSET, cx + FEET_BOX_INSET
    if supported(mp, feet, L, R):
        return feet
    ground = min(tp for _, _, tp in mp["cells"])
    if feet <= ground:
        return ground
    cand = [tp for sx, _, tp in mp["cells"] if tp < feet - SUPPORTED_TOL and R > sx and L < sx + mp["TW"]]
    return max(cand) if cand else ground


def supported(mp: dict, feet: float, L: float, R: float, legacy: bool = False) -> bool:
    cx = L + FEET_BOX_INSET
    if legacy:
        return any(abs(tp - feet) < 0.001 and sx <= cx < sx + mp["TW"] for sx, _, tp in mp["cells"])
    return any(abs(tp - feet) <= SUPPORTED_TOL and R > sx and L < sx + mp["TW"] for sx, _, tp in mp["cells"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = find_root(args.root)
    got: dict[str, object] = {}
    controls: dict[str, bool] = {}
    maps = [load_map(p) for p in sorted((root / "Exolon" / "Resources").glob("*.tmx"))]

    # 1. геометрия и объём данных
    got["maps_total"] = len(maps)
    geom = {(m["W"], m["H"], m["TW"]) for m in maps}
    got["maps_geometry"] = f"{maps[0]['W']}x{maps[0]['H']}@{maps[0]['TW']}"
    controls["geometry_uniform"] = len(geom) == 1
    got["objects_total"] = sum(len(m["objects"]) for m in maps)

    # 2. уникальность контента (контроль: порт одной карты обязан создать новый класс)
    sig = {m["file"]: canon_map(m) for m in maps}
    groups = collections.defaultdict(list)
    for k, v in sig.items():
        groups[v].append(k)
    dup_groups = [sorted(g) for g in groups.values() if len(g) > 1]
    got["unique_levels"] = len(groups)
    got["redundant_copies"] = sum(len(g) - 1 for g in dup_groups)
    got["reskin_pairs_L02_L05"] = sum(1 for g in dup_groups
                                      if any(x.startswith("L02") for x in g) and any(x.startswith("L05") for x in g))
    got["other_dup_groups"] = sum(1 for g in dup_groups
                                  if not (any(x.startswith("L02") for x in g) and any(x.startswith("L05") for x in g)))
    mutated = dict(sig)
    # контроль обязан быть на члене дубликат-пары: мутация одиночной карты
    # не меняет число классов эквивалентности, и зонд выглядит «не перевернувшимся»
    pair = next((g for g in dup_groups if any(x.startswith("L05") for x in g)), None)
    if pair is None:
        controls["uniqueness_moves_on_mutation"] = False
    else:
        victim_name = pair[-1]
        victim = next(m for m in maps if m["file"] == victim_name)
        mutated[victim_name] = canon_map({**victim, "objects": victim["objects"] + [
            {"name": "ctrl", "x": 1.0, "y": 2.0, "w": 0.0, "h": 0.0, "props": (), "PH": victim["PH"]}]})
        controls["uniqueness_moves_on_mutation"] = len(set(mutated.values())) == len(groups) + 1

    # 3. покрытие source_marker
    def marker_split(handled: tuple[str, ...]):
        tot = read = 0
        lost = collections.Counter()
        lostmaps: set[str] = set()
        for m in maps:
            for o in m["objects"]:
                if o["name"] != "source_marker":
                    continue
                tot += 1
                sb = source_block(o)
                if any(s in sb for s in handled):
                    read += 1
                else:
                    lost[sb] += 1
                    lostmaps.add(m["file"])
        return tot, read, lost, lostmaps

    tot, read, lost, lostmaps = marker_split(HANDLED)
    got["markers_total"], got["markers_read"] = tot, read
    got["markers_lost"] = sum(lost.values())
    got["markers_lost_maps"] = len(lostmaps)
    got["markers_lost_kinds"] = dict(sorted(lost.items(), key=lambda kv: -kv[1]))
    _, _, lost_c, _ = marker_split(tuple(h for h in HANDLED if h != "beam_"))
    got["markers_control_drop_beam"] = sum(lost_c.values())
    controls["markers_probe_flips"] = got["markers_control_drop_beam"] > got["markers_lost"]

    # 4. поршни против фактического уровня ног в своей карте
    pist = [(m["file"], world_bottom(o)) for m in maps for o in m["objects"] if o["name"] == "piston"]
    got["pistons_objects"] = len(pist)
    got["pistons_maps"] = len({f for f, _ in pist})
    got["pistons_bottom_hist"] = {str(int(b)): n for b, n in sorted(collections.Counter(b for _, b in pist).items(), reverse=True)}
    feet_by_map = {m["file"]: stable_feet(m) for m in maps}

    def piston_class(delta: float = 0.0):
        lethal = edge = below = 0
        for f, b in pist:
            ft = feet_by_map.get(f) or 0.0
            bottom, top = b + delta, b + delta + PISTON_TRAVEL
            if top > ft and bottom < ft + PLAYER_DAMAGE_H:
                lethal += 1
            elif top == ft:
                edge += 1
            else:
                below += 1
        return lethal, edge, below

    got["pistons_lethal_area"], got["pistons_edge"], got["pistons_below_feet"] = piston_class()
    ctrl_l, ctrl_e, ctrl_b = piston_class(delta=PISTON_TRAVEL)   # контроль: поднять все поршни на полный ход
    controls["pistons_flip_when_raised"] = ctrl_l > got["pistons_lethal_area"]
    controls["pistons_partition"] = (got["pistons_lethal_area"] + got["pistons_edge"] + got["pistons_below_feet"]) == len(pist)

    # 5. спавн: две меры
    legacy_exact = sum(1 for m in maps if m["objects"] and supported(
        m, world_bottom(next((o for o in m["objects"] if o["name"] == "vitorc"), {"PH": 0, "y": 0, "h": 0})),
        0, 0, legacy=True) if any(o["name"] == "vitorc" for o in m["objects"]))
    buckets: collections.Counter[int] = collections.Counter()
    for m in maps:
        v = next((o for o in m["objects"] if o["name"] == "vitorc"), None)
        if v is None or not m["cells"]:
            buckets["нет_vitorc_или_коллизии"] += 1
            continue
        feet = world_bottom(v)
        cx = v["x"] + SPAWN_HALF_W
        L, R = cx - FEET_BOX_INSET, cx + FEET_BOX_INSET
        st = stable_feet(m)
        if st is None:
            continue
        if supported(m, feet, L, R):
            buckets[0] += 1
        else:
            buckets[int(st - feet)] += 1
    got["spawn_legacy_exact"] = legacy_exact
    got["spawn_clean"] = buckets[0]
    got["spawn_lift"] = sum(n for d, n in buckets.items() if isinstance(d, int) and d > 0)
    got["spawn_drop"] = sum(n for d, n in buckets.items() if isinstance(d, int) and d < 0)
    got["spawn_zero_delta_total"] = sum(n for d, n in buckets.items() if isinstance(d, int))
    controls["spawn_partitions_maps"] = got["spawn_zero_delta_total"] == len(maps)
    controls["spawn_lift_and_drop_both_exist"] = got["spawn_lift"] > 0 and got["spawn_drop"] > 0

    # 6. границы пули против клампа игрока
    gc = (root / "Exolon" / "GameCore" / "GameConstants.swift").read_text(encoding="utf-8")
    lw = int(re.search(r"logicalSize = CGSize\(width: (\d+)", gc).group(1))
    pad = int(re.search(r"position\.x > GameConstants\.logicalSize\.width \+ (\d+)",
                        (root / "Exolon" / "GameCore" / "Weapons" / "BlasterBullet.swift").read_text(encoding="utf-8")).group(1))
    clamp = int(re.search(r"GameConstants\.logicalSize\.width \+ (\d+)\)",
                          (root / "Exolon" / "GameCore" / "Player" / "Player.swift").read_text(encoding="utf-8")).group(1))
    got["logical_width"], got["bullet_kill_bound"], got["player_clamp"] = lw, lw + pad, lw + clamp
    got["maps_solid_at_or_beyond_512"] = sum(1 for m in maps if any(sx >= lw for sx, _, _ in m["cells"]))
    controls["bullet_bound_reachable"] = got["player_clamp"] > got["bullet_kill_bound"] and got["maps_solid_at_or_beyond_512"] > 0

    # 7. beam-пары и пусковые
    up = {m["file"] for m in maps if any("blk_beam_up" == source_block(o) for o in m["objects"])}
    dn = {m["file"] for m in maps if any("blk_beam_down" == source_block(o) for o in m["objects"])}
    got["beam_maps_up"], got["beam_maps_down"], got["beam_maps_both"] = len(up), len(dn), len(up & dn)
    lo = (root / "Exolon" / "GameCore" / "Objects" / "LevelObstacles.swift").read_text(encoding="utf-8")
    got["beam_hit_points"] = int(re.search(r"private var hitPoints = (\d+)", lo).group(1))
    got["beam_total_hits"] = got["beam_hit_points"] * 2
    dl_maps = [m for m in maps if any(o["name"] == "double_launcher" for o in m["objects"])]
    got["double_launcher_objects"] = sum(len([o for o in m["objects"] if o["name"] == "double_launcher"]) for m in dl_maps)
    got["double_launcher_maps"] = len(dl_maps)
    controls["beam_pairs_not_nested"] = got["beam_maps_both"] > 0 and up == dn

    # 8. текстуры: вызовы, литералы, вычисляемые имена
    joined = "".join(p.read_text(encoding="utf-8") for p in (root / "Exolon").rglob("*.swift"))
    call_args = re.findall(r"SKTexture\(imageNamed:\s*([^)]*)\)", joined)
    names_at_sites = set(re.findall(r'SKTexture\(imageNamed:\s*"([^"]+)"', joined))
    switch_names = set(re.findall(r'(?:imageName|sheetName|texName)\s*=\s*"([^"]+)"', joined))
    got["texture_sites"] = len(call_args)
    got["texture_literal_names"] = len(names_at_sites)
    got["texture_computed_sites"] = len(call_args) - sum(1 for a in call_args if a.startswith('"'))
    union = names_at_sites | switch_names
    got["texture_union_names"] = len(union)
    got["texture_names_missing_on_disk"] = sum(
        1 for n in union if not ((root / "Exolon" / "Resources" / f"{n}.png").exists() or (root / "Exolon" / "Resources" / n).exists()))
    controls["texture_measures_distinct"] = got["texture_sites"] != got["texture_literal_names"]

    # 9. generated_terrain: объявлен / использован / в бандле
    declared = used = 0
    for m in maps:
        if "generated_terrain" not in m["text"]:
            continue
        declared += 1
        for gt in re.finditer(r'<tileset[^>]*firstgid="(\d+)"[^>]*>(.*?)</tileset>', m["text"], re.S):
            if "generated_terrain" not in gt.group(2):
                continue
            fg = int(gt.group(1))
            tw = re.search(r'width="(\d+)"', gt.group(2))
            ts = re.search(r'tilewidth="(\d+)"', gt.group(2))
            n = (int(tw.group(1)) // int(ts.group(1))) if tw and ts else 16
            if any(v in set(range(fg, fg + max(n, 1))) for _, g in m["tiles_sig"] for v in set(g)):
                used += 1
    got["gen_terrain_declared"], got["gen_terrain_used"] = declared, used
    pbx = (root / "Exolon.xcodeproj" / "project.pbxproj").read_text(encoding="utf-8")
    bid = re.findall(r"(\w{24}) /\* generated_terrain\.png in Resources \*/ = \{isa = PBXBuildFile", pbx)
    got["gen_terrain_in_resources_phase"] = int(bool(bid) and f"{bid[0]} /* generated_terrain.png in Resources */," in pbx)
    l04 = (root / "Exolon" / "Resources" / "L01S04.tmx").read_text(encoding="utf-8")
    got["l01s04_dangling_gif"] = len(re.findall(r'source="\.\./images/[^"]+\.gif"', l04))
    got["images_dir_exists"] = int((root / "Exolon" / "images").is_dir() or (root / "Exolon" / "Resources" / "images").is_dir())

    # 10. наблюдаемость, чекпоинт, релизный слой
    got["product_log_calls"] = len(re.findall(r"\bprint\(|NSLog\(|os_log", joined))
    got["loadcheckpoint_calls"] = len(re.findall(r"(?<!func )(?<!\w)loadCheckpoint\(\s*\)", joined))
    got["clearcheckpoint_calls"] = len(re.findall(r"\.clearCheckpoint\(\)", joined))
    got["shared_xcschemes"] = len(list(root.glob("**/*.xcscheme")))
    got["test_targets"] = len(re.findall(r'isa = PBXNativeTarget;.*?productType = com\.apple\.product-type\.bundle\.unit-test', pbx, re.S))
    got["product_xctest_files"] = len([p for p in (root / "Exolon").rglob("*.swift") if "XCTest" in p.read_text(encoding="utf-8")])
    controls["counters_are_counters_not_names"] = got["loadcheckpoint_calls"] < len(re.findall(r"loadCheckpoint", joined))

    mism = {k: (v, got.get(k)) for k, v in EXPECTED.items() if got.get(k) != v}
    out = {"root": root.name, "measured": got, "controls": controls, "mismatches": mism,
           "ok": not mism and all(controls.values())}
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    else:
        for k in EXPECTED:
            flag = "" if EXPECTED[k] == got.get(k) else f"   ✗ ожидалось {EXPECTED[k]!r}"
            print(f"{k:34} = {got.get(k)!r}{flag}")
        print("controls:")
        for k, v in controls.items():
            print(f"  {'OK ' if v else 'BAD'} {k}")
        if mism:
            print("НЕСОВПАДЕНИЯ:", json.dumps(mism, ensure_ascii=False, default=str))
        print("RESULT:", "ALL_V3_MEASUREMENTS_MATCH_REPORT" if out["ok"] else "MISMATCH")
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
