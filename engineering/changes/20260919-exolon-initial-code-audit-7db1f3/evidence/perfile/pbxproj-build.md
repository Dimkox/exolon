# Lane сборки/упаковки: `project.pbxproj`, `Info.plist`, scheme-слой

HEAD `52795d1`. Только чтение репозитория; скрипты и полный вывод прогона —
`/tmp/lane-pbx/` (`audit.py` — полный разбор OpenStep-plist + аудит, `shipcheck.py`,
`names.py`, `out.txt`). Метод: собственный рекурсивный парсер `project.pbxproj`
(620 объектов разобраны без ошибок) + join с файловальной системой и с литералами Swift/TMX.
`xcodebuild` на этом хосте **не запускался и запустить его нельзя** — ни одна строка ниже
не является результатом сборки; всё, что требует macOS, вынесено в последний раздел.

Проверяемые артефакты: `Exolon.xcodeproj/project.pbxproj` (1474 строки, 133 718 байт,
`objectVersion = 51`), `Exolon/Resources/Info.plist` (24 строки), `Exolon/` (300 файлов),
`Exolon/GameCore/Effects/ExplosionEffect.swift` (только поверхность настроек эффекта).

## Итог

| метрика | значение |
|---|---|
| объектов в pbx / уникальных UUID | **620 / 620** |
| дубликатов UUID верхнего уровня | **0** |
| «висячих» ссылок (фаза → несуществующий объект, `fileRef` → несуществующий) | **0** |
| `PBXBuildFile`, не входящих ни в одну фазу (сироты) | **0** |
| пустых build-фаз | **0** (Sources 18, Frameworks 3, Resources 276) |
| перекрёстной членки (`.swift` в Resources, картинка/`.tmx`/`.plist` в Sources) | **0** |
| pbx-записей с несуществующим репозиторным путём | **0** |
| файлов на диске под `Exolon/` без `PBXFileReference` | **5** |
| `.swift` на диске ↔ в `PBXSourcesBuildPhase` | **18 ↔ 18** (полное покрытие) |
| `.xcscheme` в репозитории (любых, включая `xcshareddata`) | **0** |
| `PBXNativeTarget` | **1** (`Exolon`, application); тест-таргета нет |
| расхождение версии продукта (pbx `0.5` против бандла `0.3`) | **есть, P1** |

Раздел «целостность графа» — чист: ни дублей UUID, ни висячих ссылок, ни мусорных
build-файлов, ни осиротевших групп. Ни один файл не теряется при компиляции:
все 18 `.swift` в `Sources`, все 276 ресурса в `Resources`.

Дефекты сосредоточены в **настройках, решающих поведение артефакта**, и в **отсутствии
scheme-слоя**: собранный `.app` представится версией `0.3` при проектном `0.5`
(`GENERATE_INFOPLIST_FILE = NO`, а `Info.plist` не ссылается на `$(MARKETING_VERSION)`);
подпись ad-hoc (`CODE_SIGN_IDENTITY = "-"`) без hardened runtime; иконок нет ни в
`Info.plist`, ни в сборке (`.xcassets`/`.icns` в дереве отсутствуют); Debug и Release
конфигурации побайтово идентичны на обоих уровнях.

Отдельно по `ExplosionEffect.swift` — настройки эффекта **подтверждены против реального
арта**: `blaster_explosion.png` = 80×16 → ровно 5 кадров по 16×16 (код: `frameCount = 5`,
`frameSize 16×16`, строка 24–27); `circular_explosion.png` = 320×32 → ровно 10 кадров по
32×32 (код: `frameCount = 10`, `frameSize 32×32`, строка 28–31). Горизонтальная нарезка
`x = index/count, width = 1/count, height = 1` для этих атласов корректна; обе текстуры
входят в `PBXResourcesBuildPhase`. Расхождений размера кадров и геометрии нарезки — 0.

## Расхождения pbx ↔ диск

### Список 1 — записи pbx, пути которых нет на диске

