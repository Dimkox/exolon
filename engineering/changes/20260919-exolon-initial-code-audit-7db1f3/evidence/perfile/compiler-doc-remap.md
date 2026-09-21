# D-01: исправленный артефакт — `LEVEL_COMPILER_AUDIT.md` ↔ привезённые TMX ↔ Swift

**Lane:** read-only, только этот файл. **HEAD:** `52795d1`. **Продукт не тронут:**
`git status --porcelain` по `Exolon/`, `LEVEL_COMPILER_AUDIT.md` — пусто; все измерения
сняты `python3` (stdlib) и `grep`, скрипт — `/tmp/lane-remap/join_measure.py` (в дереве не добавлен).
C1 в этой работе не касается: здесь нет ни одного утверждения про вырез пола в кабине.

## Итог

1. **`LEVEL_COMPILER_AUDIT.md` — не описание привезённых уровней.** Это трассировка **входа
   ASM-компилятора 1987 года**: 970 кортежей `(колонка, строка, тип действия)` на сетке оригинала
   32×20 и счётчик `solid=` на экран. Единственное соединение этого документа с данными 125 TMX,
   которое не является догадкой, — точное совпадение `sourceX/sourceY` объекта с кортежем той же
   зоны: **72 объекта из 145 кандидатов (7,4 % от 970 кортежей)**. Остальные 73 кандидата не
   матчатся **ни с одним** кортежем.
2. **«тип ↔ документ 1:1» неверно системно, и это измеримо по типам.** Из 16 типов документа
   хотя бы одно точное соединение дают **5**: типы **3, 4, 11, 12, 13**. У **11 типов** соединений
   ноль: **2, 5, 6, 7, 8, 9, 10, 14, 15, 16, 17**. Полное 1:1 по всему семейству — только у типа 13
   (`blk_control_beacon` 13/13); у типа 12 — 4/5, у остальных трёх — 18/37, 19/341, 18/56.
3. **Тип 11 = `blk_gunMachine_BOTTOM` (18/18), а не «56 rocket launchers».** Ракетные башни в данных —
   `blk_tower_rocket` = 23 (носитель — имя `rocket`, 29), и с документом они не соединяются вовсе:
   у всех 23 нет `sourceX/sourceY`. Рантайм из `rocket` делает `addDestructible`
   (`TMXLevelRuntime.swift:264-269`), то есть статический ящик, а не пушку.
4. **Тип 15 = конец стадии, а не high voltage.** `blk_stage_end` — 5 объектов с провенанс-координатами,
   и все 5 дают **один и тот же** соседний кортеж типа 15 при стабильном смещении `dx=+2, dy=0`
   (замер §«Честный замер», п. 4). Раскладка 7 кортежей типа 15 по экранам: `L01S25 14:4:15`,
   `L02S01 13:7:15`, `L02S25 19:3:15`, `L03S17 8:6:15`, `L03S25 14:5:15`, `L04S25 14:4:15`,
   `L05S25 19:3:15` — то есть **5 из 7 стоят ровно на пяти экранах конца стадии**, а два
   (`L02S01`, `L03S17`) в середине стадии. Тип 16 («stage end» по унаследованной таблице) встречается
   ровно на тех же пяти `?S25` и **ни с одним объектом не соединяется**. `blk_topdown_electro` (HV) =
   2 объекта, и у них нет соседа даже в окне ±3 клетки.
5. **`solid=` не воспроизводится из привезённых карт: 0/125** ни при одной из двух дефиниций
   (ненулевые клетки слоя `Collision` / ровно `gid==1`). При этом слои декодируются корректно:
   число ячеек **840 = 35×24 во всех 125 файлах**, так что 0/125 — не артефакт парсера.
6. **Контрольное число в сводном отчёте завышено и должно быть исправлено:** не «контроль **0/370**»,
   а **3/370** (см. §«Честный замер джойна и контроля»). Прав сам артефакт
   (`analysis-docs_researcher-fullaudit.md:159` — «370 из 370, кроме 3»), не прав
   `engineering/reports/exolon-full-audit-20260920.md:16`. На вывод D-01 это не влияет:
   даже самая выгодная для ложного джойна конвенция даёт **20/370 (5,4 %)**, то есть индекс
   по-прежнему не является соединением.
7. **Обратная сторона — код не реализует данные, которые документом не покрыты вообще:**
   **72 из 127** объектов `source_marker` остаются без реализации (51 в `default`: `blk_waggon` 24,
   `blk_gunMachine_BOTTOM` 18, `blk_mushroom` 9; 21 в ветках-`break`: `blk_blinker` 19,
   `blk_topdown_electro` 2); `stageExitMarkers`
   заполняется и **никогда не читается** (0 обращений вне билдера); `sourceHazards` читается в
   `GameScene.swift:575` и **никогда не заполняется** (0 `append`). Числовое совпадение «72 джойна /
   72 выброшенных объекта» — случайность, это разные множества.

## Что описывает документ

Ровно три осмысленных элемента, больше в файле 133 строк ничего нет
(`grep -c '^#' LEVEL_COMPILER_AUDIT.md` → **1**):

