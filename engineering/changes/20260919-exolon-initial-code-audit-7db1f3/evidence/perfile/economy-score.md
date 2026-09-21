# Пер-файловый аудит: экономика очков / жизней / бонусов

HEAD `52795d13d879ad477a3023cae69978436ff82d1a`. Lane: economy-score.

Файлы среза, прочитаны построчно: `Exolon/GameCore/GameState.swift` (100),
`Exolon/GameCore/GameScene.swift` (1130), `Exolon/GameCore/HUDNode.swift` (64),
`Exolon/GameCore/GameConstants.swift` (34), `Exolon/GameCore/Levels/TMXLevelRuntime.swift`
(532, только секции начислений/маркеров), `Exolon/GameCore/Objects/LevelObstacles.swift`
(880, только значения `points`, `hitByBlaster`, `collectBonusIfTouched`, `triggerIfPlayerEnters`,
пикапы, инкубатор), `Exolon/GameCore/Player/Player.swift` (313, только `configure`/`respawn`/
`beginDeath`/`finishDeathAndRespawn`/экзоскелет/клампы), `Exolon/Platform/macOS/AppDelegate.swift`
(42), `Exolon/main.swift` (8), все 125 `Exolon/Resources/LxxSyy.tmx`.

Скрипты и замеры: `/tmp/lane-score/inventory.py`, `/tmp/lane-score/zones.py` (разбор TMX),
`/tmp/lane-score/econ.swift` (Swift 6.4 Linux, чистая реплика арифметики начислений без
SpriteKit). Ни один файл репозитория, кроме этого отчёта, не изменён; write-side git не трогался.
C1 (геометрия кабины) в этом отчёте не касается.

## Итог

Экономика в коде **односторонняя**: начислений 11 видов, списаний очков — **ноль**
(`awardPoints` отбрасывает `value <= 0`, `GameScene.swift:660-661`; `points -=` в дереве нет).
Списываются только жизни и боезапас. Потолок `min(999_999, …)` (`:662`) защищает от переполнения
— это отдельно подтверждено как **верное**.

Детерминированный пул начислений на 100 % зачистку всех 125 зон (посчитан по фактическим
маркерам TMX, `inventory.py`):

| компонент | количество | × очки | итого |
|---|---:|---:|---:|
| турели (граната) | 37 | 150 | 5 550 |
| cocoon/radar/rocket/gate (граната) | 1+12+29+6 = 48 | 150 | 7 200 |
| инкубаторы (граната) | 22 | 150 | 3 300 |
| бонус-регионы дабл-лончера | 19 | 1 000 | 19 000 |
| силовые поля `beam_up`/`beam_down` | 10+10 = 20 | 1 000 | 20 000 |
| зелёные маяки наведения | 13 | 1 000 | 13 000 |
| яйца-сферы (22 × 8) | 176 | 50 | 8 800 |
| бонусы стадии, 5 границ, lives=9 | 5 | 9 000 | 45 000 |
| **итого статика** | | | **121 850** |

Всё сверх этого — фарм возрождающихся целей (камикадзе 150, выпущенные сферы 50, ракеты
дабл-лончера 50), ограниченный только боезапасом: при 99 патронах это 14 850 очков за зону в
один выстрел и **29 700** с экзоскелетом (двойной выстрел стоит один патрон,
`GameScene.swift:341-351`). 31 зона из 125 вообще не содержит ни одного начисляемого объекта
(в т.ч. 24, 49, 74, 99, 124 — стадии, где весь бонус = `lives*1000`).

Находок: **13 — 5 × P2, 8 × P3, P0/P1 нет**. Главные:

1. **ECO-01 (P2)** — ферма бонуса стадии в зоне 124 (`B-03`) подтверждена независимо:
   **+9 000 за цикл, 107 циклов от 45 000 до потолка 999 999**, и результат персистентен
   (`Exolon.Step10.HighScore`), а кнопки сброса рекорда в продукте нет.
2. **ECO-02 (P2)** — бонус стадии привязан к `player.position.x > 510`, а не к stage-end-триггеру;
   5 маркеров `blk_stage_end` разбираются в `stageExitMarkers` (`TMXLevelRuntime.swift:30, 370`)
   и **никогда не читаются**.
3. **ECO-03 (P2)** — из четырёх пунктов бонус-секции оригинала реализован один: `10 000 bravery`
   и timed bonus `0/1000/3000/5000/7000` в дереве отсутствуют (grep `bravery|10_000|7_000|5_000|3_000`
   → 0 совпадений).
4. **ECO-04 (P2)** — экзоскелет не снимается на границе стадии: `setExoskeleton(false)` есть
   только в `restartFromBeginning` (`:963`), в `applyOriginalStageBoundaryIfNeeded` — нет.
5. **ECO-05 (P2)** — контакт со сферой/камикадзе **платит очками** и не защищён ни
   `invulnerability`, ни `isDying` (`:580-598` → `awardPoints` до `hitPlayer()`), т.е. смерть
   приносит очки, а 0.4 с защиты после респауна — бесплатные начисления.

