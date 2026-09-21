# Матрица соответствия механик `ORIGINAL_MECHANICS.md` ↔ код ↔ данные

Лейна: READ-ONLY аудит фидельности. Репозиторий `<repo>`, HEAD `52795d13d879ad477a3023cae69978436ff82d1a`.

## Как считалось

- Реализация: 18 Swift-файлов, 4227 строк (`find . -name '*.swift' -not -path './.git/*' -exec wc -l {} +`), 125 TMX (`find . -name '*.tmx' | wc -l`).
- Каждый TMX-объект несёт либо игровое имя (`turret`, `mine`, …), либо `source_marker` со свойством `sourceBlock`. Всего 515 объектов с `sourceBlock`: 127 на `source_marker`, 388 — на именованных игровых объектах (перебор всех 125 TMX; сверено дважды — `/tmp/lane-mechanics/join2.py` и независимый пообъектный подсчёт).
- Второй независимый источник по данным: `LEVEL_COMPILER_AUDIT.md` — оригинальная таблица из **970** action-ячеек (строки `NNN LxxSyy solid=… actions=…`, формат `sourceX:sourceY:ActionID`). Заголовок `Action counts:` сходится с перегруппировкой построчно (970 = 970).
- Первичный статус берётся из `ORIGINAL_MECHANICS.md`; формулировки README шага 9 проверяются отдельно (§20).
- Статусы: `реализован` / `частичен` / `отсутствует` / `противоречит`. Пометка `нужен macOS` — требуется плейтест, статически не доказывается.
- Находка C1 (пол кабины) здесь не рассматривается и нигде не пересматривается.

## Итог

Посчитано скриптом по колонке «Статус» таблиц §1-§20 (`/tmp/lane-mechanics/final_census.py`; ячейки режутся по ` | `, чтобы экранированные `\|` внутри `code span` не ломали столбцы):

| Статус | Строки |
|---|---|
| реализован | 86 |
| частичен | 27 |
| отсутствует | 21 |
| противоречит | 17 |
| **Всего** | **151** |

Нумерация строк 1-151 непрерывна, дублей нет. Помечено `нужен macOS`: 18 строк (9, 22, 29, 45, 53, 63, 70, 73, 90, 95, 99, 104, 105, 114, 116, 117, 119, 147). Разбивка по подразделам: §1=9, §2=7, §3=6, §4=5, §5=4, §6=4, §7=10, §8=4, §9=4, §10=6, §11=9, §12=5, §13=3, §14=8, §15=6, §16=5, §17=9, §18=15, §19=17, §20=15.

Краткое содержание дефектов: 32 из 125 зон (объединение по трём типам) содержат маркеры, на которые Swift не создаёт ровно ничего (`TMXLevelRuntime.swift:351-407`, `default:` на `:409` — «Unknown objects are intentionally ignored»): нижние gun machines (18 маркеров, 15 зон), `blk_waggon` (24 маркера, 14 зон), `blk_mushroom` (9 маркеров, 6 зон). Четыре механики, которые док требует явно, отсутствуют целиком: стреляющая ракетная бонус-секвенция преследователя (таймер 700 + несъедобный истребитель), bravery-бонус 10 000, timed bonus cursor, сброс экзоскелета на границе стадии. 29 объектов `rocket` в 15 зонах (из них 23 несут `blk_tower_rocket`, 12 зон) — это статика, а не башня, и бластер в них гаснет, хотя док требует сбивать их за 50.

## Матрица механик

### 1. Глобальная структура (§Global structure)

| # | Механика по доку | Статус | Код | Данные / проверка |
|---|---|---|---|---|
| 1 | 125 зон `000…124`, пять стадий по 25 | реализован | `GameScene.swift:53` (`includedLevels`), `:988-996` (`zoneNumber`) | 125 TMX; `nextLevel`-цепочка L01S01→…→L05S25 без разрывов, у `L05S25` свойства нет |
| 2 | Экраны сменяются дискретно, без прокрутки | реализован | камер/скролла нет: `grep -rni "camera\|scroll" Exolon/` — пусто; `Player.swift:127-128` кламп; `GameScene.swift:610` | все 125 карт `35×24` тайла = 560×384 при логических 512×384 (`GameConstants.swift:4`) ⇒ 3 колонки тайлов за кадром |
| 3 | Обычный вход на экран без неуязвимости | реализован | `GameScene.swift:649` (`invulnerability = 0` в `transition`) | — |
| 4 | Новая игра: 9 жизней, 99 выстрелов, 10 гранат | реализован | `GameState.swift:81-83`, `:85-88`, `:93-99` | HUD: `HUDNode.swift:57-63` |
| 5 | Смерть снимает жизнь и делает refill 99/10 | реализован | `GameScene.swift:322`, `:330-331` | — |
| 6 | После смерти оригинал **пересобирает текущую зону** | противоречит | `GameScene.swift:311-336`: зона не пересобирается, `clearTransientObjects()` там не вызывается; комментарий `:328-329` «Destroyed objects remain destroyed» | `clearTransientObjects()` (`:999-1010`) вызывается только из `transition` (`:634`) и `restartFromBeginning` (`:953`) |
| 7 | Новая зона снимает активные пули, гранаты, врагов, мины, ракеты, буферы сфер, транзиенты | реализован | `GameScene.swift:633-638` + `:999-1010`; на каждый экран конструируется новый `TMXLevelRuntime` | `mines`/`eggs`/`bubbles`/`homingMissiles` живут в рантайме зоны ⇒ обнуляются вместе с ней |
| 8 | TEST INVULNERABILITY — сознательно не-оригинал | реализован | `GameScene.swift:186-188` (пауза-меню), `:601-602` (`guard !testInvulnerabilityEnabled`) | метка `:106-116` |
| 9 | Post-death защита 0.4 с (в доке не описана) | частичен | `GameConstants.swift:10`, `GameScene.swift:333` | нужен macOS |

### 2. Бластер (§Player weapons / Blaster)

