# docs_researcher — канон конца стадии (P1-10) и формулировки приёмки релизного слоя (P1-11)

Изменение: `20260924-complete-wave-d-specification-and-release-audit-8341b7`
Маршрут: `8341b7aa6eb4` (intent=release, risk=high, write-owner=none).
Дерево на момент чтения: HEAD `295690b7fc724e57b37b5fac86b71c1da7d8b032`
(`codex/wave-d-spec-release-20260924` == `origin/main` == база всех четырёх wave-веток).
Режим: **только чтение**. Отчёт — разбор источников, не проект.

Правило пометок: `НОРМА` — прямой текст нормативного источника; `ФАКТ ДЕРЕВА` — измерено
чтением кода/данных в этом прогоне; `SILENT — ruling required` — источник молчит.

---

## 0. Инвентарь нормативных источников и их иерархия

| Источник | Статус | Что даёт по концу стадии |
| --- | --- | --- |
| `ORIGINAL_MECHANICS.md:138-148` | **первичная норма** | 8 пунктов последовательности |
| `ORIGINAL_MECHANICS.md:111-119` | норма | экзоскелет: персист, сброс на границе стадии, forfeit bravery |
| `ORIGINAL_MECHANICS.md:105-109` | норма | refill 99/10 как **restore**, не аддитивный pickup |
| `ORIGINAL_MECHANICS.md:11-17` | норма | 125 зон / 5 стадий, старт 9 жизней |
| `ORIGINAL_MECHANICS.md:166`, `:148` | норма | что после зоны 124 |
| `engineering/reports/exolon-full-audit-20260920-v3.md:35` (P1-10) | авторитет находки (**и этот файл — авторитет по иерархии документов, `:11-14`**) | «из 6 правил конца стадии работают 3» |
| GitHub `Dimkox/exolon` issue **#14** (label `wave-D`, OPEN) | постановка владельцем | одна фраза, без чисел |
| GitHub `Dimkox/exolon` issue **#15** (label `wave-D`, OPEN) | постановка владельцем | формулировка приёмки P1-11 (см. §3.1) |
| README.md | **не** норма по концам стадии | ни одного упоминания stage-end бонуса (grep `bravery\|timed\|10000` по README — 0) |
| `evidence/perfile/mechanic-fidelity.md`, `economy-score.md` (пакет 20260919) | слой доказательств, не норма | подтверждают отсутствие |
| `rusarh/exolon-esl` (первоисточник дизассемблирования, `ORIGINAL_MECHANICS.md:4`) | **вне дерева** | в репозитории 0 файлов `.asm` (`find . -iname '*.asm'` → пусто) — перепроверить норму по первичке на этой машине нельзя |

Сокращение `evidence/perfile/…` ниже означает
`engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/perfile/…`;
кроме файлов с суффиксом/именем `…-v2`, `macos-validation-handout-v2.md` и
`release_layer_check.py` — они лежат в `engineering/changes/20260921-close-audit-finding-p1-11-release-layer-for-the-2e7698/evidence/`.

Текст issue #14 дословно: *«Отсутствуют bravery bonus 10000 и timed bonus 0/1000/3000/5000/7000
на границах 24/49/74/99/124. Восстановить механику или зафиксировать спецификацию. Источник:
full audit P1-10.»* — то есть владелец явно допустил исход «зафиксировать спецификацию», а не
только «чинить».

---

## 1. Канон: полный состав конца стадии и его числовая семантика

### 1.0 Дословная норма (`ORIGINAL_MECHANICS.md:138-148`)

```
138: ## Stage ends: Zones 024, 049, 074, 099, 124
140: - Reaching the stage-end trigger opens the bonus sequence.
141: - Award 1000 points per remaining life.
142: - If no exoskeleton was taken, award 10,000 bravery points.
143: - Timed bonus cursor can add 0/1000/3000/5000/7000 points depending on the selected phase.
144: - Add one life, capped at 9.
145: - Clear exoskeleton.
146: - Restore ammo=99 and grenades=10.
147: - Stage starting positions from source: Zone 000 `(16,112)`, 025 `(0,120)`, 050 `(0,32)`, 075 `(40,128)`, 100 `(16,112)` in original coordinates.
148: - Zone 124 displays FULL COMBAT ABILITY and then returns the game to the beginning.
```

