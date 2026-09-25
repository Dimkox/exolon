#!/usr/bin/env python3
"""Wave B — самопроверяющийся измеритель четырёх исправлений (P1-1/P1-2/P1-3/P1-5).

Авторитет: change-spec этого пакета. Имена проверок — ровно `test`-пути
acceptance_criteria/invariants/forbidden_outcomes:

    spawn_ground_all_maps      AC-001  BOUNDED+PREFERENCE (amendment 2): в окне ±16px ближайший
                                       топ foot-спаня, body-clear — предпочтение (не фильтр);
                                       пустое окно — маркер не тронут, карта перечислена;
                                       bound ≤16px, no-worse-than-base (buried 48 ≤ base 61),
                                       старая формула даёт 37/59/29, отклонённое безграничное —
                                       91/50 (оба контроля краснеют); carried-Y раскрытие в шапке;
    piston_anchor_all_pistons  AC-002  46/46 поршней достают до полосы ног,
                                       старый якорь строки маркера проваливает тот же предикат;
    beam_shared_hp_all_maps    AC-003  поле луча = 25 хитов на пару сторон, сумма по картам;
    bullet_cull_bounds         AC-004  blaster bound = clamp+muzzle+width (594) — ни один
                                       выстрел не рождается за своей границей (origin ≤578);
                                       та же политика для гранат (564, inline-литералы ушли);
                                       переход экрана x>510 не тронут;
    controls_flip              AC-005  каждый отменённый контроль реально переворачивается,
                                       битая фикстура падает громко, harness-контроли на месте;
    no_magic_offsets           FORBID-001 ни per-map таблиц, ни литералов ±16, TMX не редактированы;
    single_surface_query       FORBID-002 один запрос поверхности, у него четыре потребителя,
                                       ad-hoc вычислений земли больше нет;
    zone_index_formula         INV-001 int(zoneNumber) == (stage-1)*25+(scene-1), канон — имя файла;
    pinned_geometry_unchanged  INV-002 512x384, x>510, clamp 544, ветка worldBottomLeft,
                                       геометрия поршня/пули и прямоугольники коллизии стабильны.

Числа берутся из продукта, а не из моей копии: константы разбираются regex'ом из
Swift-исходников, а формулы спавна/поршней/группировки лучей additionally
исполняются НАСТОЯЩИМ SpriteKit-free кодом через wave_b_harness/run.sh
(delta сборки = ровно одна строка импорта, негативный контроль без стаба —
техника закоммиченного piston-anchor-harness). Python-зеркало обязано совпасть
с harness пиксель-в-пиксель на всех 125 картах; расхождение = rc!=0.

Старое (для контролей) считается каноническим закоммиченным измерителем
v3_measurements.stable_feet (тот же аудиторский инструмент, что опубликовал
37/59/29), parser TMX тоже заимствован у него — fail-closed: без него цифр нет.

Запуск:  python3 wave_b_check.py [--root <путь>] [--json] [--artifact-only]
rc=0 ⇔ все проверки зелёные И все контрольные провалы перевернулись. Без swiftc
(или с --artifact-only) harness не пересобирается, но закоммиченный артефакт
всё равно сверяется; при живом запуске он обязан совпасть с артефактом байт-в-байт.
"""
from __future__ import annotations

import argparse
import base64
import json
import pathlib
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

HERE = pathlib.Path(__file__).resolve().parent
COMMITTED_MEASURER = "engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence"
HARNESS = HERE / "wave_b_harness"
ARTIFACT = HERE / "wave_b_swift.txt"
RUN_LOG = HARNESS / "last-run.txt"
TMX_MANIFEST = HERE / "tmx_base_hashes.json"
DELTAS = HERE / "wave_b_deltas.md"

# ————— закреплённые ожиданием числа (все воспроизводятся этим измерителем) —————
EXPECTED: dict[str, object] = {
    "maps_total": 125,
    "tmx_blobs_match_base_commit": 125,
    "zone_named_files": 125,
    "zone_number_present": 117,          # 8 легаси-карт L01S01..L01S08 без свойства
    "zone_number_matches_formula": 117,
    # P1-2: спавн (BOUNDED правило, AC-001 поправка 2026-09-24)
    "spawn_bounded_max_move": 16,        # ни один спавн не сдвигается больше чем на тайл
    "spawn_surface_matched": 119,        # delta 0 против поверхности из окна
    "spawn_kept_unmoved": 6,             # нет поверхности в окне — маркер не тронут
    "spawn_kept_files": ["L01S17.tmx", "L02S24.tmx", "L03S06.tmx",
                         "L04S09.tmx", "L04S19.tmx", "L05S24.tmx"],
    "spawn_old_rule_hist": {"0": 37, "16": 59, "-16": 29},   # контрольный baseline (stable_feet)
    "spawn_new_vs_marker_hist": {"0": 41, "16": 83, "-16": 1},
    "spawn_rejected_unbounded_moved": 91,  # отклонённое безграничное правило сдвигало всего
    "spawn_rejected_unbounded_beyond_tile": 50,  # ...из них за пределы ±16px — 50 (45+5)
    "spawn_pool_types": {"clear": 71, "dirty": 48, "kept": 6},   # preference-выбор
    "spawn_buried_after": 48,              # телом в грунте после фикса
    "spawn_buried_base": 61,               # телом в грунте на base 295690b (no-worse control)
    # P1-1: поршни
    "piston_objects": 46,
    "piston_maps": 27,
    "piston_anchor_moved": 43,           # новый якорь != строка маркера
    "piston_lethal_new": 46,
    # контроль СТАРЫМ якорем: 3 у реальной поверхности + 3 дымящих над void-шахтой
    # (ноги игрока там на fallback-полосе и старый хитбокс [0,64] её задевает).
    # Закоммиченный p1-1 probe считал 3, потому что у его band-референса нет
    # понятия плоскости; предикат «все 46 летальны» проваливается в обоих случаях.
    "piston_lethal_old": 6,
    "piston_from_plane_fallback": 3,     # нет колонки в пределе — общий fallback-пол
    # P1-5: лучи
    "beam_markers": 20,
    "beam_maps": 10,
    "beam_fields": 10,                   # 1 поле на карту (пара up/down)
    "beam_field_sides": 2,
    "beam_hit_points_per_field": 25,
    "beam_total_hit_points": 250,        # 25 × 10
    "beam_total_hit_points_old": 500,    # контроль: по 25 на сторону
    "beam_destroy_hit_index": 25,        # из исполняемого BeamFieldModel
    "beam_notify_count": 1,
    # P1-3: пули/гранаты (AC-004 amended: дульный вылет + та же политика гранат)
    "bullet_cull_bound_old": 528,
    "bullet_cull_bound_new": 594,         # 544 clamp + 34 muzzle + 16 width
    "bullet_cull_min_new": -50,           # -(34+16): левое зеркало дульного вылета
    "blaster_muzzle_offset": 34,
    "grenade_old_cull_bound": 536,         # inline logicalSize.width + 24
    "grenade_cull_bound_new": 564,         # 544 + 4 throw + 16 width
    "grenade_cull_min_new": -20,          # -(4+16)
    "grenade_max_reachable_origin": 548,  # 544 + 4 — старая граница убивала при рождении
    "player_clamp_max": 544,
    "player_clamp_min": 24,
    "bullet_width": 16,
    "maps_solid_right_of_512": 61,
    "max_solid_right_edge": 560,
    "logical_width": 512,
    "logical_height": 384,
    "screen_exit_trigger": 510,
    # INV-002 стабильность
    "renderer_rects_identical_all_maps": 125,
    "renderer_rects_total": 1437,
    "piston_hit_inset": 3,
    "piston_hit_width": 42,
    "piston_travel": 64,
    "piston_node_h": 64,
}


def find_root() -> pathlib.Path:
    here = pathlib.Path(__file__).resolve()
    for cand in [here.parent, *here.parents]:
        if (cand / "Exolon" / "Resources").is_dir() and (cand / ".git").exists():
            return cand
    print("FATAL: корень репозитория не найден от", here)
    raise SystemExit(2)


ROOT = find_root()

sys.path.insert(0, str(ROOT / COMMITTED_MEASURER))
try:
    import v3_measurements as v3  # noqa: E402  канонический парсер TMX и старое правило спавна
except Exception as exc:  # fail-closed: без закоммиченного измерителя сверять нечем
    print(f"FATAL: нет доступа к закоммиченному измерителю {COMMITTED_MEASURER}: {exc}")
    raise SystemExit(2)

# ————————————————————— разбор констант из Swift —————————————————————

GAME_CONSTANTS = ROOT / "Exolon/GameCore/GameConstants.swift"
LOADER = ROOT / "Exolon/GameCore/Levels/TMXMapLoader.swift"
RUNTIME = ROOT / "Exolon/GameCore/Levels/TMXLevelRuntime.swift"
RENDERER = ROOT / "Exolon/GameCore/Levels/TMXTileMapRenderer.swift"
OBSTACLES = ROOT / "Exolon/GameCore/Objects/LevelObstacles.swift"
PLAYER = ROOT / "Exolon/GameCore/Player/Player.swift"
BULLET = ROOT / "Exolon/GameCore/Weapons/BlasterBullet.swift"
GRENADE = ROOT / "Exolon/GameCore/Weapons/Grenade.swift"
SCENE = ROOT / "Exolon/GameCore/GameScene.swift"


def read(p: pathlib.Path) -> str:
    return p.read_text(encoding="utf-8")