| # | Механика по доку | Статус | Код | Данные / проверка |
|---|---|---|---|---|
| 10 | Конечный боезапас | реализован | `GameScene.swift:340-351` | `AmmoPackPickup` в 48 зонах |
| 11 | Рядовые раунды сбивают плавающих врагов, сферы и ракеты | реализован | `GameScene.swift:383-389` (bubble), `:391-397` (egg), `:373-381` (снаряд лаунчера) | — |
| 12 | Пули неподвижной турели не сбиваются | реализован | `LevelObstacles.swift:141` (`canBeShotDown = false`) | — |
| 13 | Снаряды дабл-лаунчера сбиваются и дают 50 | реализован | `LevelObstacles.swift:147-153` (`pointsWhenShotDown = 50`); `GameScene.swift:373-381` | 19 объектов `double_launcher` |
| 14 | Вертикальное поле считает попадания, гаснет на 25-м, award 1000 | реализован | `LevelObstacles.swift:766` (`hitPoints = 25`), `:777-789`; `GameScene.swift:399-405` | 20 маркеров `blk_beam_up/down` в 10 зонах |
| 15 | Твёрдый рельеф и разрушаемые преграждают огонь | реализован | `GameScene.swift:407-417` | `solidRects` `TMXLevelRuntime.swift:124-129` |
| 16 | Скорость и дальность раунда (док не задаёт) | частичен | `BlasterBullet.swift:14-15` (360 px/с, 210 px, взято из HTML5-ремейка) | оригинальные константы недоступны: `rusarh/exolon-esl` в дереве нет (`find . -name '*.asm'` — пусто) |

### 3. Граната (§Grenade)

| # | Механика по доку | Статус | Код | Данные / проверка |
|---|---|---|---|---|
| 17 | GRENADE отдельной кнопкой вместо удержания FIRE 15 тиков | реализован | `GameScene.swift:338-360`, комментарий `:339` | санкционированное доком отступление; `GameView.swift:57`, `GameView.swift:62`, `GamepadInput.swift:59`, `GamepadInput.swift:83` |
| 18 | Одна активная граната | реализован | `GameScene.swift:355` (`grenades.isEmpty`) | — |
| 19 | Фиксированная фазовая таблица, не «generic ballistic» | реализован | `Grenade.swift:53-77` (`rising` → `glide` 30 тиков → `dive`) | константы 1.5/3.3/0.2/5.5/0.1 на `Grenade.swift:23` |
| 20 | Контакт с рельефом/преградой/границей → деактивация и проверка таблицы разрушаемых | реализован | `GameScene.swift:427-471` | порядок: турель→преграда→инкубатор→маяк→рельеф/земля |
| 21 | Универсальный разрушаемый объект = 150 очков | реализован | `GameScene.swift:481-488` (`awardPoints(150)`) | — |
| 22 | Взрыв гранаты проверяет таблицу (зона поражения, а не point-overlap) | частичен | `GameScene.swift:437-471` — только пересечение хитбокса 10×10 (`Grenade.swift:41-43`) | нужен macOS |

### 4. Неподвижная gun machine (§Stationary gun machine)

| # | Механика по доку | Статус | Код | Данные / проверка |
|---|---|---|---|---|
| 23 | Случайный ритм «from the original RNG» | частичен | `LevelObstacles.swift:98-102` (`Int.random(50...300)/60`) | оригинальный ГПСЧ ZX не портирован, seed-воспроизводимость отсутствует |
| 24 | Происхождение пули: `turret.left + 2`, `turret.bottom + 56` | реализован | `LevelObstacles.swift:76-82` — буквально `hitbox.minX + 2`, `hitbox.minY + 56` | точное совпадение с формулировкой дока |
| 25 | Пули идут влево и не сбиваются бластером | реализован | `LevelObstacles.swift:140-141` (`speed = -300`) | — |
| 26 | Турель разрушается гранатой, 150 очков | реализован | `GameScene.swift:437-442` + `:481-488` | 37 объектов `turret` в 33 зонах |
| 27 | **Нижняя турель** (`blk_gunMachine_BOTTOM`) | противоречит | `TMXLevelRuntime.swift:351-407`: ветки для gun machine в `source_marker` нет, маркер уходит в `default:` `:409` | 18 маркеров, все на голых `source_marker`, 0 рантайм-объектов; затронуто 15 зон: 23, 32, 45, 46, 53, 57, 61, 71, 73, 78, 81, 97, 107, 120, 121 |

### 5. Дабл-баррель лаунчер (§Double-barrel launcher)

| # | Механика по доку | Статус | Код | Данные / проверка |
|---|---|---|---|---|
| 28 | Огонь из двух разнесённых по вертикали стволов | реализован | `LevelObstacles.swift:713-715` (`barrelY = 40 or 24`) | 18 маркеров `blk_double_barrel` |
| 29 | Прекращает огонь, когда Vitorc слишком близко | реализован | `LevelObstacles.swift:701-704` (`distance > 110`) | нужен macOS (метрика — по левому краю, не по центру) |
| 30 | 16×16 снаряды идут влево, сбиваются бластером, 50 очков | реализован | `LevelObstacles.swift:145-153` | — |
| 31 | Пересечение невидимой бонус-области даёт 1000 ровно один раз | частичен | `LevelObstacles.swift:718-723`; `TMXLevelRuntime.swift:219-223`; `GameScene.swift:299-303` | «область» = хитбокс самого корпуса 64×48 (`LevelObstacles.swift:695`), отдельного невидимого региона в данных нет; при этом взятие бонуса ставит `isActive = false` и орудие навсегда перестаёт стрелять — док такого не требует |

### 6. Rocket tower (§Rocket tower)

| # | Механика по доку | Статус | Код | Данные / проверка |
|---|---|---|---|---|
| 32 | Башня случайно стреляет, только пока игрок далеко (порог 30) | противоречит | нет ни одного места: `grep -rni "tower" Exolon/ --include=*.swift` — 4 совпадения, все в комментариях про guidance tower (`TMXLevelRuntime.swift:38, 102, 383, 384`); `EnemyTurretBullet.Kind` знает лишь `.turret`/`.doubleLauncher` (`LevelObstacles.swift:116-119`), типа снаряда «rocket» нет | 23 маркера `blk_tower_rocket` в 12 зонах (9, 10, 18, 21, 23, 40, 44, 55, 66, 84, 115, 119) сводятся к **статическому** `DestructibleObstacle` (`TMXLevelRuntime.swift:264-269`) — ровно тот случай, который запрещает правило аудита дока («механика не считается реализованной из-за спрайта на фоне») |
| 33 | Скорость ракеты −2, полёт влево | отсутствует | — | типа снаряда «rocket» не существует |
| 34 | Ракеты сбиваются бластером и дают 50 | отсутствует | `GameScene.swift:366-425` — ветки нет | хуже: `rocket` входит в `hitIndestructible` (`:407-415`), то есть бластер об него гаснет |
| 35 | Столкновение ракеты с игроком убивает | отсутствует | `GameScene.swift:538-597` — перебора ракет-снарядов нет | — |

