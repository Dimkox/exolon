# Crash surface — статическая инвентаризация + достижимость из shipped-данных

Лейн: `crash-surface` (read-only). HEAD `52795d13d879ad477a3023cae69978436ff82d1a`.
Объект: 18 Swift-файлов продукта (`Exolon/`, 4227 строк по `wc -l`) × 125 `.tmx` × 153 `.png`.
Инструмент: `swiftc 6.4 (x86_64-unknown-linux-gnu)` — **только `-frontend -parse`**, полный
синтаксический разбор 18/18 файлов прошёл без ошибок. Typecheck, link и сборка **невозможны**
(SpriteKit/AppKit/GameController/Foundation-XML на Linux отсутствуют), поэтому ниже нет ни одного
вывода, полученного «из компилятора»: все вердикты — ручной разбор конкретного места + замер
по данным. `-frontend -parse` не является доказательством отсутствия ловушек и нигде не
используется как таковое.

Репозиторий не изменялся: скрипты и мутированные копии только в `/tmp/lane-crash/`.
Найденная ранее finding **C1 не пересматривается**.

---

## Итог

1. **Классический crash-синтаксис в продукте отсутствует полностью.** За всё дерево:
   **0** force-unwrap-использований (`expr!`), **0** `try!`, **0** `as!`, **0** `precondition`,
   **0** `assert`/`assertionFailure`/`preconditionFailure`, **0** `first!`/`last!`,
   **0** `removeFirst()`/`removeLast()`, **0** `dict[k]!`. Это подтверждено не «grep по `!`»,
   а перебором **всех** вхождений `!` в дереве вне строк и комментариев: 3 вхождения, и все три —
   *объявления* IUO (`NSWindow!`, `GamepadInput!`, `TMXLevelRuntime!`), а не разыменования.
2. **`fatalError` — ровно 5**, и это единственный живущий в коде trap-конструкт:
   1× ловушка загрузки (`TMXLevelRuntime.swift:53`) + 4× заглушка `init(coder:)`, у которой
   в продукте нет вызывающего пути (ни `.storyboard`, ни `.xib`, ни `NSMainNibFile`,
   ни `SKScene(fileNamed:)`, ни `.copy(`, ни `NSKeyedArchiver` — см. строку таблицы F).
3. **Утверждение v1-аудита «fatalError в `TMXMapLoader` на сжатии» — неверно по месту.**
   В `TMXMapLoader` нет ни одного `fatalError`; там `throw TMXMapLoaderError.unsupportedCompression`
   (`TMXMapLoader.swift:308`), объявлена ветка на `:307`. В trap оно превращается единственным
   способом: `do/catch` в `TMXLevelRuntime.swift:51-53` → `fatalError`. Формулировка «любой throw →
   fatalError» по сути верна (и в B-04 оба файла указаны правильно), но локализовать сам trap надо
   в `TMXLevelRuntime.swift:53`, а не в загрузчике. Это важно для фикса: менять надо точку catch.
4. **Найденный дополнительно класс, которого в перечне B-04 нет:** 12 сайтов целочисленного
   умножения/индексной арифметики `Int` в путях загрузчика и рендерера
   (`TMXMapLoader.swift:276,316,323`, `TMXMapLoader.swift:54,55`,
   `TMXTileMapRenderer.swift:49,53,66,100,117,125,134,139,141,143`), которые на **изменённых**
   данных дают `Multiplication overflow` / `Index out of range` — то есть те же `fatalError`-классы,
   но вообще без `throw`. Достигимость доказана контрольным файлом (см. п.6).
