# Ценз схемы shipped-данных TMX (только данные, read-only)

Лейн: `tmx-census`. Репозиторий `<repo>`, HEAD `52795d13d879ad477a3023cae69978436ff82d1a`,
выборка `Exolon/Resources/*.tmx` = 125 файлов. Скрипт ценза: `/tmp/lane-census/census.py` →
`/tmp/lane-census/census.json` (полный пофайловый дамп, 616 123 байта, sha256
`016acc4454bfcf5e78061a099816fa422b95d95f639085fe4843efd52b9da0ec`). В репозиторий записан только этот файл.
Корректность кода, читательского парсинга и C1 здесь не рассматриваются — зафиксировано ровно то, что лежит в XML.

Все контрольные числа пересчитаны второй, независимой реализацией (`xml.dom.minidom` плюс сырой
regex/CSV/base64-декод по тексту файла, без `ElementTree`): 125 файлов, один вариант `<map>`-заголовка,
138 слоёв, `csv` 128 / `base64` 10 / `compression` 0, 680 объектов (`id` 632, `width`/`height` 360,
`x=y=0` 28), ровно 6 атрибутов у объектов, свойства 515/145/145/28/28/1, 41 distinct gid,
13 088 painted-тайлов, max gid 491 — совпали 1:1.

## Итог

| Метрика | Значение |
|---|---|
| Файлов `.tmx` | **125** (L01S01…L05S25, 5 зон × 25) |
| Значений `version` | **1** — `1.0` ×125 |
| `orientation` | **1** — `orthogonal` ×125 |
| `tilewidth`×`tileheight` | **1** — `16x16` ×125 |
| Размеров карты | **1 distinct** — `35x24` ×125 (560×384 px) |
| Тайлсёров / слоёв / объектов | 364 `tileset` / 138 `layer` + 125 `objectgroup` + 120 `imagelayer` / 680 `object` |
| Кодирование `data` | `csv` **128** слоёв, `base64` **10** слоёв, `compression=` **0/138** |
| gid вне объявленных диапазонов | **0** |
| Ошибок декодирования / рассогласования ячеек | **0 / 0** |
| Объектов с `x=0,y=0` | **28** (все `bubble_creator`), при этом объектов **без** атрибутов `x`/`y` — **0** |
| Отсутствующих стандартных атрибутов | `type`,`gid`,`rotation`,`visible`,`template`,`class` — **0 вхождений на всех 680** |
| Аномальных файлов | **8** legacy-карт `L01S01…L01S08` против 117 канонических; из них `L01S04` — отдельный сломанный случай |

Основная форма данных единообразна: 117 из 125 карт имеют идентичный заголовок, три тайлсета, один
imagelayer, один тайл-слой `Collision`, один `objectgroup` и CSV-кодирование. Всё разнообразие схемы
сжат в 8 первых файлах `L01S01…L01S08`, которые заметно старше остальных и несут почти все расхождения.

## Карта схемы

**1. Атрибуты `<map>`.** На всех 125 файлах ровно шесть атрибутов, ни больше ни меньше:
`version`, `orientation`, `width`, `height`, `tilewidth`, `tileheight`. Нет `nextlayerid`, `nextobjectid`,
`background_color`-атрибута, `tilecount`, `infinite` — то есть карты не генерировались свежими версиями Tiled.

- `version="1.0"` — 125/125, других значений нет.
- `orientation="orthogonal"` — 125/125 (ни `isometric`, ни `hexagonal`).
- `tilewidth="16" tileheight="16"` — 125/125.

**2. Размеры карт.** `distinct_map_sizes = 1`. Распределение: `35x24` — 125 файлов (100%).
В пикселях 560×384 на всю выборку. Ни одной карты другого размера, ни одного тайл-слоя с `width`/`height`,
отличным от карты (`layer_wh_differs_from_map = []`).

**3. Кодирование и хранение.** Все 138 элементов `<data>` несут атрибут `encoding`, `compression` нет
ни разу (`data_compression_attr = {"None": 138}`). Разделение строго бинарное:

- `encoding="csv"` — **128** слоёв (всё в 121 файле плюс части legacy-файлов).
- `encoding="base64"` — **10** слоёв, и все 10 лежат в четырёх файлах: `L01S01` (2 слоя), `L01S02` (2),
  `L01S03` (2), `L01S04` (4). Каждый payload после снятия переносов даёт 4480 b64-символов → 3360 байт,
  что ровно 840 × 4 байта (35×24), хвостовых байт 0, магии gzip (`1f 8b`) или zlib (`78 …`) нет —
  **base64 здесь не сжат, это голый little-endian uint32**.
- `<tile gid="…"/>` дочерних элементов в данных нет вообще (0), формат всегда `format` не указан.
- Декодировались 138/138 слоёв; количество тайлов в payload равно `width*height` в 138/138 случаях.

**4. Инвентарь слоёв по типам.**

| Тип | Элементов | Карт | Примечание |
|---|---|---|---|
| `layer` (tilelayer) | 138 | 125 | 1 слой в 118 картах, 2 в 4 (`L01S01-03`,`L01S07`), 4 в 3 (`L01S04-06`) |
| `objectgroup` | 125 | 125 | ровно один на карту, всегда |
| `imagelayer` | 120 | 120 | по одному; **отсутствует в 5 картах** |
| `layergroup` / `weltlayer` | 0 | — | в выборке не встречаются |

Карты **без** imagelayer: `L01S01.tmx`, `L01S02.tmx`, `L01S03.tmx`, `L01S04.tmx`, `L01S07.tmx`.
(Показательно: `L01S05`, `L01S06`, `L01S08` — тоже legacy, но imagelayer у них уже есть.)

**5. Порядок элементов (z-order).** 6 вариантов расположения детей `<map>`:

- 117 карт — канонический `properties > tileset×3 > imagelayer > layer > objectgroup`;
- 8 legacy-карт (`L01S01…L01S08`) — `Collision`-слой стоит **после** `objectgroup`, то есть поверх объектов;
- из них `L01S05`/`L01S06` дополнительно разрывают `objectgroup` с двух сторон
  (`… > layer(Stars) > layer(Tile Layer 1) > objectgroup > layer(Tile Layer 2) > layer(Collision)`).

