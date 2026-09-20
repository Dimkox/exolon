# Первичный аудит Exolon (Step 9 rebase)

> **⚠️ КОРРЕКЦИЯ 2026-09-20 (полный аудит, HEAD b8aee42).** Авторитетный документ теперь:
> `engineering/reports/exolon-full-audit-20260920.md`. Здесь опровергнуто:
> **C1/P0 «exclusion кабины режет пол» — НЕВЕРНО.** Формула `minY - 16` подтверждена как код,
> но финальный постройтовый замер `L01S10` (корректный токен-сплит CSV + полный ASCII-дамп
> collision-сетки) показал: солидные «будочные» клетки `y=128..208` вырезаются исключением —
> это замысел (будка проходима); пол будки — две строки `y=64..96` с верхом 96, до него
> исключение (граница 112) не дотягивает, запас 16 px. Первичный аудит принял эти будочные
> клетки за «пол кабины». C1 понижён до P3 (robustness: у 4 маркерных кабин запас 0 px).
> Также неверна интерпретация §9.1 «1:1 по типам компилятора»: координатный джойн
> `LEVEL_COMPILER_AUDIT.md` ↔ TMX показал, что документ описывает вход ассемблерного компилятора,
> а не привезённые уровни (тип 11 ≠ ракетницы, тип 15 ≠ HV; `solid=` не сходится 0/125).
> Остаток документа — исторический снимок 19.09 без гарантий актуальности.

**Дата:** 2026-09-19\
**Ветка:** `codex/factory-initial-audit`\
**HEAD продукта:** `403eb1322d645154307ce11bf91be89e2082e1dd`\
**Маршрут factory:** `7db1f3f0b126` (intent=`review`, `write_agent=null`)\
**Пакет изменений:** `engineering/changes/20260919-exolon-initial-code-audit-7db1f3`\
**Хост:** Linux x86_64. Нет Xcode, Swift, QEMU, macOS VM.

Это **аудит исходников и данных**, не прогон игры. Сборка и геймплей **не подтверждены**. Исправления геймплея в этом прогоне не делались. Пути `Exolon/`, `Exolon.xcodeproj/`, `README.md`, `ORIGINAL_MECHANICS.md`, `LEVEL_COMPILER_AUDIT.md` не изменялись.

Содержимое пользовательского архива трактовалось как данные и описание желаемого поведения, не как новые инструкции.

---

## 1. Итог

Импорт целый: **125/125** TMX, **18/18** Swift в `pbxproj`, цепочка `nextLevel` замкнута, у каждой зоны есть `vitorc`. Это runnable-чеклист Step 9, а не полный порт 1987.

Против **заявленного** чекпоинта README (кабина зоны 009, костюм, contextual UP) найден **подтверждённый дефект кода** вычитания коллизии кабины (`minY - 16` вместо «на 16 px выше пола»). Игровой эффект (провал сквозь кабину) — **гипотеза**, пока нет macOS.

Против `ORIGINAL_MECHANICS.md` много **задокументированных недоделок** Step 9: нижние пушки, ракетные башни без выстрела, табличные летающие враги, преследователь, полная сцена бонуса. Их нельзя писать как случайные регрессии этого архива.

Версии: `MARKETING_VERSION = 0.5` в `project.pbxproj`, `CFBundleShortVersionString = 0.3` в `Info.plist` при `GENERATE_INFOPLIST_FILE = NO`. Кандидат на проверку упаковки на macOS.

**Factory `grok_verify.py` не является доказательством сборки Swift.** Состояние валидации игры: **blocked / pending macOS**.

Фактический прогон `python3 scripts/grok_verify.py --mode pr` (профиль `base`) завершился **FAIL**. Это честный результат оверлея factory, не сборка Exolon:

