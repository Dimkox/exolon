# Lane: SpriteKit node/texture lifecycle при смене зоны

HEAD `52795d13d879ad477a3023cae69978436ff82d1a`. Файлы: `Exolon/GameCore/GameScene.swift`,
`Exolon/GameCore/Levels/TMXLevelRuntime.swift`, `Exolon/GameCore/Levels/TMXTileMapRenderer.swift`,
`Exolon/GameCore/Levels/TMXMapLoader.swift`, `Exolon/GameCore/Player/PlayerSpriteNode.swift`,
`Exolon/GameCore/Objects/LevelObstacles.swift`, `Exolon/GameCore/Effects/ExplosionEffect.swift`,
`Exolon/GameCore/Weapons/{BlasterBullet,Grenade}.swift`, `Exolon/GameCore/HUDNode.swift`,
`Exolon/Platform/macOS/{GameView,AppDelegate,GamepadInput}.swift`, `Exolon.xcodeproj/project.pbxproj`,
`Exolon/Resources/*` (125 `.tmx`, 153 `.png`).

Потолок: `swiftc -parse` (Swift 6.4, Linux) — **0 ошибок, парсится всё**; тайпчек SpriteKit
на Linux невозможен, поэтому все выводы ниже — либо текстовые/структурные доказательства из
 исходников, либо измеренные по `.tmx`/`.png`/`.pbxproj` числа. Ни один пункт не требует
запуска игры, кроме явно помеченных `macOS`.

## Итог

Ядро жизненного цикла **здорово**: `repeatForever`/`SKAction.repeat*`/`animate(with:)` в дереве
нет вообще (0 вхождений), `run(_:completion:)` нет вообще (0 вхождений), единственная замыкание
внутри `SKAction` — `[weak self]`, `GamepadInput.scene` — `weak`, `GameView.inputState` — `weak`.
Классический баг «анимация пережила узел» структурно невозможен: вся покадровая анимация
(11 кадров Vitorc, 8 у турели/телепорта, 3 у bubble, 2 у egg/missile, 5/10 у взрывов) ведётся
вручную в `fixedUpdate`, а не экшенами. `rootNode.removeFromParent()` снимает поддерево зоны
целиком, и все транзиенты сцены, кроме одного, покрыты `clearTransientObjects()`.

Но есть **два доказуемых дефекта и пять дыр в жизненном цикле текстур**:

1. **LC-2 (главный).** Зона перестраивается *синхронно внутри* `fixedUpdate`, а шаг-аккумулятор
   считает время по wall-clock и обрезан сверху 0.25 с. Следствие: кадр после перехода
   прогоняет до 15 фиксированных шагов уже на новой зоне, при том что `transition()` явно
   выставляет `invulnerability = 0`. Игрок получает ~0.25 с «вслепую» симулированной смерти
   на входе в каждый экран. Это механизм, а не гипотеза: цепочка вызовов читается целиком.
2. **LC-3.** `createTeleportFlash` — единственный узел уровня сцены, который **не** отслеживается
   ни в одном массиве и потому переживает смену зоны; его удаление — единственная ставка на
   `SKAction.removeFromParent()`, а `setGameplayNodesPaused` ставит `isPaused` и на него тоже.
3. **LC-8/LC-9.** `SKTexture(rect:in:)` заводится на *каждую клетку* тайла, а не на уникальный
   тайл (замер: отношение уникальных GID к общему числу тайлов в зоне = 0.122, т.е. ~8× потерь);
   атласа нет (0 `SKTextureAtlas`, ни одного `*.spriteatlas` в проекте), `purgeTextureCache()`/
   `preload`/`textureMemoryLimit` не вызываются никогда, 120 уникальных фуллскрин-фонов по
   512×384 → **95.0 МБ** декодированного RGBA при условии, что кеш SpriteKit ничего не сбрасывает.
4. Уточнение к брифу: **«27 именованных загрузок» на HEAD не воспроизводится** — измерено 23
   вызова `SKTexture(imageNamed:` (17 с литералом, 6 с вычисленным именем), 23 уникальных
   литеральных имени, **все** они резолвятся в существующий PNG; и **загрузка по имени покадро
   отсутствует** — все 23 сайта находятся в `init`/конструкции, горячий путь — «на каждый спавн
   сущности», а не «на каждый кадр». Конфигурация `SKView` в брифе приписана неверно: в
   `GameView.swift` её нет вовсе, флаги стоят в `AppDelegate.swift:22-23`.