### 7. Green missile-guidance beacon (§Green missile-guidance beacon)

| # | Механика по доку | Статус | Код | Данные / проверка |
|---|---|---|---|---|
| 36 | Блок 31, явно разрушается гранатой | реализован | `TMXLevelRuntime.swift:394-406`; `GameScene.swift:458-467` | 13 маркеров `blk_control_beacon`, у всех есть `sourceX/sourceY` |
| 37 | Пока маяк жив — активна ровно одна ракета | реализован | `TMXLevelRuntime.swift:169-176` (гейт `homingMissiles.isEmpty`) | — |
| 38 | Старт справа; ускорение после X=70 → X=280 | реализован | `LevelObstacles.swift:846`, `:858-861`; `:832-833` (90→180 px/с = 1.5→3 px/тик) | порог ровно 280, как в доке |
| 39 | Каждый тик — шаг по вертикали на 1 к текущему Y игрока | реализован | `LevelObstacles.swift:834`, `:866-871` (`verticalSpeed = 60` = 1 px/тик); цель — `TMXLevelRuntime.swift:178` | — |
| 40 | ракету нельзя сбить бластером напрямую | реализован | `GameScene.swift:366-425` — `homingMissiles` среди целей пули отсутствует | — |
| 41 | Граната по маяку немедленно снимает активную ракету | реализован | `TMXLevelRuntime.swift:193-206` | — |
| 42 | 150 за маяк + 850 за снятую ракету = 1000 | реализован | `TMXLevelRuntime.swift:205` (`150 + (positions.isEmpty ? 0 : 850)`) | — |
| 43 | После разрушения маяка основание перестаёт блокировать проход | реализован | `TMXLevelRuntime.swift:101-110`, `:380-393`, `subtract(rect:removing:)` `:447-486` | 13 маркеров `blk_beacon_base` |
| 44 | Обязательная механика Zone 008 | реализован (по данным) | строки 36-43 | `L01S09` (zone 008): `blk_control_beacon`×1, `blk_beacon_base`×1, 2 `teleport`, `incubator` |
| 45 | Проход Zone 008 гранатой реально возможен на геймпаде/клавиатуре | частичен | код маяка и ракеты готов (строки 36-43) | нужен macOS |

### 8. Мины (§Mines)

| # | Механика по доку | Статус | Код | Данные / проверка |
|---|---|---|---|---|
| 46 | Триггер от узкой горизонтальной/foot-области, не от произвольного оверлея | реализован | `LevelObstacles.swift:746-752` (`minX−10`, `width+20`, `height 28` от базы) | 53 объекта `mine` (50 с `blk_mine`) в 24 зонах |
| 47 | После срабатывания мина переходит в spent/взрывное состояние | частичен | `LevelObstacles.swift:753-754` — `isArmed = false` + `node.removeFromParent()`; spent-спрайта нет, эффект дорисовывает сцена (`GameScene.swift:549`) | — |
| 48 | Обычный игрок гибнет; урон идёт через `KillPlayer_unless_Exoskeleton` | частичен | `GameScene.swift:545-554`: при экзоскелете `continue` **до** триггера | семантика оригинала — мина детонирует, но не убивает; здесь она не детонирует вовсе и остаётся взведённой |
| 49 | Zone 007 — первые мины | реализован (по данным) | строки 46-48 | `L01S08` (zone 007): `mine`×3; в зонах 000-006 мин нет (перебор `grep -c 'name="mine"' L01S0[1-7].tmx` = 0) |

### 9. Насосы / крашеры (§Pumps / crushers)

| # | Механика по доку | Статус | Код | Данные / проверка |
|---|---|---|---|---|
| 50 | Скрыт → вход в игровую область по оригинальному счётчику фаз → пауза → уход | частичен | `LevelObstacles.swift:311-388`; `waitDuration = Int.random(60...300)/60` (`:331`, `:383`) | фазы `waiting/rising/exposed/falling` есть; «original phase counter» заменён случаем, синхронности между насосами нет |
| 51 | Контакт в активной фазе убивает обычного игрока | реализован | `GameScene.swift:556-565` + `LevelObstacles.swift:341-346` (хитбокс только по видимой части) | — |
| 52 | Иммунитет экзоскелета | реализован | `GameScene.swift:557` | — |
| 53 | §Pumps называет объект «crushers»: движение в игровую область должно взаимодействовать с телом игрока | частичен | `TMXLevelRuntime.swift:124-129` — `pistons` не входят в `solidRects`, тело не выталкивается и не блокируется | док не формулирует это отдельным требованием; засчитано как частичное покрытие §Pumps, а не как отдельная отсутствующая механика; нужен macOS |

### 10. Sphere homes / birthpods (§Sphere homes / birthpods)

| # | Механика по доку | Статус | Код | Данные / проверка |
|---|---|---|---|---|
| 54 | Каждый дом инициализирует 8 сфер | реализован | `LevelObstacles.swift:518`, `:539` (`for index in 0..<8`) | 22 объекта `incubator` (21 с `blk_birthpod`) в 18 зонах |
| 55 | Ёмкость движка — 24 сферы | отсутствует | `TMXLevelRuntime.swift:317-320` — append без капа | максимум в данных — 2 инкубатора в зоне (зоны 40, 65, 94, 115) = 16 сфер; инвариант «24» не защищён кодом |
| 56 | Отскоки по горизонтали от границ/рельефа, случайные смены по вертикали | реализован | `LevelObstacles.swift:608-672` (`:625-639` рельеф/границы, `:663-666` случайные инверсии) | — |
| 57 | Попадание бластером уничтожает сферу, 50 очков | противоречит | `GameScene.swift:391-397` идёт **раньше** проверки `hitIndestructible`/`incubators` (`:407-415`) | сфера сбивается насквозь сквозь целый контейнер, то есть до «релиза» — против §Zone 005 |
| 58 | Контакт сферы убивает игрока и уничтожает сферу | реализован | `GameScene.swift:590-597` | плюс незапрошенные 50 очков за самоубийство (`:593`) |
| 59 | Container релизит сферы только после разрушения | реализован | `LevelObstacles.swift:551-553`, `:604-606` | — |

### 11. Летающие враги (§Flying enemies)

