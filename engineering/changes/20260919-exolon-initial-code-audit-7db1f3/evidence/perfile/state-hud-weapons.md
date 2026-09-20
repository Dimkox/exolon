# Пер-файловый аудит: состояние / персистентность / HUD / оружие / жизненный цикл / сборка

HEAD `52795d13d879ad477a3023cae69978436ff82d1a`. Lane: state-hud-weapons.

Файлы моего среза (прочитаны построчно): `Exolon/GameCore/GameState.swift` (100),
`Exolon/GameCore/GameConstants.swift` (34), `Exolon/main.swift` (8),
`Exolon/Platform/macOS/AppDelegate.swift` (42), `Exolon/Platform/macOS/GameView.swift` (76),
`Exolon/GameCore/HUDNode.swift` (64), `Exolon/GameCore/Weapons/BlasterBullet.swift` (50),
`Exolon/GameCore/Weapons/Grenade.swift` (120),
`Exolon/GameCore/Effects/ExplosionEffect.swift` (81),
`Exolon.xcodeproj/project.pbxproj` (1474, build settings + resource membership),
`Exolon/Resources/Info.plist` (23).

`GameScene.swift`, `Player*.swift`, `InputState.swift`, `GamepadInput.swift`, `TMX*`,
`LevelObstacles.swift` читались **только как контекст** (там же — доказательства для
находок, якоря которых в моих файлах). Ни один файл репозитория не изменён;
эксперименты — только `python3`-разбор `Exolon/Resources/*.tmx` и `project.pbxproj`
в `/tmp/perfile-state` (артефакты не сохранялись, скрипты одноразовые).

## Итог

В моём срезе **16 находок: 1 × P1, 6 × P2, 9 × P3**. Ни одна не является «падением на
Linux» — все делятся на статически доказуемые расхождения констант/сборки и ветки,
треющие macOS-play. Три вещи, которые я отдельно **подтвердил как верные** (контрольные
случаи, чтобы аудит не раздувался ложными finding-ами):

1. **Нарезка кадров взрывов корректна.** `blaster_explosion.png` = 80×16 при `frameCount = 5`
   → ровно 16×16; `circular_explosion.png` = 320×32 при `frameCount = 10` → ровно 32×32
   (`ExplosionEffect.swift:22-45`). Формула `1.0/CGFloat(frameCount)` здесь не врёт.
2. **Утечек узлов нет.** `bullets`/`grenades`/`enemyBullets` фильтруются с `removeFromParent()`
   (`GameScene.swift:421-424, 475-478, 516-518`), взрывы и точки следа пересобираются
   (`:1039-1053`), `clearTransientObjects()` чистит всё (`:1000-1004`). Пулинга нет,
   но и неограниченного роста нет.
3. **`GameConstants.defaultGroundY = 96` честная.** Во всех 125 картах нижний сплошной ряд
   слоя `Collision` — 18-й (0-индексированный сверху), то есть верх солида на
   `384 − 19·16 + 16 = 96`. Также подтверждён расчёт «20 тиков при 50 Гц = 0.4 с» для
   `postDeathProtectionDuration` (`GameConstants.swift:8-10`) и «6 px/тик × 60 = 360 px/с»
   для `BlasterBullet.speed` (`:12-14`).

Главный провал среза — **`GameConstants.logicalSize.width = 512` против 560 px,
авторизованных во всех 125 картах**: из-за этого границы деспауна снаряда и гранаты
(`BlasterBullet.swift:42`, `Grenade.swift:80`) ключеваны на ширину мира, которой нет,
а 48-px `hudHeight` перекрывает непрозрачной панелью солиды-тайлы в 44 из 125 карт.

Версии: **фактически shipping-версия — 0.3 (build 1)**; `MARKETING_VERSION = 0.5` и
`CURRENT_PROJECT_VERSION = 1` **мертвы**, потому что `GENERATE_INFOPLIST_FILE = NO`, а
`Info.plist` содержит литералы вместо `$(…)`. «Номера шага» расходятся в **четырёх**
независимых местах (9 в окне / 9 в debug-метке / «STEP 10» в титуле / `Step10.*` в ключах).
Персистентность: **`loadCheckpoint()` не вызывается нигде в дереве** — чекпоинт действительно
write-only, при том что титул показывает «CONTINUE · ZONE %03d».

## Таблица находок