Crash-рисков на переходе нет: цепочка `nextLevel` замкнута (125/125 TMX на месте, 0 целей вне
набора, терминатор — `L05S25`), ни один слой не сжат (`unsupportedCompression` не сработает),
все геометрии источников совпадают с объявленными (0 расхождений), 0 GID с flip-флагами.

## Таблица находок

| ID | Pri | file:line | доказательство | Linux/macOS |
|----|-----|-----------|----------------|-------------|
| LC-1 | P2 | `GameScene.swift:633-640`, `TMXLevelRuntime.swift:44-90` | Смена зоны — не «освободить, потом создать»: Swift вычисляет RHS до записи в `currentLevel`, поэтому на время конструации зоны N+1 старая зона целиком жива (`currentLevel` — единственный владелец `rootNode`). Пик = старая + новая одновременно; худшая зона L01S03 ≈ 262 узла под `rootNode` (247 тайловых спрайтов). `deinit` ни у `GameScene`, ни у `TMXLevelRuntime`, ни у рендерера нет → факт освобождения в коде не наблюдаем | механизм — Linux; реальный пик памяти — macOS |
| LC-2 | **P1** | `GameScene.swift:124-136`, `:294-296`, `:633-650`; `GameConstants.swift:7`; `TMXMapLoader.swift:104-121`; `TMXTileMapRenderer.swift:25,64-71,110` | `transition()` вызывается из `fixedUpdate`, который крутится в `while accumulator >= fixedTimeStep`. `frameTime = min(currentTime - previousUpdateTime, 0.25)`. Внутри `transition()` синхронно: `Data(contentsOf:)` + `XMLParser` + base64-декод до 10 слоёв + до 247 `SKSpriteNode` + до 247 `SKTexture(rect:in:)` + **холодный** `SKTexture(imageNamed:)` нового фона 512×384. Дорожка `update()`→`transition()` занимает главный поток ⇒ следующий `currentTime` дельт ≈ стоимости перехода ⇒ до 15 симуляционных шагов на новой зоне до первого кадра. Усилено `invulnerability = 0` (`:649`) при «обычном входе на экран» | механизм — Linux; длительность перехода и число реально прогнанных шагов — macOS |
| LC-3 | P2 | `GameScene.swift:1024-1037`, `:999-1010`, `:944-947` | `addChild(flash)` на уровне сцены, `flash` не кладётся ни в один массив, `clearTransientObjects()` его не знает (перечислены ровно bullets/grenades/enemyBullets/explosions/trailDots). Удаление — только `SKAction.sequence([group(scale,fade), removeFromParent])`. Триггер: UP в телепорте и `x > 510` в пределах 0.16 с (`checkScreenExit`, `:605`) → кольцо из зоны A дорисовывается в зоне B. Второй триггер: `setGameplayNodesPaused(true)` попадает и по `flash` (он не в белом списке из трёх оверлеев) → секвенция замерзает с частичным alpha, кольцо висит до `leavePause` | Linux |
| LC-4 | P2 | `GameScene.swift:944-947`, `:669-681`, `:94` | `setGameplayNodesPaused` — белый список *по тождеству* над снапшотом `children`. (а) Он замораживает единственных двух реальных потребителей `SKAction`: `bannerLabel` (zPosition 200) и `flash`. Если пауза/game over/`contentComplete` пришли в пределах 0.95 с от `showBanner`, последовательность `.wait(0.75)→.fadeOut(0.20)→.run` встанет посреди фейда: баннер с дробным `alpha` и непустым `text`; после `leavePause` доедет и очистится (т.е. обратимо, не утечка, а залипший артефакт). (б) Любой ребёнок, добавленный *после* вызова, наследует `isPaused = false` — инвариант «на паузе всё игровое стоит» держится не на `isPaused`, а на `return` по `flowState` в `fixedUpdate` | Linux |
| LC-5 | P2 | `GameScene.swift:129-135` vs `:1034-1036`, `:671-680`; `AppDelegate.swift:22-28` | Два независимых часа. Экшены идут на clock SpriteKit (подвержен `SKView.animationSpeed`, `SKNode.speed`, `isPaused`), вся симуляция — на аккумулятор от «сырого» `currentTime` (ни `speed`, ни `animationSpeed` на него не влияют). `animationSpeed` не назначен, поэтому сегодня часы случайно совпадают; `view.isPaused = true` «чтобы заморозить» остановит картинку, но `update(_:)` и `fixedUpdate` продолжат. Побочный эффект: `hud.update`, `updateDebugText`, `updateDebugOverlay` вызываются на *render*-rate, а не на fixed-rate (`:138-141`) | Linux; поведение при `animationSpeed != 1` — macOS |
| LC-6 | P2 | `GameScene.swift:138-141`, `:1062-1073`; `HUDNode.swift:55-61` | `update(_:)` не проверяет ни `flowState`, ни изменение значений: 5 присваиваний `SKLabelNode.text` в HUD + `inputLabel.text` (метка `isHidden = true` по умолчанию, `GameScene.swift:80`) каждый кадр ⇒ 6 переразметок глифов за кадр плюс аллокации `String(format:)` каждый кадр. На 120 Гц вдвое больше, чем на 60 Гц, и это же крутится на титульном экране и в паузе. `updateDebugOverlay()` вызывает `removeAllChildren()` **до** `guard showHitboxes` (`:1075-1077`) ⇒ мутация дерева каждый кадр даже при выключенном дебаге | Linux (код); цена на кадр — macOS |
| LC-7 | P2 | `GameScene.swift:1075-1133`, `:1120-1133` | Дебаг-оверлей пересоздаёт каждый хитбокс как новый `SKShapeNode(path: CGPath(rect:))` / `SKShapeNode(circleOfRadius:)` каждый кадр; за один кадр проходит по `terrainRects` (у L01S03 это десятки смёрженных горизонтальных прогонов), турелям, инкубаторам, яйцам, пулям, гранатам. `SKShapeNode` — самый дорогой класс узлов SpriteKit (не батчится с текстурными). Только debug-путь, но это единственное место, где дерево перестраивается на кадровом темпе | Linux; величина — macOS |
| LC-8 | P2 | `TMXTileMapRenderer.swift:48-71,80-113` (кэш `:9`, новый `SKTexture` на `:110`) | `render(layer:)` зовёт `tileTexture` на **каждую** непустую клетку; кэшируется только лист (`sheetTextures`), а субтекстура `SKTexture(rect:in: sheet)` создаётся заново каждый раз, хотя rect для данного `(image, localIndex)` детерминирован. Замер по 125 картам: 781 видимый тайловый спрайт, среднее отношение уникальных GID к общему по зоне = **0.122** (≈8× дублей), максимум 247 субтекстур в L01S03. `sheetTextures` — свойство экземпляра, а экземпляр на зону свой ⇒ кэш выбрасывается при каждой смене зоны, межзонного переиспользования нет. Дополнительно: 37 турелей ×8, 70 телепортов ×8, 22×8 яиц, 31 баббл-спавнер ×3 — всё пересоздаётся при каждой ререлокации зоны через `restartFromBeginning`/`transition` | Linux (число аллокаций); их стоимость — macOS |
| LC-9 | P2 | весь `Exolon/`; `grep`: 0 `SKTextureAtlas`, 0 `*.spriteatlas`, 0 `SKTileMapNode`, 0 `preload`, 0 `purgeTextureCache`, 0 `textureMemoryLimit` | Атласов нет: 123 уникальных имени резолвятся по одному (`SKTexture(imageNamed:)`), т.е. до 123 отдельных GPU-текстур. Замер по PNG×4 байта: **95.0 МБ** декодированного RGBA при условии полной резидентности; 120 из 125 зон — ровно один уникальный фон 512×384 (≈0.79 МБ каждый), ни один фон не переиспользуется между зонами. `removeFromParent()` GPU-память не освобождает: решение об эвикции принимает внутренний кеш SpriteKit. Прогон «все 125 зон» — это накопительный тест, которого в коде нет ни разу | арифметика — Linux; кривая памяти — только macOS (VM Tracker/Allocations) |
| LC-10 | P3 | `grep 'SKTexture(imageNamed'` = 23 сайта | **Коррекция брифа:** «27 именованных загрузок» не воспроизводится — 23 сайта, из них 17 с литералом и 6 с вычисленным именем (`TMXTileMapRenderer.swift:25` image-layer, `:90` тайлсет, `TMXLevelRuntime.swift:482` addStaticSprite, `LevelObstacles.swift:155` EnemyTurretBullet, `:191` DestructibleObstacle, `ExplosionEffect.swift:33`); 23 уникальных литеральных имени и все они существуют как PNG. Гипотеза «загрузка по имени каждый кадр» **опровергнута**: каждый из 23 сайтов лежит внутри `init`/конструкции. Настоящий горячий путь — на спавн: 1 именованная загрузка на каждый выстрел blaster (`BlasterBullet.swift:21`) и на каждый вражеский снаряд (`LevelObstacles.swift:155`), на каждую гранату (`Grenade.swift:33`), +5/+10 субтекстур на каждый взрыв (`ExplosionEffect.swift:33-43`), +3 на каждую bubble, +2 на каждую ракету. `destroyWithGrenade` (`GameScene.swift:481-488`) за один вызов плодит до 3+`N` взрывов ⇒ до ~40 субтекстур за событие | Linux |
| LC-11 | P3 | `Exolon.xcodeproj/project.pbxproj` (Resources phase), `Exolon/Resources/` | `light.png` и `ship_fire.png` есть на диске, но **не** в build phase (в фазе 151 PNG + 125 TMX против 153 + 125 на диске). Проверил точно: ни `SKTexture(imageNamed: "light")`, ни `"ship_fire"`, ни `<image source="light|ship_fire">` в картах — нет (`case "ship_fire":` в `TMXLevelRuntime.swift:342` матчит *имя объекта*, а текстура берётся `ship_fire_frame`, которая в фазе есть). Значит это мёртвые файлы, а не баг пустой текстуры. Структурный риск остаётся: фаза перечисляет файлы поштучно (0 folder reference, 0 PBXVariantGroup) ⇒ новая зона, не вписанная в pbxproj, даст `bundle.url(...) == nil` → `resourceNotFound` → `fatalError` | Linux |
| LC-12 | P3 | `TMXLevelRuntime.swift:44-53`; `GameScene.swift:633-640` | Отказ — `fatalError`, и порядок в `transition()` такой: `clearTransientObjects()` → `rootNode.removeFromParent()` → конструирование новой зоны. То есть любая регрессия ресурса/XML — не «зона не загрузилась», а падение на пустой сцене. На HEAD чисто: 125/125 TMX, все `nextLevel` резолвятся, 0 целей вне 125, терминатор `L05S25`, спавн-центры в 0…510 (инвариант «нет петли переходов» выполняется). `decodeLayerData` отвергает любой `compression` (`TMXMapLoader.swift:318-320`); замер: 128 CSV + 10 base64 слоёв, **0** сжатых ⇒ ветка не срабатывает | Linux |
| LC-13 | P3 | `TMXTileMapRenderer.swift:56,128` (`& 0x1FFF_FFFF`) | Flip-биты Tiled (H/V/D) стираются и не применяются: отражённый тайл отрендерится неотражённым. Замер по всем 125 картам и всем слоям (CSV и base64, с учётом флага): **0** GID с выставленным flip-битом ⇒ сегодня дефекта нет, есть латентная ловушка для любой карты, досочиненной в Tiled вручную | Linux |
| LC-14 | P3 | `GameConstants.swift:5` vs все 125 `.tmx` | Замер: **все 125 карт — 560×384 px**, логическая сцена — 512×384, `checkScreenExit` срабатывает при `x > 510`. Следствие для жизненного цикла: 21 тайловый спрайт создаётся в полосе x ≥ 512 и никогда не может быть нарисован (`shouldCullNonVisibleNodes` экономит отрисовку, но не аллокацию узла и субтекстуры). Видимого расхождения нет: все 120 image-layer ровно 512×384. `TMXMapLoader` вообще не валидирует пиксельный размер карты относительно `logicalSize` | Linux |
| LC-15 | P3 | `GameScene.swift:56`, `:1120-1133`; `LevelObstacles.swift:772-780,800-812` | Неявный контрактив координат: `addDebugRect` строит `SKShapeNode(path: CGPath(rect: worldRect))` без `position`, а `ForceFieldBarrier`/`GreenMissileGuidance` — `SKShapeNode(rect: hitbox)` тоже без `position`, т.е. мировые координаты зашиты в path. Это верно **только** при `scene.anchorPoint = (0,0)` (ставится в `didMove`) и родителе в `.zero`. Смена якоря сцены или позиции `debugOverlay` сдвинет и отладочную сетку, и чёрные «заплаты» разрушенных полей/маяка на полэкрана — ни компилятор, ни рантайм не предупредят | Linux |
| LC-16 | P3 | `AppDelegate.swift:22` + все `zPosition` | `ignoresSiblingOrder = true` делает порядок тотальным по `zPosition` и **нестабильным при ничьих**. Ничьи с пересечением в коде есть: 8 (`TurretObstacle`/`DestructibleObstacle`/`CocoonObstacle`), 9 (`AmmoPackPickup`/`IncubatorObstacle`/`DoubleLauncherObstacle`), 7 (`TeleportPortal`/`GrenadePackPickup`), 18 (`BubbleEnemy`/`GrenadeTrailDot`), 20 (`BlasterBullet`/`EnemyTurretBullet`/`HomingMissile`) — причём пуля против ракеты это ровно тот случай, где они обязано перекрываются. Отдельно: два «невидимых» `SKShapeNode` (`ForceFieldBarrier`, `GreenMissileGuidance`) после `destroy()` не снимаются с дерева, а перекрашиваются в чёрный (`LevelObstacles.swift:784-791,814-821`) и висятся в дереве до конца зоны | структура — Linux; мерцание — macOS |
| LC-17 | P3 | `TMXLevelRuntime.swift:86-87`; `PlayerSpriteNode.swift:34`; `GameScene.swift:61-64` | `zPosition` в SpriteKit действует в пределах родителя. Вся графика зоны — под `currentLevel.rootNode` (`zPosition = 0`, ребёнок сцены), а `playerNode` — прямой ребёнок сцены с `zPosition = 10` ⇒ всё содержимое зоны гарантированно **за** игроком, локальные z тайлов (0..N слоёв) на это не влияют: передний план не может закрыть Vitorc'а без репарентинга. Симметрично: `ExplosionEffect` (30) и `GrenadeTrailDot` (18) — дети сцены, они поверх игрока. Соответствует ли это оригиналу — только глазами | семантика — Linux; приемлемость — macOS |
| LC-18 | ✅ P3 | `grep`: `repeatForever` = 0, `SKAction.repeat*` = 0, `SKAction.animate(with:)` = 0, `SKAction` = ровно 3 строки | Весь `SKAction` в проекте: `GameScene.swift:1034-1036` (flash) и секвенция баннера (`:671-680`). Ни одного вечно повторяющегося экшена ⇒ класс «`repeatForever` пережил `removeFromParent()` и крутится на мусоре» структурно невозможен. Вся покадровая анимация — ручные таймеры в `fixedUpdate` (`PlayerSpriteNode.swift:44-63`, `LevelObstacles.swift:92-108,297-303,468-483,601-613`, `ExplosionEffect.swift:64-79`), а модель (`Player.swift`) вообще не знает SpriteKit (`import CoreGraphics, Foundation`) | Linux |
| LC-19 | ✅ P3 | `grep '\.run('` = 2 сайта; `grep -r completion Exolon/` = **0 вхождений во всём дереве** | `run` вызывается только как `run(_:)`; обработчиков завершения в проекте нет ни одного (не только у `SKNode`) ⇒ классический hazard «completion не выстрелит после `removeFromParent`»/«выстрелит на мёртвом состоянии» в дереве отсутствует. Единственный async-ish механизм очистки — action-based `SKAction.removeFromParent()` (он и есть ставка LC-3) | Linux |
| LC-20 | ✅ P3 | `GameScene.swift:676`; `GamepadInput.swift:6,49-98,102`; `GameView.swift:5,73` | Замкнутых циклов удержания не найдено: единственное замыкание внутри экшена — `[weak self]`; `GamepadInput.scene` — `weak var`; все `pressedChangedHandler`/`valueChangedHandler`/`controllerPausedHandler` и `DispatchQueue.main.async` — `[weak self]`; `GameView.inputState` — `weak`; `deinit { removeObserver }` есть в обоих `NSView`-классов; `InputState` обратных ссылок на сцену/вью не имеет (`InputState.swift:35-38`, только `NSLock` + словарь). Оговорки: `viewDidMoveToWindow` (`GameView.swift:31-41`) при повторном прикреплении окна зарегистрирует наблюдателя второй раз; `controllerDidDisconnect` (`GamepadInput.swift:41-44`) не снимает хендлеры с уплывшего геймпада (безвредно из-за weak-хватов) | Linux; реальный double-register — macOS |
| LC-21 | ✅ P3 | `GameScene.swift:635,954`, `:999-1010` | Смена зоны корректна по удалению: `rootNode.removeFromParent()` снимает всё поддерево зоны одним вызовом, а все нетелевелевые транзиенты (bullets, grenades, enemyBullets, explosions, trailDots) дети сцены и все покрыты `clearTransientObjects()`. Узлы, уничтоженные в бою (`DestructibleObstacle.destroy()` → `node.removeFromParent()` и аналоги в `LevelObstacles.swift:24,111,204,226,248,551,754`), остаются в массивах рантайма — это осознанное хранение состояния «разрушено навсегда», и оно умирает вместе с зоной. Единственное исключение — `flash` (LC-3) | Linux |
| LC-22 | P3 | `GameView.swift` (всего 76 строк, 0 конфигурации SKView); `AppDelegate.swift:21-28` | **Неверная атрибуция в брифе:** `GameView.swift` — чистый `NSResponder`-подкласс (клавиатура + `NSWindow.didResignKey`), ни одного свойства `SKView` там не выставляется. Единственные два флага — `ignoresSiblingOrder` и `shouldCullNonVisibleNodes` (`AppDelegate.swift:22-23`). Не выставлены вообще: `isPaused`, `isEnabled`, `antialiasing`, `animationSpeed`, `preferredFramesPerSecond`/`maximumFramesPerSecond`, `showsFPS`/`showsNodeCount`/`showsDrawCount`/`showsUpdateCount`, `textureMemoryLimit`, `allowsTransparency`. Из поименованных в брифе: `isAllowed` — свойства с таким именем у `SKView`/`NSView` нет (ближайшее реальное — `isEnabled`); `acceptsTouchEvents` — член `NSView`, объявленный deprecated в macOS 10.12 в пользу `allowedTouchTypes`, к SpriteKit отношения не имеет. Практический вывод для аудита: штатных счётчиков нет, значит macOS-прогон обязан сначала их включить (или идти в Instruments) | Linux |
| LC-23 | P2 | `GameView.swift:33-43,45-47`; `AppDelegate.swift` (нет `applicationDidResignActive`/`DidBecomeActive`) | При потере фокуса вызывается **только** `inputState?.reset(source: .keyboard)` — сцена, `SKView` и аккумулятор не останавливаются, `gameView.isPaused` не выставляется нигде. Вводимая часть гаснет (Vitorc стоит), а симуляция живёт: турели (50–300 тиков), поршни, мины и homing missile продолжают, и игрок возвращается на труп. Тот же корень, что у LC-2: единственным «часовым» переключателем является `flowState`, а он не связан с активностью приложения | Linux (код); действительно ли SKView шлёт `update(_:)` при occluded/minimised окне — только macOS |
| LC-24 | P3 | `GameView.swift:8-14,63-75`; `AppDelegate.swift:9-36` | `keyDown(with:)`/`keyUp(with:)` не вызывают `super` для необработанных кодов (`default: break` в `setKey`), при этом `AppDelegate` не строит ни `NSMenu`, ни `mainMenu`. Итог: стандартные ⌘Q/⌘W/⌘M зависят от фолбэка AppKit без строки меню, а «съеденный» `keyDown` убирает и системный beep. Я не могу это проверить без AppKit — помечаю как macOS-пункт, а не как дефект | macOS |
| LC-25 | ✅ P3 | `GameScene.swift:813-814,900,905,910-913` | Все 8 `childNode(withName:)` — по оверлеям, которые строятся один раз в `didMove` и никогда не перестраиваются/снимаются; имена (`pause-restart`, `pause-invulnerability`, `title-status`, `title-high-score`, `terminal-*`) уникальны и являются **непосредственными** детьми, поэтому двусмысленность между «только дети»/«рекурсивно» безразлична. Вызовы — только из событийных путей (навигация меню, game over, титр), ни одного из `update`/`fixedUpdate` ⇒ поиска по дереву на кадр нет. Имена в поддереве уровня (`rootNode.name = name`, `renderer.node.name = "tmx-map"`, `sprite.name = layer.name` из TMX, `playerNode.name = "vitorc"`) нигде не ищутся ⇒ переименование слоя в Tiled не способно сломать lookup. Единственная шероховатость: идиом `.map { ($0 as? SKLabelNode)?.text = … }` (`:910-913`) молча no-op'ит при неверном классе — опечатка в имени проявится как пустой оверлей, а не как ошибка | Linux |