Порядок строк 141→146 — единственный в tree-источнике носитель порядка операций. Сам он
число не фиксирует (см. §1.2, §1.4), но он **есть** в тексте и снимается только явным решением.

### 1.1 `lives × 1000`

- НОРМА: «Award 1000 points per remaining life» (`:141`). Множитель — за **оставшиеся** жизни.
- ФАКТ ДЕРЕВА: `GameScene.swift:627` `awardPoints(gameState.lives * 1_000)` — реализовано,
  вызывается из `checkScreenExit` (`:609-619`, вызов на `:612`).
- Границы:
  - `lives` на момент расчёта — до `+1` (`:627` раньше `:628`), что согласуется с порядком
    строк нормы. Совпадает ли это с оригиналом — **SILENT — ruling required** (норма не говорит,
    до или после прибавления считается бонус; вывод по порядку строк — интерпретация).
  - Верхняя отсечка счёта: `awardPoints` клампит `min(999_999, …)` (`GameScene.swift:662`).
    ОРИГИНАЛЬНАЯ норма про потолок 999999 **молчит** — это решение ремейка.
    **SILENT — ruling required**: поведение при переполнении (кламп vs wrap vs «не начислять»).
- Неясное: «remaining life» = `lives` после смерти в этой зоне? Смерть списывает жизнь на
  `GameScene.swift:322`, значит да — но норма это не проговаривает.

### 1.2 Bravery 10000

- НОРМА: `:142` «If no exoskeleton was taken, award 10,000 bravery points»;
  `:118` «Having the exoskeleton forfeits the 10,000-point bravery bonus».
- ФАКТ ДЕРЕВА: в `Exolon/` bravery нет (`grep -rni "bravery" --include=*.swift Exolon/` → **0**
  совпадений; с `10_000|7_000|5_000|3_000` вместе — тоже **0**. То же зафиксировано в
  `evidence/perfile/mechanic-fidelity.md:184, :291`).
- Предикат **не** сведён к булеву флагу в норме. Три разных чтения:
  1. «не брал за всю стадию» (текучая форма `was taken`, `:142`);
  2. «не надет в момент конца стадии» (форма состояния, `:118` «Having»);
  3. «не надет и не снимал» — различимы только если костюм можно выключить.
  Костюм **тоггловый** (`:113` «It toggles the exoskeleton state»; `Player.swift:243-246
  toggleExoskeleton`), а кабины в данных — по одной на стадию: `changing_room` встречается
  ровно в 5 файлах, `L01S10 / L02S10 / L03S11 / L04S16 / L05S10` (зоны 009/034/060/090/109),
  1 маркер в каждом. Значит выключить можно только в той же зоне, где включил: прочесть
  различие (1) vs (2) игрок штатно может, повторно нажав UP в той же кабине.
  **SILENT — ruling required** (какое из трёх).
- Момент проверки флага vs момент сброса флага: норма ставит «Clear exoskeleton» (`:145`)
  **после** bravery (`:142`) — порядок обязывает читать флаг до очистки. ФАКТ ДЕРЕВА: нигде в
  `Exolon/` нет ни `setExoskeleton(false)` на границе стадии, ни чтения `hasExoskeleton` в
  бонус-ветке; единственный писатель `false` — рестарт (`GameScene.swift:963`, внутри
  `restartFromBeginning`, `:950`). Аудит это же фиксирует как «`setExoskeleton(false)` —
  единственное вхождение в `:963` (только рестарт)» (`…-v3.md:35`).
- Bravery + timed: начисляются ли оба и в каком порядке — норма перечислением, без суммы.
  Максимально возможный «идеальный» конец стадии по тексту нормы = `lives·1000 + 10000 + 7000`
  (при 9 жизнях = 98 000). Это **арифметика по норме**, а не цитата; в дереве нигде не зафиксировано.