| строки | заголовок/содержимое | что это на самом деле |
|---|---|---|
| 1 | `# Original level compiler audit` | единственный заголовок всего файла; подразделов нет |
| 3 | «Generated all 125 screens from the 1987 zone/block/font data.» | тезис о провенансе: источник — **данные 1987 года**, а не TMX ремейка |
| 5 | «Action counts: 2=101, …, 17=10» | гистограмма **по третьему полю** кортежа; Σ=970 |
| 7–133 | один fenced-блок, 125 строк `NNN LxxSyy solid=NNN actions=c:r:t,…` | дамп выхода генератора: индекс экрана, имя зоны, счётчик твёрдых клеток, список действий |

Измерения формы (раздел 1 скрипта):

- шапка равна гистограмме **только** третьего поля: `header tallies field #[2]`, и
  `declared == body histogram per type: True` (16/16). То есть поле 3 — **тип действия**, а поля 1–2 —
  **координаты ячейки**; первая-проходная интерпретация «первое поле = тип» опровергается самой шапкой.
- диапазоны полей: `col 0..31` (32 значения), `row 1..20`, `type 2..17`. Сетка документа — **32×20**,
  а карта ремейка — **35×24** (`map geometry=[(35, 24, 16, 16)]`): документ живёт в строго
  подмножестве геометрии TMX, и это ещё одна причина, по которой «пиксель ≠ ячейка».
- **970 кортежей лежат на 970 различных клетках** — двух действий в одной клетке документ не
  выражает вовсе; это форма трассировки «одно действие = одна клетка», а не схема уровня.
- `0` и `1` как типы не встречаются; 4 экрана имеют пустой `actions=`
  (`L01S23`, `L03S09`, `L03S14`, `L04S11`).
- **Легенды имён в документе нет.** Единственный источник названий для типов 2…17 в дереве —
  упорядоченный список семейств действий в `ORIGINAL_MECHANICS.md:170`
  («torches, gun machines, flashing cells, mines, teleport, white/yellow refill boxes, sphere homes,
  pumps, rocket launchers, changing room, green guidance, bonus triggers, high voltage, stage end and
  beam» — ровно 16 позиций на 16 ключей шапки), перенесённый на коды по возрастанию в
  `engineering/reports/exolon-initial-audit.md:280-301`. Поэтому колонка «имя» в матрице ниже —
  **унаследованная**, а не документная: сам документ не называет ни одного типа.
- `solid=` — счётчик твёрдых клеток входа компилятора; из привезённого слоя `Collision` не
  воспроизводится (0/125, две дефиниции).

## Матрица тип↔данные↔код

Столбцы: `doc` — объявленное количество в `LEVEL_COMPILER_AUDIT.md:5`; `джойн` — число объектов,
**точно** совпавших по `(sourceX, sourceY)` с кортежем той же зоны; `носитель` — имя TMX-объекта,
на котором семейство ездит, и его полное количество по всем 125 картам; `код` — что делает с ним
`TMXLevelRuntime.buildObjectsFromTMX` (`switch object.name`, `:241`; под-дิสпатч `source_marker`
по 7 подстрокам, `:356-408`; `default:` — молча `break`, `:409-413`).

| тип | унаследованное имя | doc | джойн | семейство → носитель (n/125 карт) | код | вердикт |
|---|---|---:|---:|---|---|---|
| 2 | torch | 101 | 0 | семейств `blk_torch*` в данных **нет**; `grep -ril torch Exolon/` → **0 файлов** | нет `case` | **no data** |
| 3 | gun machine | 37 | 18 | `blk_gunMachine_TOP` 18 → `turret` **37** (18 TOP + 15 `blk_gunMachine1` + 4 без провенанса) | `case "turret"` → `TurretObstacle` (live) | **verified join** (18/37 = 49 %) |
| 4 | flashing cell | 341 | 19 | `blk_blinker` 19 → `source_marker` 127 | ветка `blinker` = `break` (`:366-368`) | **code-ignored data** (19/341 = 5,6 %) |
| 5 | mine | 53 | 0 | `blk_mine` 50 → `mine` **53** | `case "mine"` (live) | **name-only join** |
| 6 | teleport | 70 | 0 | `blk_teleportGate` 66 → `teleport` **70** | `case "teleport"` (live) | **name-only join** |
| 7 | white refill box | 48 | 0 | `blk_box_white` 46 → `ammo_pack` **48** | `case "ammo_pack"` (live) | **name-only join** |
| 8 | yellow refill box | 38 | 0 | `blk_box_yellow` 35 → `grenade_pack` **38** | `case "grenade_pack"` (live) | **name-only join** |
| 9 | sphere home | 48 | 0 | `blk_birthpod` 21 → `incubator` 22; `blk_anim_swarm` 28 → `bubble_creator` 31 | оба live | **name-only join** (48 совпадает лишь с `ammo_pack`) |
| 10 | pump | 46 | 0 | `blk_anim_pump` 45 → `piston` **46** | `case "piston"` (live) | **name-only join** |
| 11 | rocket launcher | 56 | 18 | `blk_gunMachine_BOTTOM` 18 → `source_marker` 127 | **нет** ни одной из 7 подстрок → `default: break` | **code-ignored data**; имя ложно (ракеты = `blk_tower_rocket` 23, джойн 0) |
| 12 | changing room | 5 | 4 | `blk_changing_room` 5 → `source_marker` 4 **+** `capsule` 1 | обе ветки live (`changing_room`, `:371-379`; `case "capsule"`) | **verified join** (4/5 точных + 1 через контроль-индекс) |
| 13 | green guidance | 13 | 13 | `blk_control_beacon` 13 → `source_marker` | ветка `control_beacon` → `GreenMissileGuidance` (live) | **verified join** — единственное полное 1:1 (13/13) |
| 14 | bonus trigger | 92 | 0 | ни одно из 25 семейств не называется бонус-триггером | — | **no data** |
| 15 | high voltage | 7 | 0 | `blk_topdown_electro` 2 (носитель `source_marker`) — соседа в ±3 нет; сам тип 15 занят `blk_stage_end` | ветка `topdown_electro` = `break` (`:361-365`) | **name-only join**; тип 15 фактически = **stage end** (5/5 при `dx=+2`) |
| 16 | stage end | 5 | 0 | `blk_stage_end` 5 → `source_marker` | `stage_end` → `stageExitMarkers`, читается **0** раз | **no data** для типа 16 (данные живут под типом 15) |
| 17 | beam | 10 | 0 | `blk_beam_up` 10 и `blk_beam_down` 10 → `source_marker`; в 10 экранах есть **оба** | ветка `beam_` (`:356-360`) → `ForceFieldBarrier`, `hitPoints = 25` (`LevelObstacles.swift:766`); up/down не различаются | **no data** (см. двусмысленность смещения ниже) |