## Жизненный цикл узла при смене зоны

Три уровня владения, и они разной честности.

**Уровень 1 — дети сцены.** `GameScene` держит 12 постоянных детей (`:61-113`:
`currentLevel.rootNode`, `playerNode`, `hud`, 4 метки, `debugOverlay`, 3 оверлея,
`testModeLabel`) и N временных, добавляемых в рантайме: `shot.node` (`:294`),
`bullet.node`/`second.node` (`:345,349`), `grenade.node` (`:358`), `GrenadeTrailDot` (`:433`),
`ExplosionEffect` (`:1015,1021`), `flash` (`:1032`). Из них **все**, кроме `flash`,
переживают смену зоны через `clearTransientObjects()` (`:999-1010`), который и зовёт
`removeFromParent()`, и очищает массив-владелец. `flash` — единственный узел, у которого нет
владельца в Swift: он «существует», пока живёт его экшен. Отсюда LC-3.

**Уровень 2 — поддерево зоны.** Все сущности TMX — дети `currentLevel.rootNode`
(`TMXLevelRuntime.swift:88-89,244-341`), поэтому `rootNode.removeFromParent()` (`GameScene.swift:635`)
снимает зону целиком за один вызов; отдельных `removeFromParent()` для 262 узлов не требуется и
они не нужны. Одновременно это означает, что `removeFromParent()` **не** разрывает
`rootNode → entity.node`: родительские рёбра внутри поддерева остаются, и весь граф зоны —
связный компонент, живущий ровно столько, сколько живёт объект `TMXLevelRuntime`.

