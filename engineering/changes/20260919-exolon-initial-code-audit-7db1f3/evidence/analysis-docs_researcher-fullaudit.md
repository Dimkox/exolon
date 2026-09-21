# Docs researcher — полный аудит документации против дерева (fullaudit)

**Route:** `7db1f3f0b126` · **intent:** review · **write_agent:** none · **я read-only, кроме этого файла**
**HEAD:** `b8aee429e2565aa3824759639060787a7b36ae20` (`codex/factory-updated-20260920`)
**base_commit роута:** `403eb1322d645154307ce11bf91be89e2082e1dd`

```
$ cd <repo> && git log --oneline -3 && git rev-parse HEAD
b8aee42 (HEAD -> codex/factory-updated-20260920, origin/codex/update-factory-20260920) chore: update installed factory to upstream 9007895
403eb13 (origin/main, codex/update-factory-20260920, codex/factory-initial-audit) Import Exolon Step 9 and factory 2.0.18 at 26a0d3d
b8aee429e2565aa3824759639060787a7b36ae20
```

Проверено, что интересующий меня продукт между base роута и HEAD не менялся — все мои измерения
справедливы и для `base_fingerprint` роута:

```
$ git diff --stat 403eb13..b8aee42 -- Exolon Exolon.xcodeproj README.md LEVEL_COMPILER_AUDIT.md ORIGINAL_MECHANICS.md
(пусто)
$ git diff --name-only 403eb13..b8aee42 | sed 's|/.*||' | sort | uniq -c
      1 decisions.md
     20 engineering
      3 factory
```

Это отдельный файл, а НЕ правка `analysis-docs_researcher.md`:

```
$ ls -la engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/analysis-docs_researcher-fullaudit.md
ls: cannot access '...analysis-docs_researcher-fullaudit.md': No such file or directory   (до записи этого отчёта)
```

---

## 0. Методика и границы измерений

Инвентарь (stdlib `python3`, `git`, `find`, `grep`; ничего в дерево не писались, скрипты в `/tmp/docsaudit/`):

```
$ find Exolon -name '*.swift' | wc -l            → 18
$ ls Exolon/Resources/*.tmx | wc -l              → 125
$ ls Exolon/Resources | wc -l                    → 282
$ find Exolon -type f | sed 's|/[^/]*$||' | sort | uniq -c | sort -rn
     282 Exolon/Resources
       5 Exolon/GameCore
       3 Exolon/Platform/macOS
       3 Exolon/GameCore/Levels
       2 Exolon/GameCore/Weapons
       2 Exolon/GameCore/Player
       1 Exolon/GameCore/Objects
       1 Exolon/GameCore/Effects
       1 Exolon
```

**Что реально лежит в TMX.** У 680 объектов ровно 20 разных имён; провенанс несёт в себе
свойство `sourceBlock` (25 значений), а **координаты исходника** (`sourceX`+`sourceY`) — только 145 объектов:

```
$ python3 - <<'PY'   # полный скрипт в /tmp/docsaudit/names.py
import xml.etree.ElementTree as ET, glob, collections
names=collections.Counter(); total=0
for f in sorted(glob.glob('Exolon/Resources/*.tmx')):
    for o in ET.parse(f).getroot().iter('object'):
        total+=1; names[o.get('name')]+=1
print(total, len(names)); [print(v,k) for k,v in names.most_common()]
PY
TOTAL OBJECTS: 680 | DISTINCT NAMES: 20
  127 source_marker   125 vitorc   70 teleport   53 mine   48 ammo_pack   46 piston
   38 grenade_pack    37 turret     31 bubble_creator  29 rocket  22 incubator
   19 double_launcher 12 radar       7 ship       6 gate    3 light_ceiling
    3 light_floor      2 ship_fire   1 capsule     1 cocoon

$ python3 - <<'PY'   # /tmp/docsaudit/blocks.py
... гистограмма property-ключей и sourceBlock ...
== property key combos ==
  341 ('sourceBlock',)
  165 ()
  145 ('sourceBlock', 'sourceX', 'sourceY')
   28 ('behavior', 'delay', 'sourceBlock')
    1 ('coordinateMode', 'sourceBlock')
TOTAL sourceBlock objects: 515
```

**Граница, которую честно надо объявить.** Сопоставить документы с данными **полностью** невозможно:
`LEVEL_COMPILER_AUDIT.md` — это 970 кортежей `x:y:type` на 32-колоночной сетке оригинала (field1 ∈ [0,31],
измерено ниже), а TMX — 680 объектов с пиксельными координатами ремейка. Прямое, **не выводимое**,
сопоставление даёт только подмножество с явными `sourceX/sourceY` (145 объектов, 12 семейств `sourceBlock`).
Все выводы про «тип ↔ блок» ниже опираются именно на точное совпадение координат, а не на догадку.

---

## 1. README.md: обещание ↔ код/данные

