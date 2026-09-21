# Аудит ресурсов и бандла (assets/bundle lane)

HEAD `52795d1`, ветка `codex/factory-updated-20260920`. Только чтение репозитория;
все скрипты в `/tmp/perfile-assets/`. Объём: `Exolon/Resources/`,
`Exolon.xcodeproj/project.pbxproj` (членство в бандле), join имя-ресурса → Swift/TMX → диск.

## Итог

**Counts (проверено этим прогоном, `bash /tmp/perfile-assets/verify.sh`):**

| метрика | значение |
|---|---|
| `.tmx` в `Exolon/Resources/` | **125** |
| `.png` | **153** |
| `.gif` | **3** |
| `.plist` | 1 (`Info.plist`) |
| всего файлов | **282** |
| записей в `PBXResourcesBuildPhase` (уникальных имён) | **276** (= 552 строки в файле: объявление BuildFile + позиция в `files = (…)`) |
| из них `.png` / `.tmx` / `.gif` | 151 / 125 / **0** |
| подвешенных записей pbx → диск | **0** |
| файлов на диске вне Resources phase | **6** |
| `imageNamed:` — мест вызова | **23** |
| литералов прямо в `imageNamed:` (уникальных) | **17** |
| уникальных имён, достижимых из Swift (через переменные/хелперы) | **27** |
| уникальных имён, достижимых из TMX (stems) | **123** |
| всего уникальных lookup-имён (Swift ∪ TMX) | **150** |

**Целостность:** `pngcheck` — 153/153 OK; `xmllint` — 125/125 well-formed, 0 bad;
0 расхождений объявленного и фактического размера изображений; 0 gid вне ёмкости тайлсета;
0 рассогласований числа ячеек в слоях (138 слоёв: 128 `csv` + 10 `base64`).

**Главный вывод по V3:** ядро опровержения полночного аудита **верно** — дыры в бандле нет,
`RUNTIME_MISSING_RISK = 0`. Но **три составных утверждения §3 неверны** (см. таблицу),
и сам §3 пропустил реальный дефект контента: `L01S04.tmx` содержит 2 битых пути к изображению
тайлсета, а `generated_terrain.png` — отладковая заглушка, объявленная в 117 из 125 карт
и не рисующая **ни одного** тайла.

Join «имя → диск → pbx» замкнут: 125 имён карт из `includedLevels`
(`GameScene.swift:53`, `(1...5) × (1...25)` = 125) **точно** равны множеству 125 `.tmx`
на диске — ни отсутствующих, ни недостижимых. 20 имён TMX-объектов ↔ 20 `case` в
`TMXLevelRuntime.swift`, необработанных **0**.

## Таблица находок