**Уровень 3 — сам рантайм.** `currentLevel` — единственный сильный владелец `TMXLevelRuntime`
(ни одна замыкание в проекте его не хватает; `Player` про рантайм ничего не знает —
`Player.swift` импортирует только CoreGraphics). Значит освобождение происходит при записи
нового значения в `currentLevel`. По семантике Swift RHS вычисляется **до** записи, поэтому
освобождение старой зоны происходит не перед, а *после* полной конструации новой — пик
«зона N + зона N+1» одновременно (LC-1). Аналогично в `restartFromBeginning` (`:954-958`).

**Что уходит в GPU-память и что из неё не возвращается.** Узел умер — текстура нет.
`SKTexture(imageNamed:)` кладёт растр в общий кеш SpriteKit, а `removeFromParent()` до кеша
дело не касается. В проекте нет ни `purgeTextureCache()`, ни `preload`, ни `textureMemoryLimit`,
ни атласа, поэтому 120 уникальных фонов по 512×384 дают накопительный профиль ~0.79 МБ на
посещённую зону и ~95 МБ на все 125 (LC-9). Никакой подписи в коде не говорит, что это утечка, —
но ни один механизм и против этого не защищает; это ровно тот вопрос, который закрывается только
VM Tracker.

**Действия и замыкания.** `repeatForever` — 0; `SKAction.repeat*` — 0;
`SKAction.animate(with:)` — 0; `run(_:completion:)` — 0. Двумя потребителями `SKAction`
в итоге оказались ровно те узлы, чей жизненный цикл не ведётся: `bannerLabel` (постоянный
ребёнок сцены, но его секвенция не снимается при смене зоны — `transition()` обнуляет только
`bannerLabel.text`, `:655`) и untracked `flash`. Замыкание `.run { [weak self] … }` (`:676`)
корректно: ни цикла, ни «завершение на мёртвом состоянии». `showBanner` честно делает
`removeAllActions()` перед новой секвенцией (`:670`) — единственное место в коде, где
последствия накопленных экшенов учтены явно.