| № | Цитата `README.md` | Evidence (измерено) | Вердикт |
|---|---|---|---|
| L3 | «the **first runnable** archive» | Нет ни одной сборки/артефакта; `find Exolon.xcodeproj -type f` → ровно `project.pbxproj`, схем нет (§3); тестов Swift нет (§4.4). «Runnable» на этом хосте не проверяемо | **НЕ ВЕРИФИЦИРУЕМО локально** |
| L6 | «keeps the existing **125-zone** project and **original-visual pipeline**» | 125 TMX ✓; `includedLevels` = 125 ✓; `python3`-генерация `L%02dS%02d` 1..5 × 1..25 → 125, расхождений с диском нет. Но `imagelayer` с оригинальным артом есть не везде: **5 экранов без него** | **ЧАСТИЧНО**: зоны ✓, визуал ✗ |
| — | — | `screens WITHOUT imagelayer: 5 ['L01S01','L01S02','L01S03','L01S04','L01S07']` = **зоны 000, 001, 002, 003, 006**; `imagelayer name → files: {'Original Scenery': 2, 'Original Static Scenery': 118}`; `zone_*_original.png on disk: 118`, `NOT referenced: []` | первые 7 зон — самые первые играемые экраны — без original-подложки |
| L7 | «**Zone 009** object placement is rebuilt from the reference TMX coordinates rather than the old source-marker approximation» | `Exolon/Resources/L01S10.tmx` (map property `zoneNumber=009`): объектов `source_marker` — **0**; 6 не-`vitorc` объектов стоят пиксельными координатами и несут `sourceBlock` без `sourceX/Y` | **ПОДТВЕРЖДЕНО** (структурно) |
| L8 | «Zone 009 pistons now use **x=64/192, y=320** (not y=384)» | `piston x=192 y=320` и `piston x=64 y=320` (дамп L01S10 ниже) | **ПОДТВЕРЖДЕНО** |
| L9 | «changing room is a real **32x80** rectangle at **x=368, y=176** in Tiled coordinates» | `capsule x=368 y=176 w=32 h=80 {'coordinateMode': 'tiledRect', 'sourceBlock': 'blk_changing_room'}` | **ПОДТВЕРЖДЕНО** |
| L10 | «**rectangle-object coordinate conversion is explicit**, so tile objects and rectangles are no longer conflated» | `TMXMapLoader.swift:77` `if object.properties["coordinateMode"] == "tiledRect"`. А измерение охвата: `grep -ln "coordinateMode" Exolon/Resources/*.tmx` → **`L01S10.tmx` — 1 файл из 125**; объектов с `width>0 and height>0` — **360**, из них режим явно объявлен у **1** | **ВЕРНО, НО МАРКИРОВАНО ОДНО ЭКРАННОМ**: «явный пересчёт» реализован для 1 из 360 прямоугольных объектов |
| L11 | «pistons are **lethal when exposed** (unless test Invulnerability is ON)» | `LevelObstacles.swift:341-345` `hitbox` → `.zero`, если `visibleHeight <= 0`; `GameScene.swift:556-566` шлюз `box.width > 0` (`:559`); `GameScene.swift:602` `guard !testInvulnerabilityEnabled else { return }` | **ПОДТВЕРЖДЕНО** |
| L12 | «pressing **UP** inside the changing room **toggles** Exoskeleton mode» | `GameScene.swift:233-238` (`jumpJustPressed` ∩ `currentLevel.changingRooms`) → `player.toggleExoskeleton()`; `Player.swift:243-246` `hasExoskeleton.toggle()`, `guard !isDying` | **ПОДТВЕРЖДЕНО для клавиатуры и D-pad; НАРУШЕНО для стика** — `GamepadInput.swift:64-72`: стик вверх ставит только `.menuUp`, никогда `.jump` ⇒ «pressing UP» на геймпаде кабину не включает |
| L13 | «Exoskeleton fires a **double blaster** and **protects against mines/pistons**» | двойной выстрел `GameScene.swift:346-350`; неуязвимость к минам `GameScene.swift:545-546` (`if player.hasExoskeleton { continue }`), к поршням `:557` | **ПОДТВЕРЖДЕНО** |
| L14 | «**Restart/new session resets Exoskeleton**» | `GameScene.swift:963` `player.setExoskeleton(false)` в `restartFromBeginning`; `respawn()` (`Player.swift:232-240`) флаг **не** трогает ⇒ переживает смерть ✓ как и требует `ORIGINAL_MECHANICS.md:115` | **ПОДТВЕРЖДЕНО** (и см. §6.3 — это же нарушает другой пункт документа) |
| L15 | «every application launch still starts from **Zone 000**; **High Score persists**» | `GameScene.swift:687-692` при старте `persistence.clearCheckpoint(); currentLevelName = "L01S01"`; `zoneNumber(for:)` `:996` `L01S01→0`; `:961` `gameState.highScore = persistence.loadHighScore()`, `persistence.saveHighScore` `:665` | **ПОДТВЕРЖДЕНО** |
| L21 | «changing-room artwork is now **pass-through** scenery … no longer hidden behind compiled static collision» | `TMXLevelRuntime.swift:291-306` (`capsule`) и `:371-379` (`source_marker/blk_changing_room`) наполняют `changingRoomCollisionExclusions` | **ПОДТВЕРЖДЕНО** |
| L22 | «The collision exclusion is applied by **object type**, so it affects **every** changing-room screen, not only Zone 009» | измеряемое число экранов с кабиной: `blk_changing_room` = **5** — `L01S10/capsule, L02S10, L03S11, L04S16, L05S10`; обе ветки по типу объекта ✓ | **ВЕРНО по охвату, НО геометрия разная**: `capsule` → `width: max(96, w+64)` (`TMXLevelRuntime.swift:304`), `source_marker` → `width: w+32` (`:377`). Один и тот же объект на 4 из 5 экранов получает другой вырез |
| L23 | «UP inside a changing room/teleport is **consumed** … cannot become an accidental jump on the following fixed step» | `GameScene.swift:231,238,244` флаг `consumedUpInteraction`, `:251-253` `player.consumeContextualJumpPress()`, `Player.swift:256-258` (`jumpWasPressed = true`), и `GameScene.swift:255-258` конструируется `InputSnapshot(jump: false …)` | **ПОДТВЕРЖДЕНО** |
| — | «controls list» — **в README его нет** | `grep -rn "Option\|F1\|D-pad\|gamepad\|Gamepad" README.md ORIGINAL_MECHANICS.md LEVEL_COMPILER_AUDIT.md factory/README.md AGENTS.md decisions.md` → **пусто**. Фактическая карта только в коде: `GameView.swift:46-68` (стрелки, Space=fire, **Option= grenade**, P, **F1**=hitboxes) и `GamepadInput.swift:44-90` | **НОВЫЙ РАЗРЫВ**: `Option` (граната) и `F1` (отладка хитбоксов) не описаны **ни в одном .md** дерева; в README нет ни одной строки про управление |
| — | версия | В README **нет строки версии**: `grep -nE "(^\|[^a-z])[Vv][Ee][Rr][Ss][Ii][Oo][Nn]([^a-z]\|$)" README.md` → **exit=1** (наивный `grep -n "version"` бьёт только в слово `conversion` на L10). Фактические версии рассинхронизированы: 0.5 ↔ 0.3 (§3.1) | противоречит `AGENTS.md:26` (§5) |

---

## 2. `LEVEL_COMPILER_AUDIT.md` ↔ 125 TMX

### 2.1 Внутренняя непротиворечивость документа (контроль №1 — обязан был сойтись)

```
$ python3 - <<'PY'   # /tmp/docsaudit/docaudit.py
hdr=re.search(r'Action counts: ([^\n]+)', open('LEVEL_COMPILER_AUDIT.md').read()).group(1)
declared={int(k):int(v) for k,v in (p.split('=') for p in hdr.split(','))}
rows=re.findall(r'^(\d{3}) (L\d{2}S\d{2}) solid=(\d+) actions=(.*)$', txt, re.M)
# разбор каждого x:y:type и подсчёт по третьему полю
PY
HEADER: 2=101, 3=37, 4=341, 5=53, 6=70, 7=48, 8=38, 9=48, 10=46, 11=56, 12=5, 13=13, 14=92, 15=7, 16=5, 17=10
ROWS: 125 ; TOTAL action tuples in body: 970
  key   2  body= 101  declared=101      key  10  body=  46  declared=46
  key   3  body=  37  declared=37       key  11  body=  56  declared=56
  key   4  body= 341  declared=341      key  12  body=   5  declared=5
  key   5  body=  53  declared=53       key  13  body=  13  declared=13
  key   6  body=  70  declared=70       key  14  body=  92  declared=92
  key   7  body=  48  declared=48       key  15  body=   7  declared=7
  key   8  body=  38  declared=38       key  16  body=   5  declared=5
  key   9  body=  48  declared=48       key  17  body=  10  declared=10
```

**Шапка документа честна по отношению к собственному телу: 16/16, Σ=970.** То есть расхождения ниже —
это не «опечатка в саммари», а разрыв **документ ↔ данные**.

### 2.2 Контроль №2 (обязан был НЕ сойтись — доказательство, что парсер различает имена)

Сопоставление «pix coords / 16 → кортеж doc’а» для объектов **без** `sourceX/sourceY`:

```
$ python3 - <<'PY'   # джойн по tile (x/16, y/16) для 370 объектов без sourceX/Y
== blocks WITHOUT sourceX/Y: doc type found at tile (x/16,y/16) ==
 66 blk_teleportGate  {(): 66}      21 blk_birthpod      {(): 21}
 50 blk_mine          {(): 50}      18 blk_double_barrel {(): 18}
 46 blk_box_white     {(): 46}      15 blk_gunMachine1   {(): 15}
 45 blk_anim_pump     {(10,): 2, (): 43}
 35 blk_box_yellow    {(): 35}      10 blk_tower_dish    {(): 10}
 28 blk_anim_swarm    {(): 28}       6 blk_gate_green    {(): 6}
 23 blk_tower_rocket  {(): 23}       6 blk_ship          {(): 6}
  1 blk_changing_room {(12,): 1}
```

370 из 370 (кроме 3) **не** матчатся → пиксельные координаты TMX не являются ячейками действий оригинала.
При этом там же единственный `capsule` матчится на `23:11:12` (тип 12) — ровно потому, что README
переставил его по эталонным координатам. Контроль сработал в обе стороны.

### 2.3 Точный джойн по `sourceX/sourceY` (главное измерение)