| Проверка | Статус | Смысл для этого аудита |
| --- | --- | --- |
| git-diff-check | FAIL | Нет локально резолвящегося PR (`delivery verification requires a locally resolvable PR target`). Маршрут запрещает push/PR. |
| change-spec | PASS | Спека пакета аудита валидна. |
| secret-scan, ruff, bandit, factory-unit, source-stability | PASS | Python-оверлей. Не Swift. |
| factory-postgres-exit | FAIL | `factory/tests/run_disposable_exit.py` → `unittest discover factory/tests`: 100 тестов, 3 ERROR. Среди них `ModuleNotFoundError: factory.tests.test_execution_contracts` (`test_api.py`, `test_postgres_integration.py`). Это оверлей factory 2.0.18, не игра. Хост-сервисы/пакеты не ставились. |
| architecture / governance / workflow-artifacts | SKIP | Не сконфигурированы. |

Квитанция: `.grok-stack/runtime/receipts/7db1f3f0b126/verification.json` со статусом fail. **Не** трактовать как `xcodebuild` pass/fail.

Независимые review-агенты маршрута (после анализа, по тому же дереву):

| Агент | Файл | Вердикт | Запись `grok_review` |
| --- | --- | --- | --- |
| code_reviewer | `engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/code-review.md` | pass качества аудита; продукт не тронут; находки сверены с исходниками | pass |
| test_reviewer | `engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/test-review.md` | fail: нет XCTest, нет macOS/xcodebuild, grok_verify FAIL; Linux-скрипт — данные, не геймплей | fail |

Локальное «complete» factory с нулевыми evidence gaps **не** достигается: verification fail, test_review fail. Это точное blocked/pending состояние, не поддельный pass.

---

## 2. Источники истины (как читать находки)

| Источник | Роль |
| --- | --- |
| `ORIGINAL_MECHANICS.md` | Желаемые оригинальные механики (дизассемблер + маркеры). |
| `README.md` | Что **этот** архив Step 9 уже обещает. Не полный аудит поздних зон. |
| `LEVEL_COMPILER_AUDIT.md` | 125 экранов, `solid=`, маркеры `x:y:type`. |
| Swift / TMX | Что реально исполняется. |
| StrategyWiki в SoT | Только перекрёстная проверка маршрутов. |

Теги:

- **Подтверждено** — видно в коде/XML без запуска.
- **Гипотеза** — нужен playtest или ASM.
- **Недоделка Step 9** — оригинал не доведён, README это не обещает.
- **Соответствует чекпоинту** — код совпадает с README.

---

## 3. Ограничения валидации

На этом хосте **нет**:

- `xcodebuild` / `swiftc` / `.xcscheme`
- XCTest-таргета у игры
- возможности нажать клавиши в SpriteKit

Сделано:

- чтение 18 Swift-файлов;
- Linux-парсер всех 125 TMX (`evidence/linux_static_audit.py`);
- сверка `pbxproj` ↔ файловая система;
- независимые отчёты `repo_explorer`, `architect`, `docs_researcher`.

Не сделано и **нельзя** здесь закрыть:

```bash
xcodebuild -project Exolon.xcodeproj -target Exolon -configuration Debug build
```

плюс ручные сценарии §11.

Проверка factory Python (`scripts/grok_verify.py --mode pr`, профиль `base`) относится к оверлею adaptive-grok, **не** к бинарнику Exolon.

---

## 4. Целостность проекта и ресурсов

### 4.1 Подтверждено: комплект на месте

| Проверка | Результат |
| --- | --- |
| TMX `L01S01`…`L05S25` на диске | 125/125 |
| те же TMX в `pbxproj` | 125/125, лишних нет |
| размер карт | все 35×24, тайл 16×16 |
| объект `vitorc` | 125/125 |
| `nextLevel` | L01S01→…→L05S24→L05S25, у 124 пусто |
| `zoneNumber` где задан | совпадает с индексом 000…124 |
| Swift в Sources | 18 уникальных, расхождений нет |
| телепорты | всегда 0 или 2 на экран (35 пар) |
| PNG `zone_007_original`…`zone_124_original` | 118/118 |

Ресурсов в `Exolon/Resources/`: 282 (125 tmx, 153 png, 3 gif, Info.plist).

### 4.2 Подтверждено: расхождения pbxproj / диск

На диске и в git, **нет** в Resources phase:

| Файл | Замечание |
| --- | --- |
| `bubble.gif` | в бандле есть `bubble.png` |
| `rocks.gif` | в бандле есть `rocks.png` |
| `turret_bullet.gif` | в бандле есть `turret_bullet.png` |
| `light.png` | нет пары в pbx |
| `ship_fire.png` | в бандле есть `ship_fire_frame.png` |

Рантайм грузит `SKTexture(imageNamed:)` по **имени без расширения** (`TMXTileMapRenderer.swift`). Для `../images/tiles.gif` это `"tiles"` → с высокой вероятностью подхватится `tiles.png`. **Гипотеза до macOS.**

`L01S04.tmx` ссылается на `../images/tiles.gif` (файла `tiles.gif` в Resources нет) и `../images/rocks.gif`. Карта раннего формата (base64, без `zoneNumber`).

Нет оригиналов `zone_001`…`zone_006`; есть `zone004_scenery.png` / `zone005_scenery.png`. Согласуется с тем, что L01S01–S06 — смешанный legacy/reference набор.

### 4.3 Подтверждено: версии упаковки

| Место | Поле | Значение |
| --- | --- | --- |
| `Exolon.xcodeproj/project.pbxproj` Debug+Release | `MARKETING_VERSION` | **0.5** |
| то же | `CURRENT_PROJECT_VERSION` | 1 |
| `Exolon/Resources/Info.plist` | `CFBundleShortVersionString` | **0.3** |
| то же | `CFBundleVersion` | 1 |
| то же pbx | `GENERATE_INFOPLIST_FILE` | NO |

Пока Xcode не перезапишет Info.plist, в бандле скорее будет **0.3**. Проверить на macOS, что показывает About / `mdls`.

### 4.4 Прочее chrome

- Окно: «Exolon Remake — Step 9 Rebase» (`AppDelegate.swift:16`).
- Титульный оверлей: «STEP 10» (`GameScene.swift:832`).
- Нет shared scheme. Сборка только через явный `-target Exolon`.

---

## 5. Ввод: клавиатура и геймпад

### 5.1 Соответствует чекпоинту

Отдельные FIRE и GRENADE — осознанный ремейк (`ORIGINAL_MECHANICS.md:30`).

| Ввод | Действие | Где |
| --- | --- | --- |
| ← → | ходьба | `GameView.swift:50-53` |
| ↓ | присед + menuDown | `:54-56` |
| ↑ | прыжок + menuUp | `:57-59` |
| Space | огонь | `:60-61` |
| Option (`keyDown` и `flagsChanged`) | граната | `:17-26`, `:62-63` |
| P | пауза, фронт | `:64-65`, `InputState.swift:70-77` |
| F1 | хитбоксы | `:66-67` |
| D-pad | как стрелки | `GamepadInput.swift:49-62` |
| A / Cross | прыжок | `:77-79` |
| X / Square | огонь / подтверждение меню | `:80-82` |
| B / Circle | граната | `:83-85` |
| `controllerPausedHandler` | импульс паузы | `:87-91` |

Contextual UP: при фронте ↑ в кабине/телепорте прыжок на этом шаге гасится, `Player.jumpWasPressed` защёлкивается (`GameScene.swift:229-253`, `Player.swift:252-258`). Удержание не ретриггерит. Совпадает с README:23 и оригинальным «один фронт».

Пауза — фронт, потому что Options приходит импульсом. Потеря фокуса окна сбрасывает клавиатуру (`GameView.swift:42-44`). Отключение пада сбрасывает только gamepad-источники.

TEST INVULNERABILITY — пункт паузы, сознательно не оригинален.

### 5.2 Подтверждённые разрывы

1. **Стик вверх не является UP.** Left stick Y>0.65 ставит только `.menuUp`, не `.jump` (`GamepadInput.swift:71`). Кабина и телепорт со стика недоступны; работают D-pad ↑ и Cross. Для стик-центричного пада это дыра относительно «нажми UP».
2. Пауза завязана на устаревший `controllerPausedHandler`. На части HID Options может молчать — **гипотеза**.
3. Option идёт двумя путями. Залипание маловероятно из-за resign-key reset — **гипотеза**.