| # | находка | severity | evidence (прогон этого прохода) |
|---|---|---|---|
| A-1 | §3: «настоящая дыра — GIF-анимация: декодера нет» — **опровергнуто**. Все 3 gif **однокадровые**, ни одной анимации терять нечем; и в бандл они не входят вообще | P3 (текст аудита) | `ffprobe -count_frames` → `bubble.gif 1`, `rocks.gif 1`, `turret_bullet.gif 1`; PIL `n_frames=1` на всех трёх; контроль `ctl10.gif` (ffmpeg, 2s@5fps) → корректно `nb_read_frames=10`, PIL 10 |
| A-2 | §3: «gif-имена только в комментариях кода» — **неверно как причина**. Точные имена с `.gif` действительно только в комментариях (2 упоминания: `LevelObstacles.swift:63,74`), но **стемы** gif — живые lookup-ключи: `SKTexture(imageNamed:"bubble")` (`:444`) и `"turret_bullet"` (`:138`) | P3 (текст аудита) | `grep -rn 'imageNamed:'` + `python3 /tmp/perfile-assets/final.py` → `SWIFT_DISTINCT_NAMES 27`, из них `bubble`, `turret_bullet` совпадают со стемами gif |
| A-3 | Спасение даёт **столкновение стема с включённым в бандл PNG**, а не «комментарийность». Стем-коллизии: `bubble`, `rocks`, `turret_bullet` — по 2 файла на одно имя | P3 | `ls \| sed -E 's/\.[^.]+$//' \| sort \| uniq -d` → `bubble rocks turret_bullet` (3 коллизии) |
| A-4 | **`L01S04.tmx:9,12` — 2 битых пути тайлсета: `../images/tiles.gif`, `../images/rocks.gif`. Ни каталога `images/`, ни этих файлов в репозитории нет.** Резолвятся только случайно: рендерер берёт stem без расширения (`TMXTileMapRenderer.swift:23-25,84-86`) и попадает в `tiles.png`/`rocks.png`. В Tiled/любом path-resolving загрузчике карта теряет оба тайлсета | **P2** | `python3 /tmp/perfile-assets/join2.py` → `REFS_ESCAPING_RESOURCES 2`, `REFS_NOT_RESOLVING_ON_DISK 2`; `grep -oh 'source="\.\./' *.tmx \| wc -l` → **2**; `find . -name tiles.gif` → пусто |
| A-5 | **`generated_terrain.png` — отладковая заглушка.** 16 тайлов чистыми цветами на чёрном: `(0,255,0)`, `(255,0,255)`, `(0,255,255)`, `(255,255,0)`, `(255,0,0)`, `(190,190,190)` — по 2 цвета на тайл. Объявлен тайлсетом в **117** из 125 карт (`firstgid="577"`), фактических тайлов кладётся в **0** карт | **P2** | PIL-разбор 16 тайлов (см. вывод); `python3` per-map разбивка: `generated_terrain DECLARED 117 / PLACED BY 0` |
| A-6 | `rocks.png` объявлен тайлсетом в **118** картах, реально рисует ровно в **1** (`L01S04`, одним тайлом 512×48 на всю картинку, `gid=491`). В 117 стандартных картах диапазон 481–576 не используется ни одним gid | P3 | та же per-map разбивка: `rocks DECLARED 118 / PLACED BY 1`; gid-набор `L01S04` = `{1,2,491}` + `{7,25..29,40..44}` |
| A-7 | Мёртвое арт-наследие в бандле: `step5_tiles.png` (330 B) — в `pbx`, имя не встречается ни в Swift, ни в одном TMX | P3 | `python3 final.py` → `SET2_PRESENT_BUT_UNREFERENCED_IMAGES 3`; `grep -rn "step5_tiles" --include=*.swift .` → пусто, по TMX → пусто; `pbxproj:43,345,740` → в бандле |
| A-8 | 4 пары **byte-identical** scenery-арта: `zone_028↔103`, `zone_040↔115`, `zone_046↔121`, `zone_047↔122` — систематический сдвиг **+75** и ровно пары `L02Sxx ↔ L05Sxx`. Избыточно **10218 B** в бандле | P3 | alpha-aware метрика (`visualdup.py`) → `VISUALLY_IDENTICAL_GROUPS 7`; sha256 файлов совпадает в 4 группах; `grep -l zone_103_original` → `L05S04.tmx`, `zone_028` → `L02S04.tmx` и т.д. |
| A-9 | `light.png` (301 B) и `ship_fire.png` (737 B) — на диске, вне pbx, **имена не встречаются нигде**. `light` вообще не имя TMX-объекта; `ship_fire` — имя объекта (2 шт), но Swift маппит его на текстуру `ship_fire_frame`, поэтому файл-тёзка мёртвая | P3 (cleanup) | `final.py` → `SET3`, `RUNTIME_MISSING_RISK 0`; `grep -nE "light\.png\|ship_fire\.png" project.pbxproj` → **пусто** (0 упоминаний во всём pbxproj) |
| A-10 | Полная геометрия сходится: все срезы листов попиксельно кратны. `vitorc 528x64`/11=48×64 ✓, `turret_tube 256x16`/8=32×16 ✓, `teleport 512x96`/8=64×96 ✓, `bubble 96x192`=3×6 по 32 ✓, `egg 32x16`/2=16 ✓, `missile 64x32`/2=32 ✓, `blaster_explosion 80x16`/5=16 ✓, `circular_explosion 320x32`/10=32 ✓, `turret_body 64x80` ✓. Снаряды 1:1: `turret_bullet 4x4`→4×4, `blaster_bullet 16x2`→16×2, `grenade 16x16`→16×16 | — (pass) | `pngcheck` dims + чтение всех 10 сайтов `SKTexture(rect:in:)` |
| A-11 | Единственные 2 PNG вне сетки 16 — `blaster_bullet.png 16x2`, `turret_bullet.png 4x4` — обе рисуются ровно в своем натуральном размере, дефекта нет | — (pass) | awk по `/tmp/perfile-assets/dims.txt`: `non-multiple-of-16 = 2` |
| A-12 | Все 125 карт — 35×24 тайла = **560×384 px**, а каждый scenery-imagelayer — **512×384**. Единый, строго одинаковый недобор **48 px (3 тайла) справа** в 120/120 слоях; объявленный размер совпадает с фактическим (не ложь в TMX) | P3 (дизайн-факт) | python: `distinct combos = 1`, `map=560,384 declared=(512,384) actual=(512,384) maps=120`, `all mismatches are the same delta? 1` |
| A-13 | `L01S04` — единственный map с неплотной раскладкой gid: `tiles` firstgid=1 ёмкость 480, следующий firstgid=491 ⇒ **10 «мёртвых» gid (481–490)**. Сейчас безопасен (ни один слой их не использует), но это заложенная мина. Остальные 124 карты: `tiles 1..480 / rocks 481..576 / generated_terrain 577..` — запасы **0**, без щелей и наложений | P3 | python: `117 maps: (tiles,1,480,slack 0),(rocks,481,96,0),(generated_terrain,577,16,0)`; `1 maps: (tiles,1,480,**10**),(rocks,491,1,0)`; `L01S04 ... DEAD gids: 10` |
| A-14 | Капсула прозрачности: 151/153 PNG — `32-bit RGB+alpha`; выбиваются `bubble.png` (4-bit palette+**tRNS**, 59.1% непрозрачных — OK) и `rocks.png` (2-bit palette, **без tRNS, 100% непрозрачен**, 3 цвета, фон чистый чёрный). Безвреден только потому, что единственная карта, рисующая rocks (`L01S04`), **не имеет scenery-слоя** — непрозрачный квадрат крыть нечего | P3 (хрупкость) | `grep -vE "32-bit RGB\+alpha"` → ровно 2 файла; PIL `alpha_kinds=1 opaque=100.0%`; «maps WITHOUT any imagelayer (5): L01S01,L01S02,L01S03,L01S04,L01S07» |
| A-15 | Целостность бандла: 276 записей Resources-фазы, **0 висячих**; все существуют на диске. 3 gif в фазе — **0** упоминаний во всём pbxproj | — (pass) | verify.sh п.7–9, п.11; `grep -c '\.gif in Resources'` → **0** |
| A-16 | Факты упаковки: `PRODUCT_BUNDLE_IDENTIFIER = com.exolon.remake`; `MARKETING_VERSION = 0.5`; **`CFBundleShortVersionString` захардкожен в `0.3`** (не `$(MARKETING_VERSION)`) — рассинхн внутри двух источников одной версии; `CFBundleVersion`/`CURRENT_PROJECT_VERSION` = 1; `MACOSX_DEPLOYMENT_TARGET = 10.14` и `LSMinimumSystemVersion 10.14` согласованы; `NSHighResolutionCapable = true`; `GENERATE_INFOPLIST_FILE = NO`; `CODE_SIGN_IDENTITY = "-"` (ad-hoc), `CODE_SIGN_STYLE = Manual` | P3 (семантика версий — не здесь) | `grep -nE "PRODUCT_BUNDLE_IDENTIFIER\|MARKETING_VERSION\|..." project.pbxproj`; `cat Exolon/Resources/Info.plist` |
| A-17 | **Иконки нет вообще**: ни `.icns`, ни `.xcassets`/`Assets.car`, ни `CFBundleIconFile`/`CFBundleIconName`/`ASSETCATALOG_COMPILER*`. Иконка приложения на macOS будет дефолтной | P3 | `find . -name "*.icns" -o -iname "*icon*"` → пусто; `grep -iE "CFBundleIcon\|AppIcon\|ASSETCATALOG"` по plist+pbxproj → пусто |
| A-18 | **Нет shared scheme и нет entitlements-файла** (`find Exolon.xcodeproj -name "*.xcscheme"` → пусто; `find . -name "*.entitlements"` → пусто) — сборка зависит от локально сгенерированной схемы, sandbox не описан | P3 (delivery) | те же `find` |
| A-19 | Gamepad-ключей в `Info.plist` **нет** (ни controller/gamepad/UsageDescription-ключей) и на macOS не требуется. Проверено, что это **не дефект**: код использует только `controller.extendedGamepad` (`GamepadInput.swift:47`), а `GCController.extendedGamepad` доступен с macOS 10.9+ ⇒ конфигурация 10.14 не противоречит API. Отдельно проверено, что deprecated-свойство `GCController.gamepad` в дереве **не** вызывается (совпадения в grep — локальная переменная `gamepad` и кейсы `.gamepadDPad/.gamepadStick/.gamepadButtons`) | — (pass) | `grep -n "gamepad" GamepadInput.swift` (все 15 строк — `extendedGamepad`+кейсы); документация Apple для `GCController.extendedGamepad` = macOS 10.9+ |
| A-20 | Не-анимированность — свойство и PNG-двойников тоже: `bubble.png`, `rocks.png`, `turret_bullet.png` → `nb_read_frames=1` | — (pass) | `ffprobe -count_frames` по всем 6 файлам |