5. **Ни одна из перечисленных ловушек не достижима текущими 125 картами и 153 PNG.**
   Замер по всем 138 слоям: атрибут `compression` не встречается **ни разу**; `encoding` — только
   `csv` (128) или `base64` (10); длина каждого base64-блока ровно `w*h*4` байт; количество CSV-
   токенов ровно `w*h`; в CSV-слоях нет ни одного символа вне `[0-9,\s]`; максимальный GID = 481;
   все координаты `<object>` — неотрицательные целые, ни `inf`, ни `nan`; сетка имён
   `L01S01…L05S25` полна (125/125), цепочка `nextLevel` замкнута и не ссылается на отсутствующий
   файл; все 125 `.tmx` состоят в `PBXResourcesBuildPhase`; все 25+17 имён текстур (включая
   непрямые `image:`-параметры и `../images/tiles.gif` → `tiles`) резолвятся в собранный бандл.
   Максимумы арифметики: `w*h` = 840, `gids*4` = 3360, `pixelWidth` = 560, `pixelHeight` = 384,
   `columns*rows` = 480 — запас до `Int64.MAX` от 2.7·10¹⁵× до 2.4·10¹⁶×.
6. **Методика провалидирована контрольными случаями, которые обязаны были перевернуться.**
   Реплика семантики Swift (`split`+`compactMap UInt32`, `?? 0`, `Data(base64Encoded:)`,
   `expectedCount`) на shipped-корпусе даёт **0** срабатываний, а на 12 намеренных мутациях —
   **12/12** срабатываний: `compression="zlib"`, снятие `encoding`, `-1` значение в CSV,
   нечисловой токен, токен > `UInt32.max`, укороченный base64, мусор в base64, битый XML,
   невалидный UTF-8, `width` слоя 35→36, слой 4·10⁹×4·10⁹. Отдельный контроль для рендерера:
   тайлсет `9·10¹⁸ × 9·10¹⁸` при тайле 1px → `columns*rows = 8.1·10³² > Int64.MAX` = trap,
   при этом загрузчик на том же файле говорит `ok` — то есть «ловушка мимо throw-веток» реальна.
   Без этого контроля вывод «0 срабатываний» был бы непроверяемым утверждением.

**Итог по lanes:** достижимых с текущими данными точек падения игры — **ноль**. Остаток — три
пункта, которые статикой не закрываются в принципе (нужен macOS), и класс «один правленый/
перегенерённый TMX убивает процесс на старте уровня», который является уже зафиксированным B-04.

---

## Инвентаризация (grep + счёт)

База: 18 файлов, 4227 строк. Все счётчики — по тексту вне строковых литералов и `//`-комментариев
(`!` внутри `"…"` и комментариев исключён намеренно, иначе `fatalError("…\(name)…)` и `if !x`
засоряют выборку; первая наивная реализация давала 27 «force-unwrap» — все 27 оказались
префиксным `!` и строками).