| ID | Pri | Где (мой lane) | Поведение (цитата) | Триггер | Ожидаемо vs фактически | Класс |
| --- | --- | --- | --- | --- | --- | --- |
| **SH-01** | **P1** | `GameConstants.swift:5` + `BlasterBullet.swift:42`, `Grenade.swift:80` | `static let logicalSize = CGSize(width: 512, height: 384)`; `position.x > GameConstants.logicalSize.width + 16` / `+ 24` | Все 125 `<map … width="35" height="24" tilewidth="16">` = 560×384; в **61/125** карт слой `Collision` имеет солиды при `x ≥ 512` (до 560): L01S03, L01S09, L01S10, L01S12, L01S13, L01S15, … Встать правее x≈512 (Player допускает x ≤ 544, `Player.swift:128`) и выстрелить вправо | Ожидается: снаряд проходит свой `maximumRange` по авторизованной геометрии. Фактически: `x > 528` убивает пулю на **первом же** тике — выстрел исчезает у дула; граната — при `x > 536`. Правый фланг уровня (3 тайловых колонки) непристреливаем | Linux-static (доказуемо) → macOS-play |
| **SH-02** | **P2** | `GameConstants.swift:33` + `HUDNode.swift:9,14-20` | `static let hudHeight: CGFloat = 48`; `background = SKSpriteNode(color: .black, …)` при `zPosition = 100` | Карты с солидными тайлами в рядах 20–21 слоя `Collision` = мировой `y < 64` | Ожидается: HUD занимает не-игровую полосу. Фактически: в **44/125** карт солиды полностью (`y < 48`) и в **60/125** частично лежат **за** непрозрачной чёрной панелью → геометрия уровня навсегда скрыта; при поверхности на y=48 Vitorc идёт «по верху HUD» | Linux-static |
| **SH-03** | **P2** | `GameConstants.swift:24-31` | «The turret bullet travels with its lower edge at **ground+50**; a 52 px damage box **overlaps that trajectory by two pixels** … Keeping the vulnerable crouch body at **49 px**» | Мезза: `LevelObstacles.swift:81` `CGPoint(x: hitbox.minX + 2, y: hitbox.minY + 56)` при `hitbox = CGRect(x: leftX, y: groundY, …)` (`:40`) и `projectileSize = 4×4` (`:139`) | Ожидается: комментарий описывает реальные пиксели. Фактически: центр на `groundY+56`, **нижний край на `groundY+54`** (не +50); бокс 52 с ним **не пересекается вовсе** (зазор 2 px), а не «перекрывается на два пикселя». Реальный запас у 49-px бокса — **5 px, а не 1**. Поведение сегодня корректно, но обоснование константы устарело после миграции меззы `+52 → +56` (см. собственный комментарий `LevelObstacles.swift:76-79`); эхо лжи — `Player.swift:63-65` | Linux-static |
| **SH-04** | **P2** | `GameState.swift:40-52` (+ `:24-31`) | `func loadCheckpoint() -> GameCheckpoint?` — **единственное вхождение имени во всём дереве есть его же определение** | Любой запуск, любой чекпоинт | Ожидается: CONTINUE читает сохранение. Фактически: 6 ключей пишутся на каждой смене зоны (`GameScene.swift:657`) и на каждом респавне (`:335`), затем **удаляются** в `loadPersistentState()` (`:690`); `beginFromTitle` (`:710-718`) к персистентности не обращается. Титульная строка `CONTINUE · ZONE %03d` (`:901-902`) отражает only-in-session `hasSavedCheckpoint`, то есть **обещание, за которым нет кода**. ~20 строк мёртвого API + 12 бесполезных записей UserDefaults на переход | Linux-static (подтверждено аудитом B-05) |
| **SH-05** | **P2** | `GameState.swift:71-77` (политика хранилища) + `GameScene.swift:45,186,950-985` | `testInvulnerabilityEnabled = false` — только память; `restartFromBeginning` и `enterGameOver` его не сбрасывают | Пауза → INVULNERABILITY: ON → RESTART (или GAME OVER → SPACE) | Ожидается (`ORIGINAL_MECHANICS.md:17` — чит «существует только для верификации»): чит не должен переживать перезапуск и не должен точить рекорд. Фактически: неуязвимость и жёлтая плашка `TEST MODE · INVULNERABILITY` (`:187` — единственный писатель `isHidden`) держатся **до конца процесса**, а `persistence.saveHighScore` (`:665`, `:726`) в это время пишет рекорд на диск **без какого-либо маркера** | Linux-static |
| **SH-06** | **P2** | `main.swift` (все 8 строк) + `AppDelegate.swift:8-38, 40-42` | `let application = NSApplication.shared … application.run()` — `NSApp.mainMenu` не присваивается нигде; `grep -rn "NSMenu\|mainMenu\|keyEquivalent" Exolon/**/*.swift` → **0 совпадений** | Любая попытка выйти с клавиатуры | Ожидается: ⌘Q работает как в любом macOS-приложении. Фактически: меню-бара нет вообще → ни ⌘Q, ни ⌘W, ни ⌘H, ни «About Exolon» (значит shipping-версию 0.3 в UI не увидеть). **Корень B-06 — не `GameView.keyDown`** (key-equivalent’ы диспатчатся до `keyDown`), а отсутствие меню; выход один — красный крестик, т.к. `applicationShouldTerminateAfterLastWindowClosed → true` | Linux-static |
| **SH-07** | **P2** | `GameView.swift:42-44` (+ `GameConstants.swift:7`) | `@objc private func windowDidResignKey() { inputState?.reset(source: .keyboard) }` | Зажать стик/D-pad и увести фокус окна (⌘Tab, Space, клик по другому приложению) | Ожидается: ввод обнуляется целиком, сим не догоняет. Фактически: (а) геймпад-источники не чистятся — `InputState.resetGamepad()` (`InputState.swift:80`) вызывается **только** при отключении геймпада (`GamepadInput.swift:42`), а `resetAll()` (`:63-67`, единственный сбрасывающий `pausePressPending`) **не вызывается нигде** → Vitorc продолжает идти, а отложенный пульс pause выстрелит позже (`GameScene.swift:151`); (б) `isPaused` ни view, ни scene не выставляется (`grep isPaused` → только `GameScene.swift:946`), поэтому после возврата `frameTime = min(…, GameConstants.maximumFrameTime)` = **0.25 с = ровно 15 fixed-шагов догоня за один кадр** при уже очищенном вводе | Linux-static → macOS-play |
| **SH-08** | **P2** (V1) | `Info.plist:18,20` ↔ `project.pbxproj:1418,1420,1424,1437,1439,1443` | `<key>CFBundleShortVersionString</key><string>0.3</string>`, `<key>CFBundleVersion</key><string>1</string>` — литералы; при этом `GENERATE_INFOPLIST_FILE = NO`, `MARKETING_VERSION = 0.5`, `CURRENT_PROJECT_VERSION = 1` | Сборка Debug или Release | Ожидается: один источник версии. Фактически: `MARKETING_VERSION`/`CURRENT_PROJECT_VERSION` **ни на что не влияют** (они питают только авто-генерируемый plist, он выключен) → бандл всегда 0.3 (1). Показательно: в том же `Info.plist` строки 12/14/16 используют `$(DEVELOPMENT_LANGUAGE)`, `$(EXECUTABLE_NAME)`, `$(PRODUCT_BUNDLE_IDENTIFIER)` → подстановка работает, версии просто не были подключены | Linux-static; проверить `plutil -p` |
| **SH-09** | **P3** (V2) | `AppDelegate.swift:16` ↔ `GameScene.swift:67,656,984,832,624` ↔ `GameState.swift:25-31` ↔ `README.md:1` | «Exolon Remake — **Step 9** Rebase» / «**STEP 9** · ALL 125 ORIGINAL ZONES» / «**STEP 10**» в титуле / ключи `Exolon.**Step10**.*` | Визуальный проход | Ожидается: один ярлык продукта. Фактически: **четыре** независимых литерала для одного состояния, ни один не выведен из другого и ни один — из `CFBundleVersion`. Важная поправка к формулировке задания: **«STEP 9…» — не HUD**, а отдельный `stepLabel` (`GameScene.swift:16,67-73`), скрытый по умолчанию и показываемый только вместе с debug-хитбоксами (`:224` `stepLabel.isHidden = !showHitboxes`); `HUDNode` вообще не знает про «шаг» | Linux-static |
| **SH-10** | **P3** (V3) | `project.pbxproj` PBXResourcesBuildPhase ↔ диск | ресурс на диске, но нет `… in Resources` | Диффом `Exolon/Resources/**` (282 файла) против 276 записей `PBXBuildFile … in Resources` | Не едут в бандл: **`bubble.gif`** (96×192), **`rocks.gif`** (512×48), **`turret_bullet.gif`** (4×4), **`light.png`**, **`ship_fire.png`**. (6-я разница — `Info.plist`, верно: он `INFOPLIST_FILE`, а не ресурс.) Рантайм не падает: код грузит `bubble`/`turret_bullet`/`rocks`/`ship_fire_frame`, все есть как .png. Но `LevelObstacles.swift:64-66` («must reproduce the original composite **turret.gif** exactly») ссылается на файл, которого в бандле не будет | Linux-static |
| **SH-11** | **P3** (T2 + упаковка) | `project.pbxproj` / `Info.plist` | нет `.icns`/`Assets.xcassets` (`find` → 0), нет `CFBundleIconFile`/`CFBundleIconName`, `grep -c icns pbxproj` → 0; `find Exolon.xcodeproj -type f` → **только `project.pbxproj`** (нет `xcshareddata/xcschemes`); `CODE_SIGN_IDENTITY = "-"`, `CODE_SIGN_STYLE = Manual`, `DEVELOPMENT_TEAM = ""`, `ENABLE_HARDENED_RUNTIME` не задан; `CreatedOnToolsVersion = 10.2`, `LastUpgradeCheck = 1020`, `objectVersion = 51` | Сборка/вывеска | Следствия: generic-иконка в Dock/Finder; `xcodebuild -scheme Exolon` невозможен (только `-target`); ad-hoc-подпись → не дистрибутируется и карантинится при скачивании; проект ни разу не мигрировался (Xcode 15/16 предложит upgrade). **Отсутствующий `TARGETED_DEVICE_FAMILY` — норма** для чисто-macOS-таргета, чинить нечего | Linux-static |
| **SH-12** | **P3** | `BlasterBullet.swift:12-15` | «The **HTML5 remake** uses 6 pixels/tick and a 210 pixel range» → `speed = 360`, `maximumRange = 210` | любой выстрел | Ожидается: константа опирается на авторитет, перечисленный в `ORIGINAL_MECHANICS.md:3-7` (`rusarh/exolon-esl`, `data_zone_*.asm`, `actions_*.asm`; StrategyWiki — только cross-check). Фактически: HTML5-ремейк в авторитеты не входит, раздел Blaster (`:21-27`) ни скорости, ни дальности не называет; 210 px = **41 %** заявленной ширины 512 (и 37 % реальной 560). Плюс значение живёт внутри класса, а не в `GameConstants` | Linux-static (провенанс) |
| **SH-13** | **P3** | `GameState.swift:81-83` vs `GameScene.swift:526,533` | `startingAmmo = 99`, `startingGrenades = 10`, но `gameState.ammo = 99` / `gameState.grenades = 10` литералами | подобрать белый/жёлтый ящик | Ожидается: одно число на «старт», «смерть» и «ящик». Фактически: смерть/бонус используют константы (`:330-331`, `:629-630`), ящики — свои литералы → правка `startingAmmo` рассинхронит их молча. Сейчас оба верны `ORIGINAL_MECHANICS.md:11,105-107`. Там же `:628` использует `startingLives` как **потолок** (перегрузка «starting» = «max»; против оригинала не противоречит) | Linux-static |
| **SH-14** | **P3** | `ExplosionEffect.swift:25,30,59-76` | `duration = 1.0 / 22.0` и `1.0 / 18.0` при водителе `fixedTimeStep = 1/60`; на каждый взрыв — новый `SKTexture(imageNamed:)` + 5/10 оберток `SKTexture(rect:in:)` + `Array` | любой взрыв | 60/22 = 2.727 и 60/18 = 3.333 → кадр показывается чередой 3,3,2 (соотв. 3,3,4) тиков: **микродрожание** анимации. `1/20` или `1/15` были бы точными делителями. Пулинга нет, утечки нет (см. Итог, п.2). `required init?(coder:) fatalError` — приемлемо для программно создаваемых нод | Linux-static |
| **SH-15** | **P3** | `Grenade.swift:19-22,38,57-66,71-72,83-84,91-99` | комментарий «**30** glide ticks» vs `if glideTicks > 30`; `hitbox` 10×10 при спрайте 16×16; `position.y - 5 <= groundY + 2`; `private var life: TimeInterval = 0.20` и `alpha = … / 0.20` | полёт гранаты | (а) глид — **31** тик, и в нём `velocityPerTick.dy` не обнуляется, а донесён из `.rising` (≈ −0.1) → «парение» на самом деле медленное снижение ≈3.1 px; (б) хитбокс на 6 px меньше спрайта → видимое погружение в стену/турель на ≤3 px без детонации; (в) размеры коллизии земли (5 и +2) — вторая, не связанная с `hitbox` копия: правка `hitbox` молча меняет высоту взрыва; (г) ветка `position.y > logicalSize.height + 40` недостижима (апекс лоба ≈ spawn + 29 px: 17 тиков подъёма, 3.3+3.1+…+0.1) → мёртвый код-страховка; (д) `GrenadeTrailDot.init` пересобирает палитру `[SKColor]` на **каждую** точку (~18 точек/с при 1 гранате, `:83-84`) и дублирует литерал времени жизни | Linux-static |
| **SH-16** | **P3** | `HUDNode.swift:57-61` + `GameState.swift:71-73` | `"%02d"`/`"%06d"`/`"%03d"`, `loadHighScore() = max(0, defaults.integer(…))` — без верхнего клампа | показать HUD / вручную поправить `~/Library/Preferences/com.exolon.remake.plist` | Ожидается: формат поля = инвариант состояния. Фактически: 6-значная гарантия даёт **только** `min(999_999, …)` в `awardPoints` (`GameScene.swift:662`), а не `GameState`; `points` как поле не ограничен ничем, `highScore` с диска клампится лишь снизу → 7+ цифр проедут в `%06d` и сделают рекорд недостижимым. additionally: `highScore` есть в `GameState`, но в строке HUD его нет — за игроком рекорд не виден (только титул/game over). Раскладка колонок (48/145/266/382/470, Menlo-Bold 11/12) при статической оценке адванса ~0.6·size не пересекается | Linux-static |