| # | Механика по доку | Статус | Код | Данные / проверка |
|---|---|---|---|---|
| 60 | Появляются не везде, по явному списку зон (`tab_enemy`) | частичен | `TMXLevelRuntime.swift:308-311` | 31 `bubble_creator` в 18 зонах; сверить со `tab_enemy` невозможно — `rusarh/exolon-esl` в репозитории отсутствует |
| 61 | Шесть точных таблиц траекторий, «must be ported literally, not replaced by generic homing/patrol AI» | противоречит | `LevelObstacles.swift:477-495` — три аналитические ветки: `circular` (`cos`), `zig_zag` (`sin`), default `swing` (`sin(x/20)` + `Double.random(1...3)`) | в данных только `behavior="swing"` (28) либо свойство отсутствует (3 → default `swing`); `circular`/`zig_zag` — мёртвые ветки, шести таблиц нет ни в коде, ни в данных |
| 62 | Максимум шесть активных слотов | отсутствует | `TMXLevelRuntime.swift:145-152` — append без капа; `grep "bubbles.count\|maxActive"` — пусто | — |
| 63 | Старт справа X=120, Y от Y игрока (≈10 выше ИЛИ Y+random 0…15) | частичен | `LevelObstacles.swift:417-423` (`x = 528 + 0…32`, `y = player.y + 2 − 0…16`) | реализован только один из двух режимов Y (всегда выше); константы из reference-ремейка, ×4-конверсия дока (120→480) не соблюдена; нужен macOS |
| 64 | Нет спавна, если X игрока ≥ 84 (original units) | частичен | `LevelObstacles.swift:414` (`player.position.x <= 320`) | при ×4 (той же, что `X=70→280`) ожидалось 336 |
| 65 | Убийство бластером = 150 | реализован | `LevelObstacles.swift:432`; `GameScene.swift:383-389` | — |
| 66 | Контакт убивает игрока и удаляет врага | реализован | `GameScene.swift:580-588` | плюс незапрошенные 150 очков (`:583`) |
| 67 | Зона выбирает семейство спрайта | противоречит | `LevelObstacles.swift:449` (`Int.random(in: 0..<6)` — случайный ряд цвета листа `bubble.png`) | свойства `family` в данных нет ни у одного `bubble_creator` |
| 68 | Зона выбирает spawn delay | частичен | `TMXLevelRuntime.swift:309` (свойство читается) | во всех 28 маркированных creator стоит `delay=1.0`, вариации по зонам нет |

### 12. Телепорты (§Teleports)

| # | Механика по доку | Статус | Код | Данные / проверка |
|---|---|---|---|---|
| 69 | Никогда автоматически | реализован | `GameScene.swift:229-244` — только по фронту нажатия | — |
| 70 | Встать в портал и нажать UP; одно нажатие, удержание не ретриггерит | реализован | `GameScene.swift:229`, `:251-252`; `Player.swift:256-258` (`consumeContextualJumpPress`); `LevelObstacles.swift:296-299` (`fullyContains`) | нужен macOS (ощущение «правильной выравнивания») |
| 71 | Пункт назначения — парный портал, маленький X-сдвиг, партиклы | реализован | `TMXLevelRuntime.swift:226-232`; `LevelObstacles.swift:290` (`+24/+32`); `GameScene.swift:1024-1037` | гистограмма порталов: 90 карт — 0, 35 карт — ровно 2, 1 или 3+ нет ⇒ `(index+1) % count` корректен на всех данных |
| 72 | Zone 002 — первый парный телепорт | реализован (по данным) | строки 69-71 | `L01S03` (zone 002): `teleport`×2 |
| 73 | Zone 059 — телепорт, чтобы достать/сломать маяк | реализован (по данным) | строки 36-43 | `L03S10` (zone 059): `teleport`×2 + `blk_control_beacon` + `blk_beacon_base`; нужен macOS |

### 13. Ящики боеприпасов (§Ammo / grenade boxes)

| # | Механика по доку | Статус | Код | Данные / проверка |
|---|---|---|---|---|
| 74 | Белый ящик выставляет ровно 99 и исчезает | реализован | `GameScene.swift:522-536` (`gameState.ammo = 99`); `LevelObstacles.swift:230-250` | 48 `ammo_pack`, из них 46 с `blk_box_white` |
| 75 | Жёлтый ящик выставляет ровно 10 гранат и исчезает | реализован | `GameScene.swift:522-528` (`gameState.grenades = 10`); `LevelObstacles.swift:208-228` | 38 `grenade_pack`, из них 35 с `blk_box_yellow` |
| 76 | Это refill, а не additive pickup | реализован | присваивание, не `+=` | — |

### 14. Экзоскелет / раздевалка (§Exoskeleton / changing room)

| # | Механика по доку | Статус | Код | Данные / проверка |
|---|---|---|---|---|
| 77 | Встать в раздевалку и нажать UP, edge-triggered | реализован | `GameScene.swift:233-238` | 5 раздевалок: 1 `capsule` (zone 009) + 4 `blk_changing_room` (зоны 34, 60, 90, 109) |
| 78 | Переключает состояние экзоскелета | реализован | `Player.swift:243-246` | — |
| 79 | Меняет спрайт-сет игрока | противоречит | `PlayerSpriteNode.swift:44-46` — только `color = .cyan`, `colorBlendFactor = 0.35` на том же листе из 11 кадров; комментарий прямо называет это «Temporary visual cue until the original exoskeleton frames are wired as a second sheet» | второй спрайт-сет не заведён |
| 80 | Двойной бластер-огонь | реализован | `GameScene.swift:346-350` (второй снаряд, +12 px по Y) | 13 потяжек × 2 = 26 ≥ 25 ⇒ сходится с §Vertical force field |
| 81 | Иммунитет к опасностям `KillPlayer_unless_Exoskeleton` | частичен | `GameScene.swift:546` (мины), `:557` (насосы) | см. строку 48: мина при костюме вообще не детонирует |
| 82 | Переживает смерти | реализован | `Player.swift:227-240` — `respawn()` флаг не трогает | — |
| 83 | Сбрасывается в конце текущей 25-зонной стадии | отсутствует | `GameScene.swift:622-631` — сброса нет; единственный `setExoskeleton(false)` — `:963` в `restartFromBeginning` | против §Exoskeleton «At stage end the exoskeleton flag is cleared» |
| 84 | Наличие костюма лишает bravery-бонуса 10 000 | отсутствует | `grep -rni "bravery\|10_000\|10000" Exolon/` — пусто | бонуса нет вообще |