Полный разбор всех 299 `PBXFileReference` с пересбором путём по цепочке `PBXGroup`
(`mainGroup` → `Exolon` → подгруппы) и проверкой `os.path.exists` на case-sensitive
файловой системе. Репозиторных путей, которых нет на диске: **0**.

Ниже — 4 записи, формально не решаемых относительно корня репозитория, и почему это
не дефект (они и не должны быть в дереве):

| путь | UUID | строка | sourceTree | квалификация |
|---|---|---|---|---|
| `System/Library/Frameworks/Cocoa.framework` | `2000…0011` | 319 | `SDKROOT` | внутри macOS SDK, норма |
| `System/Library/Frameworks/SpriteKit.framework` | `2000…0012` | 320 | `SDKROOT` | внутри macOS SDK, норма |
| `System/Library/Frameworks/GameController.framework` | `2000…0013` | 321 | `SDKROOT` | внутри macOS SDK, норма |
| `Exolon.app` | `2000…0010` | 318 | `BUILT_PRODUCTS_DIR` | выход продукта, `includeInIndex = 0`, норма |

**Итого по списку 1: настоящих отсутствующих путей — 0 из 295 репозиторных ссылок.**
Побочный вывод: совпадение регистра имён полное (на Linux регистрозависимая проверка
ловит `Ship.png` против `ship.png` — таких случаев 0), то есть `pbx` пережил перенос
с APFS без повреждения имён.

### Список 2 — файлы на диске без `PBXFileReference` (не скомпилируются и не попадут в бандл)

| файл | размер/свойства | вердикт |
|---|---|---|
| `Exolon/Resources/bubble.gif` | 1 кадр | мёртв: код просит `"bubble"` (`LevelObstacles.swift:444`), что резолвится на **попавший в бандл** `bubble.png` |
| `Exolon/Resources/rocks.gif` | 1 кадр | упомянут только как `../images/rocks.gif` внутри `L01S04.tmx:12`; рендерер берёт `lastPathComponent` без расширения (`TMXTileMapRenderer.swift:23-25`) → `"rocks"` → попавший в бандл `rocks.png` |
| `Exolon/Resources/turret_bullet.gif` | 1 кадр | в коде только в комментарии (`LevelObstacles.swift:74`); lookup-имя `"turret_bullet"` (`:138`) резолвится на попавший в бандл `turret_bullet.png` |
| `Exolon/Resources/light.png` | 128×32 | никем не именуется: `grep -rn '"light'` по Swift → 0; используются `light_floor`/`light_ceiling` |
| `Exolon/Resources/ship_fire.png` | 48×128 | никем не именуется: объект `case "ship_fire"` грузит `ship_fire_frame` (`TMXLevelRuntime.swift:342-343`) |

**Итого по списку 2: 5 файлов из 300.** Все 5 отслеживаются в git (`git ls-files` подтверждает,
неотслеживаемых файлов под `Exolon/` — 0), то есть они есть у каждого, кто клонирует репозиторий,
но в бандл не попадают. Проверка «не теряет ли игра текстуру» сделана обратным join'ом:
собраны все имена, которые код запрашивает у бандла (`SKTexture(imageNamed:)` — 23 места,
`Bundle.url(forResource:)`, стемы из `<image source=…>` всех 125 `.tmx`), и сверены с
`PBXResourcesBuildPhase` → **несопоставленных имён 0**. То есть список 2 — это мёртвый вес в
репозитории (5 файлов), а не дыра в бандле. Числа точно сходятся с соседней lane
`perfile/assets-bundle.md` (276 в фазе, 6 вне фазы, 0 подвешенных).

Отдельный, правильный случай: `Exolon/Resources/Info.plist` имеет `PBXFileReference`
(`2000…0009`, строка 317) и висит в группе `Resources` (строка 726), но **не** входит в
`PBXResourcesBuildPhase` — при `INFOPLIST_FILE` это единственно верное состояние; попади он
в фазу, в бандле появился бы второй `Contents/Resources/Info.plist` поверх системного.
`PBXShellScriptBuildPhase` в проекте нет вообще, поэтому «второго источника» `Info.plist`
(генерации или shell-копирования) тоже нет: конфликт `INFOPLIST_FILE` против inline-фазы
отсутствует.

