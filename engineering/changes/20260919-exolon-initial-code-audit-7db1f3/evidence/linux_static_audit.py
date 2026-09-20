#!/usr/bin/env python3
"""Linux-only static audit of Exolon TMX zones, pbxproj membership and resources.

Does not compile Swift or simulate gameplay. Writes JSON + Markdown evidence.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
EXOLON = ROOT / "Exolon"
RES = EXOLON / "Resources"
PBX = ROOT / "Exolon.xcodeproj" / "project.pbxproj"
COMPILER = ROOT / "LEVEL_COMPILER_AUDIT.md"
OUT_DIR = Path(__file__).resolve().parent

HANDLED_OBJECT_NAMES = {
    "vitorc",
    "turret",
    "cocoon",
    "radar",
    "rocket",
    "grenade_pack",
    "ammo_pack",
    "teleport",
    "piston",
    "capsule",
    "bubble_creator",
    "incubator",
    "double_launcher",
    "mine",
    "ship",
    "gate",
    "ship_fire",
    "light_floor",
    "light_ceiling",
    "source_marker",
}

# TMXLevelRuntime.buildObjectsFromTMX source_marker branches.
HANDLED_SOURCE_SUBSTRINGS = (
    "beam_",
    "topdown_electro",
    "blinker",
    "stage_end",
    "changing_room",
    "beacon_base",
    "control_beacon",
)

# Runtime actually constructs a live gameplay entity (not scenery/no-op).
LIVE_OBJECT_NAMES = {
    "turret",
    "cocoon",
    "radar",
    "rocket",
    "grenade_pack",
    "ammo_pack",
    "teleport",
    "piston",
    "capsule",
    "bubble_creator",
    "incubator",
    "double_launcher",
    "mine",
    "gate",
}

LIVE_SOURCE_SUBSTRINGS = (
    "beam_",
    "stage_end",
    "changing_room",
    "beacon_base",
    "control_beacon",
)

SCENERY_OBJECT_NAMES = {
    "vitorc",
    "ship",
    "ship_fire",
    "light_floor",
    "light_ceiling",
}

NOOP_SOURCE_SUBSTRINGS = (
    "topdown_electro",
    "blinker",
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_compiler_audit(text: str) -> dict[int, dict]:
    zones: dict[int, dict] = {}
    for line in text.splitlines():
        m = re.match(
            r"^(\d{3})\s+(L\d{2}S\d{2})\s+solid=(\d+)\s+actions=(.*)$",
            line.strip(),
        )
        if not m:
            continue
        zone = int(m.group(1))
        actions_raw = m.group(4).strip()
        actions = []
        type_counts: Counter[int] = Counter()
        if actions_raw:
            for token in actions_raw.split(","):
                parts = token.split(":")
                if len(parts) != 3:
                    continue
                x, y, t = (int(parts[0]), int(parts[1]), int(parts[2]))
                actions.append({"x": x, "y": y, "type": t})
                type_counts[t] += 1
        zones[zone] = {
            "level": m.group(2),
            "solid": int(m.group(3)),
            "actions": actions,
            "action_count": len(actions),
            "type_counts": dict(type_counts),
        }
    return zones


def collision_solid_count(map_el: ET.Element) -> int | None:
    for layer in map_el.findall("layer"):
        if (layer.get("name") or "").lower() != "collision":
            continue
        data = layer.find("data")
        if data is None or not (data.text or "").strip():
            return 0
        encoding = (data.get("encoding") or "").lower()
        text = data.text.strip()
        if encoding == "csv":
            nums = [int(x) for x in re.split(r"[,\s]+", text) if x]
            return sum(1 for n in nums if n != 0)
        if encoding == "base64":
            return None  # binary; counted separately if needed
        return None
    return 0


def iter_objects(map_el: ET.Element):
    for group in map_el.findall("objectgroup"):
        for obj in group.findall("object"):
            props = {}
            prop_el = obj.find("properties")
            if prop_el is not None:
                for p in prop_el.findall("property"):
                    props[p.get("name") or ""] = p.get("value") or (p.text or "")
            yield {
                "name": obj.get("name") or "",
                "id": obj.get("id"),
                "x": obj.get("x"),
                "y": obj.get("y"),
                "width": obj.get("width"),
                "height": obj.get("height"),
                "properties": props,
                "sourceBlock": props.get("sourceBlock", ""),
            }


def source_marker_runtime(source: str) -> str:
    if not source:
        return "source_marker_empty"
    for needle in LIVE_SOURCE_SUBSTRINGS:
        if needle in source:
            return f"live:{needle}"
    for needle in NOOP_SOURCE_SUBSTRINGS:
        if needle in source:
            return f"noop:{needle}"
    return "unhandled"


def object_runtime(obj: dict) -> str:
    name = obj["name"]
    if name == "source_marker":
        return source_marker_runtime(obj["sourceBlock"])
    if name in LIVE_OBJECT_NAMES:
        return f"live:{name}"
    if name in SCENERY_OBJECT_NAMES:
        return f"scenery:{name}"
    if name in HANDLED_OBJECT_NAMES:
        return f"handled:{name}"
    if not name:
        return "unnamed"
    return "unknown"


def map_properties(map_el: ET.Element) -> dict[str, str]:
    props = {}
    el = map_el.find("properties")
    if el is None:
        return props
    for p in el.findall("property"):
        props[p.get("name") or ""] = p.get("value") or (p.text or "")
    return props


def image_sources(map_el: ET.Element) -> list[str]:
    sources = []
    for image in map_el.findall(".//image"):
        src = image.get("source")
        if src:
            sources.append(src)
    return sources


def expected_levels() -> list[str]:
    names = []
    for stage in range(1, 6):
        for screen in range(1, 26):
            names.append(f"L{stage:02d}S{screen:02d}")
    return names


def pbx_paths(text: str) -> set[str]:
    refs = set(re.findall(r"path = ([^;]+);", text))
    return {p.strip().strip('"') for p in refs}


def main() -> int:
    levels = expected_levels()
    tmx_files = sorted(RES.glob("L??S??.tmx"))
    tmx_names = {p.stem for p in tmx_files}

    compiler = parse_compiler_audit(COMPILER.read_text(encoding="utf-8"))
    pbx_text = PBX.read_text(encoding="utf-8", errors="replace")
    pbx = pbx_paths(pbx_text)

    resource_files = [p for p in RES.iterdir() if p.is_file()]
    resource_names = {p.name for p in resource_files}

    swift_files = sorted(EXOLON.rglob("*.swift"))
    swift_in_pbx = []
    swift_missing_pbx = []
    for path in swift_files:
        if path.name in pbx:
            swift_in_pbx.append(str(path.relative_to(ROOT)))
        else:
            swift_missing_pbx.append(str(path.relative_to(ROOT)))

    object_name_counts: Counter[str] = Counter()
    source_block_counts: Counter[str] = Counter()
    runtime_counts: Counter[str] = Counter()
    unhandled: list[dict] = []
    missing_vitorc: list[str] = []
    next_chain: dict[str, str] = {}
    zone_numbers: dict[str, str] = {}
    missing_images: list[dict] = []
    odd_dimensions: list[dict] = []
    teleport_counts: dict[str, int] = {}
    capsule_maps: list[str] = []
    no_collision_layer: list[str] = []
    base64_collision: list[str] = []
    action_vs_object: list[dict] = []
    zone_rows: list[dict] = []

    for name in levels:
        path = RES / f"{name}.tmx"
        row: dict = {
            "level": name,
            "exists": path.exists(),
            "in_pbx": f"{name}.tmx" in pbx,
        }
        if not path.exists():
            zone_rows.append(row)
            continue
        row["sha256"] = sha256_file(path)
        row["bytes"] = path.stat().st_size
        try:
            tree = ET.parse(path)
            root = tree.getroot()
        except ET.ParseError as exc:
            row["xml_error"] = str(exc)
            zone_rows.append(row)
            continue

        width = int(root.get("width") or 0)
        height = int(root.get("height") or 0)
        tw = int(root.get("tilewidth") or 0)
        th = int(root.get("tileheight") or 0)
        row["width"] = width
        row["height"] = height
        row["tilewidth"] = tw
        row["tileheight"] = th
        if (width, height, tw, th) != (35, 24, 16, 16):
            odd_dimensions.append(
                {"level": name, "width": width, "height": height, "tilewidth": tw, "tileheight": th}
            )

        props = map_properties(root)
        row["nextLevel"] = props.get("nextLevel", "")
        row["zoneNumber"] = props.get("zoneNumber", "")
        next_chain[name] = props.get("nextLevel", "")
        zone_numbers[name] = props.get("zoneNumber", "")

        imgs = image_sources(root)
        row["images"] = imgs
        for src in imgs:
            base = Path(src).name
            if base not in resource_names:
                missing_images.append({"level": name, "source": src})

        objects = list(iter_objects(root))
        row["object_count"] = len(objects)
        names = [o["name"] for o in objects]
        row["object_names"] = dict(Counter(names))
        if "vitorc" not in names:
            missing_vitorc.append(name)
        teleport_counts[name] = names.count("teleport")
        if "capsule" in names:
            capsule_maps.append(name)

        runtime_here: Counter[str] = Counter()
        for obj in objects:
            object_name_counts[obj["name"] or "(empty)"] += 1
            if obj["sourceBlock"]:
                source_block_counts[obj["sourceBlock"]] += 1
            kind = object_runtime(obj)
            runtime_counts[kind] += 1
            runtime_here[kind] += 1
            if kind.startswith("unhandled") or kind == "unknown" or kind == "unnamed" or kind == "source_marker_empty":
                unhandled.append(
                    {
                        "level": name,
                        "name": obj["name"],
                        "sourceBlock": obj["sourceBlock"],
                        "x": obj["x"],
                        "y": obj["y"],
                        "runtime": kind,
                    }
                )
        row["runtime"] = dict(runtime_here)

        solid = collision_solid_count(root)
        row["collision_solid"] = solid
        if solid is None:
            data_enc = None
            for layer in root.findall("layer"):
                if (layer.get("name") or "").lower() == "collision":
                    data = layer.find("data")
                    data_enc = data.get("encoding") if data is not None else None
            if data_enc == "base64":
                base64_collision.append(name)
            else:
                no_collision_layer.append(name)
        else:
            # Compiler audit uses original 32-wide character grid; TMX is 35x24.
            # Compare only when we can map zone number.
            zn = props.get("zoneNumber")
            if zn and zn.isdigit():
                z = int(zn)
                if z in compiler:
                    expected = compiler[z]["solid"]
                    # Not a 1:1 cell mapping; record both for later judgement.
                    row["compiler_solid"] = expected
                    row["compiler_actions"] = compiler[z]["action_count"]

        live_gameplay = sum(v for k, v in runtime_here.items() if k.startswith("live:"))
        row["live_gameplay_objects"] = live_gameplay
        zn = props.get("zoneNumber")
        if zn and zn.isdigit() and int(zn) in compiler:
            expected_actions = compiler[int(zn)]["action_count"]
            row["compiler_action_count"] = expected_actions
            # Heuristic: TMX live objects vs original action markers (exclude type 4 flash cells).
            type_counts = compiler[int(zn)]["type_counts"]
            non_flash = expected_actions - type_counts.get(4, 0)
            row["compiler_non_flash_actions"] = non_flash
            if abs(live_gameplay - non_flash) >= 3:
                action_vs_object.append(
                    {
                        "level": name,
                        "zone": int(zn),
                        "live_tmx": live_gameplay,
                        "compiler_actions": expected_actions,
                        "compiler_non_flash": non_flash,
                        "object_names": row["object_names"],
                    }
                )

        zone_rows.append(row)

    # nextLevel chain
    chain_breaks = []
    for i, name in enumerate(levels):
        nxt = next_chain.get(name, "")
        if i == len(levels) - 1:
            if nxt not in ("", "L01S01"):
                chain_breaks.append({"level": name, "nextLevel": nxt, "expected": "(empty or L01S01)"})
        else:
            expected = levels[i + 1]
            if nxt != expected:
                chain_breaks.append({"level": name, "nextLevel": nxt, "expected": expected})

    # zoneNumber property vs filename
    zone_number_mismatches = []
    for i, name in enumerate(levels):
        zn = zone_numbers.get(name, "")
        expected = f"{i:03d}"
        if zn and zn != expected:
            zone_number_mismatches.append({"level": name, "zoneNumber": zn, "expected": expected})
        if not zn and i >= 8:
            # Early hand-authored maps (L01S01..) may omit zoneNumber.
            zone_number_mismatches.append({"level": name, "zoneNumber": zn, "expected": expected})

    odd_teleports = [
        {"level": k, "teleports": v}
        for k, v in teleport_counts.items()
        if v not in (0, 2) and k in tmx_names
    ]

    png_zone = sorted(p.name for p in RES.glob("zone_*_original.png"))
    expected_zone_png = [f"zone_{i:03d}_original.png" for i in range(7, 125)]
    missing_zone_png = [n for n in expected_zone_png if n not in resource_names]
    extra_zone_png = [n for n in png_zone if n not in expected_zone_png]

    tmx_missing_disk = [n for n in levels if n not in tmx_names]
    tmx_missing_pbx = [f"{n}.tmx" for n in levels if f"{n}.tmx" not in pbx]
    pbx_tmx_extra = sorted(
        p for p in pbx if re.fullmatch(r"L\d{2}S\d{2}\.tmx", p) and p[:-4] not in set(levels)
    )

    info_plist = (RES / "Info.plist").read_text(encoding="utf-8")
    m_info = re.search(r"<key>CFBundleShortVersionString</key>\s*<string>([^<]+)</string>", info_plist)
    info_version = m_info.group(1) if m_info else None
    marketing = sorted(set(re.findall(r"MARKETING_VERSION = ([^;]+);", pbx_text)))

    # Gameplay source files
    gameplay_swift = [str(p.relative_to(ROOT)) for p in swift_files]

    summary = {
        "host_limitation": "Linux x86_64 static/data checks only; no xcodebuild/Swift/gameplay.",
        "tmx_expected": 125,
        "tmx_on_disk": len(tmx_files),
        "tmx_missing_disk": tmx_missing_disk,
        "tmx_missing_pbx": tmx_missing_pbx,
        "pbx_tmx_extra": pbx_tmx_extra,
        "odd_dimensions": odd_dimensions,
        "missing_vitorc": missing_vitorc,
        "chain_breaks": chain_breaks,
        "zone_number_mismatches_count": len(zone_number_mismatches),
        "zone_number_mismatches_sample": zone_number_mismatches[:20],
        "odd_teleports": odd_teleports,
        "capsule_maps": capsule_maps,
        "base64_collision": base64_collision,
        "no_collision_layer": no_collision_layer,
        "missing_images": missing_images,
        "missing_zone_png": missing_zone_png,
        "extra_zone_png": extra_zone_png,
        "unhandled_count": len(unhandled),
        "unhandled_sample": unhandled[:40],
        "unhandled_by_sourceBlock": dict(Counter(u["sourceBlock"] or u["name"] for u in unhandled)),
        "object_name_counts": dict(object_name_counts),
        "source_block_counts": dict(source_block_counts),
        "runtime_counts": dict(runtime_counts),
        "action_vs_object_count": len(action_vs_object),
        "action_vs_object_sample": action_vs_object[:25],
        "info_plist_version": info_version,
        "marketing_version": marketing,
        "swift_files": gameplay_swift,
        "swift_missing_pbx": swift_missing_pbx,
        "resource_file_count": len(resource_files),
        "compiler_zones": len(compiler),
    }

    (OUT_DIR / "linux-static-audit.json").write_text(
        json.dumps({"summary": summary, "zones": zone_rows}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    md = []
    md.append("# Linux static audit evidence")
    md.append("")
    md.append("Host: Linux x86_64. This is **not** an `xcodebuild` or gameplay result.")
    md.append("")
    md.append("## Integrity")
    md.append("")
    md.append(f"- TMX on disk: {len(tmx_files)} / 125")
    md.append(f"- TMX missing on disk: {tmx_missing_disk or 'none'}")
    md.append(f"- TMX missing from pbxproj: {tmx_missing_pbx or 'none'}")
    md.append(f"- Extra TMX in pbxproj: {pbx_tmx_extra or 'none'}")
    md.append(f"- Swift sources: {len(gameplay_swift)}; missing from pbxproj: {swift_missing_pbx or 'none'}")
    md.append(f"- Info.plist CFBundleShortVersionString: {info_version}")
    md.append(f"- pbxproj MARKETING_VERSION: {marketing}")
    md.append(f"- Resource files under Exolon/Resources: {len(resource_files)}")
    md.append(f"- Missing zone original PNGs (007-124 expected): {missing_zone_png or 'none'}")
    md.append(f"- Extra zone original PNGs: {extra_zone_png or 'none'}")
    md.append(f"- Missing image references from TMX: {missing_images or 'none'}")
    md.append(f"- Non-35x24@16 maps: {odd_dimensions or 'none'}")
    md.append(f"- Maps without vitorc spawn: {missing_vitorc or 'none'}")
    md.append(f"- nextLevel chain breaks: {chain_breaks or 'none'}")
    md.append(f"- Odd teleport counts (not 0 or 2): {odd_teleports or 'none'}")
    md.append(f"- Capsule/changing-room maps: {capsule_maps}")
    md.append(f"- Base64 collision layers (solid count not decoded here): {base64_collision}")
    md.append("")
    md.append("## Object names")
    md.append("")
    for k, v in sorted(object_name_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        md.append(f"- `{k}`: {v}")
    md.append("")
    md.append("## sourceBlock values")
    md.append("")
    for k, v in sorted(source_block_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        md.append(f"- `{k}`: {v}")
    md.append("")
    md.append("## Runtime classification (from TMXLevelRuntime.swift switch)")
    md.append("")
    for k, v in sorted(runtime_counts.items(), key=lambda kv: (-kv[1], kv[0])):
        md.append(f"- `{k}`: {v}")
    md.append("")
    md.append(f"Unhandled/unknown objects: {len(unhandled)}")
    md.append("")
    if unhandled:
        md.append("| level | name | sourceBlock | x | y | runtime |")
        md.append("| --- | --- | --- | --- | --- | --- |")
        for u in unhandled[:80]:
            md.append(
                f"| {u['level']} | {u['name']} | {u['sourceBlock']} | {u['x']} | {u['y']} | {u['runtime']} |"
            )
    md.append("")
    md.append("## Compiler action count vs live TMX objects (heuristic)")
    md.append("")
    md.append(
        "Original type 4 flashing cells are excluded from the expected live count. "
        "A large gap is a candidate missing runtime mapping, not proof of a crash."
    )
    md.append("")
    if action_vs_object:
        md.append("| level | zone | live TMX | compiler actions | non-flash | objects |")
        md.append("| --- | --- | --- | --- | --- | --- |")
        for row in action_vs_object[:40]:
            md.append(
                f"| {row['level']} | {row['zone']} | {row['live_tmx']} | {row['compiler_actions']} | {row['compiler_non_flash']} | {row['object_names']} |"
            )
    else:
        md.append("No zones with |live - non-flash| >= 3.")
    md.append("")
    (OUT_DIR / "linux-static-audit.md").write_text("\n".join(md) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