### 15. Вертикальное силовое поле (§Vertical force field)

| # | Механика по доку | Статус | Код | Данные / проверка |
|---|---|---|---|---|
| 85 | Тянется от маркера до следующей no-walk клетки | противоречит | `TMXLevelRuntime.swift:356-359` — жёсткий прямоугольник `48 × 272`, `y = max(0, bottomY − 240)`; `blk_beam_up` и `blk_beam_down` дают одинаковую рамку, направление не учитывается | пересчёт по всем 10 «beam»-зонам: up и down пересекаются на 32×160 px (`/tmp/lane-mechanics/forcefield.py`) ⇒ из-за `forceFields.first(where:)` (`GameScene.swift:399`) вторая рамка почти не получает попаданий |
| 86 | Касание летально | реализован | `GameScene.swift:568-571` | — |
| 87 | Ровно 25 попаданий бластером (13 потяжек двойного выстрела) | реализован | `LevelObstacles.swift:766`, `:777-789` | — |
| 88 | Разрушение даёт 1000 | реализован | `GameScene.swift:401-404` | — |
| 89 | Граната — не обходной путь | реализован | `GameScene.swift:427-471` — ветки для `forceFields` нет | точное соответствие доке |
| 90 | Zone 035 — поле на 25 попаданий проходима | частичен | строки 85-88 | `L02S11` (zone 035): `blk_beam_up` + `blk_beam_down`; нужен macOS |

### 16. Таймер + несъедобный преследователь (§Timed indestructible pursuer)

| # | Механика по доку | Статус | Код | Данные / проверка |
|---|---|---|---|---|
| 91 | Порог 700 циклов на зону | отсутствует | `grep -rni "700\|zoneTimer\|pursuer\|fighter" Exolon/` — ни одного совпадения (exit 1) | таймера зоны нет вообще |
| 92 | После задержки справа появляется несъедобный истребитель на Y игрока | отсутствует | — | ни класса, ни спавнера, ни данных |
| 93 | Быстро идёт влево, касание убивает, сбить нельзя | отсутствует | — | — |
| 94 | У левого края удаляется, потом повтор; таймер сбрасывается новой зоной/смертью | отсутствует | — | — |
| 95 | ~20-30 секунд на оригинальном железе | отсутствует | — | нужен macOS (замерить нечего) |

### 17. Финалы стадий (§Stage ends: Zones 024/049/074/099/124)

| # | Механика по доку | Статус | Код | Данные / проверка |
|---|---|---|---|---|
| 96 | Достижение триггера конца стадии открывает бонус-секвенцию | противоречит | `TMXLevelRuntime.swift:369-370` заполняет `stageExitMarkers`, но нигде их не читает (`grep -rn stageExitMarkers Exolon/` → только объявление `:30` и append); выход — только `player.position.x > 510` (`GameScene.swift:610`) | 5 маркеров `blk_stage_end` в зонах 24, 49, 74, 99, 124 — данные есть, рантайм их игнорирует |
| 97 | 1000 очков за каждую оставшуюся жизнь | реализован | `GameScene.swift:627` | — |
| 98 | 10 000 bravery, если костюм не брали | отсутствует | — | строка 84 |
| 99 | Timed bonus cursor 0/1000/3000/5000/7000 | отсутствует | `GameScene.swift:622-631` — ни курсора, ни оверлея | нужен macOS для подтверждения |
| 100 | +1 жизнь с капом 9 | реализован | `GameScene.swift:628` (`if gameState.lives < GameState.startingLives`) | — |
| 101 | Сброс экзоскелета | отсутствует | — | строка 83 |
| 102 | Восстановление 99/10 | реализован | `GameScene.swift:629-630` | — |
| 103 | Стартовые позиции стадий: 000 (16,112), 025 (0,120), 050 (0,32), 075 (40,128), 100 (16,112) | противоречит | спавн берётся из TMX-объекта `vitorc` (`TMXLevelRuntime.swift:59-68`); stage-start обрабатывается в `GameScene.swift:642-645` | фактические Tiled-координаты: zone 000 → x=64,y=288; зоны 025, 050, 075, 100 → **одинаковые** x=0,y=320. При ×4 (та же, что `X=70→280` в доке) для 000 выходит 64 ✓, но для 075 ожидалось 160, для 100 — 64 ✗; четыре разных оригинальных Y схлопнуты в один |
| 104 | Zone 124: FULL COMBAT ABILITY, затем возврат в начало | частичен | `GameScene.swift:744-752` показывает `FULL COMBAT ABILITY`; дальше `:761-767` → title, а `beginFromTitle` (`:708-717`) не перезапускает игру и не сбрасывает состояние | `L05S25` не имеет `nextLevel` ⇒ `enterContentComplete` достигается ✓; фактического «вернуть в начало» нет (только пауза→RESTART, `:950`); нужен macOS |

### 18. Walkthrough-чекпоинты (§Walkthrough checkpoints that must work exactly)