**Итоговые множества (точные, из `final.py`):**

* `referenced-but-absent` = **0** (из 150 lookup-имён: 27 Swift + 123 TMX)
* `present-but-unreferenced` (изображения) = **3**: `light.png`, `ship_fire.png`, `step5_tiles.png`
* `on-disk-but-not-in-bundle` = **6**: `Info.plist` (штатно потребляется как `INFOPLIST_FILE`, не ресурс) +
  `bubble.gif`, `rocks.gif`, `turret_bullet.gif`, `light.png`, `ship_fire.png` ⇒ **«5 потерянных» из V3 подтверждено ровно**
* `pbx-in-но-нет-на-диске` = **0**
* `runtime_missing_risk` (referenced by Swift ∧ not bundled ∧ нет включённого в бандл брата по стему) = **0**

## Join: имя ресурса → код/TMX → диск → pbx

### 3.1 Swift → диск → pbx (все 27 достижимых имён)

Форма `код → имя → файл → в бандле`. Всё 27/27 резолвится; `pbx` = попадает ли в Resources phase.

| # | имя | сайт в Swift | файл на диске | pbx |
|---|---|---|---|---|
| 1 | `ammo_pack` | `LevelObstacles.swift:236` | `ammo_pack.png` 32×32 | ✓ |
| 2 | `blaster_bullet` | `BlasterBullet.swift:21` | `blaster_bullet.png` 16×2 | ✓ |
| 3 | `blaster_explosion` | `ExplosionEffect.swift:22` (assign) | `blaster_explosion.png` 80×16 | ✓ |
| 4 | `bubble` | `LevelObstacles.swift:444` | `bubble.png` 96×192 (+ `bubble.gif` **вне pbx**) | ✓ (png) |
| 5 | `circular_explosion` | `ExplosionEffect.swift:27` (assign) | `circular_explosion.png` 320×32 | ✓ |
| 6 | `cocoon` | `LevelObstacles.swift:10`; `TMXLevelRuntime.swift:252` | `cocoon.png` 80×128 | ✓ |
| 7 | `double_launcher` | `LevelObstacles.swift:689` | `double_launcher.png` 64×48 | ✓ |
| 8 | `double_launcher_bullet` | `LevelObstacles.swift:148` (assign) | `double_launcher_bullet.png` 16×16 | ✓ |
| 9 | `egg` | `LevelObstacles.swift:584` | `egg.png` 32×16 | ✓ |
| 10 | `gate` | `LevelObstacles`-нет; `TMXLevelRuntime.swift:421` и `:337` | `gate.png` 176×144 | ✓ |
| 11 | `grenade` | `Grenade.swift:33` | `grenade.png` 16×16 | ✓ |
| 12 | `grenade_pack` | `LevelObstacles.swift:214` | `grenade_pack.png` 32×32 | ✓ |
| 13 | `incubator` | `LevelObstacles.swift:525` | `incubator.png` 64×96 | ✓ |
| 14 | `light_ceiling` | `TMXLevelRuntime.swift:349` (static) | `light_ceiling.png` 16×16 | ✓ |
| 15 | `light_floor` | `TMXLevelRuntime.swift:346` (static) | `light_floor.png` 16×16 | ✓ |
| 16 | `mine` | `LevelObstacles.swift:735` | `mine.png` 32×16 | ✓ |
| 17 | `missile` | `LevelObstacles.swift:837` | `missile.png` 64×32 | ✓ |
| 18 | `piston` | `LevelObstacles.swift:333` | `piston.png` | ✓ |
| 19 | `radar` | `TMXLevelRuntime.swift:259` (destructible) | `radar.png` | ✓ |
| 20 | `rocket` | `TMXLevelRuntime.swift:266` (destructible) | `rocket.png` | ✓ |
| 21 | `ship` | `TMXLevelRuntime.swift:333` (static) | `ship.png` | ✓ |
| 22 | `ship_fire_frame` | `TMXLevelRuntime.swift:343` (static) | `ship_fire_frame.png` | ✓ (`ship_fire.png` — другой файл, мёртвый, вне pbx) |
| 23 | `teleport` | `LevelObstacles.swift:264` | `teleport.png` 512×96 | ✓ |
| 24 | `turret_body` | `LevelObstacles.swift:45` | `turret_body.png` 64×80 | ✓ |
| 25 | `turret_bullet` | `LevelObstacles.swift:138` (assign) | `turret_bullet.png` 4×4 (+ `.gif` **вне pbx**) | ✓ (png) |
| 26 | `turret_tube` | `LevelObstacles.swift:52` | `turret_tube.png` 256×16 | ✓ |
| 27 | `vitorc` | `PlayerSpriteNode.swift:18` | `vitorc.png` 528×64 | ✓ |