### Целостность графа (пункт 2 задания)

| проверка | результат |
|---|---|
| дубликаты UUID верхнего уровня | **0**; единственное совпадение регулярки — `5000…0001` на строках 1028 (объект `PBXNativeTarget`) и 1053 (вложенный ключ `TargetAttributes`), это вложенный словарь, а не второй объект |
| `PBXBuildFile.fileRef` → несуществующий объект | 0 |
| `PBXBuildFile` без `fileRef` | 0 |
| позиция фазы → несуществующий объект / объект не `PBXBuildFile` | 0 |
| `PBXBuildFile`, не перечисленный ни в одной фазе | 0 |
| дублирование одной пары (`fileRef`, фаза) | 0 |
| `PBXFileReference` вне любой `PBXGroup` (невидим в навигаторе) | 0 |
| `PBXGroup`, недостижимых из `mainGroup` | 0 (13 групп, все достижимы; пути групп = `Exolon`, `GameCore`, `Player`, `Weapons`, `Effects`, `Objects`, `Levels`, `Platform`, `macOS`, `Resources`, + виртуальные `Frameworks`, `Products`) |
| `XCBuildConfiguration` вне `XCConfigurationList` | 0 |
| пустые фазы / фазы вне `buildPhases` таргета | 0 (порядок `Sources → Frameworks → Resources`) |
| `.swift` в `Resources` или ресурс в `Sources` | 0 |
| `.framework` в `Sources`/`Resources` | 0 (3 framework-записи только в `PBXFrameworksBuildPhase`) |

Наблюдение, важное для сопровождения: в файлом сосуществуют **4 непересекающихся схемы
генерации UUID** — `10000000…/20000000…` (59 + 61 записей, синтетические «ручные»),
`9A…/9B…` (по 117), `9C…/9D…` (по 3) и настоящие Xcode-подобные пары `A1……/A2……` (117).
Такой набор означает, что файл дописывался скриптом/вручную, а не только писателем Xcode.
Генератор `pbxproj` в репозитории отсутствует (`grep -rln "pbxproj\|PBXFileReference"
scripts/ factory/` → 0 совпадений), вся история файла — один коммит импорта `403eb13`.
То есть легального пути добавления ресурса нет: следующий автор вынужден будет руками
редактировать 1474 строки, и именно так в список 2 и попадают неиспользуемые файлы.

## Таблица build settings

Значения — фактические, из `XCBuildConfiguration` (4 блока, строки 1388–1449).
«Уровень» — где объявлено: П = проект (`9000…0001`), Т = таргет (`9000…0002`).
Колонка Debug/Release: **одинаково** везде, где написано «=».