| # | Чекпоинт | Статус | Код | Данные / проверка |
|---|---|---|---|---|
| 105 | Zone 000: гранатой снести стартовую турель/камни | реализован (по данным) | `GameScene.swift:437-456` | `L01S01`: `turret`×1 + `cocoon`×1 + `ship`/`gate`; нужен macOS |
| 106 | Zone 002: UP активирует пару-телепорт | реализован | строки 69-71 | `L01S03`: `teleport`×2 |
| 107 | Zone 003: первый «табличный» летающий враг | противоречит | строка 61 | `L01S04`: `bubble_creator`×1, но логика не табличная |
| 108 | Zone 005: birthpod релизит сферы после разрушения | реализован (по данным) | строки 54-59 | `L01S06` (zone 005): `incubator`×1 + `bubble_creator`×1 |
| 109 | Zone 006: снаряды сбиваемы, вблизи не стреляет, бонус-регион 1000 | частичен | строки 28-31 | `L01S07` (zone 006): `double_launcher`×1 |
| 110 | Zone 007: первые мины | реализован | строки 46-48 | `L01S08`: `mine`×3 |
| 111 | Zone 008: ракета несъедобна, граната ломает антенну | реализован | строки 36-45 | `L01S09` |
| 112 | Zone 009: UP даёт костюм и двойной выстрел | реализован | `GameScene.swift:233-238`, `:346-350` | `L01S10`: `capsule` 32×80 при x=368,y=176 — ровно как заявляет README |
| 113 | Zone 023: комбинированное верхнее+нижнее расположение gun-machine | противоречит | строка 27 | `L01S24`: `turret`(TOP)×1 + `source_marker`(BOTTOM)×1 → нижнее орудие не появляется вообще |
| 114 | Zone 024: первый stage bonus | частичен | строки 96-102 | `L01S25`: `blk_stage_end`×1; бонус считается по номеру зоны, а не по маркеру; нужен macOS |
| 115 | Zone 035: поле на 25 попаданий | частичен | строки 85-90 | `L02S11` |
| 116 | Zone 043: постановка гранаты обязательна на маршруте | частичен | строки 36-43 | `L02S19`: `blk_control_beacon`, `blk_beacon_base`, `mine`×2, `blk_mushroom` (нереализован); нужен macOS |
| 117 | Zones 086–088: альтернативный маршрут и ещё один guided-missile | частичен | строки 36-43 | zone 086 = `L04S12` (2 портала, `blk_box_white`), zone 087 = `L04S13` (`double_launcher`×2), zone 088 = `L04S14` (маяк + насос); нужен macOS |
| 118 | Zones 100–124 повторяют структуру 25–49 с косметикой после 101 | реализован | — | сравнение мультимножеств объектов `zone 25+k` ↔ `zone 100+k`: 24/25 идентичны, расходится только пара 025 (`L02S01`: 3 `source_marker`) ↔ 100 (`L05S01`: `ship`+`gate`) |
| 119 | Zone 124 завершает игру и зацикливает в начало | противоречит | строка 104 | `beginFromTitle` не делает restart; нужен macOS |

### 19. Правило аудита из конца `ORIGINAL_MECHANICS.md` (каждый action-маркер обязан иметь рантайм)

| # | Маркер из обязательного списка | Статус | Код | Данные / проверка |
|---|---|---|---|---|
| 120 | torches | отсутствует | `grep -rni "torch" Exolon/` — пусто | и в данных нет: `grep -rlio torch Exolon/Resources/*.tmx` — пусто (ни кода, ни данных) |
| 121 | gun machines | противоречит | строки 23-27 | TOP/`gunMachine1` → 33 турели; BOTTOM (18 маркеров) → ничего |
| 122 | flashing cells (`blk_blinker`) | отсутствует | `TMXLevelRuntime.swift:366-368` — явный `break` («Blinker is an attribute-flash action»), рантайм-объект не создаётся | 19 маркеров в 11 зонах: 24, 49, 60, 61, 74, 75, 79, 83, 84, 99, 124 |
| 123 | mines | реализован | строки 46-48 | 50 `blk_mine` |
| 124 | teleport | реализован | строки 69-71 | 66 `blk_teleportGate` |
| 125 | white / yellow refill boxes | реализован | строки 74-76 | 46 + 35 |
| 126 | sphere homes | реализован | строки 54-59 (кроме строки 57) | 21 `blk_birthpod` |
| 127 | pumps | частичен | строки 50-52 | 45 `blk_anim_pump` |
| 128 | rocket launchers | противоречит | строки 32-35 | 23 `blk_tower_rocket` (12 зон) → статический разрушаемый |
| 129 | changing room | реализован | строка 77 | 5 |
| 130 | green guidance | реализован | строки 36-43 | 13 |
| 131 | bonus triggers | отсутствует | строка 96 (маркер парсится и никогда не читается) | 5 `blk_stage_end` |
| 132 | high voltage (`blk_topdown_electro`) | отсутствует | `TMXLevelRuntime.swift:361-365` — явный `break`; `sourceHazards` (`:28`) нигде не заполняется, летальная проверка `GameScene.swift:574-577` мертва (всегда пустой массив) | 2 маркера: зоны 25 (`L02S01` x=176,y=48) и 66 (`L03S17`) |
| 133 | stage end | противоречит | строка 96 | 5 маркеров |
| 134 | beam | частичен | строки 85-89 | 20 маркеров в 10 зонах |
| 135 | (вне списка дока) `blk_waggon` | отсутствует | `TMXLevelRuntime.swift:409` `default:` | 24 маркера, 14 зон: 22, 23, 26, 37, 48, 54, 65, 75, 78, 91, 94, 101, 112, 123 |
| 136 | (вне списка дока) `blk_mushroom` | отсутствует | `TMXLevelRuntime.swift:409` `default:` | 9 маркеров, 6 зон: 25, 43, 53, 69, 90, 118 |

### 20. Заявления README.md (Step 9)

| # | Заявление | Статус | Код | Данные / проверка |
|---|---|---|---|---|
| 137 | Сохранён проект 125 зон и original-visual pipeline | реализован | `GameScene.swift:53`; `TMXTileMapRenderer.swift:20-46`, `:115-150` | 125 TMX, image- + tile-слои |
| 138 | Placement объектов Zone 009 перестроен из reference TMX-координат | реализован | `TMXMapLoader.swift:73-81` | `L01S10.capsule` с `coordinateMode=tiledRect` |
| 139 | Поршни Zone 009 теперь x=64/192, y=320 (не y=384) | реализован | `TMXLevelRuntime.swift:286-289` | `L01S10`: `piston` x=192 y=320 и x=64 y=320 — точно |
| 140 | Раздевалка — реальный прямоугольник 32×80 при x=368, y=176 (Tiled) | реализован | `TMXLevelRuntime.swift:291-306` | `L01S10`: `capsule x=368 y=176 w=32 h=80` — точно |
| 141 | Конверсия прямоугольных объектов явная, tile- и rect-объекты больше не смешиваются | частичен | `TMXMapLoader.swift:73-81` | флаг `tiledRect` стоит ровно 1 объекту во всех 125 картах; остальные 359 rect-объектов идут по bottom-anchor ветке «legacy» (проверка совместимости: bottom-anchor читается без выхода за карту во всех 359 случаях, top-left — с 99 нарушениями) |
| 142 | Поршни летальны при exposed (кроме TEST INVULNERABILITY) | реализован | `GameScene.swift:556-565`, `:601-602` | — |
| 143 | UP в раздевалке переключает Exoskeleton | реализован | `GameScene.swift:233-238` | — |
| 144 | Exoskeleton: двойной бластер + защита от мин/поршней | частичен | `GameScene.swift:346-350`, `:546`, `:557` | строка 48: мина при костюме не детонирует вовсе |
| 145 | Restart/new session сбрасывает Exoskeleton | реализован | `GameScene.swift:963`; `:685-695` | — |
| 146 | Каждый запуск начинается с Zone 000; High Score сохраняется | реализован | `GameScene.swift:685-694` (`clearCheckpoint`, `currentLevelName = "L01S01"`) | — |
| 147 | Rebase cabin fix: artwork раздевалки — pass-through scenery | реализован | `TMXLevelRuntime.swift:97-122`, `:291-307`, `:371-379` | нужен macOS |
| 148 | Исключение коллизии по типу объекта ⇒ действует на всех screens с раздевалкой | частичен | две разные ветки с разной геометрией: `capsule` (`:301-307`, `max(96, w+64)`) и `source_marker/changing_room` (`:374-379`, `w+32`) | обе существуют, но геометрия исключения не совпадает |
| 149 | UP в раздевалке/телепорте не превращается в случайный прыжок на следующем фикс-шаге | реализован | `GameScene.swift:251-266`; `Player.swift:256-258` | — |
| 150 | README озаглавлен «Step 9 Rebase» | противоречит | `GameScene.swift:67` («STEP 9 · ALL 125 ORIGINAL ZONES») против `:832` («STEP 10» на title), `TMXLevelRuntime.swift:3` («Step 10»), `:494` («Step 9 fixed»), ключи персистентности `Exolon.Step10.*` (`GameState.swift:24-31`) | версионирование док↔код рассогласовано |
| 151 | «runnable checkpoint … not the claim that every late-zone action is already audited» | реализован (дискаймер соответствует истине) | `README.md:19` | подтверждается строками 27, 32-35, 96, 122, 132 |