Закрытые динамические каналы (иначе множество было бы неполным): 6 сайтов `imageNamed:` передают
переменную, и все они прослежены до литералов — `imageName`/`image` в `ExplosionEffect.swift:33`,
`TMXLevelRuntime.swift:482`, `LevelObstacles.swift:155,191`, `TMXTileMapRenderer.swift:25,90`.
Два из них (`TMXTileMapRenderer`) берут имя из TMX — см. 3.2. Других API загрузки ресурсов в
дереве нет: `grep -rnE "fileNamed|SKTextureAtlas|SKAudioNode|SKVideoNode|NSImage|contentsOfFile|URL(forResource"`
→ единственный не-imageNamed результат `TMXMapLoader.swift:106 bundle.url(forResource:withExtension:"tmx")`.
`SKSpriteNode(imageNamed:)` — **0** вхождений.

### 3.2 TMX → диск (484 ссылки, path-aware)

| разбивка | число |
|---|---|
| всего `<image source>` в TMX (tileset + imagelayer) | **484** |
| уникальных verbatim-источников | **125** |
| уникальных stem-имён, которые спросит SpriteKit | **123** |
| разрешающихся на диск как путь | **482** |
| **не разрешающихся (битые пути)** | **2** — обе в `L01S04.tmx`: `../images/tiles.gif`, `../images/rocks.gif` |
| уходящих выше `Exolon/Resources/` | **2** (те же) |
| объявленный размер ≠ фактический пиксельный | **0** |

