# Lane: TMXMapLoader.swift + TMXTileMapRenderer.swift (перифайловый аудит)

HEAD 52795d1. Метод: код прочитан построчно; `TMXMapLoader.swift` РЕАЛЬНО ИСПОЛНЕН на этом
хосте (Swift 6.4 for Linux, /opt/swift/usr/bin/swiftc) — байт-в-байт копия файла + два
допуска, ни один не касается логики разбора: (1) добавлена строка `import FoundationXML`
(на Linux XMLParser перенесён в этот модуль), (2) стаб-модуль `CoreGraphics`, который делает
только `@_exported import Foundation` (на Linux Foundation уже даёт CGFloat, на macOS это
нативный тип). Харнесс: 17 malformed-фикстур в /tmp/lane-loader2/fb + прогон всех 125
штатных карт через `TMXMapLoader.load`. Рендерер исполнить нельзя (SpriteKit) — его вердикты
из чтения кода + python-модель его же арифметики (GID/tileset/rect), плюс пометка «нужен
macOS» там, где решает поведение SKTexture.

## Итог

B-04 подтверждён целиком, все три ветки воспроизведены исполнением настоящего Swift-кода:
(a) любой `compression=` (zlib и gzip) → `unsupportedCompression` → `fatalError` на
TMXLevelRuntime.swift:53 (фикстуры f03/f04); (b) well-formed `<map/>` или чужой корень без
имён layer/data/objectgroup → `makeMap()` без единой проверки → нулевой TMXMapData →
«играбельная пустота» (f02); (c) опечатка в числовом атрибуте молча становится 0:
`y="17o"`→0, `tilewidth="32a"`→0 (обрушивает всю геометрию карты), `gid="2a"`→Some(0) (f05).
При этом экспозиция в текущих данных = 0: все 125 карт загрузились реальным Swift-загрузчиком
125/125, ни одного `compression`, ни одного отсутствующего/нечислового x/y среди 680 объектов,
ни одного слоя/группы пустых. Найдена сверх B-04 системная ошибка области видимости
`<property>`: свойства imagelayer/objectgroup утекают в свойства карты, свойства layer/tileset
молча выбрасываются (f06, исполнено). README о «явной конверсии прямоугольников» завышен:
механизм `coordinateMode=tiledRect` есть и работает, но помечен им ровно 1 объект из 360
прямоугольных; обе числовые заявки README по L01S10 подтверждены данными. Разбиение
csv/base64 проверено независимо: 121 csv / 4 base64 (L01S01–L01S04).

## Таблица находок