**Что действительно «сиротливо» после смены зоны:** только незавершённый `flash`. Всё остальное
либо в снятом поддереве, либо в очищенных массивах. Уничтоженные в бою объекты, оставшиеся
в `destructibleObstacles`/`turrets`/`mines`, сиротами не являются — это состояние зоны,
умирающее вместе с ней.

## Что проверить на macOS

Порядок — по убыванию ценности. Перед любым пунктом включить счётчики (в коде их нет, LC-22):
`gameView.showsFPS = true; gameView.showsNodeCount = true; gameView.showsDrawCount = true;
gameView.showsUpdateCount = true`, либо сразу Instruments.

1. **Длительность перехода зоны и её превращение в симуляционные шаги (LC-2, P1).** Time
   Profiler / os_signpost вокруг `GameScene.transition(to:)`: сколько миллисекунд стоит
   `TMXMapLoader.load` + `TMXTileMapRenderer.init` + первичное декодирование фона, и сколько итераций
   `while accumulator >= fixedTimeStep` выполняется в следующем кадре. Целевой факт — число
   шагов и накопленный `dt` **на новой зоне до её первой отрисовки**. Воспроизвести: `L01S02`
   → `L01S03` (247 тайлов) и любой вход в «оригинальную» зону с холодным фоном.
   Противоречащий контрольный случай, который обязан перевернуться: тот же переход при
   `previousUpdateTime = 0` сразу после `transition()` — если после сброса шагов становится 0,
   механизм подтверждён.
