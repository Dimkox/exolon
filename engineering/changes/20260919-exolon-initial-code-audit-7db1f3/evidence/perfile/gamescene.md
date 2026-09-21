# Per-file аудит: `Exolon/GameCore/GameScene.swift` (1130 LOC, HEAD 52795d1)

Лейн: один файл, построчно. Прочитаны также (только для проверки утверждений):
`GameCore/GameState.swift`, `GameCore/InputState.swift`, `GameCore/GameConstants.swift`,
`GameCore/Player/Player.swift`, `GameCore/Player/PlayerSpriteNode.swift`,
`GameCore/Levels/TMXLevelRuntime.swift`, `GameCore/Levels/TMXMapLoader.swift`,
`GameCore/Objects/LevelObstacles.swift`, `GameCore/Weapons/BlasterBullet.swift`,
`GameCore/Weapons/Grenade.swift`, `GameCore/HUDNode.swift`,
`Platform/macOS/GameView.swift`, `Platform/macOS/GamepadInput.swift`, `Platform/macOS/AppDelegate.swift`,
`README.md`, `ORIGINAL_MECHANICS.md`.

Методы проверки, кроме чтения:
- `/tmp/perfile-gamescene/chain.py` — разбор 125 TMX (цепочка `nextLevel`, геометрия кабин и спавна).
- `/tmp/perfile-gamescene/farm_sim.swift` — **реплика** конечного автомата `GameScene`
  (`fixedUpdate` 148–308 + 601–680 + 685–767 + кламп x из `Player.swift:128`), запущена на
  Swift 6.4 под Linux. Это НЕ сборка продукта (SpriteKit/AppKit на Linux нет), а перенос
  логики состояний 1-в-1 в исполняемый вид; все строки-ссылки в комментариях реплики —
  строки продукта.

---

## Итог

- **Ферма B-03 подтверждена и измерена.** В зоне 124 (`L05S25.tmx` — единственный файл из 125
  без `nextLevel`) бонус стадии начисляется **до** проверки пустого `nextLevel`
  (`GameScene.swift:612` vs `:614`), а цикл `.contentComplete → .title → beginFromTitle`
  не трогает ни `points`, ни `zone`, ни позицию. Реплика: **111 циклов = 222 нажатия SPACE →
  +990 999 очков, до потолка 999 999, и потолок уходит в персистентный high score**;
  заодно каждый цикл возвращает жизнь до 9 и refill 99/10. Это не «P2-ферма», а дыра
  единственного персистентного показателя игры.
- **F1 подтверждена как корень B-03:** `beginFromTitle` (`:708-717`) — это «продолжить»,
  а не «новая игра»; полный сброс делает только `restartFromBeginning` (`:950-986`), который
  из титула недостижим. `ORIGINAL_MECHANICS.md:147` («Zone 124 displays FULL COMBAT ABILITY and
  then returns the game to the beginning») нарушено.
- **O5 подтверждена и расширена:** комментарий `:623-625` («deliberately dormant … until later
  steps add Zones 024/049/074/099/124») вращается — все пять карт существуют и бонус **живой**;
  при этом из шести правил конца стадии (`ORIGINAL_MECHANICS.md:140-145`) реализовано три:
  нет bravery-бонуса 10 000, нет timed-бонуса, и — главное — **костюм никогда не снимается**:
  `setExoskeleton` в продукте вызывается ровно один раз, в `:963` (restart).
- **B-05 подтверждена с уточнением:** `GamePersistence.loadCheckpoint()` не вызывается нигде,
  а `loadPersistentState` удаляет запись до всякого чтения (`:690`); надпись «CONTINUE»
  (`:900-903`) берётся из памяти процесса, а не с диска, и честна в рамках сессии.
  То есть «лжёт» не текст, а сама персистентность: 6 ключей чекпоинта пишутся 5 вызовами
  и не читаются никогда.