```
$ python3 - <<'PY'   # см. вывод ниже; 145 объектов с sourceX/Y ищем кортеж (x,y) той же зоны
objects with sourceX+sourceY: 145 | doc-coordinate match: 72 | no match: 73

== EMPIRICAL doc-type -> TMX sourceBlock join (exact coordinate match) ==
  type  3: {'blk_gunMachine_TOP': 18}
  type  4: {'blk_blinker': 19}
  type 11: {'blk_gunMachine_BOTTOM': 18}
  type 12: {'blk_changing_room': 4}
  type 13: {'blk_control_beacon': 13}
```

72 совпадения раскладываются на **5 семейств, каждое совпало на 100 %** (18/18, 19/19, 18/18, 4/4, 13/13).
Оставшиеся 73 не матчатся **ни на один** кортеж; ближайший сосед с фиксированным смещением:

```
$ python3 - <<'PY'   # поиск ближайшего doc-кортежа в радиусе ±3 ячеек
 24 blk_waggon             near={(2, 0, -3): 2}
 13 blk_beacon_base        near={(2, -3, 2): 1}
 10 blk_beam_up            near={(2, 0, 2): 10, (17, 2, 2): 10}
 10 blk_beam_down          near=NONE within 3 cells
  9 blk_mushroom           near=NONE within 3 cells
  5 blk_stage_end          near={(15, 2, 0): 5}
  2 blk_topdown_electro    near=NONE within 3 cells
```

`blk_stage_end` 5/5 дают один и тот же тип **15** со смещением `dx=+2`; `blk_beam_up` 10/10 дают тип **17**
со смещением `(+2,+2)`. Это уже не «совпало», а стабильное аффинное смещение — помечаю как
**подтверждённое смещением**, а не как точное равенство.

### 2.4 Итоговая таблица: документ / измерено / прошлый аудит

`doc` = `LEVEL_COMPILER_AUDIT.md:5`; `prior` = `engineering/reports/exolon-initial-audit.md:280-296,307`
и преды-оценка из брифа; `measured` = мои подсчёты (§2.3, `/tmp/docsaudit/final_table.py`).

| doc type | doc | prior audit (утверждал) | measured (я) | Δ | вердикт |
|---|---:|---|---|---:|---|
| 2 | **101** | «torches», 101 | в TMX **нет ни одного** блока этого типа; torch: `grep -rn "torch\|Torch" --include=*.md` → только `ORIGINAL_MECHANICS.md:170`, в Swift — **0** (`torch\|Torch` → ABSENT), в TMX — **0** (`grep -lc torch Exolon/Resources/*.tmx` → пусто) | **−101** | ✗ данных и кода нет вообще |
| 3 | 37 | «37 `turret` … 37=37 ✓ 1:1» | имя `turret` = **37** ✓, но внутри: `blk_gunMachine_TOP`=18 (100 % точно матчится с типом 3), `blk_gunMachine1`=15, **4 без provenance**. Плюс **18** `blk_gunMachine_BOTTOM` — это **тоже пушки**, но тип **11** | 0 по имени, **+18 по семантике** | △ совпало «снаружи», разводится внутри: «1:1» из прошлой оценки неверно |
| 4 | **341** | «flashing cells», densest | `blk_blinker` = **19**, и это **ровно** те же 19 (19/19) матчатся с типом 4 | **−322** | ✗ 341 ячейка типа 4, наружу выгружено 19 |
| 5 | 53 | «53 `mine` 53=53 ✓» | имя `mine` = **53** ✓; `blk_mine` = **50** (3 без provenance); `blk_mine` вообще **без** `sourceX/Y` → точного джойна нет | 0 по имени / **−3** по provenance | △ чиселка верна, доказательство «это те же мины» отсутствует |
| 6 | 70 | «70 `teleport` 70=70 ✓» | `teleport` = **70** ✓; `blk_teleportGate` = **66** (4 без provenance) | 0 / **−4** | △ |
| 7 | 48 | «48 ammo_pack ✓» | `ammo_pack` = **48** ✓; `blk_box_white` = **46**; рантайм `gameState.ammo = 99` (`GameScene.swift:533`) = «ровно», как требует `ORIGINAL_MECHANICS.md:107` | 0 / **−2** | △ |
| 8 | 38 | «38 grenade_pack ✓» | `grenade_pack` = **38** ✓; `blk_box_yellow` = **35**; рантайм `gameState.grenades = 10` (`GameScene.swift:526`) ✓ | 0 / **−3** | △ |
| 9 | 48 | «48 sphere homes; 22 incubator — частично» | `incubator` = **22**, `blk_birthpod` = **21**; `bubble_creator` = **31** / `blk_anim_swarm` = **28** (22+28=50 ≠ 48) | **−26** (9→incubator) | ✗ ни одно семейство не даёт 48 |
| 10 | 46 | «46 piston ✓» | `piston` = **46** ✓; `blk_anim_pump` = **45** | 0 / **−1** | △ |
| 11 | **56** | «rocket launchers 56» | **опровергнуто измерением**: тип 11 = `blk_gunMachine_BOTTOM` **18/18**. `blk_tower_rocket` = **23** (`rocket` = 29), и `grep '"rocket"' → TMXLevelRuntime.swift:264-268` создаёт **`addDestructible`**, то есть статический ящик, а не турель: `grep -n "[Rr]ocket" Exolon/GameCore/*/*.swift` → **3 строки, ни одной пушки/ракеты** | doc 56 ↔ measured 18 (**−38**) | ✗✗ предыдущая таблица была неверна |
| 12 | **5** | «changing room; L01S10, L02S10, L03S11, L04S16, L05S10» | ровно так и есть: `blk_changing_room` → `L01S10/capsule, L02S10/source_marker, L03S11, L04S16, L05S10` = **5** | **0** | ✓ единственное полное 1:1 (4 через точный джойн + capsule через тайловый) |
| 13 | 13 | «13 control_beacon + 13 base» | `blk_control_beacon` = **13**, **13/13** точных совпадений с типом 13 ✓; `blk_beacon_base` = **13**, точных — **0** (13 из 13 вообще не матчатся). Значит «13=13» верно ровно для одного из двух; документ же говорит про **один** тип 13, а в данных их два | 0 / **+13 вторых** | △ |
| 14 | **92** | «bonus triggers» | ни один `sourceBlock` не матчится; `blk_waggon` 24/24 — мимо | **−92** | ✗ |
| 15 | **7** | «high voltage (stage-end adjacent?)» | **противоречие**: `blk_stage_end` 5/5 сидят на типе **15** (`dx=+2, dy=0`). `blk_topdown_electro` = **2**, и он вообще не матчится ни с чем в радиусе 3 ячеек. При этом 2 из 7 — `14:4:15` в L01S25/L05S25 (т.е. тип 15 ≠ HV) | — | ✗ тип 15 = **конец стадии**, а не high voltage |
| 16 | 5 | «stage end: L01S25…L05S25» | экранный список `stage_end` **совпадает** (L01S25, L02S25, L03S25, L04S25, L05S25 = зоны 024/049/074/099/124 ✓ = `ORIGINAL_MECHANICS.md:138`) ✓, но **тип** у них в dump-е **15**, а тип 16 не матчится ни с чем | 0 по спискам / **−5** по типу | △ места верные, код неверный |
| 17 | **10** | «beam / vertical force field; L02S11 `20:2:17`» | `blk_beam_up` = **10** — и 10/10 дают тип 17 со смещением (+2,+2) ✓. `blk_beam_down` = **10**, точных совпадений **0**, соседей в ±3 нет вообще. Рантайм ветка одна: `source.contains("beam_")` (`TMXLevelRuntime.swift:356`) ставит `ForceFieldBarrier` с `hitPoints = 25` (`LevelObstacles.swift:766`) на **каждый** из 20 маркеров | 10 ✓ / **+10 фантомов** | ✓/✗ — см. «дубль поля» ниже |