| ID | Pri | Файл:строка | Поведение (цитата) | Вход, который триггерит | Исход |
|----|-----|-------------|--------------------|--------------------------|-------|
| LD-01 (B-04a) | Suggestion (lat.) | TMXMapLoader.swift:307-309 + TMXLevelRuntime.swift:53 | `if !compression.isEmpty { throw .unsupportedCompression(compression) }` | `<data encoding="base64" compression="gzip">` (или zlib) — любой экспорт Tiled с включённой компрессией | throw → `fatalError("Unable to load TMX map...")` — жёсткий краш игры на инициализации уровня; доказано прогоном (f03, f04). В 138 `<data>` аттрибута compression нет ни в одной из 125 карт |
| LD-02 (B-04b) | Suggestion | TMXMapLoader.swift:116-123,155-166 | `return delegate.makeMap()` — в makeMap нет ни одного guard | well-formed `<map/>`, `<map/>` без слоёв, или чужой корень (`<somedata/>`) без имён layer/data/objectgroup | нулевая карта width=0,height=0,layers=[] проходит в рантайм: renderer даёт collisionRects=[], vitorc нет → спавн по умолчанию → пустой playable void (f02, f13). В shipped-данных 0/125 (у всех есть слои и объекты) |
| LD-03 (B-04c) | Suggestion | TMXMapLoader.swift:346-350 | `Int(value ?? "") ?? 0`, `UInt32(...) ?? 0`, `guard let number = Double(value) else { return 0 }` | `y="17o"`, `x="368 "`, `tilewidth="32a"`, `gid="2a"`, отсутствующие x/y | молча 0 вместо ошибки: объект на лету, нулевой размер тайлсета, gid Some(0). Доказано прогоном (f05). Замер: среди 680 объектов 125 карт — 0 отсутствующих и 0 нечисловых x/y |
| LD-04 | Suggestion | TMXMapLoader.swift:231-239 | `else if currentLayerName == nil && currentTileset == nil { mapProperties[name] = value }` — условия на imagelayer/objectgroup нет | `<properties>` внутри `<imagelayer>` или `<objectgroup>`; внутри `<layer>`/`<tileset>` | свойства утекают в свойства КАРТЫ (контекстная подмена), а свойства слоёв/тайлсетов молча ДРОППУВАЮТСЯ. Доказано прогоном (f06: `fromImageLayer=LEAK` в map props). В данных 0 таких вхождений (свойства есть только на map 495 и object 515) — латентно для ручной правки/чужих карт |
| LD-05 | Nice to have | TMXMapLoader.swift:270-281,343 | `<layer>` без `<data>` → `decodeLayerData("", "", "")` → `throw .unsupportedEncoding("")` | самозакрывающийся `<layer ... />` (в т.ч. под чужим корнем — XMLParser матчит по локальному имени) | краш вместо «пустой слой» (f01: бросается ещё до makeMap). Сообщение `Unsupported TMX encoding: ` с пустым значением — нетаксономично |
| LD-06 | Nice to have | TMXTileMapRenderer.swift:54 | `let gid = rawGID & 0x1FFF_FFFF // remove Tiled flip flags` | GID с флагами H/V/D-reflect (биты 0x80000000/0x40000000/0x20000000) | флаги снимаются, но отражение НЕ применяется → тайл рисуется неотражённым (молча). Замер: 0 флаговых GID и в csv, и в base64 по всем 125 |
| LD-07 | Nice to have | TMXMapLoader.swift (атрибуты layer не читаются) | `visible`/`opacity`/`tintcolor`/`offsetx/y` ни на layer, ни на imagelayer не парсятся | `<layer visible="0" ...>` с непустым содержимым не-collision | скрытый в Tiled слой отрисовался бы. Единственный `visible=` в данных — L01S04.tmx:30 на слое Collision (именно collision выключен по имени, эффект нулевой) |
| LD-08 | Nice to have | TMXTileMapRenderer.swift:55,74-77,100 | `guard gid != 0, let tileset = tileset(for: gid) else { continue }`; `guard localIndex >= 0, localIndex < columns * rows else { return nil }` | GID вне диапазона всех tileset (firstgid/размеры картинки) | тайл молча исчезает без warning. Python-модель по 125 картам: 781 видимый непустой тайл, молча сброшенных = 0. firstgid<=gid max-выбор корректен для имеющихся данных |
| LD-09 | Nice to have | TMXMapLoader.swift:180-181 + renderer:76 | `firstGID: uint(attributeDict["firstgid"])` → отсутствие = 0 | tileset без firstgid | firstGID=0 матчится на любой gid (`filter { $0.firstGID <= gid }` max) → перехват чужих тайлов. В данных 0 тайлсетов без firstgid |
| LD-10 | Suggestion | TMXMapLoader.swift:73-80 | ветвление только на `object.properties["coordinateMode"] == "tiledRect"`; ни gid, ни width/height не смотрятся | любой rect-объект без этого свойства (все генерируемые карты) | «конфликт» tile↔rect решается не типом объекта, а оп-ин-свойством, которое проставлено 1 разу из 360 rect-объектов (capsule L01S10). См. раздел README — заявка завышена |
| LD-11 | Nice to have | TMXMapLoader.swift:316 | `guard data.count >= expectedCount * 4` | base64 с лишними байтами | лишнее молча игнорируется (f10 OK); усечение бросает invalidLayerData (f09). Асимметрия с csv (`values.count == expectedCount`, строка 337) |
| LD-12 | Nice to have | TMXMapLoader.swift:275-279 | `expectedCount: currentLayerWidth * currentLayerHeight` — Int-умножение до любых проверок | layer width/height ~1e10 в фикстуре | потенциальный арифметический trap вместо типизированной ошибки; память не аллоцируется (reserveCapacity в b64 после проверки data.count; в csv count-проверка по факту текста, f17 fail-closed). Теоретическое, требует malform-файл |
| LD-13 | Suggestion | TMXTileMapRenderer.swift:23-25,84-90 | `URL(fileURLWithPath: source).deletingPathExtension().lastPathComponent` → `SKTexture(imageNamed:)` | `../images/tiles.gif`, `../images/rocks.gif` (L01S04.tmx:9,12) | каталог И расширение выбрасываются намеренно → выживание через стем `tiles`/`rocks`, которые бандлятся как tiles.png/rocks.png (pbxproj: rocks.png 6 refs, tiles.png 12; rocks.gif в бандл не входит). Это НЕ «by design safe»: тот же механизм молча схлопывает одноимённые стемы из разных каталогов и проглатывает опечатки расширения; при отсутствии стема SKTexture на macOS вернёт placeholder-текстуру (?), а не ошибку — визуальный мусор без единого лого-сообщения. Нужен macOS |
| LD-14 | Nice to have | TMXMapLoader.swift:261-263 | `if let imageLayer = ..., !imageLayer.imageSource.isEmpty` | imagelayer без `<image source=>` | слой молча выбрасывается без предупреждения |