### 1.3 Timed bonus 0/1000/3000/5000/7000 — что именно он измеряет

- НОРМА (`:143`) дословно: «Timed bonus **cursor** can add 0/1000/3000/5000/7000 points
  depending on the **selected phase**». Три слова-несущих: *cursor*, *selected*, *phase*.
  Норма **не** определяет, временем ли она является; слово *Timed* в заголовке строки —
  единственное указание на время.
- **Ловушка склейки источников.** В `ORIGINAL_MECHANICS.md` есть другой «timed»: раздел
  `:129-136` «Timed indestructible pursuer», где «Zone timer uses a **700-loop threshold**»
  (`:131`) и «roughly 20–30 seconds on original hardware» (`:136`). Это механика преследователя,
  **не** бонуса. Считать `0/1000/3000/5000/7000` функцией от `700` или от времени стадии —
  ничем не обоснованная контаминация. Отдельно: преследователь и rocket towers в дереве не
  реализованы (`engineering/reports/exolon-full-audit-20260920-v3.md:134-135` — P2-строка бэклога
  «rocket towers и таймер-преследователь не реализованы»), так что даже переиспользовать его
  таймер нечем.
- Что говорят вне-древесные кросс-чеки (источник #4 по иерархии `ORIGINAL_MECHANICS.md:7` —
  «StrategyWiki walkthrough only as a cross-check», то есть **не** норма): тайм-бонус — это
  бонус-экран с бегущей стрелкой/курсором и списком значений, где игрок останавливает её
  нажатием FIRE; 7000 — максимум. Подтверждающие тексты (внешние, прочитаны поисковым агентом,
  мной напрямую не открыты — `strategywiki.org` отдал 403 на два запроса):
  `https://retrogames.biz/games/spectrum/exolon/`,
  `https://rufusplaysgames.wordpress.com/2017-11-28/exolon/`,
  `https://thekingofgrabs.com/2022-06-20/exolon-zx-spectrum/`.
  Это **косвенно подтверждает** чтение «phase = позиция курсора, а не таймер», но косвенный
  слой не может закрыть норму: `rusarh/exolon-esl` вне дерева (§0), первичку на этой машине
  не прочитать.
- Итого по границам значений — **SILENT — ruling required** по каждому пункту:
  - сколько фаз у курсора и в каком порядке стоят слоты (текст даёт **5 значений**, из них
    `0` — одно из них, а не «промах по умолчанию»);
  - какое нажатие что фиксирует (edge? удержание? FIRE/START/UP?) и можно ли пропустить экран;
  - скорость/длительность прокрутки и её единицы (тики 50 Гц, 60 Гц фикс-шаг ремейка —
    `GameConstants.swift:6` `fixedTimeStep = 1/60`, а комментарий `GameConstants.swift:9-10`
    про оригинал говорит «ZX Spectrum timing is 50 Hz»; противоречие единиц — отдельный
    незакрытый P2, `TC-05` в `…-v3.md:87`);
  - начисляется ли timed на зоне 124 (строка `:148` описывает только оверлей);
  - что делает `0`: «значений пять, ноль — одно из них» или «нет попадания — нет очков».
- ФАКТ ДЕРЕВА: ни курсора, ни оверлея, ни таблицы фаз (`evidence/perfile/mechanic-fidelity.md:214`
  — «Timed bonus cursor 0/1000/3000/5000/7000 | отсутствует | `GameScene.swift:622-631` — ни
  курсора, ни оверлея»).

### 1.4 «+1 life, capped at 9»

- НОРМА: `:144`; контекст — «New game starts with 9 lives» (`:14`).
- ФАКТ ДЕРЕВА: `GameScene.swift:628` `if gameState.lives < GameState.startingLives { gameState.lives += 1 }`;
  `GameState.swift:81-83` `startingAmmo = 99`, `startingGrenades = 10`, `startingLives = 9`.
  Потолок реализован как «не прибавлять при 9», а не как «прибавить и обрезать».