Контрольные случаи, которые я отдельно **подтвердил как корректные** (чтобы не раздувать
находки): отрицательных начислений нет; переполнения `points` нет; каждое лицо отдаёт своё
начисление ровно один раз (`isActive`/`isAlive`-гейты в `ForceFieldBarrier.hitByBlaster`
`LevelObstacles.swift:777-789`, `GreenMissileGuidance.destroy` `:810-821`,
`DoubleLauncherObstacle.collectBonusIfTouched` `:718-723`, `destroyWithGrenade` `GameScene.swift:481-488`
с `guard grenade.isAlive` + `continue`); сферу внутри целого инкубатора **нельзя** прострелить
(порядок проверок в `updateBullets`: яйцо → поле → `hitIndestructible`, а инкубатор входит в
`solidRects`/`hitIndestructible`, `TMXLevelRuntime.swift:126-129` — пуля гасится об оболочку до
камеры); ни один `vitorc`-спавн не имеет `x > 510` (перебор 125 карт, max x=64 px + 24), поэтому
в зонах 24/49/74/99 бонус гасится `transition` и начисляется ровно один раз; `L05S25.tmx` —
**единственная** карта из 125 без свойства `nextLevel`, остальные 124 образуют строгую цепочку
`LxxS01…LxxS25 → L(xx+1)S01` без разрывов; гранаты не повреждают силовое поле (его нет в списке
`updateGrenades`) — соответствует «Grenades are not the intended shortcut».

## Таблица начислений/списаний

Все строки — `Exolon/GameCore/GameScene.swift`, если не указано иное. «Состояние» — что обязано
быть истинно в момент срабатывания.

| # | file:line | событие | сумма | требуемое состояние |
|---|---|---|---:|---|
| A1 | `:301` ← `TMXLevelRuntime.swift:219-224` | пересечение бонус-региона дабл-лончера | **+1 000** | `launcher.isActive` (после срабатывания `false`, `LevelObstacles.swift:718-723`) **И** `player.movementHitbox ∩ hitbox(64×48 корпуса)`; `flowState ∈ {playing, playerDead, respawning}`; `isDying` **не** проверяется |
| A2 | `:379` ← `LevelObstacles.swift:147-152` | сбитая пуля дабл-лончера | **+50** | `bullet.isAlive && hostile.canBeShotDown` (`.doubleLauncher`) **И** пересечение хитбоксов; `kind == .turret` → `canBeShotDown=false`, `pointsWhenShotDown=0` (`:141-142`) — начисления нет |
| A3 | `:386` ← `LevelObstacles.swift:432` | пуля по камикадзе (`bubble`) | **+150** | `bubble.isAlive && bullet.isAlive` и пересечение; дальше `continue`, поэтому второй пулей того же выстрела то же лицо не оплачивается |
| A4 | `:394` ← `LevelObstacles.swift:562` | пуля по сфере (`egg`) | **+50** | `egg.isAlive`; камера защищена оболочкой инкубатора (см. контрольные случаи) |
| A5 | `:403` ← `LevelObstacles.swift:766-789` | разрушено силовое поле | **+1 000** | ровно на 25-м попадании: `hitPoints 25→0` при `isActive`; `hitByBlaster()` возвращает `true` один раз, затем `isActive=false` |
| A6 | `:465` ← `TMXLevelRuntime.swift:193-205` | граната по зелёному маяку наведения | **+150**, **+850** если живёт ракета (1 000) | `guidance.isActive && grenade.hitbox ∩ beacon box`; 850 добавляется только при `homingMissiles.filter{isAlive}` ≠ ∅ |
| A7 | `:486` (`destroyWithGrenade`, вызовы `:440`, `:447`, `:454`) | граната по турели / разрушаемому / инкубатору | **+150** | `grenade.isAlive` (guard `:482`) **И** `target.isActive`; `continue` после ветки → не более одного начисления на гранату |
| A8 | `:583` | **контакт** игрока с камикадзе | **+150** | `player.damageHitbox ∩ bubble.hitbox`; гейтов `invulnerability`/`isDying`/`hasExoskeleton` **нет**; затем `hitPlayer()`, который может и не сработать → очко без риска |
| A9 | `:593` | **контакт** игрока со сферей | **+50** | то же; `return` после первого совпадения → ≤1 начисление такого рода за фикс. шаг |
| A10 | `:627` | граница стадии (зона 24/49/74/99/124), вызов из `checkScreenExit` `:612` | **+ lives × 1 000** (0…9 000) | `completedZone ∈ [24,49,74,99,124]` **И** `player.position.x > 510`; `lives` берётся **до** прибавления |
| A11 | `:628` | та же граница | **+1 жизнь** | `lives < 9`; при `lives == 9` жизнь **не** даётся (кап 9 по доку) |
| A12 | `:663-665` | каждое начисление, побившее рекорд | очков 0; запись `highScore = points` + `persistence.saveHighScore` | `points > highScore`; выполняется на **каждом** award, а не раз за забег |
| A13 | `:724-726` | `enterGameOver` | очков 0; повторный фолд рекорда | `points > highScore` — избыточно после A12, двойного начисления не создаёт |