def parse_game_constants() -> dict[str, object]:
    """Значения констант GameConstants — из исходника, не из моей копии.

    Комментарии снимаются, переносы строк в правой части склеиваются
    (границы cull теперь многострочные). Поддерживаются литералы CGFloat/Int,
    CGSize(width:_, height:_) и арифметика из уже разобранных имён.
    Неизвестный RHS -> KeyError (fail-closed).
    """
    src = re.sub(r"//.*", "", read(GAME_CONSTANTS))
    src = re.sub(r"\s+", " ", src)
    decls: dict[str, str] = {}
    for m in re.finditer(r"static let (\w+)(?::\s*[\w.]+)?\s*=\s*(.+?)(?=\s+static let |\s*$)", src):
        decls[m.group(1)] = m.group(2).strip()
    values: dict[str, object] = {}

    def resolve(name: str, depth: int = 0) -> object:
        if name in values:
            return values[name]
        if depth > 8 or name not in decls:
            raise KeyError(f"GameConstants.{name} неразложима")
        rhs = decls[name]
        cm = re.fullmatch(r"CGSize\(width: ([\d.]+), height: ([\d.]+)\)", rhs)
        if cm:
            out = (float(cm.group(1)), float(cm.group(2)))
        else:
            expr = re.sub(r"\b(\w+)\.(width|height)\b",
                          lambda mm: repr(resolve(mm.group(1))[0 if mm.group(2) == "width" else 1]), rhs)
            expr = re.sub(r"\b[A-Za-z_]\w*\b", lambda mm: repr(resolve(mm.group(0))), expr)
            if not re.fullmatch(r"[\d\.eE+\-*/() ]+", expr):
                raise KeyError(f"неизвестная форма RHS: {rhs}")
            out = eval(expr, {"__builtins__": {}})  # noqa: S307 — только чистая арифметика выше
        values[name] = out
        return out

    for key in ("logicalSize", "defaultGroundY", "playerSpriteSize", "playerStandingMovementSize",
                "playerMaximumCenterX", "playerMinimumCenterX", "footSupportHorizontalInset",
                "blasterBulletSize", "blasterMuzzleOffsetX", "blasterCullMaximumX", "blasterCullMinimumX",
                "grenadeSize", "grenadeThrowOffsetX", "grenadeCullMaximumX", "grenadeCullMinimumX",
                "pistonNodeSize", "pistonTravel", "pistonHitXInset", "pistonHitWidth"):
        resolve(key)
    return values


GC = parse_game_constants()
LOADER_SRC = read(LOADER)
RUNTIME_SRC = read(RUNTIME)
OBSTACLES_SRC = read(OBSTACLES)
BULLET_SRC = read(BULLET)
PLAYER_SRC = read(PLAYER)
SCENE_SRC = read(SCENE)
RENDERER_SRC = read(RENDERER)

BEAM_HP = int(re.search(r"static let sharedHitPoints\s*=\s*(\d+)", LOADER_SRC).group(1))

# ————————————————————— python-зеркало продукта —————————————————————


class SurfaceMirror:
    """Зеркало TMXSurfaceQuery: клетки (x0, bottom, top) из v3.load_map."""

    def __init__(self, mp: dict) -> None:
        self.tw = float(mp["TW"])
        self.ph = float(mp["PH"])
        self.tile_height = float(mp["TH"])
        self.cells = [(float(sx), float(tp)) for sx, _b, tp in mp["cells"]]
        tops = [t for _x, t in self.cells]
        self.plane = min(tops) if tops else float(GC["defaultGroundY"])

    def tops_in(self, x0: float, x1: float) -> list[float]:
        return [t for sx, t in self.cells if sx < x1 and sx + self.tw > x0]

    def ground_y(self, x0: float, x1: float, at_or_below: float) -> float:
        cands = [t for t in self.tops_in(x0, x1) if t <= at_or_below]
        return max(cands) if cands else self.plane

    # потребители:
    def resolved_spawn_feet(self, marker_x: float, marker_feet: float) -> tuple[float, list[float], str]:
        """BOUNDED + PREFERENCE (AC-001 amendment 2): топы foot-спаня в окне
        ±tile; среди них предпочитает body-clear, иначе ближайший из всех
        (never-worse-than-base), пустое окно — маркер не тронут (kept).
        Возвращает (feet, window, pool-тип: clear|dirty|kept)."""
        cx = marker_x + GC["playerSpriteSize"][0] * 0.5
        half = GC["playerStandingMovementSize"][0] * 0.5
        inset = GC["footSupportHorizontalInset"]
        tops = self.surface_tops(cx - half + inset, cx + half - inset)
        window = [t for t in tops if abs(t - marker_feet) <= self.tile_height]
        if not window:
            return marker_feet, window, "kept"
        body = self.tops_in(cx - half, cx + half)
        body_h = GC["playerStandingMovementSize"][1]
        clear = [t for t in window if not any(c > t and c - self.tile_height < t + body_h for c in body)]
        pool = clear if clear else window
        feet = min(pool, key=lambda t: (abs(t - marker_feet), t))
        return feet, window, ("clear" if clear else "dirty")

    def body_buried(self, marker_x: float, feet: float) -> bool:
        """Стоит ли тело ногами внутри грунта (топ клетки строго внутри тела)."""
        cx = marker_x + GC["playerSpriteSize"][0] * 0.5
        half = GC["playerStandingMovementSize"][0] * 0.5
        body_h = GC["playerStandingMovementSize"][1]
        return any(c > feet and c - self.tile_height < feet + body_h for c in self.tops_in(cx - half, cx + half))

    def surface_tops(self, x0: float, x1: float) -> list[float]:
        seen: list[float] = []
        for sx, t in self.cells:
            if sx < x1 and sx + self.tw > x0 and t not in seen:
                seen.append(t)
        return sorted(seen)

    def rejected_unbounded_clear_feet(self, marker_x: float, marker_feet: float) -> float:
        """ОТКЛОНЁННОЕ безграничное nearest-body-clear правило — только как
        контроль: оно сдвигало спавны дальше тайла."""
        cx = marker_x + GC["playerSpriteSize"][0] * 0.5
        half = GC["playerStandingMovementSize"][0] * 0.5
        inset = GC["footSupportHorizontalInset"]
        foot_tops = self.surface_tops(cx - half + inset, cx + half - inset)
        body_tops = self.tops_in(cx - half, cx + half)
        clear = [t for t in foot_tops
                 if not any(c > t and c - self.tile_height < t + GC["playerStandingMovementSize"][1]
                            for c in body_tops)]
        if not clear:
            return self.plane
        return min(clear, key=lambda t: (abs(t - marker_feet), t))

    def piston_ground_y(self, marker_x: float, marker_y: float) -> float:
        x0 = marker_x + GC["pistonHitXInset"]
        return self.ground_y(x0, x0 + GC["pistonHitWidth"], marker_y + GC["pistonTravel"])

    def walkable_piston_surface(self, marker_x: float, marker_y: float) -> float:
        """Самая верхняя ОПУСТИМАЯ (body-clear для стоячего тела) поверхность
        под поднятым протектором — тот пол, на котором нога игрока у поршня."""
        x0 = marker_x + GC["pistonHitXInset"]
        x1 = x0 + GC["pistonHitWidth"]
        tread = marker_y + GC["pistonTravel"]
        tops = self.tops_in(x0, x1)
        body_h = GC["playerStandingMovementSize"][1]
        cands = [t for t in tops
                 if t <= tread and not any(c > t and c - self.tile_height < t + body_h for c in tops)]
        return max(cands) if cands else self.plane

    def query_collision_rects(self) -> list[tuple[float, float, float, float]]:
        """СЛЕПОК НОВОГО TMXSurfaceQuery.collisionRects (product, TMXMapLoader.swift):
        уникальные топы по insertion-order → sort(reverse); для каждого топа клетки
        filtered+sorted по x0; merge при cell.x0 == run.x1. НЕЗАВИСИМ от
        old_collision_rects (тот строит rows-dict; иной обход и порядок)."""
        tops: list[float] = []
        for _sx, t in self.cells:
            if t not in tops:
                tops.append(t)
        tops.sort(reverse=True)
        rects: list[tuple[float, float, float, float]] = []
        for top in tops:
            row = sorted(sx for sx, t in self.cells if t == top)
            x0 = row[0]
            x1 = x0 + self.tw
            for sx in row[1:]:
                if sx == x1:
                    x1 = sx + self.tw
                else:
                    rects.append((x0, top - self.tile_height, x1 - x0, self.tile_height))
                    x0, x1 = sx, sx + self.tw
            rects.append((x0, top - self.tile_height, x1 - x0, self.tile_height))
        return rects


def base_build_collision_rects(mp: dict) -> list[tuple[float, float, float, float]]:
    """Точная портировка base-коммитного buildCollisionRects
    (`git show 295690b:Exolon/GameCore/Levels/TMXTileMapRenderer.swift`) —
    построчный while-merge НАПЯМУЮ по gid'ам Collision-слоя (row-major).
    Это СТАРАЯ сторона пары base-vs-new; независима от обоих cell-портов
    SurfaceMirror (другой вход: gids, а не клетки; другой обход)."""
    root = ET.fromstring(mp["text"])
    collision = None
    for lay in root.iter("layer"):
        if (lay.get("name") or "").lower() == "collision":
            collision = lay
            break
    if collision is None:
        return []
    data = collision.find("data")
    if data is None:
        return []
    W = int(collision.get("width") or 0)
    H = int(collision.get("height") or 0)
    gids = v3.decode_layer(data)
    if len(gids) != W * H:
        return []
    TW, TH = mp["TW"], mp["TH"]
    PH = mp["PH"]
    rects: list[tuple[float, float, float, float]] = []
    for row in range(H):
        column = 0
        while column < W:
            if gids[row * W + column] & 0x1FFF_FFFF == 0:
                column += 1
                continue
            start = column
            column += 1
            while column < W:
                if gids[row * W + column] & 0x1FFF_FFFF == 0:
                    break
                column += 1
            y = PH - (row + 1) * TH
            rects.append((start * TW, y, (column - start) * TW, TH))
    return rects


def beam_boxes(mp: dict) -> list[tuple[float, float, float, float]]:
    """Арифметика коробок из TMXLevelRuntime (закреплена regex-стражей ниже)."""
    out = []
    for o in mp["objects"]:
        if o["name"] != "source_marker":
            continue
        props = dict(o["props"])
        if "beam_" not in props.get("sourceBlock", ""):
            continue
        sx = float(int(props.get("sourceX", "0"))) * 16
        sy_top = float(int(props.get("sourceY", "0"))) * 16
        bottom_y = mp["PH"] - sy_top - 32
        out.append((sx, max(0.0, bottom_y - 240), 48.0, 272.0))
    return out


def beam_grouping(boxes: list[tuple[float, float, float, float]]) -> list[list[int]]:
    """Зеркало TMXBeamGrouping.groups(for:) — строгое перекрытие x-интервалов.
    Корпус обязан иметь различные minX (иначе порядок Swift-sort не детерминирован) —
    это проверяется до сверки."""
    indexed = sorted(range(len(boxes)), key=lambda i: (boxes[i][0], i))
    groups: list[list[int]] = []
    current: list[int] = []
    current_max_x = 0.0
    for i in indexed:
        if current and boxes[i][0] >= current_max_x:
            groups.append(list(current))
            current = []
        current.append(i)
        current_max_x = max(current_max_x, boxes[i][0] + boxes[i][2])
    if current:
        groups.append(list(current))
    return groups