| setting | Debug | Release | ур. | факт и следствие |
|---|---|---|---|---|
| `SWIFT_VERSION` | `5.0` | `5.0` | П+Т | согласовано на обоих уровнях; Swift 6 strict-mode не включён; `main.swift` — top-level-код, при переводе в Swift 6/`-parse-as-library` сломается |
| `MACOSX_DEPLOYMENT_TARGET` | `10.14` | `10.14` | П+Т | 10.14 объявлен и на проекте, и на таргете (дублирование, не конфликт) |
| `LSMinimumSystemVersion` (`Info.plist:21`) | `10.14` | `10.14` | plist | **литерал, не `$(MACOSX_DEPLOYMENT_TARGET)`**: сегодня сходится, но при подъёме deployment target пол в plist замрёт на 10.14 → Gatekeeper/Finder разрешат запуск на системе, где бинарь не работает |
| `SDKROOT` | `macosx` | `macosx` | П | норма |
| `MARKETING_VERSION` | `0.5` | `0.5` | Т | строки 1424/1443 |
| `CFBundleShortVersionString` (`Info.plist:18`) | **`0.3`** | **`0.3`** | plist | **P1-расхождение.** `GENERATE_INFOPLIST_FILE = NO`, а plist жёстко содержит `0.3` и нигде не ссылается на `$(MARKETING_VERSION)` → значение сборки `0.5` мертво, собранный `.app` показывает `0.3` |
| `CURRENT_PROJECT_VERSION` | `1` | `1` | Т | строки 1418/1437 |
| `CFBundleVersion` (`Info.plist:20`) | `1` | `1` | plist | литерал `1`; совпадение с `CURRENT_PROJECT_VERSION` случайное, не механическое (нет `$(CURRENT_PROJECT_VERSION)`) → следующий билд так же не поднимет build number |
| `INFOPLIST_FILE` | `Exolon/Resources/Info.plist` | … | Т | резолвится от `SRCROOT` = корень репозитория; файл существует; единственный источник plist |
| `GENERATE_INFOPLIST_FILE` | `NO` | `NO` | Т | inline-генерации нет; конфликта с фазой тоже нет (`Info.plist` вне `PBXResourcesBuildPhase`) |
| `ENABLE_HARDENED_RUNTIME` | **отсутствует** | отсутствует | — | дефолт `NO` → hardened runtime не включён; для notarization и обхода Gatekeeper при распространении вне MAS нужен `YES` |
| `CODE_SIGN_IDENTITY` | `-` | `-` | Т | ad-hoc подпись: локально на Apple Silicon запустится, «Developer cannot be verified» при скачивании — гарантировано |
| `CODE_SIGN_STYLE` | `Manual` | `Manual` | Т | ручная подпись при `CODE_SIGN_IDENTITY = "-"` → ни автоматической команды, ни профиля |
| `DEVELOPMENT_TEAM` | *(пусто)* | *(пусто)* | Т | пустая строка, а не отсутствие ключа → перекрывает любой `xcconfig`/CLI-дефолт команды |
| `CODE_SIGN_ENTITLEMENTS` | отсутствует | отсутствует | — | файла `.entitlements` в дереве нет (0 совпадений) → вне песочницы; для MAS-ветки это блокер, для прямой дистрибуции — осознанный выбор |
| `COMBINE_HIDPI_IMAGES` | `YES` | `YES` | Т | правильно для `.app` с ретиной; вместе с `NSHighResolutionCapable = true` в plist даёт корректный `Assets.csv`/Cocoa-путь |
| `ASSETCATALOG_COMPILER_APPICON_NAME` | **отсутствует** | отсутствует | — | и `Info.plist` не содержит `CFBundleIconFile`/`CFBundleIconName` (0 совпадений), и `.xcassets`/`.icns` в дереве нет → приложение с системной иконкой-заглушкой в Dock/Finder и на「О программе» |
| `PRODUCT_BUNDLE_IDENTIFIER` | `com.exolon.remake` | … | Т | один раз, на таргете; `CFBundleIdentifier` в plist = `$(PRODUCT_BUNDLE_IDENTIFIER)` → подстановка живая, расхождения нет |
| `PRODUCT_NAME` | `$(TARGET_NAME)` | … | Т | → `Exolon`, согласуется с `productReference = Exolon.app` |
| `LD_RUNPATH_SEARCH_PATHS` | `$(inherited) @executable_path/../Frameworks` | … | Т | норма для `.app` |
| `ALWAYS_SEARCH_USER_PATHS` | `NO` | `NO` | П | норма |
| `CLANG_ENABLE_MODULES` / `CLANG_ENABLE_OBJC_ARC` | `YES` / `YES` | … | П | норма |
| `GCC_*` (`GCC_WARN_*`, `GCC_TREAT_WARNINGS_AS_ERRORS`, `GCC_NO_COMMON_BLOCKS`) | **ни одного ключа** | — | — | нулевой уровень явных предупреждений; дефолты тулчейна. Шаблонный `GCC_NO_COMMON_BLOCKS = YES` не выставлен |
| `CLANG_WARN_*` (`…_DOCUMENTATION`, `…_IMPLICIT_OPTIONAL_CONVERSIONS`, `…_SHADOW_IVARS`) | **ни одного ключа** | — | — | предупреждений нет ни в проекте, ни в таргете; `-Werror` нет → тихая деградация качества сборки |
| `SWIFT_STRICT_CONCURRENCY` | **отсутствует** | отсутствует | — | дефолт `minimal`: компилятор не проверяет data race. Для игрового цикла с `Timer`/`DispatchQueue` (вне рамок этой lane) — нулевой автоматический контроль |
| `SWIFT_ACTIVE_COMPILATION_CONDITIONS` | отсутствует | отсутствует | — | значит `DEBUG` не объявлен в Debug. Сейчас безопасно: `grep -rn "#if \|DEBUG"` по Swift → 0 попаданий; но любой будущий `#if DEBUG` молча не сработает |
| `ONLY_ACTIVE_ARCH` | отсутствует | отсутствует | — | шаблон Xcode выставляет `YES` в Debug; без него Debug-сборка не ограничена активной архитектурой |
| `SWIFT_OPTIMIZATION_LEVEL`, `DEBUG_INFORMATION_FORMAT`, `VALIDATE_PRODUCT`, `DEAD_CODE_STRIPPING` | отсутствуют | отсутствуют | — | только дефолты; в Release нет `dwarf-with-dSYM` → символизовать краш релизного артефакта нечем, `VALIDATE_PRODUCT = YES` нет → plist/ресурсы в Release не валидируются |
| `ENABLE_TESTABILITY` | отсутствует | отсутствует | — | следствие: даже при добавлении тест-таргета `@testable import` был бы недоступен |