| # | Категория | Метод | Счёт | Где |
|---|---|---|---|---|
| A | Force-unwrap `expr!` | перебор **каждого** `!`, не `!=` и не префиксного | **0** | — |
| A2 | Объявления IUO `T!` (implicit-unwrap при использовании) | `[A-Za-z0-9_)\]]!` | **3** | `AppDelegate.swift:5,6`; `GameScene.swift:11` |
| B | `try!` | `\btry!\b` | **0** | — |
| C | `as!` | `\bas!\b` | **0** | — |
| D | `fatalError` | подстрока | **5** | `TMXLevelRuntime.swift:53`; `HUDNode.swift:54`; `ExplosionEffect.swift:54`; `PlayerSpriteNode.swift:38`; `Grenade.swift:108` |
| E | `precondition` / `preconditionFailure` / `assert` / `assertionFailure` / `unreachable` | подстроки | **0** | — |
| F | `first!` / `last!` / `removeFirst()` / `removeLast()` | `\.(first|last)!`, `\.remove(First|Last)\(` | **0** | — |
| G | Dictionary-субскрипты | `(\w+)\[` по базам `attributeDict`/`properties`/`mapProperties`/`pressedBySource`/`sheetTextures`/`patterns` | **50**, из них с `!` — **0** | `TMXMapLoader.swift` (×22, `attributeDict`), `TMXLevelRuntime.swift` (×11 `properties` + `patterns[name]`), `InputState.swift` (×6), `TMXTileMapRenderer.swift` (×2), пр. |
| H | Array/String-субскрипты | те же, без dictionary-баз | **34** | 13 с константным индексом + 21 с переменным |
| H1 | ↳ константный индекс `[0] [3] [8] [9] [10]` | `\[\d+\]` | **13** | `LevelObstacles.swift:62,93,276,464,595`; `PlayerSpriteNode.swift:31,68,70,72,74,76,78`; `ExplosionEffect.swift:48` |
| H2 | ↳ переменный индекс | ручной разбор H | **21** | `TMXMapLoader.swift:324-327` (×4); `TMXTileMapRenderer.swift:53,125,134` (×3); `LevelObstacles.swift:91,306,503,666`; `PlayerSpriteNode.swift:61` (×2), `:70`; `ExplosionEffect.swift:76`; `Grenade.swift:102`; `TMXLevelRuntime.swift:229,518`; `GameScene.swift:995` (×2) |
| I | Деление/остаток `Int` с **плавающим** делителем (trap при 0) | разбор `/`,`%` по не-литералам | **5** | `TMXTileMapRenderer.swift:96,97,101,102`; `TMXLevelRuntime.swift:229` |
| J | Целочисленное умножение/сложение, питаемое **данными карты** (overflow trap) | разбор `*`, `+` на `Int` | **12** | `TMXMapLoader.swift:54,55,276,316,323`; `TMXTileMapRenderer.swift:49,53,66,100,117,125/134,139,141,143` |
| K | `Int(Double)` — trap при NaN/вне диапазона | `\bInt\(` | **1** | `LevelObstacles.swift:90`; плюс `Int($1.value)` `TMXLevelRuntime.swift:513` (UInt32→Int, безопасен по построению) |
| L | `.random(in:)` — trap на пустом/перевёрнутом диапазоне | `\.random\(in:` | **15** | `TMXLevelRuntime.swift:170`; `LevelObstacles.swift:102,331,383,419,422,449,493,574,578,580,671,672,686,708` — все литеральные, все возрастающие |
| M | `throws`-функции / `throw`-сайты | `\bthrows\b`, `\bthrow ` | **2 / 9** | обе в `TMXMapLoader` (`:105`, `:305`); 8 → `catch` в `TMXLevelRuntime.swift:52`, 1 (`decodeLayerData`) → `catch` в `TMXMapLoader.swift:280` → ре-трос через `:118` → тот же catch |
| N | Неразобранный `throw`, убегающий в `main`/AppKit | трассировка M | **0** | ни одного вызова `try` вне `do/catch` или `try?`; `async`/`await`/`rethrows` в дереве нет |
| O | `try?` (не ловушка, но место молчаливого отказа) | — | **2** | `TMXMapLoader.swift:109`; `GameScene.swift:991` |

Дополнительно по данным, без чего счётчики выше были бы утверждением:

| Замер | Результат |
|---|---|
| `.tmx` с `compression` | **0 / 125** (атрибут не встречается ни разу) |
| слои `<data>` по encoding | `csv` 128, `base64` 10, прочего/без атрибута — **0** |
| несовпадений `count == width*height` | **0 / 138** |
| base64-блоков с `data.count < w*h*4` | **0 / 10** (все ровно 3360 байт при 840 клетках) |
| символов вне `[0-9,\s]` в CSV-слоях | **0** |
| максимальный GID / ёмкость атласа | 481 / 480 (`firstgid` 1, 481, 491, 577) → `localIndex` валиден; rejection-ов по guard — **0** |
| flip-флагов (`gid & 0xE0000000`) | **0** |
| `<object x/y/width/height>` не-чисел / `inf` / `nan` / отрицательных | **0** (32 уникальные формы, все целые ≥ 0) |
| DOCTYPE / `<!ENTITY>` / пространства имён / control-chars / сущности | **0** во всех 125 |
| сетка имён | 125/125 `L01S01…L05S25`, лишних и отсутствующих нет |
| `nextLevel` вне сетки или на несохранённый файл | **0**; терминация только `L05S25` (без `nextLevel`) |
| `.tmx` вне `PBXResourcesBuildPhase` | **0 / 125** |
| `.png` вне phase | 2 (`light.png`, `ship_fire.png`) — **никому не ссылается**; коды просят `light_floor`/`light_ceiling`/`ship_fire_frame`, все in-bundle |
| имена текстур (17 литералов + 8 непрямых `image:` + 125 TMX `<image source>`) вне бандла | **0** |
| `#teleport` на карту | только 0 (90 карт) или 2 (35 карт); **ни одной карты с 1 порталом** |
| незнакомых имён `<object>` (уходят в `default: break`) | 0 из 680 объектов / 20 имён |
| `vitorc`-объект | присутствует в **125/125** карт (fallback-ветка `TMXLevelRuntime.swift:62` мертва, но она и не ловушка) |

