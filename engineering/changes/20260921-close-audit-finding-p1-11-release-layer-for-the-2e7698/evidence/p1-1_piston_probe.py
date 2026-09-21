#!/usr/bin/env python3
"""P1-1: самопроверяющийся измеритель геометрии поршней (exolon, 2026-09-21).

Что он решает
-------------
Строка P1-1 авторитетного отчёта
`engineering/reports/exolon-full-audit-20260920-v3.md` и закоммиченный измеритель
`engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/v3_measurements.py`
считают основание hazard-бокса поршня как `PH - y - height`, а продуктовый
`TMXMapLoader.worldBottomLeft(for:)` для объектов без `coordinateMode=tiledRect`
возвращает `PH - y`. Разница = ровно `height` = 64 px для 45 из 46 маркеров.
Этот зонд считает обе модели, сверяет продуктовую модель с ИСПОЛНЕННЫМ Swift-кодом
(артефакт `piston-anchor-swift.txt`, см. `piston-anchor-harness/run.sh`) и печатает
распределение летальности по фактическому полу каждой карты.

Разбор TMX — только `xml.etree`; заимствован у закоммиченного измерителя (import),
чтобы не переписывать парсер и не разъезжаться с ним.

Клетки `m["cells"]` имеют вид `(startX, cellBottomY, cellTopY)` — верх клетки это
индекс 2 (`v3_measurements.load_map`). Ошибка на этом индексе сдвигает весь вывод
на 16 px и является отдельным контролем ниже.

Запуск: python3 p1-1_piston_probe.py [--root <путь>] [--json]
rc=0 ⇔ все EXPECTED совпали И все controls перевернулись (иначе rc=1).
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
COMMITTED = HERE.parent.parent / "20260919-exolon-initial-code-audit-7db1f3" / "evidence"
sys.path.insert(0, str(COMMITTED))
try:
    import v3_measurements as v3  # noqa: E402  (закоммиченный парсер и правила опоры)
except Exception as exc:  # fail-closed: без закоммиченного измерителя цифры нечем отличить
    print(f"FATAL: нет доступа к закоммиченному измерителю {COMMITTED}: {exc}")
    sys.exit(2)

ARTIFACT = HERE / "piston-anchor-swift.txt"

TRAVEL = 64                 # LevelObstacles.swift:329-330 hiddenY=groundY-64, exposedY=groundY
BOX_H = 64                  # LevelObstacles.swift:335 нода 48x64; :345 высота = visibleHeight
HIT_X_INSET = 3             # LevelObstacles.swift:345 x = node.position.x + 3
HIT_W = 42                  # LevelObstacles.swift:345 width = 42
PLAYER_DAMAGE_H = 63        # GameConstants.swift:23 playerStandingDamageSize.height
PLAYER_DAMAGE_W = 46        # там же ширина
SOLID_IDX = 2               # cells = (startX, bottom, TOP)

EXPECTED: dict[str, object] = {
    "piston_objects": 46,
    "piston_maps": 27,
    "swift_groundy_agrees_product_rule": 46,
    "swift_groundy_agrees_audit_rule": 1,
    "anchor_models_differ_objects": 45,
    "product_groundy_hist": {"96": 1, "64": 2, "32": 12, "16": 15, "0": 16},
    # аудит v3 (§1 P1-1) под СВОЕЙ моделью якоря и СВОЕЙ базой «ноги спавна»
    "audit_model_spawnfeet": {"lethal_area": 1, "edge_only": 2, "below": 43, "no_support": 0},
    # продуктовая модель (Swift-подтверждённый якорь) против локального пола
    "product_model_localfloor": {"lethal_area": 3, "edge_only": 42, "below": 0, "no_support": 1},
    "lethal_area_objects": 3,
    "edge_only_objects": 42,
    "edge_only_maps": 25,
    "no_support_maps": ["L01S15.tmx"],
    # что стало бы с перекрытием, если поднять ход на одну клетку (data-side фикс)
    "overlap_hist_after_one_tile_lift": {"63": 3, "16": 42},
    "swift_maps_ok": 125,
    # семантика CGRect.intersects исполненным Swift (Linux-указатель, НЕ доказательство
    # для Apple): flush=true ⇒ 42 поршня летальны только по правилу «касание кромкой»
    "swift_semantics_linux": {"flush": True, "one_px": True, "deep": True},
    # сколько поршней имеет хоть какой-то контакт (площадь ИЛИ кромка): 45 из 46
    "contact_if_edge_counts": 45,
    # статическая стража правила якоря (краснеет без пересборки Swift)
    "anchor_default_branch_no_height": True,
    "anchor_height_branch_is_tiledrect_only": True,
    "pistons_with_tiledrect": 0,
    "pistons_case_groundy_source": 1,
}


def find_root(explicit: str | None) -> pathlib.Path:
    if explicit:
        return pathlib.Path(explicit).resolve()
    return v3.find_root(None)


def parse_swift_artifact(path: pathlib.Path):
    """({(map, x, y): groundY}, {(map, x, y): coordinateMode}) из вывода Настоящего TMXMapLoader."""
    gy: dict[tuple[str, float, float], float] = {}
    mode: dict[tuple[str, float, float], str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("PISTON "):
            continue
        parts = line.split()
        kv = dict(tok.split("=", 1) for tok in parts[1:] if "=" in tok)
        key = (parts[1], float(kv["x"]), float(kv["y"]))
        gy[key] = float(kv["groundY"])
        mode[key] = kv.get("mode", "-")
    return gy, mode


def classify(pistons: list[dict], base: str, ref: str) -> collections.Counter:
    """base: 'product' (PH-y) | 'audit' (PH-y-height); ref: 'localfloor' | 'spawnfeet'."""
    cls: collections.Counter = collections.Counter()
    for p in pistons:
        gy = p[base]
        tread = gy + BOX_H
        f = p[ref]
        if f is None:
            cls["no_support"] += 1
            continue
        ov = min(tread, f + PLAYER_DAMAGE_H) - max(gy, f)
        if ov > 0:
            cls["lethal_area"] += 1
        elif ov == 0 and tread == f:
            cls["edge_only"] += 1
        else:
            cls["below"] += 1
    return cls


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = find_root(args.root)
    got: dict[str, object] = {}
    controls: dict[str, bool] = {}
    detail: list[dict] = []

    maps = [v3.load_map(p) for p in sorted((root / "Exolon" / "Resources").glob("*.tmx"))]
    feet_by_map = {m["file"]: v3.stable_feet(m) for m in maps}
    zone_by_file = {name: i for i, name in enumerate(sorted(m["file"] for m in maps))}

    pistons: list[dict] = []
    for m in maps:
        for o in m["objects"]:
            if o["name"] != "piston":
                continue
            product_gy = m["PH"] - o["y"]                    # TMXMapLoader.swift:79
            audit_gy = v3.world_bottom(o)                    # v3_measurements.py:171
            tops = [(sx, tp) for sx, _bt, tp in m["cells"]]
            own = [tp for sx, tp in tops
                   if sx < o["x"] + HIT_X_INSET + HIT_W and sx + m["TW"] > o["x"] + HIT_X_INSET]
            band = [tp for sx, tp in tops                  # полоса достижимости ног игрока
                    if sx < o["x"] + HIT_X_INSET + HIT_W + 40 and sx + m["TW"] > o["x"] + HIT_X_INSET - 40]

            def surface(limit: float, pool: list[float]) -> float | None:
                cands = [tp for tp in pool if tp <= limit]
                return max(cands) if cands else None

            f_own = surface(product_gy + BOX_H, own)
            f_band = surface(product_gy + BOX_H, band)
            f_local = f_own if f_own is not None else f_band
            detail.append({
                "map": m["file"], "zone": zone_by_file[m["file"]], "x": o["x"], "y": o["y"],
                "height": o["h"], "product_gy": product_gy, "audit_gy": audit_gy,
                "tread": product_gy + BOX_H, "floor_own": f_own, "floor_band": f_band,
                "floor_used": f_local, "spawn_feet": feet_by_map[m["file"]],
                "headroom": sum(1 for sx, tp in tops
                                if sx < o["x"] + HIT_X_INSET + HIT_W and sx + m["TW"] > o["x"] + HIT_X_INSET
                                and f_local is not None and f_local < tp <= f_local + PLAYER_DAMAGE_H),
            })

    got["piston_objects"] = len(pistons) or len(detail)
    got["piston_maps"] = len({d["map"] for d in detail})
    got["product_groundy_hist"] = {str(int(v)): n for v, n in
                                   sorted(collections.Counter(d["product_gy"] for d in detail).items(), reverse=True)}

    # 1. сверяюсь с ИСПОЛНЕННЫМ продуктовым кодом, а не со своей моделью
    if ARTIFACT.exists():
        text = ARTIFACT.read_text(encoding="utf-8")
        swift, swift_mode = parse_swift_artifact(ARTIFACT)
        summary = dict(tok.split("=", 1) for tok in
                       next((ln for ln in text.splitlines() if ln.startswith("SUMMARY ")), "")
                            .split()[1:] if "=" in tok)
        got["swift_rows"] = len(swift)
        got["swift_maps_ok"] = int(summary.get("maps_ok", -1))
        got["swift_groundy_agrees_product_rule"] = sum(
            1 for d in detail if swift.get((d["map"], d["x"], d["y"])) == d["product_gy"])
        got["swift_groundy_agrees_audit_rule"] = sum(
            1 for d in detail if swift.get((d["map"], d["x"], d["y"])) == d["audit_gy"])
        got["anchor_models_differ_objects"] = sum(1 for d in detail if d["product_gy"] != d["audit_gy"])
        controls["swift_artifact_covers_every_object"] = len(swift) == len(detail)
        # контроль: модели обязаны расходяться, иначе зонд не отличает одну от другой
        controls["anchor_models_distinguishable"] = got["anchor_models_differ_objects"] > 0
        # контроль: расхождение обязано быть ровно на height, и только там, где height>0
        controls["anchor_delta_is_exactly_height"] = all(
            d["product_gy"] - d["audit_gy"] == d["height"] for d in detail)
        # семантика CGRect.intersects, измеренная исполнением (Linux-указатель):
        # flush=true означает «касание кромками = пересечение», т.е. 42 впритык-поршня
        # летальны ТОЛЬКО по этому правилу, без положительной площади.
        sem = dict(tok.split("=", 1) for tok in
                   next((ln for ln in text.splitlines() if ln.startswith("SEMANTICS ")), "")
                        .split()[1:] if "=" in tok)
        got["swift_semantics_linux"] = {"flush": sem.get("flush") == "true",
                                        "one_px": sem.get("onePx") == "true",
                                        "deep": sem.get("deep") == "true"}
        # контроль обязан перевернуться: 32 px наложения не могут НЕ считаться
        # пересечением, иначе весь примитив и все классы выше бессмысленны
        controls["semantics_deep_overlap_counts"] = got["swift_semantics_linux"]["deep"] is True
        controls["semantics_one_pixel_overlap_counts"] = got["swift_semantics_linux"]["one_px"] is True
    else:
        swift_mode = {}
        got["swift_rows"] = 0
        got["swift_maps_ok"] = -1
        got["swift_semantics_linux"] = {}
        controls["swift_artifact_covers_every_object"] = False
        controls["anchor_models_distinguishable"] = False
        controls["anchor_delta_is_exactly_height"] = False
        controls["semantics_deep_overlap_counts"] = False
        controls["semantics_one_pixel_overlap_counts"] = False

    # 2. статическая стража якоря: за числом не только в артефакт, но и в исходник —
    #    если правка вернёт `- object.height` в default-ветке, тест обязан
    #    покраснеть даже без пересборки Swift.
    loader_src = (root / "Exolon" / "GameCore" / "Levels" / "TMXMapLoader.swift").read_text(encoding="utf-8")
    runtime_src = (root / "Exolon" / "GameCore" / "Levels" / "TMXLevelRuntime.swift").read_text(encoding="utf-8")
    default_line = next((ln for ln in loader_src.splitlines()
                         if "return CGPoint(x: object.x, y: pixelHeight - object.y" in ln
                         and "- object.height" not in ln), "")
    height_line = next((ln for ln in loader_src.splitlines()
                        if "pixelHeight - object.y - object.height" in ln), "")
    got["anchor_default_branch_no_height"] = bool(default_line)
    got["anchor_height_branch_is_tiledrect_only"] = ("tiledRect" in loader_src
                                                    and height_line.count("return CGPoint") == 1)
    got["pistons_with_tiledrect"] = sum(1 for d in detail if swift_mode.get((d["map"], d["x"], d["y"])) == "tiledRect")
    got["pistons_case_groundy_source"] = 1 if re.search(
        r'case "piston":\s*\n\s*let piston = PistonHazard\(leftX: bottom\.x, groundY: bottom\.y\)',
        runtime_src) else 0
    controls["anchor_source_guard_binds"] = bool(default_line) and bool(height_line)
    controls["pistons_not_tiledrect"] = got["pistons_with_tiledrect"] == 0

    # 3. воспроизвожу опубликованные числа аудита ЕГО моделью (иначе я меряю не то же)
    audit_cls = classify(detail, "audit_gy", "spawn_feet")
    got["audit_model_spawnfeet"] = {k: audit_cls.get(k, 0) for k in
                                    ("lethal_area", "edge_only", "below", "no_support")}
    prod_cls = classify(detail, "product_gy", "floor_used")
    got["product_model_localfloor"] = {k: prod_cls.get(k, 0) for k in
                                       ("lethal_area", "edge_only", "below", "no_support")}
    got["lethal_area_objects"] = prod_cls.get("lethal_area", 0)
    got["edge_only_objects"] = prod_cls.get("edge_only", 0)
    got["contact_if_edge_counts"] = prod_cls.get("lethal_area", 0) + prod_cls.get("edge_only", 0)
    got["edge_only_maps"] = len({d["map"] for d in detail
                                 if d["floor_used"] is not None and d["tread"] == d["floor_used"]})
    got["no_support_maps"] = sorted({d["map"] for d in detail if d["floor_used"] is None})

    # 3. что меняет фикс «касание кромки = поражение» (или +16 px хода)
    fixed_hist = collections.Counter()
    for d in detail:
        if d["floor_used"] is None:
            continue
        # edge-inclusive: касание верха блока с уровнем ног тоже летально ⇒ площадь = 16? нет:
        # считаем фикс «поднять ход на одну клетку» (data-side), tread += 16
        fixed_hist[int(min(d["tread"] + 16, d["floor_used"] + PLAYER_DAMAGE_H) - d["floor_used"])] += 1
    got["overlap_hist_after_one_tile_lift"] = {str(k): v for k, v in sorted(fixed_hist.items(), reverse=True)}

    # 4. controls: чувствительность зонда
    def with_tread(delta: float) -> collections.Counter:
        c: collections.Counter = collections.Counter()
        for d in detail:
            f = d["floor_used"]
            if f is None:
                c["no_support"] += 1
                continue
            top = d["tread"] + delta
            ov = min(top, f + PLAYER_DAMAGE_H) - max(d["product_gy"], f)
            c["lethal_area" if ov > 0 else ("edge_only" if ov == 0 and top == f else "below")] += 1
        return c

    up, down = with_tread(16), with_tread(-BOX_H)
    controls["raising_tread_increases_lethal"] = up["lethal_area"] > prod_cls["lethal_area"]
    controls["lowering_tread_decreases_lethal"] = down["lethal_area"] < prod_cls["lethal_area"]
    controls["edge_only_is_the_whole_gap"] = (prod_cls["lethal_area"] + prod_cls["edge_only"]
                                             + prod_cls["below"] + prod_cls["no_support"]) == len(detail)
    controls["edge_only_class_not_empty"] = prod_cls["edge_only"] > 0
    controls["audit_and_product_models_disagree"] = got["audit_model_spawnfeet"] != got["product_model_localfloor"]
    # контроль на сам парсер: если взять нижний край клетки вместо верхнего, пол уедет на 16 px
    shifted = 0
    for d in detail:
        m = next(x for x in maps if x["file"] == d["map"])
        pool = [bt for sx, bt, tp in m["cells"]
                if sx < d["x"] + HIT_X_INSET + HIT_W and sx + m["TW"] > d["x"] + HIT_X_INSET
                and bt <= d["tread"]]
        if pool and max(pool) != d["floor_own"]:
            shifted += 1
    controls["cell_index_is_load_bearing"] = shifted > 0
    # контроль: пустой слой Collision обязан убить все поверхности
    noboost = classify([{**d, "floor_used": None} for d in detail], "product_gy", "floor_used")
    controls["no_cells_means_no_verdict"] = noboost["no_support"] == len(detail)

    mism = {k: (v, got.get(k)) for k, v in EXPECTED.items() if got.get(k) != v}
    out = {"root": root.name, "artifact": str(ARTIFACT), "measured": got,
           "controls": controls, "mismatches": mism, "ok": not mism and all(controls.values())}
    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False, default=str))
    else:
        for k in EXPECTED:
            flag = "" if EXPECTED[k] == got.get(k) else f"   ✗ ожидалось {EXPECTED[k]!r}"
            print(f"{k:38} = {got.get(k)!r}{flag}")
        print("controls:")
        for k, v in controls.items():
            print(f"  {'OK ' if v else 'BAD'} {k}")
        print(f"detail rows = {len(detail)}")
        print("RESULT:", "ALL_P1_1_MEASUREMENTS_MATCH_REPORT" if out["ok"] else "MISMATCH")
    if not args.json:
        return 0 if out["ok"] else 1
    print(json.dumps({"detail": detail}, ensure_ascii=False, default=str), file=sys.stderr)
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