## Персистентные ключи и их жизнь между версиями

Хранилище **одно**: `UserDefaults.standard` (`GameState.swift:21-38`, домен
`com.exolon.remake` → `~/Library/Preferences/com.exolon.remake.plist`, опосредованно
`cfprefsd`). Инъекция `init(defaults:)` есть, но нигде не используется (`GameScene.swift:24`
берёт `.shared`) и тестов, которые бы её использовали, в проекте нет.

| # | Ключ (`GameState.swift:25-31`) | Пишется | Читается | Удаляется | Переживает bump версии? |
| --- | --- | --- | --- | --- | --- |
| 1 | `Exolon.Step10.HasCheckpoint` | `saveCheckpoint` (`:54`) | `loadCheckpoint` (`:41`) — **никогда, вызовов нет** | `clearCheckpoint` (`:63`) | **да** |
| 2 | `Exolon.Step10.LevelName` | `:55` | `:42` — никогда | `:64` | **да** |
| 3 | `Exolon.Step10.Ammo` | `:56` | `:46` — никогда | `:65` | **да** |
| 4 | `Exolon.Step10.Grenades` | `:57` | `:47` — никогда | `:66` | **да** |
| 5 | `Exolon.Step10.Points` | `:58` | `:48` — никогда | `:67` | **да** |
| 6 | `Exolon.Step10.Lives` | `:59` | `:49` — никогда | `:68` | **да** |
| 7 | `Exolon.Step10.HighScore` | `saveHighScore` (`:75`) | `loadHighScore` (`:71`) — `GameScene.swift:689,961` | **никогда** | **да** |