---

## Таблица достижимости

Вердикты: **И** = недостижимо, доказано данными/построением (data-proven impossible);
**Т** = теоретически достижимо, требует текущих данных (possible with current data);
**M** = нужно macOS.

### A. `fatalError` — единственный живой trap-конструкт

| ID | Место | Конструкт | Условие срабатывания | Вердикт | На чём основан вердикт |
|---|---|---|---|---|---|
| **A1** | `TMXLevelRuntime.swift:53` | `fatalError("Unable to load TMX map …")` | **любой** throw из `TMXMapLoader.load` (7 веток, см. B) | **И** (при текущих данных) / **Т** на изменённой карте | реплика семантики: 0/125 срабатываний + 12/12 контролей; цепочка `nextLevel` замкнута; `L01S01` хардкод-старта существует |
| **A2** | `HUDNode.swift:54` | `fatalError("init(coder:) …")` | декодирование `HUDNode` из nib/storyboard или keyed-копирование | **И** статически | `.storyboard`/`.xib` в репо нет; в `Info.plist` нет `NSMainNibFile`/`NSStoryboardName`; `HUDNode` создаётся только `HUDNode()`; в дереве 0 `fileNamed`, 0 `.copy(`, 0 архиверов |
| **A3** | `ExplosionEffect.swift:54` | то же | то же для `ExplosionEffect` | **И** статически | только `ExplosionEffect.blaster/circular(at:)`; SKSpriteNode-подкласс никем не кодируется |
| **A4** | `PlayerSpriteNode.swift:38` | то же | то же для `PlayerSpriteNode` | **И** статически | единственный конструктор — `PlayerSpriteNode()` в `GameScene.swift:8` |
| **A5** | `Grenade.swift:108` (`GrenadeTrailDot`) | то же | то же для `GrenadeTrailDot` | **И** статически | только `GrenadeTrailDot(position:index:)` в `GameScene.swift:430` |

> Оговорка к A2–A5: «статически» здесь означает отсутствие **явного** пути в коде продукта.
> Приватная реализация SpriteKit может internally key-code узлы (например при `copy()`).
> Ни `copy()`, ни `fileNamed:`, ни архивация в дереве не вызываются и окон восстановления нет,
> поэтому путь закрыт; полная гарантия возможна только прогоном → поз. **M1**.

### B. `throw`-ветки загрузчика (все → A1)

| ID | Место | Ветка | Вердикт | Доказательство по 125 картам |
|---|---|---|---|---|
| B1 | `TMXMapLoader.swift:107` | `resourceNotFound` | **И** | 125/125 файлов на месте, 125/125 в `PBXResourcesBuildPhase`, сетка имён полна, `nextLevel`-цепочка замкнута, `L01S01` существует |
| B2 | `TMXMapLoader.swift:110` | `unreadableResource` (`try? Data(contentsOf:)`) | **M** | IO/бандл-уровень: повреждение бандла, срезанная доставка ресурсов. Статически не исключается и не подтверждается |
| B3 | `TMXMapLoader.swift:118/121` | `invalidXML` | **И** по данным / **M** по эквивалентности парсеров | 125/125 well-formed; нет DOCTYPE, сущностей (`&…;` — 0), пространств имён, control-символов, BOM-аномалий; валидны и как UTF-8, и expat, и (см. M2) надо подтвердить libxml2 |
| B4 | `TMXMapLoader.swift:308` | `unsupportedCompression` — **та самая ветка из v1** | **И** | атрибут `compression` не встречается **ни в одном** из 138 слоёв; контроль `compression="zlib"` реплику перевернул |
| B5 | `TMXMapLoader.swift:314,317` | `invalidLayerData` (base64: decode fail / `data.count < w*h*4`) | **И** | 10/10 base64-блоков декодируются и имеют ровно `3360` байт при `840·4`; контроль «укоротить на 8 символов» перевернул |
| B6 | `TMXMapLoader.swift:338` | `invalidLayerData` (CSV `count != w*h`) | **И** | 128/128 CSV-слоёв: число Swift-токенов == `w*h` ровно; вне `[0-9,\s]` символов нет (значит `compactMap { UInt32($0) }` ничего не теряет); контрольные `-1`/мусор/`>UInt32.max` перевернули |
| B7 | `TMXMapLoader.swift:343` | `unsupportedEncoding` | **И** | только `csv` и `base64`; контроль «снять атрибут encoding» перевернул → это и есть самая вероятная регрессия при переэкспорте из Tiled |

