# UI-текст и локализация — реестр всех видимых игроку строк

Лейн: `ui-text-localization` (read-only). HEAD `52795d1`.
Объект: 18 Swift-файлов продукта (`Exolon/`, 4227 строк), `Exolon/Resources/Info.plist`,
`Exolon.xcodeproj/project.pbxproj`, `README.md`, `ORIGINAL_MECHANICS.md`.

Метод: машинный разбор всех строковых литералов вне строк комментариев
(`python3`, одноразовые скрипты в `/tmp/lane-uitext/`), затем ручной отбор того, что
реально доезжает до глаз игрока. Замеры геометрии HUD — по метрике Menlo
(ширина символа ≈ 0.602 em). Замеры по данным — по всем 125 `.tmx` из
`Exolon/Resources/`. Ни один файл репозитория, кроме этого отчёта, не изменён.
Finding **C1 не пересматривается**; достижимость `fatalError`-строк — в
`crash-surface.md`, здесь они учтены только как текстовая поверхность.

Якоря — полный репозиторный путь + номер строки, как в исходнике на HEAD `52795d1`.

---

## Итог

1. **Видимый текст: 64 позиции реестра (№1–№64 в таблице ниже), что после
   разворачивания составных ячеек (#21/#22 — по два варианта, #55 — семь состояний)
   даёт 72 конечные отображаемые фразы.** Из 64 позиций **55 внутриигровые** (№1–№55:
   одна AppKit-подпись окна + SpriteKit-labels, плюс одна неявная позиция №1a — имя
   приложения в меню-баре, не являющееся литералом) и **9** (№56–№64) доходят до
   пользователя только через отчёт о падении (`fatalError` +
   `TMXMapLoader.errorDescription`). **Кредитов, экрана
   «об игре», экрана настроек, подсказки управления и какой-либо error/alert-панели нет
   вообще**: в дереве 0 `NSMenu`/`mainMenu`/`NSAlert`, текст ошибки — только `fatalError`.
2. **Локализации нет ни в каком виде — 0.** Ни `NSLocalizedString`, ни `String(localized:)`,
   ни `.strings`, ни `.xcstrings` (String Catalog), ни `.lproj`. Все 64 позиции реестра — голые
   Swift-литералы, вшитые в код. При этом `Exolon.xcodeproj/project.pbxproj:1062` объявляет
   `knownRegions = (en, Base)`, а `Exolon/Resources/Info.plist:5-6` подставляет
   `$(DEVELOPMENT_LANGUAGE)`, **которая не определена ни в одной build-конфигурации**
   (`grep -n DEVELOPMENT_LANGUAGE` по pbxproj → 0 совпадений): то есть бандл несёт пустую
   development region и фиктивную запись `Base`, не закрывающую ни одного ресурса.
   Стоимость добавления i18n для этого набора — **64 ключа (14 с плейсхолдерами), либо
   72 при разворачивании ON/OFF-вариантов и семи состояний**, причём 7 из них (#55) — это
   сейчас сырые `rawValue` enum'а, прогнанные через `.uppercased()`; плюс необходим
   MainMenu.xib/программное меню, без которого локализованное About/Настройки недостижимы.
3. **Один и тот же milestone игрок видит под двумя именами.** Экран заставки говорит
   `STEP 10` (`Exolon/GameCore/GameScene.swift:832`), все остальные поверхности —
   `STEP 9` (отладочная строка `GameScene.swift:67`, `:656`, `:984`; заголовок окна
   `Exolon/Platform/macOS/AppDelegate.swift:16`; `README.md:1`), а ключи персистентности
   живут под третьим именем — `Exolon.Step10.*` (`Exolon/GameCore/GameState.swift:25-31`).
4. **Надпись `CONTINUE` против кода, который её никогда не выполнит по назначению.**
   Ветка `CONTINUE · ZONE %03d` (`GameScene.swift:902`) выбирается по `hasSavedCheckpoint`
   (`:901`), но на каждом холодном старте `loadPersistentState()` сам удаляет сохранённый
   чекпойнт (`:690`) и выставляет флаг в `false` (`:691`), а
   `GamePersistence.loadCheckpoint()` (`GameState.swift:40`) имеет **ноль вызывающих** во
   всём дереве. Итог: после любой предыдущей сессии заставка показывает
   `NEW GAME · ZONE 000` (`:903`), а записанные в UserDefaults уровень/патроны/очки/жизни
   читаются только чтобы быть удалёнными.
5. **Четыре строки — мёртвый текст.** `CONTENT COMPLETE` (`:752`), `ZONE %03d` (`:753`),
   `CONTINUES WITH %@` (`:754`) и `NEXT ZONE` (`:742`) рендерятся только из `else`-ветки
   `:750-756`, которая по приложенным данным недостижима: из 125 `.tmx` ровно один
   (L05S25) не имеет `nextLevel`, а все 124 ненулевых `nextLevel` указывают внутрь
   `includedLevels` (`:53`). Единственная достижимая концовка — `FULL COMBAT ABILITY`
   (`:745`).
6. **`HIGH SCORE` на GAME OVER — это не рекорд, а то же самое число.** `awardPoints()`
   уже обновила рекорд на каждом начислении (`:663-666`), поэтому проверка
   `points > highScore` в `enterGameOver()` (`:724-727`) мертва, а две строки тирминала
   (`:731`, `:732`) при новом рекорде печатают идентичное значение.
7. **Геометрия HUD в норме, отладочная строка — нет.** Пять колонок
   (`Exolon/GameCore/HUDNode.swift:27-31`, `:58-62`) расходятся без перекрытий
   (самая широкая пара — `POINTS`/`999999`: 246.1..285.9 против 244.3..287.7 по вертикали
   `y=32`/`y=13`), все значения гарантированно фиксированной длины. Зато три отладочные
   подписи, включаемые одной кнопкой F1 (`GameScene.swift:224-226`), стоят на **одной
   базовой линии `y=370`** и перекрываются: у `inputLabel` левый край `x=8`, правый
   `≈229.8` при полной длине, у `stepLabel` левый край `≈190.7…201.2` → **нахлёст
   28.6…39.2 логических пикселя, до 7.6% ширины**. `SKLabelNode` не умеет ни
   truncate, ни перенос: в дереве 0 `lineBreakMode`/`preferredMaxLayoutWidth`/
   `numberOfLines`, то есть длинная строка просто рисуется поверх соседней.
8. **Отладочный текст и бейдж теста рисуются прямо по арте уровня.** Все 125 карт —
   560×384 px при логических 512×384 (`GameConstants.swift:5`), image-слой
   `Original Static Scenery` объявлен 512×384, то есть покрывает и полосу `y≈357…384`.
   `stepLabel`/`inputLabel`/`gamepadLabel` (`zPosition = 120`, `GameScene.swift:71`, `:78`, `:86`)
   и `testModeLabel` (`zPosition = 121`, `:111`) лежат **поверх** этой арт-полосы
   (карта — `zPosition = 0`, `Levels/TMXLevelRuntime.swift:87`) без подложки, в кегле
   5.5–7 pt. Для сравнения: нижний HUD имеет собственную чёрную панель
   (`HUDNode.swift:14-20`), а верхняя «HUD-подобная» полоса — нет.
9. **3-значных жизней и 7-значных очков не бывает — но только по воле констант, а не текста.**
   `points` зажат `min(999_999, …)` (`GameScene.swift:662`), `lives` стартует с 9
   (`GameState.swift:83`) и может только вырасти до 9 (`GameScene.swift:628`), поэтому
   `%06d`/`%03d`/`%02d` никогда не расширяются. Единственное незащищённое место —
   `loadHighScore()` (`GameState.swift:71-72`) читает UserDefaults без верха, так что
   вручную записанное значение >999999 отрисует `HIGH SCORE %06d` (`:906`) шире шести знаков.
10. **Согласованность цифр в тексте обеспечена двумя независимыми источниками.**
    Единственный баннер с суммой — литерал `"+1000"` (`GameScene.swift:302`), тогда как сама
    сумма возвращается из другого файла (`Levels/TMXLevelRuntime.swift:221 return 1_000`);
    награды `1_000` (`:403`), `150` (`:486`), `lives * 1_000` (`:627`) вообще никаким
    текстом не сопровождены.

---

## Реестр видимых строк

### A. Оболочка AppKit (1)

| # | Строка | Якорь | Где |
|---|---|---|---|
| 1 | `Exolon Remake — Step 9 Rebase` | `Exolon/Platform/macOS/AppDelegate.swift:16` | заголовок окна |
| 1a | `Exolon` (не литерал, от `PRODUCT_NAME`) | `Exolon.xcodeproj/project.pbxproj:1038-1039` | имя в меню-баре; `NSMenu` в дереве нет — меню приложения остаётся системной заглушкой |

### B. HUD, всегда виден в игре (5 подписей + 5 формата)

| # | Строка/шаблон | Якорь | Рендер |
|---|---|---|---|
| 2 | `AMMO` | `Exolon/GameCore/HUDNode.swift:27` | 11 pt, Menlo-Bold, `.cyan`, центр `x=48`, `y=32` |
| 3 | `GRENADES` | `Exolon/GameCore/HUDNode.swift:28` | 11 pt, `.yellow`, `x=145` |
| 4 | `POINTS` | `Exolon/GameCore/HUDNode.swift:29` | 11 pt, `.green`, `x=266` |
| 5 | `LIVES` | `Exolon/GameCore/HUDNode.swift:30` | 11 pt, `.white`, `x=382` |
| 6 | `ZONES` | `Exolon/GameCore/HUDNode.swift:31` | 11 pt, `.magenta`, `x=470` |
| 7 | `%02d` (патроны) | `Exolon/GameCore/HUDNode.swift:58` | значение 12 pt, `y=13` |
| 8 | `%02d` (гранаты) | `Exolon/GameCore/HUDNode.swift:59` | 12 pt, `.magenta` |
| 9 | `%06d` (очки) | `Exolon/GameCore/HUDNode.swift:60` | 12 pt, `.cyan` |
| 10 | *(без формата)* `String(max(0, state.lives))` | `Exolon/GameCore/HUDNode.swift:61` | единственный незаполненный до фикс. ширины столбец |
| 11 | `%03d` (зона) | `Exolon/GameCore/HUDNode.swift:62` | 12 pt, `.magenta` |

### C. Заставка (6)

| # | Строка/шаблон | Якорь |
|---|---|---|
| 12 | `EXOLON` | `Exolon/GameCore/GameScene.swift:831` (30 pt, Menlo-Bold, `.white`, `y=244`) |
| 13 | `STEP 10` | `Exolon/GameCore/GameScene.swift:832` (11 pt, `.cyan`, `y=214`) |
| 14 | `CONTINUE · ZONE %03d` | `Exolon/GameCore/GameScene.swift:902` (10 pt, `.yellow`) |
| 15 | `NEW GAME · ZONE 000` | `Exolon/GameCore/GameScene.swift:903` |
| 16 | `HIGH SCORE %06d` | `Exolon/GameCore/GameScene.swift:906` (8 pt, Menlo, `.white`) |
| 17 | `SPACE / □ — START` | `Exolon/GameCore/GameScene.swift:852` (8 pt) |

### D. Пауза (8)

| # | Строка/шаблон | Якорь |
|---|---|---|
| 18 | `PAUSE` | `Exolon/GameCore/GameScene.swift:785` (19 pt, `y=254`) |
| 19 | `> RESTART <` | `Exolon/GameCore/GameScene.swift:816` (14 pt, `.yellow`, `y=213`) |
| 20 | `RESTART` | `Exolon/GameCore/GameScene.swift:816` (14 pt, `.white`) |
| 21 | `> INVULNERABILITY: ON <` / `… OFF <` | `Exolon/GameCore/GameScene.swift:819` + `:821` (12 pt) |
| 22 | `INVULNERABILITY: ON` / `… OFF` | `Exolon/GameCore/GameScene.swift:819` + `:822` |
| 23 | `↑ / ↓  D-PAD — SELECT` | `Exolon/GameCore/GameScene.swift:805` (7 pt, `y=151`) |
| 24 | `SPACE / □ — ACTIVATE` | `Exolon/GameCore/GameScene.swift:806` (7 pt, `y=137`) |
| 25 | `P / OPTIONS — RESUME` | `Exolon/GameCore/GameScene.swift:807` (7 pt, `y=123`) |
| 26 | `TEST MODE · INVULNERABILITY` | `Exolon/GameCore/GameScene.swift:106` (6.5 pt, `.yellow`, `y=357`, `z=121`) |

### E. Тирминал: GAME OVER / концовки (8)

| # | Строка/шаблон | Якорь |
|---|---|---|
| 27 | `GAME OVER` | `Exolon/GameCore/GameScene.swift:730` (20 pt) |
| 28 | `SCORE %06d` | `Exolon/GameCore/GameScene.swift:731` и `:746` (10 pt, `.yellow`) |
| 29 | `HIGH SCORE %06d` | `Exolon/GameCore/GameScene.swift:732` (8 pt) — второй адрес того же #16 |
| 30 | `SPACE / □ — RESTART` | `Exolon/GameCore/GameScene.swift:733` |
| 31 | `CONTENT COMPLETE` | `Exolon/GameCore/GameScene.swift:752` — **недостижим, см. Итог-5** |
| 32 | `ZONE %03d` | `Exolon/GameCore/GameScene.swift:753` — **недостижим** |
| 33 | `CONTINUES WITH %@` | `Exolon/GameCore/GameScene.swift:754` — **недостижим** |
| 34 | `NEXT ZONE` | `Exolon/GameCore/GameScene.swift:742` — **недостижим** |
| 35 | `FULL COMBAT ABILITY` | `Exolon/GameCore/GameScene.swift:745` (единственная достижимая концовка) |
| 36 | `ALL 125 ZONES COMPLETE` | `Exolon/GameCore/GameScene.swift:747` |
| 37 | `SPACE / □ — TITLE` | `Exolon/GameCore/GameScene.swift:748` и `:755` |

### F. Баннеры по центру экрана (3)

| # | Строка | Якорь | Рендер |
|---|---|---|---|
| 38 | `EXOSKELETON ON` | `Exolon/GameCore/GameScene.swift:237` | 12 pt, `y=205`, `z=200`, затухание 0.75+0.20 с (`:669-681`) |
| 39 | `EXOSKELETON OFF` | `Exolon/GameCore/GameScene.swift:237` | то же |
| 40 | `+1000` | `Exolon/GameCore/GameScene.swift:302` | единственный текстовый фидбек начисления |

### G. Отладочная полоса F1 (выключена по умолчанию, `GameScene.swift:73, 80, 88`; включается `:224-226`)

| # | Строка/шаблон | Якорь |
|---|---|---|
| 41 | `STEP 9 · ALL 125 ORIGINAL ZONES` | `Exolon/GameCore/GameScene.swift:67` (7 pt, `y=370`, `z=120`) |
| 42 | `STEP 9 · L01S01 · ZONE 000` | `Exolon/GameCore/GameScene.swift:984` (hard-coded дубль #43) |
| 43 | `STEP 9 · <внутренний id карты> · ZONE %03d` | `Exolon/GameCore/GameScene.swift:656` |
| 44 | `GAMEPAD: waiting / keyboard ready` | `Exolon/GameCore/GameScene.swift:82` **и** `Exolon/Platform/macOS/GamepadInput.swift:96` |
| 45 | `GAMEPAD: connected (N)` | `Exolon/Platform/macOS/GamepadInput.swift:96` (5.5 pt, right-align, `x=504`) |
| 46 | `INPUT: —` | `Exolon/GameCore/GameScene.swift:1071` (5.5 pt, left-align, `x=8`) |
| 47 | `INPUT: ` + склейка через `+` | `Exolon/GameCore/GameScene.swift:1071` |
| 48-53 | `LEFT` `RIGHT` `JUMP` `CROUCH` `FIRE` `GRENADE` | `Exolon/GameCore/GameScene.swift:1065` `:1066` `:1067` `:1068` `:1069` `:1070` |
| 54 | ` · STATE: ` | `Exolon/GameCore/GameScene.swift:1072` |
| 55 | `TITLE` `PLAYING` `PAUSED` `PLAYERDEAD` `RESPAWNING` `GAMEOVER` `CONTENTCOMPLETE` | `Exolon/GameCore/GameState.swift:4-10` → печатаются как `flowState.rawValue.uppercased()` в `GameScene.swift:1072` |

### H. Текст, доходящий до пользователя только через отчёт о падении (9)

| # | Строка/шаблон | Якорь |
|---|---|---|
| 56 | `Unable to load TMX map <id>: <error>` | `Exolon/GameCore/Levels/TMXLevelRuntime.swift:53` (единственный `fatalError` с динамическим текстом) |
| 57 | `TMX resource not found: %@` | `Exolon/GameCore/Levels/TMXMapLoader.swift:94` |
| 58 | `TMX resource unreadable: %@` | `Exolon/GameCore/Levels/TMXMapLoader.swift:95` |
| 59 | `TMX XML error: %@` | `Exolon/GameCore/Levels/TMXMapLoader.swift:96` |
| 60 | `Unsupported TMX encoding: %@` | `Exolon/GameCore/Levels/TMXMapLoader.swift:97` |
| 61 | `Unsupported TMX compression: %@` | `Exolon/GameCore/Levels/TMXMapLoader.swift:98` |
| 62 | `Invalid TMX layer data: %@` | `Exolon/GameCore/Levels/TMXMapLoader.swift:99` |
| 63 | `unknown parser error` | `Exolon/GameCore/Levels/TMXMapLoader.swift:121` |
| 64 | `init(coder:) has not been implemented` | `Exolon/GameCore/HUDNode.swift:54`, `Exolon/GameCore/Weapons/Grenade.swift:108`, `Exolon/GameCore/Player/PlayerSpriteNode.swift:38`, `Exolon/GameCore/Effects/ExplosionEffect.swift:54` |

### I. Отрицательная инвентаризация (чего в текстовой поверхности нет)

- нет ни одного `NSAlert` / `presentError` / `NSSavePanel` / in-game «ошибка загрузки»;
- нет экрана кредитов и нет строки версии в игре (`0.3` живёт только в
  `Exolon/Resources/Info.plist:17`, а `MARKETING_VERSION = 0.5` —
  `Exolon.xcodeproj/project.pbxproj:1424` и `:1443` — в бандл не попадает, потому что
  `GENERATE_INFOPLIST_FILE = NO` (`:1420`, `:1439`) и подстановки `$(MARKETING_VERSION)`
  в plist нет);
- нет экрана управления: подсказки `GameScene.swift:805-807` достижимы только из паузы,
  а на заставке показана единственная строка `SPACE / □ — START` (`:852`);
- нет ни одной строки про F1, хотя именно она (`Exolon/Platform/macOS/GameView.swift:66`)
  включает весь блок G;
- нет `Localizable.*`, `.strings`, `.xcstrings`, `.lproj` (см. ниже).

---

## Дубли и расхождения

| Концепт | Вариант 1 | Вариант 2 (+) | Оценка |
|---|---|---|---|
| Номер вехи (milestone) | `STEP 10` — `Exolon/GameCore/GameScene.swift:832` (заставка) | `STEP 9` — `GameScene.swift:67`, `:656`, `:984`; `Exolon Remake — Step 9 Rebase` — `Exolon/Platform/macOS/AppDelegate.swift:16`; `# Exolon — Step 9 Rebase (test archive)` — `README.md:1`; `Exolon.Step10.HasCheckpoint … HighScore` (7 ключей) — `Exolon/GameCore/GameState.swift:25-31` | **Расхождение, видимость 1-го уровня:** игрок на заставке читает `STEP 10`, заголовок его окна и README говорят «Step 9», а persisted-данные лежат под третьим именем (`Step10`). Проверено построчно, все пять поверхностей на HEAD `52795d1` именно таковы |
| Счёт | `POINTS` — `HUDNode.swift:29` | `SCORE %06d` — `GameScene.swift:731`, `:746`; `HIGH SCORE %06d` — `:732`, `:906`; переменная одна — `GameState.points` (`GameState.swift:87`) | Дублирование: два имени для одного числа в двух соседних поверхностях (HUD снизу, тирминал по центру) |
| Зона | `ZONES` (мн. ч.) — `HUDNode.swift:31`, значение `%03d` — `:62` | `ZONE %03d` — `GameScene.swift:656`, `:753`, `:902`, `:984` | Дублирование: под заголовком в мн. числе скрывается единственный текущий индекс; `NEW GAME · ZONE 000` (`:903`) при этом жёстко зашивает `000` вместо формата |
| Идентификатор зоны | имя ресурса `L01S01` — `GameScene.swift:12`, `:692`, `:956`; `Exolon/GameCore/Levels/TMXLevelRuntime.swift:420`, `:500-505` | свойство `zoneNumber` в `.tmx`; вывод по regex `^L(\d{2})S(\d{2})$` — `GameScene.swift:988-996` | **Дублирование с одним «мёртвым» источником:** Swift не читает `zoneNumber` ни разу (`grep zoneNumber` → только функция `GameScene.swift:988` и вызовы `:116`, `:641`), а в данных свойство есть в 117 файлах и отсутствует в 8 (`L01S01`…`L01S08`). Расхождений значений нет (замерено: 0 из 117) |
| Статус геймпада | `GAMEPAD: waiting / keyboard ready` — `GameScene.swift:82` | та же строка дословно — `Exolon/Platform/macOS/GamepadInput.swift:96` | Два независимых литерала: любое изменение одного рассинхронит начальное состояние и состояние после дисконнекта |
| Формат отладочного заголовка | шаблон с интерполяцией — `GameScene.swift:656` | дословный результат того же шаблона — `GameScene.swift:984` (`STEP 9 · L01S01 · ZONE 000`) | Третье место (`:67`) — вообще другой префикс того же слота. Смена формата потребует правки в трёх несвязанных строках |
| Тест-режим | `INVULNERABILITY: ON/OFF` — `GameScene.swift:819-822` | `TEST MODE · INVULNERABILITY` — `GameScene.swift:106`; `test Invulnerability` — `README.md:11` | Три написания одного флага `testInvulnerabilityEnabled` (`:45`) |
| Глифы-разделители | `·` U+00B7 ×9 | `—` U+2014 ×9, `□` U+25A1 ×5, `↑`/`↓` U+2191/U+2193 ×1 (`GameScene.swift:67`, `:106`, `:656`, `:733`, `:748`, `:755`, `:805`, `:806`, `:1071`, `:1072`; `AppDelegate.swift:16`) | Смешаны em-dash и middot как «селектор/разделитель»; `□` — глиф именно PlayStation-раскладки, на Xbox/8BitDo-профиле `GameScene.swift:806` и `:852` обещает не ту кнопку |
| Типографика | `↑ / ↓  D-PAD — SELECT` — `GameScene.swift:805` | одиночные пробелы во всех остальных `GameScene.swift:806`, `:807`, `:733`, `:748`, `:755`, `:852` | Двойной пробел после `↓` — единственный сбой выравнивания в наборе |
| Шрифт | `Menlo` ×9 | `Menlo-Bold` ×17 (26 литерала на 17 sites `SKLabelNode(fontNamed:)`: `HUDNode.swift:5-9`, `:35`; `GameScene.swift:14-17`, `:22`, `:785`, `:787`, `:796`, `:831`, `:832`, `:834`, `:843`, `:852`, `:861-864`) | Нет ни одной константы имени шрифта; кегли 5.5/6.5/7/8/10/11/12/14/19/30 разбросаны литералами |
| Числовые награды | `"+1000"` — `GameScene.swift:302` | `return 1_000` — `Levels/TMXLevelRuntime.swift:221`; `awardPoints(1_000)` — `GameScene.swift:403`; `awardPoints(150)` — `:486`; `awardPoints(gameState.lives * 1_000)` — `:627` | Текст суммы и сама сумма — в разных файлах; три из четырёх начислений без текстового фидбека вообще |
| Версия | `CFBundleShortVersionString 0.3` — `Exolon/Resources/Info.plist:17` | `MARKETING_VERSION = 0.5` — `Exolon.xcodeproj/project.pbxproj:1424`, `:1443` | В видимый текст не попадает ни то, ни другое; дублирование зафиксировано, отнесено в `pbxproj-build.md` |

---

## Локализация

**Ответ: нет, инфраструктуры локализации в проекте ноль.**

Доказательства (каждое проверено на HEAD `52795d1`):

| Проверка | Результат |
|---|---|
| `NSLocalizedString`, `String(localized:)`, `Bundle.main.localizedString`, `localizedStandard` | 0 совпадений во всём `Exolon/` |
| `*.strings` / `*.xcstrings` (String Catalog) / `Localizable.*` | файлов нет (`find` по дереву — 0) |
| `*.lproj` | каталогов нет (0) |
| `Exolon.xcodeproj/project.pbxproj` | `developmentRegion = en` (`:1060`), `knownRegions = (en, Base)` (`:1062`); совпадений `lproj\|Localizable\|.strings\|xcstrings` — **0** |
| `Exolon/Resources/Info.plist` | `CFBundleDevelopmentRegion = $(DEVELOPMENT_LANGUAGE)` (`:5-6`); `CFBundleLocalizations` **отсутствует**; `DEVELOPMENT_LANGUAGE` не определена в pbxproj → подстановка даёт пустое значение |
| AppKit-меню | `NSMenu`/`mainMenu`/`applicationMenu` — 0 совпадений; `applicationDidFinishLaunching` (`Exolon/Platform/macOS/AppDelegate.swift:8-35`) меню не создаёт, `Info.plist` не ссылается на `NSMainNibFile` |
| Строки в `.tmx` | текст-свойств для игрока нет (`nextLevel`, `zoneNumber`, `background_color`, `source*` — только машинные); то есть данные уровней **не** держат переводимого текста |

Стоимость добавления i18n для этого набора (оценка по реестру выше, не «примерно»):

- **64 ключа** для покрытия всех видимых шаблонов — либо **72**, если разворачивать
  ON/OFF-варианты (#21/#22) и семь состояний (#55) в отдельные строки; переводчику
  обычно нужны именно 72. Девять crash-only позиций (№56–№64) разумнее оставить в
  `errorDescription`, но и они требуют 9 ключей, если нужен локализованный отчёт о
  падении;
- **14 из 64** содержат плейсхолдер или интерполяцию; **4** из них — «подпись + число» одним шаблоном
  (`CONTINUE · ZONE %03d` `GameScene.swift:902`, `HIGH SCORE %06d` `:732`/`:906`,
  `SCORE %06d` `:731`/`:746`, `ZONE %03d` `:753`) и требуют позиционных
  спецификаторов (`%1$@`) при смене порядка слов;
- **7 строк** (#55) сейчас вообще не являются текстом — это `rawValue` enum'а,
  пропущенный через `.uppercased()` (`Exolon/GameCore/GameState.swift:4-10` →
  `GameScene.swift:1072`). Для перевода их надо сначала превратить в display-строки,
  иначе русская локаль покажет `PLAYERDEAD`/`CONTENTCOMPLETE` латиницей;
- 26 литералов имени шрифта (`Menlo`/`Menlo-Bold`) и 20 кеглей придётся вынести в
  константы: Menlo не покрывает кириллицу «в оригинальном стиле», а для RU-локали
  метрики колонок `HUDNode.swift:27-31` (жёсткие `x = 48/145/266/382/470`) придётся
  пересчитывать — `GRENADES`/`POINTS` при переводе удлиняются, а `SKLabelNode` не
  умеет ни truncate, ни перенос (в дереве 0 `lineBreakMode`/`numberOfLines`), так что
  рассинхрон колонок станет виден сразу;
- отдельно: без MainMenu нет ни локализованного About, ни `Cmd+Q`, ни стандартного
  меню «Services» — это не переводческая, но обязательная сопутствующая работа
  (0 `NSMenu` в дереве, см. выше);
- фикстуры для проверки переводов отсутствуют: в репозитории нет ни одного тест-таргета
  (`PBXNativeTarget` ровно один — `Exolon`, `Exolon.xcodeproj/project.pbxproj:1029-1042`),
  так что ловить регрессии текста будет нечем.


### Отдельный риск: переводимость не-ASCII глифов

Текст в игре только ASCII-совместимый по алфавиту, но не по глифам: 5 не-ASCII
символов (см. таблицу дублей) несут смысл (`□` = кнопка, `↑/↓` = направление,
`—`/`·` = разделители). При добавлении локали они окажутся внутри переводимых
шаблонов, где их нельзя ни переписать, ни переставить — типичный повод вынести их в
отдельные ключи/атрибуты. Отдельно: `HUDNode.swift:27-31` использует жёсткие `x`
(48/145/266/382/470) при `horizontalAlignmentMode = .center`, поэтому любой перевод
длиннее оригинала съезжает к соседней колонке, а не обрезается.

---

## Надписи, которые врут

Каждый пункт: строка-лейбл → строка кода, которая ей противоречит.

### B1 (высокая) — `CONTINUE · ZONE %03d` обещает загрузку чекпойнта, которого не существует
- Лейбл: `Exolon/GameCore/GameScene.swift:902`, выбор ветки по `hasSavedCheckpoint` — `:901`.
- Противоречие: `Exolon/GameCore/GameScene.swift:690` (`persistence.clearCheckpoint()`) и
  `:691` (`hasSavedCheckpoint = false`) выполняются в `loadPersistentState()` **до** первого
  `updateTitleOverlayText()` (`:118`), то есть на каждом холодном старте показывается
  `NEW GAME · ZONE 000` (`:903`) независимо от того, что в UserDefaults лежит полный
  чекпойнт уровня/патронов/гранат/очков/жизней (`:696-706`).
- Утяжеляющее доказательство: `GamePersistence.loadCheckpoint()`
  (`Exolon/GameCore/GameState.swift:40-51`) не вызывается ниоткуда — `grep -rn
  loadCheckpoint Exolon --include=*.swift` даёт ровно одно совпадение, само объявление.
  Шесть ключей `Exolon.Step10.LevelName/Ammo/Grenades/Points/Lives/HasCheckpoint`
  (`GameState.swift:25-30`) пишутся на каждом переходе через `saveCheckpoint()`
  (`GameScene.swift:696-706`, вызовы в `:335`, `:657`, `:716`, `:740`, `:985`)
  и удаляются (`:690`, `:722`, `:951`) — **никогда не читаются**.
- Итог: строка `CONTINUE` физически может появиться только на переходе
  «концовка → заставка» (`:761-767`), где продолжение работает на in-memory-состоянии, а
  не на чекпойнте. Для нормального прохождения (`GAME OVER → RESTART`, `:733`, `:950`)
  заставка вообще не показывается (`:719-736`), так что за весь обычный цикл игры
  `CONTINUE` не виден ни разу.
- Примечание о честности автора: политика задокументирована в комментарии
  `GameScene.swift:686-688` и в `README.md:15`, но **нигде не отражена в самом тексте
  UI** — игрок читает слово, означающее загрузку сохранения.

### B2 (высокая) — `STEP 10` на заставке против `STEP 9` на остальных поверхностях
- Лейбл: `Exolon/GameCore/GameScene.swift:832`.
- Противоречие: `Exolon/GameCore/GameScene.swift:67` (`STEP 9 · ALL 125 ORIGINAL ZONES`),
  `:656` и `:984` (`STEP 9 · …`), `Exolon/Platform/macOS/AppDelegate.swift:16`
  (`Exolon Remake — Step 9 Rebase`), `README.md:1`. Одновременно
  `Exolon/GameCore/GameState.swift:25-31` хранит данные под `Exolon.Step10.*`.
- Итог: игрок, сверяющий заставку с заголовком собственного окна, видит два разных
  номера одной вехи; номер на заставке не совпадает ни с одной другой строкой в реестре.

### B3 (средняя) — `ALL 125 ORIGINAL ZONES` обещает проверенность, которую репозиторий сам отрицает
- Лейбл: `Exolon/GameCore/GameScene.swift:67`; парная концовка
  `Exolon/GameCore/GameScene.swift:747` (`ALL 125 ZONES COMPLETE`).
- Что подтвердилось: 125 `.tmx` физически присутствуют (`Exolon/Resources/`), все 125
  состоят в `Exolon.xcodeproj/project.pbxproj` как ресурсы (0 отсутствующих, 0 лишних),
  124 из 125 связаны `nextLevel` и **все** 124 цели лежат внутри
  `includedLevels` (`GameScene.swift:53`), `L05S25` (зона 124) без `nextLevel` →
  `FULL COMBAT ABILITY` (`:745`) достижим. Число «125» в тексте не врёт.
- Что врёт: квалификатор `ORIGINAL`/полнота механик. `README.md:17` прямо заявляет, что
  архив — «runnable checkpoint…, not the claim that every late-zone action is already
  audited». Соседний комментарий `GameScene.swift:624-625` утверждает, что бонус на
  границах стадий «deliberately dormant, until later steps add Zones 024/049/074/099/124»,
  хотя `guard [24, 49, 74, 99, 124].contains(completedZone)` (`:626`) срабатывает уже на
  существующем контенте (зона 24 = `L01S25`, 49 = `L02S25`, 74 = `L03S25`, 99 = `L04S25`
  по выводу `:988-996`; из пяти границ недостижима только последняя), то есть
  «original»-награда `lives * 1_000` + жизнь (`:627-628`) активна сегодня. Подпись
  «STEP 9 · ALL 125 ORIGINAL ZONES» подаёт как завершённое то, что собственные документы
  дерева объявляют незавершённым.

### B4 (средняя) — четыре строки концовки, которые игрок не увидит никогда
- Лейблы: `Exolon/GameCore/GameScene.swift:742` (`NEXT ZONE`), `:752`
  (`CONTENT COMPLETE`), `:753` (`ZONE %03d`), `:754` (`CONTINUES WITH %@`).
- Противоречие: они рендерятся только из `else`-ветки `:750-756`, куда попадают при
  `nextLevelName` непустом и вне `includedLevels` (`:614-617`). Замер по 125 `.tmx`: ровно
  один файл без `nextLevel` (L05S25), 124 ненулевых значения — все вида `L0[1-5]S(01..25)`,
  то есть внутри `includedLevels`. Значит `else` не выполняется, а `NEXT ZONE`
  (`:742`) мёртв вдвойне: в `enterContentComplete` (`:738-757`) он выбирается только при
  пустом имени, а пустое имя одновременно включает ветку `:743-749`.
- Итог: подтекст `CONTINUES WITH <id>` описывает продолжение контентом, которого в
  поставке нет, и существует только как невыполняемый код.

### B5 (средняя) — `HIGH SCORE` на GAME OVER не является «лучшим результатом до этой игры»
- Лейбл: `Exolon/GameCore/GameScene.swift:732` рядом со `:731` (`SCORE %06d`).
- Противоречие: `awardPoints()` (`:660-667`) поднимает `highScore` и пишет его в
  UserDefaults на **каждом** начислении (`:663-665`), поэтому к моменту `enterGameOver()`
  (`:719-736`) условие `:724` уже никогда не истинно — блок `:725-726` мёртв. На экране
  `GAME OVER` обе строки печатают одно и то же число ровно тогда, когда игрок поставил
  рекорд (и `SCORE ≤ HIGH SCORE` всегда). Слово `HIGH` в тирминале отделено от
  `SCORE`, но не несёт новой информации; на заставке (`:906`) оно осмысленно.
- Соседний риск: `loadHighScore()` (`Exolon/GameCore/GameState.swift:71-72`) не ограничивает
  значение, тогда как `points` зажат `min(999_999, …)` (`GameScene.swift:662`) — при
  значении из UserDefaults >999999 `HIGH SCORE %06d` перестанет быть 6-значным (см.
  раздел HUD: по ширине это безопасно, по формату — уже нет).

### B6 (средняя) — `↑ / ↓ D-PAD — SELECT` обещает направленную навигацию, которой нет
- Лейбл: `Exolon/GameCore/GameScene.swift:805`.
- Противоречие: `Exolon/GameCore/GameScene.swift:176` —
  `pauseSelectedIndex = pauseSelectedIndex == 0 ? 1 : 0`. Обе клавиши (`menuUp` и
  `menuDown`, `:170-173`) делают один и тот же toggle; направление не используется.
  Кроме того, выбор доступен не только с D-pad: стик тоже пишет `menuUp`/`menuDown`
  (`Exolon/Platform/macOS/GamepadInput.swift:70-71`, блок `:64-72`), о чём подпись не говорит.
- Сегодня безвредно (2 пункта), но подпись станет ложью в момент добавления третьего.

### B7 (средняя) — `RESTART` оставляет включённым TEST MODE
- Лейбл: `Exolon/GameCore/GameScene.swift:816` (`> RESTART <`), hint
  `:733` (`SPACE / □ — RESTART`).
- Противоречие: `restartFromBeginning()` (`:950-986`) сбрасывает уровень (`:956`),
  состояние (`:960`), экзоскелет (`:963`, что честно совпадает с `README.md:14`),
  неуязвимость-таймер (`:966`) и чекпойнт (`:951`), но **не** трогает
  `testInvulnerabilityEnabled` (`:45`, выставляется в `:186`) и **не** трогает
  `showHitboxes` (`:43`, `:223`). Значит после «RESTART» новый цикл стартует с горящим бейджем
  `TEST MODE · INVULNERABILITY` (`:106`) и, если был включён F1, с перекрытой отладочной
  полосой. Отдельно: тот же `RESTART` из паузы (`:186`) не вызывает
  `updatePauseMenuText()`, поэтому пункт меню сохраняет прошлый вид до следующей паузы.

### B8 (низкая) — `ZONES` под значением «текущая зона»
- Лейбл: `Exolon/GameCore/HUDNode.swift:31` (мн. число), значение — `:62`
  (`%03d` одного индекса 0..124, `GameScene.swift:116`, `:641`).
- Формально это не ложь, а неоднозначность: единственный заголовок HUD,
  который игрок не может разобрать без допущения. Рядом `NEW GAME · ZONE 000`
  (`GameScene.swift:903`) жёстко зашивает `000` литералом вместо `%03d` из `:902`, то есть
  «зона» в тексте имеет два независимых способа записи.

### B9 (низкая) — `PLAYERDEAD` / `CONTENTCOMPLETE` как пользовательский текст
- Лейбл-источник: `Exolon/GameCore/GameState.swift:7` и `:10` (`case playerDead`,
  `case contentComplete`) печатаются через `.uppercased()` в
  `Exolon/GameCore/GameScene.swift:1072`.
- Итог: в отладочной строке `… · STATE: PLAYERDEAD`/`CONTENTCOMPLETE` — идентификатор
  Swift вместо человеческой фразы; те же значения при этом читаются в тирминале как
  `GAME OVER` (`:730`) и `CONTENT COMPLETE` (`:752`). Одно состояние — два несводимых
  написания.

### Проверенные и ЧЕСТНЫЕ подписи (чтобы не перепроверять)
- `P / OPTIONS — RESUME` (`GameScene.swift:807`) ↔ `Exolon/Platform/macOS/GameView.swift:64`
  (keyCode 35 = P) и `Exolon/Platform/macOS/GamepadInput.swift:87-91`
  (`controllerPausedHandler` → `.pause`); переключение симметрично
  (`GameScene.swift:152-158`).
- `SPACE / □ — START|ACTIVATE|RESTART|TITLE` (`:852`, `:806`, `:733`, `:748`, `:755`) ↔
  `GameView.swift:60` (Space = keyCode 49 → `.fire`) и `GamepadInput.swift:80-81`
  (`buttonX` = Square → `.fire`); все четыре обработчика читают `.fire`
  (`:162`, `:180`, `:194`, `:202`).
- `INVULNERABILITY: ON` (`:819-822`) ↔ `GameScene.swift:601-602`
  (`guard !testInvulnerabilityEnabled else { return }` в `hitPlayer()`); все ветки урона
  (`:509-513`, `:538-599`) проходят через `hitPlayer()`, минуя его нельзя умереть —
  то есть бейдж `TEST MODE` (`:106`) соответствует флагу.
- `EXOSKELETON ON/OFF` (`:237`) ↔ `player.toggleExoskeleton()` (`:235`), второй ствол
  `:346-350`, иммунитет к минам/поршням `:546`, `:557`.
- `+1000` (`:302`) ↔ `return 1_000` (`Exolon/GameCore/Levels/TMXLevelRuntime.swift:221`) и
  `ORIGINAL_MECHANICS.md:48` («awards 1000 points once»).
- Счётчик `ALL 125 ZONES COMPLETE` и `SCORE %06d` — см. B3/B5 (число зон честно,
  квалификатор и семантика рекорда — нет).

---

## Что проверить на macOS

1. **Заставка:** совпадает ли `STEP 10` (`GameScene.swift:832`) с заголовком окна
   (`AppDelegate.swift:16`) и ожиданием владельца; после правки — какой из пяти
   источников (см. B2) признается каноническим.
2. **Холодный старт после игры в зоне != 000:** убедиться, что заставка показывает
   `NEW GAME · ZONE 000`, хотя `defaults read com.exolon.remake` содержит
   `Exolon.Step10.LevelName`/`Points` — это и есть материализация B1.
3. **Глифы Menlo:** отрисовка `□` (U+25A1), `↑`/`↓` (U+2191/2193), `·` (U+00B7),
   `—` (U+2014) в `GameScene.swift:733`, `:748`, `:755`, `:805`, `:806`, `:852`, `:1071` —
   нет ли tofu/фолбэка на другую гарнитуру (проверить в 12 pt и в минимальных 5.5 pt).
4. **F1-полоса в бою:** включить отладку (F1, `GameView.swift:66`) и проверить
   нахлёст `inputLabel` (левый `x=8`, правый ~229.8 при полной длине) и `stepLabel`
   (левый край ~190.7–201.2) на одной базовой `y=370` — ожидание: перекрытие
   28.6–39.2 логических пикселя; одновременно проверить читаемость поверх арт-полосы
   (все `.tmx` = 560×384 px, image-слой 512×384) при минимальном окне 640×480
   ( Effective кегль 5.5 → ~6.9 pt).
5. **TEST MODE:** включить `INVULNERABILITY` в паузе, выйти в `RESTART` и убедиться, что
   бейдж `TEST MODE · INVULNERABILITY` (`:106`) пережил рестарт (B7); отдельно — что
   F1-полоса тоже не сбрасывается.
6. **Пауза поверх баннера:** вызвать `EXOSKELETON ON`/`+1000` и сразу нажать P —
   `.wait(forDuration:)` внутри `bannerLabel.run(...)` (`:669-681`) стоит на ноде,
   попадающей в `setGameplayNodesPaused(true)` (`:944-948`); ожидать «застывший» баннер
   под затемнением и его доигрывание после resume.
7. **GAME OVER при рекорде:** убедиться, что `SCORE %06d` и `HIGH SCORE %06d`
   (`:731`/`:732`) печатают одно число (B5), и что после Quit→Launch заставка
   (`:906`) показывает сохранённый рекорд.
8. **HUD при крайних значениях:** `AMMO 99` / `GRENADES 10` / `POINTS 999999` /
   `LIVES 9` / `ZONES 124` — замеры выше обещают отсутствие коллизий (широкая пара
   `POINTS`-заголовок/значение: 246.1..285.9 против 244.3..287.7 на разных `y`),
   проверить визуально и убедиться, что нижняя панель 48 px (`GameConstants.swift:33`,
   `HUDNode.swift:14-20`) не съедает полезную картинку: замер по всем 125 `.tmx` дал 0
   не-`collision` тайлов в нижних трёх строках (y<48), так что скрытым оказывается
   только нижние 48 px слоя `Original Static Scenery`.
9. **3-значные жизни / 7-значные очки:** специально проверить, что они структурно
   невозможны (`GameScene.swift:628` ограничивает жизни сверху `startingLives = 9`,
   `:662` — очки сверху 999999), и что единственный реальный путь к расширению формата —
   вручную прописанное `Exolon.Step10.HighScore` (`GameState.swift:71-72`).
10. **Endgame-путь:** доиграть L05S25 до `x > 510` (`GameScene.swift:610`, зажим игрока на
    `logicalSize.width + 32` — `Player/Player.swift:128`) и подтвердить, что показывается
    `FULL COMBAT ABILITY` / `ALL 125 ZONES COMPLETE` (`:745`, `:747`), а ветка
    `CONTENT COMPLETE` (`:752`) не показывается нигде (B4).
11. **Локализация бандла:** после сборки проверить `plutil -extract CFBundleDevelopmentRegion
    raw Exolon.app/Contents/Info.plist` (ожидание: пустая строка из-за
    неопределённой `$(DEVELOPMENT_LANGUAGE)`) и наличие `Base` в
    `Contents/Resources/` при отсутствии `Base.lproj`.
12. **Меню-бар:** подтвердить, что без `NSMenu` (`grep` → 0) приложение не даёт ни
    Cmd+Q, ни About, ни пункта «Настройки», и что ни одна AppKit-строка не локализуется
    штатным путём.

---

Вердикт: fail