- **README (Step 9) по этому файлу выполняется** — поршень lethal, INVULNERABILITY-шлюз,
  UP-в-кабине, двойной бластер, защита от мин/поршней, Restart снимает костюм, старт с 000,
  High Score переживает запуск — **кроме** двух пунктов: «UP» с аналогового стика кабину и
  телепорт не включают вовсе (`:229-234` читает только `.jump`), и «UP не превращается в
  случайный прыжок» выполнено только в пределах шага, но не через границу экрана.
- **Вердикт — fail.** Два P1-дефекта (GS-01, GS-02) ловятся только игрой на macOS; локальный
  гейт не ловит ничего: в `.grok-stack/adaptive_grok/verification.py` нет ни `swift`, ни
  `xcodebuild`, а в `Exolon.xcodeproj` — ни одного test-таргета (только `Exolon`). Модуль
  физически нечем проверить, кроме ручного чтения.

---

## Таблица находок

| ID | Pri | file:line | что делает код | триггер | доказуемость |
| --- | --- | --- | --- | --- | --- |
| **GS-01** | **P1** | `GameScene.swift:612`, `:614-618`, `:708-717`, `:761-767`, `:201-207`, `:308` | `checkScreenExit` вызывает `applyOriginalStageBoundaryIfNeeded(completedZone: gameState.zone)` **до** `guard !next.isEmpty, includedLevels.contains(next)`; начисление не откатывается, если переход не состоялся. `showTitleAfterContentComplete` ведёт в `.title`, а `beginFromTitle` из `case .title:` делает только `flowState = .playing` + unpause — без сброса `points/lives/zone/позиции/костюма` | в зоне 124 дойти до `x > 510`, затем жамкать SPACE: нажал → титул, нажал → игра → на следующем фикс. шаге снова `checkScreenExit` → снова бонус → снова `.contentComplete` | **Linux**: трассировка + исполняемая реплика (111 циклов / 222 нажатия → 999 999, `checkpointWrites` растёт на каждый цикл). **macOS**: подтвердить глазами (оверлей «FULL COMBAT ABILITY» → титул → оверлей снова) |
| **GS-02** | **P1** | `GameScene.swift:622-631`, `:235`, `:963` | Тело бонуса: `awardPoints(gameState.lives * 1_000)` + `if gameState.lives < GameState.startingLives { gameState.lives += 1 }` + `ammo = startingAmmo` + `grenades = startingGrenades`. Нет `10_000` bravery (норма `ORIGINAL_MECHANICS.md:142`), нет `0/1000/3000/5000/7000` timed-бонуса (`:143`), нет «Clear exoskeleton» (`:117`, `:145`). Комментарий `:623-625` утверждает, что код спит, хотя `guard [24, 49, 74, 99, 124].contains(completedZone)` срабатывает: `chain.py` — цепочка L01S01→…→L05S25 длиной 125, все пять S25 на месте | взять костюм в зоне 009 и пройти границу стадии 024 → иммунитет к минам/поршням (`:546`, `:557`) сохраняется на все оставшиеся 100+ зон; на 124 бонус ещё и фармящийся (GS-01) | **Linux**: код+данные (grep: `setExoskeleton` — единственное вхождение в продукте, строка 963). **macOS**: замерить сложность |
| **GS-03** | **P2** | `GameScene.swift:690-691`, `:696-705`, `:335`, `:657`, `:716`, `:740`, `:985`, `:900-903`; `GameState.swift:40-50` | `persistence.clearCheckpoint()` в `loadPersistentState` **до** любого чтения; `saveCheckpoint()` пишется при каждом переходе/респауне/рестарте/входе в титул; `GamePersistence.loadCheckpoint()` — 0 вызовов во всём репо (`grep -rn loadCheckpoint --include=*.swift .` → только определение). `status?.text = hasSavedCheckpoint ? String(format: "CONTINUE · ZONE %03d", gameState.zone) : …` — про `gameState.zone` из памяти, не из диска | зайти в любую зону, убить процесс, запустить снова → «NEW GAME · ZONE 000», хотя на диске был чекпоинт; надпись «CONTINUE» появляется только после `enterContentComplete` в этой же сессии | **Linux**: grep + чтение. Play не требуется |
| **GS-04** | **P2** | `GameScene.swift:234` (vs `TMXLevelRuntime.swift:228`) | Кабина: `if currentLevel.changingRooms.contains(where: { $0.intersects(player.movementHitbox) })` — достаточно **пересечения**; телепорт рядом: `portal.fullyContains(playerBox:)` — полное вхождение. Далее `consumedUpInteraction = true` (`:238`) → `player.consumeContextualJumpPress()` (`:252`) и подмена `jump: false` (`:255-258`) | `geometry` из TMX: зона 009 триггер 32×80 → мёртвая зона UP = 78 px по X; зоны 034/060/090/109 (`source_marker changing_room`, 80×96) = **126 px**. Стоять рядом/под кабиной и нажать UP «чтобы прыгнуть» → костюм переключится, прыжка не будет | **Linux**: геометрия посчитана по 125 TMX. **macOS**: проверить ощущение (прыжок вдоль кабины в 009) |
| **GS-05** | **P2** | `GameScene.swift:229-234`, `:241` | Контекстное действие UP читает только `rawInput.jump`; стик вверх (`GamepadInput.swift:71`) ставит **только** `.menuUp`, никогда `.jump` (D-pad `:60-61` и клавиатура `GameView.swift:55-57` ставят оба) | геймпад, аналог: войти в кабину (зона 009) или в пару телепортов (зона 002) и толкнуть стик вверх → ни костюма, ни телепорта; D-pad/клавиатура — работают. Нарушение README «pressing UP inside the changing room toggles Exoskeleton» и `ORIGINAL_MECHANICS.md:156` | **Linux**: трассировка маппинга. **macOS**: подтвердить на реальном геймпаде |
| **GS-06** | **P2** | `GameScene.swift:539-541`, `:547-549`, `:581-583`, `:591-593` (шлюз в `:601-602`) | Опасности с «consume-on-contact» расходуются **до** проверки шлюза урона: `consumeGuidedMissileHit` уничтожает ракету, затем `hitPlayer()`; `mine.triggerIfPlayerEnters` ставит `isArmed = false` и `node.removeFromParent()` (`LevelObstacles.swift:753-754`), только потом `if invulnerability <= 0 && !player.isDying`; bubbles/eggs вообще без локальной проверки — `bubble.destroy(); awardPoints(bubble.points)` | 0.4 с защиты после смерти (`:333-334`) либо TEST INVULNERABILITY ON (`:186`, шлюз только в `hitPlayer`) → пройти сквозь мину/ракету/пузырь/яйцо: препятствие исчезает, очки капают, смерти нет. Для поршней/поля/хазардов (`:559-565`, `:568`, `:574`) порядок обратный — сначала шлюз, потом урон. Одна из двух половин неверна по построению | **Linux**: код. **macOS**: включить TEST INVULNERABILITY и пройтись по минному полю зоны 007 |
| **GS-07** | **P2** | `GameScene.swift:53`, `:614`, `:637`, `:60`, `:957` | `includedLevels` — захардкоженный **список имён**, а не проверка бандла; `transition(to:)` синхронно строит `TMXLevelRuntime(resource: levelName)`, у которого любая ошибка загрузки — `fatalError("Unable to load TMX map \(name): \(error)")` (`TMXLevelRuntime.swift:53`). Отката/ветки ошибки нет ни в одном из трёх конструкторов уровня | сегодня недостижимо: `chain.py` — цепочка замкнута (125/125 достижимы, 0 висячих `nextLevel`), в `PBXResourcesBuildPhase` ровно 125 `.tmx`. Опечатка в `nextLevel` или удалённый ресурс = мгновенное падение приложения посреди игры с потерей сессии (чекпоинт всё равно не читается — GS-03) | **Linux**: структура + данные. **macOS**: не требуется (проверять нечего до изменения данных) |
| **GS-08** | **P3** | `GameScene.swift:574-577` | `currentLevel.sourceHazards.contains(where: { !$0.isEmpty && $0.intersects(player.damageHitbox) })` — единственный читатель; `sourceHazards` объявлен (`TMXLevelRuntime.swift:28`) и **никогда не наполняется** (`grep -rn sourceHazards --include=*.swift .` → 2 вхождения: объявление и это чтение) | любое: ветка мертва «в обе стороны». Ветка выглядит как страховка от «high voltage/source»-убийств, которой по факту нет | **Linux**: grep |
| **GS-09** | **P3** | `GameScene.swift:610` (данные: `TMXLevelRuntime.swift:30`, `:370`) | `guard player.position.x > 510 else { return }` — авторский маркер `stage_end` (`blk_stage_end`, 5 объекта) распарсен в `stageExitMarkers` и **нигде не читается**; граница стадии выведена из номера зоны (`:626`), а не из триггера на карте | карта, где выход не справа или где `stage_end` стоит не в S25: маркер игнорируется, бонус сработает «на пустом месте» при x>510 | **Linux**: grep (0 использований). **macOS**: неактуально на текущих 125 |
| **GS-10** | **P3** | `GameScene.swift:151-157` | `if inputState.consumePausePress() { … return }` — нажатие Pause съедается всегда, а `enterPause` разрешён только из `.playing`/`.respawning` (`.paused` — выход). В `.playerDead`, `.title`, `.gameOver`, `.contentComplete` — тихий nothing | нажать P во время анимации смерти (~2.4 с падения + 70 кадров) → ни паузы, ни подсказки; пауза недоступна на всём времени смерти | **Linux**: код. **macOS**: ощущение тайминга |
| **GS-11** | **P3** | `GameScene.swift:652` + `Player.swift:239` (`respawn(){ jumpWasPressed = false }`) | `transition(to:)` обнуляет `sceneJumpWasPressed = false`, а `player.configure → respawn` обнуляет внутренний латч прыжка: **удерживаемый** UP через границу экрана превращается в новый «только что нажатый» UP в следующей зоне | удерживать UP и выйти вправо: реплика даёт `fresh-jump-steps in the new zone = 1`. Сегодня не перерастает в переключение костюма: ни один из 5 триггеров кабины не пересекает спавн-бокс (посчитано в `chain.py`), но на новых картах это мгновенный self-toggle | **Linux**: реплика (1 шаг). **macOS**: подтвердить прыжок через границу |
| **GS-12** | **P3** | `GameScene.swift:526`, `:533`, `:301-302`, `:403`, `:486` | `gameState.grenades = 10` и `gameState.ammo = 99` — литералы вместо `GameState.startingGrenades/startingAmmo`; `showBanner("+1000")` захардкожен рядом с `awardPoints(launcherBonus)` (значения сегодня совпадают); `awardPoints(1_000)` за force field и `awardPoints(150)` за гранату дублируют таблицы очков объектов | любое изменение `startingAmmo`/бонуса → HUD и баннер начинают врать; две точки истины | **Linux**: чтение |
| **GS-13** | **P3** | `GameScene.swift:988-997`, `:641-643` | `zoneNumber(for:)` при несовпадении с `^L(\d{2})S(\d{2})$` молча `else { return 0 }`; `transition` пишет этот 0 в `gameState.zone`, а `isStageStart = [0, 25, 50, 75, 100].contains(gameState.zone)` на 0 → true | некорректное `nextLevel` (например `L1S1`) → HUD «ZONE 000», ошибочный «stage start» → сброс переносимого Y; ни лога, ни ошибки | **Linux**: код |
| **GS-14** | **P3** | `GameScene.swift:1075-1076`, `:1024-1037` | `updateDebugOverlay()` вызывается каждый рисуемый кадр (`:141`) и начинает с `debugOverlay.removeAllChildren()`, пересоздавая `SKShapeNode`+`CGPath` на каждый terrain/solid/hitbox; узлы `createTeleportFlash` не состоят ни в одном массиве и живут только на `SKAction.removeFromParent()` | включить F1 на карте с сотнями rect → пересоздание сотен узлов каждый кадр (просадка FPS); если в момент телепорта наступает пауза/контент-финиш (`:944-947`, `isPaused`), action замирает и кольцо остаётся висеть до снятия паузы | **Linux**: код. **macOS**: профилить с включённым F1 |
| **GS-15** | **P3** | `GameScene.swift:1058-1059` (+ `PlayerSpriteNode.swift:45-47`) | `syncPlayerNodePosition()` каждый кадр принудительно `playerNode.alpha = 1.0` с комментарием против «artificial alpha blinking» → 0.4 с post-death protection (`:333-334`) визуально ничем не обозначены; костюм — не вторая палитра, а `colorBlendFactor = 0.35` (cyan tint), помечен в коде как «Temporary visual cue» | умереть и встать: игрок не видит, что он неуязвим (в оригинале мигание — канал обратной связи); README обещает «original-visual pipeline» | **Linux**: код. **macOS**: оценить читаемость состояния |
| **GS-16** | **P3** | `GameScene.swift:660-667`, `:723-727` | `awardPoints` поднимает `highScore` **во время** игры и пишет его в `UserDefaults` на каждый новый максимум; `enterGameOver` повторяет то же (`if gameState.points > gameState.highScore`) — мёртвая ветка | любая серия попаданий: HUD/титул «HIGH SCORE» всегда равны текущему счёту, «прошлого рекорда» в рантайме не существует; до N записей defaults за секунду (в GS-01-фарме — 111 записей) | **Linux**: код |