**Σ сверено:** `doc declared total 970` ↔ `TMX all objects 680` ↔ `minus vitorc 555` ↔ `with sourceBlock 515` ↔ `with sourceBlock+XY 145`.
Ни одна пара не равна; **ровно 40** геймплейных объектов (не `vitorc`) не имеют никакого `sourceBlock`:

```
$ python3 - <<'PY'   # объекты без sourceBlock, кроме vitorc
gameplay objects WITHOUT sourceBlock: 40
  6 rocket  4 turret  4 teleport  3 light_floor  3 light_ceiling  3 grenade_pack
  3 bubble_creator  3 mine  2 ship_fire  2 radar  2 ammo_pack  1 ship  1 cocoon
  1 piston  1 incubator  1 double_launcher
```

### 2.5 Три контрольных значения, которых прошлый аудит не касался

**(a) `solid=` из `LEVEL_COMPILER_AUDIT.md` НЕ воспроизводится из TMX — 0 из 125.**

```
$ python3 - <<'PY'   # построчный разбор Collision (csv) и base64+zlib, сравнение с solid=
encodings: {'base64': 4, 'csv': 121}   cell-count histogram: {840: 125}
solid(any-nonzero) MATCH: 0  MISMATCH: 125
    ('L01S01', 223, 32)   ('L01S02', 204, 32)   ('L01S03', 182, 72)   ('L01S04', 174, 46)
    ('L01S05', 202, 32)   ('L01S06', 122, 35)   ('L01S07', 172, 72)   ('L01S08', 187, 60)
    ('L01S09', 155, 55)   ('L01S10', 121, 80)   ('L01S11', 288, 120)  ('L01S12', 165, 101)
# и ни одна из 4 альтернативных дефиниций «solid» не даёт ни одного совпадения:
matches out of 125 per definition: {'any_nonzero': 0, 'gid_eq_1': 0, 'top_gid_only': 0,
                                    'gid_ge_481(rocks)': 0, 'gid_ge_577': 0}
distinct GIDs: 5 top: [(0, 92671), (1, 12105), (481, 199), (10, 1), (11, 1)]
```

Вывод: `LEVEL_COMPILER_AUDIT.md` описывает **вход компилятора (ASM 1987 года)**, а не привезённые уровни.
Использовать его как доказательство соответствия ТМХ оригиналу нельзя.

**(b) «Двойное силовое поле» подтверждено независимым измерением.**

```
$ python3 -c "... считать объекты с sourceBlock startswith('blk_beam_') по файлам ..."
beam objects total: 20 per-screen count histogram: {2: 10}
```
Каждый из 10 экранов имеет **и** `beam_up`, **и** `beam_down`; рантайм их не различает ⇒
**20 × 25 = 50 попаданий** там, где `ORIGINAL_MECHANICS.md:125` требует одно поле на 25 хитов.
(Прошлая оценка звала это гипотезой; по числу маркеров — это факт данных.)

**(c) Экраны с пустым `actions=`** — прошлый аудит назвал 4, измерение подтверждает:

```
$ python3 - <<'PY'  # rows=re.findall(r'^(\d{3}) (L\d{2}S\d{2}) solid=(\d+) actions=(.*)$',doc,re.M)
screens with empty actions= in dump: 4 ['L01S23', 'L03S09', 'L03S14', 'L04S11']
```

### 2.6 Walkthrough-чекпоинты `ORIGINAL_MECHANICS.md:150-166` против данных

| чекпоинт | зона→файл (измерено) | данные | рантайм |
|---|---|---|---|
| Zone 000 turret/rocks гранатой | `000=L01S01` ✓ | `{'ship':1,'ship_fire':2,'light_floor':3,'light_ceiling':3,'turret':1,'cocoon':1}`, **`blocks={}`** | нет `turret`-провенанса; арт-подложки нет (§1) |
| Zone 002 first paired teleport | `002=L01S03` | `teleport`×2 ✓, `blocks={}` | телепорт реализован ✓ |
| Zone 003 first flying enemy | `003=L01S04` | `{'rocket':2,'grenade_pack':1,'bubble_creator':1}` — **врагов нет** | ✗ (§6.1) |
| Zone 005 birthpod | `005=L01S06` | `incubator`×1 ✓; первый `incubator` = L01S06 ✓ | ✓ |
| Zone 006 double launcher | `006=L01S07` | `double_launcher`×1 ✓; первый = L01S07 ✓ | ✓ |
| Zone 007 first mines | `007=L01S08` | `mine`×3 — **ровно** 3 записи `10:19:5,15:19:5,20:19:5` dump'а ✓ | ✓ |
| Zone 008 control beacon | `008=L01S09` | `blk_control_beacon`×1 + `blk_beacon_base`×1 ✓; первый beacon = L01S09 ✓ | ✓ (`TMXLevelRuntime.swift:394-406`, `150+850`) |
| Zone 009 changing room | `009=L01S10` | ✓ см. §1 L7–L9 | ✓ |
| Zone 023 upper/lower gun machine | `023=L01S24` | `blk_gunMachine_TOP`×1 **+ `blk_gunMachine_BOTTOM`×1** ✓ | BOTTOM **не** реализуется (§2.4/§6.1) ⇒ «комбинированная расстановка» не работает |
| Zone 024 first stage bonus | `024=L01S25` | `blk_stage_end`×1 ✓ (`stage_end first=L01S25, count_screens=5`) | маркер грузится в `stageExitMarkers` и **никогда не читается** (§6.2) |
| Zone 035 25-hit force field | `035=L02S11` | `beam_up`+`beam_down` ✓ (`beam_up first=L02S11, count_screens=10`) | 50 хитов, см. §2.5(b) |
| Zone 043 grenade route | `043=L02S19` | `blk_control_beacon`,`beacon_base`,`box_white`,`mine`×2,`mushroom` | `mushroom` — no-op |
| Zone 059 teleport→beacon | `059=L03S10` | `teleport`×2 + `control_beacon` ✓ | ✓ |
| Zones 086–088 guided missile | `L04S12/L04S13/L04S14` | L04S14 `control_beacon`+`beacon_base` ✓ | ✓ |
| Zone 124 FULL COMBAT ABILITY | `124=L05S25` | `stage_end` ✓; `L05S25` — единственный файл **без** `nextLevel` (`nextLevel` в 124 из 125) ✓ | `GameScene.swift:743-749` → оверлей есть, но «returns the game to the beginning» ✗: `showTitleAfterContentComplete` (`:761-767`) ведёт на **титул**, не на старт |

---

## 3. Упаковка: версии, заголовок, схемы

### 3.1 Версии — расхождение 0.5 / 0.3 **сохранилось на HEAD**

```
$ grep -n "MARKETING_VERSION\|CURRENT_PROJECT_VERSION\|INFOPLIST_FILE\|GENERATE_INFOPLIST_FILE" Exolon.xcodeproj/project.pbxproj
1418:  CURRENT_PROJECT_VERSION = 1;      1420: GENERATE_INFOPLIST_FILE = NO;
1424:  MARKETING_VERSION = 0.5;          1426: PRODUCT_NAME = "$(TARGET_NAME)";
1437:  CURRENT_PROJECT_VERSION = 1;      1439: GENERATE_INFOPLIST_FILE = NO;
1443:  MARKETING_VERSION = 0.5;
$ grep -n -A1 "CFBundleShortVersionString" Exolon/Resources/Info.plist
CFBundleShortVersionString → 0.3        (буквальный литерал, НЕ $(MARKETING_VERSION))
```