Отдельно: `showBanner("+1000")` (`:302`) визуализирует только A1; A5/A6/A10 баннера не имеют.

Списания и сбросы ресурсов:

| # | file:line | событие | дельта | требуемое состояние |
|---|---|---|---|---|
| D1 | `:322` | смерть завершена (труп приземлился + 70 фикс. шагов) | `lives = max(0, lives − 1)` | `player.isDying && player.isGrounded && deathGroundTimer ≥ 70/60`; при `lives == 0` → `enterGameOver` и возврат (`:323-325`), refill не выполняется |
| D2 | `:351` | нажатие FIRE | `ammo −= 1` | `fireJustPressed && ammo > 0`; **одна** единица за нажатие даже при двух выпущенных пуле (`:345-349` добавляет вторую при `hasExoskeleton`) |
| D3 | `:359` | нажатие GRENADE | `grenades −= 1` | `grenadeJustPressed && grenades > 0 && grenades.isEmpty` (одна активная граната) |
| D4 | `:526` | жёлтый ящик | `grenades = 10` (**абсолют**, не `+=`) | `pickup.isActive && movementHitbox ∩ hitbox`; `isDying` не проверяется |
| D5 | `:533` | белый ящик | `ammo = 99` (**абсолют**) | то же; `collect()` деактивирует ящик (`LevelObstacles.swift:223-228, 245-250`) → «refill, not additive» соблюдено |
| D6 | `:330-331` | смерть (не последняя) | `ammo = 99`, `grenades = 10` | после D1 |
| D7 | `:629-630` | граница стадии | `ammo = 99`, `grenades = 10` | вместе с A10 |
| D8 | — | списаний `points` в дереве нет ни одного | 0 | — |

Всего источников начисления: 11 (A1–A11) + 2 служебных (A12, A13).

Начисления, **гейтованные неуязвимостью/экзоскелетом** — сводка по фактическим веткам:

| ветка урона | `invulnerability` | `isDying` | `hasExoskeleton` | `testInvulnerabilityEnabled` | начисление при блокировке |
|---|---|---|---|---|---|
| пуля врага `:509` | ✓ проверка | ✓ | ✗ | ✓ (в `hitPlayer` `:601`) | нет |
| мина `:545-554` | ✗ до срабатывания, ✓ до удара | ✗ | ✓ `continue` **до** `triggerIfPlayerEnters` | ✓ | нет (мины очков не дают) |
| пилон `:556-566` | ✓ | ✓ | ✓ `continue` | ✓ | нет |
| силовое поле `:568-572` | ✓ | ✓ | ✗ | ✓ | нет |
| `sourceHazards` `:574-578` | ✓ | ✓ | ✗ | ✓ | нет |
| ракета наведения `:539-543` | ✗ (гасится всегда) | ✗ | ✗ | ✓ | нет |
| камикадзе `:580-588` | ✗ | ✗ | ✗ | ✓ | **+150 даже когда удар заблокирован** |
| сфера `:590-598` | ✗ | ✗ | ✗ | ✓ | **+50 даже когда удар заблокирован** |
| бонус-регион лончера `:299` | ✗ | ✗ | ✗ | ✗ | **+1 000 в любом состоянии** |
| пикапы `:522-536` | ✗ | ✗ | ✗ | ✗ | ресурсы в любом состоянии |

То есть инверсия гейта в строках «камикадзе» и «сфера» и есть ECO-05: единственные начисления,
которые **растут** от неуязвимости игрока, — это начисления за контакт со смертью.

## Матрица сбросов

Легенда: `R` = сброс на стартовое значение, `S` = выживает, `W` = пишется в UserDefaults,
`C` = удаляется из UserDefaults, `−` = не трогается, `0` = обнуляется в ноль.

События и строки, которые их выполняют:

| код | событие | вход | якоря |
|---|---|---|---|
| E1 | relaunch / первый пуск сцены | `didMove(to:)` | `:55, 59` → `loadPersistentState` `:685-694` |
| E2 | титр → старт | FIRE в `.title` | `:161-167` → `beginFromTitle` `:708-717` |
| E3 | смена зоны | `x > 510` + валидный `nextLevel` | `:609-619` → `transition` `:633-658` |
| E4 | смерть (не последняя) | 70 шагов на земле | `updateDeathSequence` `:311-336` |
| E5 | game over | `lives == 0` | `enterGameOver` `:719-736` |
| E6 | restart (из паузы или game over) | FIRE на пункте RESTART | `:180-188`, `:193-199` → `restartFromBeginning` `:950-989` |
| E7 | content complete | `next` пуст/вне 125 | `enterContentComplete` `:738-759` |
| E8 | content complete → титр | FIRE | `:201-207` → `showTitleAfterContentComplete` `:761-767` |
| E9 | пауза / снять паузу | P | `:917-944` |