---

## Подтверждение/опровержение чужих claims

### 1. B-03 «ферма очков в зоне 124» — **ПОДТВЕРЖДЕНО полностью, плюс уточнения**

Реальный конечный автомат (строки продукта):

1. `:308` `if !player.isDying { checkScreenExit() }` → `:610` `guard player.position.x > 510`.
2. `:612` `applyOriginalStageBoundaryIfNeeded(completedZone: gameState.zone)` — **бонус здесь**.
3. `:614-618` `guard !next.isEmpty, includedLevels.contains(next) else { enterContentComplete(nextLevelName: next); return }` — только после начисления.
4. `:738-741` `enterContentComplete` → `flowState = .contentComplete`, `saveCheckpoint()`, `setGameplayNodesPaused(true)`, `menuFireWasPressed = inputState.snapshot().fire` (защита от авто-продолжения при удержанном SPACE — её я проверил, она работает).
5. `:201-207` `case .contentComplete:` по одному нажатию → `:761-767 showTitleAfterContentComplete` → `flowState = .title`.
6. `:161-167` `case .title:` по одному нажатию → `:708-717 beginFromTitle`, где из «новой игры» есть только `flowState = .playing` и `setGameplayNodesPaused(false)`.
7. Следующий фикс. шаг: `:209` (`case .playing, .playerDead, .respawning: break`) → снова `:308` → `:610` → **снова бонус** (позиция `player.position.x` не менялась: `beginFromTitle` не зовёт `player.configure`, а кламп `Player.swift:128` держит x до 544, т.е. >510).