**6. Служебные атрибуты слоя.** `visible` встречается **один раз на всю выборку**:
`L01S04.tmx`, слой `Collision`, `visible="0"`. Собственных `<properties>` у тайл-слоёв, объектных групп
и imagelayer нет ни одного (`{}` во всех трёх проверках). У 8 объектных групп (`L01S01…L01S08`) есть
избыточные `width="35" height="24"`, совпадающие с картой.

## Слои

Имена слоёв (число — сколько карт используют имя):

| Имя | Тип | Карт |
|---|---|---|
| `Collision` | tilelayer | **125** (по одному слою на карту, всегда) |
| `Tile Layer 1` | tilelayer | 7 (`L01S01…L01S07`) |
| `Stars` | tilelayer | 3 (`L01S04`, `L01S05`, `L01S06`) |
| `Tile Layer 2` | tilelayer | 3 (`L01S04`, `L01S05`, `L01S06`) |
| `Objects` | objectgroup | **119** |
| `Object Layer 1` | objectgroup | 6 (`L01S01…L01S06`) |
| `Original Static Scenery` | imagelayer | **118** |
| `Original Scenery` | imagelayer | 2 (`L01S05`, `L01S06`) |

**Опечаток/регистровых вариантов нет.** Проверка нормализацией (регистр + все разделители в ноль)
по всем четырём классам имён даёт пустые группы: `case_or_separator_variants_* = {}` — то есть
`Tile Layer 1`/`tile layer 1`/`TileLayer1` рядом не лежало. Расхождение другое, **лексическое (по составу
слов)**, и оно бьёт ровно по тем же 8 legacy-картам:

- `Objects` vs `Object Layer 1` — одна и та же по роли группа называется по-разному;
- `Original Static Scenery` vs `Original Scenery` — выпало слово `Static`;
- `Collision`/`Stars` (семантические) соседствуют с `Tile Layer 1`/`Tile Layer 2` (дефолты Tiled)
  в одних и тех же картах: в `L01S04…L01S06` лежат все четыре имени сразу.

То есть матчинг слоёв «по имени» обязан держать два альтернативных имени для объектной группы
и два — для фонового слоя, иначе 6/125 и 2/125 карт соответственно молча выпадают.

## Тайлсеты и gid

**1. Объявления.** Всего **364** `<tileset>`: по 3 в 117 картах, по 2 в 5 картах, по 1 в 3 картах
(`L01S01`, `L01S02`, `L01S03`). Набор атрибутов одинаков везде и полный: `firstgid`, `name`, `tilewidth`,
`tileheight` — по 364 вхождению. `tilecount`, `columns`, `spacing`, `margin`, `version`, `backgroundcolor`
не встречались ни разу, поэтому «объявленное число тайлов» в данных отсутствует как класс:
единственный источник количества тайлов — геометрия картинки.

`source` (внешний `.tsx`) — **0 из 364**. Все 364 тайлсета инлайновые, у каждого ровно один
`<image source=… width=… height=…>`; других дочерних элементов (`terraintypes`, `tile`, `wedging`) нет.

**2. `firstgid` и имена.**

| `firstgid` | Кол-во объявлений | Что это |
|---|---|---|
| 1 | 125 | `tiles` (240×512 @16 → **480** тайлов, gid 1…480) |
| 481 | 121 | `rocks` в 117 картах (512×48 @16 → **96**, gid 481…576) **и** `metatiles` в 4 картах |
| 577 | 117 | `generated_terrain` (256×16 @16 → **16**, gid 577…592) |
| 491 | 1 | `rocks` в `L01S04` (`../images/rocks.gif`) |

Имена: `tiles` 125, `rocks` 118, `generated_terrain` 117, `metatiles` 4.
Картинки: `tiles.png` 128, `rocks.png` 117, `generated_terrain.png` 117, `../images/tiles.gif` 1,
`../images/rocks.gif` 1. Оба `.gif`-пути ведут **за пределы** `Resources/` и на диске **отсутствуют**
(`../images/rocks.gif`, `../images/tiles.gif` → `exists: false`); это единственные битые ссылки на ассеты
в выборке, обе в `L01S04.tmx`. Все 120 картинок imagelayer (`zone_*_original.png`, `zone00X_scenery.png`)
на диске есть, все 512×384 px.

**3. Объявленное vs подразумеваемое число тайлов.** Все изображения кратны размеру тайла
(`images_not_exact_multiple_of_tile = []`), частичных тайлов нет, declared-vs-disk расхождений по
размеру картинки тоже нет (`7_tileset_images_wh_mismatch_vs_tmx_declared = []`). Итоговая геометрия:
480 + 96 + 16 = 592 тайла в канонической карте; объединённый вселенная gid по всем 125 картам — **960**
(её распушает `metatiles` в четырёх картах, см. аномалии).

Исключение по тайл-размеру: `L01S04` объявляет `rocks` с `tilewidth="512" tileheight="48"` —
тайл размером со всю картинку, то есть **1** тайл вместо 96. Это единственный тайлсет не-16×16
(`tileset_tile_sizes = {"16x16": 363, "512x48": 1}`).

**4. Целостность диапазонов.** Перекрытий `firstgid` нет ни в одной карте
(`firstgid_overlaps = []`). Единственный разрыв — `L01S04.tmx`: дыра **gid 481…490** между
`tiles`(1–480) и `rocks`(491…491).

**5. Используемые gid.** Покрашено **13 088** ненулевых тайлов из 115 920 ячеек (11,3%).
Используется **41** distinct gid, минимум 1, максимум 491. **Каждый** использованный gid попадает
в объявленный диапазон своего файла: список внедиапазонных gid пуст —
`gids_outside_declared_ranges = []`, счётчик 0. Флипов/поворотов (`0xE0000000`-биты) — 0 вхождений,
отрицательных gid — 0.

Распределение покрытия картами: gid **1** — в 121 карте, gid **481** — в 4 картах, gid 227/228/229/237/
243/244/245/246/250/252 — в 3 картах, и 21 gid используется ровно одной картой. По числу тайлов
доминирует gid 1 — 12 124 тайла (92,6% всех painted), дальше gid 481 — 199, gid 228 — 124.

Полный список всех 41 используемого gid:
`1, 2, 7, 25, 26, 27, 28, 29, 40, 41, 42, 43, 44, 58, 59, 60, 73, 91, 92, 93, 106, 107, 108, 227, 228,
229, 237, 243, 244, 245, 246, 250, 251, 252, 323, 324, 325, 326, 327, 481, 491`.
Из них **39** лежат в `tiles`(1…480), **2** — в камнях (`481`, и `491` только в `L01S04`);
диапазон `generated_terrain` (577…592) **не используется ни в одной из 117 карт, которые его объявляют**.