| поле | E1 | E2 | E3 | E4 | E5 | E6 | E7 | E8 | E9 |
|---|---|---|---|---|---|---|---|---|---|
| `points` | R (`:693`→`GameState.swift:96`) | − | − | − | − | R (`:960`) | − | − | − |
| `lives` | R (`GameState.swift:97`) | − | − | −1 (`:322`) | − | R | − | − | − |
| `ammo` | R (`:94`) | − | − | 99 (`:330`) | − | R | 99 (`:629`) | − | − |
| `grenades` | R (`:95`) | − | − | 10 (`:331`) | − | R | 10 (`:630`) | − | − |
| `zone` | R (`:98`) | − | `zoneNumber(for:)` (`:641`) | − | − | R | − | − | − |
| `highScore` (RAM) | ← диск (`:689`) | − | − | − | ← диск (`:724-726`) | ← диск (`:961`) | − | − | − |
| `Exolon.Step10.HighScore` | читается | W (A12) | W (A12) | − | W (A13) | читается | W (A12) | − | − |
| 6 ключей чекпойнта | **C** (`:690`) | W если `!hasSavedCheckpoint` (`:716`) | W (`:657`) | W (`:335`) | **C** (`:722`) | C (`:951`) + W (`:985`) | W (`:740`) | − | − |
| `hasSavedCheckpoint` | `false` (`:691`) | − | `true` (`:705`) | `true` | `false` (`:723`) | `false`→`true` | `true` | − | − |
| `flowState` | `.title` (`:38` init) | `.playing` (`:710`) | `.playing` (`:650`) | `.playerDead`→`.respawning` (`:605`, `:334`) | `.gameOver` (`:720`) | `.playing` (`:968`) | `.contentComplete` (`:739`) | `.title` (`:764`) | `.paused` (`:920`) |
| `invulnerability` | 0 (init `:46`) | − | **0** (`:649`) | 0.4 с (`:333`) | 0 (`:721`) | 0 (`:966`) | − | − | **заморожен** (декремент `:213` недостижим из `case .paused`, `return` на `:191`) |
| `player.hasExoskeleton` | false (новый `Player`) | − | S | S | S | **false** (`:963`) | S | S | S |
| `testInvulnerabilityEnabled` | false (init `:45`) | − | S | S | S | **S — не сбрасывается** | S | S | переключается в меню паузы (`:186-188`) |
| `currentLevelName` | `L01S01` (`:692`) | − | `next` (`:637`) | − | − | `L01S01` (`:956`) | − | − | − |
| `player.position` | spawn (`:62-63`) | **−** (`:708-717` не зовёт `configure`) | spawn/`carriedY` (`:643-647`) | `respawn()` (`:332`→`Player.swift:227-240`) | − | spawn (`:964`) | − | − | − |
| разрушенные объекты зоны | новый уровень | − | **новый уровень → всё возрождается** (`:634`) | S — зона **не** пересобирается (`:328-329`) | − | новый `L01S01` | − | − | − |
| пули/гранаты/взрывы | чистая сцена | − | `clearTransientObjects` (`:634`, `:1000-1010`) | − | − | `:953` | − | − | − |

Ключевой вывод матрицы: **E2 — единственное «начать игру» из титра, которое не является new game.**
`beginFromTitle` (`:708-717`) не трогает ни один из 12 полей выше: ни `resetForNewGame()`, ни
`player.configure`, ни `transition`, ни `setExoskeleton`. Он только снимает `isPaused` и ставит
`flowState = .playing`. Все остальные «стартовые» пути (`E1`, `E6`) вызывают `resetForNewGame()`.
Именно это и превращает E7→E8→E2 в цикл, а не в «возврат к началу», как требует
`ORIGINAL_MECHANICS.md` («Zone 124 … then returns the game to the beginning»).

## Persisted keys

Область: `UserDefaults.standard`, бандл `com.exolon.remake` (`project.pbxproj:1425, 1444`),
plist-домена `~/Library/Preferences/com.exolon.remake.plist` на macOS; sandbox-entitlements в
цели нет (`.entitlements` в репозитории отсутствует), `Info.plist` секций контейнера не задаёт.
Других механизмов персистентности нет: `grep -rn "UserDefaults\|@AppStorage\|NSUbiquitous\|Keychain"
--include=*.swift .` даёт ровно 2 совпадения, оба в `GameState.swift:34, 36`.