Что именно перевначисляется за цикл (`:626-630`): `points += lives*1000` (потолок `min(999_999, …)` в `:662`), `lives += 1` до 9, `ammo = 99`, `grenades = 10`, плюс `saveCheckpoint()` (`:740`) и запись high score (`:663-665`).

Измерено репликой (Linux, Swift 6.4):

```
after first crossing: zone=124 points=9000 lives=9 flow=contentComplete title='CONTINUE · ZONE 124' x=510
  cycle 1:   points=18000  highScore=18000  lives=9 ammo=99 grenades=10 flow=contentComplete checkpointWrites=2
  cycle 100: points=909000 highScore=909000 lives=9 ammo=99 grenades=10 flow=contentComplete checkpointWrites=101
FARM: 111 bonus cycles (222 SPACE presses) added 990999 points; final points=999999, persisted high score=999999
```

Уточнения к исходной формулировке B-03: (а) накопление идёт **не** «на каждое нажатие», а на
каждые два (титул требует отдельного нажатия) — 4 фикс. шага на цикл; (б) цикл физически упирается
в потолок 999 999, но потолок этот **персистентен**, а кнопки сброса рекорда в продукте нет;
(в) фарм работает и как «бесплатный continue» — жизни и боезапас восстанавливаются до максимума,
так что game over на 124 зоне недостижим; (г) цикл достижим **только** в 124: `enterContentComplete`
больше неоткуда вызвать (см. п.4 ниже), поэтому «ферма на 24/49/74/99» неверна — там бонус
начисляется ровно один раз и сразу гасится `transition`.