- Границы:
  - при `lives == 9` — ничего (текстом не подтверждено, что оригинал «съедает» жизнь молча);
  - может ли `lives` превысить 9 иным путём (единственный другой писатель — списание при
    смерти, `GameScene.swift:322`) — нет; значит «cap» наблюдим только как «no-op»;
  - HUD/отображение 9-vs-10 — **SILENT**;
  - порядок `+1` относительно `lives·1000` — см. §1.1, вывод по порядку строк, не прямая норма.

### 1.5 Clear exoskeleton

- НОРМА: `:145` «Clear exoskeleton»; область действия флага: `:115` «It persists through deaths
  until the end of the current 25-zone stage»; иммунитет — `:116` (только источники, зовущие
  `KillPlayer_unless_Exoskeleton`, «including mines and pumps»); двойной выстрел — `:119`
  («Walkthrough behaviour also describes the suit as giving double blaster fire; this must be
  retained in the remake»).
- ФАКТ ДЕРЕВА: персист реализуется тем, что сброса нет — `configure`/`finishDeathAndRespawn`
  (`Player.swift:40`, `:227`) `hasExoskeleton` не трогают; читается флаг в трёх местах:
  `GameScene.swift:346` (второй пуля, без списания патрона — `ammo -= 1` один раз на `:351`),
  `:546` (мины), `:557` (поршни); визуал — `PlayerSpriteNode.swift:45-46` (цветная подмена,
  «Temporary visual cue until the original exoskeleton frames are wired», `:43-44`).
  Стоимость второго выстрела в патронах норма не определяет — **SILENT** (заметим, `:125`
  считает силу поля по **пулям**, «13 trigger pulls with double-shot because two bullets count
  separately», то есть патрон ≠ пуля в норме уже различены).

### 1.6 Restore ammo=99 / grenades=10

- НОРМА: `:146`; смысл цифр — `:107-109` (белый ящик «sets ammo to exactly 99», жёлтый
  «sets grenades to exactly 10», «These are refills, not additive pickups») и `:14-15`
  (старт и смерть дают те же 99/10).
- ФАКТ ДЕРЕВА: `GameScene.swift:629-630` (конец стадии) и `:330-331` (смерть) — оба безусловным
  присваиванием констант. Аппаратного способа превысить 99/10 в модели нет, поэтому «restore»
  и «max(current, 99)» неразличимы: **SILENT — ruling required**, но не наблюдаемо.

### 1.7 Триггер: «stage-end trigger» vs номер зоны vs `x > 510`

- НОРМА `:140`: «Reaching the **stage-end trigger** opens the bonus sequence». Нигде в норме
  триггер не определяется как «номер зоны ∈ {24,49,74,99,124}» и не определяется как
  «правый край».
- ФАКТ ДЕРЕВА: маркер существует в данных — `blk_stage_end` ровно **5** вхождений, по одному
  в `Exolon/Resources/L01S25.tmx`, `L02S25.tmx`, `L03S25.tmx`, `L04S25.tmx`, `L05S25.tmx`.
  Он разбирается в `TMXLevelRuntime.swift:369-370` в `stageExitMarkers`
  (`width: 96, height: 128`, `y = max(0, bottomY - 64)`), и **не читается нигде** (`grep -rn
  stageExitMarkers Exolon/` → только объявление `:30` и запись `:370`). Фактический вход в
  бонус-ветку — `player.position.x > 510` (`GameScene.swift:610`) **И** `completedZone ∈
  [24, 49, 74, 99, 124]` (`:625`). Разрыв «норма говорит trigger, код смотрит на номер зоны»
  зафиксирован и раньше (`evidence/perfile/mechanic-fidelity.md:321`, `…-v3.md:78` RT-05).
  `gameState.zone` считается из имени файла регуляркой `^L(\d{2})S(\d{2})$`
  (`GameScene.swift:988-996`), то есть `max(0, min(124, (stage-1)*25 + (screen-1)))`.

### 1.8 После зоны 124

- НОРМА: `:148` «Zone 124 displays FULL COMBAT ABILITY and then **returns the game to the
  beginning**»; `:166` «Zone 124 completes the full game and **loops to the beginning**».