class PoolMirror:
    """Зеркало BeamFieldModel: общий пул, destroyed ровно на 25-м хите."""

    def __init__(self, hp: int) -> None:
        self.remaining = hp
        self.notified = 0

    def hit(self) -> bool:
        if self.remaining <= 0:
            return False
        self.remaining -= 1
        if self.remaining <= 0:
            self.notified += 1
            return True
        return False


# ————————————————————— корпус и артефакт harness —————————————————————

_corpus: list[dict] = []


def corpus() -> list[dict]:
    global _corpus
    if not _corpus:
        for p in sorted((ROOT / "Exolon" / "Resources").glob("*.tmx")):
            mp = v3.load_map(p)
            mp["zone"] = zone_from_name(p.stem)
            mp["path"] = p
            _corpus.append(mp)
    return _corpus


def zone_from_name(stem: str) -> int:
    m = re.fullmatch(r"L(\d{2})S(\d{2})", stem)
    if not m:
        raise ValueError(f"не каноническое имя карты: {stem}")
    stage, scene = int(m.group(1)), int(m.group(2))
    return (stage - 1) * 25 + (scene - 1)


def run_harness() -> tuple[str | None, str | None]:
    """Живой запуск продуктового кода; (None, причина) при --artifact-only/нет swiftc/сбое.

    stderr идёт в ОДНОРАЗОВЫЙ scratch-файл (в нём PID сборки — в дерево не
    пишем, fingerprint обязан стоять на месте); закоммиченный
    wave_b_harness/last-run.txt остаётся статичным свидетельством."""
    if getattr(sys, "wave_b_artifact_only", False):
        return None, "artifact-only"
    if not shutil.which("swiftc"):
        return None, "swiftc отсутствует"
    try:
        proc = subprocess.run(["bash", str(HARNESS / "run.sh")], capture_output=True,
                              text=True, timeout=180, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"запуск провален: {exc}"
    if proc.returncode != 0:
        return None, f"rc={proc.returncode}: {proc.stderr[-1500:]}"
    scratch = pathlib.Path(tempfile.mkdtemp(prefix="wave-b-meter-")) / "run-stderr.txt"
    scratch.write_text(proc.stderr, encoding="utf-8")
    _harness_stderr_scratch[0] = str(scratch)
    return proc.stdout, None


_harness_stderr_scratch: list[str] = [""]


_harness_result: dict = {}


def write_if_changed(path: pathlib.Path, text: str) -> bool:
    """Evidence-файлы переписываются ТОЛЬКО при изменении содержимого:
    повторный прогон измерителя не должен двигать fingerprint дерева
    (gate source-stability). Возвращает True, если файл изменён."""
    try:
        if path.read_text(encoding="utf-8") == text:
            return False
    except (OSError, UnicodeDecodeError):
        pass
    path.write_text(text, encoding="utf-8")
    return True


def harness() -> dict:
    if not _harness_result:
        live, error = run_harness()
        artifact_text = ARTIFACT.read_text(encoding="utf-8") if ARTIFACT.exists() else ""
        _harness_result["live"] = live
        _harness_result["error"] = error
        _harness_result["attempted"] = not (getattr(sys, "wave_b_artifact_only", False)
                                            or not shutil.which("swiftc"))
        _harness_result["live_matches_artifact"] = (live == artifact_text) if live else False
        _harness_result["artifact"] = parse_artifact(artifact_text if not live else live)
        _harness_result["ran"] = live is not None
    return _harness_result


def parse_artifact(text: str) -> dict:
    art: dict = {"spawn": {}, "piston": [], "beam": {}, "plane": {}, "rects": {},
                 "geom": {}, "pool": {}}
    for line in text.splitlines():
        parts = line.split()
        if not parts:
            continue
        kv = dict(tok.split("=", 1) for tok in parts[1:] if "=" in tok)
        if parts[0] == "GEOMETRY":
            art["geom"] = {k: float(v) for k, v in kv.items()}
        elif parts[0] == "BEAMPOOL":
            art["pool"] = kv
        elif parts[0] == "PLANESRC":
            art["plane"][kv["map"]] = (int(kv["cells"]), float(kv["plane"]))
        elif parts[0] == "RECTS":
            coords = [tuple(float(v) for v in r.split(","))
                      for r in kv["coords"].split(";") if r] if "coords" in kv else []
            art["rects"][kv["map"]] = (int(kv["count"]), coords)
        elif parts[0] == "SPAWN":
            surfs = kv["windowTops"].strip("[]")
            art["spawn"][kv["map"]] = (float(kv["markerFeet"]), float(kv["spawnFeet"]),
                                       [float(s) for s in surfs.split(";")] if surfs else [],
                                       float(kv["plane"]))
        elif parts[0] == "PISTON":
            art["piston"].append((kv["map"], float(kv["x"]), float(kv["markerY"]), float(kv["groundY"])))
        elif parts[0] == "BEAM":
            groups = [g.split("+") for g in kv["groups"].strip("[]").split(",")]
            art["beam"][kv["map"]] = (int(kv["boxes"]), int(kv["fields"]),
                                      [[int(i) for i in g] for g in groups])
        elif parts[0] == "SUMMARY":
            art["summary"] = {k: int(v) for k, v in kv.items()}
    return art


# ————————————————————— помощники проверок —————————————————————


def spawn_rows() -> list[dict]:
    rows = []
    art = harness()["artifact"]
    for mp in corpus():
        v = next(o for o in mp["objects"] if o["name"] == "vitorc")
        mirror = SurfaceMirror(mp)
        marker_feet = mp["PH"] - v["y"]              # vitorc: h=0 во всех 125
        feet, window, pool_type = mirror.resolved_spawn_feet(v["x"], marker_feet)
        cx = v["x"] + GC["playerSpriteSize"][0] * 0.5
        half = GC["playerStandingMovementSize"][0] * 0.5
        inset = GC["footSupportHorizontalInset"]
        query_at_feet = mirror.ground_y(cx - half + inset, cx + half - inset, at_or_below=feet)
        old_rest = v3.stable_feet(mp)
        # опора: top в foot-спане ровно под ногами (Player.refreshGroundSupport)
        supported = any(abs(t - feet) <= 1.5 for t in mirror.tops_in(cx - half + inset, cx + half - inset))
        rejected = mirror.rejected_unbounded_clear_feet(v["x"], marker_feet)
        rows.append({
            "map": mp["file"], "zone": mp["zone"], "marker": marker_feet, "feet": feet,
            "plane": mirror.plane, "query_at_feet": query_at_feet,
            "delta_query": feet - query_at_feet, "delta_marker": feet - marker_feet,
            "delta_old": old_rest - marker_feet if old_rest is not None else None,
            "window": window, "pool_type": pool_type, "kept": pool_type == "kept",
            "supported": supported,
            "buried_new": mirror.body_buried(v["x"], feet),
            "buried_base": mirror.body_buried(v["x"], old_rest) if old_rest is not None else False,
            "rejected_feet": rejected,
            "harness": art["spawn"].get(mp["file"]),
        })
    return rows


def piston_rows() -> list[dict]:
    rows = []
    art = harness()["artifact"]
    for mp in corpus():
        mirror = SurfaceMirror(mp)
        for o in mp["objects"]:
            if o["name"] != "piston":
                continue
            anchor = mp["PH"] - o["y"]               # продуктовый worldBottomLeft (h ветки не трогает)
            g = mirror.piston_ground_y(o["x"], anchor)
            f = mirror.walkable_piston_surface(o["x"], anchor)
            travel = GC["pistonTravel"]
            hit0 = o["x"] + GC["pistonHitXInset"]
            hit1 = hit0 + GC["pistonHitWidth"]
            body_clear = not any(c > g and c - mirror.tile_height < g + 63.0
                                 for c in mirror.tops_in(hit0, hit1))
            from_plane = not any(t <= anchor + travel for t in mirror.tops_in(hit0, hit1))
            # поштучное сравнение с исполненным настоящим Swift (wave_b_harness)
            match = [sg for m2, sx, sy, sg in art["piston"]
                     if m2 == mp["file"] and abs(sx - o["x"]) < 0.5 and abs(sy - anchor) < 0.5]
            rows.append({
                "map": mp["file"], "x": o["x"], "y": o["y"], "anchor": anchor, "ground": g,
                "walkable": f, "from_plane": from_plane, "body_clear": body_clear,
                "new_lethal": g == f and min(g + travel, f + 63.0) - max(g, f) > 0,
                "old_lethal": min(anchor + travel, f + 63.0) - max(anchor, f) > 0,
                "swift": match[0] if match else None,
                "swift_agrees": bool(match) and abs(match[0] - g) < 0.5,
            })
    return rows


def beam_rows() -> list[dict]:
    rows = []
    art = harness()["artifact"]
    for mp in corpus():
        boxes = beam_boxes(mp)
        if not boxes:
            continue
        groups = beam_grouping(boxes)
        rows.append({"map": mp["file"], "markers": len(boxes), "fields": len(groups), "groups": groups,
                     "boxes": boxes, "harness": art["beam"].get(mp["file"])})
    return rows


def old_bullet_cull_bound() -> float:
    """Старая граница из base-коммита (BLASTER update: logicalSize.width + 16)."""
    return GC["logicalSize"][0] + 16.0


def git_blob_sha1(path: pathlib.Path) -> str:
    import hashlib
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def git_show_base(rel: str):
    """Текст файла на base-коммите 295690b; None при недоступном git."""
    try:
        proc = subprocess.run(["git", "-C", str(ROOT), "show", f"295690b:{rel}"],
                              capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def wave_base() -> str:
    """База added-lines скана: актуальный rebase-base ветки (merge-base с
    origin/main после перестановки на серию A→B→…), fallback — исторический
    295690b. Иначе чужие волновые строки (например merge'нутый wave-A)
    считались бы «нашими добавленными» и размывали атрибуцию FORBID-001.
    Base-порт renderer'а и TMX-манифест ПРИНЦИПИАЛЬНО остаются на 295690b —
    это якоря бейса (git show / blob-хэши), а не diff-scope."""
    try:
        proc = subprocess.run(["git", "-C", str(ROOT), "merge-base", "HEAD", "origin/main"],
                              capture_output=True, text=True, timeout=30, check=False)
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "295690b"


def git_added_lines(base: str):
    """[(path, line)] добавленных строк *.swift под Exolon/ против base; None,
    если git недоступен (тогда скан честно краснеет, а не молчит)."""
    try:
        proc = subprocess.run(["git", "-C", str(ROOT), "diff", "-U0", base, "--", "Exolon"],
                              capture_output=True, text=True, timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    out: list[tuple[str, str]] = []
    path = None
    for line in proc.stdout.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("+") and not line.startswith("+++"):
            if path and path.endswith(".swift"):
                out.append((path, line[1:]))
    return out


# ————————————————————— проверки —————————————————————


def zone_index_formula() -> list[str]:
    errs: list[str] = []
    files = sorted(p.stem for p in (ROOT / "Exolon" / "Resources").glob("*.tmx"))
    check(len(files) == EXPECTED["maps_total"], f"карт {len(files)} != 125", errs)
    check([zone_from_name(s) for s in files] == list(range(125)),
          "имена файлов не образуют зоны 000..124 по порядку", errs)
    present = 0
    for mp in corpus():
        root = ET.fromstring(mp["text"])
        zn = None
        for props in root.findall("properties"):
            for pr in props.findall("property"):
                if pr.get("name") == "zoneNumber":
                    zn = pr.get("value")
        if zn is None:
            continue
        present += 1
        if int(zn) != mp["zone"]:
            errs.append(f"{mp['file']}: zoneNumber={zn} != (stage-1)*25+(scene-1)={mp['zone']}")
    check(present == EXPECTED["zone_number_present"], f"zoneNumber есть у {present}, ожидал 117", errs)
    check(present == EXPECTED["zone_number_matches_formula"], "не все zoneNumber совпали формуле", errs)
    # контроль обязан перевернуться: сдвиг свойства на 1 ломает формулу
    mutated = 0
    for mp in corpus():
        root = ET.fromstring(mp["text"])
        for props in root.findall("properties"):
            for pr in props.findall("property"):
                if pr.get("name") == "zoneNumber" and int(pr.get("value", "0")) + 1 != mp["zone"]:
                    mutated += 1
    check(mutated > 0, "мутация zoneNumber не ломает предикат — проверка декоративна", errs)
    print(f"  zones: 125 файлов = 000..124, zoneNumber у {present}/125, все формуле равны; "
          f"мутация +1 ловится на {mutated}")
    return errs


def spawn_ground_all_maps() -> list[str]:
    errs: list[str] = []
    rows = spawn_rows()
    print("  AC-001 disclosure: runtime потребляет resolved spawn Y только на stage-start "
          "входах/смертях (carried-Y, GameScene.swift:638-646) — ~5-6 zone entries за проход; "
          "обычные переходы несут y предыдущей зоны.")
    check(len(rows) == 125, f"строк спавна {len(rows)}", errs)
    # BOUND (AC-001 amendment 2): ни один спавн не двигается дальше одного тайла
    over = [r["map"] for r in rows if abs(r["delta_marker"]) > EXPECTED["spawn_bounded_max_move"]]
    check(not over, f"спавны сдвинуты >16px: {over[:5]}", errs)
    matched = [r for r in rows if not r["kept"]]
    kept = [r for r in rows if r["kept"]]
    check(len(matched) == EXPECTED["spawn_surface_matched"], f"поверхностей найдено {len(matched)} != 119", errs)
    check([r["map"] for r in kept] == EXPECTED["spawn_kept_files"],
          f"нет-поверхностные карты рассинхронизированы: {[r['map'] for r in kept]}", errs)
    # PREFERENCE: clear-пул выбирается когда может; в dirty-пуле Feet == nearest
    # window top (не filter-выброс), kept == unmoved
    pools = Counter(r["pool_type"] for r in rows)
    check({k: v for k, v in pools.items()} == EXPECTED["spawn_pool_types"],
          f"распределение pref-пула {dict(pools)} != закрепленное", errs)
    for r in matched:
        if r["delta_query"] != 0:
            errs.append(f"{r['map']}: delta vs запрос {r['delta_query']} != 0")
        if r["feet"] not in r["window"] or r["feet"] % 16 != 0:
            errs.append(f"{r['map']}: feet {r['feet']} вне окна {r['window']}")
        if r["pool_type"] == "dirty" and r["feet"] != min(
                r["window"], key=lambda t: (abs(t - r["marker"]), t)):
            errs.append(f"{r['map']}: в dirty-пуле взят не ближайший топ окна (tie→ниже)")
        if r["pool_type"] == "clear" and r["buried_new"]:
            errs.append(f"{r['map']}: clear-пул, но тело в грунте — зеркало врёт")
        if not r["supported"]:
            errs.append(f"{r['map']}: ноги {r['feet']} без опоры в foot-спане")
    # NO-WORSE-THAN-BASE: спавнов с телом в грунте не больше, чем на base
    buried_new = sum(1 for r in rows if r["buried_new"])
    buried_base = sum(1 for r in rows if r["buried_base"])
    check(buried_new == EXPECTED["spawn_buried_after"], f"buried after {buried_new} != 48", errs)
    check(buried_base == EXPECTED["spawn_buried_base"], f"buried base {buried_base} != 61", errs)
    check(buried_new <= buried_base,
          f"ФИКС УХУДШИЛ спавны в грунте: {buried_new} > {buried_base} (no-worse-than-base)", errs)
    # kept: маркер не тронут, и в окне нет НИ ОДНОЙ Collision-поверхности
    for r in kept:
        if r["feet"] != r["marker"] or r["window"]:
            errs.append(f"{r['map']}: kept-карта не удовлетворяет определению (feet={r['feet']}, "
                        f"marker={r['marker']}, window={r['window']})")
    # исполнение настоящим Swift пиксель-в-пиксель
    mismatch = [r["map"] for r in rows if r["harness"] is None
                or abs(r["harness"][1] - r["feet"]) > 0.01 or r["harness"][2] != r["window"]]
    check(not mismatch, f"harness разошёлся с зеркалом на картах {mismatch[:5]}", errs)
    hist_new = Counter(r["delta_marker"] for r in rows)
    hist_old = Counter(r["delta_old"] for r in rows)
    pin_hist = {str(int(k)): v for k, v in hist_old.items()}
    check(pin_hist == EXPECTED["spawn_old_rule_hist"],
          f"старое правило дало {pin_hist}, ожидался аудитовый сплит 37/59/29", errs)
    check({str(int(k)): v for k, v in hist_new.items()} == EXPECTED["spawn_new_vs_marker_hist"],
          f"bounded delta-vs-маркер гистограмма {dict(hist_new)} не закрепленная", errs)
    print(f"  AC-001 (bounded+preference): matched {len(matched)}/125 delta 0 "
          f"(clear {pools['clear']} / dirty-nearest {pools['dirty']}), kept {len(kept)} "
          f"({', '.join(r['map'][:-4] for r in kept)} — нет поверхности в окне ±16px); "
          f"buried: base {buried_base} -> after {buried_new}; hist vs marker: "
          f"{ {str(int(k)): v for k, v in sorted(hist_new.items(), key=lambda x: float(x[0]))} }; "
          f"старый контроль: {pin_hist}")
    return errs


def piston_anchor_all_pistons() -> list[str]:
    errs: list[str] = []
    rows = piston_rows()
    check(len(rows) == EXPECTED["piston_objects"], f"поршней {len(rows)} != 46", errs)
    maps = {r["map"] for r in rows}
    check(len(maps) == EXPECTED["piston_maps"], f"карт с поршнями {len(maps)} != 27", errs)
    swift_bad = [r for r in rows if not r["swift_agrees"]]
    check(not swift_bad, f"Swift groundY разошёлся с зеркалом: {[(r['map'], r['x']) for r in swift_bad[:3]]}", errs)
    lethal_new = sum(1 for r in rows if r["new_lethal"])
    lethal_old = sum(1 for r in rows if r["old_lethal"])
    moved = sum(1 for r in rows if r["ground"] != r["anchor"])
    plane_fb = sum(1 for r in rows if r["from_plane"])
    clear = sum(1 for r in rows if r["body_clear"])
    check(lethal_new == EXPECTED["piston_lethal_new"], f"летальных новым якорем {lethal_new} != 46", errs)
    check(lethal_old == EXPECTED["piston_lethal_old"],
          f"летальных СТАРЫМ якорем {lethal_old} != 6 (контроль не перевернулся или корпус уехал)", errs)
    check(moved == EXPECTED["piston_anchor_moved"], f"якорь сдвинулся на {moved} != 43", errs)
    check(plane_fb == EXPECTED["piston_from_plane_fallback"], f"plane-fallback {plane_fb} != 3", errs)
    check(clear == 46, f"якорь не body-clear на {46 - clear} поршнях", errs)
    print(f"  AC-002: летальных новым {lethal_new}/46, старым (контроль) {lethal_old}/46, "
          f"сдвинуто якорей {moved}, plane-fallback {plane_fb}")
    return errs


def beam_shared_hp_all_maps() -> list[str]:
    errs: list[str] = []
    rows = beam_rows()
    markers = sum(r["markers"] for r in rows)
    fields = sum(r["fields"] for r in rows)
    check(markers == EXPECTED["beam_markers"], f"beam-маркеров {markers} != 20", errs)
    check(len(rows) == EXPECTED["beam_maps"], f"карт с лучами {len(rows)} != 10", errs)
    check(fields == EXPECTED["beam_fields"], f"полей {fields} != 10", errs)
    for r in rows:
        if r["harness"] is None or r["harness"][0] != r["markers"] or r["harness"][1] != r["fields"] \
                or r["harness"][2] != r["groups"]:
            errs.append(f"{r['map']}: группировка расходится с исполненным Swift: {r['harness']} vs {r['groups']}")
        if any(len(g) != EXPECTED["beam_field_sides"] for g in r["groups"]):
            errs.append(f"{r['map']}: группа не из двух сторон: {r['groups']}")
    # determinism precondition (audit §Q4): в корпусе нет коробок с равным minX;
    # при равных minX и Swift (сортировка по (minX, index)), и зеркало дают
    # детерминированный порядок, но сам факт смены данных надо поймать
    ties = sum(sum(1 for i in range(len(r["boxes"])) for j in range(i)
                   if r["boxes"][i][0] == r["boxes"][j][0]) for r in rows)
    check(ties == 0, f"beam-коробки с равным minX ({ties}) — парная семантика требует ревью", errs)
    tie_grouped = beam_grouping([(0.0, 0.0, 48.0, 272.0), (0.0, 10.0, 48.0, 272.0)])
    check(tie_grouped == [[0, 1]], f"mirror не детерминирован на tie: {tie_grouped}", errs)
    check("a.offset < b.offset" in LOADER_SRC, "Swift-сортировка потеряла index tie-break", errs)
    # AC-003 предикат: сумма хит-поинтов по карте == 25 × число полей
    total_new = total_old = 0
    for r in rows:
        total_new += r["fields"] * BEAM_HP
        total_old += r["markers"] * BEAM_HP
    check(total_new == EXPECTED["beam_total_hit_points"], f"сумма HP {total_new} != 250", errs)
    check(total_old == EXPECTED["beam_total_hit_points_old"],
          f"старая модель дала {total_old}, ожидался контроль 500", errs)
    # исполнение пула настоящим Swift (BeamFieldModel)
    pool = harness()["artifact"].get("pool", {})
    check(int(pool.get("destroyHitIndex", -1)) == EXPECTED["beam_destroy_hit_index"],
          f"исполняемый пул уничтожается на {pool.get('destroyHitIndex')}-м хите != 25", errs)
    check(pool.get("aliveAfter24") == "true" and int(pool.get("notifyCount", -1)) == EXPECTED["beam_notify_count"]
          and pool.get("extraHit") == "false" and pool.get("isActiveAfter") == "false",
          f"пул-симуляция не прошла: {pool}", errs)
    check(int(pool.get("sharedHitPoints", -1)) == BEAM_HP == 25, "константа пула != 25", errs)
    # структурные стражи: сторона больше не считает хиты сама; поле строится на группу;
    # уничтожение покрывает обе стороны одним колбэком
    check("hitPoints" not in OBSTACLES_SRC.split("class ForceFieldBarrier")[1].split("class ")[0],
          "у ForceFieldBarrier остался собственный hitPoints", errs)
    check(re.search(r"func hitByBlaster\(\) -> Bool \{ field\.registerHit\(\) \}", OBSTACLES_SRC),
          "hitByBlaster стороны не делегирует общему пулу", errs)
    check(len(re.findall(r"remainingHitPoints -= 1", LOADER_SRC)) == 1,
          "счётчик пула должен декрементиться ровно в одном месте", errs)
    check(re.search(r"for group in TMXBeamGrouping\.groups\(for: beamBoxes\) \{\s*\n\s*let field = BeamFieldModel\(\)",
                    RUNTIME_SRC), "runtime не строит одно BeamFieldModel на группу", errs)
    check("field.onDestroyed { [weak side] in side?.coverDestroyed() }" in RUNTIME_SRC
          and "field.onDestroy =" not in RUNTIME_SRC,
          "уничтожение поля не покрывает все стороны слабыми захватами (retain cycle = утечка на уровень)", errs)
    check("func onDestroyed(_ handler: @escaping () -> Void)" in LOADER_SRC
          and "var onDestroy: (() -> Void)?" not in LOADER_SRC,
          "BeamFieldModel снова владеет single-strong-closure (цикл field↔side)", errs)
    check(re.search(r"CGRect\(x: sx, y: max\(0, bottomY - 240\), width: 48, height: 272\)", RUNTIME_SRC),
          "арифметика beam-коробки уехала из закреплённой (иначе зеркало/харнес врёт)", errs)
    # зеркало пула совпадает с исполняемым (свои 25 хитов)
    mirror_pool = PoolMirror(BEAM_HP)
    idx = next(i for i in range(1, 27) if mirror_pool.hit())
    check(idx == int(pool.get("destroyHitIndex", -1)) == 25 and mirror_pool.notified == 1,
          "python-зеркало пула разошлось с продуктом", errs)
    print(f"  AC-003: полей {fields} (пары), HP/поле {BEAM_HP}, сумма {total_new}; "
          f"старая по-сторонняя модель (контроль): {total_old}")
    return errs


def bullet_cull_bounds() -> list[str]:
    errs: list[str] = []
    clamp_max = GC["playerMaximumCenterX"]
    bullet_w = GC["blasterBulletSize"][0]
    muzzle = GC["blasterMuzzleOffsetX"]
    cull = GC["blasterCullMaximumX"]
    cull_min = GC["blasterCullMinimumX"]
    check(clamp_max == EXPECTED["player_clamp_max"], f"clamp игрока {clamp_max} != 544", errs)
    check(muzzle == EXPECTED["blaster_muzzle_offset"], f"muzzle offset {muzzle} != 34", errs)
    # AC-004 clause 1: bound ≥ clamp + bullet width, и clause 2 (amended):
    # ни один выстрел не рождается за своей границей — origin при x=clamp_max
    # есть clamp+muzzle, значит bound обязан его накрывать.
    check(cull >= clamp_max + bullet_w, f"граница cull {cull} < clamp+ширина {clamp_max + bullet_w}", errs)
    check(cull >= clamp_max + muzzle, f"выстрел рождается за границей: {cull} < {clamp_max + muzzle}", errs)
    check(cull == EXPECTED["bullet_cull_bound_new"], f"cull {cull} != 594", errs)
    check(cull_min == EXPECTED["bullet_cull_min_new"], f"cull min {cull_min} != -50", errs)
    # граната: та же политика, ни одного inline-литерала в Grenade.swift
    g_throw = GC["grenadeThrowOffsetX"]
    g_w = GC["grenadeSize"][0]
    g_cull = GC["grenadeCullMaximumX"]
    g_min = GC["grenadeCullMinimumX"]
    check(g_cull >= clamp_max + g_throw + g_w, "grenade bound не накрывает clamp+throw+width", errs)
    check(g_cull == EXPECTED["grenade_cull_bound_new"], f"grenade cull {g_cull} != 564", errs)
    check(g_min == EXPECTED["grenade_cull_min_new"], f"grenade min {g_min} != -20", errs)
    gren = read(GRENADE)
    gren_code = strip_comments(gren)
    check(re.search(r"position\.x < GameConstants\.grenadeCullMinimumX", gren_code)
          and re.search(r"position\.x > GameConstants\.grenadeCullMaximumX", gren_code),
          "Grenade.swift не режет по именованным выведенным границам", errs)
    check(not re.search(r"position\.x [<>] (?:-?[\d.]+|GameConstants\.logicalSize\.width [-+] [\d.]+)", gren_code),
          "в Grenade.swift остались inline-литералы по x при cull", errs)
    # выводимость из констант (FORBID-001/AC-004): правые части — формулы, не литералы
    gc_src = read(GAME_CONSTANTS)
    check(re.search(r"playerMaximumCenterX: CGFloat =\s*logicalSize\.width \+ 32", gc_src),
          "clamp больше не выведен из logicalSize.width + 32", errs)
    check(re.search(r"blasterCullMaximumX: CGFloat =\s*playerMaximumCenterX \+ blasterMuzzleOffsetX "
                    r"\+ blasterBulletSize\.width", gc_src),
          "blaster cull не выведен из clamp+muzzle+width", errs)
    check(re.search(r"blasterCullMinimumX: CGFloat =\s*-\(blasterMuzzleOffsetX \+ blasterBulletSize\.width\)", gc_src),
          "blaster lower bound не зеркало дульного вылета", errs)
    check(re.search(r"grenadeCullMaximumX: CGFloat =\s*playerMaximumCenterX \+ grenadeThrowOffsetX "
                    r"\+ grenadeSize\.width", gc_src),
          "grenade cull не выведен из той же формулы", errs)
    # стартовые позиции игрока берут те же константы (origin ≤ bound при x=clamp)
    check(re.search(r"facing == \.right\s*\?\s*GameConstants\.blasterMuzzleOffsetX : -GameConstants\.blasterMuzzleOffsetX",
                    strip_comments(PLAYER_SRC)),
          "Player.blasterOrigin не из общей muzzle-константы", errs)
    check(re.search(r"facing == \.right\s*\?\s*GameConstants\.grenadeThrowOffsetX : -GameConstants\.grenadeThrowOffsetX",
                    strip_comments(PLAYER_SRC)),
          "Player.grenadeOrigin не из общей throw-константы", errs)
    # 528-литералы в оставшемся коде — ТОЛЬКО стартовые позиции (пузырь/ракета),
    # не cull: ни одна строка `position.x </>` не содержит 528/width+16/width+24.
    for p in ROOT.glob("Exolon/**/*.swift"):
        for ln in read(p).splitlines():
            if re.search(r"position\.x\s*[<>].*?(528|logicalSize\.width \+ 1[46]|width \+ 24)", ln):
                errs.append(f"528-стиль CULL найден в {p.name}: {ln.strip()[:80]}")
    lo = strip_code_comments_keep(read(OBSTACLES))
    check("x: 528 + CGFloat(Double.random(in: 0...32))" in lo,
          "BubbleSpawner стартовая позиция уехала — пин 528-as-spawn надо пересмотреть", errs)
    check("position = CGPoint(x: GameConstants.logicalSize.width + 16, y: startY)" in lo,
          "HomingMissile стартовая позиция уехала — пин 528-as-spawn надо пересмотреть", errs)
    # данные: ни одна solid-клетка не правее границы; 61 карт с geometry за 512
    rightmost = 0.0
    beyond = 0
    for mp in corpus():
        mx = max((sx + mp["TW"] for sx, _b, _t in mp["cells"]), default=0.0)
        rightmost = max(rightmost, mx)
        if mx > GC["logicalSize"][0]:
            beyond += 1
    check(rightmost == EXPECTED["max_solid_right_edge"], f"правый край collision {rightmost} != 560", errs)
    check(cull >= rightmost, f"cull {cull} раньше правого края геометрии {rightmost}", errs)
    check(beyond == EXPECTED["maps_solid_right_of_512"], f"карт с collision правее 512: {beyond} != 61", errs)
    # контроли: СТАРЫЕ формулы проваливают РОВНО эти предикаты
    old = old_bullet_cull_bound()
    check(old == EXPECTED["bullet_cull_bound_old"], f"старая формула границы {old} != 528", errs)
    check(not (old >= clamp_max + bullet_w and old >= rightmost),
          "старая blaster-граница прошла новый предикат", errs)
    old_gren = GC["logicalSize"][0] + 24  # base Grenade.swift inline
    check(old_gren == EXPECTED["grenade_old_cull_bound"] and old_gren < clamp_max + g_throw,
          f"старая гранатная граница {old_gren} не рождается-мёртвой (origin {clamp_max + g_throw})", errs)
    # сверка с GEOMETRY исполненного Swift
    geom = harness()["artifact"].get("geom", {})
    if geom:
        for key, val in (("cullMaxX", cull), ("cullMinX", cull_min), ("muzzleX", muzzle),
                         ("grenadeCullMaxX", g_cull), ("grenadeCullMinX", g_min),
                         ("playerMaxX", clamp_max), ("playerMinX", GC["playerMinimumCenterX"]),
                         ("bulletW", bullet_w), ("grenadeW", g_w), ("grenadeThrowX", g_throw)):
            check(abs(geom.get(key, -1) - val) < 0.01, f"Swift {key}={geom.get(key)} != разобрано {val}", errs)
    print(f"  AC-004: blaster cull {cull_min}..{cull} (clamp {clamp_max} + muzzle {muzzle} + width "
          f"{bullet_w}); grenade {g_min}..{g_cull}; рождение в границах ≤{clamp_max + muzzle}/≤{clamp_max + g_throw}; "
          f"контроли: old 528<594, old grenade 536<548; правый край данных {rightmost}")
    return errs


def controls_flip() -> list[str]:
    errs: list[str] = []
    # 1. старый спавн проваливает новый предикат (остались дельты)
    rows = spawn_rows()
    old_nonzero = sum(1 for r in rows if r["delta_old"] != 0)
    check(old_nonzero == 88, f"старое правило спавна изменилось: nonzero={old_nonzero} != 88", errs)
    # 1b. ОТКЛОНЁННОЕ безграничное nearest-body-clear правило проваливает
    # BOUND поправленного AC-001: оно сдвигало 91/125 спавнов, из них 50 — за
    # пределы тайла (45 на +32px и 5 на 112–208px), что запрещает поправка.
    rejected_moved = sum(1 for r in rows if r["rejected_feet"] != r["marker"])
    rejected_far = sum(1 for r in rows if abs(r["rejected_feet"] - r["marker"]) > 16)
    check(rejected_moved == EXPECTED["spawn_rejected_unbounded_moved"],
          f"безграничное правило сдвинуло {rejected_moved} != 91 (контроль поправки)", errs)
    check(rejected_far == 50,
          f"безграничное правило сдвинуло за тайл {rejected_far} != 50 (45×+32 + 5×112..208)", errs)
    check(all(abs(r["delta_marker"]) <= 16 for r in rows),
          "bounded-предикат пропускает большие сдвиги — контроль не перевернулся бы", errs)
    # 1c. preference НЕ вырождается в nearest: синтетическая фикстура, где
    # ближайший топ bury-тый, а чистый — дальше, обязана брать чистый.
    fake = {"TW": 16, "TH": 16, "PH": 384,
            "cells": [(16, 64, 80), (0, 48, 64), (16, 48, 64), (32, 48, 64),
                      (0, 32, 48), (16, 32, 48), (32, 32, 48)]}
    fm = SurfaceMirror(fake)
    feet_f, window_f, pool_f = fm.resolved_spawn_feet(0, 64.0)
    check(feet_f == 80.0 and pool_f == "clear",
          f"preference не сработал на фикстуре: feet={feet_f} pool={pool_f} (ожидалось 80/clear)", errs)
    check(min(window_f, key=lambda t: (abs(t - 64.0), t)) == 64.0,
          "фикстура не различает plain-nearest и preference (контроль декоративен)", errs)
    check("clearBest ?? anyBest" in LOADER_SRC,
          "Swift boundedSurfaceY потерял preference-ветку (clear shadows buried)", errs)
    # 2. старый якорь поршня проваливает летальность
    prows = piston_rows()
    check(sum(1 for r in prows if r["old_lethal"]) == 6, "контроль поршня не перевернулся", errs)
    # 3. старая beam-модель проваливает сумму 25×поля
    brows = beam_rows()
    check(sum(r["markers"] for r in brows) * BEAM_HP != sum(r["fields"] for r in brows) * BEAM_HP,
          "старая по-сторонняя HP-модель прошла новый предикат", errs)
    # 4. старая граница cull проваливает новый предикат
    check(old_bullet_cull_bound() < GC["playerMaximumCenterX"] + GC["blasterBulletSize"][0],
          "старая граница cull прошла новый предикат", errs)
    # 4b. (review R1-1) rect-сверка обязана уметь краснеть: мутации стороны
    # exec/base в синтетике ловятся сравнением. Victim-карта: ≥2 различных rect.
    art_r = harness()["artifact"]
    victim = None
    for mp in corpus():
        entry = art_r.get("rects", {}).get(mp["file"])
        if entry and len(set(entry[1])) > 1:
            victim = (mp, list(entry[1]))
            break
    if victim is None:
        errs.append("нет ни одной карты с ≥2 rect — мутационный контроль геометрии декоративен")
    else:
        mp_r, exec_r = victim
        base_r = base_build_collision_rects(mp_r)
        new_r = SurfaceMirror(mp_r).query_collision_rects()
        check(bool(base_r) and base_r == new_r == exec_r,
              f"victim {mp_r['file']}: чистое сравнение уже разошлось — контроль бессмысленнен", errs)
        mut_y = [tuple(v + (0, 7.5, 0, 0)) if i == 0 else v for i, v in enumerate(exec_r)]
        mut_order = list(reversed(exec_r))
        mut_base = [tuple(v + (16, 0, 0, 0)) if i == 0 else v for i, v in enumerate(base_r)]
        check(base_r != mut_y, "мутант +7.5 (случай ревьюера) не красит сверку — сравнение тавтология", errs)
        check(base_r != mut_order, "перестановка rect не красит сверку — порядок не проверяется", errs)
        check(new_r != mut_base, "сдвиг x старшего порта не красит сверку", errs)
    # 5. метр обязан падать на битых данных (garbage fixture)
    good = next(iter((ROOT / "Exolon/Resources").glob("*.tmx"))).read_bytes()
    broken = good[: len(good) // 2]
    try:
        ET.fromstring(broken.decode("utf-8", "replace"))
        errs.append("усечённый XML разобрался без ошибки — метр слепой")
    except ET.ParseError:
        pass
    # усечение base64 Collision-данных: продукт кидает invalidLayerData, зеркало обязано
    # отличать неполный слой (короткий gid-вектор != W*H -> клетки не строим)
    mp = v3.load_map(next(iter(sorted((ROOT / "Exolon/Resources").glob("*.tmx")))))
    root = ET.fromstring(mp["text"])
    data = next(d for lay in root.iter("layer") if (lay.get("name") or "") == "Collision"
                for d in [lay.find("data")])
    raw = base64.b64decode((data.text or "").strip())
    check(len(raw) % 4 == 0 and len(raw) // 4 == mp["W"] * mp["H"], "полный слой не сходится с W*H", errs)
    short = raw[: len(raw) - 4]
    check(len(struct.unpack("<%dI" % (len(short) // 4), short)) != mp["W"] * mp["H"],
          "урезанный слой не отличается от полного", errs)
    check("data.count >= expectedCount * 4" in LOADER_SRC,
          "продуктовый guard усечённого слоя исчез — loader больше не падает громко", errs)
    # 6. живые/артефактные контроли harness
    h = harness()
    if h["ran"]:
        check(h["live_matches_artifact"], "вывод живого harness не совпал с закоммиченным артефактом", errs)
    elif h.get("attempted"):
        errs.append(f"живой harness падал: {h['error']} — цифры сверяются только по закоммиченному артефакту, "
                    "продуктовое исполнение не подтверждено")
    else:
        print("  (harness не перезапускался: swiftc недоступен или --artifact-only; сверен закоммиченный артефакт)")
    log_text = ""
    if h.get("ran") and _harness_stderr_scratch[0]:
        log_text = pathlib.Path(_harness_stderr_scratch[0]).read_text(encoding="utf-8")
    elif RUN_LOG.exists():
        log_text = read(RUN_LOG)
    if log_text:
        check("ровно 1 строка импорта" in log_text, "run.sh не подтвердил байт-дельту копии", errs)
        check("без стаба не собирается" in log_text, "run.sh не подтвердил негативный контроль без стаба", errs)
    else:
        errs.append("нет ни живого stderr, ни last-run.txt — контроль сборки harness не зафиксирован")
    print(f"  AC-005: controls flip: spawn(old nonzero {old_nonzero}, unbounded-rejected 91/50, "
          f"preference-fixture 80!=64), pistons(old lethal 6/46), "
          f"beam(old 500 != 250), cull(old 528<594, grenade 536<548), broken-TMX падает, harness-контроли на месте")
    return errs


def no_magic_offsets() -> list[str]:
    errs: list[str] = []
    # 1. TMX не редактированы: git-blob sha1 == манифест base-коммита 295690b
    manifest = json.loads(read(TMX_MANIFEST))
    check(manifest["generated_from_commit"].startswith("295690b"),
          "манифест хешей не с base-коммита wave B", errs)
    files = manifest["files"]
    check(len(files) == 125, "в манифесте не 125 файлов", errs)
    ok = 0
    for name, oid in files.items():
        p = ROOT / "Exolon/Resources" / name
        if not p.exists() or git_blob_sha1(p) != oid:
            errs.append(f"TMX изменён/отсутствует vs base commit: {name}")
        else:
            ok += 1
    check(ok == EXPECTED["tmx_blobs_match_base_commit"], "не все TMX совпали base-коммиту", errs)
    # 2. ни per-map таблиц, ни магических ±16 в новом коде (комментарии не в счёт)
    seams = {
        "loader.resolvedPlayerBottom": swift_block(LOADER_SRC, "func resolvedPlayerBottom(using"),
        "loader.boundedSurfaceY": swift_block(LOADER_SRC, "func boundedSurfaceY("),
        "loader.surfaceTops": swift_block(LOADER_SRC, "func surfaceTops("),
        "loader.pistonGroundY": swift_block(LOADER_SRC, "func pistonGroundY("),
        "loader.groundY(atOrBelow)": swift_block(LOADER_SRC, "func groundY(x0: CGFloat, x1: CGFloat, atOrBelow"),
        "loader.beamGrouping": swift_block(LOADER_SRC, "static func groups(for boxes"),
        "bullet.update": swift_block(BULLET_SRC, "func update(dt:"),
        "grenade.update-x": swift_block(read(GRENADE), "func update(dt:"),
        "runtime.piston": swift_case(RUNTIME_SRC, 'case "piston"'),
        "runtime.beam-fields": swift_block(RUNTIME_SRC, "for group in TMXBeamGrouping.groups"),
    }
    for label, block in seams.items():
        # пустой блок = проверка не может краснеть (AC-005: «check that cannot
        # fail is itself a failure») — фиксируем исчезновение шва отдельно
        if not block.strip():
            errs.append(f"FORBID-001 {label}: шов исчез из исходника — скан выродился")
            continue
        code = strip_comments(block)
        for pat, why in ((r"\b16\b", "литерал 16"),
                         (r"\b528\b", "старая граница 528"), (r"\b544\b", "литерал clamp 544"),
                         (r"\b560\b", "литерал 560"), (r"L\d{2}S\d{2}", "per-map таблица")):
            if re.search(pat, code):
                errs.append(f"FORBID-001 {label}: {why} в коде: {re.findall(pat, code)[:3]}")
    for fname, src in (("TMXMapLoader.swift", LOADER_SRC), ("GameConstants.swift", read(GAME_CONSTANTS))):
        if re.search(r"L\d{2}S\d{2}", strip_comments(src)):
            errs.append(f"FORBID-001 {fname}: имя карты в коде (per-map логика)")
    # 2b. (audit §Q2) ADDED-строки ВСЕХ изменённых продуктовых файлов относительно
    # base-коммита: магические смещения/границы/per-map имена. Существующие
    # per-map таблицы TMXLevelRuntime (:450 gate-спрайт, :530-535 backdrop) —
    # baseline'ятся самой diff-семантикой (это не добавленные строки) и в этой
    # волне не трогаются; если волной A/C/D они сдвинутся — они обязаны будут
    # пройти этот же скан как добавленные.
    added = git_added_lines(wave_base())
    if added is None:
        errs.append("git diff <wave base> недоступен — added-lines скан не выполнен (fail-closed)")
    else:
        n_files = len(set(p for p, _ in added))
        n_code = 0
        for path, line in added:
            code = strip_comments(line)
            if not code.strip():
                continue
            n_code += 1
            for pat, why in ((r"[-+] ?\b16\b", "±16 смещение"),
                             (r"\b528\b|\b544\b|\b560\b", "закреплённая граница вместо вывода из констант"),
                             (r"L\d{2}S\d{2}", "per-map имя")):
                if re.search(pat, code):
                    errs.append(f"FORBID-001 added {path}: {why}: {code.strip()[:90]}")
        check(n_files >= 7 and n_code >= 150,
              f"added-lines скан странно пуст: файлов={n_files} строк={n_code}", errs)
        print(f"  added-lines: {n_code} стронок кода в {n_files} изменённых продуктовых файлах")
    # 3. закреплённая формула старой границы существует только в комментариях/артефактах
    check(not re.search(r"logicalSize\.width \+ 16(?!\s*,\s*y)", strip_comments(BULLET_SRC)),
          "BlasterBullet всё ещё режет x>528 по формуле", errs)
    print(f"  FORBID-001: TMX байт-в-байт base-коммита ({ok}/125), "
          f"в {len(seams)} новых швах нет ±16/528/544/560 и per-map имён")
    return errs


def single_surface_query() -> list[str]:
    errs: list[str] = []
    # ровно одно определение запроса поверхности — в TMXSurfaceQuery
    defs: list[str] = []
    for p in ROOT.glob("Exolon/**/*.swift"):
        src = read(p)
        for m in re.finditer(r"func (ground\w*|boundedSurfaceY|surfaceTops)\(", src):
            if "struct TMXSurfaceQuery" not in src[:m.start()]:
                defs.append(f"{p.name}:{m.group(0)}")
    check(not defs, f"появились отдельные определения поверхности: {defs}", errs)
    check(len(re.findall(r"struct TMXSurfaceQuery", LOADER_SRC)) == 1,
          "TMXSurfaceQuery определён не один раз", errs)
    check(len(re.findall(r"var surfaceQuery", LOADER_SRC)) == 1, "surfaceQuery определяется дважды", errs)
    # интерпретация Collision-слоя едина: отбор слоя и формула топа встречаются по одному разу
    solid_sites = [p.name for p in ROOT.glob("Exolon/**/*.swift")
                   if 'lowercased() == "collision"' in read(p)]
    check(solid_sites == ["TMXMapLoader.swift"], f"Collision-слой отбирается в {solid_sites}", errs)
    check(len(re.findall(r"pixelHeight - CGFloat\(row", strip_code_comments_keep(LOADER_SRC))) == 1,
          "формула верха клетки продублирована", errs)
    # renderer и runtime — потребители, а не соавторы земли; запрос строится
    # ровно один раз на загрузку и передаётся в renderer (audit §Q6.8)
    check("collisionRects = surfaceQuery.collisionRects" in RENDERER_SRC
          and "init(map: TMXMapData, surfaceQuery: TMXSurfaceQuery)" in RENDERER_SRC,
          "renderer не получает общий запрос извне (самостоятельная сборка = второй проход)", errs)
    check("buildCollisionRects" not in RENDERER_SRC and "buildCollisionRects" not in RUNTIME_SRC,
          "старая ad-hoc сборка прямоугольников вернулась", errs)
    check("private static func buildCollisionRects" not in "".join(
        read(p) for p in ROOT.glob("Exolon/**/*.swift")), "дублирующий merge колонзийных рядов в продукте", errs)
    check(RUNTIME_SRC.count("loadedMap.surfaceQuery") == 1,
          "surfaceQuery строится в runtime больше одного раза на загрузку", errs)
    check("TMXTileMapRenderer(map: loadedMap, surfaceQuery: query)" in RUNTIME_SRC,
          "renderer не подключён к общему экземпляру запроса", errs)
    check("resolvedPlayerBottom(using: query)" in RUNTIME_SRC, "спавн не через общий запрос", errs)
    check("surfaceQuery.pistonGroundY" in RUNTIME_SRC, "поршни не через общий запрос", errs)
    check("query.fallbackPlaneY" in RUNTIME_SRC, "fallback-пол не из общего запроса", errs)
    check("min(resolvedGroundY, rect.maxY)" not in RUNTIME_SRC,
          "старая ad-hoc мин-площадка по renderer.collisionRects вернулась", errs)
    consumers = 0
    for src in (RUNTIME_SRC, RENDERER_SRC):
        consumers += src.count("surfaceQuery") + src.count("using: query")
    check(consumers >= 4, f"потребителей запроса {consumers} (<4: spawn, plane, piston, renderer)", errs)
    print(f"  FORBID-002: единственное определение поверхности — TMXSurfaceQuery; "
          f"потребители: spawn, piston, renderer-прямоугольники, fallback-пол")
    return errs


def pinned_geometry_unchanged() -> list[str]:
    errs: list[str] = []
    gc = read(GAME_CONSTANTS)
    check("static let logicalSize = CGSize(width: 512, height: 384)" in gc,
          "логическое поле 512x384 поехало", errs)
    check("static let defaultGroundY: CGFloat = 96" in gc, "defaultGroundY поехал", errs)
    check(GC["logicalSize"] == (512.0, 384.0), "разбор logicalSize не сошёлся", errs)
    check(SCENE_SRC.count("player.position.x > 510") == 1, "триггер перехода экрана x>510 не единственен", errs)
    # мирBottomLeft: default-ветка без height (та же стража, что у p1-1 probe), height — только tiledRect
    default_line = next((ln for ln in LOADER_SRC.splitlines()
                         if "return CGPoint(x: object.x, y: pixelHeight - object.y" in ln
                         and "- object.height" not in ln), "")
    height_line = next((ln for ln in LOADER_SRC.splitlines()
                        if "pixelHeight - object.y - object.height" in ln), "")
    check(bool(default_line) and bool(height_line),
          "ветки worldBottomLeft (default без height / tiledRect с height) разъехались", errs)
    # константы пули/поршня/игрока закреплены (значения, не литералы в местах)
    check(GC["blasterBulletSize"] == (16.0, 2.0), "размер пули поехал", errs)
    check(GC["pistonNodeSize"] == (48.0, 64.0), "размер поршня поехал", errs)
    check(GC["pistonHitXInset"] == 3 and GC["pistonHitWidth"] == 42 and GC["pistonTravel"] == 64.0,
          "hitbox-геометрия поршня поехала", errs)
    check(GC["playerMinimumCenterX"] == 24.0 and GC["playerMaximumCenterX"] == 544.0,
          "clamp игрока поехал", errs)
    check(GC["blasterCullMinimumX"] == -50.0, "левая граница cull поехала (-(34+16))", errs)
    # rect-геометрия renderer'а байтово-стабильна — ТРИ независимых реализации:
    # (a) base-порт buildCollisionRects прямо по gid'ам (git show 295690b,
    #     якоря строкам ниже — чтобы порт не разъехался с бейс-блобом);
    # (b) python-порт НОВОГО TMXSurfaceQuery.collisionRects (клетки, свой обход);
    # (c) ИСПОЛНЕННЫЙ продуктовый collisionRects из артефакта harness (RECTS-строки,
    #     %.1f — мутирующая продуктовой формулой красная именно здесь).
    # Сравнение чувствительно к числу, порядку и координатам; self-vs-self здесь
    # невозможно: (a) читает gids, (b)/(c) — клетки/Swift.
    base_renderer = git_show_base("Exolon/GameCore/Levels/TMXTileMapRenderer.swift")
    if base_renderer is None:
        errs.append("git show 295690b недоступен — base-порт не привязан к бейс-блобу")
    else:
        anchors = ("private static func buildCollisionRects(map: TMXMapData) -> [CGRect]",
                   "let gid = collision.gids[row * collision.width + column] & 0x1FFF_FFFF",
                   "let y = map.pixelHeight - CGFloat((row + 1) * map.tileHeight)",
                   "width: CGFloat((column - start) * map.tileWidth)")
        for a in anchors:
            check(a in base_renderer, f"якорь старого merge не найден в бейс-блобе: {a[:40]}…", errs)
    art = harness()["artifact"]
    same = 0
    total = 0
    for mp in corpus():
        mirror = SurfaceMirror(mp)
        base_rects = base_build_collision_rects(mp)
        new_rects = mirror.query_collision_rects()
        exec_entry = art.get("rects", {}).get(mp["file"])
        if exec_entry is None:
            errs.append(f"{mp['file']}: в артефакте нет RECTS-строки — исполненная геометрия не сверена")
            continue
        exec_count, exec_rects = exec_entry
        if not (base_rects == new_rects == exec_rects) or exec_count != len(base_rects):
            errs.append(f"{mp['file']}: rect-геометрия рассинхронизирована "
                        f"(base={len(base_rects)} new={len(new_rects)} exec={exec_count}/{len(exec_rects)})")
        else:
            same += 1
            total += len(base_rects)
    check(same == EXPECTED["renderer_rects_identical_all_maps"],
          f"rects совпали не на всех картах: {same}", errs)
    check(total == EXPECTED["renderer_rects_total"], f"суммарный rect-объём {total} != 1437", errs)
    print(f"  INV-002: 512x384, x>510 (1 место), clamp 24..544, defaultGroundY 96; "
          f"rects base-порт==new-порт==исполненный на {same}/125 (всего {total} rect'ов), "
          f"worldBottomLeft-ветки на месте")
    return errs


# ————————————————————— мелкие утилиты —————————————————————


def swift_block(src: str, start_marker: str) -> str:
    i = src.find(start_marker)
    if i < 0:
        return ""
    depth = 0
    started = False
    out = []
    for ch in src[i:]:
        out.append(ch)
        if ch == "{":
            depth += 1
            started = True
        elif ch == "}":
            depth -= 1
            if started and depth == 0:
                break
    return "".join(out)


def swift_case(src: str, marker: str) -> str:
    i = src.find(marker)
    if i < 0:
        return ""
    j = re.search(r"case \"", src[i + len(marker):])
    return src[i: i + len(marker) + (j.start() if j else 4000)]


def strip_comments(block: str) -> str:
    block = re.sub(r"///?.*", "", block)
    block = re.sub(r"/\*.*?\*/", "", block, flags=re.S)
    return block


def strip_code_comments_keep(src: str) -> str:
    return re.sub(r"//.*", "", src)


def check(cond: object, msg: str, errs: list[str]) -> None:
    if not cond:
        errs.append(msg)


# ————————————————————— таблицы дельт (SIG-001) —————————————————————


def write_deltas() -> None:
    srows, prows, brows = spawn_rows(), piston_rows(), beam_rows()
    lines = [
        "# Delta-таблицы wave B (SIG-001) — генерирует wave_b_check.py, не править руками",
        "",
        "## P1-2 spawn (marker -> old rest -> new feet)",
        "",
        "| карта | zone | marker feet | old rest (37/59/29) | new feet | Δ vs marker | Δ vs old | источник |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in srows:
        if r["kept"]:
            src = "KEPT — нет поверхности в окне ±16px"
        else:
            src = f"{r['pool_type']}-пул, окно: {';'.join(f'{t:.0f}' for t in r['window'])}"
        lines.append(f"| {r['map'][:-4]} | {r['zone']:03d} | {r['marker']:.0f} | {r['marker'] + r['delta_old']:.0f} "
                     f"| {r['feet']:.0f} | {r['delta_marker']:+.0f} | {r['feet'] - (r['marker'] + r['delta_old']):+.0f} | {src} |")
    buried_new = sum(1 for r in srows if r["buried_new"])
    buried_base = sum(1 for r in srows if r["buried_base"])
    pools = Counter(r["pool_type"] for r in srows)
    lines += ["",
              "### Bounded-порог AC-001 (amendment 2, 2026-09-24)",
              "",
              "- MAX movement любого спавна = 16 px (±один тайл); проверено на 125/125;",
              f"- поверхности в окне найдены на {125 - pools['kept']}/125 (delta vs surface = 0); "
              f"распределение preference-выбора: clear {pools['clear']}, dirty-nearest {pools['dirty']}, "
              f"kept {pools['kept']};",
              f"- NO-WORSE-THAN-BASE: спавнов с телом в грунте было на base {buried_base}, "
              f"стало {buried_new} (меньше на {buried_base - buried_new}); обе цифры считаются одним "
              f"и тем же predicate от общих клеток;",
              "- на этом корпусе nearest-без-preference дал бы ровно те же 125 выборов и те же "
              f"{buried_new} buried — тем не менее preference обязателен по правилу и проверяется "
              "синтетической фикстурой в controls_flip (ближайший топ в грунте, чистый дальше → "
              "выбран чистый);",
              f"- ОТКЛОНЁННОЕ безграничное nearest-body-clear правило сдвинуло бы "
              f"{sum(1 for r in srows if r['rejected_feet'] != r['marker'])}/125 спавнов, "
              f"из них {sum(1 for r in srows if abs(r['rejected_feet'] - r['marker']) > 16)} — за тайл "
              f"(45×+32 px + 5×112–208 px); его дельта-vs-маркер гистограмма: "
              f"{ {str(int(k)): v for k, v in sorted(Counter(r['rejected_feet'] - r['marker'] for r in srows).items(), key=lambda x: float(x[0]))} };",
              "- РАСКРЫТИЕ (carried-Y): runtime использует resolved spawn Y только на stage-start "
              "входах, старте приложения и респауне после смерти (GameScene.swift:638-646 несёт "
              "y предыдущей зоны на обычных переходах) — примерно 5-6 entries за проход.",
              "",
              "### Карты, оставленные БЕЗ смещения (нет Collision-поверхности в окне ±16px)",
              "",
              "| карта | zone | marker x | marker feet | plane (info) | причина |",
              "|---|---:|---:|---:|---:|---|"]
    for r in srows:
        if not r["kept"]:
            continue
        vmap = next(mp for mp in corpus() if mp["file"] == r["map"])
        vv = next(o for o in vmap["objects"] if o["name"] == "vitorc")
        lines.append(f"| {r['map'][:-4]} | {r['zone']:03d} | {vv['x']:.0f} | {r['marker']:.0f} | {r['plane']:.0f} "
                     f"| нет ни одного Collision-топа в foot-спане в [marker−16, marker+16] |")
    lines += ["",
              "## P1-1 pistons (старый якорь строки маркера -> новый от поверхности)", "",
              "| карта | x | старый якорь | новый якорь | walkable f | сдвиг | летален старым | летален новым | источник |",
              "|---|---:|---:|---:|---:|---:|---|---|---|"]
    for r in prows:
        lines.append(f"| {r['map'][:-4]} | {r['x']:.0f} | {r['anchor']:.0f} | {r['ground']:.0f} | {r['walkable']:.0f} "
                     f"| {r['ground'] - r['anchor']:+.0f} | {'да' if r['old_lethal'] else 'нет'} "
                     f"| {'да' if r['new_lethal'] else 'НЕТ'} | {'plane-fallback' if r['from_plane'] else 'span'} |")
    lines += ["", "## P1-5 beams (стороны -> поля -> суммарные HP; контроль старой модели)", "",
              "| карта | маркеров-сторон | полей | HP новых (25/поле) | HP старых (25/сторона) |",
              "|---|---:|---:|---:|---:|"]
    for r in brows:
        lines.append(f"| {r['map'][:-4]} | {r['markers']} | {r['fields']} | {r['fields'] * BEAM_HP} | {r['markers'] * BEAM_HP} |")
    lines += ["", "## P1-3 / AC-004 (amended): cull-границы снарядов", "",
              f"- blaster, старая граница: `logicalSize.width + 16` = {old_bullet_cull_bound():.0f} "
              f"< clamp+width {GC['playerMaximumCenterX'] + GC['blasterBulletSize'][0]:.0f} "
              f"< clamp+muzzle {GC['playerMaximumCenterX'] + GC['blasterMuzzleOffsetX']:.0f} "
              f"(выстрел от x=544 рождался мёртвым);",
              f"- blaster, новая граница: `playerMaximumCenterX + blasterMuzzleOffsetX + "
              f"blasterBulletSize.width` = {GC['blasterCullMaximumX']:.0f} "
              f"(лево: `-(muzzle+width)` = {GC['blasterCullMinimumX']:.0f}); "
              f"покрытие: правый край геометрии всех 125 карт = {EXPECTED['max_solid_right_edge']};",
              f"- grenade, старая граница: inline `logicalSize.width + 24` = 536 "
              f"< origin-максимум {GC['playerMaximumCenterX'] + GC['grenadeThrowOffsetX']:.0f} — "
              f"граната умирала при рождении у правой стены;",
              f"- grenade, новая граница: та же формула (clamp + throw + width) = "
              f"{GC['grenadeCullMaximumX']:.0f} (лево {GC['grenadeCullMinimumX']:.0f}); "
              f"inline-литералов x в Grenade.swift не осталось;",
              f"- 528-литералы в leftover-коде — позиции старта (BubbleSpawner x=528±32, "
              f"HomingMissile logicalSize.width+16), не cull — запинено в bullet_cull_bounds;",
              f"- карт с collision правее x=512: {EXPECTED['maps_solid_right_of_512']}",
              f"- переход экрана `x > {EXPECTED['screen_exit_trigger']}` не тронут (INV-002)", ""]
    write_if_changed(DELTAS, "\n".join(lines))


# ————————————————————— main —————————————————————

CHECKS = (
    zone_index_formula,
    spawn_ground_all_maps,
    piston_anchor_all_pistons,
    beam_shared_hp_all_maps,
    bullet_cull_bounds,
    controls_flip,
    no_magic_offsets,
    single_surface_query,
    pinned_geometry_unchanged,
)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", help="только для совместимости с probe-стилем; путь выводится из файла")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--artifact-only", action="store_true", help="не пересобирать Swift-harness")
    args = ap.parse_args()
    sys.wave_b_artifact_only = args.artifact_only
    t0 = time.time()
    failures: dict[str, list[str]] = {}
    for fn in CHECKS:
        errs = fn()
        failures[fn.__name__] = errs
        mark = "PASS" if not errs else "FAIL"
        print(f"{mark:4} {fn.__name__}")
        for e in errs:
            print(f"       - {e}")
    write_deltas()
    elapsed = time.time() - t0
    ok = not any(failures.values())
    h = harness()
    if args.json:
        print(json.dumps({"ok": ok, "tool_absent": not h["ran"] and not args.artifact_only,
                          "failures": failures, "expected": EXPECTED}, ensure_ascii=False, indent=2))
    if ok and not h["ran"] and not args.artifact_only:
        # F-2 (review-test): нет swiftc без явного --artifact-only = молчаливо-зелёного
        # вердикта не бывает: продуктовое исполнение не переподтверждено.
        print("RESULT: TOOL_ABSENT (swiftc недоступен; продуктовые сверки опираются лишь "
              "на закоммиченный артефакт; для оффлайн-режима нужен --artifact-only)")
        return 3
    print(f"delta-таблицы: {DELTAS.relative_to(ROOT)} | артефакт Swift: "
          f"{'живой' if h['ran'] else 'коммиченный (--artifact-only)'} (совпал: {h.get('live_matches_artifact', 'n/a')})")
    print(f"elapsed={elapsed:.1f}s (бюджет 60s: {'ok' if elapsed <= 60 else 'ПРЕВЫШЕН'})")
    if elapsed > 60:
        ok = False
    print("RESULT:", "ALL_WAVE_B_CHECKS_MATCH_SPEC" if ok else "MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