Разложение 123 stem-имён: `tiles`, `rocks`, `generated_terrain` (тайлсеты) + `zone004_scenery`,
`zone005_scenery` + `zone_007_original … zone_124_original` (118 подряд, **без пропусков**;
`min=7 max=124 count=118 missing=[]`) = 123. Все 118 `zone_*_original.png` реально
используются хотя бы одной картой («NEVER referenced = []»); 5 карт без imagelayer —
`L01S01, L01S02, L01S03, L01S04, L01S07`.

Тайлсеты: 364 объявления `<tileset>`, 4 раскладки — 117 карт «tiles+rocks+generated_terrain»,
4 карты «tiles+metatiles(=tiles.png)», 3 карты только «tiles», 1 карта (`L01S04`) «tiles+rocks(512×48)».
Три стандартных диапазона прилегают без щелей: 1..480 (ёмкость 480), 481..576 (96), 577.. (16).
Вне стандартной сетки — только 10 мёртвых gid в `L01S04` (A-13).

### 3.3 Три множества (точные)

```
referenced-but-absent        = ∅  (0 из 150)
present-but-unreferenced     = { light.png, ship_fire.png, step5_tiles.png }                 (3)
on-disk-but-not-in-bundle    = { Info.plist, bubble.gif, rocks.gif, turret_bullet.gif,
                                light.png, ship_fire.png }                                    (6; 5 «ресурсов» + plist)
pbx-entry-missing-on-disk    = ∅  (0 из 276)
runtime-missing-risk         = ∅  (0)
```