- ФАКТ ДЕРЕВА: `L05S25` не имеет свойства `nextlevel` (grep по файлу — 0), поэтому
  `checkScreenExit` уходит в `enterContentComplete` (`:614-616`, тело `:738-759`); при
  `gameState.zone >= 124 && nextLevelName.isEmpty` печатается оверлей `title:
  "FULL COMBAT ABILITY"`, `line2: "ALL 125 ZONES COMPLETE"`, `hint: "SPACE / □ — TITLE"`
  (`:743-749`); нажатие FIRE (edge, `:201-205`) → `showTitleAfterContentComplete`
  (`:761-768`) → `flowState = .title`. Строка `hint` и `line2` — тексты ремейка, нормы не имеют.
- Что именно значит «returns the game to the beginning» — **SILENT — ruling required**:
  сброс счёта/жизней (как `resetForNewGame`, `GameState.swift:93-99`, где `points = 0` и
  `lives = 9`; вызывается из `restartFromBeginning`, `GameScene.swift:960`, и из
  `loadPersistentState`, `:693`) или возврат на титул с сохранением прогресса
  (фактическое поведение `:761-768`). Ни то, ни другое норма не фиксирует.
- Побочный, уже документированный риск ветки: бонус применяется **до** проверки пустого
  `nextLevel`, из-за чего цикл 124 → титул → 124 повторяемо (`…-v3.md:33` P1-8; расчёт
  `(999999−45000)/9000 = 106.1 ⇒ 107` циклов; описание ожидаемого поведения —
  `evidence/perfile/macos-validation-handout.md:143` (M-07)). Любая правка конца стадии
  обязана назвать, чем этот повтор гасится, — иначе P1-10 закроет P1-8 «случайно» или наоборот.

### 1.9 Позиции старта стадии (`:147`) — единственный пункт, где норма **противоречит** дереву

- НОРМА: `:147` даёт оригинальные координаты старта: `000 (16,112)`, `025 (0,120)`,
  `050 (0,32)`, `075 (40,128)`, `100 (16,112)` — «in original coordinates».
- ФАКТ ДЕРЕВА: `transition` различает старт стадии (`isStageStart` по `[0, 25, 50, 75, 100]`,
  `GameScene.swift:642`) и берёт `currentLevel.spawnCenter` (`:643-646`), то есть **из данных
  карты**, а не из таблицы `:147`; на обычных зонах высоту несёт `carriedY` с нижней границей
  по полу (`:645`). Никакой константы `16,112 / 0,120 / 0,32 / 40,128` в `Exolon/` нет.
- Противоречие: норма `:147` лежит в разделе «Stage ends», но по содержанию — про старт
  следующей стадии, и она не переведена ни в код, ни в комментарий. Для P1-10 это граница
  скоупа: **SILENT — ruling required** (входит ли позиция старта стадии в «полную
  stage-end последовательность» этого изменения, или остаётся отдельным находкам).

### 1.10 Сводка: что из нормы уже работает, а что нет

| # | Пункт нормы (`:141-146`) | Состояние в дереве | Цитата места |
| --- | --- | --- | --- |
| 1 | lives·1000 | есть | `GameScene.swift:627` |
| 2 | bravery 10000 | **нет** | `grep bravery Exolon/` = 0 |
| 3 | timed 0/1000/3000/5000/7000 | **нет** | `GameScene.swift:622-631` (весь тело-блок) |
| 4 | +1 life cap 9 | есть | `GameScene.swift:628` |
| 5 | clear exoskeleton | **нет** на границе стадии | единственный писатель `false` — `GameScene.swift:963` |
| 6 | restore 99/10 | есть | `GameScene.swift:629-630` |

Ровно «3 из 6», как записано в `engineering/reports/exolon-full-audit-20260920-v3.md:35`.
Комментарий `GameScene.swift:623-625` («deliberately dormant until later steps add Zones
024/049/074/099/124») при этом лжёт: guard `[24, 49, 74, 99, 124]` уже активен и выполняется,
цепочка `nextLevel` полна 125/125 (`…-v3.md:35`).