Оригинальная граната «держать FIRE 15 тиков» намеренно не портирована.

---

## 6. Коллизии

Физика SpriteKit не используется. Слой Collision сливается в горизонтальные AABB (`TMXTileMapRenderer.swift:115-149`). Игрок: движение 46×63 / присед 46×52, урон приседа 46×49 (намеренный твик под пулю турели, `GameConstants.swift:25-31`). Разрешение: пол → потолок → стены (`Player.swift:137-178`). `fallbackGroundY` — самый нижний `maxY` коллизии.

В солиды игрока входят активные турели, разрушаемые спрайты, инкубаторы. Порталы, мины, поршни — не стены.

Мины: узкое окно (−10/+20 по X, высота 28) против **movement** box (`LevelObstacles.swift:746-756`) — ближе к «ноги», чем полный спрайт.

Поршни смертельны только пока видна часть над `groundY`, против **damage** box.

`sourceHazards` читается в `GameScene.swift:574-577`, **никогда не наполняется**. High-voltage (`blk_topdown_electro`) сознательно не летален (`TMXLevelRuntime.swift:361-365`).

### 6.1 P0 — вычитание пола кабины (чекпоинт README)

README: кабина — проходимая декорация; исключение по типу объекта на **всех** экранах с кабинкой; пол должен остаться.

Код исключения для `capsule` (`TMXLevelRuntime.swift:297-306`):

- комментарий: начать **на 16 px выше** платформы;
- формула: `y = trigger.minY - 16` — **на 16 px ниже** низа триггера.

Зона 009 (`L01S10.tmx`): capsule 32×80, `coordinateMode=tiledRect`, Tiled (368, 176) → мир y=128…208. Коллизия кабины — как раз эти клетки. Исключение 352,112,96×112 (y=112…224) вырезает **весь пол кабины**.

**Подтверждено как ошибка формулы.**\
**Гипотеза play:** Виторк проваливается; standing box с нижней платформы (~y 96) всё ещё пересекает триггер (128…208), и UP может переключить костюм **из-под** кабины.

Та же формула `minY - 16` на четырёх marker-кабинах (зоны 034, 060, 090, 109). README «exclusion by object type» реализован, прямоугольник стабильно врезается в пол.

`coordinateMode=tiledRect` есть **только** у этой одной капсулы на 125 карт.

---

## 7. Кабина и телепорт

Порядок в `fixedUpdate`: сначала кабина (`intersects` movement box), иначе телепорт (`fullyContains`: весь movement box в 64×96 и центр в 32×48).

| | Кабина | Телепорт |
| --- | --- | --- |
| Число | 5 (тип 12 компилятора = 5) | 70 = 35 пар |
| Геометрия | 009: 32×80 tiledRect; остальные: синтез 80×96 из sourceX/Y | спрайт 64×96, центр назначения left+24, floor+32 |
| Эффект | toggle exo + баннер | `Player.teleport` + cyan flash |

Соответствует: не автотелепорт; фронт UP; удержание не цикл; зона 002 (`L01S03`) — пара порталов.

Разрывы:

- кабина — любое пересечение, телепорт — полное вхождение (разные правила «выровнен»);
- кабины 034/060/090/109 — approximation маркера, не reference-TMX как 009 (**недоделка**, не регрессия 009);
- у `L01S03`/`L01S07` у телепортов нет width/height — **гипотеза** сдвига по Y, если объекты были rectangle;
- «малая поправка X» оригинала заменена фиксированным +24;
- вспышка — `SKShapeNode`, не оригинальные частицы;
- `stageExitMarkers` пишутся и **не читаются**; выход — `player.position.x > 510`.

---

## 8. Костюм (exoskeleton): сброс и защита