### C. Целочисленные ловушки **без throw** (новый класс, в B-04 не поименован)

> Нумерация `C1n…C15n` — сквозная по этому лейну, суффикс «n» (new). Она **не имеет отношения**
> к находке первичного аудита **C1** (exclusion кабины режет пол), которая здесь не
> пересматривается и не упоминается как предмет разбора.

Swift-`Int` — 64-бит со detecting-арифметикой: переполнение это `SIGTRAP`, а не UB.
Все сайты ниже управляются напрямую из атрибутов `.tmx`, минуя любые проверки валидности.

| ID | Сайт | Операция | Вердикт | Замер shipped-данных |
|---|---|---|---|---|
| C1n | `TMXMapLoader.swift:276` | `currentLayerWidth * currentLayerHeight` (`Int`) | **И** | max `w*h` = **840**, запас 1.1·10¹⁶× |
| C2n | `TMXMapLoader.swift:316` | `expectedCount * 4` | **И** | max **3360**, запас 2.7·10¹⁵× |
| C3n | `TMXMapLoader.swift:323,325-327` | `i*4`, `offset+3` и `data[...]` | **И** | guard `data.count >= w*h*4` выполняется точно (не «с запасом»), индексы 0…3359 |
| C4n | `TMXMapLoader.swift:54,55` | `width*tileWidth`, `height*tileHeight` | **И** | все карты 35×24@16 → max **560 / 384** |
| C5n | `TMXTileMapRenderer.swift:49,117` | `layer.width * layer.height` в guard | **И** | 840; guard всегда `true` на shipped |
| C6n | `TMXTileMapRenderer.swift:53,125,134` | `gids[row*width + column]` | **И** | max индекс **839** при count 840; циклы ограничены `row<height`, `column<width`, guard-ом равества |
| C7n | `TMXTileMapRenderer.swift:66,139,141,143,105,106` | `column*tileWidth`, `(row+1)*tileHeight`, `(column-start)*tileWidth`, `(rowFromTop+1)*tileHeight` | **И** | ≤ 560 / ≤ 384 / ≤ 560 / ≤ imageHeight |
| C8n | `TMXTileMapRenderer.swift:96,97` | `imageWidth / tileWidth`, `imageHeight / tileHeight` — trap при делении на 0 | **И** | guard `:81-82` требует `imageWidth>0, imageHeight>0, tileWidth>0, tileHeight>0`; по данным 0-размеров нет (4 combos: 240×512, 256×16, 512×48 при тайле 16) |
| C9n | `TMXTileMapRenderer.swift:100` | `columns * rows` | **И**, но **Т** на правленых данных | max **480**. Контроль: тайлсет 9·10¹⁸×9·10¹⁸ при тайле 1px → 8.1·10³² → `Multiplication overflow`, при этом загрузчик на том же файле даёт `ok` |
| C10n | `TMXTileMapRenderer.swift:101,102` | `localIndex % columns`, `/ columns` — trap при 0 | **И** | `columns = max(1, …)` → ≥1 по построению |
| C11n | `TMXTileMapRenderer.swift:56` | `Int(gid - tileset.firstGID)` — **UInt32 подчёркивание**, trap при `gid < firstGID` | **И** (строго) | `tileset(for:)` фильтрует `$0.firstGID <= gid` (`:76`) и берёт `max` из них → выбранный `firstGID ≤ gid` всегда. Единственный «страшный» сайт, который доказуемо безопасен без данных |
| C12n | `TMXMapLoader.swift:321` | `reserveCapacity(expectedCount)` | **И** | ≤ 840 (на огромном значении — не trap, а `exc.badAddress`/bad_alloc; тоже требует данных, которых нет) |
| C13n | `GameScene.swift:996` | `(stage-1)*25 + (screen-1)` | **И** | `\d{2}` → stage,screen ∈ 00…99; зажат `max(0, min(124, …))`; обратного переполнения нет |
| C14n | `GameScene.swift:662`, `:627` | `points + value`, `lives * 1_000` | **И** | value ≤ 1850 за вызов, points зажат 999_999; lives < 9 по guard |
| C15n | `TMXLevelRuntime.swift:515,516,518` | `seed &+ i*97`, `seed/7 &+ i*53`, `seed + i` | **И** | `seed = (…)& 0x7fffffff` ∈ [0, 2³¹); `i` < 10; `&*`/`&+` маскирующие; `% 500`/`% 286`/`% 5` на положительных |

