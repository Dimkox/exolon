# Локальный бэклог аудита Exolon

> **⚠️ КОРРЕКЦИЯ 2026-09-20.** Авторитет: `engineering/reports/exolon-full-audit-20260920.md`.
> Строки **C1/C1b (P0) сняты**: финальный постройтовый замер L01S10 показал, что exclusion
> `minY-16` вырезает солидные клетки-«будку» (`y=128..208`) — по замыслу, — а пол (`y=64..96`,
> верх 96) остаётся нетронутым с запасом 16 px (граница исключения 112). Первичный аудит принял
> стены будки за пол. C1 → P3 robustness (4 маркерные кабины с 0-px запасом). Актуальный
> приоритетный список — в полном аудите (§7 бэклога v2).

Источник: `engineering/reports/exolon-initial-audit.md`  
Маршрут: `7db1f3f0b126`  
HEAD: `403eb1322d645154307ce11bf91be89e2082e1dd`  
Внешние тикеты **не** создавались.

Колонки: **defect** = против заявленного Step 9 / очевидный баг кода; **unfinished** = оригинал не доведён, README не обещает; **hypothesis** = нужен macOS; **packaging** = бандл/версии.

| Pri | ID | Тип | Заголовок | Где | macOS | Следующее действие |
| --- | --- | --- | --- | --- | --- | --- |
| P0 | C1 | defect + hypothesis play | Exclusion кабины вырезает пол (`minY-16`) | `TMXLevelRuntime.swift:297-306`, `L01S10.tmx` | Обязательно: стоять в кабине 009 | Play → если провал, `minY+16` / сохранить пол |
| P0 | C1b | hypothesis | Toggle костюма из-под кабины | те же | Вместе с C1 | Зафиксировать хитбоксы F1 |
| P1 | O8 | defect vs original | Бонус double launcher гасит пусковую | `LevelObstacles.swift:718-723` | Зона 006 | Отделить bonus region от `isActive` |
| P1 | O7 | defect vs original | `beam_up` и `beam_down` = два поля по 25 | `TMXLevelRuntime.swift:356-360`, `L02S11.tmx` | Считать хиты на 035 | Одно поле до no-walk |
| P1 | O1 | unfinished | 18 `blk_gunMachine_BOTTOM` без турели | в т.ч. `L01S24.tmx` зона 023 | Визуал + граната | Кейс в `buildObjectsFromTMX` |
| P1 | O5 | unfinished (код живой) | Stage bonus частичный, костюм не сброшен, комментарий «dormant» лжет | `GameScene.swift:622-631` | 024 с/без костюма | Полная последовательность или честный флаг |
| P1 | M1 | — | Нет `xcodebuild` / геймплея на Linux | хост | Сборка Debug | Не закрывать P0 без этого |
| P2 | C5 | defect UX | Стик UP не jump/cabin/teleport | `GamepadInput.swift:71` | Стик в 002/009 | Решение: стик→`.jump` или документ |
| P2 | I1 | hypothesis | Pause/Options через `controllerPausedHandler` | `GamepadInput.swift:87-91` | DualShock/Xbox | `buttonMenu` при необходимости |
| P2 | F1 | defect flow | После 124 title не new game | `GameScene.swift:708-717,761-767` | 124→SPACE→SPACE | Reset как Restart |
| P2 | O2 | unfinished | Ракетные башни не стреляют | `TMXLevelRuntime.swift:264-269` | — | Отдельный step |
| P2 | O4 | unfinished | Swing bubbles ≠ `tab_enemy` | `BubbleSpawner` | 003 | Порт 6 таблиц |
| P2 | O3 | unfinished | Факелы, HV, timed pursuer | нет рантайма | — | Каталог маркеров |
| P2 | O6 | remake deviation | Смерть не rebuild зоны | `GameScene.swift:328-329` | — | Оставить или порт rebuild |
| P2 | O9 | unfinished | waggon/mushroom не destroyable | 33 `source_marker` | — | Таблица destroyable из ASM |
| P2 | T1 | hypothesis | Legacy телепорты без w/h | `L01S03.tmx`, `L01S07.tmx` | 002 | Сверить ноги |
| P3 | V1 | packaging | MARKETING_VERSION 0.5 vs plist 0.3 | pbxproj, `Info.plist` | `mdls` / About | Выбрать одну версию |
| P3 | V2 | packaging | Title «STEP 10», окно «Step 9» | `GameScene.swift:832`, `AppDelegate.swift:16` | визуал | Согласовать ярлык |
| P3 | V3 | packaging | 5 ресурсов вне pbx Resources | gif/png в §4.2 отчёта | сборка | Включить или удалить из git-ожиданий |
| P3 | O10 | unfinished visual | Нет кадров exo, cyan tint | `PlayerSpriteNode.swift:43-46` | — | Второй шит |
| P3 | T2 | packaging | Нет `.xcscheme` | `Exolon.xcodeproj` | Xcode | Shared scheme |
| P3 | T3 | test gap | Нет XCTest у игры | pbx | — | Characterization после macOS |

## Не делать в этом бэклоге

- Не считать factory `grok_verify` сборкой Swift.
- Не публиковать GitHub issues (запрет маршрута).
- Не править продукт, пока C1 не подтверждён playtest (кроме отдельного явно заказанного фикса).
- Не смешивать недоделки оригинала с регрессиями ZIP.

## Минимальный следующий прогон на macOS

1. `xcodebuild -project Exolon.xcodeproj -target Exolon -configuration Debug build`  
2. Сценарий C1 зоны 009.  
3. Зоны 002, 006, 008, 023, 024, 035.  
4. Стик UP vs D-pad UP.  
5. Записать фактический CFBundleShortVersionString.