Распределение вердиктов (ровно то, что печатает скрипт в разделе 7): **verified join + live code — 3**
типа (3, 12, 13); **verified join + code-ignored data — 2** (4, 11); **name-only join — 7**
(5, 6, 7, 8, 9, 10, 15: семейство/имя в данных есть, точного соединения нет; у типа 15 «совпадение»
по числу даёт только абсурдное `ship`=7); **no data — 4** (2, 14, 16, 17).

## Обратное направление

**(а) Типы документа без данных.** 11 из 16: `2, 5, 6, 7, 8, 9, 10, 14, 15, 16, 17`. Из них у двух
(`2` torch — 101 кортеж, `14` bonus trigger — 92) в данных нет даже семейства-кандидата, а у `16` и
`17` кандидаты есть (`blk_stage_end`, `blk_beam_up`/`blk_beam_down`), но они соединяются с чужими
типами — 15 и двусмысленно `2`/`17` соответственно (п. 4 ниже).

**(б) Семейства TMX, которые документ не соединяет.** **20 из 25**: `blk_anim_pump`, `blk_anim_swarm`,
`blk_beacon_base`, `blk_beam_down`, `blk_beam_up`, `blk_birthpod`, `blk_box_white`, `blk_box_yellow`,
`blk_double_barrel`, `blk_gate_green`, `blk_gunMachine1`, `blk_mine`, `blk_mushroom`, `blk_ship`,
`blk_stage_end`, `blk_teleportGate`, `blk_topdown_electro`, `blk_tower_dish`, `blk_tower_rocket`,
`blk_waggon`. Пять соединяющихся: `blk_blinker`, `blk_changing_room`, `blk_control_beacon`,
`blk_gunMachine_TOP`, `blk_gunMachine_BOTTOM`.

**(в) Имена, которых нет ни в документе, ни в семействах.** Документ не именует **вообще ничего**,
поэтому все 20 имён TMX и все 20 `case` Swift — «имена без документа». Узкое, проверяемое ядро:
5 имён не имеют даже `sourceBlock`, то есть не связаны с 1987-м входом ничем — `vitorc` (125, маркер
спавна), `light_floor` (3), `light_ceiling` (3), `ship_fire` (2), `cocoon` (1). Плюс **40** геймплейных
объектов (не `vitorc`) без провенанса: `rocket` 6, `turret` 4, `teleport` 4, `light_floor` 3,
`light_ceiling` 3, `grenade_pack` 3, `bubble_creator` 3, `mine` 3, `ship_fire` 2, `radar` 2,
`ammo_pack` 2, `ship`/`cocoon`/`piston`/`incubator`/`double_launcher` по 1 (сумма — ровно 40;
полный словарь
печатает раздел 8 скрипта).

**(г) Данные, до которых код не доезжает.** **72** объекта `source_marker` не получают никакой
реализации: **51** уходят в `default` (`blk_waggon` 24, `blk_gunMachine_BOTTOM` 18,
`blk_mushroom` 9), ещё **21** формально распознаются веткой, которая оканчивается `break`
(`blk_blinker` 19, `blk_topdown_electro` 2).
Два маркерных массива разведены по разные стороны: `stageExitMarkers` populated=1 / read=0,
`sourceHazards` populated=0 / read=1 (`GameScene.swift:575` проверяет всегда пустой список).
`beam_` не различает `up`/`down`: 20 маркеров (10 экранов × 2) → 20 барьеров по 25 хитов, тогда как
документ объявляет под «beam» 10 кортежей типа 17.