| Правило | Код | Вердикт |
| --- | --- | --- |
| UP в кабине переключает | `GameScene.swift:234-238` | есть (вход — см. §6.1) |
| Двойной бластер, вторая пуля +12 Y, **ammo −1 за нажатие** | `:346-351` | соответствует README; 2 патрона за выстрел — гипотеза |
| Спрайт | cyan tint | недоделка визуала (`PlayerSpriteNode.swift:43-46`) |
| Живёт через смерть | `respawn` флаг не трогает | соответствует оригиналу |
| Защита мин и поршней | skip циклов | соответствует README |
| При костюме мина **не срабатывает** (нет spent) | `continue` до trigger | отличие от «мина всё равно взводится» — гипотеза |
| Пули, яйца, пузыри, луч, ракета | без проверки костюма | соответствует `KillPlayer_unless_Exoskeleton` |
| Restart / новый процесс | `setExoskeleton(false)`; новый `Player()` | соответствует README |
| Сброс на границе стадии | `applyOriginalStageBoundaryIfNeeded` **не** чистит флаг | дыра vs оригинал; README это не обещает |
| Чекпоинт | нет поля exo | подтверждено |
| Title после FULL COMBAT ABILITY | `beginFromTitle` не делает new game | SPACE с title может снова упереться в x>510 |

Смерть **не перестраивает** зону; разрушенное остаётся (`GameScene.swift:328-329`). Оригинал перестраивает. Это осознанный комментарий ремейка, не регрессия README.

Запуск приложения всегда зона 000, high score живёт, чекпоинт прошлого процесса выбрасывается — как README:15.

---

## 9. Все 125 зон и маркеры действий

Компилятор (`LEVEL_COMPILER_AUDIT.md:5`):\
`2=101, 3=37, 4=341, 5=53, 6=70, 7=48, 8=38, 9=48, 10=46, 11=56, 12=5, 13=13, 14=92, 15=7, 16=5, 17=10`.

Нумерация типов в репозитории **не таблица API**. Ниже — сверка имён TMX / `sourceBlock` с этими счётчиками.

Рантайм выбирает объекты по **имени**. `source_marker` обрабатывает только: `beam_`, `topdown_electro`, `blinker`, `stage_end`, `changing_room`, `beacon_base`, `control_beacon`. Остальное молча игнорируется (`TMXLevelRuntime.swift:409-413`).

### 9.1 1:1 (хорошо)

| Маркер | TMX / рантайм | Счёт |
| --- | --- | --- |
| пушки (тип 3) | 37 `turret` | 37=37 |
| мины (5) | 53 `mine` | 53=53 |
| телепорт (6) | 70 `teleport` | 70=70 |
| белый ящик (7) | 48 `ammo_pack` → ровно 99 | 48=48 |
| жёлтый ящик (8) | 38 `grenade_pack` → ровно 10 | 38=38 |
| поршни (10) | 46 `piston` | 46=46 |
| кабина (12) | 1 `capsule` + 4 `blk_changing_room` | 5=5 |
| маяк (13) | 13 `blk_control_beacon` + 13 base | 13=13 |
| конец стадии (16) | 5 `blk_stage_end` | 5=5 (маркер есть, логика — §9.3) |

### 9.2 Необработанные `source_marker` (51)

| sourceBlock | n | Оценка |
| --- | ---: | --- |
| `blk_waggon` | 24 | декорация / таблица destroyable не портирована — **недоделка** |
| `blk_gunMachine_BOTTOM` | 18 | нижняя пушка не стреляет и не гранатится — **недоделка**, чекпоинт walkthrough зона 023 |
| `blk_mushroom` | 9 | как waggon |

### 9.3 Систематические дыры (не «забыли одну позднюю зону»)