2. **Кривая памяти/текстур на полном прогоне 125 зон (LC-9, LC-1).** Instruments → Allocations
   (`VM Tracker`) + `Metal System Trace`: растёт ли резидентный набор монотонно по ~0.79 МБ на
   зону, и сбрасывает ли SpriteKit фон ушедшей зоны.
   Отдельно замерить эффект гипотетического `SKTexture.purgeTextureCache()` на входе в
   `transition()` — это даст цифру, нужны ли атласы.
3. **Пик «двух зон сразу» (LC-1).** Allocations с `Mark generation` прямо перед
   `currentLevel = TMXLevelRuntime(...)` и после: живут ли `SKSpriteNode`/`SKTexture` старой зоны
   во время конструации новой и освобождаются ли они вообще (в коде `deinit`-наблюдателей нет).
4. **Залипание кольца телепорта и баннера (LC-3, LC-4).** Вручную: UP в телепорте и сразу `P`
   (или `P` в пределах 0.95 с после `+1000`/`EXOSKELETON ON`) — должен остаться полупрозрачный
   узел на весь период паузы; затем `leavePause`. Второй сценарий: телепорт у правого края →
   `x > 510` в пределах 0.16 с → кольцо из прежних координат в новой зоне.
5. **Частота кадров × стоимость меток (LC-6, LC-7).** Metal System Trace на 60 и 120 Гц при
   выключенном дебаге: виден ли прирост `update` по `hud.update`/`updateDebugText`; затем F1 —
   оценить `removeAllChildren()` + пересоздание `SKShapeNode` каждый кадр по `showsNodeCount` и
   `showsDrawCount`.
