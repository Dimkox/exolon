# Per-file аудит: Player + Input (HEAD 52795d1)

Лейн: `Exolon/GameCore/Player/Player.swift` (313), `Exolon/GameCore/Player/PlayerSpriteNode.swift` (81),
`Exolon/GameCore/InputState.swift` (109), `Exolon/Platform/macOS/GamepadInput.swift` (105).
Прочитано дополнительно, только чтобы проверить утверждения (не объект оценки):
`GameCore/GameScene.swift:118-290, 605-675, 905-1000`, `GameCore/GameConstants.swift`,
`GameCore/Levels/TMXLevelRuntime.swift:49-135`, `GameCore/Levels/TMXMapLoader.swift:304-343`,
`GameCore/Levels/TMXTileMapRenderer.swift:115-151`, `Platform/macOS/GameView.swift`, `Platform/macOS/AppDelegate.swift`,
`Exolon/main.swift`, `README.md`, 125 `.tmx` из `Exolon/Resources/`.

## Итог

Метод, кроме чтения: на этом Linux-хосте есть Swift 6.4 (`/opt/swift/usr/bin/swiftc`), поэтому `Player.swift`,
`InputState.swift`, `GameConstants.swift` **скомпилированы без правок** (замена `import CoreGraphics` → `import Foundation`
+ шим `CGVector`) в исполняемый стенд `/tmp/perfile-player/src*/main.swift`, который воспроизводит срез
`GameScene.fixedUpdate` (snapshot → consumePause → edge jump → cabin/teleport → synthesized snapshot →
`player.update` → цикл `resolveSolidCollision` → `refreshGroundSupport` → `finalizeMotionState`) дословно.
Все числа ниже — из прогонов, а не из чтения. Дополнительно: независимое измерение 125 карт (реплика `buildCollisionRects`
+ `worldBottomLeft` + `min(rect.maxY)` на Python).

Три следствия, которые меняют картину предыдущих аудитов:

1. **Заявка README про «consumed UP» не выполнена.** Двойной toggle действительно невозможен (это делает
   `sceneJumpWasPressed`, `GameScene.swift:216-217`), а вот «не может стать случайным прыжком на следующем
   фиксированном шаге» — **нарушено**: `Player.swift:115` безусловно пишет `jumpWasPressed = input.jump`, причём
   в том же `update()`, которому `GameScene.swift:249-258` подсунул `jump: false`. Замок, выставленный
   `consumeContextualJumpPress()` (`Player.swift:256-258`), уничтожается в том же шаге → на следующем шаге
   физически удерживаемый UP даёт настоящий прыжок. Замер: подъём **26.65 px** (control без кабины — 28.00 px,
   та же дуга), минимальная правка (отдавать реальный бит `jump`, оставив замок) — **0.00 px**.
2. **Правило опоры выведено точно, и у него есть мёртвая зона 1.0–1.5 px**, в которой игрок «на земле», но
   де-пenetрации нет, а deep-overlap ветка `resolveSolidCollision` каждый шаг откатывает `position.x` назад →
   горизонталь блокируется навсегда (спасает только прыжок). Это воспроизводится на **реальной геометрии
   L01S09**: 20 шагов удерживания RIGHT → смещение **0.00 px**; после прыжка → +51 px.
3. **B-01/B-02 уточнены по числам:** из 125 карт ровно **35** дают опору прямо в точке спавна, **59** поднимают
   игрока на **+16 px** (одна тайловая строка) на первом же шаге, **29** роняют на **−16 px** на невидимую
   плоскость, **2** оставляют стоять на самой плоскости (Δ=0). То есть «±16 px» подтверждается как величина
   (|max = 16 px, больше нигде), но «1 карта с подъёмом» в `fullaudit-b01-spawn.json` (`16_above`: 1) — занижение:
   подъёмов 59.