Пересечение «referenced ∧ not bundled» непусто по формальному критерию (`bubble.gif`,
`rocks.gif`, `turret_bullet.gif`) и пусто по фактически значимому: для каждого такого имени в
бандле есть файл с тем же stem-именем, поэтому `SKTexture(imageNamed:)` резолвится. Именно это
и делает опровержение V3 корректным по существу — но держится оно на collision-by-stem, а не на
«gif-имена живут только в комментариях».

## Контроли инструментов

Каждый зонд проверен негативным контролем, который **обязан был** перевернуться.

**1. `pngcheck` — положительная часть и два провала**

```
$ pngcheck Exolon/Resources/*.png | grep -c '^OK:'   → 153   (из 153; non-OK строк 0)

# контроль 1а: обрезанный PNG обязан упасть
$ head -c 120 Exolon/Resources/gate.png > /tmp/perfile-assets/trunc_gate.png
$ pngcheck /tmp/perfile-assets/trunc_gate.png
/tmp/perfile-assets/trunc_gate.png  EOF while reading IDAT data
ERROR: /tmp/perfile-assets/trunc_gate.png
control exit=2                                        ✓ перевернулся

# контроль 1б: бит-флип в IDAT обязан упасть
$ cp tiles.png corrupt_tiles.png; XOR среднего байта; pngcheck →
zlib: inflate error = -3 (data error)
ERROR: /tmp/perfile-assets/corrupt_tiles.png
control2 exit=2                                       ✓ перевернулся
```
Замечание: `pngcheck -q` подавляет строки `OK:` — первый прогон дал `OK count: 0`,
что является артефактом флага, а не результатом. Повторено без `-q` (153).

**2. `xmllint`**
```
$ for f in Exolon/Resources/*.tmx; do xmllint --noout "$f"; done   → ok=125 bad=0
# контроль: тот же TMX без закрывающего </map> обязан упасть
$ xmllint --noout /tmp/perfile-assets/broken.tmx
/tmp/perfile-assets/broken.tmx:141: parser error : Premature end of data in tag map line 2
control exit=1                                        ✓ перевернулся
```

**3. Зонд gid/размеров (`gidcheck.py`) — три контролируемых мутации, каждая обязана ловиться**

| контроль | мутация | ожидание | факт |
|---|---|---|---|
| A | в `L01S09` Collision (csv) вставлен несуществующий `gid=99999` | OVERFLOW>0 | `GID_OUTSIDE_TILESET_CAPACITY 1` → `('L01S09.tmx','Collision','generated_terrain','gid=99999','local=99422','cap=16')` ✓ |
| B | у `L01S01` Tile Layer 1 (base64) срезаны 4 символа | CELL_COUNT>0 | `CELL_COUNT_MISMATCH_LAYERS 1` → `have=839 need=840` ✓ |
| C | в `L01S01` объявлено `height="512"`→`"999"` | DECLARED_MISMATCH>0 | `DECLARED_VS_ACTUAL_IMAGE_SIZE 1` → `(tiles,(240,999),(240,512))` ✓ |

После валидации тот же зонд на чистом дереве: `TILE_LAYERS 138`,
`GID_OUTSIDE_TILESET_CAPACITY 0`, `CELL_COUNT_MISMATCH_LAYERS 0`,
`UNRESOLVED_GIDS 0`, `DECLARED_VS_ACTUAL_IMAGE_SIZE 0` — нولي результат доверяем.

**4. Подсчёт кадров GIF — два провалившихся зонда, один принятый**