| ключ (тип) | объявлен | пишется | читается | статус |
|---|---|---|---|---|
| `Exolon.Step10.HasCheckpoint` (Bool) | `GameState.swift:25` | `:54` (из 5 мест см. ниже) | **только `:41` внутри мёртвой `loadCheckpoint()`** | write-only |
| `Exolon.Step10.LevelName` (String) | `:26` | `:55` | только `:42` (мёртвый) | write-only |
| `Exolon.Step10.Ammo` (Int) | `:27` | `:56` | только `:46` (мёртвый) | write-only |
| `Exolon.Step10.Grenades` (Int) | `:28` | `:57` | только `:47` (мёртвый) | write-only |
| `Exolon.Step10.Points` (Int) | `:29` | `:58` | только `:48` (мёртвый) | write-only |
| `Exolon.Step10.Lives` (Int) | `:30` | `:59` | только `:49` (мёртвый) | write-only |
| `Exolon.Step10.HighScore` (Int) | `:31` | `:76` ← `GameScene.swift:665` (каждое A12) и `:726` (E5) | `:72` ← `GameScene.swift:689` (E1) и `:961` (E6) | **единственный рабочий ключ** |

Мои собственные greps (не с чужих слов):

```
$ grep -rn "loadCheckpoint" --include=*.swift .
./Exolon/GameCore/GameState.swift:40:    func loadCheckpoint() -> GameCheckpoint? {
$ grep -rn "saveCheckpoint" --include=*.swift .
./Exolon/GameCore/GameState.swift:53:    func saveCheckpoint(_ checkpoint: GameCheckpoint) {
./Exolon/GameCore/GameScene.swift:335:        saveCheckpoint()          # E4 смерть/респаун
./Exolon/GameCore/GameScene.swift:657:        saveCheckpoint()          # E3 переход зоны
./Exolon/GameCore/GameScene.swift:696:    private func saveCheckpoint() {   # обёртка сцены
./Exolon/GameCore/GameScene.swift:704:        persistence.saveCheckpoint(checkpoint)  # фактический вызов
./Exolon/GameCore/GameScene.swift:716:        if !hasSavedCheckpoint { saveCheckpoint() }   # E2 условно
./Exolon/GameCore/GameScene.swift:740:        saveCheckpoint()          # E7 content complete
./Exolon/GameCore/GameScene.swift:985:        saveCheckpoint()          # E6 restart
$ grep -rn "clearCheckpoint" --include=*.swift .
./Exolon/GameCore/GameState.swift:62
./Exolon/GameCore/GameScene.swift:690   # E1 relaunch: всё, что осталось от прошлого процесса
./Exolon/GameCore/GameScene.swift:722   # E5 game over
./Exolon/GameCore/GameScene.swift:951   # E6 restart
```

**B-05 подтверждён: вызовов `loadCheckpoint()` — 0, определений — 1.** Из 7 объявленных ключей
6 пишутся и никогда не читаются (audit N-2 по количеству ключей тоже верен: 7, а не 6).
`clearCheckpoint()` не трогает `HighScore` — это единственное, что переживает relaunch.
Заметка по честности формулировки: строка на титре `CONTINUE · ZONE %03d` (`:901-903`) зависит от
`hasSavedCheckpoint`, а не от диска; на свежем пуске `loadPersistentState` ставит
`hasSavedCheckpoint = false` (`:691`), поэтому «CONTINUE» может появиться **только** после E7→E8.
Формально надпись не лжёт (в памяти действительно текущая зона 124), но обещанного «продолжения с
диска» в продукте нет ни в одном пути.

Инъектируемость `GamePersistence.init(defaults:)` (`:36`) не используется нигде: Swift-тестов в
проекте нет (в `project.pbxproj` один `productType = com.apple.product-type.application`
(`:1041`), test-target отсутствует; `find -name "*Tests*"` бьёт только в `factory/`, это
Python-фабрика, не продукт). Вся экономика держится на ручных числах без единого автотеста.

Побочный, но реальный эффект A12: запись `saveHighScore` происходит на **каждом** рекордном
начислении, без `synchronize()`. Значения оседают в кэше `cfprefsd` процесса; принудительное
убийство процесса между начислениями может их потерять — это уже поведение macOS,
**нужен macOS**.

## Окна двойного начисления

D-1. **Зона 124: `.contentComplete → .title → beginFromTitle` (ECO-01 = B-03). Реальный путь,
код-трассировка полная; живой прогон — нужен macOS.**

Трассировка по строкам:

1. `:308` `if !player.isDying { checkScreenExit() }` → `:610` `guard player.position.x > 510`.
2. `:611` `let next = currentLevel.nextLevelName` — у `L05S25.tmx` свойства `nextLevel` нет
   (проверено: единственный случай из 125), значит `TMXLevelRuntime.swift:96` → `""`.
3. `:612` **до** guard'а вызывается `applyOriginalStageBoundaryIfNeeded(completedZone: 124)` →
   `:627` `awardPoints(lives * 1_000)` = +9 000, `:628` жизнь (не даётся при 9), `:629-630` refill.
4. `:614-617` `guard !next.isEmpty … else { enterContentComplete; return }` → `:739-741`
   `flowState = .contentComplete`, `saveCheckpoint()`, `setGameplayNodesPaused(true)`.
