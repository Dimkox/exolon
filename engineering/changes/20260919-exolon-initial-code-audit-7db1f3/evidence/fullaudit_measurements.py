#!/usr/bin/env python3
r"""Full-audit product measurements (route 7db1f3f0b126, 2026-09-20).

Reproduces three load-bearing measurements of engineering/reports/
exolon-full-audit-20260920.md with built-in must-fail controls:

  1. L01S10 cabin geometry vs collision-exclusion formula (C1 retraction)
  2. beam_up + beam_down map matrix (O7)
  3. vitorc spawn feet vs local collision floor, all 125 maps (B-01)
     -> writes fullaudit-b01-spawn.json next to this script

Read-only against the repository; the only file written is the B-01 JSON.
CSV tokenization uses the same [,\s]+ split as TMXMapLoader.swift (L01S10
has no trailing commas and must be tokenized accordingly).
"""
import json
import re
import sys
from pathlib import Path

import xml.etree.ElementTree as ET

REPO = Path(__file__).resolve().parents[4]
RES = REPO / "Exolon" / "Resources"
TILE = 16


def world_root(fname):
    return ET.parse(RES / fname).getroot()


def collision_gids(root):
    """Return (W, Hpx, gids) for the first layer named 'collision' or None."""
    W, H = int(root.get("width")), int(root.get("height"))
    for lay in root.iter("layer"):
        if (lay.get("name") or "").lower() != "collision":
            continue
        d = lay.find("data")
        if d.get("encoding") == "base64":
            import base64
            import zlib
            raw = base64.b64decode(d.text)
            if d.get("compression"):
                raw = zlib.decompress(raw)
            n = W * H
            if len(raw) == n:
                gids = list(raw)
            else:  # 32-bit little-endian GIDs, no compression
                gids = [int.from_bytes(raw[i * 4:i * 4 + 4], "little") for i in range(n)]
        else:
            gids = [int(t) for t in re.split(r"[,\s]+", d.text.strip()) if t]
        assert len(gids) == W * H, (lay.get("name"), len(gids))
        return W, H * TILE, gids
    return None


def solid_rects(fname):
    """Merged horizontal runs exactly like TMXTileMapRenderer.buildCollisionRects."""
    data = collision_gids(world_root(fname))
    if data is None:
        return []
    W, PH, gids = data
    H = PH // TILE
    rects = []
    for row in range(H):
        col = 0
        while col < W:
            if gids[row * W + col] & 0x1FFF_FFFF == 0:
                col += 1
                continue
            start = col
            while col < W and gids[row * W + col] & 0x1FFF_FFFF != 0:
                col += 1
            y = PH - (row + 1) * TILE
            rects.append((start * TILE, y, (col - start) * TILE, TILE))
    return rects


def subtract(rects, ex):
    ex_x, ex_y, ex_w, ex_h = ex
    out = []
    for (x, y, w, h) in rects:
        ix = max(0, min(x + w, ex_x + ex_w) - max(x, ex_x))
        iy = max(0, min(y + h, ex_y + ex_h) - max(y, ex_y))
        if ix == 0 or iy == 0:
            out.append((x, y, w, h))
            continue
        if x < ex_x:
            out.append((x, y, ex_x - x, h))
        if x + w > ex_x + ex_w:
            out.append((ex_x + ex_w, y, x + w - ex_x - ex_w, h))
        if y < ex_y:
            out.append((max(x, ex_x), y, min(x + w, ex_x + ex_w) - max(x, ex_x), ex_y - y))
        if y + h > ex_y + ex_h:
            out.append((max(x, ex_x), ex_y + ex_h,
                        min(x + w, ex_x + ex_w) - max(x, ex_x), y + h - ex_y - ex_h))
    return [r for r in out if r[2] > 0 and r[3] > 0]