Итого набор: **6 ключей на уровне проекта и 13 на уровне таргета** против ~50+35 в стандартном
шаблоне Xcode 15/16; конфигурации Debug и Release **побайтово идентичны**
(проверено скриптом: `Debug==Release identical? True | True`), то есть «релизной» сборки
как отдельного режима настроек в проекте не существует.

### Target-уровень против проекта (пункт 5)

| проверка | факт |
|---|---|
| `PBXProject.targets` | 1: `5000…0001 /* Exolon */` |
| объектов `PBXNativeTarget` / `PBXAggregateTarget` / `PBXLegacyTarget` в файле | 1 / 0 / 0 |
| расхождение `targets` против определённых таргетов | пустое: «targets NOT in project.targets: none» |
| `productType` | `com.apple.product-type.application` |
| `dependencies` / `buildRules` | `()` / `()` |
| тест-таргет (`com.apple.product-type.bundle.unit-test`) | **отсутствует**; `attributes.TargetAttributes` содержит только `CreatedOnToolsVersion = 10.2`, без `TestTargetID` |
| файлов XCTest | 0 (`find`/`grep -rl XCTest --include=*.swift` → пусто) |
| `knownRegions` / `developmentRegion` | `(en, Base)` / `en`; `.lproj` и `PBXVariantGroup` в дереве нет — локализация не собрана, `CFBundleDevelopmentRegion = $(DEVELOPMENT_LANGUAGE)` опирается на неявную настройку, которой нет в списке ключей |
| `compatibilityVersion` / `objectVersion` / `LastUpgradeCheck` | `Xcode 9.3` / `51` / `1020` — формат Xcode 10.2 (2019); современная Xcode при первом открытии предложит «Update to Common Standard Settings», что перепишет файл целиком |
| `BuildIndependentTargetsInParallel` | `1` при единственном таргете — настройка без эффекта |

Несоответствий «таргет ↔ проект» по членству нет: один таргет, одна фаза каждого типа,
обе `XCConfigurationList` прикреплены. Структурная аномалия одна — **отсутствие тест-таргета
при наличии `PBXSourcesBuildPhase` только у продукта**: проверить сборку автотестом нельзя
в принципе, `xcodebuild test` нечем запускать.

### Scheme-слой (пункт 4)