Про `try!`/force unwrap в двух аудитованных файлах: нет ни одного (`grep` чист). try!/fatalError
на пути данных — только у потребителя: TMXLevelRuntime.swift:51-54 (см. LD-01).
Производительность: рендер — однократно в init, покадровых аллокаций в файле нет; пер-тайловый
`tileset(for:)` создаёт массив на каждый тайл (O(tilesets) на тайл), но потолок по замеру —
247 спрайтов на карту (L01S03), несущественно. collision-раны: максимум 35 rect на карту.

## Реальные замеры по 125 картам

Прогон реального Swift-загрузчика: **125/125 карт загружаются без единой ошибки**
(Linux FoundationXML; для well-formed входных данных платформа не влияет). Python-и
Swift-замеры совпали по всем совпадаемым позициям.

- Encoding data-элементов: csv 128, base64 10, **compression: 0 из 138**. По картам:
  **121 только-csv / 4 только-base64 / 0 смешанных / 0 без data** — base64-четвёрка:
  L01S01.tmx, L01S02.tmx, L01S03.tmx, L01S04.tmx (независимо подтверждает параллельную lane 121/4).
- Корень `<map>` у 125/125; width/height/tilewidth/tileheight присутствуют у всех;
  слоёв с w*h=0 — 0; пустых `<objectgroup>` (0 объектов) — 0; карт без тайл-слоёв — 0;
  «void-формы» (ни слоёв с данными, ни объектов) — 0.
- Объекты: всего 680; **tile-объектов (с gid) — 0 во всех 125**; rect-объектов (w>0,h>0, без gid)
  — 360, из них с `coordinateMode=tiledRect` — **1**; point-объектов (w=h=0) — 320;
  x/y отсутствуют — 0; x/y нечисловые — 0; gid="0" — 0; `type=` у объектов — 0;
  `draworder="index"` — 0; дубли имён объектов в 104 картах (норма: несколько piston/teleport;
  `object(named:)` берёт первый, рантайм использует `objects(named:)`).
- Свойства: map-level 495 (из них zoneNumber у 117 карт; значений ровно по одному на номер,
  '009'→единственная карта L01S10; без zoneNumber — L01S01…L01S08), object-level 515,
  layer/tileset/objectgroup/imagelayer-level — 0 (т.е. LD-04 в данных не задет).
- Тайлсеты: 125 из 125 карт — инлайн, с firstgid, image с width/height; `source=` у tileset
  (.tsx) — 0; margin/spacing/columns — 0; tile animation/probability/type — 0;
  `<chunk>`/`<tileoffset>`/wangset — 0.
- Изображения: 125 distinct `<image source>`; с путем или расширением, не совпадающим с файлом
  в Resources — ровно **2: `../images/tiles.gif` и `../images/rocks.gif` обе в L01S04.tmx
  (строки 9 и 12)** — выживают только через стем-фолбэк LD-13; каталог `images/` в дереве
  отсутствует вовсе. Стемы всех остальных источников существуют как файлы в Resources.
- GID-арифметика рендерера: видимых непустых тайлов по корпусу 781 (макс. 247, L01S03);
  молча сброшенных (нет tileset / localIndex вне columns*rows) — **0**; флагов отражения — 0;
  тайлсетов без годных размеров — 0. layer size == map size у всех; tilesize тайлсетов ==
  map tilesize у всех; >1 collision-слоя ни в одной карте.

## Покрываемость фич TMX