Сайдбар про платформу: `CGRect.intersects` в swift-corelibs-foundation (Linux) считает касающимися
пересекающимися (`feet == solid.maxY` → `intersects == true`), а по документации Apple (https://developer.apple.com/documentation/coregraphics/cgrectintersectsrect(_:_:))
и подтверждённому SO-кейсу (https://stackoverflow.com/questions/25373752) на Darwin касание ребром **не** является пересечением. Значит часть «замирания ходьбы» на Linux — артефакт
семантики, и на macOS её обязана подтвердить/опровергнуть проверка №1 чек-листа ниже. Все находки с
приоритетом P1 намеренно сформулированы так, чтобы **не** зависеть от этого различия (перекрытия > 1 px).

## Таблица находок

| ID | Pri | Файл:строка | Поведение (цитата) | Триггер | Ожидание (оригинал/README) vs Факт | Тип |
|----|-----|-------------|--------------------|---------|-------------------------------------|-----|
| **PI-01** | **P1** | `Player.swift:110-115` + `GameScene.swift:243-258` | `jumpWasPressed = input.jump` (безусловно, в конце `update`) после `player.consumeContextualJumpPress()` и подачи `InputSnapshot(jump: false)` | UP удержан ≥ 1 фикс. шаг (≥16.7 мс — любое «человеческое» нажатие) внутри кабины/телепорта | README: «UP … **cannot become an accidental jump on the following fixed step**». Факт: на следующем шаге — полный прыжок, **замер +26.65 px** (control 28.00 px; фикс-вариант с реальным битом — 0.00 px) | Linux-static (исполняемо воспроизведено) + macOS-play |
| **PI-02** | **P1** | `Player.swift:207-214` (`teleport` сам ставит `jumpWasPressed = true`) + тот же корень, что PI-01 | `position = center; velocity = .zero; isGrounded = true; jumpWasPressed = true` | UP удержан на входе в телепорт | Оригинал: телепорт — мгновенный перенос без движения. Факт: в точке прибытия Виторc **подпрыгивает** (замер: y 232→252 за 10 шагов), то есть входит в hazard/портал-приём с смещением по вертикали | Linux-static (исполняемо) + macOS-play |
| **PI-03** | **P1** | `Player.swift:173-176` (`else if !isDying { position.x = previousPosition.x; velocity.dx = 0 }`) | deep-overlap ветка откатывает x и обнуляет dx; вертикальной де-пенетрации нет вообще | бокс игрока пересекает solid с заходом **> 1.5 px** и при этом `previousBox.minY < solid.maxY - 1.0` (спавн «в полу», snap-up, carried-Y-вход, кривой teleport-destination) | Оригинал: спавн стоит на полу и ходит. Факт: **горизаль заблокирована насовсем**. Реальные данные L01S09 (zone 008): `solids=[0..304]×[64..80]`, feet=64 → заход 16 px; 20 шагов RIGHT → **Δx=0.00**; после прыжка Δx=+51. По 125 картам: **61 карта** имеет в точке покоя перекрытие > 1.5 px | Linux-static (исполняемо, реальные rect'ы) + macOS-play |
| **PI-04** | **P2** | `Player.swift:173-176` vs `Player.swift:144-146` (`previousBox.minY >= solid.maxY - 1.0`) vs `Player.swift:191-193` (`abs(solid.maxY - footY) <= 1.5`) | допуски 1.0 px (посадка) и 1.5 px (опора) не совпадают | заход по вертикали в интервале **(1.0, 1.5] px** | Ожидание: один допуск и восстановимое состояние. Факт (замер D4, feet=238.5 при top=240): `isGrounded` остаётся `true` (гравитации нет), посадочная ветка не срабатывает → x откатывается каждый шаг, **Δx=0.00 за 10 шагов**, вечный пин | Linux-static (исполняемо) |
| **PI-05** | **P2** | `InputState.swift:38-50, 84-108` (только текущее «удерживается», без очереди/замока) + `GameScene.swift:149` (сэмпл один раз за шаг) | `snapshot()` = объединение `pressedBySource`; `set(…, pressed:false)` стирает событие | нажатие и отпускание попадают в один интервал между двумя фикс. шагами | Ожидание: ни один ввод не теряется. Факт (замер S8): `jump` press+release внутри окна → `snapshot.jump == false`, нажатие **потеряно**; единственный замок — `pausePressPending` (`InputState.swift:35-45, 66-73`) | Linux-static (исполняемо) |
| **PI-06** | **P2** | `Gameview` → `InputState.swift:57-61` + `GamepadInput.swift:41-44` | `windowDidResignKey` → `inputState?.reset(source: .keyboard)`; геймпад-источники и `pausePressPending` не чистятся; `resetGamepad()` — только на `GCControllerDidDisconnect` | alt-tab / потеря фокуса при удержанном d-pad/stick/кнопке | Ожидание: при потере фокуса весь ввод сбрасывается. Факт (замер S9): после resign `moveRight(stick)=true`, `consumePausePress()=true` (игра сама встанет на паузе после возврата); `InputState.resetAll()` — **никого не имеет** (dead code) | Linux-static + macOS-play |
| **PI-07** | **P2** | `GamepadInput.swift:64-72` (строка **:71**: `self.inputState.set(.menuUp, pressed: y > 0.65, source: .gamepadStick)`) | stick UP даёт только `.menuUp`; `.jump` — только d-pad (`:59-61`) и Cross (`:77-79`) | левый стик вверх | README: «pressing **UP** inside the changing room toggles Exoskeleton». Факт: стиком — ни кабины, ни телепорта, ни прыжка; только навигация меню паузы (C5 подтверждён построчно) | Linux-static |
| **PI-08** | **P2** | `GamepadInput.swift:87-91`, `:47` | `controller.controllerPausedHandler = { set(.pause, true); set(.pause, false) }`; `guard let gamepad = controller.extendedGamepad else { return }` | геймпад без `extendedGamepad`; кнопки Select/Back/Guide; F1-only для отладки | Ожидание (I1): пауза/опции доступны с геймпада. Факт: **достигнуемо** — Options/Start/+ → пауза и снятие (через `pausePressPending`), навигация меню — d-pad/stik, подтверждение — buttonX/Space. **Недостижимо** — `debugHitboxes` (только клавиатурная F1), любая «отмена» (`buttonMenu` не замаплен), пауза-меню на падах без extended-профиля (такие вообще молчат: `configure` выходит по guard, статус-лейбл показывает «waiting») | Linux-static + macOS-play |
| **PI-09** | **P3** | `Player.swift:291-297` | `if position.y <= standingCenterY { position.y = standingCenterY; … }` — телепорт без интерполяции и без учёта того, что в целевом боксе уже стоит solid | спавн/падение ниже плоскости; плоскость = `min(rect.maxY)` по **всей** карте, включая погребённые строки | Факт (59 карт): мгновенный **lift +16 px**; он же — причина вхождения в PI-03 (тот же шаг: `previousPosition` = дo-snap, поэтому приземление не распознаётся) | Linux-static + данные 125 карт |
| **PI-10** | **P3** | `GameScene.swift:167-193` (`flowState == .paused`) + `Player.swift:110-115` | во время паузы `fixedUpdate` выходит раньше, чем читается jump; `.pause` из снапшота никто не читает | пауза, удержанный UP | Ожидание: снятие паузы не должно стрелять прыжком — и не стреляет: `leavePause` синхронизирует `sceneJumpWasPressed`/`fireWasPressed`/`grenadeWasPressed` (`GameScene.swift:930-944`) ✓. Побочно: `InputSnapshot.pause` — мёртвое поле | Linux-static |
| **PI-11** | **P3** | `GameScene.swift:120-136` | `let frameTime = min(currentTime - previousUpdateTime, GameConstants.maximumFrameTime)` — нижней отсечки нет | возврат/пересборка таймбейзы (`currentTime` меньше предыдущего) | Ожидание: `max(0, …)`. Факт (замер S10): `accumulator = -0.5` → **45 кадров подряд с нулём фиксированных шагов** (игра стоит, пока долг не выберется) | Linux-static (исполняемо) |
| **PI-12** | **P3** | `Player.swift:126-128` | `position.x = min(max(position.x, visualHalfWidth), GameConstants.logicalSize.width + 32)` | удержание RIGHT у краёв | Слева зажим по ширине **спрайта** (24) при коллайдере 23 ✓ (как в комментарии); справа — 544, т.е. 32 px за краем карты, а переход срабатывает при x>510 → ~34 px «офскрин-прогулки» | Linux-static |
| **PI-13** | **P3** | `PlayerSpriteNode.swift:4-6, 19-31` | `frameCount = 11`, `frameSize = CGSize(48, 64)` продублированы из `GameConstants.playerSpriteSize`; `SKTexture(imageNamed: "vitorc")` без проверки | переименование ресурса / правка `playerSpriteSize` | Проверено: `Exolon/Resources/vitorc.png` = **528×64 = 11×48** ✓, значит `SKTexture(rect:in:)` сегодня корректен (одна строка → нет проблемы с флипом Y). Риск: при отсутствии ассета `imageNamed` не крэшится, а даёт пустую текстуру → невидимый Виторc без единого сообщения | Linux-static |
| **PI-14** | **P3** | `PlayerSpriteNode.swift:43-60` | сброс `animationIndex = 0` при каждой смене `displayedState`; `while animationTimer >= runFrameDuration` | прыжок→бег, присед→бег | Цикл ходьбы перезапускается с кадра 0 после любого перехода (косметика оригинала не подтверждена); `runSequence` включает кадры 3 и 8 (jump/fall) — ровно как в комментарии про HTML5-ремейк ✓; индексы ≤10 в границах ✓ | Linux-static |
| **PI-15** | **P3** | `GameScene.swift:246-258` | вручную сконструированный `InputSnapshot(moveLeft: …, debugHitboxes: …)` из 10 полей | добавление нового `GameAction` | Новое поле молча станет `false` в «consumed»-ветке. Отдельно ✓: `finalizeMotionState(input: playerInput)` получает **тот же** синтетический снапшот, поэтому `crouch` не рассинхронизируется | Linux-static |
| **PI-16** | **P3** | `GameScene.swift:653-654, 735, 758, 1063` | повторные `inputState.snapshot()` вне единственного сэмпла шага (и по кадру в `updateDebugText`) | переход зоны / заголовок / отладочный HUD | Один логический шаг снимает состояние 2–3 раза; debug-строка может показать биты, которые симуляция никогда не видела. Функционально на macOS безвредно (тот же поток), но ломает модель «один сэмпл на шаг» | Linux-static |
| **PI-17** | **P3** | `GameScene.swift:233-241` | триггер кабины/телепорта = `movementHitbox.intersects(rect)` без требования `isGrounded` | стойка/пролёт рядом с будкой 32×80 | collider 46 широкий → UP съедается будкой с расстояния до ~23 px по X; toggle возможен в воздухе (замер S7b: второй toggle на fell-фазе, `grounded=false`). Для zone 009 с exclusion-полем это означает «кабина ловит UP почти у половины экрана» | Linux-static + macOS-play |
| **PI-18** | **P3** | `GamepadInput.swift:41-44` | `controllerDidDisconnect` → `inputState.resetGamepad()` без разбора, какой пад отвалился | два геймпада | Отключение одного чистит held-биты второго (само-восстановление на следующем событии) | Linux-static |
| **PI-19** | **P3** | `Player.swift:182-183`, `:243-249` | `refreshGroundSupport` имеет `guard isGrounded else { return }` → никогда не «заземляет» | solid, появившийся под ногами (поршень/силовое поле) | Ожидание: приземление на вновь появившуюся платформу. Факт: только `resolveSolidCollision`/fallback-snap ставят `isGrounded = true`; «впередишагивания» нет. Плюс стой на турели/разрушаемом блоке разрешены (они в `solidRects`) и легальны | Linux-static |

### Что измерено и признано корректным (анти-находки, чтобы не перепроверять)

* **Однократный toggle при удержании UP** — 40 шагов удержания → `toggles=1`; отпускание+нажатие → `toggles=1` (OFF). Пункт 2 macOS-чеклиста («holding → no repeat toggle») выполняется.
* **Авто-прыжок при удержании jump отсутствует** (100 шагов → один подъём, apex 36.45 px).
* **Присед не меняет уровень ног** (`movementHitbox.minY` stand==crouch == 100.0), `damageHitbox` 49 px — как задкументировано.
* **Туннелирования нет**: терминальная скорость −300 px/s → максимум **5.0 px/шаг** < 16 px тайла; платформа 16 px всегда ловит (замер S13).
* **`set(true)`/`set(false)` разных источников не перекрываются** (union по `InputSource` корректен, d-pad down + отпущенный стик → `crouch=true`).
* **Костюм**: `respawn()`/`finishDeathAndRespawn()` его не снимают ✓ (README: сброс только на restart, `GameScene.swift:963`); `toggleExoskeleton()` под `guard !isDying` ✓, а `setExoskeleton(_:)` — **нет** (замер T8), что сегодня безопасно, потому что внешних вызовов во время смерти нет.
* `beginDeath()` выставляет `jumpWasPressed = false`, так что после воскрешения удержанный UP сам не прыгает ✓.
* Смерть/респавн/`teleport` не ломают `facing`, `motionState` ✓; `teleport` во время смерти — guarded (замер T8: тело не сдвинулось).
* `deinit`/`removeObserver`, `[weak self]` во всех handler'ах, слабый `scene` — утечек и форс-анрапов в четырёх файлах **нет** (единственный `fatalError` — стандартный `init(coder:)`).

## Матрица маппинга ввода

Канал: `NSEvent`/`GCController` → `InputState.set(action, pressed, source)` → `snapshot()` один раз на фикс. шаг
(`GameScene.swift:149`, 60 Гц, `maximumFrameTime = 0.25` → до 15 шагов «догона» на одном кадре) → edge-замки
уровня сцены (`sceneJumpWasPressed`, `fireWasPressed`, `grenadeWasPressed`, `pauseMenu*WasPressed`) и уровня
игрока (`Player.jumpWasPressed`).

| Действие | Source | Клавиатура (`GameView.swift`) | D-pad (`:49-62`) | Левый стик (`:64-72`) | Кнопки (`:77-91`) | Тип срабатывания |
|---|---|---|---|---|---|---|
| `moveLeft` | keyboard / gamepadDPad / gamepadStick | ← (123) | left | `x < −0.35` | — | level + сценный edge только в меню |
| `moveRight` | keyboard / gamepadDPad / gamepadStick | → (124) | right | `x > 0.35` | — | level |
| `jump` | keyboard / gamepadDPad / gamepadButtons | ↑ (126) | **up** | **— (нет!)** | **A/Cross** | level-бит + edge в `Player` и в `GameScene` |
| `crouch` | keyboard / gamepadDPad / gamepadStick | ↓ (125) | down | `y < −0.65` | — | level |
| `fire` | keyboard / gamepadButtons | Space (49) | — | — | X/Square | level + edge `fireWasPressed` |
| `grenade` | keyboard / gamepadButtons | Option (58/61) через `flagsChanged` | — | — | B/Circle | level + edge `grenadeWasPressed` |
| `pause` | keyboard / gamepadButtons | P (35) | — | — | **`controllerPausedHandler`** (Options/Start/+) | **edge-замок `pausePressPending`** (уникальный латч на всю систему) |
| `menuUp` | keyboard / gamepadDPad / gamepadStick | ↑ | up | `y > 0.65` | — | level + edge в `.paused` |
| `menuDown` | keyboard / gamepadDPad / gamepadStick | ↓ | down | `y < −0.65` | — | level + edge в `.paused` |
| `debugHitboxes` | keyboard | **F1 (122)** | — | — | — | level + edge `debugWasPressed`; с геймпада недоступно |
| contextual UP (кабина/телепорт) | — | ↑ | up | **✗** (`GameScene` читает `rawInput.jump`, стик его не ставит) | Cross | edge `jumpJustPressed` → `consumedUpInteraction` (см. PI-01) |
| выход из приложения | — | ✗ (нет main menu: `main.swift` не задаёт `NSApp.mainMenu`; `keyDown` не вызывает `super`) | ✗ | ✗ | ✗ | единственный способ — крестик окна (`applicationShouldTerminateAfterLastWindowClosed == true`) |

Память источников: `pressedBySource: [InputSource: Set<GameAction>]` — три геймпад-источника разделены намеренно
и это правильно (один источник не «крадёт» бит у другого), но `resetAll()` не вызывается нигде, а
`resetGamepad()` привязан только к дисконнекту.

## Заявки README ↔ код

| Заявка (README) | Код | Статус |
|---|---|---|
| «UP inside a changing room/teleport is **consumed** as a contextual action and **cannot become an accidental jump on the following fixed step**» | `GameScene.swift:243-258` (`consumedUpInteraction`, `consumeContextualJumpPress`, синтетический `InputSnapshot(jump:false)`) + `Player.swift:113` | **НАРУШЕНО (PI-01/PI-02)**. Same-step — съедается корректно; following-step — прыжок 26.65 px при удержанном UP. Предыдущий вердикт «ПОДТВЕРЖДЕНО» (`analysis-docs_researcher-fullaudit.md:110`) верен только для double-toggle |
| «pressing UP inside the changing room **toggles** Exoskeleton mode» | `GameScene.swift:233-238` → `Player.swift:243-246` | **ПОДТВЕРЖДЕНО для ↑/d-pad/Cross; НАРУШЕНО для стика (PI-07)**; плюс toggle срабатывает по всему 46×63 боксу и в воздухе (PI-17) |
| «holding → no repeat toggle» (чеклист macOS, item 2) | `GameScene.swift:216-217` (`sceneJumpWasPressed`) | **ПОДТВЕРЖДЕНО измерением**: 40 шагов удержания → 1 toggle |
| «Exoskeleton fires a double blaster and protects against mines/pistons» | `GameScene.swift:346-350, 546, 557` (вне моих файлов, проверено только наличие) | **ПОДТВЕРЖДЕНО** (чужой лейн) |
| «Restart/new session resets Exoskeleton» | `GameScene.swift:963` | **ПОДТВЕРЖДЕНО**: сброс есть; смерть (`respawn`) и смена зоны (`transition`) костюм сохраняют — это согласуется с README и с `Player` (нет хука стадии; `setExoskeleton` неguarded по `isDying`) |
| «keeps the existing 125-zone project and **original-visual** pipeline» | `PlayerSpriteNode.swift:45-46` (cyan-тинт вместо кадров экзоскелета) | **ОТКЛОНЕНИЕ задокументировано в коде** («Temporary visual cue»), но не в README (PI-14 смежно) |
| «every application launch still starts from Zone 000» | `didMove(to:)` → `currentLevelName = "L01S01"` | **ПОДТВЕРЖДЕНО**; на паузе Restart → `restartFromBeginning` тоже L01S01, и он единственный снимает костюм |
| «pistons are lethal when exposed (unless test Invulnerability is ON)» | `testInvulnerabilityEnabled` (`GameScene.swift:189-192`), `invulnerability` в сцене | Вне моих файлов; в `Player` поля неуязвимости **нет** — единственное место состояния — `GameScene.invulnerability`, и `transition()` обнуляет его (спорно, но не мой файл) |

## Что проверить на macOS

Порядок = по ценности. Первые пять пунктов — это то, что Linux-стенд принципиально не может решить.

1. **Ходьба по плоскому полу, зона 000 (L01S01).** Зажать RIGHT на 0.5 с → ожидание +45 px/30 шагов. На Linux
   (swift-corelibs `CGRect.intersects`: касание = пересечение) игрок **не двигается вообще** (замер C1/D2:
   `Δx=0.00`, `touches=[true]`), на Darwin касание рёбер пересечением не считается. Если на macOS ходьба
   ломается — это P0 и причина ровно в связке «feet == solid.maxY → ни одна из трёх веток не подходит →
   else-branch откатывает x».
2. **Спавн в зоне 008 (L01S09): зажать RIGHT, не отпуская.** Предсказание (из реальных rect'ов карты): **игрок
   не двигается**; затем один UP → он «вспрыгивает» сквозь пол (за 40 шагов +51 px) и после приземления на
   реальные 80 px ходьба работает. Это PI-03. Повторить на любой из 61 карты с заходом > 1.5 px (список
   формируется: L01S09, L01S11, L01S12, L01S13, L01S19, L01S20, …).
3. **Кабина, удержание UP (≥50 мс) — клавиатура, d-pad, Cross.** Ожидание по README: ровно один «EXOSKELETON
   ON» и **никакого прыжка**. Фактическое предсказание кода: через 1 шаг (≈16 мс) Виторc подпрыгнет (PI-01).
   Заодно проверить, что в момент прыжка он не утаскивает за собой toggle (повторного не будет ✓).
4. **Телепорт, удержание UP.** Проверить отсутствие «подскока» в точке прибытия (PI-02) и не убивает ли этот
   подскок на прибытии (hazard прямо под точкой телепорта).
5. **Мёртвая зона 1.0–1.5 px (PI-04).** Медленно подойти вплотную к краю уступа так, чтобы ноги встали на
   ~1 px ниже его верха (удобно делать у входа в кабину с exclusion-полем): проверить, не замирает ли x
   навсегда без возможности выйти (кроме прыжка).
6. **Потеря фокуса с зажатым вводом (PI-06).** Зажать d-pad RIGHT (и отдельно стик), alt-tab на 2 с, вернуться,
   отпустить. Ожидание: персонаж не бежит сам. Дополнительно: нажать Options/P **до** alt-tab и не отпускать —
   проверить самопроизвольную паузу после возвращения (`pausePressPending` переживает `reset(source:.keyboard)`).
7. **Cmd+Q (B-06).** Ожидание: ничего (ни `NSApp.mainMenu`, ни forwarding в `keyDown`); закрыть окно крестиком →
   приложение должно завершиться (`applicationShouldTerminateAfterLastWindowClosed`).
8. **C5 (PI-07): левый стик вверх** в кабине/на телепорте/на плоском полу — трижды убедиться, что ничего не
   происходит, а **стик вниз** приседает. Это документированный отказ, а не баг, но чеклист без него врёт.
9. **I1 (PI-08): Options → пауза → d-pad UP/DOWN → buttonX(Square) = Restart / Test Invulnerability.**
   Отдельно: воткнуть пад **без** `extendedGamepad` (дешёвые USB-джойпады, часть XInput-адаптеров) — экран
   «GAMEPAD: waiting / keyboard ready» и никакой реакции; и что Select/Back/Guide не делают ничего.
10. **Двойной нажатый за кадр ввод (PI-05).** Максимально коротко «отстучать» UP (быстрый тап ~10 мс) 20 раз у
    кабины: ожидаем пропуски toggles — это и есть потеря press+release внутри одного окна.
11. **Обратный ход времени (PI-11).** Увести игру в фон на 1–2 с и вернуть, затем deiconify/resize: если
    `currentTime` даст скачок назад, игра будет «стоять» десятки кадров. Фикс — `max(0, …)` и/или сброс
    `accumulator`.
12. **Визуал (PI-13/PI-14).** Проверить, что 11-кадровый лист (528×64) на Retina при `aspectFit` 1024×768 и
    `filteringMode = .nearest` не даёт срезов соседних кадров, и что цикл ходьбы не «дёргается» после каждого
    приземления (сброс `animationIndex = 0`).
13. **Отладочный оверлей.** F1 → hitbox'ы; убедиться, что `damageHitbox` 46×49 в приседе реально ниже
    `movementHitbox` 46×52 (заявка в `GameConstants.swift:24-31`), иначе «турель стреляет над головой» не
    подтверждена.

## Вердикт: fail

`PI-01`/`PI-02` — прямое нарушение явно сформулированной заявки README, воспроизведённое исполняемым прогоном
реального `Player.swift`; `PI-03` — блокировка ввода на спавне 61 карты из 125 (минимум zone 008) с измеренным
Δx = 0.00. Остальное (P2) чинится точечно: единый допуск 1.5 px + вертикальная де-пенетрация в deep-overlap
ветке, `max(0, frameTime)`, `resetAll()` на resign и `resetGamepad()`+`pausePressPending = false`, `.jump` со
стика.

---

Материалы проверки (одноразовые, вне дерева репозитория): `/tmp/perfile-player/src/` (раунд 1: S1–S15),
`/tmp/perfile-player/src2` (T-серия: кабина/телепорт/edge-touch), `src3` (C1–C5: батарея контроля ходьбы и
опоры в изоляции), `src4` (доказательство причины: вариант A vs минимальный фикс B), `src5` (D1–D4:
пенетрация 1.0/1.5/24 px), `src6` (реальная геометрия L01S09). Изменений в репозитории нет:
`git status --porcelain` по трекаемым файлам пуст.