Проверено полным обходом дерева: `find . -name "*.xcscheme" -o -name "xcshareddata" -o
-name "*.xcworkspacedata" -o -name "xcuserdata"` → **0 совпадений**. В
`Exolon.xcodeproj/` ровно один файл — `project.pbxproj` (`ls -la` подтверждает);
ни `project.xcworkspace/contents.xcworkspacedata`, ни
`xcshareddata/xcschemes/Exolon.xcscheme`, ни `xcuserdata/` в VCS нет.
Файла `.gitignore` в репозитории нет (0 совпадений), поэтому всё, что создаст
локально Xcode, упадёт в `git status` мусором.

Утверждение аудита (`engineering/reports/exolon-full-audit-20260920.md:79`:
«shared `.xcscheme` отсутствует — сборка только явным `-target Exolon»`) **подтверждено**
и является полной мерой того, что можно проверить без macOS: scheme-файлов в дереве нет.
Что из этого следует для свежего клона и CI-less-потока:

1. `xcodebuild -project Exolon.xcodeproj -list` на машине, где Xcode этот проект не открывали, не покажет ни одной scheme: `xcshareddata` нет, а scheme, создаваемая Xcode при открытии, кладётся в `xcuserdata/` (не в VCS). Команда `-scheme Exolon` на свежем клоне не имеет объекта — это и есть то, что обязан подтвердить прогон на macOS.
2. `-target Exolon` (как в `engineering/reports/exolon-initial-audit.md:101,362`) — единственный синтаксис, который можно гарантированно воспроизвести по материалам репозитория. Он даёт `build`, но **не даёт scheme-экшены**: `archive`, `test`, `clean build folder`, action-уровневые pre/post-шаги, `-destination`-маппинг и diagnose/analyze-режим живут в `.xcscheme`. Артефакт для релиза (`.xcarchive` → notarization) без shared scheme получить нечем.
3. Нет и механизма переопределения подписи: `CODE_SIGN_IDENTITY = "-"`, `CODE_SIGN_STYLE = Manual`, `DEVELOPMENT_TEAM = ""` зашиты в сам `pbxproj`, а не в scheme-override и не в `.xcconfig` (файлов `.xcconfig` в дереве 0). Чтобы собрать подписанный билд, придётся правитьtracked-файл проекта — то есть менять дерево после аппрува, что прямо конфликтует с правилом контракта «grant не позволяет менять протестированное дерево».
4. Первый же `xcodebuild`/открытие Xcode создаст `DerivedData`, `xcuserdata/`, `project.xcworkspace/` и (в новых Xcode) `xcshareddata/xcschemes/Exolon.xcscheme`. Без `.gitignore` это неотслеживаемый мусор, который легко коммитится и превращает следующий review-diff в шум.

## Что сломается при сборке/релизе

Стадия **компиляции и копирования ресурсов — не ломается**: целостность графа чистая
(0 dangling, 0 дублей, 0 отсутствующих путей), 18/18 Swift в `Sources`, 276/276 ресурсов в
`Resources`, ни одно lookup-имя кода не осталось без файла в бандле.
Ломается всё, что происходит **после** успешной сборки.

1. **`P1` — релизный артефакт врёт о себе.** Собранный `Exolon.app` будет показывать
   `0.3`, тогда как проект объявляет `0.5`: `GENERATE_INFOPLIST_FILE = NO` + литерал
   `0.3` в `Info.plist:18` при `MARKETING_VERSION = 0.5` (`pbx:1424,1443`).
   Механика однозначна: `$(MARKETING_VERSION)` в plist не используется ни в одном ключе,
   поэтому настройка сборки не используется. Следствие: «About»/Finder/`mdls`/счётчик
   скачиваний и любой сравнительный гейт релиза видят `0.3`; tag/release `0.5` не будет
   соответствовать бинарю.
2. **`P1` — build number не эволюционирует.** `CFBundleVersion` — литерал `1`
   (`Info.plist:20`), `$(CURRENT_PROJECT_VERSION)` не задействован. Два собранных артефакта
   одной версии неразличимы, что ломает и кэш Gatekeeper, и откат/повторную выдачу.