Собственный block-walker (`gifcheck.py`) на контроле из 4 реальных кадров показал `frames: 1`
⇒ **бракован, отброшен**. Наивный `grep -c $'\x2c'` дал 13/14/1 (считает байты внутри LZW-потока)
⇒ **бракован, отброшен**. Приняты только независимые инструменты, провалидированные на
контроле, собранном самим ffmpeg:

```
$ ffmpeg -f lavfi -i "testsrc=duration=2:size=64x64:rate=5" -pix_fmt pal8 ctl10.gif
$ ffprobe -count_frames ... ctl10.gif   → nb_read_frames=10   ✓ контроль считает 10
$ python3 -c "PIL.Image.open('ctl10.gif').n_frames" → 10      ✓ второй инструмент согласен

$ ffprobe -count_frames bubble.gif rocks.gif turret_bullet.gif → 1, 1, 1
$ PIL n_frames тех же                                           → 1, 1, 1
```
Дополнительно: побайтовое сравнение `convert('RGBA').tobytes()` gif↔png по всем трём стемам →
`identical=True`, то есть даже единичный кадр gif не несёт нового содержательного пикселя.

**5. Alpha-aware метрика визуальных дублей (`visualdup.py`) — три контроля**

```
CTRL1 перекодировать без изменений        → canon равны        ✓ (must True)
CTRL2 менять RGB только там, где A==0     → canon равны, raw различаются ✓ (метрика слепа к невидимому)
CTRL3 менять один видимый пиксель         → canon различаются  ✓ (метрика не всеслепа)
```
Без этого контроля я был готов объявить дублями `zone_030↔105`, `zone_039↔114`, `zone_044↔119`:
у них `diffbbox=None` при `nzRGB=11296/8452/15600` — различия лежат целиком в невидимых
областях, но `getbbox()` PIL по RGBA-разнице их не отражает, и наивный «bbox=None ⇒ идентичны»
дал бы ложные дубли, а «nzRGB>0 ⇒ дубли отсутствуют» — ложный пропуск. По alpha-aware хэшу
они **не** дубли (часть отличающихся пикселей имеет A≠0), и в итоговые 7 групп не входят.

**6. Два собственных ложных срабатывания этого прогона — зафиксированы и сняты**

* Первый прогон сообщил «TRUNCATED 128 слоёв». Причина: в счётчике атрибутов я захардкодил
  `v if k!='encoding' else 'b64'`, уничтожив информацию о кодировании, и затем декодировал
  **csv**-текст как base64. Реальное распределение: `encoding="csv"` — **128**,
  `encoding="base64"` — **10**; все 10 base64 дают ровно `w*h*4` байт. Находка снята полностью.
* Первый gid-зонд вернул `TMX_WITH_GID_DATA 0` — пустой результат при неверном предположении о
  кодировании. Заменён корректным (`join2.py` → `gidcheck.py`), провалидирован контролем B.
* Также снято предположение о несовместимости gamepad API с `MACOSX_DEPLOYMENT_TARGET 10.14`
  (A-19): `extendedGamepad` — macOS 10.9+, дефекта нет.

**7. Swift — только синтаксис, не сборка**

```
$ swiftc -frontend -parse <файл>   LevelObstacles.swift / TMXLevelRuntime.swift / TMXTileMapRenderer.swift → PARSE OK (3/3)
```
Это **синтаксическая** проверка. Полной сборки нет (Swift/SpriteKit на этом хосте не собираются),
поэтому ни один вывод в этом срезе не является доказательством компилируемости или поведения рантайма.

## Что проверить на macOS

1. **Резолв коллизий стемов.** В собранном бандле лежат `bubble.png`, `rocks.png`,
   `turret_bullet.png`; gif в бандл не копируются, так что коллизии быть не должно — но это надо
   **увидеть**, а не вывести. Проверить: `ls Exolon.app/Contents/Resources | grep -E 'bubble|rocks|turret_bullet'`
   и отдельно проверить в lldb/однотестовом прогоне: что реально возвращает `SKTexture(imageNamed:"bubble")`.
2. **`L01S04` без Tiled.** Открыть `L01S04.tmx` в Tiled: оба тайлсета (`../images/tiles.gif`,
   `../images/rocks.gif`) должны показать «missing image». Убедиться, что в игре карта рендерится
   корректно **именно** за счёт stem-фолбэка, и зафиксировать это тестом, иначе правка
   «давайте уважать source как путь» молча лишит карту обеих тайлсет-картинок.