---

## 2. Сводка ambiguities P1-10 (только перечёт решений, без проекта)

1. Timed: измеряет ли что-то время — **SILENT** (норма говорит *cursor*/*phase*; кросс-чек
   говорит «останови стрелку»; первичка `rusarh/exolon-esl` вне дерева).
2. Timed: таблица фаз, число слотов, порядок значений, единицы движения, пропуск экрана — **SILENT**.
3. Timed на зоне 124 (есть/нет, до/после оверлея) — **SILENT**.
4. Bravery: «was taken» (за стадию) vs «having» (в момент конца) — **SILENT**, различимо
   тогглом в той же кабине.
5. Порядок операций 141→146 как обязательный — вывод из перечисления, прямой нормы на порядок
   нет — **SILENT**.
6. `lives·1000` до или после `+1` — **SILENT** (код: до).
7. Потолок 999999 vs сумма бонусов — **SILENT** (кламп есть, `GameScene.swift:662`; нормы нет).
8. Cap 9 при уже 9: no-op vs «сгорает» — **SILENT**.
9. Триггер конца стадии: `blk_stage_end` (5 маркеров, не читается) vs номер зоны vs `x > 510` —
   норма называет только «trigger»; **SILENT**, какой из трёх носителей канонический.
10. «Returns to the beginning»: полный reset vs титул с сохранением — **SILENT**.
11. Позиции старта стадии `:147` — противоречат дереву; входят ли в скоуп — **SILENT**.
12. Скоуп-ссылка «in coordination with the wave-A **StageBoundaryLedger**»
    (`brief.md:1`, `change-spec.yaml:16`): сущности нет ни в дереве, ни в истории.
    `git log --all -S "StageBoundaryLedger"` → **0 коммитов**; `grep -rn StageBoundaryLedger
    Exolon/` → 0; ветка `codex/wave-a-gameplay-log-tick-fixes-20260924` стоит на том же
    `295690b`, что и wave-D. То есть «координация» предписана с объектом, который ещё не
    существует в Git. **БЛОКИРУЮЩАЯ неясность для скоупа**: либо план wave-A (вне дерева), либо
    опечатка. Никаких других артефактов wave-A в `/home/pall/projects/.exolon-wave-*` нет
    (каталоги `b`, `c`, `d`; `wave-a` отсутствует).
13. `change-spec.yaml` этого изменения — шаблон: `acceptance_criteria: []`,
    `forbidden_outcomes: []`, `invariants: []`, `success_metric: "UNKNOWN"`,
    `target: "UNKNOWN"` (`change-spec.yaml:2`, `:12`, `:13`, `:17-18`). Типизированной приёмки P1-10 в
    пакете нет ни одной; markdown-файлы пакета тоже пусты (`requirements.md:7` — `- [ ] Given …`).

---

## 3. P1-11: точные формулировки приёмки релизного слоя

### 3.1 Постановка владельца (issue #15, репо `Dimkox/exolon`, label `wave-D`, OPEN)

> «Проверить version identity, hardened runtime, signing, archive и notarization end-to-end на
> чистой машине. Источник: full audit P1-11.»

Пять именуемых клауз: **version identity**, **hardened runtime**, **signing**, **archive**,
**notarization**; способ приёмки — «end-to-end на чистой машине», то есть macOS-прогон, а не
статика.

### 3.2 Строка находки (`engineering/reports/exolon-full-audit-20260920-v3.md:36`)

> «P1-11 | **Релизный слой не годен для публикации** | `Info.plist` литерал
> `CFBundleShortVersionString=0.3` при `MARKETING_VERSION=0.5` и `GENERATE_INFOPLIST_FILE=NO`;
> `CFBundleVersion=1` литерал; `.xcscheme` — **0** (1 native target, 0 test-таргетов); подпись
> `CODE_SIGN_IDENTITY="-"`, `CODE_SIGN_STYLE=Manual`, `ENABLE_HARDENED_RUNTIME` отсутствует»

**Важно для этого маршрута:** строка датирована базой `403eb13` и на HEAD `295690b` частично
устарела — первые две клаузы уже закрыты и **вмержены** (`git merge-base --is-ancestor
fee613e HEAD` → истина; пакет `20260921-close-audit-finding-p1-11-release-layer-for-the-2e7698`):

- `Exolon/Resources/Info.plist:17-20` — `$(MARKETING_VERSION)` / `$(CURRENT_PROJECT_VERSION)`;
- `Exolon.xcodeproj/xcshareddata/xcschemes/Exolon.xcscheme` — существует (1 на всё дерево);
- при этом `GENERATE_INFOPLIST_FILE = NO` остаётся (`project.pbxproj:1420`, `:1439`),
  `CODE_SIGN_IDENTITY = "-"`, `CODE_SIGN_STYLE = Manual`, `DEVELOPMENT_TEAM = ""`
  (`project.pbxproj:1415-1419`, `:1434-1438`), `ENABLE_HARDENED_RUNTIME` — **0 вхождений**.

Правила датированного доказательства запрещают править эту строку задним числом
(`change-spec.yaml` прошлого пакета: AC-009 «Dated evidence is append-only», FORBID-004).

### 3.3 Дословные формулировки приёмки из закрытого пакета (на них обязан опереться «remaining scope»)

- `change-spec.yaml` AC-006: «engineering/runbooks/macos-probe.sh no longer asserts the
  pre-fix gaps as expectations (zero stale EXPECTED lines) and gained the archive step plus the
  shared-vs-autogenerated scheme discriminator and a codesign flags reader that can actually
  observe the hardened runtime.»
- AC-007: «ENABLE_HARDENED_RUNTIME stays absent from every build configuration and that
  deferral is recorded as a decision with a reason and a next step in this package (release.md,
  requirements.md, change-spec), not silently skipped; the verifier turns red if the deferral
  record disappears while the key is still absent.»
- AC-010 (граница Linux-verdict): «The Linux verdict never certifies macOS-only facts: expanded
  bundle values, scheme-loader acceptance, archive outcome and codesign runtime flags are
  asserted only by the macOS runbook and handout v2, and the verifier contains no acceptance
  criterion that pretends to measure them here.»
- FORBID-002: «ENABLE_HARDENED_RUNTIME must not be enabled in this change, in either
  configuration, before the first successful build (M-01) is proven on macOS…»
- FORBID-003: «No test target, no TestableReference, no signing identity, no DEVELOPMENT_TEAM
  value and no .entitlements file may enter the tree through this change.»
- FORBID-006: «P1-11 must not be declared fully closed: only the identity and scheme clauses
  are closed, the signing clause remains open.»
- INV-001: «…ENABLE_HARDENED_RUNTIME is either absent from both or present in both, never
  one-sided.»
- `approvals.required_scopes`: `scope_and_design_approval`, `defer_hardened_runtime`,
  `macos_validation_run_by_owner`, `audit_backlog_partial_closure_note`.
- `success_metric`: «release_layer_check.py rc=0 with 0 red AC and 29/29 controls OK on the
  merged head, plus grok_verify --mode pr PASS on the same fingerprint»; `target`:
  «rc=0 / red_ac=0 / bad_controls=0».
- `release.md:6` прошлого пакета: «релизный **слой** дерева становится пригодным для
  публикации, самого артефакта (`.xcarchive`, notarization, Release на GitHub) этот change не
  создаёт»; `release.md:65`: «Подписные материалы (Developer ID, сертификаты, `.entitlements`,
  нотаризация, MAS) — **вне периметра репозитория навсегда**: AGENTS.md запрещает агенту
  создавать или использовать человеческие ключи approvals и читать подписные секреты».

Это и есть жёсткий конфликт, который пакет обязан разрешить явным решением: issue #15 требует
проверить signing и notarization end-to-end, а `AGENTS.md:173` («Reading `.env`, private keys,
credential stores, … CI signing keys, GitHub App keys or approval keys») и `AGENTS.md:21`
(агент не создаёт и не использует человеческие ключи) не пускают агента в подписные материалы.
Формулировка «проверить» ⇒ «зафиксировать проверяемость и прогнать на машине владельца» —
единственная непротиворечивая; **решение за человеком** (гейт маршрута
`scope_and_design_approval`, `route.json: human_gates`).

### 3.4 Что реально покрывает инфраструктура сегодня (ФАКТ ДЕРЕВА)

- `engineering/runbooks/macos-probe.sh` (210 строк): `codesign -dv` (`:115`), `spctl -a` (`:116`),
  чтение флага hardened runtime только из `flags=` (`:118-121` — «hardened runtime наблюдается
  только в словах flags= из `-d --verbose=4`»), archive **за отдельным флагом** `WITH_ARCHIVE=1`
  (`:18`, `:132-142`, иначе `archive_rc=SKIPPED`, `:142`).
- **Notarization: 0 упоминаний** и в probe (`grep -in "notar" engineering/runbooks/macos-probe.sh`
  → пусто), и в верификаторе (`grep -ci notar release_layer_check.py` → **0**).
- Проверка верификатора в этом прогоне: `python3 evidence/release_layer_check.py --root .` на
  HEAD `295690b` — **rc=0** (релизный слой совпал с пост-фиксными ожиданиями).
- Формулировка «честного ожидания» для archive, которую нужно сохранить и в новом скоупе
  (`evidence/perfile/macos-validation-handout-v2.md:50-53`): «`archive_rc` может быть
  ненулевым **из-за подписи** … провал класса „нет схемы / нечего архивировать“ означал бы,
  что M-02′ не прошёл, а провал по подписке — что работа схемы в порядке и находка переходит к
  клаузе „подпись“. Фиксировать вывод полностью.»
- Предел Linux-вердикта зафиксирован нормативно (§3.3 AC-010) и подтверждён практикой:
  `…-v3.md:47-49` — исполнимы модули без SpriteKit, «сборка и рендер — только macOS».

### 3.5 Границы remaining-скоупа P1-11, не закрытые ни одним источником

1. Канон «чистой машины»: чистый пользователь, чистый `/tmp`, без кэшей Xcode — **SILENT**
   (и в issue #15, и в runbook критерий «clean» не определён).
2. Notarization: кто запускает (`xcrun notarytool` vs `altool`), чем проверяется результат
   (`stapler validate`, `spctl` на распространяемом артефакте), где хранится профиль — **SILENT**
   + запрещённая зона по подписным секретам (`AGENTS.md:21,173`).
3. Пригоден ли существующий `release_layer_check.py` для расширения или заводится новый
   измеритель — вопрос не источников, а маршрута; здесь только фиксируется: он лежит в
   **чужом** change-пакете (`20260921-…/evidence/`), а не в этом.
4. Формулировка «Linux-decidable parts committed, the macOS run documented as an external
   handout» (`brief.md:1`) не определяет, чем именно является «external handout» в терминах
   доказательства (файл в дереве vs вне) — прошлый пакет решил это как
   `evidence/perfile/macos-validation-handout-v2.md`; прямого нормативного требования нет.
5. Судьба отсрочки `ENABLE_HARDENED_RUNTIME` в новом скоупе (по-прежнему ли absent, или
   предусловие M-01′ уже снят) — **SILENT**: в репозитории нет ни одного артефакта зелёного
   M-01′ (первой успешной сборки), значит по FORBID-002 предусловие не доказано.

---

## 4. Что этот отчёт НЕ утверждает

- Не предлагает дизайн, порядок исправлений, имена сущностей или тесты.
- Не подтверждает ни одно число timed-бонуса как производное от времени: ни один древесный
  источник этого не говорит.
- Не читал и не цитировал первичную дизассемблировку (`rusarh/exolon-esl`) — её нет в дереве.
- Внешние walkthrough-строки (§1.3) — кросс-чек слой, получен через поисковый агент; прямых
  fetch'ей strategywiki.org получить не удалось (403 дважды), поэтому они помечены как
  неподтверждённые мной лично и нормой не являются.