3. **`P1` — архив и notarization недостижимы.** Нет shared scheme → нет источника
   archive-экшена; плюс ad-hoc подпись (`CODE_SIGN_IDENTITY = "-"`, `CODE_SIGN_STYLE = Manual`,
   пустой `DEVELOPMENT_TEAM`) и отсутствующий `ENABLE_HARDENED_RUNTIME` (дефолт `NO`).
   Даже если кто-то соберёт `.app` по `-target`, подписать его «в поле» нельзя, а
   скачанный пользователем ad-hoc билд блокируется Gatekeeper.
4. **`P2` — продукт без иконки.** Нет `ASSETCATALOG_COMPILER_APPICON_NAME`, нет
   `CFBundleIconFile`/`CFBundleIconName`, в дереве нет ни `.xcassets`, ни `.icns`.
   В Dock/Finder/«About» приложение выглядит системной заглушкой; для MAS-ветки
   (`CFBundlePackageType = APPL` уже задан, а `LSApplicationCategoryType` — нет)
   это ещё и блокер при загрузке.
5. **`P2` — нулевой уровень предупреждений.** Ни одного `GCC_WARN_*`/`CLANG_WARN_*`,
   нет `SWIFT_STRICT_CONCURRENCY` (дефолт `minimal`), нет `-Werror`, нет `VALIDATE_PRODUCT`
   в Release. Конкретный риск: `Release` не валидирует plist, а строгая проверка concurency
   для SKScene-цикла не включена никогда — дефект такого класса прилетит только пользователю.
6. **`P2` — Release-артефакт не симболизируется.** `DEBUG_INFORMATION_FORMAT` не задан,
   в Release нет `dwarf-with-dSYM`; в связке с ad-hoc подписью это означает: упавший
   релизный билд невозможно разобрать постфактум.
7. **`P2` — тестов нет и добавить нельзя без переделки проекта.** `PBXNativeTarget` один,
   тест-таргета нет, `ENABLE_TESTABILITY` не выставлен, `@testable import` был бы недоступен.
   Любая «регрессия сборки» сейчас обнаруживается только ручной кнопкой Play на macOS.
8. **`P3` — хрупкость формата.** `objectVersion = 51` / `Xcode 9.3` / `LastUpgradeCheck 1020`
   при 4 несовместимых схемах генерации UUID и отсутствии генератора. Первое же открытие в
   современной Xcode предложит апгрейд формата и перепишет 1474 строки — диффом, в котором
   тонут реальные правки.
9. **`P3` — мёртвый вес и «нет входа для ресурса».** 5 файлов (`bubble.gif`, `rocks.gif`,
   `turret_bullet.gif`, `light.png`, `ship_fire.png`) лежат в git и никогда не попадают в
   бандл. Рядом — ложная «работающая» конструкция: `L01S04.tmx:9,12` объявляет
   `../images/tiles.gif` и `../images/rocks.gif` (пути из исходного Tiled-проекта), которых
   нет ни на диске, ни в бандле; сборка не падает **только потому**, что рендерер отбрасывает
   каталог и расширение (`TMXTileMapRenderer.swift:23-24,84-85`) и попадает в стемы
   `tiles`/`rocks`, совпадающие с `.png`, попавшими в бандл. Это не «норма», а совпадение имён:
   переименуй `rocks.png` — и единственный из 125 карт слой погаснет.
10. **`P3` — меню приложения не собирается.** `Info.plist` корректно не содержит
    `NSMainNibFile` (`main.swift` поднимает `NSApplication` программно, `AppDelegate`
    создаёт `NSWindow` с `styleMask [.titled, .closable, .miniaturizable, .resizable]`),
    но и `NSMenu`/`NSApp.mainMenu` в коде нет (`grep -rni "menu"` по Swift — только игровые
    состояния `.menuUp/.menuDown`). Итог — строка меню отсутствует: нет Cmd+Q, Cmd+H,
    нет стандартных Edit-команд. Формально это packaging-слой (plist без ниб-ключа при
    отсутствии эквивалента в коде), воспроизвести/подтвердить можно только на macOS.