**(д) Что документ не описывает никогда:** слои (`Collision` есть в 125/125, `Tile Layer 1` лишь в 7,
`Stars`/`Tile Layer 2` в 3), `imagelayer` (`Original Static Scenery` 118 + `Original Scenery` 2),
свойств карты (`zoneNumber`, `zoneSource`, `nextLevel`, `originalSource`, `step9Corrected`, …) —
то есть вся геометрия и весь пиксельный арт привезённых уровней лежат **вне предметной области
документа**, что и согласуется с 0/125 по `solid=`.

## Честный замер джойна и контроля

**1. Лестница провенанса (ничего не додумывая):** 680 объектов → 515 с `sourceBlock` →
**145** с `sourceX`+`sourceY` → **72** точно матчатся кортежем той же зоны, **73** — нет.
По семьям точное соединение дают только: `blk_gunMachine_TOP` 18/18 (тип 3),
`blk_blinker` 19/19 (тип 4), `blk_gunMachine_BOTTOM` 18/18 (тип 11),
`blk_control_beacon` 13/13 (тип 13), `blk_changing_room` 4/5 (тип 12).
Джойн инъективен в обе стороны и потому не «покрытие на глаз»: 970 кортежей лежат на 970 различных
клетках `(зона, col, row)`, а 145 провенанс-объектов — на 145 различных клетках
`(зона, sourceX, sourceY)` (измерено; коллизий нет ни там, ни там).

**2. Контроль на нерелевантном индексе — то, что в сводке названо «0/370».** Пул — **370** объектов
с `sourceBlock`, но **без** `sourceX/sourceY`; им приходится угадывать ячейку. Прогнано 8 конвенций
(2 трактовки TMX `y` × 4 сдвига колонки):

| конвенция | col-shift | совпало | типы |
|---|---:|---:|---|
| `row = y/16` (Tiled, верх-левый) | 0 | **3/370** | `{10: 2, 12: 1}` |
| `row = y/16` | 1 / 2 / 3 | 0 / 1 / 2 | `{}` / `{5:1}` / `{7:1, 10:1}` |
| `row = (Hpx−y)/16` (то, что делает `worldBottomLeft`, `TMXMapLoader.swift:73-80`) | 0 | **20/370** | `{4: 15, 7: 2, 8: 2, 14: 1}` |
| `row = (Hpx−y)/16` | 1 / 2 / 3 | 3 / 3 / 7 | `{9:2,11:1}` / `{4:1,9:2}` / `{4:7}` |

Три совпадения наивной конвенции — это **не шум в четыре цифры**, а ровно те же объекты, что
называет артефакт:

```
L01S10/capsule        x=368 y=176 blk_changing_room -> tile (23,11) тип [12]
L01S10/piston         x=192 y=320 blk_anim_pump     -> tile (12,20) тип [10]
L01S10/piston         x=64  y=320 blk_anim_pump     -> tile (4,20)  тип [10]
```

**Какое число верно.** `analysis-docs_researcher-fullaudit.md:159` («370 из 370, кроме 3
не матчатся») — **верно**, моя независимая ре-деривация даёт ровно **3/370** (и те же самые
объекты). `engineering/reports/exolon-full-audit-20260920.md:16` («контроль **0/370**») —
**неверно**: ноль там получен округлением «кроме 3» до «нулей». Корректная формулировка:
**3/370 (0,8 %) случайных совпадений, 367/370 чисто**, и даже при самой выгодной конвенции
**не более 20/370 (5,4 %)** — то есть контроль остаётся контролем (он не даёт джойна), но он
**не нулевой**. Одно из трёх совпадений содержательное: капсула `L01S10` попала в тип 12
именно потому, что README расставил её по эталонным координатам оригинала, — это, наоборот,
мелкий **плюс** к строке 12 в матрице, а не «шум».

**3. Специфичность основного джойна (контроли, которые обязаны перевернуться):**

```
(sourceX+1, sourceY+1) в той же зоне  : 0/145
те же координаты в соседней зоне      : 0/145
те же координаты в своей зоне         : 72/145   <- базовый замер
```

Сдвиг на одну ячейку и «перенос в чужую зону» убивают соединение полностью: 72 — не артефакт
смещения и не путаница зон.

**4. Смещения вместо равенства.** Для семейств с провенанс-координатами, но без точного совпадения,
окно ±3 клетки даёт стабильное («для всех объектов семейства») смещение только в двух случаях:

```
blk_stage_end  n=5   STABLE-for-all = [(15, +2, 0)]
blk_beam_up    n=10  STABLE-for-all = [(2, 0, +2), (17, +2, +2)]
```

Первая строка — доказательство, что тип 15 занят концом стадии. Вторая — честное
предостережение против «17 = beam»: у тех же 10 маркеров есть **два** конкурирующих стабильных
соседа, тип 2 (факелы) со сдвигом `dy=+2` и тип 17 со сдвигом `dx=+2, dy=+2`. Выбрать между ними
по этим данным нельзя, поэтому «beam ↔ 17» остаётся **не подтверждённым**, а не «подтверждённым
смещением». Остальные (`blk_waggon` 24, `blk_beam_down` 10, `blk_beacon_base` 13, `blk_mushroom` 9,
`blk_topdown_electro` 2) — `STABLE-for-all=NONE`.