Обратная сторона: из 960 объявленных gid **никогда не рисуется 919** (`declared_but_never_used_gids`).
Слои `Collision` во всех 125 картах содержат ровно **один** distinct gid: `1` в 121 карте и `481`
в `L01S05`, `L01S06`, `L01S07`, `L01S08`; плотность collision-тайлов — от 23 до 213 на карту.

## Атрибуты объектов

Всего **680** объектов, распределение по картам — от 1 до 12 (мода 6: 26 карт).

**1. Атрибуты элемента `<object>`.**

| Атрибут | Объектов (из 680) |
|---|---|
| `name` | 680 |
| `x` | 680 |
| `y` | 680 |
| `id` | **632** (48 без id) |
| `width` | **360** (320 без) |
| `height` | **360** (320 без) |
| `type` | **0** |
| `gid` | **0** |
| `rotation` | **0** |
| `visible` | **0** |
| `template` | **0** |
| `class` | **0** |

Ни one tile-object (`gid`), ни prototype-ссылок (`template`), ни поворотов (`rotation`), ни `type`/`class`:
вся семантика объекта несётся `name` + `<properties>`. Дублирующихся `id` внутри карты — 0.
Все 48 объектов без `id` сосредоточены в 8 legacy-картах (`L01S01`:12, `L01S02`:6, `L01S03`:6,
`L01S04`:5, `L01S05`:3, `L01S06`:3, `L01S07`:7, `L01S08`:6) и они же — единственные, у кого нет и
`width`/`height`.

**2. Координаты.** Атрибуты `x`/`y` присутствуют у **680/680**; отсутствующих — 0
(`objects_missing_x_or_y = 0`), нечисловых и нецелых — 0 (`objects_non_integer_xy = []`).
Диапазон: `x ∈ [0, 512]`, `y ∈ [0, 384]`.