Ответы на вопросы задания:

* **Что переживает повышение версии?** Всё, кроме ровно ничего: в именах ключей зашит
  литерал `Step10`, а не версия; `MARKETING_VERSION`/`CFBundleShortVersionString` в них
  не участвуют; `register(defaults:)`, миграции и поле `schemaVersion` отсутствуют.
  Переход 0.3 → 0.5 → 0.6 не меняет в хранилище **ничего** — и, что важнее, не даёт
  способа старый набор инвалидировать.
* **Что происходит с сейвом возвращающегося игрока?** На первом же тике `loadPersistentState()`
  (`GameScene.swift:686-695`) читается **только** `HighScore`, после чего
  `clearCheckpoint()` сносит 6 ключей чекпоинта. То есть: рекорд — навсегда; остальное —
  уничтожается самим приложением при каждом старте. Дополнительно: удаление `.app` с диска
  **не** трогает `~/Library/Preferences/com.exolon.remake.plist`, а in-game сброса данных нет
  (`clearCheckpoint` `HighScore` не касается) → рекорд, намотанный в том числе в SH-05,
  фактически вечен.
* **Ключи как общий ресурс сборки.** Все сборки (все ветки, все «steps») делят один domain id
  `com.exolon.remake`. Два разных checkout'а перетирают друг друга: сборка A пишет
  чекпоинт, сборка B стартует и удаляет его. Тот же механизм делает `HighScore`
  необъяснимым между сборками — кто накрутил, не записано (SH-05).