### 2. B-05 «CONTINUE лжёт» — **ПОДТВЕРЖДЕНО (write-only чекпоинт), но оговорка про «ложь»**

Состояние, которое пишется и никогда не читается: `GameCheckpoint(levelName:ammo:grenades:points:lives)`
(`GameState.swift:18-24`), пируется `saveCheckpoint` (`GameScene.swift:696-705`) из 5 мест
(`:335`, `:657`, `:716`, `:740`, `:985`) и 6 ключами `Exolon.Step10.*`. Читатель `loadCheckpoint()`
(`GameState.swift:40`) не вызван ни разу. Более того, `:690 persistence.clearCheckpoint()`
в `loadPersistentState` затирает запись **до** любой попытки чтения — то есть даже будущий
`beginFromTitle`, захоти он продолжить, ничего бы не нашёл.

Оговорка: сам текст надписи честен в рамках процесса — `hasSavedCheckpoint == true` бывает только
после записи в этой же сессии, а на холодном старте (`:691 hasSavedCheckpoint = false`) титул всегда
«NEW GAME · ZONE 000». Ложь не в строке, а в обещании: «CONTINUE» на титуле, который физически не
может продолжить после перезапуска, и `GameCheckpoint` без полей `position.y`/`hasExoskeleton`,
так что «продолжить» даже после починки чтения было бы неполным.