Значит подстановка `MARKETING_VERSION` **не подключена**: `GENERATE_INFOPLIST_FILE = NO` и
`CFBundleShortVersionString` жёстко `0.3`. Итог: **сборка 0.5, «О программе»/Finder-показ — 0.3.**
Плюс `CFBundleVersion` = 1 при `CURRENT_PROJECT_VERSION = 1` ✓ (это единственное согласованное поле).
**Δ = 0.2; не исправлено с прошлой оценки.**

### 3.2 Заголовок окна ↔ HUD ↔ титульный экран: **три** разных имени шага

```
$ grep -rn "Step \|STEP" --include=*.swift Exolon
Exolon/Platform/macOS/AppDelegate.swift:16   window.title = "Exolon Remake — Step 9 Rebase"
Exolon/GameCore/GameScene.swift:67            stepLabel.text = "STEP 9 · ALL 125 ORIGINAL ZONES"
Exolon/GameCore/GameScene.swift:656           stepLabel.text = "STEP 9 · \(levelName) · ZONE %03d"
Exolon/GameCore/GameScene.swift:832           addMenuLabel("STEP 10", font: "Menlo-Bold", size: 11, color: .cyan, y: 214, to: titleOverlay)
Exolon/GameCore/GameScene.swift:984           stepLabel.text = "STEP 9 · L01S01 · ZONE 000"
```

Новое (в прошлой оценке этого нет): те же «Step 10» утекли в **имена ключей персистентности**:

```
$ grep -n "Exolon.Step10" Exolon/GameCore/GameState.swift
25: static let hasCheckpoint = "Exolon.Step10.HasCheckpoint"   ... LevelName/Ammo/Grenades/Points/Lives/HighScore
```
⇒ сохранение Step 9 физически лежит в ключах `Step10`; ни `CFBundleShortVersionString`, ни шаг-версия
в чекпоинт не входят (`GameCheckpoint` = `levelName, ammo, grenades, points, lives`), так что
跨-версионный «продолжить» ничем не защищён.

### 3.3 Shared schemes: **нет**

```
$ find Exolon.xcodeproj -type f
Exolon.xcodeproj/project.pbxproj
$ find Exolon.xcodeproj -iname '*xcscheme*'
(пусто)
$ grep -n "MACOSX_DEPLOYMENT_TARGET" Exolon.xcodeproj/project.pbxproj
1394: 10.14   1406: 10.14   1423: 10.14   1442: 10.14     (совпадает с NSMinimumSystemVersion=10.14 ✓)
```
Ни `xcshareddata/xcschemes/`, ни `xcuserdata`. `xcodebuild -list` может показать только авто-схему;
воспроизводимый прогон сборки/тестов в CI или на другой машине **не зафиксирован**.
`README.md` при этом обещает «first runnable archive» (§1 L3).

---

## 4. pbxproj против диска

### 4.1 Swift — чисто

```
$ python3 - <<'PY'   # /tmp/docsaudit/pbx.py: regex по isa = PBXResourcesBuildPhase / PBXSourcesBuildPhase
Resources build phase entries: 276
Sources  build phase entries: 18
Swift on disk: 18
in phase not on disk: []      on disk not in phase: []
```
Все 18 файлов (`main, GameConstants, AppDelegate, BlasterBullet, HUDNode, GameView, ExplosionEffect,
PlayerSpriteNode, GameState, GamepadInput, InputState, Grenade, TMXTileMapRenderer, Player,
TMXMapLoader, TMXLevelRuntime, LevelObstacles, GameScene`) в `PBXSourcesBuildPhase`. 18/18 ✓ (цифра брифа подтверждена).

### 4.2 Ресурсы — ровно те же 5 потерь, что в прошлой оценке, но теперь с вердиктом «не дефект»

```
$ python3 - <<'PY'   # /tmp/docsaudit/pbx2.py: PBXFileReference × PBXBuildFile × фаза ресурсов
PBXFileReference count: 299 ; Resources phase entries: 276 ; buildfiles without PBXBuildFile def: 0
ON DISK but NOT in Resources phase: ['Info.plist','bubble.gif','light.png','rocks.gif','ship_fire.png','turret_bullet.gif']
REFERENCED but NOT on disk: []
fileRef paths not resolvable on disk: <18 *.swift (group-relative), 3 системных framework-пути, Exolon.app>
```
Арифметика сходится: `ls Exolon/Resources | wc -l` = **282** = 276 фаза + 6 (§инвентарь).
Висячих ссылок (ресурс в сборке, файла нет) — **0**.

Ключевая проверка, которой не было раньше: **используются ли эти 5 файлов вообще?**

```
$ python3 - <<'PY'   # /tmp/docsaudit/imgnames.py: все SKTexture(imageNamed:) / image: / imageName = в 18 Swift
image names referenced in Swift: 27
  ammo_pack OK  blaster_bullet OK  blaster_explosion OK  bubble OK  circular_explosion OK  cocoon OK
  double_launcher OK  double_launcher_bullet OK  egg OK  gate OK  grenade OK  grenade_pack OK
  incubator OK  light_ceiling OK  light_floor OK  mine OK  missile OK  piston OK  radar OK
  rocket OK  ship OK  ship_fire_frame OK  teleport OK  turret_body OK  turret_bullet OK
  turret_tube OK  vitorc OK      (27/27 на диске; NOT ON DISK: нет)
```
Все 27 используемых имён разрешаются; ни одно не указывает на `bubble`-gif / `rocks`-gif /
`turret_bullet`-gif / `light.png` / `ship_fire.png`. Код явно берёт «парные» `ship_fire_frame`
(`TMXLevelRuntime.swift:342-343`) и `turret_bullet` png (`LevelObstacles.swift:138`).
⇒ **вердикт меняется с «пропало из сборки» на «это неиспользуемые исходники .gif/дубли; в бандл
не входят и не нужны»**. Отдельный риск остаётся: `.gif` — единственный носитель анимации
(4-кадровой, судя по `turret_bullet.gif` из комментария `LevelObstacles.swift:74`), а SK-код
анимации из gif не строит — то есть **никакого GIF-декодера в дереве нет**, и это не «дефект сборки»,
а неконсистентность формата данных и рантайма.

### 4.3 Формат CSV в TMX — гетерогенен, но рантайм устойчив

```
$ python3 - <<'PY'   # классификация строк Collision по наличию завершающей запятой
 118 files : 23/24 rows end with comma
   4 files : base64
   2 files : 24/24 rows end with comma
   1 files : 0/24 rows end with comma      → L01S10
```
Это **ловушка для парсера**: наивный «flatten по запятым» даёт для `L01S10.tmx` **817** вместо 840
(23 склеенных значения на стыках строк) — я в это реально попал на первой итерации. Настоящий
загрузчик устойчив, потому что режет и по `,`, и по переносу:

```
$ sed -n '333,341p' Exolon/GameCore/Levels/TMXMapLoader.swift
        if encoding == "csv" {
            let values = text
                .split { $0 == "," || $0 == "\n" || $0 == "\r" || $0 == "\t" || $0 == " " }
                .compactMap { UInt32($0) }
            guard values.count == expectedCount else {
                throw TMXMapLoaderError.invalidLayerData(layerName)
```
Строгая проверка `count == expectedCount` есть ✓; `compression` ни в одном из 4 base64-файлов не
используется (`compression=None`), а поддержки zlib в загрузчике нет ⇒ **любой будущий TMX со
`compression="zlib"` уронит загрузку** (`TMXMapLoaderError.unsupportedCompression`). Отдельно:
`Exolon/Resources/L01S10.tmx` — единственный csv без завершающих запятых, т.е. самая «хрупкая»
разметка лежит ровно на рекламном экране Step 9.