- **28 объектов стоят ровно в (0, 0)**. Это не «потерянные» координаты: у всех 28 атрибуты `x="0" y="0"`
  записаны явно, все 28 называются `bubble_creator` и несут один и тот же набор свойств —
  `behavior=swing`, `delay=1.0`, `sourceBlock=blk_anim_swarm`. Лежат в 15 картах
  (13 карт по 2 штуки, `L01S22` и `L03S18` по 1). Полный список:
  `L01S21#3`, `L01S21#4`, `L01S22#6`, `L02S06#3`, `L02S06#4`, `L02S10#3`, `L02S10#4`, `L02S14#3`,
  `L02S14#4`, `L02S22#3`, `L02S22#4`, `L03S03#4`, `L03S03#5`, `L03S17#3`, `L03S17#4`, `L03S18#5`,
  `L03S22#3`, `L03S22#4`, `L04S24#3`, `L04S24#4`, `L05S06#3`, `L05S06#4`, `L05S10#3`, `L05S10#4`,
  `L05S14#3`, `L05S14#4`, `L05S22#3`, `L05S22#4` (карта#id).
- Дополнительно **16 объектов выходят за пиксельную коробку карты**: у всех `y="384"` (= 24×16, строка
  ровно за нижней границей сетки), `x` в диапазоне, имя у всех — `piston`, файлы:
  `L01S14`, `L01S15` (3), `L02S15`, `L02S23` (3), `L03S18`, `L03S23`, `L04S16` (2), `L05S15`,
  `L05S23` (3).

**3. Кастомные `<property>`.** На объектах 862 элемента свойства, **6 distinct имён**:

| Имя свойства | Объектов | Домен значений |
|---|---|---|
| `sourceBlock` | **515** | 25 значений, все `blk_*`; топ: `blk_teleportGate` 66, `blk_mine` 50, `blk_box_white` 46, `blk_anim_pump` 45, `blk_box_yellow` 35, `blk_anim_swarm` 28, `blk_waggon` 24, `blk_tower_rocket` 23, `blk_birthpod` 21, `blk_blinker` 19, `blk_double_barrel` 18, `blk_gunMachine_BOTTOM` 18, `blk_gunMachine_TOP` 18, `blk_gunMachine1` 15, `blk_beacon_base` 13, `blk_control_beacon` 13, `blk_beam_down` 10, `blk_beam_up` 10, `blk_tower_dish` 10, `blk_mushroom` 9, `blk_gate_green` 6, `blk_ship` 6, `blk_changing_room` 5, `blk_stage_end` 5, `blk_topdown_electro` 2 |
| `sourceX` | **145** | 25 значений, целые 2…28 |
| `sourceY` | **145** | 18 значений, целые 0…19 |
| `behavior` | 28 | единственный член: `swing` |
| `delay` | 28 | единственный член: `1.0` |
| `coordinateMode` | 1 | единственный член: `tiledRect` (один объект `capsule`, `L01S10`, id 5) |

Орфографических вариантов имён свойств нет (`property_name_spelling_variants = {}`).
`sourceX`/`sourceY` **всегда идут парой**: 145 объектов с обоими, 0 объектов только с одним,
535 — без обоих. То есть «половинчатой» пары в shipped-данных сегодня нет.

Сигнатуры наборов свойств (5 вариантов на 680 объектов): `sourceBlock` — 341; ничего — 165;
`sourceBlock,sourceX,sourceY` — 145; `behavior,delay,sourceBlock` — 28; `coordinateMode,sourceBlock` — 1.

Разрезы по именам объектов (20 distinct имён; `объектов / карт`): `source_marker` 127/63,
`vitorc` 125/125, `teleport` 70/35, `mine` 53/24, `ammo_pack` 48/48, `piston` 46/27,
`grenade_pack` 38/38, `turret` 37/33, `bubble_creator` 31/18, `rocket` 29/15, `incubator` 22/18,
`double_launcher` 19/18, `radar` 12/9, `ship` 7/7, `gate` 6/5, `light_ceiling` 3/1, `light_floor` 3/1,
`ship_fire` 2/1, `capsule` 1/1, `cocoon` 1/1. Ровно один `vitorc` (точка появления) есть в каждой из
125 карт — это единственный всепокрывающий объект. `source_marker` всегда несёт всю тройку
`sourceBlock,sourceX,sourceY`; у `turret` конвенция смешана: 18 с тройкой, 15 только `sourceBlock`,
4 без свойств.

`width`/`height` (360 объектов): значения `width` — {32:132, 64:128, 48:45, 96:33, 176:12, 80:10};
значения `height` — {96:110, 32:81, 16:50, 64:45, 80:34, 48:18, 128:16, 144:6}; все кратны 16.

**4. Свойства уровня (`<map><properties>`).** 495 элементов, 9 distinct имён: `background_color` 125
(единственное значение `#000000`), `nextLevel` 124, `zoneSource` 121 (4 различных строки-провенанса),
`zoneNumber` 117 (обнуляемые до 3 знаков, непрерывно 008…124, каждое один раз) плюс 8 «одноразовых»
легаси-ключа: `originalSource` (`L01S01`, `L01S02`), `referenceSource` (`L01S03`),
`referenceObjects` (`L01S04`), `step9Corrected` (`L01S05`, `L01S06`), `step9Progress`
(`L01S07`, `L01S08`). `nextLevel`: 124 ребра, все 124 цели существуют в поставке, каждая цель
использована ровно один раз (ветвления нет); `L05S25.tmx` — единственная карта без `nextLevel`
(терминальная), `L01S01.tmx` — единственная, на которую никто не ссылается (вход).
`zoneNumber` совпадает с номером
картинки imagelayer во всех 117 случаях, а номер картинки = порядковый индекс карты минус 1
во всех 120 случаях (`zone_008_original.png` ↔ `L01S09`); без `zoneNumber` остались те же 8 legacy-карт.

## Расхождения и аномалии

1. **Раскол поколений 8 vs 117.** `L01S01…L01S08` одновременно отличаются кодированием (`base64`
   в `L01S01…L01S04`), составом тайлсетов, порядком слоёв (collision **поверх** объектов), именами
   слоёв (`Object Layer 1`, `Original Scenery`, `Tile Layer N`), отсутствием `id` у 48 объектов
   и отсутствием провенанс-свойств `zoneNumber`/`zoneSource`. Любой «канон» схемы, выведенный по
   117 картам, молча ломается на этих восьми; наоборот, 117 карт между собой различаются только
   данными.
2. **`L01S04.tmx` — самый дефектный файл выборки.** Ссылается на две отсутствующие картинки за пределами
   `Resources/` (`../images/tiles.gif`, `../images/rocks.gif`); объявляет `rocks` с тайлом 512×48
   (1 тайл вместо 96); единственный в наборе имеет разрыв `firstgid` (дыра 481…490); единственный
   имеет `visible="0"` на слое `Collision`, то есть невидимая коллизия; и это единственная карта с
   полностью пустым слоем `Stars` (0 ненулевых тайлов из 840).
3. **Двойное объявление одной картинки.** В `L01S05…L01S08` `tiles.png` объявлен дважды: как `tiles`
   (firstgid 1, gid 1…480) и как `metatiles` (firstgid 481, gid 481…960). Формального перекрытия
   диапазонов нет, но gid 481…576 в этих картах разрешается в тот же тайл `tiles.png`, что и gid 1…16,
   а в 117 канонических картах gid 481…576 — это уже `rocks.png`. Один и тот же gid значит разное
   в разных файлах; вселенная объявленных gid из-за этого раздувается с 592 до 960.
4. **Молчаливый ноль измерен, но не как «опечатка».** Опечаток в именах слоёв/свойств в данных нет
   (`variants` и `property_name_spelling_variants` пусты), атрибутов `x`/`y` не хватает ни у одного
   объекта, нецелых значений нет. 28 объектов в (0,0) — **явно** записанные нули, и это всегда
   `bubble_creator`+`behavior=swing`. Так что «тихий ноль» в shipped-данных сегодня существует
   не как следствие опечатки, а как 28 валидных на вид записей, у которых нулевая позиция
   осмысленна только если координата берётся из чего-то ещё (а `sourceX`/`sourceY` у них **отсутствуют** —
   у этих 28 есть только `sourceBlock`).
5. **16 `piston` вне поля.** `y=384` — ровно на строку ниже 24-строчной сетки; при пересчёте
   `y/16` это ячейка 24, которой в карте нет.
6. **Мёртвый тайлсет.** `generated_terrain.png` объявлен в **117** картах (gid 577…592, 16 тайлов),
   но ни один gid из этого диапазона не нарисован ни в одном файле выборки — слой `Collision`
   использует единственный gid, а декоративные слои есть только в 8 legacy-картах, где этого тайлсета
   нет. Вместе с п.5 это даёт 919 из 960 объявленных gid без единого тайла.
7. **Чистка «неиспользуемых» gid небезопасна.** Объявления покрывают все 480 тайлов `tiles.png`,
   хотя из `tiles`-диапазона рисуется 39 gid; в `L01S05…L01S08` те же gid 481…576 разрешаются
   в `tiles.png` повторно (п.3), поэтому удалённый «мусор» меняет смысл этих четырёх файлов.
8. **Фон уже карты.** Все 120 imagelayer-картинок 512×384 px, а карта 560×384 px: 3 правые колонки
   тайлов (48 px) не имеют пиксельного слоя фона ни в одной карте. Атрибутов `offsetx`/`offsety`
   у imagelayer нет нигде, то есть сдвиг компенсировать нечем.
9. **Формат XML-drift.** `<?xml version='1.0' encoding='UTF-8'?>` в 120 файлах и `encoding='utf-8'`
   в 5; завершающий перевод строки есть только в 2 файлах из 125. На данные не влияет, но ломает
   «побайтовое равное» сравнение при перегенерации.
10. **Что не является аномалией (зафиксировано как норма):** `orientation`, `version`, тайл-размер,
   размер карты, число объектных групп, `nextLevel`-цепочка, наличие `vitorc`, покрытие gid,
   кратность картинок тайлу, совпадение `zoneNumber` с фоном — отклонений 0.

### JSON-блоб ценза

```json
{
 "1_map_header": {
  "distinct_map_sizes": 1,
  "file_bytes": {
   "max": 19251,
   "mean": 4094.3,
   "min": 2850,
   "total": 511783
  },
  "map_attributes_present_on_all_files": {
   "height": 125,
   "orientation": 125,
   "tileheight": 125,
   "tilewidth": 125,
   "version": 125,
   "width": 125
  },
  "map_size_distribution_tiles": {
   "35x24": 125
  },
  "map_size_px": [
   560,
   384
  ],
  "orientation_attr": {
   "orthogonal": 125
  },
  "tilewidth_tileheight": {
   "16x16": 125
  },
  "version_attr": {
   "1.0": 125
  },
  "xml_declaration_format": {
   "decl=<?xml version='1.0' encoding='UTF-8'|trailing_newline=False": 120,
   "decl=<?xml version='1.0' encoding='utf-8'|trailing_newline=False": 3,
   "decl=<?xml version='1.0' encoding='utf-8'|trailing_newline=True": 2
  }
 },
 "2_encoding_storage_layers": {
  "base64_layer_files": {
   "L01S01.tmx": [
    "Tile Layer 1",
    "Collision"
   ],
   "L01S02.tmx": [
    "Tile Layer 1",
    "Collision"
   ],
   "L01S03.tmx": [
    "Tile Layer 1",
    "Collision"
   ],
   "L01S04.tmx": [
    "Stars",
    "Tile Layer 1",
    "Tile Layer 2",
    "Collision"
   ]
  },
  "base64_layers_are_uncompressed_le_uint32": true,
  "data_compression_attr_present": {
   "None": 138
  },
  "data_encoding_attr": {
   "base64": 10,
   "csv": 128
  },
  "decoded_count_ne_expected_cells": [],
  "imagelayer_image_count_distinct": 120,
  "imagelayer_image_px_uniform": [
   [
    512,
    384
   ]
  ],
  "imagelayer_names_maps_using": {
   "Original Scenery": 2,
   "Original Static Scenery": 118
  },
  "imagelayer_offset_attrs_present": 0,
  "imagelayers_per_map_distribution": {
   "0": 5,
   "1": 120
  },
  "layer_level_custom_properties": {
   "imagelayer": {},
   "objectgroup": {},
   "tilelayer": {}
  },
  "layer_visible_attr_instances": [
   {
    "attr": "visible",
    "file": "L01S04.tmx",
    "layer": "Collision",
    "value": "0"
   }
  ],
  "layer_wh_differs_from_map": [],
  "maps_where_collision_layer_is_after_objectgroup": [
   "L01S01.tmx",
   "L01S02.tmx",
   "L01S03.tmx",
   "L01S04.tmx",
   "L01S05.tmx",
   "L01S06.tmx",
   "L01S07.tmx",
   "L01S08.tmx"
  ],
  "maps_without_imagelayer": [
   "L01S01.tmx",
   "L01S02.tmx",
   "L01S03.tmx",
   "L01S04.tmx",
   "L01S07.tmx"
  ],
  "objectgroup_names_maps_using": {
   "Object Layer 1": 6,
   "Objects": 119
  },
  "objectgroup_redundant_wh_attrs": [
   "L01S01.tmx",
   "L01S02.tmx",
   "L01S03.tmx",
   "L01S04.tmx",
   "L01S05.tmx",
   "L01S06.tmx",
   "L01S07.tmx",
   "L01S08.tmx"
  ],
  "objectgroups_per_map_distribution": {
   "1": 125
  },
  "payload_decode_mode": {
   "base64:none-raw-little-endian-uint32": 10,
   "csv:None": 128
  },
  "tile_children_payloads": 0,
  "tilelayer_element_attrs_seen": {
   "height": 138,
   "name": 138,
   "visible": 1,
   "width": 138
  },
  "tilelayer_names_maps_using": {
   "Collision": 125,
   "Stars": 3,
   "Tile Layer 1": 7,
   "Tile Layer 2": 3
  },
  "tilelayers_per_map_distribution": {
   "1": 118,
   "2": 4,
   "4": 3
  },
  "tilelayers_total": 138,
  "top_level_child_order_variants": {
   "properties > tileset > layer > objectgroup > layer": 3,
   "properties > tileset > tileset > imagelayer > layer > layer > objectgroup > layer > layer": 2,
   "properties > tileset > tileset > imagelayer > objectgroup > layer": 1,
   "properties > tileset > tileset > layer > layer > objectgroup > layer > layer": 1,
   "properties > tileset > tileset > layer > objectgroup > layer": 1,
   "properties > tileset > tileset > tileset > imagelayer > layer > objectgroup": 117
  }
 },
 "3_tilesets_gid": {
  "canonical_ranges_117_maps": {
   "generated_terrain.png": [
    577,
    592
   ],
   "rocks.png": [
    481,
    576
   ],
   "tiles.png": [
    1,
    480
   ]
  },
  "cells_total": 115920,
  "collision_layer_gid_per_map": {
   "distinct_gids_per_map": "exactly 1 in all 125 maps",
   "gid_1_maps": 121,
   "gid_481_maps": [
    "L01S05.tmx",
    "L01S06.tmx",
    "L01S07.tmx",
    "L01S08.tmx"
   ],
   "gid_universe": [
    1,
    481
   ]
  },
  "declared_but_never_painted_gids_count": 919,
  "declared_gid_universe_size": 960,
  "declared_tilecount_attr_present_anywhere": false,
  "distinct_gids_painted": 41,
  "external_tsx_references": 0,
  "firstgid_values": {
   "1": 125,
   "481": 121,
   "491": 1,
   "577": 117
  },
  "gid_flip_flag_instances": [],
  "gid_min_max_painted": [
   1,
   491
  ],
  "gids_outside_declared_ranges": [],
  "gids_outside_declared_ranges_count": 0,
  "image_element_attrs_seen": {
   "height": 364,
   "source": 364,
   "width": 364
  },
  "image_geometry_implied_counts": {
   "../images/rocks.gif": {
    "declarations": 1,
    "exact_multiple": true,
    "firstgids": [
     491
    ],
    "image_wh": [
     512,
     48
    ],
    "implied_tile_count": 1,
    "tile_wh": [
     512,
     48
    ]
   },
   "../images/tiles.gif": {
    "declarations": 1,
    "exact_multiple": true,
    "firstgids": [
     1
    ],
    "image_wh": [
     240,
     512
    ],
    "implied_tile_count": 480,
    "tile_wh": [
     16,
     16
    ]
   },
   "generated_terrain.png": {
    "declarations": 117,
    "exact_multiple": true,
    "firstgids": [
     577
    ],
    "image_wh": [
     256,
     16
    ],
    "implied_tile_count": 16,
    "tile_wh": [
     16,
     16
    ]
   },
   "rocks.png": {
    "declarations": 117,
    "exact_multiple": true,
    "firstgids": [
     481
    ],
    "image_wh": [
     512,
     48
    ],
    "implied_tile_count": 96,
    "tile_wh": [
     16,
     16
    ]
   },
   "tiles.png": {
    "declarations": 128,
    "exact_multiple": true,
    "firstgids": [
     1,
     481
    ],
    "image_wh": [
     240,
     512
    ],
    "implied_tile_count": 480,
    "tile_wh": [
     16,
     16
    ]
   }
  },
  "image_sources": {
   "../images/rocks.gif": 1,
   "../images/tiles.gif": 1,
   "generated_terrain.png": 117,
   "rocks.png": 117,
   "tiles.png": 128
  },
  "maps_with_firstgid_gap": [
   {
    "file": "L01S04.tmx",
    "gaps": [
     [
      481,
      490
     ]
    ]
   }
  ],
  "maps_with_firstgid_overlap": [],
  "metatiles_alias_maps": {
   "L01S05.tmx": "1-480 + 481-960 both tiles.png",
   "L01S06.tmx": "1-480 + 481-960 both tiles.png",
   "L01S07.tmx": "1-480 + 481-960 both tiles.png",
   "L01S08.tmx": "1-480 + 481-960 both tiles.png"
  },
  "negative_gid_values": [],
  "painted_gid_by_map_coverage_top": {
   "1": 121,
   "227": 3,
   "228": 3,
   "229": 3,
   "237": 3,
   "243": 3,
   "244": 3,
   "245": 3,
   "246": 3,
   "25": 2,
   "250": 3,
   "252": 3,
   "26": 2,
   "27": 2,
   "28": 2,
   "40": 2,
   "41": 2,
   "42": 2,
   "43": 2,
   "481": 4
  },
  "source_vs_inline": {
   "inline <image> child": 364
  },
  "tiles_painted_nonzero": 13088,
  "tileset_element_attrs_seen": {
   "firstgid": 364,
   "name": 364,
   "tileheight": 364,
   "tilewidth": 364
  },
  "tileset_images_missing_on_disk": [
   "../images/tiles.gif",
   "../images/rocks.gif"
  ],
  "tileset_names": {
   "generated_terrain": 117,
   "metatiles": 4,
   "rocks": 118,
   "tiles": 125
  },
  "tileset_tile_sizes": {
   "16x16": 363,
   "512x48": 1
  },
  "tilesets_per_map_distribution": {
   "1": 3,
   "2": 5,
   "3": 117
  },
  "tilesets_total": 364,
  "tmx_declared_image_wh_vs_disk_wh_mismatch": []
 },
 "4_layer_naming": {
  "distinct_imagelayer_names": {
   "Original Scenery": 2,
   "Original Static Scenery": 118
  },
  "distinct_objectgroup_names": {
   "Object Layer 1": 6,
   "Objects": 119
  },
  "distinct_tilelayer_names": {
   "Collision": 125,
   "Stars": 3,
   "Tile Layer 1": 7,
   "Tile Layer 2": 3
  },
  "lexical_regime_drift": {
   "imagelayer": [
    "Original Static Scenery (118 maps)",
    "Original Scenery (2 maps: L01S05,L01S06)"
   ],
   "objectgroup": [
    "Objects (119 maps)",
    "Object Layer 1 (6 maps: L01S01-L01S06)"
   ],
   "tilelayer": [
    "Collision (semantic, 125 maps)",
    "Tile Layer 1 / Tile Layer 2 (Tiled default, 7 / 3 maps)",
    "Stars (3 maps)"
   ]
  },
  "pure_case_or_separator_variants": {
   "imagelayer": {},
   "object_name": {},
   "objectgroup": {},
   "tilelayer": {}
  }
 },
 "5_objects": {
  "custom_property_domain_sizes": {
   "behavior": 1,
   "coordinateMode": 1,
   "delay": 1,
   "sourceBlock": 25,
   "sourceX": 25,
   "sourceY": 18
  },
  "custom_property_elements_total": 862,
  "custom_property_names_on_objects": {
   "behavior": 28,
   "coordinateMode": 1,
   "delay": 28,
   "sourceBlock": 515,
   "sourceX": 145,
   "sourceY": 145
  },
  "custom_property_value_domains": {
   "behavior": {
    "swing": 28
   },
   "coordinateMode": {
    "tiledRect": 1
   },
   "delay": {
    "1.0": 28
   },
   "sourceBlock": {
    "blk_anim_pump": 45,
    "blk_anim_swarm": 28,
    "blk_beacon_base": 13,
    "blk_beam_down": 10,
    "blk_beam_up": 10,
    "blk_birthpod": 21,
    "blk_blinker": 19,
    "blk_box_white": 46,
    "blk_box_yellow": 35,
    "blk_changing_room": 5,
    "blk_control_beacon": 13,
    "blk_double_barrel": 18,
    "blk_gate_green": 6,
    "blk_gunMachine1": 15,
    "blk_gunMachine_BOTTOM": 18,
    "blk_gunMachine_TOP": 18,
    "blk_mine": 50,
    "blk_mushroom": 9,
    "blk_ship": 6,
    "blk_stage_end": 5,
    "blk_teleportGate": 66,
    "blk_topdown_electro": 2,
    "blk_tower_dish": 10,
    "blk_tower_rocket": 23,
    "blk_waggon": 24
   },
   "sourceX": {
    "10": 7,
    "11": 8,
    "12": 8,
    "13": 4,
    "14": 9,
    "15": 6,
    "16": 5,
    "17": 6,
    "18": 8,
    "19": 8,
    "2": 1,
    "20": 8,
    "21": 4,
    "22": 5,
    "23": 3,
    "24": 8,
    "25": 11,
    "26": 9,
    "27": 5,
    "28": 6,
    "5": 2,
    "6": 6,
    "7": 3,
    "8": 1,
    "9": 4
   },
   "sourceY": {
    "0": 10,
    "1": 2,
    "10": 4,
    "11": 8,
    "13": 14,
    "14": 16,
    "15": 22,
    "16": 17,
    "17": 7,
    "18": 7,
    "19": 3,
    "2": 5,
    "3": 5,
    "4": 3,
    "5": 3,
    "6": 11,
    "8": 5,
    "9": 3
   }
  },
  "distinct_object_names_element_count": {
   "ammo_pack": 48,
   "bubble_creator": 31,
   "capsule": 1,
   "cocoon": 1,
   "double_launcher": 19,
   "gate": 6,
   "grenade_pack": 38,
   "incubator": 22,
   "light_ceiling": 3,
   "light_floor": 3,
   "mine": 53,
   "piston": 46,
   "radar": 12,
   "rocket": 29,
   "ship": 7,
   "ship_fire": 2,
   "source_marker": 127,
   "teleport": 70,
   "turret": 37,
   "vitorc": 125
  },
  "duplicate_object_ids_within_map": [],
  "object_element_attribute_counts": {
   "height": 360,
   "id": 632,
   "name": 680,
   "width": 360,
   "x": 680,
   "y": 680
  },
  "object_height_values": {
   "128": 16,
   "144": 6,
   "16": 50,
   "32": 81,
   "48": 18,
   "64": 45,
   "80": 34,
   "96": 110
  },
  "object_name_map_coverage": {
   "ammo_pack": 1,
   "bubble_creator": 1,
   "capsule": 1,
   "cocoon": 1,
   "double_launcher": 1,
   "gate": 1,
   "grenade_pack": 1,
   "incubator": 1,
   "light_ceiling": 1,
   "light_floor": 1,
   "mine": 1,
   "piston": 1,
   "radar": 1,
   "rocket": 1,
   "ship": 1,
   "ship_fire": 1,
   "source_marker": 1,
   "teleport": 1,
   "turret": 1,
   "vitorc": 1
  },
  "object_name_x_property_signature": {
   "ammo_pack": {
    "": 2,
    "sourceBlock": 46
   },
   "bubble_creator": {
    "": 3,
    "behavior,delay,sourceBlock": 28
   },
   "capsule": {
    "coordinateMode,sourceBlock": 1
   },
   "cocoon": {
    "": 1
   },
   "double_launcher": {
    "": 1,
    "sourceBlock": 18
   },
   "gate": {
    "sourceBlock": 6
   },
   "grenade_pack": {
    "": 3,
    "sourceBlock": 35
   },
   "incubator": {
    "": 1,
    "sourceBlock": 21
   },
   "light_ceiling": {
    "": 3
   },
   "light_floor": {
    "": 3
   },
   "mine": {
    "": 3,
    "sourceBlock": 50
   },
   "piston": {
    "": 1,
    "sourceBlock": 45
   },
   "radar": {
    "": 2,
    "sourceBlock": 10
   },
   "rocket": {
    "": 6,
    "sourceBlock": 23
   },
   "ship": {
    "": 1,
    "sourceBlock": 6
   },
   "ship_fire": {
    "": 2
   },
   "source_marker": {
    "sourceBlock,sourceX,sourceY": 127
   },
   "teleport": {
    "": 4,
    "sourceBlock": 66
   },
   "turret": {
    "": 4,
    "sourceBlock": 15,
    "sourceBlock,sourceX,sourceY": 18
   },
   "vitorc": {
    "": 125
   }
  },
  "object_property_signature_histogram": {
   "": 165,
   "behavior,delay,sourceBlock": 28,
   "coordinateMode,sourceBlock": 1,
   "sourceBlock": 341,
   "sourceBlock,sourceX,sourceY": 145
  },
  "object_width_values": {
   "176": 12,
   "32": 132,
   "48": 45,
   "64": 128,
   "80": 10,
   "96": 33
  },
  "objects_at_x0_y0": {
   "absent_x_or_y_attributed_objects": 0,
   "all_names": [
    "bubble_creator"
   ],
   "all_property_signature": [
    "behavior=swing",
    "delay=1.0",
    "sourceBlock=blk_anim_swarm"
   ],
   "by_file": {
    "L01S21.tmx": 2,
    "L01S22.tmx": 1,
    "L02S06.tmx": 2,
    "L02S10.tmx": 2,
    "L02S14.tmx": 2,
    "L02S22.tmx": 2,
    "L03S03.tmx": 2,
    "L03S17.tmx": 2,
    "L03S18.tmx": 1,
    "L03S22.tmx": 2,
    "L04S24.tmx": 2,
    "L05S06.tmx": 2,
    "L05S10.tmx": 2,
    "L05S14.tmx": 2,
    "L05S22.tmx": 2
   },
   "count": 28,
   "detail": [
    "L01S21.tmx#3:bubble_creator",
    "L01S21.tmx#4:bubble_creator",
    "L01S22.tmx#6:bubble_creator",
    "L02S06.tmx#4:bubble_creator",
    "L02S06.tmx#5:bubble_creator",
    "L02S10.tmx#8:bubble_creator",
    "L02S10.tmx#9:bubble_creator",
    "L02S14.tmx#3:bubble_creator",
    "L02S14.tmx#4:bubble_creator",
    "L02S22.tmx#8:bubble_creator",
    "L02S22.tmx#9:bubble_creator",
    "L03S03.tmx#5:bubble_creator",
    "L03S03.tmx#6:bubble_creator",
    "L03S17.tmx#6:bubble_creator",
    "L03S17.tmx#7:bubble_creator",
    "L03S18.tmx#5:bubble_creator",
    "L03S22.tmx#6:bubble_creator",
    "L03S22.tmx#7:bubble_creator",
    "L04S24.tmx#5:bubble_creator",
    "L04S24.tmx#6:bubble_creator",
    "L05S06.tmx#4:bubble_creator",
    "L05S06.tmx#5:bubble_creator",
    "L05S10.tmx#8:bubble_creator",
    "L05S10.tmx#9:bubble_creator",
    "L05S14.tmx#3:bubble_creator",
    "L05S14.tmx#4:bubble_creator",
    "L05S22.tmx#8:bubble_creator",
    "L05S22.tmx#9:bubble_creator"
   ]
  },
  "objects_missing_id": 48,
  "objects_missing_id_files": {
   "L01S01.tmx": 12,
   "L01S02.tmx": 6,
   "L01S03.tmx": 6,
   "L01S04.tmx": 5,
   "L01S05.tmx": 3,
   "L01S06.tmx": 3,
   "L01S07.tmx": 7,
   "L01S08.tmx": 6
  },
  "objects_missing_x_or_y": 0,
  "objects_non_integer_xy": [],
  "objects_outside_map_pixel_box": {
   "all_names": [
    "piston"
   ],
   "coordinate_pattern": "y == 384 (row 24, one row below the 24-row grid); x in range",
   "count": 16,
   "files": [
    "L01S14.tmx",
    "L01S15.tmx",
    "L02S15.tmx",
    "L02S23.tmx",
    "L03S18.tmx",
    "L03S23.tmx",
    "L04S16.tmx",
    "L05S15.tmx",
    "L05S23.tmx"
   ]
  },
  "objects_per_map_histogram": {
   "1": 3,
   "11": 1,
   "12": 1,
   "2": 3,
   "3": 14,
   "4": 22,
   "5": 22,
   "6": 26,
   "7": 18,
   "8": 9,
   "9": 6
  },
  "objects_total": 680,
  "property_name_spelling_variants": {},
  "sourceX_sourceY_pairing": {
   "both sourceX+sourceY": 145,
   "neither sourceX nor sourceY": 535
  },
  "standard_tmx_attrs_absent_from_every_object": {
   "class": 680,
   "gid": 680,
   "rotation": 680,
   "template": 680,
   "type": 680,
   "visible": 680
  },
  "vitorc_exactly_one_per_map": true,
  "xy_pixel_range": {
   "x_max": 512.0,
   "x_min": 0.0,
   "y_max": 384.0,
   "y_min": 0.0
  }
 },
 "6_map_properties": {
  "elements_total": 495,
  "maps_missing_nextLevel": [
   "L05S25.tmx"
  ],
  "maps_never_referenced_as_nextLevel": [],
  "maps_without_zoneNumber": [
   "L01S01.tmx",
   "L01S02.tmx",
   "L01S03.tmx",
   "L01S04.tmx",
   "L01S05.tmx",
   "L01S06.tmx",
   "L01S07.tmx",
   "L01S08.tmx"
  ],
  "names": {
   "background_color": 125,
   "nextLevel": 124,
   "originalSource": 2,
   "referenceObjects": 1,
   "referenceSource": 1,
   "step9Corrected": 2,
   "step9Progress": 2,
   "zoneNumber": 117,
   "zoneSource": 121
  },
  "nextLevel_edges": 124,
  "nextLevel_targets_all_present": true,
  "one_off_legacy_keys": {
   "originalSource": [
    "L01S01.tmx",
    "L01S02.tmx"
   ],
   "referenceObjects": [
    "L01S04.tmx"
   ],
   "referenceSource": [
    "L01S03.tmx"
   ],
   "step9Corrected": [
    "L01S05.tmx",
    "L01S06.tmx"
   ],
   "step9Progress": [
    "L01S07.tmx",
    "L01S08.tmx"
   ]
  },
  "scenery_image_number_equals_seq_index_minus_1": true,
  "values_compact": {
   "background_color": {
    "#000000": 125
   },
   "full_value_lists_in": "census.json:aggregate.6_map_properties.map_level_property_values",
   "nextLevel": "124 distinct targets, each used exactly once; every target is a shipped LxxSxx.tmx; L05S25.tmx has no nextLevel (terminal)",
   "originalSource": {
    "newagebegins/exolon maps/L01S01.tmx": 1,
    "newagebegins/exolon maps/L01S02.tmx": 1
   },
   "referenceObjects": {
    "newagebegins/exolon L01S04": 1
   },
   "referenceSource": {
    "newagebegins/exolon maps/L01S03.tmx": 1
   },
   "step9Corrected": {
    "authoritative original zone 004 layout": 1,
    "authoritative original zone 005 layout": 1
   },
   "step9Progress": {
    "original zone 006 source reconstruction": 1,
    "original zone 007 source reconstruction": 1
   },
   "zoneNumber": "117 values, zero-padded 3-digit, contiguous 008..124, each once",
   "zoneSource": {
    "rusarh/exolon-esl asm/data_zone_data.asm": 117,
    "rusarh/exolon-esl data_zone_data.asm + actions_mines.asm": 1,
    "rusarh/exolon-esl data_zone_data.asm + verified object behavior": 1,
    "rusarh/exolon-esl original zone_data.asm + original walkthrough": 2
   }
  },
  "zoneNumber_equals_scenery_image_number": true
 },
 "7_anomalies": {
  "decode_errors": 0,
  "explicit_0_0_objects": 28,
  "firstgid_gap_only_map": "L01S04.tmx (481-490)",
  "flip_or_negative_gids": 0,
  "layer_visible_zero": "L01S04.tmx Collision",
  "legacy_generation_split": {
   "canonical_shape_maps": 117,
   "count": 8,
   "differs_in": [
    "encoding (base64 in L01S01-L01S04)",
    "tileset count/firstgid layout",
    "layer z-order (Collision above objectgroup)",
    "objectgroup + imagelayer naming",
    "missing object id",
    "missing zoneNumber/zoneSource provenance keys"
   ],
   "files": [
    "L01S01.tmx",
    "L01S02.tmx",
    "L01S03.tmx",
    "L01S04.tmx",
    "L01S05.tmx",
    "L01S06.tmx",
    "L01S07.tmx",
    "L01S08.tmx"
   ]
  },
  "missing_referenced_tileset_images": [
   "../images/tiles.gif",
   "../images/rocks.gif"
  ],
  "objects_one_row_below_grid": 16,
  "out_of_range_gids": 0,
  "scenery_png_narrower_than_map": "512px image vs 560px map (3 tile columns uncovered)",
  "single_tile_512x48_tileset": "L01S04.tmx rocks",
  "tiles_png_declared_twice_in_same_map": [
   "L01S05.tmx",
   "L01S06.tmx",
   "L01S07.tmx",
   "L01S08.tmx"
  ]
 },
 "meta": {
  "decoder": "stdlib ElementTree + base64/csv tile decode",
  "full_artifact_bytes": 616123,
  "full_artifact_sha256": "016acc4454bfcf5e78061a099816fa422b95d95f639085fe4843efd52b9da0ec",
  "full_per_map_artifact": "/tmp/lane-census/census.json",
  "git_head": "52795d13d879ad477a3023cae69978436ff82d1a",
  "glob": "Exolon/Resources/*.tmx",
  "lane": "tmx-census (data only, read-only)",
  "layer_decode_errors": 0,
  "layers_decoded_ok": 138,
  "repo": "<repo>",
  "tmx_files": 125
 }
}
```

Вердикт: pass