* **`clearCheckpoint()` асимметричен намеренно и это верно:** удаляются 6 из 7 ключей,
  `HighScore` не удаляется (`:62-69`). Отдельно: `synchronize()` не вызывается ни разу,
  поэтому force-quit может потерять последние `set` — на фоне SH-04 безразлично.
* **Что читается из чекпоинта с защитой, а что нет.** `loadCheckpoint` (`:44-51`) —
  `max(0,…)` на ammo/grenades/points, `max(1,…)` на lives, непустой `levelName`. Это
  **единственная** валидация: `levelName` не сверяется с множеством 125 существующих
  уровней, `lives` с нулём превращается в фантомную жизнь, `zone` не хранится вовсе
  (выводится `zoneNumber(for:)`, а тот на мусорном имени молча возвращает 0 → «ZONE 000»).
  Опасно ровно в тот момент, когда SH-04 починят и `loadCheckpoint` начнут вызывать.
* **Флag invulnerability:** хранилища нет, ключа нет, очистка — только рестарт процесса
  (SH-05). **Высокочастотная запись:** `saveHighScore` вызывается из `awardPoints` на
  каждое очко, превысившее прежний рекорд → сотни `set` за сессию; `saveCheckpoint` —
  6 ключей на каждый переход зоны.

## Версии и «номера шага»