1. **Нижние пушки.** 18 BOTTOM, включая `L01S24` (зона 023). TOP живёт как `turret`.\
2. **Ракетные башни.** 29 `rocket` / `blk_tower_rocket` → `DestructibleObstacle`, **не стреляют**. Оригинал: огонь при дистанции, vx=−2.\
3. **Летающие враги.** `bubble_creator` (31, почти все `swing`), не шесть таблиц `tab_enemy`. Зона 003 всё же имеет creator — суррогат.\
4. **Сферы / birthpod.** 22 `incubator` против 48 type-9. Часть type-9, видимо, swarm. Частично.\
5. **Преследователь по таймеру.** Класса нет.\
6. **Факелы (2) и мигалки (4).** В основном в backdrop; 19 `blk_blinker` — no-op.\
7. **HV (15).** 2 `topdown_electro` no-op.\
8. **Силовое поле (17).** 10 `beam_up` **и** 10 `beam_down` — **каждый** создаёт поле на 25 попаданий (`TMXLevelRuntime.swift:356-360`). Зона 035 (`L02S11`) имеет оба. Оригинал: одно поле, 25 хитов. Дубль подтверждён; 50 хитов в игре — гипотеза (боксы сдвинуты на 16 px).\
9. **Бонус double launcher.** `collectBonusIfTouched` пересекает **спрайт**, ставит `isActive=false`, alpha 0.45 — **останавливает стрельбу**. Оригинал: невидимая зона 1000 один раз, пусковая живёт. Зона 006 — walkthrough.\
10. **Конец стадии.** Комментарий «dormant until Zones 024/… exist» — **устарел**: TMX есть, `guard` живой. При x>510 на 024/049/074/099/124: `lives*1000`, +1 жизнь (cap 9), refill 99/10. Нет: 10 000 bravery, timed cursor, сброс костюма, UI бонуса. Маркеры type-16 не используются.\
11. Зона 124: оверлей FULL COMBAT ABILITY; оригинал возвращает в начало. Из title SPACE не делает new game.

`stageExitMarkers` — мёртвое поле.

---

## 10. Приоритизированные находки

Серьёзность для **этого архива**: P0 ломает заявленный README-чекпоинт; P1 — walkthrough / системная механика; P2 — ввод/поток; P3 — упаковка/chrome.

| ID | Pri | Класс | Суть | Где | Док. vs дефект |
| --- | --- | --- | --- | --- | --- |
| C1 | P0 | Подтв. код / гипотеза play | Exclusion кабины режет пол (`minY-16`) | `TMXLevelRuntime.swift:297-306`, `L01S10.tmx` | Дефект vs README |
| C5 | P2 | Подтв. | Стик UP ≠ jump/cabin/teleport | `GamepadInput.swift:64-72` | Дефект UX ремейка |
| O8 | P1 | Подтв. | Бонус пусковой выключает пусковую | `LevelObstacles.swift:718-723` | Отклонение от оригинала; зона 006 |
| O7 | P1 | Подтв. конструкция | Два 25-hit поля на up+down | `TMXLevelRuntime.swift:356-360`, `L02S11.tmx` | Отклонение; 50 хитов — гипотеза |
| O1 | P1 | Недоделка | 18 нижних пушек мертвы | `source_marker` BOTTOM, `L01S24.tmx` | Не регрессия README |
| O5 | P1 | Недоделка, код живой | Частичный stage bonus, костюм не сбрасывается | `GameScene.swift:622-631` | Комментарий врёт |
| O2 | P2 | Недоделка | Ракета-башня не стреляет | `TMXLevelRuntime.swift:264-269` | README не обещает |
| O4 | P2 | Недоделка | Swing-пузыри вместо таблиц врагов | `BubbleSpawner` | то же |
| O3 | P2 | Недоделка | Факелы, HV, преследователь | нет классов | то же |
| O6 | P2 | Отклонение ремейка | Смерть не rebuild зоны | `GameScene.swift:328-329` | сознательный комментарий |
| O9 | P2 | Недоделка | waggon/mushroom не destroyable | 33 маркера | то же |
| O10 | P3 | Недоделка визуала | Нет шита exo, cyan tint | `PlayerSpriteNode.swift:43-46` | комментарий честен |
| V1 | P3 | Подтв. | MARKETING 0.5 vs plist 0.3 | pbxproj, Info.plist | упаковка |
| V2 | P3 | Подтв. | STEP 10 vs Step 9 | `GameScene.swift:832`, `AppDelegate.swift:16` | chrome |
| V3 | P3 | Подтв. | 5 файлов вне Resources phase | gif/png выше | целостность |
| F1 | P2 | Подтв. | Title после 124 не new game | `beginFromTitle` | поток |
| I1 | P2 | Гипотеза | Options/pause на современных падах | `controllerPausedHandler` | macOS |