6. **`isPaused`/`isEnabled`/`antialiasing`/`animationSpeed` не закреплены (LC-22, LC-5).**
   Проверить фактическое поведение по умолчанию на Retina (window 1024×768 pt → 2048×1536 px,
   scale 4 при сцене 512×384) и на дробных размерах (800×600 → 1.5625×): рвёт ли `.nearest`
   пиксельную сетку, включено ли MSAA по умолчанию. Отдельно: временно выставить
   `gameView.animationSpeed = 0` и убедиться, что симуляция продолжается (это подтвердит LC-5
   как механизм, а не как догадку).
7. **Жизнь без фокуса (LC-23).** Убрать фокус окна (клик по другому приложению), подождать 5 с,
   вернуться: засчитываются ли попадания. Заодно проверить, что `NSWindow` occluded/minimised
   делает с поставкой `update(_:)`.
8. **Перетаскивание/ресайз окна.** Тот же класс, что и LC-2: во время live-resize главный поток
   занят AppKit, а после — один кадр с обрезанным `frameTime = 0.25` ⇒ пачка шагов.
9. **Ничьи `zPosition` при `ignoresSiblingOrder = true` (LC-16).** Искать мерцание порядка на
   пересечениях: пуля blaster (z 20) против ракеты double-launcher (z 20), `GrenadeTrailDot`
   (18) поверх `BubbleEnemy` (18), инкубатор/патрон/двойная турель (9).