### 4.4 Тесты: ноль

```
$ find . -iname '*test*' -not -path './.git/*' -not -path './factory/*' -not -path './.grok-stack/*' -not -path './.ruff_cache/*'
./.agents/skills/bitrix-development/references/testing-review.md
./.grok/agents/test_reviewer.md   ./.grok/agents/test_reviewer.toml
./.grok/skills/bitrix-development/references/testing-review.md
./engineering/changes/.../evidence/test-review.md      (×2 пакета)
./engineering/changes/.../test-plan.md                 (×2 пакета)
```
Ни `*Tests*`, ни `.xctest`, ни XCTest-таргета в `project.pbxproj` (`PBXNativeTarget` один). Значит
каждое утверждение README (§1) подтверждается **только ручным прогоном на macOS**, а самого
процедуру-чеклиста в репозитории нет.

---

## 5. `AGENTS.md` / `decisions.md` / `mistakes.md` против дерева

### 5.1 Обязательные артефакты контракта — отсутствуют

```
$ for p in architecture architecture/system.yaml architecture/rules.yaml architecture/generated \
    START_HERE.md PROJECT_STATE.json mistakes.md trust-ci; do [ -e "$p" ] && echo "PRESENT $p" || echo "MISSING $p"; done
MISSING  architecture            MISSING  architecture/system.yaml
MISSING  architecture/rules.yaml MISSING  architecture/generated
MISSING  START_HERE.md           MISSING  PROJECT_STATE.json
MISSING  mistakes.md             MISSING  trust-ci
$ find . -name 'mistakes.md' -not -path './.git/*'      → пусто
$ find . -name 'decisions.md' -not -path './.git/*'     → ./decisions.md   (только корневой)
```

| строка контракта | требование | состояние |
|---|---|---|
| `AGENTS.md:55,12,57,72` | «Read `START_HERE.md`, `PROJECT_STATE.json`» — **обязательный** вход в каждый деf-таск | оба файла отсутствуют ⇒ «mandatory entrypoint» неисполним; fresh-clone bootstrap (§«Fresh-clone bootstrap») ссылается на несуществующие файлы |
| `AGENTS.md:7,32` | ошибки — в `mistakes.md`; shared memory = `AGENTS.md, decisions.md, mistakes.md` | `mistakes.md` нет нигде |
| `AGENTS.md:26` | «update `README.md` … **current VERSION**» | в README нет версии; фактические версии конфликтуют 0.5/0.3 (§3.1) |
| `AGENTS.md:27` | «Keep README links to `architecture/system.yaml`, `rules.yaml`, `generated/`» | каталога `architecture/` нет, в README **ни одной** ссылки на архитектуру |
| `AGENTS.md:20` | «Trust CI is operated from `trust-ci/`» | каталога нет |
| `AGENTS.md:19,159` | гейт — App-owned чек `adaptive-trust-ci/verified@<policy-sha12>` | в дереве нет ни конфига policy, ни `trust-ci/`; проверить имя чека локально нельзя |
| `AGENTS.md` (bitrix/api/data/ES/ClickHouse разделы) | доменные правила | дерево — Swift/macOS-игра: 0 PHP, 0 SQL, 0 OpenAPI-спека. `engineering/contracts/{openapi,asyncapi,schemas}` — **пусто** (`find engineering/contracts -type f | wc -l` → 0); `engineering/adr` — **0 файлов**; `engineering/reviews` — **0 файлов** (а `AGENTS.md:151` требует хранить ревью-отчёты там или в change package — лежат только в change package ✓) |

**Дополнительно (конфиг роута против дерева):**

```
$ cat .grok-stack/runtime/active-route.json
  "domains": ["generic"],  "repo": { "kind": "generic", "languages": [], "signals": [], "bitrix_modules": [] },
  "base_commit": "403eb132...",  "route_id": "7db1f3f0b126",  "write_agent": null,  "status": "approved"
$ grep -rn "swift\|xcodebuild\|Swift" .grok-stack/config/ | head → пусто
$ ls .grok-stack/config/quality-profiles/
ai.json base.json bitrix.json contracts.json data.json frontend.json infra.json integration.json php.json
```
Роутер объявил репозиторий **безъязыковым** (`languages: []`), хотя в нём 18 `.swift` + `.xcodeproj`;
ни одного Swift/macOS-профиля в `quality-profiles/` нет. Следствие: доменная волна анализа и
профиль качества для этого стека **не выбирались вообще** — «generic» это не «нет риска», а «нет
правила». Также `base_commit` роута (`403eb13`) отстал от HEAD (`b8aee42`) на один commit —
для продукта содержательно не изменивший дерево (§вступление), но отпечаток роута уже не HEAD.

### 5.2 `decisions.md` — **подтверждён**, включая digest

Единственная запись (`decisions.md`, дата 2026-09-20) про «exact pinned upstream module», «two omitted
upstream test modules» и «record them separately from installer-owned files» проверяется полностью:

```
$ cat engineering/runbooks/factory-source.json
"source_commit": "90078959ff...",  "previous_source_commit": "26a0d3db8fa...",  "product_version": "2.0.18",
"managed_file_count": 346,
"changed_managed_files": {"factory/src/adaptive_factory/landing_http.py": "21c03d67fe...01ddc"},
"supplemental_upstream_test_modules": ["factory/tests/test_execution_contracts.py","factory/tests/test_execution_service.py"]

$ sha256sum factory/src/adaptive_factory/landing_http.py
21c03d67fe6f2db1126238397d59e4fec5d38c17de6a82de2eb22d565ca01ddc   ← совпадает с манифестом
$ find factory .grok .agents .grok-stack -type f -not -path '*__pycache__*' | wc -l   → 326
$ echo $((326 + $(ls *.py | wc -l) + $(ls schemas | wc -l)))                          → 346   ← ровно managed_file_count
```
Три проверяемых числа (`346`, digest, 2 supplemental-модуля на диске из `git show --stat HEAD`) сходятся.
**Ни одного противоречия `decisions.md` ↔ дерево не найдено.**

### 5.3 `factory/README.md` — 7 сломанных ссылок из 8

```
$ grep -o '](\.\./[^)]*\|](runtime/[^)]*' factory/README.md | sed 's/^](//' | sort -u | while read p; do ...done
MISSING  ../DARK_FACTORY_ROADMAP.md
MISSING  ../engineering/runbooks/l5-filesystem-publication.md
MISSING  ../engineering/runbooks/l5-production-runtime.md
MISSING  ../engineering/runbooks/l5-provider-failover.md
MISSING  ../engineering/runbooks/l5-runtime-observation-2026-09-15.md
MISSING  ../engineering/runbooks/m4-v2.0.13-local-control-plane.md
PRESENT  ../README.md
MISSING  runtime/landing-failover.example.json      (каталога factory/runtime нет)
```
Плюс внутренняя несостыкованность версий в одном файле: `factory/README.md:14` — «published in `v2.0.13`»,
`:16` — «Published `v2.0.14` …», а `factory/pyproject.toml:6-7` — `name = "adaptive-factory"`, `version = "0.1.0"`,
и `engineering/runbooks/factory-source.json:6` — `product_version: 2.0.18`. Четыре несвязанных номера
версии в одном установочном дереве. Это оверлей фабрики, не игра — но AGENTS-контракт требует, чтобы
доки «matches this tree», и здесь они неmatch.

---

## 6. `ORIGINAL_MECHANICS.md` — заявленный авторитет против рантайма

### 6.0 Заголовки (полный список)