## Чего нет вообще

Ни кода, ни рантайм-объекта. По убыванию влияния на фидельность.

| Механика / маркер | Требование | Что есть вместо | Evidence |
|---|---|---|---|
| Таймер зоны 700 циклов + несъедобный преследователь | §Timed indestructible pursuer, весь раздел | ничего | `grep -rni "700\|pursuer\|fighter\|zoneTimer" Exolon/` — пусто |
| Стреляющая ракетная башня (порог 30, скорость −2, сбивается за 50, убивает контактом) | §Rocket tower | 23 маркера `blk_tower_rocket` в 12 зонах → статический `DestructibleObstacle` «rocket», разрушаемый только гранатой за 150 и глушащий бластер | `TMXLevelRuntime.swift:264-269`; `GameScene.swift:407-417` |
| Bravery-бонус 10 000 за отказ от костюма | §Stage ends, §Exoskeleton | ничего | `grep -rni "bravery" Exolon/` — пусто |
| Timed bonus cursor 0/1000/3000/5000/7000 | §Stage ends | ничего | `GameScene.swift:622-631` |
| Сброс экзоскелета на границе стадии | §Stage ends, §Exoskeleton | только пауза→RESTART | `GameScene.swift:622-631`, `:963` |
| Бонус-секвенция / stage-end как триггер | §Stage ends, §audit rule | `stageExitMarkers` заполняется и никогда не читается | `TMXLevelRuntime.swift:30, 369-370` |
| Кап 6 активных слотов летающих врагов | §Flying enemies | append без ограничения | `TMXLevelRuntime.swift:145-152` |
| Кап 24 сферы для «engine capacity» | §Sphere homes | append без ограничения | `TMXLevelRuntime.swift:317-320` |
| Шесть оригинальных таблиц траекторий | §Flying enemies | 3 аналитические ветки, достижима одна | `LevelObstacles.swift:477-495` |
| Выбор семейства спрайта по зоне | §Flying enemies | случайный ряд цвета | `LevelObstacles.swift:449` |
| Нижние gun machines (`blk_gunMachine_BOTTOM`) | §Stationary gun machine, §Zone 023 | маркер молча игнорируется | `TMXLevelRuntime.swift:351-407`, `:409` |
| Torches | §audit rule | ни данных, ни кода | `grep -rli torch Exolon/Resources/*.tmx` — пусто |
| Flashing cells (`blk_blinker`) | §audit rule | явный `break` | `TMXLevelRuntime.swift:366-368` |
| High voltage (`blk_topdown_electro`) | §audit rule | явный `break` + мёртвый `sourceHazards` | `TMXLevelRuntime.swift:361-365`, `:28`; `GameScene.swift:574-577` |
| `blk_waggon` | §audit rule («каждый action-маркер») | `default:` | 24 маркера, 14 зон |
| `blk_mushroom` | то же | `default:` | 9 маркеров, 6 зон |
| `CocoonObstacle` (80×128, отдельная нода) | — | класс объявлен и нигде не инстанцируется; `cocoon` строится как `DestructibleObstacle` | `LevelObstacles.swift:4-26`; `TMXLevelRuntime.swift:250-255` |
| Три полностью пустые зоны | §Global structure | `L03S09` (058), `L03S14` (063), `L04S11` (085) содержат только `vitorc` | перебор объектов 125 TMX |
| Провенанс для части карт | §audit rule | 11 TMX вообще без `sourceBlock`: `L01S01…L01S08`, `L03S09`, `L03S14`, `L04S11`; ещё 40 из 428 именованных игровых объектов несут имя без `sourceBlock` (rocket 6, bubble_creator 3, grenade_pack 3, light_floor 3, light_ceiling 3, turret 4, teleport 4, mine 3, ammo_pack 2, radar 2, ship_fire 2, piston 1, double_launcher 1, ship 1, cocoon 1, incubator 1) | `grep -l sourceBlock *.tmx \| wc -l` = 114 из 125; пообъектный перебор |
| Опорные asm-исходники | §Sources of truth | `rusarh/exolon-esl`, `data_zone_data.asm`, `actions_*.asm` в дереве отсутствуют → пороги (X=84/120, 700 циклов, 15 тиков, «block 31», 24/25) подтвердить нечем | `ls rusarh` — нет; `find . -name '*.asm'` — пусто |

## Противоречия README ↔ код