### D. Остальные ловушки-кандидаты (не данные карты)

| ID | Место | Конструкт | Вердикт | Обоснование |
|---|---|---|---|---|
| D1 | `GameScene.swift:11` + 49 обращений `currentLevel.` | IUO `currentLevel: TMXLevelRuntime!` → nil-разыменование = trap | **И** | присваивается в `didMove(to:)` (`:60`) до первого обращения; `update`/`fixedUpdate` SpriteKit вызывает только после `didMove`; другие пути (`transition:639`, `restart:957`) тоже присваивают до использования. Единственный реальный исход при сбое загрузки — A1, до D1 дело не доходит |
| D2 | `AppDelegate.swift:5,6` | IUO `window`, `gamepadInput` | **И** | `window` присваивается non-failable-инициализатором `NSWindow(contentRect:…)` на строке 10 до первого использования (16); `gamepadInput` — на 35 до 36. В `applicationDidFinishLaunching` нет ветки раннего возврата между ними |
| D3 | `LevelObstacles.swift:91` | `tubeFrames[7 - animationIndex]` (массив 8) | **И** | `animationIndex = min(7, Int(elapsed/0.0225))`, `elapsed = max(0, 0.18 - animationTimer)`; `animationTimer` уменьшается только на фиксированный `dt`, значит `elapsed ≤ 0.18+1/60` → `Int(...) ≤ 8` → индекс ∈ [0,7] |
| D4 | `LevelObstacles.swift:90` | `Int(Double)` — trap при NaN/out-of-range | **И** | опирается на инвариант: `dt` в `fixedUpdate` **всегда** `GameConstants.fixedTimeStep` (цикл-аккумулятор в `GameScene.update` + clamp `maximumFrameTime`), т.е. `dt = 1/60` — константа компиляции. Если инвариант когда-нибудь нарушат (передача сырого frame time), D3/D4 становятся живыми → поз. **M3** |
| D5 | `LevelObstacles.swift:306,503,666`; `PlayerSpriteNode.swift:61,70`; `ExplosionEffect.swift:76` | `frames[frameIndex]`, `frames[runSequence[animationIndex]]` | **И** | делители `frames.count`/`runSequence.count` — массивы, построенные предыдущим `for index in 0..<8/3/2/11` с литеральной границей; длина ≥ 1 по построению; значения `runSequence` = 0…8 при `frames.count = 11` |
| D6 | `PlayerSpriteNode.swift:68,70,72,74,76,78` (H1) | `frames[0/3/8/9/10]` | **И** | `frameCount = 11` (static let), все литералы < 11 |
| D7 | `LevelObstacles.swift:62,93,276,464,595`; `ExplosionEffect.swift:48`; `PlayerSpriteNode.swift:31` | `built*[0]` | **И** | массив заполнен в `for 0..<N` непосредственно перед субскриптом, N ∈ {8,3,2,5,10,11} ≥ 1 |
| D8 | `TMXLevelRuntime.swift:229` | `portals[(index+1) % portals.count]` — trap при `count == 0` | **И** | `guard portals.count >= 2` на `:227`; по данным число порталов на карту — только 0 или 2 (1 не встречается, так что и «одиночный портал → nil» не реализуется) |
| D9 | `Grenade.swift:102` | `palette[index % palette.count]` | **И** | литерал из 4 цветов; `index` = monotone `grenadeTrailIndex ≥ 0` |
| D10 | `TMXLevelRuntime.swift:518` | `colors[(seed+i) % colors.count]` | **И** | литерал из 5; `seed ≥ 0` (маска), `i < 10` |
| D11 | `GameScene.swift:995` | `levelName[stageRange]` / `[screenRange]` | **И** | `Range(match.range(at:), in:)` — failable, оба в `guard let`; при неудаче `return 0` |
| D12 | `.random(in:)` ×15 (L) | trap «Range requires lowerBound <= upperBound» | **И** | все 15 — литеральные возрастающие диапазоны: `32...159`, `50...300`, `60...300`, `20...160`, `0..<6`, `0..<360`, `1...3`, `0...32`, `0...16`, `-3.0...3.0`, `-1.0...1.0`, `1...UInt64.max` |
| D13 | Dictionary (G, 50 сайтов) | `dict[k]!` | **И** | ни одного `!`; чтения — `?? default` / `guard let` / `if let`, записи — `dict[k] = …`; `TMXMapLoader.swift:346-350` (`int/uint/cgfloat`) возвращают 0 на мусоре молча (это B-04, не ловушка) |
| D14 | `Grenade.swift:85`, `LevelObstacles.swift:540,541` | `% 2`, `% 4`, `/ 4` | **И** | литеральные ненулевые делители, `index < 8` из `for 0..<8` |
| D15 | `ExplosionEffect.swift:25,30,37`; `PlayerSpriteNode.swift:22` | `1.0 / 22.0`, `1.0 / 18.0` (литералы) и `1.0 / CGFloat(frameCount)` | **И** | frameCount ∈ {5,10,11} литералы; и Float-деление на 0 в Swift не trap-ает |
| D16 | `GamepadInput.swift:97` | `DispatchQueue.main.async` → `scene?.setGamepadStatus` | **И** | единственный внеосевой путь в UI; `InputState` закрыт `NSLock`, reentrancy нет (`set` не вызывает `snapshot`). Гонка как источник trap не обнаружена |