### 3. O5 «частичный бонус стадии + вращающийся dormant-комментарий» — **ПОДТВЕРЖДЕНО, расширено до P1**

Комментарий `:623-625`:

> `// Our current content is still being extended through Step 9, so this is deliberately dormant`
> `// until later steps add Zones 024/049/074/099/124.`

Факт: `L01S25/L02S25/L03S25/L04S25` имеют `nextLevel` (`L02S01`, `L03S01`, `L04S01`, `L05S01`),
`L05S25` — не имеет; все 125 файлов есть в бандле и в resources-фазе. Значит `:626`
`guard [24, 49, 74, 99, 124].contains(completedZone) else { return }` **проходит** и код жив.
Недостающие правила нормы (`ORIGINAL_MECHANICS.md:140-145`): bravery 10 000 при отсутствии костюма,
timed bonus 0/1000/3000/5000/7000, и «Clear exoskeleton». Последнее — не косметика: `setExoskeleton`
в продукте вызывается один раз (`GameScene.swift:963`), поэтому взятый в 009 костюм даёт иммунитет
к минам и поршням (`:546`, `:557`) до конца игры, вопреки `:117`.

### 4. F1 «после 124 титул не начинает новую игру» — **ПОДТВЕРЖДЕНО**; сравнение путей по полям