## Что проверить на macOS

Ни один пункт ниже не подтверждён этим прогоном — на этом хосте нет ни `xcodebuild`,
ни `swiftc`. Порядок — от «просто собрать» к «просто выпустить».

```bash
# 1. Есть ли scheme вообще и чем реально можно собирать
xcodebuild -project Exolon.xcodeproj -list
xcodebuild -project Exolon.xcodeproj -target Exolon -configuration Debug build 2>&1 | tail -40
#    ожидаем: scheme-список пуст; -target собирается; -scheme Exolon падает

# 2. Фактическая версия в собранном бандле (главный контрольный вопрос)
/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' \
  build/Debug/Exolon.app/Contents/Info.plist
/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' build/Debug/Exolon.app/Contents/Info.plist
mdls -name kMDItemVersion build/Debug/Exolon.app
xcodebuild -showBuildSettings -project Exolon.xcodeproj -target Exolon \
  | grep -E 'MARKETING_VERSION|CURRENT_PROJECT_VERSION|INFOPLIST_FILE|GENERATE_INFOPLIST|ENABLE_HARDENED|DEVELOPMENT_LANGUAGE'

# 3. Состав бандла: ни одного лишнего Info.plist, все 276 ресурса на месте, gif не попали
ls build/Debug/Exolon.app/Contents/Resources | wc -l          # ожидаем 276 (+ каталоги)
ls build/Debug/Exolon.app/Contents/Resources | grep -c '\.gif$'   # ожидаем 0
ls build/Debug/Exolon.app/Contents/Info.plist            # один, на уровне Contents
codesign -dv --verbose=4 build/Debug/Exolon.app 2>&1 | head
codesign --verify --deep --strict --verbose=4 build/Debug/Exolon.app

# 4. Проверяется ли Gatekeeper при скачивании (quarantine), и есть ли иконка
xattr -dr com.apple.quarantine /tmp/Exolon.zip && open build/Debug/Exolon.app

# 5. Минимальная система: что реально записано в Load Command, против plist
vtool -show-build build/Debug/Exolon.app/Contents/MacOS/Exolon | grep -i version
plutil -p build/Debug/Exolon.app/Contents/Info.plist | grep -i LSMinimumSystemVersion

# 6. Проверка предупреждений «как в шаблоне» (после явного включения, не до)
xcodebuild -project Exolon.xcodeproj -target Exolon -configuration Release \
  GCC_TREAT_WARNINGS_AS_ERRORS=YES SWIFT_STRICT_CONCURRENCY=complete build 2>&1 | grep -c warning:
# 7. Есть ли вообще что архивировать без scheme (подтвердить/опровергнуть п.3)
xcodebuild -project Exolon.xcodeproj -scheme Exolon -configuration Release archive \
  -archivePath /tmp/Exolon.xcarchive
```

Отдельно зафиксировать поведению на ретине: `COMBINE_HIDPI_IMAGES = YES` +
`NSHighResolutionCapable = true` при отсутствии `@2x`-альтернатив — все 151 `.png`
одиночные, значит пиксель-арт апскейлится (компенсируется `filteringMode = .nearest`
во всех местах загрузки, включая `ExplosionEffect.swift:34,41`).

Вердикт: fail

Обоснование вердикта: слой **сборочно цел** (ни одной сломанной ссылки, дубля или
потерянного исходника — 0 по всем шести проверкам графа), но **не годен как релизный**:
артефакт выходит с неверной версией (`0.3` вместо `0.5`, build number навсегда `1`),
ad-hoc подписан без hardened runtime, без иконок и без dSYM, не архивируется и не
тестируется из-за отсутствия shared scheme и тест-таргета, а сам `pbxproj` —
формат 2019 года с четырьмя конкурирующими схемами UUID и без генератора.
Пункты 1–3 из «Что сломается» — блокеры выпуска; 4–7 — обязательны к исправлению до
первого релизного тега; 8–10 — сопровождение.