```
$ grep -n '^#' ORIGINAL_MECHANICS.md
1:# Exolon — authoritative mechanics audit          98:## Teleports
9:## Global structure                              105:## Ammo / grenade boxes
19:## Player weapons                                111:## Exoskeleton / changing room
21:### Blaster                                     121:## Vertical force field
29:### Grenade                                     129:## Timed indestructible pursuer
36:## Stationary gun machine                        138:## Stage ends: Zones 024, 049, 074, 099, 124
43:## Double-barrel launcher                        150:## Walkthrough checkpoints that must work exactly
50:## Rocket tower                                  168:## Current remake audit rule
57:## Green missile-guidance beacon
68:## Mines            74:## Pumps / crushers     80:## Sphere homes / birthpods     87:## Flying enemies
```

### 6.1 Механики без какой-либо реализации в 18 Swift-файлах

Поиск по существующим в кодам идентификаторам (`grep` по всем `Exolon/**/*.swift`, скрипт
`/tmp/docsaudit/mech.py`):

| раздел | механика | маркер в данных | маркер в коде | вердикт |
|---|---|---|---|---|
| `:87` Flying enemies | `tab_enemy`, **шесть таблиц траекторий**, 6 слотов, X=120 spawn, стоп при X≥84, 150 pts | — | `trajector\|Trajectory\|FlyingEnemy\|flyer` → **ABSENT**; `spawn`-логики врагов нет; в `GameScene` есть только `enemyBullets: [EnemyTurretBullet]` (`:28`), наполняемый **исключительно** выстрелами турелей (`:293`) | **НЕТ РЕАЛИЗАЦИИ** — подраздел про «шесть таблиц, портируемых буквально» не имеет ни данных, ни кода |
| `:129` Timed indestructible pursuer | 700-loop таймер, неуязвимый преследователь | — | `pursuer\|Pursuer\|\b700\b` → **ABSENT** | **НЕТ РЕАЛИЗАЦИИ** |
| `:50` Rocket tower | огонь только издалека (порог 30), vx=−2, ракета сбивается за 50, контакт убивает | `blk_tower_rocket` = **23** (`rocket` = 29) | `TMXLevelRuntime.swift:264-268` — только `addDestructible(name:"rocket", size 64×96)`; `grep "[Rr]ocket"` по `GameCore/*/*.swift` → 3 строки, ни одной пушки/баллистики; порог `30` в этом смысле — **ABSENT** | **ЕСТЬ СПРАЙТ, НЕТ МЕХАНИКИ** — прямое нарушение собственного правила `:170` («a sprite in the backdrop is not implementation») |
| `:170` audit rule: **torches** | обязателен рантайм-аналог | **0** маркеров в 125 TMX (`grep -lc torch` → пусто) | **0** упоминаний в Swift | **НЕТ НИ ДАННЫХ, НИ КОДА** |
| `:121` Vertical force field | «extends … until the next no-walk cell» | `beam_up`10 + `beam_down`10 | `TMXLevelRuntime.swift:357` — **жёсткий** прямоугольник `bottomY-240`, `height 272`; поиска «next no-walk cell» нет | **РЕАЛИЗОВАНО ПРИБЛИЖЁННО** (формулировка документа не соблюдена) + дубль полей (§2.5b) |
| `:80` Sphere homes | 8 на дом ✓, **ёмкость движка 24** | `incubator`22 → 176 яиц | `for index in 0..<8` (`LevelObstacles.swift:539`) ✓; глобального лимита 24 **нет** (`\b24\b` в `GameScene` — только `L%02dS%02d` и `0.25`) | **ЧАСТИЧНО**: 8 ✓, capacity 24 ✗ |
| `:138` Stage ends | +1 life ✓, 1000×lives ✓, **10 000 bravery**, **timed bonus 0/1000/3000/5000/7000**, **«Clear exoskeleton»** | `blk_stage_end` = 5 | `GameScene.swift:622-631` делает только award(lives×1000), +1 life, ammo=99, grenades=10. `bravery\|10_000\|10000` → **ABSENT**; `setExoskeleton` вызывается ровно **один** раз — `:963` (restart), на границе стадии — **никогда** | **3 из 6 правил отсутствуют**; и следствие: экзоскелет переживает **все** 5 стадий, вопреки `:117` «At stage end the exoskeleton flag is cleared» |
| `:168` audit rule: **bonus triggers** (тип 14, 92) | обязателен рантайм | ни одного матча (§2.4) | `bonus` в Swift — только комментарий `:623` | **НЕТ** |
| `:168` audit rule: **high voltage** | обязателен рантайм | `blk_topdown_electro` = 2 | `TMXLevelRuntime.swift:361-365` — явный `break` с комментарием «do not turn the visual marker into a blanket lethal rectangle» | **СОЗНАТЕЛЬНО NO-OP** (решение обосновано, но правило `:170` формально не выполнено) |
| `:168` audit rule: **flashing cells** (тип 4) | обязателен рантайм | `blk_blinker` = 19 | `:366-368` — `break`, no-op | **СОЗНАТЕЛЬНО NO-OP** |
| `:168` (и §2.4 тип 11) | нижние gun machines | `blk_gunMachine_BOTTOM` = **18** | ни `case`, ни `contains("gunMachine")`: `source.contains(...)` = `[beacon_base, beam_, blinker, changing_room, control_beacon, stage_end, topdown_electro]` | **НЕТ**: 18 маркеров молча отбрасываются |
| — | `blk_waggon` = **24**, `blk_mushroom` = **9**, `blk_beacon_base` = 13 (12 из 13 без матча) | — | `waggon\|Waggon` → **ABSENT**; `mushroom\|Mushroom` → **ABSENT** | **НЕТ**: 51 `source_marker` не обрабатывается (моя независимая пересъёмка цифры прошлой оценки: 24+18+9 = **51** ✓) |

### 6.2 Мёртвый код в той же связке

```
$ grep -rn "stageExitMarkers" Exolon --include=*.swift
Levels/TMXLevelRuntime.swift:30:  private(set) var stageExitMarkers: [CGRect] = []
Levels/TMXLevelRuntime.swift:370: stageExitMarkers.append(...)          # наполняется 5 маркерами
(ни одного чтения)
$ grep -rn "sourceHazards" Exolon --include=*.swift
GameScene.swift:575:  currentLevel.sourceHazards.contains(where: ...)   # читается в ветке смерти
Levels/TMXLevelRuntime.swift:28: private(set) var sourceHazards: [CGRect] = []
(ни одного append)
```
Значит: бонус стадии срабатывает **не** от stage-end-маркера, а от `player.position.x > 510`
(`GameScene.swift:610-612`: `guard player.position.x > 510` → `applyOriginalStageBoundaryIfNeeded`), а «source hazard» ветка обработки урона мертва в обе стороны.

### 6.3 Что в `ORIGINAL_MECHANICS.md` **выполнено** (позитивный контроль)