### E. Итоговая сводка вердиктов

| Вердикт | Строк таблицы | Состав |
|---|---|---|
| **Т** — достижимо с текущими 125 картами / 153 PNG | **0** | — |
| **И** — недостижимо, доказано данными или построением кода | **42** | все строки A–D, кроме B2 |
| ↳ из них **И**, но остаются латентными ловушками на изменённых/перегенерённых данных (одна правка TMX убивает процесс) | **11** | A1, B3–B7, C1n–C3n, C9n, C12n |
| **M** — нужен macOS | **1 строка** (B2) **+ 2 остаточных риска** | B2 (`unreadableResource`); A2–A5 (внутреннее keyed-кодирование SpriteKit → поз. M4); D3/D4 (инвариант `dt` → поз. M3). Отдельно M1/M2/M5/M6 |

Всего разобранных строк: 43 (A 5 + B 7 + C 15 + D 16). Проверено 111 ссылок `файл:строка`,
все разрешаются в строку, содержащий заявленный конструкт.

---

## Что проверить на macOS

Только то, что принципиально не закрывается статикой на этом хосте. Сборка (`xcodebuild`) на
Linux невозможна, `-frontend -parse` 18/18 не является ни сборкой, ни typecheck-ом.

1. **M1 — старт и полный проход 125 уровней (`L01S01` → `L05S25`) без `SIGTRAP`.**
   Это закрывает A1/B-группу эмпирически: каждый уровень реально проходит
   `TMXMapLoader.load` + `TMXTileMapRenderer` (в т.ч. 4 карты с base64 — `L01S01…L01S04`)
   и ни разу не попадает в `fatalError`. Отдельно: `L01S04` — единственная карта с
   `../images/tiles.gif` и `../images/rocks.gif`; Swift из пути делает имена `tiles`/`rocks`,
   в бандле есть `tiles.png`/`rocks.png` — убедиться, что `SKTexture(imageNamed:)` резолвится,
   а не отдаёт placeholder (визуал, не ловушка).