| # | Утверждение (README или ORIGINAL_MECHANICS) | Что делает код | Файл:строка |
|---|---|---|---|
| 1 | README озаглавлен «Exolon — Step 9 Rebase» | один и тот же рантайм размечен и Step 9, и Step 10 | `GameScene.swift:67`, `:656`, `:984` vs `:832`; `TMXLevelRuntime.swift:3` vs `:494`; `GameState.swift:24-31` (`Exolon.Step10.*`) |
| 2 | README: «Zone 009 pistons now use x=64/192, y=320» и «changing room … x=368, y=176» | обе цифры верны для `L01S10`, то есть для 0-based zone **9**; при этом §Walkthrough относит «Zone 008: guided missile» к `L01S09`, а «Zone 009: changing room» к `L01S10` — имя файла и номер зоны расходятся на единицу, и в README это нигде не оговорено | `GameScene.swift:988-996` |
| 3 | README: «rectangle-object coordinate conversion is explicit, so tile objects and rectangles are no longer conflated» | явный режим `coordinateMode=tiledRect` проставлен ровно 1 объекту в 125 картах; 359 rect-объектов (с `width`/`height`) по-прежнему конвертятся bottom-anchor веткой «legacy» | `TMXMapLoader.swift:73-81` |
| 4 | README: «Exoskeleton … protects against mines/pistons» | при костюме мина не детонирует и остаётся взведённой; в оригинале урон обнуляется, а триггер происходит | `GameScene.swift:545-547` |
| 5 | README: «Restart/new session resets Exoskeleton» | единственный путь сброса — пауза→RESTART; §Exoskeleton требует сброс на границе стадии («persists … until the end of the current 25-zone stage», «At stage end the exoskeleton flag is cleared») | `GameScene.swift:622-631`, `:963` |
| 6 | README: «The collision exclusion is applied by object type, so it affects every changing-room screen, not only Zone 009» | исключение строят две разные ветки с разной геометрией: `capsule` → `max(96, w+64)` на `x−16`; `source_marker/changing_room` → `w+32` | `TMXLevelRuntime.swift:301-306` vs `:374-379` |
| 7 | README: «pressing UP inside the changing room toggles Exoskeleton» | условие — простое пересечение (`intersects`), тогда как телепорт требует полного вхождения коллайдера (`fullyContains`); «правильно выровнен» для кабины не обеспечивается | `GameScene.swift:234` vs `:239` |
| 8 | ORIGINAL_MECHANICS: «Reaching the stage-end trigger opens the bonus sequence» | `stageExitMarkers` заполняются из 5 маркеров и не читаются; бонус запускается по `x > 510` плюс номер зоны | `TMXLevelRuntime.swift:370`; `GameScene.swift:610-627` |
| 9 | Комментарий в коде: «our current content is still being extended through Step 9 … deliberately dormant until later steps add Zones 024/049/074/099/124» | эти пять зон уже лежат в дереве (`L01S25`, `L02S25`, `L03S25`, `L04S25`, `L05S25`), и ветка реально исполняется — комментарий устарел и описывает не-истину | `GameScene.swift:623-626` |
| 10 | ORIGINAL_MECHANICS: «The original rebuilds the current zone after death» | зона после смерти не пересобирается; разрушенные объекты остаются разрушенными, активные снаряды/гранаты/взрывы/след не снимаются | `GameScene.swift:311-336` |
| 11 | ORIGINAL_MECHANICS: «Rockets are destroyable by blaster and award 50 points» | `rocket` входит в `hitIndestructible` → бластер гаснет без очка; уничтожается только гранатой за 150 | `GameScene.swift:407-417`, `:444-450` |
| 12 | ORIGINAL_MECHANICS: «A blaster hit destroys a sphere for 50» + §Zone 005 «releases … after destruction» | сфера уничтожается бластером насквозь сквозь целый контейнер: ветка `eggs` (`:391`) идёт раньше проверки инкубаторов (`:407-415`) | `GameScene.swift:391-397` vs `:407-415` |
| 13 | ORIGINAL_MECHANICS: «Extends vertically from its source marker until the next no-walk cell» | высота поля фиксирована (272 px), up/down-маркеры дают перекрывающиеся рамки 32×160, а `first(where:)` отдаёт попадания только первой | `TMXLevelRuntime.swift:356-359`; `GameScene.swift:399` |
| 14 | ORIGINAL_MECHANICS: «Zone 124 … returns the game to the beginning» | показ баннера есть, возврат — на title; `beginFromTitle` не перезапускает уровень и состояние, следующая `fire` возвращает в ту же зону 124 | `GameScene.swift:708-717`, `:744-752`, `:761-767` |
| 15 | ORIGINAL_MECHANICS: «Stage starting positions from source … 075 (40,128), 100 (16,112)» | у зон 025/050/075/100 в TMX стоит идентичный `vitorc x=0, y=320` | данные `L02S01`/`L03S01`/`L04S01`/`L05S01` |
| 16 | ORIGINAL_MECHANICS: «No new flying enemy is spawned once player X ≥ 84» / «start from the right at X=120» (original units) | пороги 320 и 528 взяты из reference-ремейка; при ×4-конверсии, которую сам док использует для `X=70→280`, ожидалось 336 и 480 | `LevelObstacles.swift:414`, `:419` |
| 17 | ORIGINAL_MECHANICS §audit rule: «Every action marker … must have a corresponding runtime implementation» (blinker, high voltage) | обе ветки явно обнулены с обратным обоснованием | `TMXLevelRuntime.swift:361-368` |
| 18 | ORIGINAL_MECHANICS: «Hidden/waiting, then move … according to the original phase counter» | `Int.random(60...300)` на каждый цикл | `LevelObstacles.swift:331`, `:383` |
| 19 | ORIGINAL_MECHANICS: «Sphere/player contact destroys the sphere and kills the player» / «Contact kills the player and removes the enemy» | контакт дополнительно начисляет очки (150 за bubble, 50 за egg), которых док для контакта не обещает | `GameScene.swift:583`, `:593` |
| 20 | ORIGINAL_MECHANICS: «Crossing the launcher's invisible bonus region awards 1000 points once» | бонусная «область» = видимый корпус орудия, а её пересечение ещё и навсегда выключает стрельбу (`isActive = false`) | `LevelObstacles.swift:695`, `:718-723` |
| 21 | ORIGINAL_MECHANICS §Stationary gun machine описывает один тип турели, но §Walkthrough требует «Zone 023: combined upper/lower gun-machine arrangement» | нижняя турель существует только как `source_marker` и не создаёт объект, поэтому парной схемы в Zone 023 нет (и ещё в 14 зонах) | `TMXLevelRuntime.swift:351-407`, `default:` `:409` |
| 22 | README: «keeps the existing 125-zone project and original-visual pipeline» | верно по числу файлов, но 3 зоны (`058`, `063`, `085`) не содержат ни одного объекта, а в 32 зонах есть маркеры без рантайма — «original» в них сведён к фону | перебор объектов 125 TMX |

Вердикт: fail