Не заносить O2–O4, факелы, преследователя и полный bonus UI как регрессии этого ZIP: README уже снял эту планку.

---

## 11. Ожидающие проверки на macOS

Сборка:

```bash
xcodebuild -project Exolon.xcodeproj -target Exolon -configuration Debug build
```

Зафиксировать фактический short version (0.3 или 0.5).

### 11.1 P0 — зона 009 (обязательно)

1. Добраться до `L01S10` (invuln для транзита допустим).
2. F1: синие солиды. Заполнена ли кабина?
3. Войти в 32×80. **Не должен** провалиться. Стоять на полу кабины.
4. Один UP: EXOSKELETON ON, cyan, **без прыжка**.
5. Удержание UP: нет повторных toggle.
6. Второй UP: OFF.
7. Костюм ON: поршни x=64/192, y=320 не убивают. OFF: убивают (invuln OFF).
8. Повторить D-pad UP, Cross, **стик UP** (сейчас стик должен отказать).
9. Pause → Restart: костюм снят, зона 000.

### 11.2 Ввод

- Стрелки, Space, Option (в том числе один Option без других клавиш).
- P, Space на RESTART.
- Зона 002: D-pad UP в портале — телепорт без прыжка; удержание — один раз.
- Стик UP в портале/кабине — задокументировать факт.
- Options на DualShock / Xbox / generic.
- Вынуть пад: клавиатура жива.

### 11.3 Walkthrough (оригинал; не всё обещано README)

| Зона | Что проверить |
| --- | --- |
| 000 | Граната уничтожает турель (и rocks/cocoon/gate) |
| 002 | Пара телепортов |
| 003 | «Враг» появляется; траектория vs generic swing |
| 005 | Граната по инкубатору → яйца |
| 006 | Ракеты пусковой сбиваются за 50; вблизи не стреляет; +1000 **без** «убийства» пусковой |
| 007 | Мины от ног; exo skip |
| 008 | Ракету бластером не сбить; граната по маяку снимает ракету и открывает базу |
| 009 | §11.1 |
| 023 | Нижняя пушка стреляет и гранатится (**ожидаемый fail**) |
| 024 | Бонус с костюмом и без |
| 035 | Хиты до снятия луча (25 vs 50) |
| 059 | Телепорт к маяку |
| 124 | FULL COMBAT ABILITY → title → SPACE (ожидаемый повтор complete) |

---

## 12. Воспроизведение Linux-доказательств

Из корня репозитория:

```bash
python3 engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/linux_static_audit.py
```

Артефакты: `evidence/linux-static-audit.md`, `evidence/linux-static-audit.json`.

Анализ маршрута:

- `evidence/analysis-repo_explorer.md`
- `evidence/analysis-architect.md`
- `evidence/analysis-docs_researcher.md`

Бэклог: `engineering/reports/exolon-initial-audit-backlog.md`.

Повторный запуск скрипта не требует Swift.

---

## 13. Следующие шаги (после этого аудита, не в этом прогоне)

1. macOS: `xcodebuild` + §11.1 — закрыть гипотезу провала кабины.\
2. Если play подтвердит C1: исправить exclusion на `trigger.minY + 16` (или эквивалент «пол остаётся»), не перекрашивать тайлы 009 вручную.\
3. Развести бонус double launcher и `isActive` стрельбы.\
4. `beam_up`+`beam_down` → одно поле, 25 хитов.\
5. Либо реализовать BOTTOM-пушки / ракеты / таблицы врагов, либо явно пометить как следующий step.\
6. Честный комментарий/флаг у stage-end; либо полный оригинал (bravery, сброс костюма, UI).\
7. Решение по стик-UP = `.jump`.\
8. Согласовать 0.3 vs 0.5.\
9. Не считать зелёный `grok_verify` сборкой игры.

Продуктовый код в этом маршруте **не менять**.