10. **Невозможность перекрытия игрока (LC-17).** Сравнить с оригиналом: должен ли Vitorc
    прятаться за передним планом (в текущей иерархии — нет ни при каких локальных z тайлов).
11. **⌘Q/⌘W/⌘M без строки меню и при «съеденном» `keyDown` (LC-24).**
12. **Двойная регистрация `NSWindow.didResignKeyNotification` (LC-20).** Вытащить/вставить
    `contentView` (или сменить экран) и посчитать срабатывания `windowDidResignKey`.

Вердикт: fail

Основание: LC-2 (P1) — доказуемая потеря до ~0.25 с игрового времени и до 15 фиксированных
шагов на входе в каждую зону при обнулённой неуязвимости; LC-3 — единственный, но реальный
сиротский узел, переживающий смену зоны, плюс залипание баннера/кольца из-за `isPaused` по
белому списку (LC-4). Текстурный жизненный цикл (LC-8 субтекстуры на клетку, LC-9 отсутствие
атласов/purge/preload) — не падение, но незакрытый вопрос на ~95 МБ и ~8× лишних аллокаций.
Положительная часть существенна: никаких `repeatForever`, никаких `run(completion:)`, никаких
циклов удержания, снятие зоны одним `removeFromParent()`, все 23 литеральных имени текстур
резолвятся, геометрии всех 123 листов точны (0 растяжений), цепочка 125 зон замкнута и
`fatalError`-ветка загрузки на HEAD не достижима. C1 не касался.