2. **M2 — эквивалентность `XMLParser`(libxml2) и моей expat-основы реплики на 125 файлах.**
   Аномалий, где парсеры расходятся (DOCTYPE, сущности, namespaces, control-chars), в данных
   нет, но `parser.parse() == false` при `delegate.error == nil` (`TMXMapLoader.swift:120-122`)
   — единственная ветка, которую нельзя исключить без Darwin-парсера. Достаточно 125× прогона
   загрузчика с логом.
3. **M3 — инвариант `dt == GameConstants.fixedTimeStep` во всех вызовах `fixedUpdate`.**
   От него зависят D3/D4 (`tubeFrames[7 - animationIndex]`, `Int(elapsed / 0.0225)`) и
   «незастреивающие» `while`-циклы (`TeleportPortal:303`, `ExplosionEffect:69`).
   Подтвердить замером на просадках FPS (alt-tab, drag окна, внешняя нагрузка): аккумулятор
   в `GameScene.update` обязан резать `frameTime` до 0.25 и никогда не передавать в `fixedUpdate`
   ничего, кроме 1/60. Если хотя бы один вызов получит сырое время — D3/D4 становятся **Т**.
4. **M4 — отсутствие keyed-кодирования SpriteKit-подклассов (закрывает остаток A2–A5).**
   Проверить: переключение окна/loss of focus, Cmd+Q, перерисовка при `showHitboxes`
   (`debugOverlay.removeAllChildren()`), `removeFromParent()` на узле в середине `fixedUpdate`
   (`TeleportPortal`/`Bubble`/`Egg`-фильтры). Ни один из этих путей не должен позвать
   `init(coder:)`.
5. **M5 — поведение `SKTexture(rect:in:)` на граничных rect.**
   Guard `:100` отсекает выход за атлас, поэтому unit-rect по построению в [0,1]; но сам факт
   вызова с нормализованными rect на реально загруженном `SKTexture(imageNamed:)` надо увидеть
   в логах хотя бы на одной tile-карте (`L01S01`) и на `missile`/`egg`/`bubble`/`teleport`/
   `turret_tube` (все режут атлас через `SKTexture(rect:in:)`).
6. **M6 (вне crash-класса, отметить одним прогоном):** `light.png` и `ship_fire.png` лежат в
   `Exolon/Resources/`, но не состоят в `PBXResourcesBuildPhase` — в бандл не попадают. Ссылок
   на них в коде нет (`ship_fire_frame`/`light_floor`/`light_ceiling` — отдельные, in-bundle),
   так что это мусорные файлы, а не падение; прогон это подтвердит косвенно.

Рекомендация по устранению (одна точка, снимает A1 + всю C-группу как класс): `TMXMapLoader`
должен возвращать валидированную структуру (непустая карта, `width/height/tilewidth/tileheight > 0`,
`w*h` совпадает, арифметика на `Int64` с проверкой `multipliesOverflowing`/`addingOverflowing`
или `Int` через `multipliedReportingOverflow`), а `TMXLevelRuntime.swift:53` — не `fatalError`,
а воспроизводимый экран ошибки уровня с именем ресурса и причиной.

---

Вердикт: **pass**

*Оговорка объёма:* `pass` означает, что при текущих 125 `.tmx` и 153 `.png` статически
обнаружен **ноль** достижимых точек падения процесса (0 «possible with current data»), что
подтверждено замерами и 12/12 контрольных мутаций, которые были обязаны перевернуться. Он не означает,
что сборка и прогон успешны: `swiftc` на этом хосте способен только на `-frontend -parse`
(18/18 синтаксис чист), typecheck и сборка не выполнялись. Найденный новый класс (C-группа:
целочисленное переполнение в геометрии загрузчика/рендерера минуя `throw`) остаётся
латентным риском на будущих/перегенерённых данных и требует отдельной находки, если воркфлоу
аудита это предполагает; по текущему shipped-корпусу он недостижим.
