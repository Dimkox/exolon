# Архитектурное ре-верифицирующее аудирование Exolon (полный проход)

**Маршрут:** `7db1f3f0b126` (intent=`review`, `write_agent=null`), агент `architect`, read-only.
**Дата:** 2026-09-20.
**HEAD:** `b8aee429e2565aa3824759639060787a7b36ae20`.
**Хост:** Linux x86_64. Нет Xcode, Swift, macOS. Это **аудит исходников и данных**, не прогон игры.

Файл: `engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/analysis-architect-fullaudit.md`.
Он **не** заменяет `analysis-architect.md` (тот от 19.09, HEAD `403eb13`) и содержит исправления его выводов.

---

## 0. Метод и дисциплина контроля

1. **Целостность дерева относительно предыдущего аудита.**
   `git diff --stat 403eb13 b8aee42 -- Exolon Exolon.xcodeproj` → **пусто** (проверено в этой сессии, exit 0).
   `git status --porcelain` показывает только untracked workflow-артефакты (`.grok-stack/`, `engineering/`).
   → Продуктивное дерево не менялось; расхождения ниже — это **ошибки прошлой проверки**, а не дрейф кода.

2. **Ничему не верю на слово.** Каждый вердикт TASK A получен повторным чтением текущего содержимого файла в этой
   сессии с цитатой `file:line`, либо повторной реализацией того же алгоритма (TMX → collision rects → `subtract`)
   поверх фактических 125 `.tmx`. Прошлый отчёт использовался только как список утверждений для проверки.