| артефакт | значение | место |
| --- | --- | --- |
| `MARKETING_VERSION` (Debug, Release) | **0.5** | `project.pbxproj:1424`, `:1443` |
| `CURRENT_PROJECT_VERSION` | 1 | `project.pbxproj:1418`, `:1437` |
| `GENERATE_INFOPLIST_FILE` | **NO** (обе строки — причина, по которой оба параметра мертвы) | `project.pbxproj:1420`, `:1439` |
| `CFBundleShortVersionString` | **0.3** (литерал) | `Info.plist:18` |
| `CFBundleVersion` | **1** (литерал) | `Info.plist:20` |
| заголовок окна | `Exolon Remake — Step 9 Rebase` | `AppDelegate.swift:16` |
| отладочная метка сцены | `STEP 9 · ALL 125 ORIGINAL ZONES`, далее `STEP 9 · <LxxSyy> · ZONE nnn` | `GameScene.swift:67`, `:656`, `:984` (visible только при F1, `:73`,`:224`) |
| титульное меню | `STEP 10` | `GameScene.swift:832` |
| комментарий-обещание | «still being extended through Step 9 … deliberately dormant» | `GameScene.swift:624-625` |
| ключи UserDefaults | `Exolon.Step10.*` ×7 | `GameState.swift:25-31` |
| README | `# Exolon — Step 9 Rebase (test archive)`; **строки версии нет** | `README.md:1` |

Итог по идентичности:shipping = **0.3 (build 1)**; 0.5 существует только в build settings и
никуда не попадает. Три «номера шага» из формулировки задания подтверждаются построчно, но
второй из них — **не HUD, а debug-оверлей**, и четвёртый («STEP 10» в титуле) там же пропущен;
всего литералов — четыре. README не содержит версии, что формально противоречит
`AGENTS.md` («update `README.md` … current VERSION»).

## Build settings

Полная инвентаризация того, что влияет на продукт (Debug и Release конфигурации таргета
`Exolon` — `project.pbxproj:1413-1427` и `:1432-1446`; проектные — `:1389-1409`):