5. FIRE (`:201-207`, edge-лatch `menuFireWasPressed` работает — удержание не пролистывает) →
   `:761-767` `flowState = .title`. Позиция `player.position` **не** меняется, `currentLevel`
   **не** пересоздаётся.
6. FIRE на титре (`:161-167`) → `:708-717` `beginFromTitle`: только `flowState = .playing` +
   unpause. `hasSavedCheckpoint == true`, поэтому даже `saveCheckpoint()` не перпишется.
7. Следующий фикс. шаг: `:209` → `case .playing …: break` → снова `:308` → `:610`
   (x остаётся > 510: `Player.swift:128` кламит в `[24, 544]`, а `beginFromTitle` не зовёт
   `configure`) → **A10 начисляется повторно** → снова шаг 4.

Замер репликой (`/tmp/lane-score/econ.swift`, Swift 6.4 Linux, только арифметика):

```
A) 5 границ стадии без смертей: +9000 ×5 = 45000, жизнь не добавлена ни разу (lives == 9)
B) те же 5 границ при lives=3: 3000+4000+5000+6000+7000 = 25000, lives=8
C) цикл в зоне 124: 107 циклов от 45 000 до 999 999; persistedHighScore=999 999;
   checkpointWrites=108; 2 нажатия FIRE на цикл; ammo/grenades/lives каждый цикл = 99/10/9
D) потолок на зону при 99 патронах: 14 850 одиночным, 29 700 экзоскелетом
```

Три следствия, которые стоит держать вместе с цифрой: (а) цикл — это одновременно бесплатный
«continue» (refill 99/10 + жизнь к 9 каждый круг), поэтому game over в зоне 124 недостижим;
(б) каждый круг пишет чекпойнт и рекорд, то есть испорченный счёт **переживает перезапуск**;
(в) сбросить рекорд нечем — в UI нет ни одного пути к `HighScore` кроме двух чтений.
Время живого прогона (107 × 2 нажатия плюс 4 фикс. шага на цикл) — **нужен macOS**.

D-2. **Начисления за контакт во время неуязвимости и во время смерти (ECO-05). Реальный путь,
подтверждён порядком кадров; величина — нужен macOS.**
`:580-598` вызывают `awardPoints` **до** `hitPlayer()`, а `hitPlayer` (`:601-603`) имеет оба
гейта (`testInvulnerabilityEnabled`, `invulnerability <= 0`, `!player.isDying`). Значит: 0.4 с
защиты после респауна (`:333`) и всё время падения трупа (до 70+ шагов после приземления)
каждый контакт оплачивается как убийство. Ограничение — `return` после первого совпадения:
≤1 такое начисление за фикс. шаг, т.е. теоретический темп до 9 000 очков/сек при плотном
рое; сколько их на практике — **нужен macOS**.

D-3. **TEST INVULNERABILITY как множитель, а не как чит-без-очков. Реальный путь.**
`:601` гасит только урон; ни один из 11 источников начисления не проверяет
`testInvulnerabilityEnabled`. Состояние к тому же переживает restart (матрица, строка
`testInvulnerabilityEnabled`), т.е. «новая игра» из меню паузы стартует уже с включённой
неуязвимостью. Документ прямо называет этот режим неоригинальным, но не оговаривает, что он
делает весь пул начислений безрисковым.

D-4. **Двойной выстрел экзоскелета: 2 пули за 1 патрон (`:341-351`). Реальный путь, код.**
Это не двойное начисление одного события, а двойной потолок начислений на единицу ресурса;
в примере с камикадзе — 29 700 против 14 850 за зону при одном и том же `ammo = 99`. Для
силового поля это, наоборот, совпадает с оригиналом («two bullets count separately»,
`LevelObstacles.swift:777-789` — минус по `hitPoints` на каждую пулю).

D-5. **Бонус-регион лончера пересобирается вместе с зоной (не дефект, но стоит знать).**
`transition` (`:639`) создаёт новый `TMXLevelRuntime`, поэтому все `isActive=false` лица в новой
зоне снова платят. Строгая цепочка `nextLevel` (проверено на 125 картах, разрывов нет) не даёт
вернуться в пройденную зону, так что «один и тот же регион дважды» в легальном забеге
невозможно. Исключение — только D-1, и там уровень **не** пересобирается, т.е. 1 000 из A1
по циклу не капает; капает A10.

D-6. **`applyOriginalStageBoundaryIfNeeded` стоит до guard'а перехода (ECO-02). Реальный путь,
код.** Для зон 24/49/74/99 это безопасно: `transition → configure → respawn` возвращает игрока на
спавн, а ни один `vitorc` не лежит правее 510 (перебор 125 карт). Но сам факт, что вызов
висит **до** проверки `next`, означает: любой будущий путь, который «выйдет» из зоны 24/49/74/99
без `transition` (посмертный респаун на границе, кат-сцена, отладочный warp), унаследует ферму
D-1. Отдельно: бонус получают и те, кто stage-end-маркера не касался, потому что `stageExitMarkers`
не читается нигде.