def measure_cabin():
    """C1: capsule (368,176,32,80) tiled in 35x24 map -> trigger world y=128..208."""
    rects = solid_rects("L01S10.tmx")
    booth = [r for r in rects if 128 <= r[1] and r[1] + r[3] <= 208 and r[0] >= 352 and r[0] + r[2] <= 448]
    def floor_whole(rl):  # intact single platform rect y=80..96 spanning the cabin width
        return [r for r in rl if abs(r[1] - 80) < 1e-6 and r[3] == 16
                and r[0] <= 352 and r[0] + r[2] >= 448]
    shipped = (352, 112, 96, 112)   # x=minX-16, y=minY-16, w=max(96,w+64), h=height+32
    after = subtract(rects, shipped)
    booth_after = [r for r in after if 128 <= r[1] and r[1] + r[3] <= 208
                   and r[0] >= 352 and r[0] <= 448 and r[3] > 4]
    # must-fail control: push the exclusion bottom down through the floor top (96)
    control = floor_whole(subtract(rects, (352, 95, 96, 129)))
    ok = (len(booth) == 5 and len(floor_whole(rects)) == 1
          and len(booth_after) == 0 and len(floor_whole(after)) == 1
          and len(control) == 0)
    return {
        "booth_cells_before": len(booth), "floor_rects_before": len(floor_whole(rects)),
        "booth_cells_after_shipped_exclusion": len(booth_after),
        "floor_rects_after_shipped_exclusion": len(floor_whole(after)),
        "control_mutated_exclusion_floor_rects_whole": len(control),
        "verdict": "C1 retracted" if ok else "UNEXPECTED - re-check",
        "ok": ok,
    }


def measure_beams():
    maps, both = set(), []
    for f in sorted(RES.glob("*.tmx")):
        ups = downs = 0
        for o in world_root(f.name).iter("object"):
            for p in o.iter("property"):
                if p.get("name") == "sourceBlock":
                    v = p.get("value") or ""
                    if v == "blk_beam_up":
                        ups += 1
                    elif v == "blk_beam_down":
                        downs += 1
        if ups or downs:
            maps.add(f.name)
            if ups and downs:
                both.append(f.name)
    return {"maps_with_any_beam_marker": len(maps), "maps_with_both_up_and_down": len(both),
            "list": both,
            "ok": len(maps) == 10 and len(both) == 10}


def measure_b01():
    cats = {}
    for f in sorted(RES.glob("*.tmx")):
        root = world_root(f.name)
        W, PH, gids = collision_gids(root)
        H = PH // TILE
        v = next((o for o in root.iter("object") if (o.get("name") or "") == "vitorc"), None)
        if v is None:
            cats[f.name] = "NO_VITORC"
            continue
        fx, fy = float(v.get("x")), float(v.get("y"))
        fw, fh = float(v.get("width") or 0), float(v.get("height") or 0)
        feet = PH - (fy + fh)
        col = int((fx + fw / 2) // TILE)
        # same rule as the interactive measurement: nearest solid cell top at or below feet
        tops = [PH - row * TILE for row in range(H)
                if gids[row * W + col] != 0 and (PH - row * TILE) <= feet + 0.5]
        floor = max(tops) if tops else None
        if floor is None:
            cats[f.name] = "void"
        else:
            d = int(feet - floor)
            cats[f.name] = {0: "exact", -16: "16_below", 16: "16_above"}.get(d, f"other:{d}")
    out = Path(__file__).resolve().parent / "fullaudit-b01-spawn.json"
    out.write_text(json.dumps(cats, indent=1, sort_keys=True))
    import collections
    tally = collections.Counter(cats.values())
    # control: totals must partition 125 and exact-group must match 35 (docs join)
    return {"tally": dict(tally), "total": sum(tally.values()),
            "ok": sum(tally.values()) == 125 and tally["exact"] == 35,
            "json_written": out.name}


def main():
    results = {"cabin_L01S10": measure_cabin(), "beam_matrix": measure_beams(),
               "b01_spawn": measure_b01()}
    print(json.dumps(results, ensure_ascii=False, indent=2))
    failed = [k for k, v in results.items() if not v.get("ok")]
    print("ALL_MEASUREMENTS_MATCH_REPORT" if not failed else f"MISMATCH: {failed}", file=sys.stderr)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