**5. Лестница «а может, мы просто перепутали имя».** Наивный тест «N кортежей типа T ↔ N объектов
с именем X» проходит для **8 из 16** типов: `3, 5, 6, 7, 8, 9, 10, 15` (ровно то печатает раздел 8
скрипта: `8/16 -> [3, 5, 6, 7, 8, 9, 10, 15]`). Но координатно из этих восьми соединяется **один**
тип — 3 (`turret`=37): скрипт даёт `ALSO join on coordinates: 1 -> [3]`, то есть **7 из 8**
«1:1-совпадений по числу» — чистая коллизия чисел. Две из них откровенно абсурдны: тип 9
«sphere home» (48) «совпадает» с `ammo_pack` (48), а тип 15 «high voltage» (7) — с `ship` (7).
Ровно поэтому колонка «есть ли имя в TMX» в матрице
отделена от колонки «джойн»: `turret=37`, `mine=53`, `teleport=70`, `ammo_pack=48`,
`grenade_pack=38`, `piston=46` — валидные утверждения «имя ↔ данные», и невалидные утверждения
«тип документа ↔ эти данные».

**6. Итоговая честная фраза для отчёта.** 970 кортежей документа имеют доказанное объектом
подтверждение для **72 (7,4 %)**; 452 из 970 задекларированных кортежей принадлежат пяти типам,
которые вообще что-то соединяют, но и внутри них покрыто 72 из 452 (15,9 %); `solid=` — 0/125;
контрольный нерелевантный индекс даёт 3/370 (не 0/370), максимум 20/370 при самой выгодной
конвенции. Документ годится как **спецификация входа ASM-компилятора** и как **перекрёстная
проверка пяти семейств**; как доказательство соответствия 125 TMX оригиналу — не годится.

## Скрипт
`/tmp/lane-remap/join_measure.py` (в репозиторий не добавлен — решение о коммите за родителем;
ниже — та же копия, байт в байт).
Прогон: `python3 /tmp/lane-remap/join_measure.py <repo>` → exit 0, 8 разделов
вывода; ASCII-only, stdlib-only, ничего не пишет.