D-7. **Пауза в `.respawning` замораживает защиту (ECO-10). Реальный путь, код.**
`case .paused: … return` (`:191`) стоит выше декремента `:213`, поэтому 0.4 с
`postDeathProtectionDuration` не убывают в паузе; суммарно это < 0.4 с на жизнь, не ферма, но
оно и не «нормальный» режим.

Проверенные и **опровергнутые** кандидаты (чтобы не унаследовать чужие ложные находки):
дабл-оплата одного лица двумя пулями того же выстрела (гасится `isAlive`-гейтом + `continue`);
повторные 1 000 за одно поле (одноразовый `isActive`); повторные 1 000 за один маяк
(`guidance.destroy()` + `first(where:)`); 1 000 за один и тот же лончер (`collectBonusIfTouched`
ставит `isActive=false`, `:718-723`); 150+850 дважды за одну гранату (ветки гранат идут через
`continue`, `:440-466`); «просмотр» 850 без живой ракеты (`positions.isEmpty ? 0 : 850`,
`TMXLevelRuntime.swift:205`); прострел сферы сквозь оболочку инкубатора (см. контрольные
случаи в «Итоге»); двойной фолд рекорда в `enterGameOver` (пишет то же значение, очков не
меняет); двойное списание жизни (счётчик живёт в одном месте — `:322`).

## Отличия от оригинала

Ожидаемое — цитаты из `ORIGINAL_MECHANICS.md`; фактическое — по строкам выше.

| раздел дока | ожидание | в коде | вердикт |
|---|---|---|---|
| Global structure | 9 жизней / 99 / 10 | `GameState.swift:81-83`, `:93-99` | ✓ |
| Global structure | «Death consumes one life and refills ammo to 99 and grenades to 10» | `:322, 330-331` | ✓ |
| Global structure | «The original rebuilds the current zone after death» | зона **не** пересобирается (`:328-329`, комментарий к делу); разрушенные лица не возвращаются | ✗ осознанное (задокументировано в коде, но счёт на зону становится одноразовым) |
| Global structure | «Normal screen entry gives no invulnerability» | `:649` `invulnerability = 0` | ✓ |
| Blaster | «Double-barrel launcher projectiles … award 50 points» | `LevelObstacles.swift:147-152`, `:379` | ✓ |
| Blaster | «Ordinary fixed-turret bullets are not shootable» | `:141-142` (`canBeShotDown=false`, 0 очков) | ✓ |
| Blaster | «force field … disappears on the 25th hit; award is 1000» | `hitPoints = 25`, `:403` | ✓ |
| Grenade | «Generic destroyable object: 150 points» | `destroyWithGrenade` `:486` | ✓ |
| Grenade | «One active grenade at a time» | `:355` `grenades.isEmpty` | ✓ |
| Stationary gun machine | «worth 150 points through the generic destroyable table» | `:440` → `:486` | ✓ |
| Double-barrel launcher | «Crossing the launcher's **invisible bonus region** awards 1000 points once» | регион = видимый корпус 64×48 (`LevelObstacles.swift:695, 718-723`); «once» соблюдено | ✗ частично (не невидимый регион; при этом лончер нельзя ни подбить, ни даже остановить пулей — его нет ни в `hitIndestructible`, ни в `updateGrenades`) |
| Rocket tower | «Rockets are destroyable by blaster and award 50 points», порог 30 px, vx −2 | реализации нет: `grep -i rocketTower` = 0, а TMX-объект `rocket` (29 шт.) — это статический разрушаемый объект за 150 (`TMXLevelRuntime.swift:264-271`) | ✗ |
| Green beacon | «150 + 850 = 1000 total in the normal case» | `TMXLevelRuntime.swift:205` | ✓ |
| Mines / Pumps | «routes damage through `KillPlayer_unless_Exoskeleton`» | `:546`, `:557` — но `continue` **до** `triggerIfPlayerEnters`, поэтому с костюмом мина не расходуется и остаётся вооружённой | ✗ частично (очки не затронуты) |
| Sphere homes | «blaster hit destroys a sphere for 50 points», 8 сфер/дом | `LevelObstacles.swift:539`, `:562` | ✓ |
| Sphere homes | «contact destroys the sphere and kills the player» | контакт дополнительно даёт **+50** (`:593`) | ✗ лишнее начисление |
| Flying enemies | «Blaster kill = 150 points»; «Contact kills the player and removes the enemy» | `:432` ✓ / контакт дополнительно **+150** (`:583`) | ✗ лишнее начисление |
| Ammo / grenade boxes | «sets ammo to exactly 99 / grenades to exactly 10 … These are refills, not additive pickups» | `:526, 533` абсолютные присваивания | ✓ |
| Exoskeleton | «It persists through deaths until the end of the current 25-zone stage» / «At stage end the exoskeleton flag is cleared» | через смерть живёт ✓ (E4/E5 его не трогают), на границе стадии **не** снимается (`:621-631`) | ✗ |
| Exoskeleton | «Having the exoskeleton forfeits the 10,000-point bravery bonus» | ни bravery-бонуса, ни флага «костюм брался» в состоянии | ✗ |
| Exoskeleton | «double blaster fire» | `:345-349` ✓, но стоит 1 патрон вместо 2 (`:351`) | ✗ частично |
| Vertical force field | «13 trigger pulls with double-shot because two bullets count separately» | 25 × `hitByBlaster` на пулю | ✓ |
| Timed indestructible pursuer | «700-loop threshold», появляется справа, неуязвим | нет ни `zoneTimer`, ни pursuer (grep = 0) | ✗ |
| Stage ends | «Award 1000 points per remaining life» | `:627` | ✓ |
| Stage ends | «If no exoskeleton was taken, award 10,000 bravery points» | отсутствует | ✗ |
| Stage ends | «Timed bonus cursor can add 0/1000/3000/5000/7000» | отсутствует | ✗ |
| Stage ends | «Add one life, capped at 9» | `:628` | ✓ (при `lives == 9` жизнь не даётся — кап работает) |
| Stage ends | «Clear exoskeleton» | отсутствует | ✗ |
| Stage ends | «Restore ammo=99 and grenades=10» | `:629-630` | ✓ |
| Stage ends | «Reaching the stage-end trigger opens the bonus sequence» | открывает любой выход `x > 510`; `stageExitMarkers` (5 маркеров разобраны) не читается | ✗ |
| Stage ends | «Zone 124 displays FULL COMBAT ABILITY and then **returns the game to the beginning**» | оверлей есть (`:743-750`), возврата нет: FIRE → титр (`:761-767`) → FIRE → та же зона 124 (`:708-717`) → D-1 | ✗ корень фермы |
| Walkthrough checkpoints | Zone 002 teleport / 003 flying enemy / 005 birthpod / 006 launcher / 007 mines / 008 beacon / 009 changing room / 023 gun machine / 024 bonus / 035 force field / 059 teleport+beacon / 086–088 | по факту в TMX: 002 `teleport` ✓, 003 `bubble_creator` ✓, 005 `incubator` ✓, 006 `double_launcher` ✓, 007 `mine` ✓, 008 `control_beacon` ✓, 009 `capsule` (кабина) ✓, 023 `turret` ✓, 024/049/074/099/124 `blk_stage_end` ✓, 035 `beam` ✓, 059 `beacon`+`teleport` ✓, 086 `teleport` + 088 `beacon` ✓, 043 `beacon`+`mine` ✓ | ✓ по маркерам (это проверка наличия, не поведения) |
| Current remake audit rule | каждый action-маркер должен иметь runtime | из 127 `source_marker` (сумма всех `sourceBlock` = 127 ✓) ветку в `TMXLevelRuntime.swift:356-407` не имеют `blk_waggon` (24), `blk_gunMachine_BOTTOM` (18), `blk_mushroom` (9) = 51 шт. — они молча проваливаются сквозь if/else-цепочку; `blk_blinker` (19) и `blk_topdown_electro` (2) обработаны явными `break` с комментарием (`:361-368`). Орудия машины при этом существуют отдельно как объект `turret` (37 шт.), так что это аннотация слоя, а не потерянный механизм. К очкам ни один `sourceBlock` не относится | вне скоупа этого отчёта, отмечено как контекст |