3. **Контроли чувствительности** (чтобы «всё хорошо» не было артефактом слепой проверки):
   - §1.1: мутация формулы исключения с `−16` на `−32`/`−48` **обязательно** должна была показать срезанный пол —
     и показала (1 и 2 rect'а). Значит ноль при `−16` — измеренный факт, а не пустой прогон.
   - §1.2: проверка «сколько карт содержат оба маркера» сделана перебором 125 файлов; контрольное значение —
     число карт, содержащих *хотя бы один* `beam_*` (10), совпало с числом «оба» (10) только для реальных данных.
   - §1.4: grep по всему дереву `Exolon/**/*.swift` на оба поля, с раздельным подсчётом записей и чтений.
   - §1.5: цепочка `nextLevel` пройдена независимо (125 узлов, конец `L05S25`), а не принята на веру.

4. **Чего здесь нет и не может быть на Linux:** сборки Swift, поведения SpriteKit/AppKit, реального геймплея,
   таймингов, визуального соответствия оригиналу. Всё такое помечено `runtime-hypothesis`.

---

## 1. TASK A — независимые вердикты по находкам прошлого аудита

### Сводная таблица

| ID прошлого аудита | Утверждение | Вердикт | Краткое доказательство |
| --- | --- | --- | --- |
| **C1 (P0)** | `minY - 16` режет пол кабины; в зоне 009 вырезается весь пол | **ОПРОВЕРГНУТО** как дефект; **УТОЧНЕНО** до P3 robustness | Исключение срезает ровно 5 клеток самого объёма будки (6400 px²) и **0** клеток пола; пол зоны 009 — `y=64..96`, нижняя грань исключения `y=112` (запас 16 px). Замерено по всем 5 будкам |
| **O7 (P1)** | `beam_up` и `beam_down` → два поля по 25 хитов | **ПОДТВЕРЖДЕНО**, масштаб **УТОЧНЁН**: не «зона 035», а **все 10 карт** с beam-маркерами содержат оба | 10×`blk_beam_up` + 10×`blk_beam_down`; `TMXLevelRuntime.swift:356-360` — одна ветка `contains("beam_")` на каждый объект |
| **O8 (P1)** | сбор бонуса двойной пушки выключает её | **ПОДТВЕРЖДЕНО** + усилено | `LevelObstacles.swift:718-723`; `isActive = false` — **единственный** источник сброса флага у этого класса; оружием/гранатой пушка не убивается вообще |
| **A4.1** | `sourceHazards` никогда не наполняется | **ПОДТВЕРЖДЕНО** | объявление `TMXLevelRuntime.swift:28`; единственное чтение `GameScene.swift:575`; ни одного `append` |
| **A4.2** | `stageExitMarkers` пишутся, но не читаются | **ПОДТВЕРЖДЕНО** + **УТОЧНЕНО** | запись `TMXLevelRuntime.swift:370`, чтений нет; **и** данные маркеров непригодны как триггер выхода: `sourceX`=12/17 → прямоугольники в **середине экрана** (x=192..288, 272..368), а не у правого края |
| **O5 (P1)** | комментарий «dormant» устарел, бонус стадии живой | **ПОДТВЕРЖДЕНО** | `GameScene.swift:624` («deliberately dormant…») против `guard [24, 49, 74, 99, 124]` на `:626`; все пять карт (`L01S25`…`L05S25`) существуют в реестре 125 |

Дополнительно по TASK A найден **новый дефект**, которого в прошлом отчёте нет: повторяющееся начисление бонуса
стадии в зоне 124 (см. §2, находка **B-03**).

---

### 1.1 C1 — пересчёт координат кабины зоны 009 с нуля

**Данные (`Exolon/Resources/L01S10.tmx`, слой `Objects`, csv-слой `Collision` 35×24, тайл 16×16, `pixelHeight`=384):**

```xml
<object name="capsule" x="368" y="176" width="32" height="80">
  <properties> coordinateMode=tiledRect, sourceBlock=blk_changing_room
```

**Шаг 1. Триггер.** `TMXMapLoader.swift:74-81`:

```swift
if object.properties["coordinateMode"] == "tiledRect" {
    return CGPoint(x: object.x, y: pixelHeight - object.y - object.height)
}
```
→ `bottom = (368, 384 − 176 − 80) = (368, 128)`. `TMXLevelRuntime.swift:292-295`: `trigger = (368, 128, 32, 80)`, то есть
**y 128…208**, x 368…400.

**Шаг 2. Исключение.** `TMXLevelRuntime.swift:297-306` (текущий текст):

```swift
// ... but start
// 16 px above the supporting platform so the floor stays solid.
changingRoomCollisionExclusions.append(CGRect(
    x: trigger.minX - 16,
    y: max(0, trigger.minY - 16),
    width: max(96, trigger.width + 64),
    height: trigger.height + 32
))
```
→ `exclusion = (352, 112, 96, 112)`, то есть **y 112…224**, x 352…448.

**Шаг 3. Что реально стоит в слое коллизий.** Прогон `TMXTileMapRenderer.buildCollisionRects`
(`TMXTileMapRenderer.swift:117-150`, слияние горизонтальных прогонов, `y = pixelHeight − (row+1)·16`) над
`L01S10.tmx` даёт 9 прямоугольников; значимые:

| прямоугольник | назначение |
| --- | --- |
| `x=272..560, y=64..80` и `x=272..560, y=80..96` | **платформа под будкой**, верхняя грань `y=96` |
| `x=0..288, y=48..64`, `x=272..288, y=32..48` | продолжение пола левее/ниже |
| `x=368..448, y=128..144 / 144..160 / 160..176 / 176..192 / 192..208` | **объём будки** (5×5 клеток, 80×80 px) |

**Шаг 4. Применение `subtract` (`TMXLevelRuntime.swift:437-483`) к этим данным:**

```
removes rect x=368 y=192..208 w=80 -> remains 0
removes rect x=368 y=176..192 w=80 -> remains 0
removes rect x=368 y=160..176 w=80 -> remains 0
removes rect x=368 y=144..160 w=80 -> remains 0
removes rect x=368 y=128..144 w=80 -> remains 0
```

Удаляются **только** 5 клеток объёма будки (ровно те, что и задумано: `README.md:21` — «pass-through scenery»).
Клетки пола (`y=64..96`) в пересечение с `y 112..224` **не попадают**: до них 16 px запаса. `groundY` карты при этом
`= min(rect.maxY) = 48` (`TMXLevelRuntime.swift:70-77`), то есть «пол» игры стоит ещё ниже.

**Шаг 5. Все будки дерева** (1 `capsule` + 4 `source_marker/changing_room`; `coordinateMode=tiledRect` действительно
только у одной капсулы — проверено перебором 125 карт):

| карта | триггер (y) | исключение (y) | верх платформы под будкой | удалено клеток пола |
| --- | --- | --- | --- | --- |
| `L01S10` (capsule) | 128…208 | 112…224 | 96 | **0** (запас 16 px) |
| `L02S10` | 256…352 | 240…368 | 240 | **0** (запас 0 px) |
| `L03S11` | 112…208 | 96…224 | 96 | **0** (запас 0 px) |
| `L04S16` | 80…176 | 64…192 | 64 | **0** (запас 0 px) |
| `L05S10` | 256…352 | 240…368 | 240 | **0** (запас 0 px) |

**Шаг 6. Контроль чувствительности.** Тот же прогон с намеренно неверным смещением:

```
CONTROL off=16: floor rects cut = 0      <- фактический код
CONTROL off=32: floor rects cut = 1      (rect x=0..288, y=224..240)
CONTROL off=48: floor rects cut = 2
```

Проверка не «всегда ноль»: одно изменение тайла в формуле уже режет пол.

**Вердикт.** Утверждение «*для zone 009 это cut'ает пол кабины*» — **опровергнуто**. Прошлый аудит правильно заметил
несоответствие текста комментария и того, от чего считается формула (комментарий говорит про «supporting platform»,
код мерит от `trigger.minY`), но сделал из этого неверный вывод об удалении пола. В `L01S10` `trigger.minY − 16 = 112`
— это ровно «на 16 px выше платформы с верхом 96», то есть комментарий и код **случайно согласованы**.

**Что остаётся (P3, а не P0):** смещение `−16` жёстко зашито от триггера, а не от реальной платформы, поэтому
в 4 из 5 будок нижняя грань исключения **впритык** совпадает с верхней гранью пола (запас 0 px). Свойство «пол цел»
в данном дереве выполняется, но обеспечивается совпадением данных компилятора уровней, а не кодом. Также в
`capsule`-ветке `x: trigger.minX - 16` **не** защищён `max(0, …)`, в отличие от marker-ветки
(`TMXLevelRuntime.swift:375`) — асимметрия.

---

### 1.2 O7 — двойное силовое поле

**Ветка кода, `TMXLevelRuntime.swift:356-360`:**

```swift
if source.contains("beam_") {
    let box = CGRect(x: sx, y: max(0, bottomY - 240), width: 48, height: 272)
    let field = ForceFieldBarrier(hitbox: box)
    forceFields.append(field)
    rootNode.addChild(field.node)
```

`blk_beam_up` и `blk_beam_down` оба содержат подстроку `beam_` → **каждый** `source_marker` создаёт отдельный
`ForceFieldBarrier`. Бюджет — 25 попаданий на экземпляр (`LevelObstacles.swift:766` `private var hitPoints = 25`),
уменьшается только у первого совпавшего поля за шаг (`GameScene.swift:449` `forceFields.first(where: …)`), то есть
суммарно на направление тратится **50 выстрелов**.

**Сколько карт содержат оба — ответ на задачу:** перебором 125 файлов:

```
maps containing any beam_: 10
maps containing BOTH beam_up and beam_down: 10
['L02S11','L02S15','L02S17','L03S01','L03S13','L03S19','L04S18','L05S11','L05S15','L05S17']
```

То есть **10 из 10** карт с beam-маркерами содержат обе пары (по одному `beam_up` и одному `beam_down`); всего в
дереве 20 полей там, где по оригиналу их 10. Прошлый отчёт (§9.3 п.8, таблица O7) привёл как пример только
`L02S11` — это **недооценка охвата**, а не ошибка.

**Уточнение к прошлому «50 хитов — гипотеза».** Конструкция «два поля» и «50 выстрелов до уничтожения» —
**code-confirmed** (циклы `hitByBlaster`/`first(where:)` перечитаны выше). Гипотезой остаётся только игровое
восприятие. При этом **опасная зона для Виторка не удваивается**: `GameScene.swift:568-572` использует
`contains(where:)`, то есть урон наносит пересечение с любым из двух боксов. Боксы перекрываются: в `L02S11`
up = x 288…336 / y 112…384, down = x 304…352 / y 0…272 → общее пересечение x 304…336, y 112…272. Значит дефект
лежит строго в плоскости «цена прочистки», а не «размер lethal-зоны».

---

### 1.3 O8 — бонус двойной пушки

`LevelObstacles.swift:718-723` (текущий текст):

```swift
func collectBonusIfTouched(playerBox: CGRect) -> Bool {
    guard isActive, playerBox.intersects(hitbox) else { return false }
    isActive = false
    node.alpha = 0.45
    return true
}
```

`LevelObstacles.swift:698-699`:

```swift
func fixedUpdate(dt: TimeInterval, player: Player) -> EnemyTurretBullet? {
    guard isActive, !player.isDying else { return nil }
```

→ сбор бонуса **останавливает стрельбу**. **Подтверждено.**

Что прошлого отчёта в цитатах нет, но я проверил как усилители:

1. `isActive` у `DoubleLauncherObstacle` меняется **только** здесь. Grep по `isActive` в
   `LevelObstacles.swift` (строки 685/699/719/720) и по `doubleLauncher` в `GameScene.swift`: ни `updateBullets`
   (`:431-446` — turrets / destructibles / incubators / forceFields), ни `updateGrenades` (`:448-478`) не
   содержат `doubleLaunchers`. То есть **оружием пушка неуязвима**, а прикосновение к её спрайту — единственный
   способ её «убить», и он же даёт +1000.
2. Проверка бонуса идёт по **спрайтовому** `hitbox` 64×48 (`:695`), а не по отдельной невидимой зоне, и пушка
   **не** входит в `solidRects` (`TMXLevelRuntime.swift:124-130`) — то есть Виторк проходит сквозь неё телом и
   гарантированно собирает бонус, просто пробегая мимо.
3. Вызов — `GameScene.swift:299` (`player.movementHitbox`), без условия «стоим/не стреляем».

Итог: отклонение от оригинала не «на поздних зонах», а на всех **19** `double_launcher` (`L01S06` — walkthrough).
P1 остаётся.

---

### 1.4 `sourceHazards` и `stageExitMarkers`

Grep по всему `Exolon/**/*.swift`:

```
TMXLevelRuntime.swift:28:    private(set) var sourceHazards: [CGRect] = []
TMXLevelRuntime.swift:30:    private(set) var stageExitMarkers: [CGRect] = []
TMXLevelRuntime.swift:370:   stageExitMarkers.append(CGRect(x: sx, y: max(0, bottomY - 64), width: 96, height: 128))
GameScene.swift:575:         currentLevel.sourceHazards.contains(where: { !$0.isEmpty && $0.intersects(player.damageHitbox) }) {
```

- `sourceHazards`: объявлено, читается в `updateLethalEntities`, **ни одного** `append`. Мёртвая ветка урона,
  `hitPlayer()` из неё недостижим. Подтверждено.
  Корень: `TMXLevelRuntime.swift:361-368` — `topdown_electro` и `blinker` явно `break` без записи;
  в данных 2 × `topdown_electro` и 19 × `blinker`.
- `stageExitMarkers`: пишется (5 маркеров `stage_end`), **не читается нигде**. Подтверждено.
  **Новое уточнение:** прочесть их «как есть» нельзя. `sourceX` у пяти маркеров = 12, 17, 12, 12, 17 → по формуле
  `sx = sourceX·16` это x=192…288 и x=272…368, то есть **середина** 512-пиксельного экрана, а не правый край.
  Либо масштаб `sourceX` для `stage_end` иной, либо семантика маркера не «выход». Прошлый аудит этого не проверял.

---

### 1.5 Бонус конца стадии и комментарий «dormant»

`GameScene.swift:609-620`:

```swift
private func checkScreenExit() {
    guard player.position.x > 510 else { return }
    let next = currentLevel.nextLevelName
    applyOriginalStageBoundaryIfNeeded(completedZone: gameState.zone)

    guard !next.isEmpty, includedLevels.contains(next) else {
        enterContentComplete(nextLevelName: next)
        return
    }
    transition(to: next)
}
```

`GameScene.swift:622-631`:

```swift
private func applyOriginalStageBoundaryIfNeeded(completedZone: Int) {
    // Original Exolon awards the lives bonus at the five 25-zone stage ends.
    // Our current content is still being extended through Step 9, so this is deliberately dormant
    // until later steps add Zones 024/049/074/099/124.
    guard [24, 49, 74, 99, 124].contains(completedZone) else { return }
    awardPoints(gameState.lives * 1_000)
    if gameState.lives < GameState.startingLives { gameState.lives += 1 }
    gameState.ammo = GameState.startingAmmo
    gameState.grenades = GameState.startingGrenades
}
```

Незавимая перепроверка данных: цепочка `nextLevel` замкнута и проходит ровно 125 узлов `L01S01 → … → L05S25`
(пустой `nextLevel` ровно один — `L05S25`, все цели существуют на диске). Номера зон считаются в
`GameScene.swift:987-997`: `(stage−1)·25 + (screen−1)`, значит зона 24 = `L01S25`, …, зона 124 = `L05S25`.
Все пять карт в дереве есть → **guard живой**, комментарий про «dormant until later steps add Zones…» **устарел**.
Подтверждено (совпадает с прошлым O5).

Формулы подтверждены с одной поправкой к их читанию: `GameState.startingLives = 9` (`GameState.swift:88`), а
`lives` стартует с 9 → «+1 жизнь» — это **не бонус сверх лимита, а восстановление** (сработает только если игрок
уже потерял жизнь). Формально «cap 9» в прошлом отчёте верный, но механически это «верни одну жизнь, если тратил».

**Новой находкой** здесь является то, что `applyOriginalStageBoundaryIfNeeded(...)` вызывается **до** guard'а на
пустой `nextLevel`, а в зоне 124 перехода нет → см. §2 B-03.

---

## 2. TASK B — новые находки (области, которые прошлый аудит не вскрывал)

Формат: **что** → `file:line` → **severity** → **статус** (code-confirmed / runtime-hypothesis).

---

### B-01 — Авторская точка входа `vitorc` не согласована с коллизией в 90 картах из 125

`TMXLevelRuntime.swift:60-66` берёт спавн строго из объекта `vitorc`; `Player.swift:40-44` +
`Player.swift:291-297` (`landOnFallbackFloorIfNeeded`) и `Player.swift:182-201` (`refreshGroundSupport`)
его немедленно корректируют.

Промер по всем 125 карт (воспроизведён тот же расчёт, что и в Swift: `footY = worldBottomLeft.y`,
бокс 46×63, допуск опоры 1.5 px, `fallbackGroundY = min(rect.maxY)`):

```
supported (есть клетка коллизии с верхом ровно под ногами): 35
unsupported, foot = groundY - 16   (игрок поднимается плоскостью на 16 px): 59
unsupported, foot = groundY + 16   (игрок входит и падает на 16 px):        29
unsupported, foot = groundY, но под ногами пусто (L01S09, L04S16):           2
```

Причина — сдвиг конвенции в компиляторе: в `L01S01…L01S05` `vitorc.y` даёт ноги ровно по верху платформы,
начиная примерно с `L01S08` значение рассинхронизировано ровно на один тайл. `groundY` по дереву:
48 — в 44 картах, 64 — 16, 80 — 60, 96 — 5.

**Severity:** P1 (для контракта «данные уровня → поведение»): в 72% зон фактическая стартовая позиция определяется
**не** объектом `vitorc`, а глобальной «нижней» плоскостью карты. Никакого падения/зависания нет (механизм
самостоятельно доводит игрока до поверхности — проверено трассировкой `update → landOnFallbackFloor →
resolveSolidCollision`), но `vitorc.y` фактически декоративен, и любая зона, где стартовые 16 px осмысленны
(низкий коридор, стартовая платформа над пропастью), будет вести себя не по данным.
**Статус:** code-confirmed + data-confirmed. Заметность на глаз — runtime-hypothesis.

---

### B-02 — Глобальная невидимая плоскость `fallbackGroundY` держит игрока в 13 картах прямо на выходе

`Player.swift:291-297`:

```swift
private func landOnFallbackFloorIfNeeded() {
    let standingCenterY = fallbackGroundY + GameConstants.playerSpriteSize.height * 5 - ...
    if position.y <= standingCenterY { position.y = standingCenterY; velocity.dy = 0; isGrounded = true }
}
```
(фактическая строка — `position.y = standingCenterY`, `Player.swift:292-297`).

Это **плоскость на всю ширину экрана**, а не поверхность: она не проверяет наличие коллизии под ногами по X.
Замер покрытия коллизиями колонок:

```
карты, где в колонках x>=496 (31..34) нет НИ ОДНОЙ клетки коллизии: 13
  L01S16 L02S04 L02S16 L02S22 L03S05 L03S18 L03S24 L03S25 L04S17 L04S18 L05S04 L05S16 L05S22
правая покрытая колонка == 22 (x=368) в 6 картах, == 23 в 1
```

Пример `L05S16`: **вся** коллизия карты — один прямоугольник `x=0..368, y=48..64`. Правые 38% экрана (включая
зону выхода `x>510`) — пустота; игрок пересекает её, шагая по невидимой плоскости `y=64`.

Следствия, все code-confirmed:
- выход из зоны в этих 13 картах физически возможен **только** благодаря fallback-плоскости (без неё — провал);
- любая яма/провал ниже `groundY` на любой карте безвреден: `isGrounded` сбрасывается лишь при
  `footY > fallbackGroundY + 1.5` (`Player.swift:198`), поэтому спроектировать смертельный провал текущим
  механизмом нельзя;
- в 44 картах `groundY = 48` = ровно верхняя граница HUD (`GameConstants.hudHeight = 48`), то есть нижняя
  «подстраховочная» горизонталь совпадает с линией HUD.

**Severity:** P2. **Статус:** геометрия и покрытие — code/data-confirmed; «игрок визуально идёт по воздуху» —
runtime-hypothesis (зависит от того, дорисован ли пол на скриншоте-бейдроpe).

---

### B-03 — Повторное начисление бонуса стадии в зоне 124 (ферма очков)

Трассировка по `GameScene.swift`:

1. `checkScreenExit()` (`:609`) при `x > 510` в зоне 124 сначала вызывает
   `applyOriginalStageBoundaryIfNeeded(completedZone: 124)` (`:612` → `+lives·1000`, refill 99/10), затем
   `next == ""` → `enterContentComplete` (`:738`), `flowState = .contentComplete`, `saveCheckpoint()` (`:740`).
2. SPACE → `showTitleAfterContentComplete` (`:761-766`): `flowState = .title`. **Позиция игрока не сбрасывается**,
   `currentLevelName` остаётся `L05S25`.
3. SPACE на титре → `beginFromTitle` (`:708-718`): `flowState = .playing`, `setGameplayNodesPaused(false)`.
   Никакого `configure`/`respawn`/`transition` нет.
4. Следующий `fixedUpdate`: `x` всё ещё > 510 → `checkScreenExit()` → **бонус стадии начисляется повторно** →
   снова `.contentComplete`.

Цикл «SPACE → SPACE» повторяем неограниченно: до +9000…+124000 очков за цикл, и `persistence.saveHighScore`
(`:666`) честно закрепляет результат. Прошлый аудит (§9.3 п.11) отметил только «из титра SPACE не делает new game»,
не связав это с повторным бонусом.

**Severity:** P2 (целостность счёта; достижимо только при прохождении 125 зон). **Статус:** code-confirmed
(полная трассировка состояний, macOS не нужен).

---

### B-04 — `TMXMapLoader`: три разных молчаливых/летальных пути в загрузке

**(a) Любая компрессия = краш приложения.** `TMXMapLoader.swift:305-309`:

```swift
private func decodeLayerData(_ text: String, encoding: String, compression: String, ...) throws -> [UInt32] {
    if !compression.isEmpty {
        throw TMXMapLoaderError.unsupportedCompression(compression)
    }
```

`zlib` и `gzip` не различаются — всё летит в исключение, а `TMXLevelRuntime.swift:50-53` превращает его в
`fatalError("Unable to load TMX map …")`. Перебором 125 карт: **ни один** слой не сжат (121 `Collision` — csv,
10 base64-слоёв в 4 картах, `compression` атрибут отсутствует везде), так что сегодня это **латентный** риск, а
не активный баг. Любой будущий экспорт из Tiled с галочкой «Compress layer data» убивает игру на старте зоны.

**(b) Base64 перенос строк обработан корректно** — это проверено контрольным прогоном, а не принято на веру:
`TMXMapLoader.swift:312-318` сначала `components(separatedBy: .whitespacesAndNewlines).joined()`, затем
`Data(base64Encoded:)`, затем `guard data.count >= expectedCount * 4` и чтение по 4 байта. Все 10 base64-слоёв
(`L01S01…L01S04`, включая перенесённые строки) имеют длину, кратную 4, и ровно `w·h·4` байт → падений нет.
Индексация `data[offset+3]` защищена guard'ом, выхода за границы нет.

**(c) Пустая карта без ошибки.** `makeMap()` (`:155-167`) не валидирует ни `mapWidth/mapHeight > 0`, ни наличие
хотя бы одного слоя/объектов; неизвестные элементы XML уходят в `default: break` (`:243-245`).
`XMLParser.parse()` возвращает `true` на любом well-formed XML независимо от имени корневого элемента.
→ переименованный/чужой/обрезанный-but-well-formed TMX даёт **играбельный пустой уровень** (игрок на
`defaultGroundY = 96`, ноль коллизий, `checkScreenExit` всё равно срабатывает на `x > 510`) вместо ошибки.
125 карт сейчас валидны (проверено: у всех `layer.width/height == map.width/height`, ровно один слой
`Collision`), так что это **дыра в контракте**, а не активный сбой.

**(d) Мусор → ноль, без жалобы.** `:346-350`:
```swift
private func int(_ value: String?) -> Int { Int(value ?? "") ?? 0 }
private func cgfloat(_ value: String?) -> CGFloat { guard let value = value, let number = Double(value) else { return 0 } ... }
```
Опечатка в `sourceX`/`sourceY` роняет объект в (0,0) молча (`TMXLevelRuntime.swift:345-346`); отсутствие
`width`/`tilewidth` у тайлсета даёт 0, и `tileTexture` просто возвращает `nil`
(`TMXTileMapRenderer.swift:79-81`) → тайл исчезает без единого сообщения.

**Severity:** P2 для (a) и (c), P3 для (d). **Статус:** code-confirmed; частота проявления в реальном
экспорте Tiled — вне области статической проверки.

---

### B-05 — `GamePersistence.loadCheckpoint()` не вызывается нигде: чекпойнт пишется и не читается

`GameState.swift:40` — `func loadCheckpoint() -> GameCheckpoint?` определён; grep по `Exolon/**/*.swift` даёт
**ровно одно** вхождение (само определение). `GameScene.swift:685-695` (`loadPersistentState`) вместо чтения
чекпойнта делает `persistence.clearCheckpoint()` и жёстко ставит `currentLevelName = "L01S01"`.

При этом запись идёт активно: `saveCheckpoint()` вызывается из `transition()` (`:657`),
`updateDeathSequence()` (`:335`), `enterContentComplete()` (`:740`), `beginFromTitle()` (`:716`),
`restartFromBeginning()` (`:985`) — то есть **6 ключей `UserDefaults` на каждую смену зоны и на каждый респаун**,
на главном потоке, внутри фиксированного шага симуляции. Побочный эффект: надпись титра
`"CONTINUE · ZONE %03d"` (`GameScene.swift:764-768`, `:783-788`) означает «продолжить» только в рамках запущенного
процесса; после рестарта приложения она гарантированно врёт про «NEW GAME», а внутри сессии — ведёт себя как
продолжение (что и порождает B-03).

**Severity:** P2 (мёртвый API + write-only I/O в игровом цикле + двусмысленный UX). **Статус:** code-confirmed.

---

### B-06 — Обработчик ввода: фокус, опции и отсутствие меню

1. **Сброс при потере фокуса неполный.** `GameView.swift:42-44`:
   ```swift
   @objc private func windowDidResignKey() { inputState?.reset(source: .keyboard) }
   ```
   Сбрасывается только `.keyboard`; `InputState.resetGamepad()` (`InputState.swift:75-81`) при этом не вызывается,
   а `pressedBySource[.gamepad*]` сохраняет зажатым D-pad/стики. Холдер на геймпаде в момент alt-tab остаётся
   активным. Дополнительно `reset(source:)` (`InputState.swift:57-61`) **не** чистит `pausePressPending`, так что
   «заряженное» нажатие паузы срабатывает уже после возврата фокуса.
   `didBecomeKeyNotification` не подписан, и никто не ставит `flowState = .paused` при resign: `SKView` сам по
   себе не паузится, `update(_:)` продолжает гонять `fixedUpdate` на неактивном окне с «вечным» зажатым
   геймпадом. **Severity P2, status code-confirmed** (что именно делает `SKView` без фокуса на macOS —
   runtime-hypothesis).
2. **Гонка Option: `keyDown/keyUp` против `flagsChanged`.** `GameView.swift:19-26` выставляет grenade по
   факту модификатора (`event.modifierFlags.contains(.option)`), `GameView.swift:62-63` — по keyCode 58/61 из
   `keyUp`. Сценарий: зажат левый Option, зажат правый, отпущен левый → `keyUp(58)` пишет `grenade=false`,
   хотя правый Option всё ещё нажат; `flagsChanged(61)` в этот момент уже не приходит. И наоборот —
   освобождение последнего Option даёт `flagsChanged` с `optionIsDown=false` и корректно.то есть «отпускание
   одной из двух клавиш Option» гасит гранату. **P3, частично runtime** (порядок событий AppKit на Linux не
   воспроизводим).
3. **Нет главного меню и `Cmd+Q`.** `main.swift` (8 строк) и `AppDelegate.swift:8-36` не создают
   `NSMenu`/`mainMenu`, нет `applicationShouldTerminate`. Единственный способ выйти — кнопка закрытия окна
   (есть `.closable`, `applicationShouldTerminateAfterLastWindowClosed → true`, `AppDelegate.swift:38-40`);
   закрытие завершает приложение корректно. additionally `GameView.keyDown` (`:10-12`) не вызывает `super`,
   а `setKey` для неизвестных клавиш идёт в `default: break` (`:68-69`) — то есть key-equivalents в меню всё
   равно бы не дошли. **P3, code-confirmed**; чистота терминции после закрытия окна — гипотеза (нет
   `applicationWillTerminate`, но и ресурсов для освобождения нет).
4. **`GamepadInput`:** все замыкания обработчиков — `[weak self]` (`GamepadInput.swift:49-91`),
   `scene` — `weak` (`:5`), ретейн-цикла нет. `controllerPausedHandler` корректно эмулирует импульс
   (`:87-91` set true + set false), и `InputState.set` его ловит (`:44-46`). `updateStatus` идёт через
   `DispatchQueue.main.async` с `[weak self]` (`:97-102`) — безопасно. `deinit` снимает наблюдения (`:104-106`).
   Находка лишь в том, что при переподключении того же контроллера `configure` навешивает обработчики повторно
   (перезапись, а не накопление) — вреда нет. **P3/информационно.**

---

### B-07 — Игрок и порядок разрешения коллизий; туннелирование опровергнуто

- **Порядок — не «пол → потолок → стены».** `GameScene.swift:271-276`:
  ```swift
  let solids = currentLevel.solidRects
  for solid in solids where player.movementHitbox.intersects(solid) {
      player.resolveSolidCollision(previousPosition: previousPosition, solid: solid)
  }
  player.refreshGroundSupport(solids: solids)
  ```
  `solidRects` = `terrainRects` + активные turret/destructible/incubator (`TMXLevelRuntime.swift:124-130`), а
  `buildCollisionRects` обходит `for row in 0..<collision.height` (`TMXTileMapRenderer.swift:124`), то есть
  **сверху вниз по карте**: верхние ряды и потолки разрешаются раньше нижнего пола, динамика — в конце.
  Итерация при этом использует **изменяющийся** `player.movementHitbox` (условие `where` вычисляется на каждом
  элементе), то есть позднее разрешённое тело может перестать пересекать ранее проверенный rect. Это не ошибка
  per se, но она делает поведение зависимым от порядка вставки.
- **Туннелирование — опровергнуто.** `moveSpeed = 90`, `jumpVelocity = 165`, `maximumFallSpeed = -300`
  (`Player.swift:27-32`) при `fixedTimeStep = 1/60` (`GameConstants.swift:5`) дают максимум 1.5 px/шаг по X и
  5 px/шаг по Y против 16-пиксельных клеток. `maximumFrameTime = 0.25` ограничивает догоняющий цикл
  (`GameScene.swift:129-136`) ~15 шагами, размер шага не меняется. Сквозь пол пройти нельзя.
- **Гипотетическая ловушка «встать под низким потолком» — опровергнута данными.** В
  `resolveSolidCollision` (`Player.swift:137-180`) при `velocity.dy == 0` и глубоком вертикальном пересечении
  не срабатывает ни ветка пола (`previousBox.minY >= solid.maxY - 1.0`), ни ветка потолка
  (`velocity.dy > 0`), и остаётся только `else { position.x = previousPosition.x; velocity.dx = 0 }`
  (`Player.swift:171-177`) — то есть подъём из приседа под потолком с зазором ∈ (52, 63] пикселя заморозил бы
  горизонтальное движение. Проверено по всем 125 картам: зазоры кратны 16 px, в окно (52, 63] не попадает
  **0 клеток** (распределение: …, 48 → 91 клетка, 64 → 59). Путь в коде есть, достижимости в данных нет.
  **P3/справка**, статус — опровергнуто измерением.
- **Побочный, достижимый частный случай:** зазор 48 px (3 тайла) тоже непроезжаем — и стоячий бокс 63, и
  присед 52 (`GameConstants.swift:24-25`) больше 48. В 111 картах встречаются «карманы» с зазором ≤48 px;
  являются ли они обязательной частью маршрута — требует pathfind/прогона, поэтому подаю как
  **runtime-hypothesis** с измеренным списком (топ: `L02S05`/`L05S05` — 145 клеток, `L02S22`/`L03S04`/`L05S22` — 140).

---

### B-08 — Ресурсы и время жизни: цена загрузки зоны

1. **Загрузка зоны синхронна и происходит внутри фиксированного шага.** `GameScene.swift:308 → :633-657`:
   `transition(to:)` прямо в `fixedUpdate` создаёт `TMXLevelRuntime(resource:)` → XML-парсинг, base64-декод,
   построение коллизий и **всех** `SKSpriteNode`. Единственный «штраф» — пауза кадра на смене зоны.
2. **Объём не катастрофичен — это измерено, а не предположено.** По 125 картам: в среднем **11.5** прямоугольников
   коллизии (максимум 35 — `L03S18`, `L02S01`), а число тайловых `SKSpriteNode` на зону: **0** для 118 карт
   (визуал — один `imagelayer` со скриншотом `zone_NNN_original.png`) и максимум **247** в `L01S03`.
   То есть «взрыв нод на тайлах» для поздних зон неактуален; риск сосредоточен в декоде одного полноэкранного
   PNG (512×384) на новую `SKTexture` при каждой смене зоны.
3. **Атласов нет, `SKTexture(imageNamed:)` вызывается на каждый экземпляр объекта.** Например 70 порталов
   (`TeleportPortal.init`, `LevelObstacles.swift:264-277`) порождают 70×8 sub-`SKTexture`, 22 инкубатора —
   22×8 яиц по 2 кадра (`:585-593`). `SKTexture(imageNamed:)` внутри SpriteKit кэшируется по имени, а
   `SKTexture(rect:in:)` — нет. Локальный кэш листов есть только у рендерера тайлов
   (`TMXTileMapRenderer.swift:77-88`, `sheetTextures`). **P3.**
4. **`ExplosionEffect` строит кадры заново на каждый эффект** (`ExplosionEffect.swift:34-43`: 5 или 10
   `SKTexture(rect:in:)` на инстанс), а эффект создаётся на каждое попадание пули/гранаты
   (`GameScene.swift:413-419, 426-441`). Кадры — константа вида, их можно поднять в `static let`. **P3.**
5. **Построение отладочного оверлея и текстов — каждый кадр.** `GameScene.swift:1075-1077` безусловно вызывает
   `debugOverlay.removeAllChildren()` на каждом `update(_:)`, даже когда хитбоксы выключены;
   `updateDebugText()` (`:1062-1073`) пересобирает строку и пишет `inputLabel.text` каждый кадр;
   `hud.update(state:)` (`:139`, `HUDNode.swift:56-62`) присваивает **5** `SKLabelNode.text` без проверки
   изменения. Присваивание `text` у `SKLabelNode` инвалидирует глиф-кэш. Всё это работает и на скрытых нодах
   (`stepLabel`/`inputLabel`/`gamepadLabel` скрыты, но обновляются). **P3, code-confirmed; измеримый ли это
   прогиб на 60 Гц — runtime-hypothesis.**
6. **Сцена на весь жизненный цикл, пересобирается только уровень.** `SKScene` не пересоздаётся (единственный
   `GameScene(size:)` — `AppDelegate.swift:25`), поэтому «утечка сцены на уровень» из гипотез задания
   **опровергнута**: нет ни одного места, создающего новый `SKScene`. `transition()` делает
   `clearTransientObjects()` (`:634`, `:999-1009`) и `currentLevel.rootNode.removeFromParent()` (`:635`) перед
   заменой `currentLevel`. Отдельных детей сцены, которые переход не чистит, я не нашёл: `enemyBullets`,
   `bullets`, `grenades`, `explosions`, `grenadeTrailDots` — все в списке; пули/яйца/ракеты живут внутри
   `rootNode` старого рантайма. Ретейн-циклов не найдено (`Player` — не нода, `GamepadInput.scene` — weak,
   единственное `SKAction.run`-замыкание в `showBanner` с `[weak self]`, `GameScene.swift:677-681`).
7. **`currentLevel` — IUO** (`GameScene.swift:11`), присваивается только в `didMove(to:)` (`:60`). До `didMove`
   любое попадание в `fixedUpdate` → trap. `SKScene.update(_:)` до `didMove` не вызывается, так что сегодня это
   не активный баг, но `fatalError` в `TMXLevelRuntime.swift:53` означает: один отсутствующий/битый TMX в
   бандле = мгновенный краш, а не деградация. **P2 (обработка ошибок) / P3 (IUO).**
8. **Ресурсы: совпадение имён в бандле проверено.** На диске есть пары `bubble.png|.gif`,
   `rocks.png|.gif`, `turret_bullet.png|.gif`, но в `Resources` build phase попадают только `.png`
   (`bubble.gif`, `rocks.gif`, `turret_bullet.gif`, `light.png`, `ship_fire.png` — не в `pbxproj`; всего 151
   уникальная ссылка). **Коллизий базовых имён внутри бандла нет**, поэтому ссылка `L01S04.tmx` на
   `../images/rocks.gif` (имя берётся без расширения: `TMXTileMapRenderer.swift:73-75, 88-90`)
   **однозначно** резолвится в `rocks.png`. Прошлый §4.2 помечал это как «гипотезу до macOS» — статически она
   закрывается. Не используется кодом: `light.png`, `ship_fire.png`, `step5_tiles.png` (на диске), в `pbx` —
   без последствий.

---

### B-09 — `terrainRects`/`solidRects` пересобираются на каждое обращение

`TMXLevelRuntime.swift:97-130` — вычисляемые свойства, каждый доступ строит новый массив и, при наличии
исключений, прогоняет `flatMap { subtract(...) }` по всем прямоугольникам. Точки обращений внутри одного шага:
`GameScene.swift:271` (через `solidRects`), `:415`, `:469`, `:503` — по разу **на каждую пулю/гранату**, и
`TMXLevelRuntime.swift:159` — по разу **на каждое яйцо**. Плюс `:1081` на каждый кадр отрисовки.

Оценка стоимости сделана по факту, а не на глаз: при 11.5 rect'ах в среднем и ≤35 в худшем, плюс типично 0–8
снарядов, это ~10–40 перестроений по ~35 элементов в секунду на кадр — **десятки тысяч `CGRect` в секунду, но не
тысячи**. **Severity: P3** (чистая пересборка мусора, не тормоз; лечится одним `let` в начале `fixedUpdate` или
кэшем со сбросом по мутации). Прошлый аудит этого не касался.

---

### B-10 — Прочее (P3, собрано в кучу)

- `TMXLevelRuntime.swift:302` vs `:375`: в `capsule`-ветке `x` не ограничен `max(0, …)`, в `changing_room` —
  ограничен. Асимметрия поведения у левого края карты.
- `includedLevels` зашита как `L01S01…L05S25` (`GameScene.swift:56`), а не выведена из бандла. Пока все 124
  `nextLevel` резолвятся (проверено), ветка `enterContentComplete` с текстом «CONTINUES WITH …»
  (`GameScene.swift:748-753`) **недостижима** с текущими данными; единственный достижимый исход —
  `FULL COMBAT ABILITY` в зоне 124.
- `source_contains`-диспетчеризация по подстроке (`TMXLevelRuntime.swift:356-404`) чувствительна к порядку
  веток: `beam_` проверяется раньше `beacon_base`, и `stage_end` раньше `changing_room`. Новое имя вида
  `beam_changing_room_x` уйдёт в beam-поле молча. Хрупко, но сейчас однозначно (значения в данных —
  8 разных, пересечений по подстроке нет).
- Chrome-расхождение подтверждено независимо: `stepLabel.text = "STEP 9 · ALL 125 ORIGINAL ZONES"`
  (`GameScene.swift:68`) против `"STEP 10"` на титре (`GameScene.swift:838`) и `window.title =
  "Exolon Remake — Step 9 Rebase"` (`AppDelegate.swift:16`), при том что класс и ключи UserDefaults уже
  «Step 10» (`GameState.swift:24-31`). Это ровно прошлый §4.4 — не новая находка, но всё ещё верно.
- Целочисленных переполнений не найдено: `awardPoints` ограничен `min(999_999, …)` (`GameScene.swift:661`),
  `Int` — 64-битный; звёздный сид использует `&*`/`&+` с маской (`TMXLevelRuntime.swift:509`).
  Индексных выходов не найдено: `tubeFrames[7 - animationIndex]` защищён `min(7, …)`
  (`LevelObstacles.swift:90-92`), все `frames[...]` — из `[0..<N]` с `%`, `portals[(index+1) % portals.count]`
  под `guard portals.count >= 2` (`TMXLevelRuntime.swift:230`), `data[offset+3]` под guard'ом длины.
  `try!` и `as!` в дереве нет ни одного; `fatalError` — 5 штук, все либо загрузка TMX, либо
  `init(coder:)` (`grep` приведён в логе сессии).

---

## 3. Что на Linux статически проверяемо (и что я реально проверил)

**Проверено и закрыто без macOS** (воспроизведением алгоритмов на Python по 125 `.tmx` и чтением Swift):

| Класс проверки | Результат |
| --- | --- |
| Пересчёт `worldBottomLeft` / `trigger` / `exclusion` / `subtract` для будок | 5 будок, 0 срезанных клеток пола; контроль мутацией `−32` режет 1 клетку |
| Инвентарь `source_marker` по `sourceBlock` | `beacon_base` 13, `control_beacon` 13, `blinker` 19, `beam_up` 10, `beam_down` 10, `stage_end` 5, `changing_room` 4, `topdown_electro` 2 |
| Пары `beam_up`+`beam_down` | 10 карт, все 10 содержат оба |
| Целостность цепочки `nextLevel` | 125 узлов, 1 пустой (`L05S25`), 0 висячих ссылок, 0 циклов |
| Согласованность размеров слоёв | 125/125: `layer.w/h == map.w/h`, ровно один слой `Collision` |
| Разложения base64 (перенос строк, кратность 4, `w·h·4` байт) | 10/10 слоёв декодируются; `compression` нет ни у одного |
| Разрешение `tileset.imageSource` → бандл | 0 отсутствующих базовых имён; коллизий `png`/`gif` внутри бандла нет |
| Покрытие коллизиями, `groundY`, распределение зазоров | средн. 11.5 rect'ов; `groundY` ∈ {48,64,80,96}; зазоры кратны 16 px; 13 карт без коллизии у выхода |
| Согласованность спавна `vitorc` с коллизией | 35 / 59 / 29 / 2 (см. B-01) |
| Мёртвые поля и мёртвые API | `sourceHazards`, `stageExitMarkers`, `GamePersistence.loadCheckpoint`, `CocoonObstacle` (объявлен и не создаётся — в `buildObjectsFromTMX` есть `case "cocoon"` через `addDestructible`, отдельный класс не используется) |
| Переполнения/индексы/`try!`/`as!`/ретейн-циклы | не найдено (перечислено в B-10) |

**Что без macOS проверить нельзя (остается blocked):**

- собирается ли таргет (`xcodebuild -target Exolon`), и что реально покажет `GENERATE_INFOPLIST_FILE = NO`
  при `MARKETING_VERSION = 0.5` против `CFBundleShortVersionString = 0.3`;
- фактический рендер `SKTexture(imageNamed:)`, `SKTexture(rect:in:)`, `filteringMode = .nearest`, `anchorPoint`
  и z-порядок;
- реальные тайминги `SKView`/`preferredFramesPerSecond`, стоимость `removeAllChildren()` и переприсвоения
  `SKLabelNode.text`, цена декода полноэкранного бейдропа на смене зоны;
- поведение AppKit-событий (порядок `keyDown`/`keyUp`/`flagsChanged` для двух Option, пауза `SKView` без фокуса),
  `GCController`-обработчики и `controllerPausedHandler`;
- any «выглядит ли как оригинал»: 125 фонов — скриншоты, совпадение коллизий с нарисованным полом (B-02) видно
  только глазами.

---

## 4. Итог для планирования исправлений

1. **Прошлый P0 (C1) снять с рельса.** Дефекта вычитания пола нет; остаются три реальные, но более мелкие вещи:
   нулевой запас у 4 маркерных будок, незащищённый `minX - 16`, и вводящий в заблуждение комментарий
   (`TMXLevelRuntime.swift:297-300`). Чинить формулу «на глаз» (как советовал прошлый §10 «исправить на
   `trigger.minY + 16`») **нельзя** — это как раз и вырезало бы пол: контроль с `+16`/`−32` даёт 1–2 срезанные
   клетки пола.
2. Первым по ценности идёт **B-01** (смещение спавна на тайл в 90 из 125 карт) — это дефект данных компилятора,
   маскируемый рантаймом.
3. Затем **O7** (10 карт, 20 полей вместо 10) и **O8** (19 пушек, прикосновение = выстрел в никуда) — оба
   подтверждены и локализованы в одна-двумя строками.
4. **B-03** (ферма бонуса в зоне 124) чинится переносом `applyOriginalStageBoundaryIfNeeded` за guard
   достижения новой зоны либо сбросом позиции в `beginFromTitle`.
5. **B-04(a)/(c)** — дешёвые превентивные правки в загрузчике: поддержать `zlib`/`gzip` либо честно
   валидировать «карта непустая», и убрать `fatalError` из `TMXLevelRuntime.init` в пользу воспроизводимой
   ошибки уровня.
6. **B-05** — либо читать чекпойнт, либо перестать его писать и снять слово «CONTINUE» с титра.

Продуктовый код в этом маршруте не изменялся; изменений рабочего дерева нет
(`git status --porcelain` — только untracked workflow-артефакты).