```
$ grep -n "startingAmmo\|startingGrenades\|startingLives" Exolon/GameCore/GameState.swift
81: startingAmmo = 99   82: startingGrenades = 10   83: startingLives = 9   ← :14 «9 lives, 99 blaster, 10 grenades» ✓
$ grep -n "hitPoints = " Exolon/GameCore/Objects/LevelObstacles.swift
766: private var hitPoints = 25                                              ← :125 «exactly 25 blaster hits» ✓
$ grep -n "return (guidance.center, positions" Exolon/GameCore/Levels/TMXLevelRuntime.swift
205: return (guidance.center, positions, 150 + (positions.isEmpty ? 0 : 850)) ← :65 «150 + 850 = 1000» ✓
$ grep -n "isFast && position.x <= 280" Exolon/GameCore/Objects/LevelObstacles.swift
859:                                                    ← :61 «X=70 → X=280 в 512-wide» ✓
$ grep -n "grenadeJustPressed" Exolon/GameCore/GameScene.swift
354: let grenadeJustPressed = input.grenade && !grenadeWasPressed  ← :30 «GRENADE — отдельная кнопка» ✓
$ grep -n "for index in 0..<8" Exolon/GameCore/Objects/LevelObstacles.swift → 539 ✓ 8 eggs/home (:81)
```
Также ✓: «Normal screen entry gives no invulnerability» (`ORIGINAL_MECHANICS.md:13`) — комментарий и
`invulnerability = 0` в `transition` (`GameScene.swift:648-649`); край срабатывания UP и для телепорта,
и для кабины (`GameScene.swift:233/239/244`, против `:102` «holding UP must not continuously retrigger»);
«Ammo/grenade boxes are refills, not additive» (`:107-109`) — `GameScene.swift:533` `= 99`, `:526` `= 10` ✓;
стартовые позиции стадии — код берёт `currentLevel.spawnCenter` + `isStageStart = [0,25,50,75,100]` (`:642`),
сверить с ASM-числами `(16,112)/(0,120)/(0,32)/(40,128)/(16,112)` локально **нельзя** (источника
`rusarh/exolon-esl` в дереве нет, §8).

---

## 7. Сводка новых противоречий «документ ↔ дерево»

Рангом по вреду; «новое» = не зафиксировано в `analysis-docs_researcher.md`, `analysis-architect.md`
и `engineering/reports/exolon-initial-audit.md`.

1. **`TYPE 11 = нижние пушки, а не rocket launchers.** Точный координатный джойн: 18/18 `blk_gunMachine_BOTTOM` ↔ тип 11. Предыдущая таблица (`analysis-docs_researcher.md` §3) присвоила типу 11 «rocket launchers», а «Rocket tower» в данных — `blk_tower_rocket` = 23, и он **не** имеет ни одного матчевого кода. Следствие: недооценённая дыра в 18 турелях и ложный чекпоинт «зона 005/rocket» в README-логике.
2. **`TYPE 15 = конец стадии`, а не high voltage.** 5/5 `blk_stage_end` стоят на типе 15 (смещение `dx=+2, dy=0`). Прошлая таблица: 15 = «high voltage (stage-end adjacent?)», 16 = «stage end» — оба неверно; тип 16 не матчится ни с чем.
3. **`TYPE 4 = 341`, а мигалок в данных 19 (19/19 точных).** Равенство «4=341» и «341 объекта с единственным свойством sourceBlock» — **случайность**, а не соответствие: 341 — это ячейки-атрибуты, из которых наружу выгружено 5.7 %.
4. **`solid=` в `LEVEL_COMPILER_AUDIT.md` не воспроизводится: 0/125** (ни при одной из 5 дефиниций). Документ описывает вход компилятора, а не привезённые уровни; использовать его как доказательство соответствия оригиналу нельзя.
5. **Три разных имени шага + Step10 в ключах UserDefaults.** README/`AppDelegate.swift:16` = «Step 9 Rebase», HUD `:67,656,984` = «STEP 9», титул `:832` = **«STEP 10»**, персистентность `GameState.swift:25-31` = **`Exolon.Step10.*`** — при этом чекпоинт не несёт версии ⇒ кросс-версионное «продолжить» ничем не защищено.
6. **Версии всё ещё рассинхронизированы**: `MARKETING_VERSION = 0.5` ↔ `CFBundleShortVersionString = 0.3` (литерал, `GENERATE_INFOPLIST_FILE = NO`).
7. **`coordinateMode=tiledRect` ровно в 1 файле из 125** (у 360 rect-объектов). Значит README L10 («rectangle conversion is explicit … no longer conflated») — правка одного экрана, поданная как системное свойство.
8. **«original-visual pipeline» не полон**: у 5 экранов (зоны 000, 001, 002, 003, 006) нет ни одного `imagelayer`; у L01S01–L01S04 вообще нулевой `sourceBlock`-провенанс.
9. **Исключение коллизий кабины имеет две разные геометрии** для одного класса объекта (`capsule`: `max(96, w+64)`; `source_marker`: `w+32`) ⇒ «applied by object type» верно по типу, неверно по форме на 4 из 5 экранов.
10. **`stageExitMarkers` пишется и не читается; `sourceHazards` читается и не пишется.** Бонус стадии привязан к `x > 510`, а не к маркеру.
11. **20 силовых полей вместо 10** (по 2 на каждом из 10 экранов, `beam_up`+`beam_down`) ⇒ 50 хитов против документированных 25.
12. **Нет ни одной общей схемы Xcode** (`find Exolon.xcodeproj -iname '*xcscheme*'` → пусто) и **ни одного Swift-теста** при обещании «first runnable archive».
13. **Контракт `AGENTS.md` неисполним в дереве**: `START_HERE.md`, `PROJECT_STATE.json`, `mistakes.md`, `architecture/{system.yaml,rules.yaml,generated}/`, `trust-ci/` — все отсутствуют; README без VERSION и без ссылок на архитектуру; `engineering/{adr,contracts/*,reviews}` пусты.
14. **Конфиг роута объявляет репозиторий безъязыковым** (`repo.languages: []`, `kind: generic`) при 18 Swift-файлах и `.xcodeproj`; в `quality-profiles/` нет ни одного Swift-профиля ⇒ для этого стека не выбрано ни одно правило качества. Плюс `base_commit` роута (`403eb13`) не равен HEAD (`b8aee42`).
15. **`factory/README.md`: 7 из 8 относительных ссылок битые**, и в одном файле соседствуют v2.0.13 / v2.0.14 / `pyproject version = 0.1.0` / `product_version = 2.0.18`.
16. **5 «потерянных» ресурсов прошлой оценки — не дефект сборки** (ни один не используется в коде: 27/27 referenced имён есть на диске). Настоящая проблема другая: `.gif`-файлы остаются единственным носителем анимации, а декодера GIF в рантайме нет.
17. **Форматная ловушка `L01S10.tmx`**: единственный csv без завершающих запятых в строках (0/24 против 23/24 у 118 файлов); наивный парсер теряет 23 ячейки. Загрузчик Swift устойчив (режет и по `\n`) и строго проверяет `count == expectedCount`, но поддержки zlib нет — base64+zlib TMX уронит загрузку.

Подтверждённое позитивное (§5.2): `decisions.md` ↔ `factory-source.json` ↔ `sha256sum` ↔ `managed_file_count = 346` — **всё сходится**, противоречий нет.

---

## 8. Что я не смог измерить локально (границы отчёта)

- **Runtime-поведение.** Нет macOS/Xcode, `xcodebuild` недоступен, схем и тестов нет ⇒ все строки README из §1 проверены как **структура кода и данных**, не как игровой прогон.
- **Оригинальные ASM-первоисточники.** `rusarh/exolon-esl`, `data_zone_data.asm`, `actions_*.asm`, `game_init_actions.asm`, `tab_enemy`, «шесть таблиц траекторий», `BLASTER_BULLET_OFFSET_Y`, стартовые `(16,112)/(0,120)/(0,32)/(40,128)` — в дереве **отсутствуют** (`find . -name '*.asm' -not -path './.git/*' | wc -l` → **0**) ⇒ перепроверить можно только по внешней копии). Значит соответствие «маркер ↔ ROM» остаётся непроверяемым; в отчёте я опираюсь на внутренний джойн `LEVEL_COMPILER_AUDIT.md ↔ TMX`, а он, как показал §2.5(a), не является доказательством соответствия оригиналу.
- **Число и имя требуемого Trust CI чека** (`adaptive-trust-ci/verified@<policy-sha12>`) — policy не лежит в дереве, §5.1.
- **`git fetch --all --prune`** я не выполнял: задача — read-only сверка локального дерева, HEAD зафиксирован брифом (`b8aee42`).