Итоговое расхождение по балансу: легальный максимум детерминированных очков в этом билде —
**121 850**, из которых по доку должно быть ≈ 45 000 (lives) + 50 000 (bravery) + до 35 000
(timed bonus) = ~130 000 только на бонусах стадии. Здесь bravery и timed бонус равны нулю, зато
есть неучтённые оригиналом 150/50 за каждый смертельный контакт. Прямой «итог» сравнимой цифры
док не содержит — сличение по пунктам, не по сумме.

Вердикт: fail

Обоснование: из четырёх обязательных компонентов бонус-секции стадии реализован один
(`lives*1000`); бонус открывается не stage-end-триггером, а произвольным выходом `x > 510` при
мёртвом `stageExitMarkers`; экзоскелет не снимается на границе стадии, из-за чего и правило
«bravery forfeit» нечем выразить; контакт со сферой/камикадзе платит очками, которых в оригинале
нет, и платит даже тогда, когда удар заблокирован неуязвимостью или смертью; в зоне 124
`FULL COMBAT ABILITY` не возвращает игру к началу, а закрывает цикл `.contentComplete → .title →
beginFromTitle`, дающий +9 000 за два нажатия с персистентной записью рекорда и без какого-либо
пути сброса; вся экономка не имеет ни одного Swift-теста. Не является дефектом и подтверждено
контрольными случаями: отсутствие отрицательных списаний, потолок 999 999, однократность всех
объектных начислений, абсолютные (не аддитивные) пикапы, корректный `lives*1000 → +1 life`
порядок и кап жизни 9.