|Setting (строка)|Значение|Влияние на продукт|Диагноз|
| --- | --- | --- | --- |
|`GENERATE_INFOPLIST_FILE`|`NO` (`:1420`, `:1439`)|выключает подстановку версии из build settings|**SH-08, причина**|
|`MARKETING_VERSION`|`0.5` (`:1424`, `:1443`)|никуда не попадает|**SH-08, мёртвая константа**|
|`CURRENT_PROJECT_VERSION`|`1` (`:1418`, `:1437`)|никуда не попадает (в plist литерал `1`)|совпадает случайно|
|`INFOPLIST_FILE`|`Exolon/Resources/Info.plist`|единственный источник версии бандла|`0.3` (1)|
|`MACOSX_DEPLOYMENT_TARGET`|`10.14` (`:1394`, `:1406`, `:1423`, `:1442`)|согласован с `LSMinimumSystemVersion 10.14` (`Info.plist:22`)|верно, не дефект|
|`SDKROOT`|`macosx` (только на уровне проекта, таргет наследует)|чисто-macOS таргет|верно|
|`TARGETED_DEVICE_FAMILY`|**отсутствует**|для macOS-таргета ключ не применим|нормально, чинить нечего|
|`COMBINE_HIDPI_IMAGES`|`YES`|нужен для Retina при загрузке свободных .png без asset catalog|верно|
|`CODE_SIGN_STYLE` / `CODE_SIGN_IDENTITY` / `DEVELOPMENT_TEAM`|`Manual` / `"-"` / `""`|ad-hoc подпись: не дистрибутируется, карантинится при скачивании; `ENABLE_HARDENED_RUNTIME` не задан|**SH-11**|
|`SWIFT_VERSION`|`5.0`|—|верно|
|`PRODUCT_BUNDLE_IDENTIFIER`|`com.exolon.remake`|домен `UserDefaults` и «общий ресурс» всех сборок|см. SH-05/персистентность|
|`ALWAYS_SEARCH_USER_PATHS`|`NO`|—|верно|
|`objectVersion` / `LastUpgradeCheck` / `CreatedOnToolsVersion` / `compatibilityVersion`|`51` / `1020` / `10.2` / `Xcode 9.3`|проект ни разу не мигрировался; Xcode 15/16 предложит upgrade|**SH-11**|
|`LD_RUNPATH_SEARCH_PATHS`|`$(inherited) @executable_path/../Frameworks`|связка Cocoa/SpriteKit/GameController из системных фреймворков|верно|
|`ASSETCATALOG_COMPILER_*`|**нет** (и нет `Assets.xcassets`)|все текстуры — свободные файлы в `Contents/Resources`; `SKTexture(imageNamed:)` резолвится по имени файла|объясняет SH-10|
|иконка|`CFBundleIconFile`/`CFBundleIconName` нет, `.icns` в репозитории нет|generic-иконка Dock/Finder|**SH-11**|
|`.xcscheme`|`find Exolon.xcodeproj -type f` → только `project.pbxproj`|нет `xcshareddata/xcschemes` → `xcodebuild -scheme` невозможен|**SH-11** / backlog T2|
|`PBXResourcesBuildPhase`|276 записей против 282 файлов на диске|5 ресурсов не едут в бандл|**SH-10**|
|`PBXSourcesBuildPhase`|18/18 `.swift`, 0 «in Sources but missing on disk»|полнота компиляции|верно|

Правила ресурсов против кода — конфликт проверен и **отсутствует**: и `.tmx`, и `.png`
копируются плоско в `Contents/Resources`, и читаются плоско
(`TMXMapLoader.swift:106` — `bundle.url(forResource:withExtension:)`; текстуры —
`SKTexture(imageNamed:)`). `productType = com.apple.product-type.application`,
`buildRules = ()`, таргет один.

Отдельно по переменным в `Info.plist`: `CFBundleName = $(PRODUCT_NAME)`,
`CFBundleExecutable = $(EXECUTABLE_NAME)`, `CFBundleIdentifier = $(PRODUCT_BUNDLE_IDENTIFIER)`
резолятся корректно (значения заданы в таргете). `CFBundleDevelopmentRegion =
$(DEVELOPMENT_LANGUAGE)` — при том что `DEVELOPMENT_LANGUAGE` в проекте **не определён**
(ни в одной XCBuildConfiguration, `.xcconfig` в репозитории нет); резолвится из встроенных
дефолтов Xcode в `en`, но это надо подтвердить на macOS через `plutil -p`, потому что
литерал `$(DEVELOPMENT_LANGUAGE)` внутри готового бандла был бы таким же по природе дефектом,
что и SH-08.

## Что проверить на macOS

1. `xcodebuild -project Exolon.xcodeproj -target Exolon -configuration Debug build` — **без
   `-scheme`**: shared scheme нет (SH-11).