| Фича | В данных? | Читается кодом? | Комментарий |
|------|-----------|-----------------|-------------|
| encoding=csv | да (121 карта) | да | строгая проверка количества (337) |
| encoding=base64 | да (4 карты) | да | little-endian разбор 4 байт, только «>=» по длине (316) |
| compression=zlib/gzip | нет | отказ throw (307) | → fatalError потребителя (LD-01) |
| encoding=xml/пустой | нет | отказ throw (343) | и `<layer/>` без data попадает сюда (LD-05) |
| `<chunk>` | нет | нет | текст chunk собрался бы в data → почти наверняка invalidLayerData |
| map-properties / object-properties | 495 / 515 | да | |
| properties на layer/tileset | нет | выбрасываются | LD-04 |
| properties на imagelayer/objectgroup | нет | **утекают в mapProperties** | LD-04 (исполнено f06) |
| object type / point / ellipse / polygon | нет | нет | ни одного в данных |
| object x/y/w/h, gid | да | да, с нулевым фолбэком | LD-03 |
| tileset source=.tsx | нет | нет (только name) | тайлсет без image → все его тайлы молча исчезнут (LD-08) |
| tileset margin/spacing/columns | нет | нет | renderer выводит columns=imageWidth/tileWidth |
| tile animation / probability | нет | нет | |
| image width/height | да | да | без них tileTexture → nil молча |
| image transparent/tintcolor | нет | нет | |
| layer opacity/tintcolor/offset | нет | нет | |
| layer visible | 1 (L01S04:30 Collision) | нет | LD-07 |
| imagelayer opacity/offset/visible | нет | нет | imagelayer без source молча дропается (LD-14) |
| objectgroup draworder/color/offset | нет | нет | |
| GID flip/transpose флаги | нет | маскируются без применения | LD-06 |
| map nextlayerid/version/orientation/hexsidelength | есть атрибуты | нет | безвредно |

## Заявки README ↔ код

Контекст: README.md:8-10 (блок changelog). Зона 009 идентифицирована по properties:
единственная карта с `zoneNumber value="009"` — **L01S10.tmx** (значения нулевые-дополненные,
`value="9"` не встречается).

1. **«Zone 009 pistons now use x=64/192, y=320 (not y=384)» — подтверждено данными.**
   В L01S10.tmx ровно два объекта `piston` (sourceBlock=blk_anim_pump): x=64,y=320 и x=192,y=320,
   w=48,h=64. Исполненным Swift-загрузчиком: worldBottomLeft=(64,64) и (192,64) при pixelHeight=384.
2. **«changing room is a real 32x80 rectangle at x=368, y=176 in Tiled coordinates» — подтверждено.**
   Тот же L01S10.tmx: объект `capsule` (sourceBlock=blk_changing_room), без gid, x=368 y=176
   w=32 h=80, с `coordinateMode=tiledRect`; загрузчик даёт bottomLeft (368, 384-176-80=128) —
   арифметика конверсии верна (исполнено).
3. **«rectangle-object coordinate conversion is explicit, so tile objects and rectangles are no
   longer conflated» — завышено.** Механизм (TMXMapLoader.swift:73-80) различает режимы ТОЛЬКО по
   опциональному свойству `coordinateMode=tiledRect`; сам факт rect-формы (w/h>0 без gid) кодом не
   анализируется. По корпусу: rect-объектов 360, помеченных — 1 (капсула L01S10); остальные 359,
   включая piston в заявленной zone 009, идут легаси bottom-anchor веткой. Формально «explicit
   mechanism» существует, фактически «no longer conflated» верно для 0.3% прямоугольных объектов;
   корректность остальных — молчаливое допущение к генератору карт (для tile-объектов конвенция
   bottom-anchor верна по определению Tiled, но в данных их 0, так что проверка негде не
   приложена). Оценка: README стоит переписать как «capsule-объект переведён в tiledRect;
   конвертирование опционально и включено точечно».

## Что проверить на macOS

1. Поведение `SKTexture(imageNamed:)` при отсутствующем имени — плейсхолдер «?» или nil:
   от этого зависит, является ли LD-13 «молча визуальный мусор» или чем-то хуже. Прогнать
   L01S04 (стемы tiles/rocks) и фикстуру с `source="no_such_stem.png"`.
2. Порядок разрешения `imageNamed("rocks")`, если в бандл попадут и rocks.png, и rocks.gif
   (сейчас в pbxproj только rocks.png — конфликт потенциальный).
3. Malformed-поведение XMLParser на macOS: на Linux corelibs усечённый `<map width="1"...>` и
   пустой файл ПРОПУСТИЛИСЬ как OK-карты (f14/f15), тогда как libxml2 в macOS Foundation должен
   дать parse()=false → invalidXML → fatalError. Void-поведение well-formed `<map/>` (f02) не
   платформозависимо — оно следует из отсутствия проверок в makeMap.
4. Реальный кадр: anchorPoint сцены (0,0) (GameScene.swift:57) и scaleMode .aspectFit
   (AppDelegate.swift:26) согласуются с допущением renderer'а о map-pixel пространстве; проверить
   смещений тайл-сетки не должен — арифметика позиция/размер сходится с замерами.

Вердикт: fail