```
#!/usr/bin/env python3
"""join_measure.py - what `LEVEL_COMPILER_AUDIT.md` actually describes, measured
against the shipped `Exolon/Resources/*.tmx` maps and the Swift runtime that
reads them.

Read-only, stdlib only.  Usage:  python3 join_measure.py [repo-root]

Sections
  1  internal shape/consistency of the document (which field the header tallies)
  2  inventory of the shipped maps (names, provenance families, collision cells)
  2b reproducibility of the `solid=` column from the shipped maps
  3  what the Swift runtime actually dispatches on
  4  primary join: exact (sourceX,sourceY) == document (col,row) in the same zone
  5  control: same join attempted on an index that has no provenance coordinates
  6  affine-offset scan for families that do not join exactly
  7  corrected type -> data -> code matrix
  8  reverse direction (data/code without document names) + accidental count equality
"""
import base64
import collections
import glob
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
DOC = os.path.join(ROOT, "LEVEL_COMPILER_AUDIT.md")
RUNTIME = os.path.join(ROOT, "Exolon/GameCore/Levels/TMXLevelRuntime.swift")
GAMESCENE = os.path.join(ROOT, "Exolon/GameCore/GameScene.swift")
CELL = 16                      # both the document grid and the TMX tile size
RADIUS = 3                     # offset-scan window, in document cells

# The document carries no legend of any kind.  The only naming authority in the
# tree is the ordered action-family list in ORIGINAL_MECHANICS.md:170; the
# audited legacy table (engineering/reports/exolon-initial-audit.md:280-296)
# maps those names onto the document type codes positionally, ascending from 2.
LEGEND = ["torch", "gun machine", "flashing cell", "mine", "teleport",
          "white refill box", "yellow refill box", "sphere home", "pump",
          "rocket launcher", "changing room", "green guidance", "bonus trigger",
          "high voltage", "stage end", "beam"]

# ------------------------------------------------------------------ 1. the doc
txt = open(DOC, encoding="utf-8").read()
declared = {int(k): int(v) for k, v in
            (p.split("=") for p in
             re.search(r"Action counts: ([^\n]+)", txt).group(1).split(","))}
rows = re.findall(r"^(\d{3}) (L\d{2}S\d{2}) solid=(\d+) actions=(.*)$", txt, re.M)
assert len(rows) == 125, len(rows)

per_field = [collections.Counter(), collections.Counter(), collections.Counter()]
doc_index = collections.defaultdict(dict)          # zone -> (col,row) -> {type}
doc_solid = {}
tuples_total = 0
for _, zone, solid, actions in rows:
    doc_solid[zone] = int(solid)
    for tri in filter(None, actions.split(",")):
        x, y, t = (int(v) for v in tri.split(":"))
        for i, v in enumerate((x, y, t)):
            per_field[i][v] += 1
        doc_index[zone].setdefault((x, y), set()).add(t)
        tuples_total += 1

tally = [i for i in range(3) if per_field[i] == declared]
print("== 1. DOCUMENT ==")
print(f"  header tallies field #{tally} (0=col 1=row 2=type); sum(header)={sum(declared.values())} "
      f"body tuples={tuples_total}")
print(f"  field ranges col/row/type = {[(min(c), max(c)) for c in per_field]}")
print(f"  declared == body histogram per type: {all(declared[t] == per_field[2][t] for t in declared)}")
cells = sum(len(v) for v in doc_index.values())
print(f"  {tuples_total} tuples on {cells} distinct (zone,col,row) cells -> "
      f"{'no two tuples share a cell' if cells == tuples_total else 'collisions!'}")
print(f"  types present {sorted(declared)}; 0 and 1 never appear")
print(f"  screens with empty actions= {[z for (_, z, _, a) in rows if not a.strip()]}")
print(f"  doc cell span col {min(per_field[0])}..{max(per_field[0])} ({len(per_field[0])} distinct)"
      f" x row {min(per_field[1])}..{max(per_field[1])} ({len(per_field[1])} distinct);"
      f" the shipped TMX grid is 35x24 (section 2)")

# ------------------------------------------------------------ 2. shipped data
maps = sorted(glob.glob(os.path.join(ROOT, "Exolon/Resources/*.tmx")))
Obj = collections.namedtuple("Obj", "zone name x y w h props")
objs, geom = [], {}
for path in maps:
    root = ET.parse(path).getroot()
    zone = os.path.basename(path)[:-4]
    mw, mh = int(root.get("width")), int(root.get("height"))
    tw, th = int(root.get("tilewidth")), int(root.get("tileheight"))
    coll = next(l for l in root.iter("layer") if l.get("name") == "Collision")
    data = coll.find("data")
    # split exactly like TMXMapLoader.decodeLayerData does: on comma OR whitespace
    pieces = [v for v in re.split(r"[,\s]+", (data.text or "").strip()) if v]
    if data.get("encoding") == "csv":
        gids = [int(v) for v in pieces]
    else:
        blob = base64.b64decode("".join(pieces))
        gids = [int.from_bytes(blob[i:i + 4], "little") for i in range(0, len(blob), 4)]
    geom[zone] = (mw, mh, tw, th, sum(1 for g in gids if g), sum(1 for g in gids if g == 1), len(gids))
    for o in root.iter("object"):
        props = {p.get("name"): p.get("value") for p in o.iter("property")}
        objs.append(Obj(zone, o.get("name") or "", float(o.get("x", 0)), float(o.get("y", 0)),
                        float(o.get("width", 0)), float(o.get("height", 0)), props))

names = collections.Counter(o.name for o in objs)
fam = collections.Counter(o.props["sourceBlock"] for o in objs if o.props.get("sourceBlock"))
withxy = [o for o in objs if "sourceX" in o.props and "sourceY" in o.props]
control = [o for o in objs if o.props.get("sourceBlock")
           and not ("sourceX" in o.props and "sourceY" in o.props)]
print("\n== 2. SHIPPED DATA ==")
print(f"  maps={len(maps)} objects={len(objs)} map geometry={sorted({g[:4] for g in geom.values()})} "
      f"-> {max({g[0] for g in geom.values()})}x{max({g[1] for g in geom.values()})} cells")
print(f"  distinct object names={len(names)}: "
      + ", ".join(f"{k}={v}" for k, v in names.most_common()))
print(f"  distinct sourceBlock families={len(fam)}: "
      + ", ".join(f"{k}={v}" for k, v in fam.most_common()))
fam_by_name = {f: dict(collections.Counter(o.name for o in objs if o.props.get("sourceBlock") == f))
               for f in fam}
print(f"  provenance ladder: all objects={len(objs)} -> sourceBlock={sum(fam.values())} "
      f"-> +sourceX&sourceY={len(withxy)} -> provenance-less pool={len(control)}")
print("  family -> carrying TMX object name: "
      + "; ".join(f"{f}={fam_by_name[f]}" for f in sorted(fam)))

print("\n== 2b. solid= reproduction from the shipped Collision layer ==")
for label, i in (("nonzero cells", 4), ("gid==1", 5)):
    eq = [z for (_, z, _, _) in rows if geom[z][i] == doc_solid[z]]
    print(f"  {label}: equal to doc solid= on {len(eq)}/125 screens; "
          f"cell count per map={sorted({g[6] for g in geom.values()})}")

# ------------------------------------------------------------- 3. swift code
src = open(RUNTIME, encoding="utf-8").read()
body = src[src.index("func buildObjectsFromTMX"):]
switches = set(re.findall(r'^\s*case "([a-z_]+)":', body, re.M))
tokens = re.findall(r'source\.contains\("([^"]+)"\)', body)
noops = []
for tok in tokens:
    seg = body.split(f'source.contains("{tok}")', 1)[1].split("} else if", 1)[0]
    seg = seg.split("{", 1)[1] if "{" in seg else seg
    code = "\n".join(l for l in seg.splitlines() if l.strip() and not l.strip().startswith("//"))
    if re.fullmatch(r"\s*break\s*\}?\s*", code or " "):
        noops.append(tok)
scene = open(GAMESCENE, encoding="utf-8").read()
builder = body[:body.index("private func addDestructible")]
print("\n== 3. SWIFT RUNTIME ==")
print(f"  dispatch is by object NAME: {len(switches)} switch cases -> {sorted(switches)}")
print(f"  source_marker is sub-dispatched on 7 sourceBlock substrings: {tokens}")
print(f"  ...of which the branch body is a bare break (parsed, then discarded): {noops}")
for arr in ("stageExitMarkers", "forceFields", "sourceHazards", "changingRooms"):
    pop = len(re.findall(rf"{arr}\.append\(", builder))
    read = len(re.findall(rf"currentLevel\.{arr}\b", scene))
    print(f"  marker array {arr}: populated in builder={pop}, read by GameScene={read}")


def classify(o):
    """How the runtime treats one shipped object."""
    if o.name == "vitorc":
        return "spawn-marker (break by design)"
    if o.name == "source_marker":
        f = o.props.get("sourceBlock", "")
        if any(t in f for t in noops):
            return "code-ignored (explicit no-op)"
        if any(t in f for t in tokens):
            return "live"
        return "code-ignored (no branch, silent default)"
    return "live" if o.name in switches else "code-ignored (no case)"


# ------------------------------------------- 4. primary join (convention-free)
print("\n== 4. PRIMARY JOIN: exact (sourceX,sourceY) == document (col,row), same zone ==")
matched = []                                   # (type, obj)
for o in withxy:
    for t in doc_index.get(o.zone, {}).get((int(o.props["sourceX"]), int(o.props["sourceY"])), ()):
        matched.append((t, o))
print(f"  candidates={len(withxy)} objects -> exact matches={len(matched)} "
      f"objects, unmatched={len(withxy) - len({id(o) for _, o in matched})}")
dup_obj = [k for k, v in collections.Counter(
    (o.zone, o.props["sourceX"], o.props["sourceY"]) for o in withxy).items() if v > 1]
print(f"  injectivity: {len(withxy)} provenanced objects on {len(withxy) - len(dup_obj)} distinct "
      f"(zone,sourceX,sourceY) cells; doc side: {tuples_total} tuples on "
      f"{sum(len(v) for v in doc_index.values())} distinct (zone,col,row) cells; dup cells={dup_obj}")
per_fam = collections.defaultdict(collections.Counter)
for t, o in matched:
    per_fam[o.props["sourceBlock"]][t] += 1
for f in sorted(fam):
    n_xy = sum(1 for o in withxy if o.props["sourceBlock"] == f)
    if not n_xy:
        print(f"    {f:24s} total={fam[f]:3d} withXY=  0  (no provenance coords to join on)")
        continue
    print(f"    {f:24s} total={fam[f]:3d} withXY={n_xy:3d} exact={sum(per_fam[f].values()):3d} "
          f"types={dict(sorted(per_fam[f].items()))}")

# --------------------------------------- 5. control on a non-provenanced index
print(f"\n== 5. CONTROL: join the {len(control)} provenance-less objects on a GUESSED tile index ==")
results = {}
for label, rowfn in (("row=y/16 (Tiled top-left)", lambda o: int(o.y) // CELL),
                     ("row=(Hpx-y)/16 (bottom anchor, what worldBottomLeft does)",
                      lambda o: int((geom[o.zone][1] * geom[o.zone][3] - o.y) // CELL))):
    for dx in range(4):
        hit = [o for o in control if doc_index.get(o.zone, {}).get((int(o.x) // CELL - dx, rowfn(o)))]
        results[(label, dx)] = hit
        types = collections.Counter(t for o in hit for t in doc_index[o.zone][(int(o.x) // CELL - dx, rowfn(o))])
        print(f"    {label:52s} col-shift={dx}: {len(hit):3d}/{len(control)} "
              f"types={dict(sorted(types.items()))}")
naive = results[("row=y/16 (Tiled top-left)", 0)]
best = max(results.values(), key=len)
print(f"  the index the document was actually checked against (top-left, shift 0): "
      f"{len(naive)}/{len(control)} accidental, {len(control) - len(naive)}/{len(control)} clean")
for o in naive:
    key = (int(o.x) // CELL, int(o.y) // CELL)
    print(f"    {o.zone}/{o.name} x={o.x:.0f} y={o.y:.0f} {o.props['sourceBlock']} "
          f"-> guessed tile {key} hits type {sorted(doc_index[o.zone][key])}")
print(f"  most favourable convention to a false join: {len(best)}/{len(control)} "
      f"({100.0 * len(best) / len(control):.1f}%)")

print("  specificity controls on the PRIMARY join (both must collapse):")
shift = sum(1 for o in withxy if doc_index.get(o.zone, {}).get(
    (int(o.props["sourceX"]) + 1, int(o.props["sourceY"]) + 1)))
zones = sorted(geom)
cross = sum(1 for o in withxy if doc_index.get(
    zones[(zones.index(o.zone) + 1) % len(zones)], {}).get(
    (int(o.props["sourceX"]), int(o.props["sourceY"]))))
print(f"    (sourceX+1, sourceY+1) in the same zone : {shift}/{len(withxy)}")
print(f"    unchanged coords in the neighbouring zone: {cross}/{len(withxy)}")
print(f"    unchanged coords in the own zone          : {len(matched)}/{len(withxy)}")

# ------------------------------------------------ 6. affine offset scan
print(f"\n== 6. OFFSET SCAN +-{RADIUS} cells for provenanced families without exact joins ==")
for f in sorted(fam):
    pool = [o for o in withxy if o.props["sourceBlock"] == f]
    if not pool or per_fam[f]:
        continue
    near = collections.Counter()
    all_found = collections.Counter()
    for o in pool:
        sx, sy = int(o.props["sourceX"]), int(o.props["sourceY"])
        found = [(t, ddx, ddy) for ddx in range(-RADIUS, RADIUS + 1) for ddy in range(-RADIUS, RADIUS + 1)
                 for t in doc_index.get(o.zone, {}).get((sx + ddx, sy + ddy), ())]
        all_found.update(found)
        near[collections.Counter(found).most_common(1)[0][0] if found else "no-neighbour-in-window"] += 1
    stable = sorted(k for k, v in all_found.items() if v == len(pool))
    print(f"    {f:24s} n={len(pool):3d} nearest={dict(near)} "
          f"STABLE-for-all={stable or 'NONE'}")

# ----------------------------------------------------- 7. corrected matrix
print("\n== 7. MATRIX  doc type -> inherited name -> shipped data -> code -> verdict ==")
by_type = collections.defaultdict(list)
for t, o in matched:
    by_type[t].append(o)
count_eq = collections.defaultdict(list)   # types whose declared count equals some TMX name count
for t in declared:
    count_eq[t] = sorted(n for n, c in names.items() if c == declared[t])
print(f"  {'type':>4} {'inherited name':17} {'doc':>4} {'join':>4} {'families':44} "
      f"{'live':>4} {'no-op':>5} {'drop':>4} {'count==name':14} verdict")
verdicts = collections.Counter()
for i, t in enumerate(sorted(declared)):
    osh = by_type[t]
    fams = collections.Counter(o.props["sourceBlock"] for o in osh)
    cls = collections.Counter(classify(o) for o in osh)
    live = sum(v for k, v in cls.items() if k == "live")
    noop = sum(v for k, v in cls.items() if k.startswith("code-ignored (explicit"))
    drop = sum(v for k, v in cls.items() if "silent" in k or "no case" in k)
    if not osh:
        v = "no data (name-only at best)" if count_eq[t] else "no data"
    elif live == len(osh):
        v = "verified join + live code"
    elif live:
        v = "verified join, partially live"
    else:
        v = "verified join, code-ignored data"
    verdicts[v] += 1
    print(f"  {t:>4} {LEGEND[i]:17} {declared[t]:>4} {len(osh):>4} "
          f"{str(dict(fams)):44} {live:>4} {noop:>5} {drop:>4} "
          f"{(','.join(count_eq[t]) or '-')[:14]:14} {v}")
print(f"  verdict distribution: {dict(verdicts)}")

# ------------------------------------------------------ 8. reverse direction
print("\n== 8. REVERSE DIRECTION ==")
joined_types = {t for t, v in by_type.items() if v}
print(f"  document types with >=1 verified join : {sorted(joined_types)} "
      f"(declared {sum(declared[t] for t in joined_types)} of {sum(declared.values())} tuples)")
print(f"  document types with ZERO join        : {sorted(set(declared) - joined_types)}")
noj = sorted(f for f in fam if not per_fam[f])
print(f"  sourceBlock families with ZERO join ({len(noj)}/{len(fam)}): {noj}")
print(f"  TMX object names with no Swift case  : {sorted(set(names) - switches)}")
print(f"  Swift cases with no shipped data     : {sorted(switches - set(names))}")
dropped = [o for o in objs if classify(o).startswith("code-ignored")]
print(f"  shipped objects the code ignores     : {len(dropped)} "
      f"{dict(collections.Counter(o.props.get('sourceBlock') or o.name for o in dropped).most_common())}")
nosrc = [o for o in objs if o.name != "vitorc" and not o.props.get("sourceBlock")]
print(f"  gameplay objects with NO provenance  : {len(nosrc)} "
      f"{dict(collections.Counter(o.name for o in nosrc).most_common())}")
print('  accidental equality control - the naive "N == N" test on names:')
naive_ok = [t for t in declared if count_eq[t]]
print(f"    types whose declared count equals at least one TMX object-name count: "
      f"{len(naive_ok)}/16 -> {naive_ok}")
print(f"    of those, how many ALSO join on coordinates: "
      f"{len([t for t in naive_ok if t in joined_types])} -> "
      f"{sorted([t for t in naive_ok if t in joined_types])}")
print(f"    => {len([t for t in naive_ok if t not in joined_types])} of the "
      f'"count == count" claims are pure number collisions, not joins')
```

Вердикт: fail