| Поле/действия | `restartFromBeginning` (`:950-986`) | `beginFromTitle` (`:708-717`) |
| --- | --- | --- |
| `persistence.clearCheckpoint()` | ✓ `:951` | ✗ (`:716` при `!hasSavedCheckpoint` ещё и пишет) |
| `hasSavedCheckpoint = false` | ✓ `:952` | ✗ |
| `clearTransientObjects()` | ✓ `:953` | ✗ (пули/гранаты/осколки переходят в «новую игру») |
| уровень/`currentLevel` | ✓ пересоздан на `L01S01` `:955-958` | ✗ (остаётся 124) |
| `gameState.resetForNewGame()` (ammo/grenades/points/lives/zone) | ✓ `:960` | ✗ |
| `gameState.highScore = persistence.loadHighScore()` | ✓ `:961` | ✗ |
| `player.setExoskeleton(false)` | ✓ `:963` | ✗ |
| `player.configure(spawnCenter:)` → `respawn()` (позиция) | ✓ `:964` | ✗ (игрок остаётся стоять за x=510) |
| `playerNode.update(from:dt:0)` | ✓ `:965` | ✗ |
| `invulnerability = 0`, `deathGroundTimer = 0` | ✓ `:966-967` | ✗ (значения и так 0, но не обнуляются) |
| `stateBeforePause = .playing` | ✓ `:969` | ✗ |
| `stepLabel.text = …ZONE 000` | ✓ `:984` | ✗ (остаётся текст старой зоны) |
| скрытие оверлеев + `setGameplayNodesPaused(false)` | ✓ `:972-975` | частично (`:709`, `:711`) |
| латчи входа (`fire/grenade/jump/menuFire/debugWasPressed`) | ✓ `:976-983` | только 4 из них (`:712-715`, `debugWasPressed` не трогается) |

Вывод: `beginFromTitle` — это **resume**. Для холодного старта он корректен (вся сцена только что
создана и уже в «зоне 0»), но после `FULL COMBAT ABILITY` тот же самый оверлей с надписью
`SPACE / □ — START` (`:852`) ничего не начинает, а продолжает — отсюда GS-01.

### 5. Матрица утверждений README (Step 9) против этого файла

| Утверждение README | Код | Статус |
| --- | --- | --- |
| «pistons are lethal when exposed (unless test Invulnerability is ON)» | `:556-565` шлюз `if box.width > 0, invulnerability <= 0, !player.isDying, player.damageHitbox.intersects(box)`; `.zero` при скрытом поршне (`LevelObstacles.swift:341-345`); `:602` `guard !testInvulnerabilityEnabled else { return }` | **выполнено** |
| «pressing UP inside the changing room toggles Exoskeleton mode» | `:229-235` | **выполнено для клавиатуры/D-pad**; не выполнено для стика (GS-05); срабатывает по касанию, а не по «aligned» (GS-04) |
| «Exoskeleton fires a double blaster» | `:346-350` (второй снаряд на +12 px) | **выполнено**; расход — 1 патрон на 2 снаряда (`:351`), что нормой не оговорено |
| «protects against mines/pistons» | `:546`, `:557` (`continue` до проверки) | **выполнено**, но иммунитет не снимается на границе стадии (GS-02) |
| «Restart/new session resets Exoskeleton» | `:963` + дефолт `Player.swift:26` | **выполнено для Restart**; «new session» — тоже (свежий `Player`), а вот «title после 124» — нет (GS-01) |
| «every application launch still starts from Zone 000» | `:689-693` (`clearCheckpoint`, `currentLevelName = "L01S01"`, `resetForNewGame`) + `:59-60`, `:116` | **выполнено** |
| «High Score persists» | `:689` чтение, `:665`/`:726` запись | **выполнено** — и ровно поэтому GS-01 опасен: фарм пишет рекорд на диск навсегда |
| «UP … cannot become an accidental jump on the following fixed step» (rebase cabin fix) | `:231`, `:238/:244`, `:251-252`, `:255-258` | **выполнено в пределах шага**; через границу экрана — нет (GS-11) |
| «rectangle-object coordinate conversion is explicit» / «collision exclusion by object type» | не этот файл (`TMXLevelRuntime`); `GameScene` только потребляет `changingRooms` | вне лейна |

### 6. Мелочи, которые я проверил и которые **не** являются дефектами