2. `plutil -p Exolon.app/Contents/Info.plist | grep -i version` и `mdls -name
   kMDItemVersion Exolon.app` → ожидаемо увидеть **0.3**, а не 0.5 (SH-08). Заодно
   `CFBundleDevelopmentRegion` и отсутствие иконки (SH-11).
3. **SH-01, главный прогон:** зона с картой из списка L01S03/L01S09/L01S10/L01S12/L01S13/L01S15 —
   дойти до правого края и стрелять вправо. Зафиксировать: есть ли за x=512 тайлы/солиды,
   заходит ли туда Vitorc, исчезает ли пуля у дула. Включить F1 и снимать хитбоксы.
4. **SH-02:** в любой из 44 карт (`L01S06, L01S10, L01S12-15, …`) найти рельеф при `y < 48`
   и проверить, перекрыт ли он панелью HUD; в картах с поверхностью на `y = 48` — не идёт ли
   Vitorc «по крыше» HUD.
5. **SH-03 (контроль ложного обоснования):** F1, присесть под выстрелом турели и замерить
   реальный зазор между `playerCrouchingDamageSize` (49) и нижним краем пули. Если пуля проходит
   с 5 px — задокументировать, что запас не «2 px», и что вариант 52 тоже проходил бы.
6. **SH-04:** перейти любую зону → убить процесс → запустить снова → на титуле должно быть
   «NEW GAME · ZONE 000» (не CONTINUE). Затем: дойти до CONTENT COMPLETE → SPACE → титул
   покажет «CONTINUE · ZONE 124» → SPACE: проверить, не возвращает ли в уже пройденную 124
   (связка с backlog F1).
7. **SH-05:** пауза → INVULNERABILITY ON → RESTART → убедиться, что плашка «TEST MODE» и чит
   остались; намотать очки → GAME OVER → «HIGH SCORE …» → перезапустить процесс и убедиться,
   что испорченный рекорд пережил перезапуск.
8. **SH-06:** ⌘Q, ⌘W, ⌘H, ⌘M, «About» — все должны быть неактивны/отсутствовать; проверить,
   что выход реально только по крестику окна. После добавления минимального `NSMenu` — ⌘Q жив.
9. **SH-07:** зажать D-pad/стик → ⌘Tab → вернуть фокус: персонаж не должен идти сам;
   отдельный кейс — нажать P/Options прямо на потере фокуса и посмотреть, не прилетит ли
   pause позже. Наблюдать 1-2 с после возврата фокуса: не «домножается» ли кадр (15 fixed
   шагов догона, `GameConstants.maximumFrameTime`), не гибнет ли Vitorc без ввода.
10. **SH-12/SH-14/T2-проверка оружия:** дальность blaster (210 px) — можно ли вообще отстреливать
    правую половину; двойной выстрел в экзокостюме (`GameScene.swift:345-350`, второй снаряд на
    `+12`) даёт ли 2 попадания по force field (по `ORIGINAL_MECHANICS.md:120` — «13 нажатий на
    25 хитов»); 12-px разнесение нигде не задокументировано. Дрожение кадров взрыва глазом.
11. **SH-10:** `unzip -l`/`ls Exolon.app/Contents/Resources` — убедиться, что `bubble.gif`,
    `rocks.gif`, `turret_bullet.gif`, `light.png`, `ship_fire.png` отсутствуют (и что absence
    безвредна), после чего удалить из git-ожиданий или задокументировать.
12. Дисплей/частота: на 120 Гц-панели убедиться, что `preferredFramesPerSecond` не выставлен
    и сим всё равно держит 60 Гц по аккумулятору (`GameScene.swift:129-135`) — аккумулятор
    не зависит от display-rate, это проверка гипотезы, а не известный дефект.

Вердикт: fail

Обоснование: одна P1 (SH-01 — границы оружия ключеваны на ширину мира, не совпадающую ни с
картами, ни с геометрией солидов) плюс шесть P2, из которых SH-04/SH-05/SH-06/SH-07 —
пользовательски видимые, а SH-08 — прямое расхождение версии бандла с версией сборки.
Моя часть среза не проходит ни local-проверку «константы не врут», ни «персистентность
согласована с UI». P1/P2 из этого файла не должны попадать в релиз без macOS-подтверждения
пунктов 3–8 списка выше.