3. **`generated_terrain` не виден, и это надо подтвердить визуально.** 117 карт объявляют его,
   0 кладут. Сделать скриншот любой стандартной карты и убедиться, что ни одного
   кислотного тайла (чистые green/magenta/cyan/yellow/red) на экране нет. Если появится —
   это не «пропал декодер», а протёк заглушка-арт.
4. **Непрозрачный `rocks.png`.** Единственный потребитель — `L01S04`, где scenery-слоя нет.
   Проверить, что `L01S04` выглядит чисто; и знать, что если в `L01S04` добавят imagelayer
   (или начнут класть gid 481–576 в картах со scenery), появятся чёрные квадраты 16×16 поверх
   фона, потому что у `rocks.png` нет ни tRNS, ни alpha-канала.
5. **Недобор 48 px справа.** Все карты 560×384, вся scenery-подложка 512×384. Проверить глазами
   полосу x=512..560: закрыта ли тайлами/фоном, или это намеренная граница оригинала.
6. **Масштабы листов при не-целых size.** Вся нарезка кратна (A-10), но `blaster_bullet.png`
   16×2 рисуется в 16×2, а `turret_bullet.png` 4×4 в 4×4 — убедиться, что `.nearest`
   не даёт полос на логическом разрешении, и что `NSHighResolutionCapable`+Retina не
   ресемплуют 2-пиксельную по высоте текстуру.
7. **Версия и иконка.** Собрать и посмотреть: `CFBundleShortVersionString` в `Info.plist`
   захаркожен `0.3`, тогда как `MARKETING_VERSION = 0.5` — какое значение окажется в Copy
   Assets-выходе и в «О программе» (семантику разрешает другая lane, здесь — только факт).
   Иконки нет ни в plist, ни в `.icns`, ни в `.xcassets` → подтвердит дефолтную иконку.
8. **Scheme.** Общие `.xcscheme` отсутствуют — проверить, что сборка воспроизводится на чистом
   клоне, а не только на машине с локально сгенерированной схемой.
9. **Gamepad.** На macOS 10.14 проверить, что `controller.extendedGamepad != nil` для целевых
   геймпадов; ключей в `Info.plist` не требуется (A-19).

## Вердикт: pass

Обоснование границы вердикта: **бандл как бандл и join «имя → диск → pbx» исправны** —
0 отсутствующих ресурсов из 150 lookup-имён, 0 висячих pbx-записей из 276, 0 runtime-риска,
153/153 PNG целостны, 125/125 TMX корректны как XML, 0 переполнений gid, вся геометрия листов
кратна, множества карт и кода равны точно (125≡125). Ни один найденный дефект не ломает
собранный бандл и не даёт отсутствующую текстуру в рантайме.

Что при этом **обязано** быть исправлено, но не блокирует этот срез:

* опровержение §3 принять по существу (V3 действительно не дефект), но **переписать его
  обоснование**: «27» — это уникальные *имена*, а не места вызова (мест 23, литералов 17);
  «настоящая дыра — GIF» снять (все gif однокадровые, в бандл не входят, терять анимацию нечем);
  «gif-имена только в комментариях» заменить на «столкновение стемов с включёнными в бандл PNG»;
* A-4 (`L01S04.tmx`, 2 битых пути) — P2, чинить как дефект контента;
* A-5 (`generated_terrain.png` — отладковая заглушка, объявлена в 117 картах, кладётся в 0) — P2;
* cleanup: A-7 `step5_tiles.png` (в бандле, имя нигде не встречается), A-8 4 дубля scenery (10218 B),
  A-9 `light.png`/`ship_fire.png`, и либо включить 3 gif в бандл, либо удалить из дерева.

Ограничение честности: ни один вывод не подтверждён сборкой или прогоном на macOS —
Swift здесь только синтаксически парсится. Пункт «почему именно stem-фолбэк, а не путь,
спасает `L01S04`» — вывод из чтения `TMXTileMapRenderer.swift`, а не наблюдение рантайма;
проверяется п.2 выше.