- `fatalError`/force-unwrap: в `GameScene` единственный IUO — `currentLevel` (`:11`), инициализируется
  в `didMove` до первого `update`; `childNode(withName:)` везде через `as?`/optional-chaining;
  `zoneNumber` — `try?` с фолбэком. Индексации без guard нет (`teleportDestination` закрыт
  `guard portals.count >= 2` в `TMXLevelRuntime.swift:227`).
- Утечки узлов: `ExplosionEffect.fixedUpdate` и `GrenadeTrailDot.fixedUpdate` зовут
  `removeFromParent()` на завершении; `clearTransientObjects` (`:999-1010`) вызывается в
  `transition` и `restartFromBeginning` — массивов-кладбищ нет. Исключение — только `createTeleportFlash` (GS-14).
- «Спираль смерти» аккумулятора: `:129` `min(currentTime - previousUpdateTime, GameConstants.maximumFrameTime)`
  при 0.25 s и шаге 1/60 даёт ≤15 шагов на кадр — ограничено, не расходится.
- Пауза не «крутит» `invulnerability` (`:213` находится после `return` всех оверлейных веток) — корректно.
- `bannerLabel`-экшены захвачены `[weak self]` (`:676`) — циклов удержания нет.
- Смерть не зависает: `beginDeath` (`Player.swift:218-225`) подбрасывает и гасит `isGrounded`,
  а `landOnFallbackFloorIfNeeded` (`Player.swift:291-297`) гарантированно ставит на fallback-плоскость,
  так что `:313-316` (`guard player.isGrounded`) в конечном счёте проходит и `.playerDead`
  не может стать вечным состоянием.

---

## Что проверить на macOS

1. **GS-01/B-03 (главное):** дойти до 124 → `FULL COMBAT ABILITY` → SPACE → SPACE и
   **зафиксировать** рост счёта; затем убедиться, что 999 999 пережили перезапуск приложения,
   и что жизни/патроны восстановились. Проверить и обратное: что после GAME OVER (там ветка
   `:193-199 → restartFromBeginning`) рекорд НЕ фармится.
2. **GS-02:** в 009 взять костюм и пройти границу 024 → костюм остаётся (ожидание нормы — снят);
   bravery-бонус 10 000 и timed-курсор отсутствуют; сравнить счёт на 124 «в костюме» и «без».
3. **GS-04:** в 009 встать на ~345–423 px по X у кабины и нажать UP (хотели прыжок) — зафиксировать
   переключение костюма вместо прыжка; в 034/060/090/109 — то же в окне 126 px.
4. **GS-05:** на геймпаде: кабина (009) и пара телепортов (002) аналоговым стиком вверх.
5. **GS-06:** TEST INVULNERABILITY ON → пройти сквозь мины 007, guided-ракету 008, пузырь/яйцо;
   зафиксировать исчезновение объектов и начисление очков без смерти.
6. **GS-10/GS-11:** P во время смерти (нет паузы) и удержанный UP при переходе экрана (лишний прыжок).
7. **GS-14/GS-15:** F1 на L05S25 — FPS; визуальная читаемость 0.4 с защиты после смерти.
8. **Тайминг оверлеев:** удержание SPACE на `CONTENT COMPLETE`/`GAME OVER` — двойного авто-перехода
   быть не должно (латчи `:758` и `:735`); проверить и на геймпаде (□).

**Вердикт: fail** — в модуле есть два P1-дефекта (GS-01 фарм/отсутствие «новой игры» на титуле,
GS-02 недоделанный бонус стадии с неснимаемым костюмом и вращающимся комментарием), которые не
ловятся ни одним существующим гейтом: `scripts/grok_verify.py` → `.grok-stack/adaptive_grok/verification.py`
не содержит ни `swift`, ни `xcodebuild`, а `Exolon.xcodeproj` не содержит ни одного test-таргета
(единственный `PBXNativeTarget` — `Exolon`), то есть весь модуль проверяется только ручным чтением
и игрой на macOS.
