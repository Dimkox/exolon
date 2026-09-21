# Анализ `docs_researcher` — релизный слой P1-11 (маршрут `2e76988444b0`)

Дата: 2026-09-21 (UTC; владелец GMT+3). Read-only: продукт не изменён, commits/push не выполнялись,
секреты/ключи не читались. База маршрута: `403eb13`; HEAD дерева на момент анализа: `d4c7a58`
(ветка `codex/release-layer-p1-11-20260921`) — то есть **HEAD продукта ушёл дальше даты аудита v3**
(`52795d1`), что само по себе затрагивает §5 ниже.

Как читались документы Apple: страницы `developer.apple.com/documentation/*` рендерятся JS и через
обычный fetch отдают только заголовок (проверено: `Build settings reference` → 18 669 байт, тела нет).
Достоверное содержимое берётся из того же официального источника через JSON-эндпоинт
`https://developer.apple.com/tutorials/data/documentation/<path>.json` (домен Apple, тот же контент).
Все цитаты ниже — из этих JSON или из статических archive-страниц Apple
(`developer.apple.com/library/archive/...`). Каждый вывод помечен `DOCUMENTED (URL)` либо `UNVERIFIED`.

---

## 0. Что в дереве сейчас (проверено чтением, не со слов отчётов)

| Факт | Значение | Где |
| --- | --- | --- |
| `GENERATE_INFOPLIST_FILE` | `NO` (обе конфигурации) | `Exolon.xcodeproj/project.pbxproj:1420`, `:1439` |
| `INFOPLIST_FILE` | `Exolon/Resources/Info.plist` | `project.pbxproj:1421`, `:1440` |
| `MARKETING_VERSION` | `0.5` | `project.pbxproj:1424`, `:1443` (`grep -c` = **2**) |
| `CURRENT_PROJECT_VERSION` | `1` | `project.pbxproj:1418`, `:1437` |
| `CFBundleShortVersionString` | литерал `0.3` | `Exolon/Resources/Info.plist:17-18` |
| `CFBundleVersion` | литерал `1` | `Info.plist:19-20` |
| Плейсхолдеры сборки в plist **уже используются** | `$(DEVELOPMENT_LANGUAGE)`, `$(EXECUTABLE_NAME)`, `$(PRODUCT_BUNDLE_IDENTIFIER)`, `$(PRODUCT_NAME)` | `Info.plist:6,8,10,14` |
| `ENABLE_HARDENED_RUNTIME` | отсутствует в файле (grep по 1474 строкам) | — |
| Подпись | `CODE_SIGN_IDENTITY = "-"`, `CODE_SIGN_STYLE = Manual`, `DEVELOPMENT_TEAM = ""` | `project.pbxproj:1415-1417`, `:1434-1436` |
| Формат проекта | `objectVersion = 51`, `compatibilityVersion = "Xcode 9.3"`, `LastUpgradeCheck = 1020`, `CreatedOnToolsVersion = 10.2` | `project.pbxproj:5`, `:1051`, `:1054`, `:1059` |
| `.xcscheme` в репозитории | **0 файлов**; в `Exolon.xcodeproj/` ровно `project.pbxproj`, каталога `xcshareddata` нет | `find` + `ls` |
| Target/продукт | 1 native target `Exolon` (`isa = PBXNativeTarget`), `productReference` → `Exolon.app` | `project.pbxproj:1028-1040`, `:318` |
| `.entitlements` в репозитории | **0 файлов** | `find` |
| Поверхность динамического кода | `dlopen`/`Bundle(path:`/`MAP_JIT`/`mprotect`/`WKWebView` = **0** входов в 18 Swift-файлах; только `import SpriteKit` | grep по `Exolon/` |

---

## 1. Подстановка `$(MARKETING_VERSION)` / `$(CURRENT_PROJECT_VERSION)` в ручной `Info.plist`

### 1.1 Ответ: **да, это корректная идиоматика, и она прямо документирована Apple**

Ключевой текст (раньше я его не находил, потому что он не в `Build settings reference`, а в
BundleResources):

> «How Xcode uses this file depends on the value of the `GENERATE_INFOPLIST_FILE` build setting. If the
> value is `Yes`, then Xcode merges the content of the property list file with the values from the
> Info.plist Values build settings when it generates your bundle's information property list file. **If
> it's `No`, then Xcode doesn't use build settings to generate the information property list file.
> Instead, it processes the values in the property list file you supply to substitute any build settings
> variables with their values, and copies the processed file into your bundle.**»
> DOCUMENTED — https://developer.apple.com/documentation/bundleresources/managing-your-app-s-information-property-list (раздел «Manually supply an information property list file»)

Там же, раздел «Build the app's information property list»:

> «During the operation, Xcode uses build settings to perform variable substitution.»
> DOCUMENTED — тот же URL

Там же, раздел «Create a new project» — про саму идиому плейсхолдеров в plist:

> «Xcode populates the project's build settings with values that it uses to generate the information
> property list, **or with variable values that it replaces at build time using build settings**. For
> example, Xcode sets `CFBundleIdentifier` with a value of `$(PRODUCT_BUNDLE_IDENTIFIER)`.»
> DOCUMENTED — тот же URL

Переключатель механизма — отдельный, документированный build setting:

> «Expand build settings in the `Info.plist` file.» — `INFOPLIST_EXPAND_BUILD_SETTINGS`
> DOCUMENTED — https://developer.apple.com/documentation/xcode/build-settings-reference#Expand-Build-Settings-in-Info.plist-File

Сами настройки:

> `MARKETING_VERSION`: «This setting defines the user-visible version of the project. When
> `GENERATE_INFOPLIST_FILE` is enabled, sets the value of the `CFBundleShortVersionString` key in the
> `Info.plist` file to the value of this build setting.»
> `CURRENT_PROJECT_VERSION`: «…The value must be a integer or floating point number, such as `57` or
> `365.8`. When `GENERATE_INFOPLIST_FILE` is enabled, sets the value of the `CFBundleVersion` key…»
> DOCUMENTED — https://developer.apple.com/documentation/xcode/build-settings-reference#Marketing-Version , #Current-Project-Version

**Важный нюанс формулировки, который в текущем отчёте размыт:** Apple описывает прямую связь
`MARKETING_VERSION → CFBundleShortVersionString` только «when `GENERATE_INFOPLIST_FILE` is enabled».
При `GENERATE_INFOPLIST_FILE = NO` связь не автоматическая — её обеспечивает **подстановка
`$(...)` в значении ключа**, то есть запись `CFBundleShortVersionString = $(MARKETING_VERSION)`
обязательна именно в файле plist. Отсюда вывод: вывод P1-11 («значение сборки `0.5` мертво») верен по
сути, но причинная формулировка в отчёте неточна — не «`GENERATE_INFOPLIST_FILE = NO`, поэтому
`MARKETING_VERSION` не применяется», а «`GENERATE_INFOPLIST_FILE = NO` **и plist не ссылается на
`$(MARKETING_VERSION)`**, поэтому нечему подставляться». Второе — правда (и именно так написано в
`…-fullaudit/evidence/perfile/pbxproj-build.md:138`).

### 1.2 Почему механизм в этом проекте гарантированно активен

`Info.plist:6,8,10,14` уже содержат `$(DEVELOPMENT_LANGUAGE)`, `$(EXECUTABLE_NAME)`,
`$(PRODUCT_BUNDLE_IDENTIFIER)`, `$(PRODUCT_NAME)`. Если бы подстановка не происходила,
`CFBundleExecutable` бандла буквально содержал бы строку `$(EXECUTABLE_NAME)` и приложение бы не
запустилось. DOCUMENTED-механизм + репозиторная эмпирика. `$(MARKETING_VERSION)` — тот же самый
подстановщик, никаких отдельных привилегий у него нет. **UNVERIFIED (требует macOS):** конкретное
значение `INFOPLIST_EXPAND_BUILD_SETTINGS` в этом проекте по умолчанию — проверить
`xcodebuild -showBuildSettings -project Exolon.xcodeproj -target Exolon -configuration Release | grep -E 'INFOPLIST_EXPAND_BUILD_SETTINGS|MARKETING_VERSION|CURRENT_PROJECT_VERSION'`.

### 1.3 «С каких пор это валидно» и совместимость с `objectVersion 51`

- `CURRENT_PROJECT_VERSION` — старая, документированная настройка версионирования; Apple описывает её
  в связке с `VERSIONING_SYSTEM = Apple Generic` и `agvtool`:
  > «Your Xcode project data file, `project.pbxproj`, includes a `CURRENT_PROJECT_VERSION` (Current
  > Project Version) build setting… agvtool searches `project.pbxproj` for `CURRENT_PROJECT_VERSION`.»
  > «Set Versioning System to Apple Generic. By default, Xcode does not use any versioning system.»
  > DOCUMENTED (archive) — https://developer.apple.com/library/archive/qa/qa1827/_index.html
  В текущем reference: `VERSIONING_SYSTEM` — «None: Use no versioning system. Apple Generic: Use the
  current project version setting.» DOCUMENTED — build-settings-reference#Versioning-System.
  В `project.pbxproj` настройки `VERSIONING_SYSTEM` **нет** → DOCUMENTED-дефолт «None», т.е. `agvtool`
  этим проектом не пользуется; это не мешает `$(CURRENT_PROJECT_VERSION)` подставляться.
- «С каких пор существует `MARKETING_VERSION`» — **UNVERIFIED из официальных источников**: в
  release notes Xcode 10–16 упоминаний `MARKETING_VERSION` нет (проверено grep'ом по JSON
  `…/xcode-release-notes/xcode-{10..16}-release-notes.json` → 0 вхождений в каждом). Широкое
  утверждение «с Xcode 8» / «templates пишут `$(MARKETING_VERSION)` с Xcode 11» — из вторичных
  источников (SO/GitHub-треды), официальной даты в документах Apple я не нашёл. **Не записывать в
  продукт как факт с датой.**
- Совместимость с `objectVersion 51` / `compatibilityVersion "Xcode 9.3"` / `CreatedOnToolsVersion 10.2`:
  **REASONING (не документировано напрямую, но доказано самим деревом).** `MARKETING_VERSION = 0.5` и
  `CURRENT_PROJECT_VERSION = 1` уже физически лежат в этом `project.pbxproj` (`:1418/1424/1437/1443`)
  при `objectVersion = 51` — то есть пара «формат 51 + эти настройки» существует и открыта в дереве.
  `XCBuildConfiguration.buildSettings` — это словарь строк; версия формата файла управляет
  структурой графа объектов, а не набором имён настроек (значения разрешает build-система установленной
  Xcode). **Практическое следствие:** менять `objectVersion`/`compatibilityVersion` **не нужно**; более
  того, менять их незачем и это ломало бы «keep backward compatibility» (AGENTS.md:102).
- Формат значения — отдельный документированный риск: `CFBundleShortVersionString`
  > «The required format is three period-separated integers, such as 10.14.1. The string can only
  > contain numeric characters (0-9) and periods.» + «[Major].[Minor].[Patch]»
  DOCUMENTED — https://developer.apple.com/documentation/bundleresources/information-property-list/cfbundleshortversionstring
  `CFBundleVersion` явно допускает 1–3 целых («You can also abbreviate the build version by using only
  one or two integers… 10.5 specifies 10.5.0») и требует инкремента для macOS-релизов.
  DOCUMENTED — https://developer.apple.com/documentation/bundleresources/information-property-list/cfbundleversion
  ⇒ после подстановки бандл покажет `CFBundleShortVersionString = 0.5` (две компоненты) и
  `CFBundleVersion = 1`. Это **не** «2-компонентный формат запрещён» (в `Preparing your app for
  distribution` сказано: «The version number and build string are expected to be in the format
  [Major].[Minor].[Patch]», без запрета на 2 части) — но расхождение «0.3 → 0.5» станет видимым
  изменением идентичности бандла. DOCUMENTED —
  https://developer.apple.com/documentation/xcode/preparing-your-app-for-distribution#Set-the-version-number-and-build-string

### 1.4 Чего в этой части делать нельзя

- `$(inherited)` к `MARKETING_VERSION`/`CURRENT_PROJECT_VERSION` **не применяется**: это скалярные
  настройки, у них нет «списка, к которому дописывают». Подстановка `$(inherited)` документирована
  Apple для списочных настроек (пример в reference — `OTHER_SWIFT_FLAGS`); для версий достаточно
  удалить перекрывающее значение на уровне target. **UNVERIFIED в части «уровень проекта вместо
  уровня target»**: в этом проекте обе настройки объявлены на уровне **target** (`:1424/1443`), на
  уровне проекта (`:1390-1411`) их нет. Перенос на уровень проекта — возможное, но не документированное
  мной улучшение; не обязательное для закрытия P1-11.

---

## 2. Hardened runtime и ad-hoc подпись

### 2.1 Что документировано

| Вопрос | Ответ | Источник |
| --- | --- | --- |
| Что такое | «The Hardened Runtime, along with System Integrity Protection (SIP), protects the runtime integrity of your software by preventing certain classes of exploits, like code injection, dynamically linked library (DLL) hijacking, and process memory space tampering.» | DOCUMENTED — https://developer.apple.com/documentation/security/hardened-runtime |
| Как включать (UI) | «To enable the Hardened Runtime for your app, navigate in Xcode to your target's Signing & Capabilities information and click the + button… choose Hardened Runtime.» | там же |
| Влияние на приложение | «The Hardened Runtime **doesn't affect the operation of most apps**, but it does disallow certain less common capabilities, like just-in-time (JIT) compilation. If your app relies on a capability that the Hardened Runtime restricts, add an entitlement to disable an individual protection.» | там же |
| Нужен ли файл entitlements | Только под исключения: «You add an entitlement by enabling one of the runtime exceptions or access permissions listed in Xcode. **Make sure to use only the entitlements that are absolutely necessary**». Плюс: «The default value of these Boolean entitlements is false. When Xcode signs your code, it includes an entitlement only if the value is true. … Don't include an entitlement if the value is false.» ⇒ файл entitlements **не является требованием** самого hardened runtime. Прямого предложения «файл не обязателен» в документах нет — это вывод из перечисленного. | там же; DOCUMENTED (формулировка), вывод — REASONING |
| Минимальная ОС / как включить без Capabilities | «Hardened runtime is available in the **Capabilities pane of Xcode 10 or later**, but you can enable the feature manually using earlier versions of Xcode, **as long as you're on macOS 10.13.6 or later**. To do this, add the following option to the `OTHER_CODE_SIGN_FLAGS` build setting: `--options=runtime`» … «If you enable hardened runtime manually using an earlier version of macOS, make sure that you also test your app running on **macOS 10.14 or later**.» | DOCUMENTED — https://developer.apple.com/documentation/security/resolving-common-notarization-issues#Enable-the-hardened-runtime |
| Требование notarization | «To upload a macOS app to be notarized, you must enable the Hardened Runtime capability.» + «If you don't enable the hardened runtime, notarization fails and reports an issue with the following message: `The executable does not have the hardened runtime enabled.`» | DOCUMENTED — hardened-runtime (aside Important); resolving-common-notarization-issues#Enable-the-hardened-runtime |
| Требование Gatekeeper | **Не документировано.** Страница «Gatekeeper and runtime protection» (Apple Platform Security) не упоминает hardened runtime ни разу (проверено grep'ом по тексту страницы: совпадений по «hardened» — 0). Её формулировка требования иная: «When a user downloads and opens an app, a plug-in, or an installer package from outside the App Store, Gatekeeper verifies that the software is from an identified developer, is notarized by Apple…, and hasn't been altered.» | DOCUMENTED-отрицание — https://support.apple.com/guide/security/gatekeeper-and-runtime-protection-sec5599b66df/web |
| Требование Mac App Store | «If you distribute your macOS app through the App Store, you must [enable App Sandbox]. If you notarize your macOS app to distribute it outside of the App Store, you must [enable the hardened runtime] and, optionally, can also enable App Sandbox.» ⇒ для MAS документировано требование **Sandbox**, а связь hardened runtime — с **notarization**. | DOCUMENTED — https://developer.apple.com/documentation/xcode/preparing-your-app-for-distribution#Configure-App-Sandbox-and-hardened-runtime-macOS |
| Ad-hoc и notarization | «Apple's notary service requires you to adopt the following protections: … Use a "Developer ID" application… certificate for your code-signing signature. (**Don't use a Mac Distribution, ad hoc, Apple Developer, or local development certificate.**.)» + «You can only notarize apps that you sign with a Developer ID certificate. If you use any other certificate — like a Mac App Distribution certificate, or a self-signed certificate — notarization fails…» | DOCUMENTED — https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution#Prepare-your-software-for-notarization ; resolving-common-notarization-issues#Use-a-valid-Developer-ID-certificate |

**Прямой вывод по P1-11:** при `CODE_SIGN_IDENTITY = "-"` включённый hardened runtime **не делает
билд notarizable**. Это не «может быть», а документированный отказ по классу сертификата. Значит
«включить hardened runtime» и «подписать Developer ID» — два разных шага, и первый сам по себе
публикацию не открывает. Отчёт формулировку «ENABLE_HARDENED_RUNTIME отсутствует ⇒ нельзя
нотаризовать» должен держать в этих рамках.

### 2.2 Сломает ли локальный запуск SpriteKit/Metal-игры

- Документированной площадки отказа нет: перечень ограничений hardened runtime в
  `…/documentation/bundleresources/entitlements` — это JIT
  (`com.apple.security.cs.allow-jit`), unsigned executable memory, library validation
  (`com.apple.security.cs.disable-library-validation` — «whether the app loads arbitrary plug-ins or
  frameworks, without requiring code signing»), DYLD env vars, debugger, executable-page protection и
  access-группы (камера/микрофон/контакты/календарь/локация/фото/Apple Events). DOCUMENTED (перечень
  подтемов страницы hardened-runtime).
- Дерево: 0 вызовов `dlopen`/`Bundle(path:`/`MAP_JIT`/`mprotect`/`WKWebView`, нет ни одного
  `.entitlements`, сторонний код не грузится, приватные ресурсы из списка не запрашиваются (см. §0).
  SpriteKit — системный фреймворк, Metal-обёрток `MTL*` в коде нет. ⇒ **ни одно документированное
  исключение не требуется; файл entitlements добавлять не нужно.** Это REASONING на базе DOCUMENTED-
  перечня, а не цитата.
- **FOLKLORE, которое нельзя записывать как проверенное:** «hardened runtime + ad-hoc подпись →
  приложение не запустится / macOS его не пустит». Официального текста ни в одну сторону я не нашёл:
  Apple не документирует поведение `--options=runtime` под идентификатором `-` (man-страница
  `codesign` на developer.apple.com не публикуется). Отмечать как **«UNVERIFIED — требует macOS-прогона»**.
- **FOLKLORE №2:** «локально собранный .app Gatekeeper не проверяет». Документированная формулировка
  Apple ограничена сценарием загрузки: Gatekeeper проверяет «when a user downloads and opens an app …
  from outside the App Store» и «requests user approval before opening **downloaded** software for the
  first time» (URL выше + https://support.apple.com/en-us/102445). Про «нет quarantine-атрибута ⇒ нет
  проверки» Apple прямо не пишет. Для macOS-контура это надо держать как наблюдение, а не как факт.
- Ужесточение macOS 15 (Sequoia), DOCUMENTED дословно:
  > «In macOS Sequoia, users will no longer be able to Control-click to override Gatekeeper when
  > opening software that isn't signed correctly or notarized. They'll need to visit System Settings >
  > Privacy & Security to review security information for software before allowing it to run.»
  > DOCUMENTED (2024-08-06) — https://developer.apple.com/news/?id=saqachfa

### 2.3 Два документированных подводных камня, которых нет в текущем отчёте

1. `CODE_SIGN_INJECT_BASE_ENTITLEMENTS`.
   > «When you create a new macOS project, Xcode automatically sets the target's
   > `CODE_SIGN_INJECT_BASE_ENTITLEMENTS` build setting to `YES`. This setting tells Xcode to add the
   > `com.apple.security.get-task-allow` entitlement to your app at build time. … If you use a custom
   > workflow and fail to remove the `com.apple.security.get-task-allow` entitlement, notarization
   > fails with the following message: `The executable requests the
   > com.apple.security.get-task-allow entitlement.` … archive (as of Xcode 10.2) or export your app
   > directly from Xcode, or set the `CODE_SIGN_INJECT_BASE_ENTITLEMENTS` build setting to `NO` before
   > building your app for distribution. But only change the build setting when you're done debugging
   > … because doing so makes it impossible to debug the binary on a system that uses SIP.»
   DOCUMENTED — https://developer.apple.com/documentation/security/resolving-common-notarization-issues#Avoid-the-get-task-allow-entitlement
   В `project.pbxproj` этой настройки **нет** (grep по 1474 строкам), и в дереве есть явные `$(inherited)`
   только у `LD_RUNPATH_SEARCH_PATHS` (`:1422`, `:1441`). Значит поведение целиком зависит от дефолта
   установленной Xcode, а дефолты Apple в reference **не публикует** ⇒ **UNVERIFIED, обязателен замер
   `xcodebuild -showBuildSettings`**. Это же — единственная документированная причина, по которой
   «Debug-сборка ≠ релиз» в этом проекте глубже, чем записано в `macos-probe.sh:151`.
2. Secure timestamp:
   > «By default, Xcode doesn't include a secure timestamp as part of the app's code signature during
   > the build process. Instead, it adds a secure timestamp only during the archive (as of Xcode 10.2)
   > and export workflows.»
   DOCUMENTED — там же, #Include-a-secure-timestamp
   ⇒ **архив через новую shared-схему — не косметика:** именно archive/export-путь добавляет timestamp.
   Это документированный аргумент за появление `ArchiveAction`.

Дефолт `ENABLE_HARDENED_RUNTIME` в reference **не указан** (строка документа: «Enable hardened runtime
restrictions.» — всё). Утверждение `pbxproj-build.md:143` «дефолт `NO`» therefore **UNVERIFIED как
цитата Apple** (эмпирически верно, но источника нет) — при корректуре помечать источником «замер
`-showBuildSettings`», а не ссылку на доки.

---

## 3. Shared `.xcscheme`: путь, минимальная структура, толерантность Xcode

### 3.1 Путь

- Apple **не публикует** путь к shared-схеме macOS/iOS проекта нигде из проверенных страниц. Единственное
  буквальное упоминание каталога в текущих документах Apple — Xcode 11 release notes про Swift-пакеты:
  > «The scheme that's autogenerated for a Swift package isn't automatically updated when the package
  > adds or removes targets. Workaround: Delete the scheme from the `swiftpm/xcode/xcshareddata/xcschemes`
  > directory inside the package directory, then reopen the package to automatically generate a new scheme.»
  DOCUMENTED — https://developer.apple.com/documentation/xcode-release-notes/xcode-11-release-notes
  (там же документирован факт автосоздания схем Xcode: «…to automatically generate a new scheme».)
- Про проект Apple говорит только поведением: «you can specify whether a scheme should be stored **in a
  project**—in which case it's available in every workspace that includes that project, or **in the
  workspace**—in which case it's available only in that workspace.» DOCUMENTED (archive) —
  https://developer.apple.com/library/archive/featuredarticles/XcodeConcepts/Concept-Schemes.html
- Конкретный путь для проекта — **UNVERIFIED из документов Apple**, подтверждён практикой: в трёх
  проверенных мной Xcode-сгенерированных репозиториях файл лежит ровно по
  `<project>.xcodeproj/xcshareddata/xcschemes/<Scheme>.xcscheme`
  (`iina.xcodeproj/…/iina.xcscheme`, `Maccy.xcodeproj/…/Maccy.xcscheme`,
  `Gifski.xcodeproj/…/Gifski.xcscheme`, все HTTP 200). Для этого репозитория:
  **`Exolon.xcodeproj/xcshareddata/xcschemes/Exolon.xcscheme`**.
  Вторичное (не-Apple) описание раскладки: https://pewpewthespells.com/blog/managing_xcode.html —
  shared: `<.xcodeproj| .xcworkspace>/xcshareddata/xcschemes/`; user:
  `<...>/xcuserdata/$USER.xcuserdatad/xcschemes/` (обычно gitignore, внешние инструменты его не видят).

### 3.2 Схема не задокументирована как формат — это надо зафиксировать в отчёте

Ни DTD, ни XSD, ни описания полей `.xcscheme` на developer.apple.com нет (проверено: в
build-settings-reference, в схемах-доках, в archive-разделе Xcode). Значит любые утверждения о
минимальном валидном наборе атрибутов можно получать только из **реального вывода Xcode** или из
**прогона на macOS**. Отмечать в продукте как «Xcode-generated output sample», а не «по документации Apple».

### 3.3 Канонический скелет, собранный из фактического вывода Xcode (macOS App)

Инвентарь элементов по трём живым файлам (grep `<[A-Za-z]+`):

- во всех трёх: `Scheme, BuildAction, BuildActionEntries, BuildActionEntry, BuildableReference,
  BuildableProductRunnable, TestAction, LaunchAction, ProfileAction, AnalyzeAction, ArchiveAction`
- только в отдельных (⇒ факультативны): `MacroExpansion` (есть у Gifski в `TestAction`, нет у IINA/Maccy),
  `Testables`/`TestableReference`/`TestPlans`/`TestPlanReference`, `EnvironmentVariables`/`EnvironmentVariable`
- только в отдельных версиях Xcode как атрибут: `buildArchitectures = "Automatic"` (Maccy, Xcode 15.4 —
  нет у IINA 14.3 и Gifski 26.4), `codeCoverageEnabled`, `enableASanStackUseAfterReturn`,
  `migratedStopOnEveryIssue`, `shouldAutocreateTestPlan`.

Атрибут `BuildableReference` во всех образцах — ровно пять, и **`BuildableNodeType` там нет ни в одном**
(`grep -c BuildableNodeType` = 0 по трём файлам): это не то, что пишет Xcode; `BuildableIdentifier`
всегда `"primary"`. Тип продукта в `.xcscheme` не дублируется — он берётся из
`BlueprintIdentifier` → `PBXNativeTarget.productType` (`project.pbxproj:1041`,
`com.apple.product-type.application`).

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Scheme
   LastUpgradeVersion = "1020"
   version = "1.3">
   <BuildAction
      parallelizeBuildables = "YES"
      buildImplicitDependencies = "YES">
      <BuildActionEntries>
         <BuildActionEntry
            buildForTesting = "YES"
            buildForRunning = "YES"
            buildForProfiling = "YES"
            buildForArchiving = "YES"
            buildForAnalyzing = "YES">
            <BuildableReference
               BuildableIdentifier = "primary"
               BlueprintIdentifier = "500000000000000000000001"
               BuildableName = "Exolon.app"
               BlueprintName = "Exolon"
               ReferencedContainer = "container:Exolon.xcodeproj">
            </BuildableReference>
         </BuildActionEntry>
      </BuildActionEntries>
   </BuildAction>
   <TestAction
      buildConfiguration = "Debug"
      selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB"
      selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB"
      shouldUseLaunchSchemeArgsEnv = "YES">
   </TestAction>
   <LaunchAction
      buildConfiguration = "Debug"
      selectedDebuggerIdentifier = "Xcode.DebuggerFoundation.Debugger.LLDB"
      selectedLauncherIdentifier = "Xcode.DebuggerFoundation.Launcher.LLDB"
      launchStyle = "0"
      useCustomWorkingDirectory = "NO"
      ignoresPersistentStateOnLaunch = "NO"
      debugDocumentVersioning = "YES"
      debugServiceExtension = "internal"
      allowLocationSimulation = "YES">
      <BuildableProductRunnable
         runnableDebuggingMode = "0">
         <BuildableReference
            BuildableIdentifier = "primary"
            BlueprintIdentifier = "500000000000000000000001"
            BuildableName = "Exolon.app"
            BlueprintName = "Exolon"
            ReferencedContainer = "container:Exolon.xcodeproj">
         </BuildableReference>
      </BuildableProductRunnable>
   </LaunchAction>
   <ProfileAction
      buildConfiguration = "Release"
      shouldUseLaunchSchemeArgsEnv = "YES"
      savedToolIdentifier = ""
      useCustomWorkingDirectory = "NO"
      debugDocumentVersioning = "YES">
      <BuildableProductRunnable
         runnableDebuggingMode = "0">
         <BuildableReference
            BuildableIdentifier = "primary"
            BlueprintIdentifier = "500000000000000000000001"
            BuildableName = "Exolon.app"
            BlueprintName = "Exolon"
            ReferencedContainer = "container:Exolon.xcodeproj">
         </BuildableReference>
      </BuildableProductRunnable>
   </ProfileAction>
   <AnalyzeAction
      buildConfiguration = "Debug">
   </AnalyzeAction>
   <ArchiveAction
      buildConfiguration = "Release"
      revealArchiveInOrganizer = "YES">
   </ArchiveAction>
</Scheme>
```

Значения идентификаторов **сняты с этого дерева**, не угаданы:
`BlueprintIdentifier` = UUID native target (`project.pbxproj:1028`); `BlueprintName` = `Exolon`
(`:1038`); `BuildableName` = `Exolon.app` (`path` у `productReference`, `:318` и `:1040`);
`ReferencedContainer` = `container:Exolon.xcodeproj` (папка проекта в корне репозитория).

### 3.4 `version="1.3"` и чтение старой схемы новым Xcode

- Эмпирика по живым файлам: `version` — версия **формата схемы**, а не версии Xcode. Xcode 14.3 и 15.4
  пишут `1.7`, Xcode 26.4 — `1.8`, а файлы эпохи Xcode 10.2 — `1.3`. При этом схема со
  `LastUpgradeVersion = "1640"` (Xcode 16.4) и `version = "1.3"` — реальный, живой пример
  (`Kingfisher.xcscheme`, HTTP 200): современный Xcode читает и сохраняет `1.3`, не обязан её поднимать.
  DOCUMENTED-статус: **нет** (это наблюдение над выводом Xcode).
- `LastUpgradeVersion` в схеме и `LastUpgradeCheck` в `project.pbxproj` — разные атрибуты; для этого
  дерева согласованное значение `1020` (pbxproj:1051) ⇒ `LastUpgradeVersion = "1020"` выглядит
  естественно и не провоцирует «проект тронут новым Xcode».
- **UNVERIFIED (требует macOS):** что из атрибутов Xcode 14/15/16 проглотит отсутствующим в
  **написанной от руки** схеме. По образцам видно лишь то, что Xcode сам пишет их непоследовательно
  (`MacroExpansion`/`Testables`/`EnvironmentVariables` факультативны), т.е. отсутствие этих блоков
  форматно допустимо; по `BuildActionEntry`/`BuildableReference`/`LaunchAction`/`ArchiveAction` ни один
  образец ничего не выкидывает — их считать обязательными.

### 3.5 Что реально произойдёт при открытии в свежей Xcode

«Xcode provides default schemes for most targets» + «disable automatic creation of schemes for new
targets» (Manage Schemes) — то есть Xcode сам создаёт схемы и сам же может переписать файл, подняв
`LastUpgradeVersion`. DOCUMENTED —
https://developer.apple.com/documentation/xcode/customizing-the-build-schemes-for-a-project
Следствие для репозитория: норм, что после первого открытия Xcode перепишет `.xcscheme` — его надо
коммитить таким, каким его написал Xcode (см. §4).

---

## 4. Коммитить ли `.xcscheme` и как добиться `xcodebuild -list`

- «**By default, Xcode shares schemes with other team members.**» DOCUMENTED —
  https://developer.apple.com/documentation/xcode/customizing-the-build-schemes-for-a-project
- Прямое требование «использовать общие схемы и включить Archive-экшен» — в CI-требованиях Apple:
  > «Use shared schemes. … Enable the archive action for the scheme that builds your app or framework.»
  DOCUMENTED — https://developer.apple.com/documentation/xcode/setting-up-your-project-to-use-xcode-cloud#Configure-your-project-and-workspace
  Формулировка «Use shared schemes» + требование удалённого Git-репозитория на той же странице
  («You need a remote repository using Git to use Xcode Cloud») означает: схема должна быть в дереве.
  Дословного «commit the .xcscheme» в этих документах нет → **DOCUMENTED по смыслу, букву помечать как вывод.**
- Пользовательские схемы (`xcuserdata/<user>.xcuserdatad/xcschemes/`) — локальные, их коммитить нельзя;
  в текущем `.gitignore` (корень репозитория, 25 строк) правила под `xcuserdata` **нет** — стоит
  добавить (`Exolon.xcodeproj/xcuserdata/`), иначе первый же запуск Xcode на хосте владельца добавит
  untracked-мусор; это же затрагивает fingerprint-правило из v3 §7.
- Про `xcodebuild -list` — важное предупреждение, меняющее ожидания пробника:
  - то, что `xcodebuild -list` покажет схему **только если есть `.xcscheme`**, нигде не документировано;
  - то, что Xcode автосоздаёт схемы, документировано (§3.5 и Xcode 11 RN §3.1);
  - предыдущий лаг это уже заметил: `…-fullaudit/evidence/analysis-docs_researcher-fullaudit.md:339`
    — «`xcodebuild -list` может показать только авто-схему» (тоже без ссылки на Apple — статус UNVERIFIED).
  ⇒ **Найденный дефект пробника:** `engineering/runbooks/macos-probe.sh:69-70` выносит
  `verdict_shared_scheme=ABSENT` из текста `xcodebuild -list`. Это неверный индикатор именно shared-схемы
  (он проверяет наличие слова `Schemes`+`Exolon`, а авто-схема даст то же самое). Индикатор shared-схемы —
  **файл на диске**: `[ -f "$TARGET/xcshareddata/xcschemes/Exolon.xcscheme" ]`. Проверять же `-list`
  нужно другое: что схема **именуется** и доступна `-scheme Exolon` (иначе `ArchiveAction` бесполезен).
  Это не «ожидание стало ложным после правки», это «ожидание было непроверяемым механизмом» — чинить в
  том же коммите.
  - Второе: `macos-probe.sh:97` определяет hardened runtime как
    `codesign -d --entitlements :-` — этот флаг выводит **entitlements**, а hardened runtime — это
    **флаг подписи** (`--options=runtime`), который смотрят в `codesign -dvvv` (строка `flags=…(runtime)`)
    либо через отказ нотариуса `The executable does not have the hardened runtime enabled.` (документирован,
    §2.1). При включённом hardened runtime и **нуле** entitlements текущая строка пробника даст
    «файл не подписан/пусто» и не зафиксирует включение. **UNVERIFIED:** точный текст `flags=0x10000(runtime)`
    — из man-страницы `codesign`, которую Apple не публикует; подтвердить на macOS.
- Рекомендуемая раскладка, чтобы `-list` показал схему (и чтобы её видел любой CI вне Xcode):
  ```
  Exolon.xcodeproj/
    project.pbxproj                              (уже есть)
    xcshareddata/xcschemes/Exolon.xcscheme       (общая — коммитить)
    project.xcworkspace/…                        (не создавать руками; Xcode добавит сам)
    xcuserdata/                                  (не коммитить, добавить в .gitignore)
  ```
  Имя файла схемы = имя в `-scheme`: `Exolon`.

---

## 5. Что в текущих документах станет ложным после правки

Три источника по скоупу вопроса: `engineering/reports/exolon-full-audit-20260920-v3.md` (§1 P1-11, §6, §9)
и `README.md`. Правило дерева («append, never overwrite dated evidence», `decisions.md:7`) ⇒ ниже каждая
строка дана как `path:line` + предлагаемая **корректура-допиской**, без правки самого текста.

| # | `path:line` | Цитата (что станет ложным/неточным) | Становится | Как корректурить (append) |
| --- | --- | --- | --- | --- |
| 1 | `engineering/reports/exolon-full-audit-20260920-v3.md:36` | «`Info.plist` литерал `CFBundleShortVersionString=0.3` при `MARKETING_VERSION=0.5` и `GENERATE_INFOPLIST_FILE=NO`; `CFBundleVersion=1` литерал; `.xcscheme` — **0** …; `ENABLE_HARDENED_RUNTIME` отсутствует» | ложны 3 из 4 клаузы (литералы версии, 0 схем, отсутствие hardened runtime); `GENERATE_INFOPLIST_FILE=NO` и ad-hoc подпись останутся истинными | тело строки таблицы **не трогать**; в новой корректурной секции (см. строку №8 — §9.12/§11) завести построчный разбор «клауза → состояние до/после + sha закрытия» |
| 2 | `…v3.md:36` (колонка «Где») | «лаг pbxproj, перепроверено частично: `grep -c MARKETING_VERSION`, `find *.xcscheme`=0» | команда `find *.xcscheme`=0 перестанет воспроизводиться ⇒ доказательство станет невоспроизводимым на HEAD | в корректуре: не переписывать, а дописать «замер снят на `52795d1`; на `<sha>` `find` = 1»; воспроизводить новым самопроверяющимся verifier'ом (см. `decisions.md:15` про `v3_measurements.py`) |
| 3 | `…v3.md:22` | «Все строки таблицы ниже получены командой или чтением кода **в этом прогоне мной лично**, если не указано иное.» | любая правка таблицы задним числом разрушает это обязательство | корректура обязана быть **отдельной** строкой/секцией с собственным provenance (кто, чем, на каком sha), как уже сделано в §4 |
| 4 | `…v3.md:130` | «**P1 (чинить до релиза):** … P1-11 релизный слой (версии/схема/подпись)» | после частичного закрытия (версии+схема+hardened; подпись остаётся ad-hoc) строка врёт дважды: и что «не чинилось», и что чинится всё сразу | дописать в §6 пометку вида «P1-11: закрыто частично 2026-09-21 (`<sha>`, см. §11); остаток = подпись (ad-hoc ⇒ notarization невозможна, DOCUMENTED §2.1)» |
| 5 | `…v3.md:137` | «**P3:** … отсутствие иконки/shared scheme …» | половина («shared scheme») становится ложной; «иконки» — остаётся | та же дописка: «shared scheme закрыт 2026-09-21; иконки нет» — **не** стирать строку |
| 6 | `…v3.md:126` | «## 6. Бэклог v3 (**единственный актуальный**)» | как только дерево ушло вперёд (`d4c7a58` ≠ `52795d1`), заголовок «единственный актуальный» уже неверен независимо от этой правки | дописать одну строку под заголовком: «Актуален на `52795d1`; состояние релизного слоя после `<sha>` — §11» |
| 7 | `…v3.md:11` | «\| **этот файл (`exolon-full-audit-20260920-v3.md`)** \| **авторитет** \|» | «авторитет» читается как «описание текущего дерева»; после правки это опасно | не менять; добавить в таблицу **новой строкой** ссылку на закрывающий артефакт с его sha (по образцу строк 12-13) |
| 8 | `…v3.md:185-193` (§9) | «`engineering/runbooks/macos-probe.sh` — исполняемый зонд: секции A–D автоматические (`xcodebuild -list`, сборка `-target Exolon`, `plutil` по версиям бандла, … `codesign`/`spctl`…)»; «`evidence/perfile/macos-validation-handout.md` — 22 исполняемые строки … с ожиданиями из закоммиченных замеров» | описание секции A перестаёт соответствовать скрипту после правки ожиданий; §9 вдобавок наследует ложные ожидания хендаута | дописать в §9 новый пункт «§9.12 Корректура релизного слоя» с диффом ожиданий; хендаут (п. 9-10) не правится |
| 9 | `engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/perfile/macos-validation-handout.md:29-31` | «`-target Exolon` обязателен, а не стилистичен: в репозитории **ноль** `.xcscheme`-файлов … то есть общей схемы нет и `-scheme Exolon` указывать не на что» | после добавления схемы «не на что» становится ложным (про «ноль файлов» — было правдой на дату, правдой и остаётся как историческое наблюдение) | датированное эвиденс: **баннер корректуры сверху файла + новая строка** «с `<sha>` схема есть, `-scheme Exolon` работает»; тело не переписывать |
| 10 | `…handout.md:137` (M-01) | «`CFBundleShortVersionString` = **0.3** (литерал `Info.plist:17-18`; `GENERATE_INFOPLIST_FILE = NO`, plist не ссылается на `$(MARKETING_VERSION)`…)» и контроль «собралось 0.5 ⇒ вывод V1 неверен» | ожидание и «контроль-перевёртыш» меняются местами: после правки 0.5 — **ожидаемое** | той же допиской по образцу v3-§4 («было → стало»): M-01 → «ожидание: `$(MARKETING_VERSION)` подставлен, бандл 0.5; контроль: бандл 0.3 ⇒ подстановка не сработала» |
| 11 | `…perfile/pbxproj-build.md:143` | «`ENABLE_HARDENED_RUNTIME` … \| **отсутствует** … \| дефолт `NO` → hardened runtime не включён; для notarization и обхода Gatekeeper при распространении вне MAS нужен `YES`» | «нужен для обхода Gatekeeper» — неверно (документировано: требование notarization; Gatekeeper hardened runtime не упоминает, §2.1); «дефолт NO» — не цитата Apple; сама клауза «отсутствует» станет ложной | баннер в этот файл: «утверждение про Gatekeeper отозвано 2026-09-21 (источник: Apple Platform Security…); статус настройки на HEAD — см. §11» |
| 12 | `…perfile/pbxproj-build.md:144` | «`CODE_SIGN_IDENTITY` \| `-` \| … ad-hoc подпись: локально на Apple Silicon запустится, „Developer cannot be verified" при скачивании — гарантировано» | «гарантировано» = folklore (см. §2.2 UNVERIFIED); правкой не затрагивается, но в корректурном проходе обязана получить статус | дописать «не проверено; требует macOS-наблюдения» — не стирать |
| 13 | `engineering/runbooks/macos-probe.sh:69-70` | `verdict_shared_scheme=PRESENT (unexpected: аудит finding no .xcscheme in tree)` / `=ABSENT (matches audit: 0 .xcscheme)` | код, а не документ; по §3.5 он измеряет не shared-схему. После правки «PRESENT» станет ожидаемым, но сам индикатор останется неверным | править ожидания **и механизм** (файл + `-scheme`), в §9 дописать, что изменено |
| 14 | `…macos-probe.sh:86` | `## C. Bundle version truth (EXPECTED: CFBundleShortVersionString=0.3 при MARKETING_VERSION=0.5 — P1 из pbxproj-лагa)` | буквально ложное ожидание после правки | инвертировать ожидание + добавить переворотный контроль (§6 решения: rc≠0 при 0.3) |
| 15 | `…macos-probe.sh:91` | `plist_marker_version_present=$(grep -c 'MARKETING_VERSION = 0.5' …)` | после правки это уже не «маркер рассогласования», а «маркер наличия» — семантика имени переворачивается | переименовать в `pbx_marker_marketing_version_count`, ожидание `2` |
| 16 | `…macos-probe.sh:97` | `hardened_runtime=$(codesign -d --entitlements :- …)` | не измеряет hardened runtime (§3.5) | заменить на `codesign -dvvv`-проверку флага + контроль «пустой файл без runtime-флага ⇒ rc≠0» |
| 17 | `…macos-probe.sh:151` | «сборка Debug не эквивалентна релизу: подпись ad-hoc/Manual, `ENABLE_HARDENED_RUNTIME` отсутствует.» | «отсутствует» станет ложной | переформулировать остаток: ad-hoc ⇒ notarization невозможна (DOCUMENTED), плюс `CODE_SIGN_INJECT_BASE_ENTITLEMENTS`/timestamp (§2.3) |
| 18 | `README.md:1`, `README.md:3`, `README.md:17` | «# Exolon — Step 9 Rebase (**test archive**)», «This is the first runnable **archive** from the new level-rebase branch.», «this archive is a runnable checkpoint of the rebase work» | ни одна строка не становится ложной от этой правки, **но** после появления `ArchiveAction` слово *archive* в README начинает означать две разные вещи (git-чекпоинт vs Xcode Product ▸ Archive). Отдельно: `…-fullaudit/evidence/analysis-docs_researcher-fullaudit.md:612` упрекает README именно за «first runnable archive» при 0 схем | README правится **в этом же изменении** (требование AGENTS.md:26), но не «переписывается»: добавить блок «Release layer (2026-09-21)» с версией сборки, схемой и статусом подписи, и снять терминологическое столкновение (написать «checkpoint» вместо «archive» в трёх строках — это правка текущей строки, что для README разрешено: README — живой документ, не датированное эвиденс) |

Механика корректуры, принятая в этом репозитории (её и держать):
1. датированные эвиденс-файлы (`…/evidence/perfile/*`, отчёты v1/v2/v3) — **только баннер/дописка** + таблица
   «было → стало» по образцу `…v3.md:98-116` (§4);
2. новое состояние дерева — в **новом** датированном артефакте (в этом маршруте: `evidence/…` пакета
   `20260921-close-audit-finding-p1-11-release-layer-for-the-2e7698` и, если нужно,
   `engineering/reports/release-layer-closure-20260921.md`), с sha, командой замера и переворотными контролями;
3. живой документ (README) — правится напрямую (AGENTS.md:26), с удалением терминологической двойности.

---

## 6. Правила самого репозитория, ограничивающие это изменение (дословно)

`AGENTS.md`:

- `AGENTS.md:26` — **«Before proposing a release, update `README.md` so it matches this tree: current
  VERSION, what exists, where it lives, and how the pieces connect.»** ⇒ README обязан получить
  описание релизного слоя в этом же изменении; молчание README = нарушение.
- `AGENTS.md:27` — «Keep README links to the reviewed architecture model (`architecture/system.yaml`),
  rules (`architecture/rules.yaml`) and generated views (`architecture/generated/`) current…» —
  **выполнимо частично: каталога `architecture/` в дереве нет** (`ls -d architecture` → No such file or
  directory), как и `START_HERE.md`/`PROJECT_STATE.json`, на которые ссылается `AGENTS.md:11`.
  Это унаследованный boilerplate фабрики; в корректуре следует зафиксировать несоответствие контракта
  дереву (и не выдумывать `architecture/*`). Равно `AGENTS.md:7` требует `mistakes.md`, которого в
  дереве нет.
- `AGENTS.md:20` — **«Never use GitHub Actions for this repository. Trust CI is operated from `trust-ci/`…»**
  и `AGENTS.md:176` — «Adding `.github/workflows/` or any GitHub Actions dependency.» ⇒ соблазн «схема
  есть — сделаем CI-архив в Actions» запрещён явно.
- `AGENTS.md:42` — «All product changes are delivered through an isolated branch and pull request.
  Direct push to `main` or another protected/shared branch is prohibited.» ; `AGENTS.md:170` — «Direct
  push to a protected/shared branch.» (в «Prohibited routine actions»).
- `AGENTS.md:43` — «Local `python3 scripts/grok_verify.py --mode pr` and route-selected reviews are
  preflight evidence. They never replace the App-owned policy-epoch check on the exact PR SHA.» ;
  `AGENTS.md:44` — «Merge only after the external Trust CI check succeeds… A new commit … requires a
  fresh check and fresh external approvals.»
- `AGENTS.md:143-157` — «Run: `python3 scripts/grok_verify.py --mode pr`» … «Use the exact local evidence
  kind requested by the route. **A local receipt is stale after any repository change.**» ⇒ любая
  корректура после правки дерева требует перевыпуска квитанций (`verification`, `security_review`,
  `release_review` — набор маршрута).
- `AGENTS.md:83-84` — «Exactly one write agent owns application-code changes in a route.» / «Review
  agents are read-only and must inspect the actual diff and surrounding implementation.» ;
  `AGENTS.md:66` — «Do not bypass the route…» (в маршруте `write_agent: null` ⇒ владельцу записи надо
  назначить явно до правок).
- `AGENTS.md:99` — «Prefer the smallest coherent vertical change.» ; `AGENTS.md:102` — «Keep backward
  compatibility unless a breaking change is explicitly approved and versioned.» ⇒ видимый скачок
  идентичности бандла `0.3 → 0.5` — это «изменение, требующее явного утверждения и версионирования»;
  его нужно назвать в `change-spec.yaml` (сейчас там `acceptance_criteria: []`,
  `forbidden_outcomes: []`, `invariants: []` — пустые).
- `AGENTS.md:103` — «Every production-facing change needs rollback or forward-recovery logic and
  observable success/failure signals.» ; в спеке: `"rollback": {"maximum_steps": 1, "strategy": "forward_fix"}`
  ⇒ откат = снять правку с plist/pbxproj; наблюдаемый сигнал = версионные ключи бандла + флаг подписи.
- `AGENTS.md:11` — «Milestone designs and implementation plans must live in the repository or the active
  pull request before a session ends. Chat is the lowest-priority source of truth.» ⇒ весь вывод этого
  файла обязан остаться в репозитории (что он и делает), а не в переписке.
- `AGENTS.md:173` — «Reading `.env`, private keys, credential stores, production dumps, CI signing keys,
  GitHub App keys or approval keys.» (запрещено; я не читал) и `AGENTS.md:170-176` — «Merge, publish,
  tag, deploy … without an exact delegated local grant naming that operation and resource.»

`decisions.md`:

- `decisions.md:7` — «## 2026-09-20: Full audit retracts cabin P0 and **appends, never overwrites, prior
  evidence**» и `decisions.md:9` — «Full-audit evidence was written under `-fullaudit` filenames so the
  dated first-pass evidence stays intact, and **correction banners were added to the live report/backlog
  instead of rewriting them**. … Swift parsing on Linux … was adopted as the strongest static gate at
  that pass; **typecheck/build remain macOS-only**.» ⇒ (а) механика корректуры из §5; (б) проверки
  сборки/подписи **нельзя** заявить как пройденные на этом хосте — только как «macOS-контур».
- `decisions.md:15` — «Consequence for every future measurement in this repo: TMX `<object>` elements are
  parsed with `xml.etree`, never with a regex… A regex pass in this session reported 97 markers instead
  of 127 …; the committed self-checking tool `evidence/v3_measurements.py` (**rc=0 iff the report
  matches, 11 flipping controls**) exists to make that class of error visible instead of plausible.»
  ⇒ новый «release-layer verifier» обязан наследовать ту же форму: **rc=0 ⇔ совпадает**, и обязательный
  переворотный контроль (например: временно вернуть литерал `0.3` в копию plist → verifier обязан стать
  rc≠0; удалить `xcshareddata/xcschemes` → обязан стать rc≠0). Без контроля доверия нет.
- `decisions.md:3-5` — прецедент «официальные тесты зависят от двух модулей, не отключать проверки»
  (контекст фабрики, не продукта) — на это изменение не влияет, кроме общего тона «не глушим проверки».

Прочие ограничения скоупа из пакета: `engineering/changes/…/change-spec.yaml` (`schema_version: 2`,
`risk.tier: "red"`) — критериев приёмки и запрещённых исходов там **нет**, то есть «docs-слой» не имеет
typed-критерия для «версия бандла = 0.5» и «схема на диске». Это блокер для закрытия: по AGENTS.md
(«typed authority») их нужно добавить до реализации, иначе гейт рапортует по устаревшей спеке
(прецедент описан в v3 §8: «гейт рапортует `criterion_mapped 8/8` по устаревшей спеке»).
Идентификаторы критериев в этом репозитории — `AC-\d{3}` (иначе валидатор спеки их не принимает).

---

## 7. Итог: DOCUMENTED-ответы и что осталось непроверенным

**DOCUMENTED (официальные источники Apple, прочитаны мной):**
1. При `GENERATE_INFOPLIST_FILE = NO` Xcode **подставляет** значения build settings прямо в plist
   («it processes the values in the property list file you supply to substitute any build settings
   variables with their values, and copies the processed file into your bundle») ⇒ `$(MARKETING_VERSION)` /
   `$(CURRENT_PROJECT_VERSION)` — правильная идиома; механизм — `INFOPLIST_EXPAND_BUILD_SETTINGS`.
2. Жёсткой даты появления `MARKETING_VERSION` в документах Apple нет; `CURRENT_PROJECT_VERSION` +
   `VERSIONING_SYSTEM` документированы давно (QA1827, agvtool), и обе настройки уже лежат в этом
   `project.pbxproj` при `objectVersion 51` ⇒ менять формат проекта не нужно.
3. Hardened runtime: требование **notarization** («you must enable the Hardened Runtime capability»,
   «The executable does not have the hardened runtime enabled.»), не Gatekeeper (страница Gatekeeper его
   не упоминает) и не MAS (там документировано требование Sandbox). Доступен в Xcode ≥10 / включается
   вручную на macOS ≥10.13.6 через `OTHER_CODE_SIGN_FLAGS = --options=runtime`; тестировать на ≥10.14
   (деплой-таргет проекта — 10.14 ✓). «Не влияет на большинство приложений», ограничения — JIT/DYLD/
   library validation/debugger/приватные ресурсы ⇒ файл entitlements не обязателен, и этому приложению
   (0 dlopen/JIT/плагинов, 0 `.entitlements`) он не нужен.
4. Ad-hoc (`-`) **не нотаризуется** — документированный отказ по классу сертификата («Don't use a Mac
   Distribution, ad hoc, Apple Developer, or local development certificate.»), плюс `CODE_SIGN_INJECT_BASE_ENTITLEMENTS=YES`
   ⇒ `com.apple.security.get-task-allow` ⇒ отказ нотариуса, и «Xcode добавляет secure timestamp только на
   archive/export» ⇒ ArchiveAction не косметика.
5. Схемы: «By default, Xcode shares schemes with other team members»; CI-требование Apple — «Use shared
   schemes» + «Enable the archive action for the scheme that builds your app or framework»; формат
   `.xcscheme` Apple **не документирует** (каноном служит реальный вывод Xcode: 5 атрибутов
   `BuildableReference`, `BuildableIdentifier = "primary"`, **без** `BuildableNodeType`; `version` 1.3→1.7→1.8
   живёт независимо от версии Xcode).

**UNVERIFIED (нет официального источника — требует macOS-прогона или остаётся folklore):**
- Значение `INFOPLIST_EXPAND_BUILD_SETTINGS` и дефолт `ENABLE_HARDENED_RUNTIME` в этом проекте (Apple
  дефолты не публикует) → `xcodebuild -showBuildSettings`.
- Запустится ли локально ad-hoc-подписанное приложение с `--options=runtime` и без entitlements — «сломает/
  не сломает» документированного ответа нет (folklore, которое нельзя переносить в отчёт как факт).
- Покажет ли `xcodebuild -list` схему при отсутствии `.xcscheme` (авто-схема) — механизм не документирован;
  значит текущий `macos-probe.sh:69-70` проверяет shared-схему неверно в обе стороны.
- Точный текст флага в `codesign -dvvv` (`flags=…(runtime)`) — из неопубликованной Apple man-страницы.
- Дословный путь `Exolon.xcodeproj/xcshareddata/xcschemes/` — в документах Apple для проекта не встречается
  (только `swiftpm/xcode/xcshareddata/xcschemes` в Xcode 11 RN); подтверждён реальными Xcode-проектами.
- Набор атрибутов `.xcscheme`, которые Xcode 14/15/16 простит отсутствующими в написанном от руки файле.

---

## 8. Источники (проверены открытием/загрузкой 2026-09-21)

- https://developer.apple.com/documentation/bundleresources/managing-your-app-s-information-property-list
- https://developer.apple.com/documentation/xcode/build-settings-reference (#Marketing-Version,
  #Current-Project-Version, #Generate-Infoplist-File, #Infoplist-File,
  #Expand-Build-Settings-in-Infoplist-File, #Enable-Hardened-Runtime, #Code-Signing-Identity,
  #Code-Sign-Style, #Code-Signing-Inject-Base-Entitlements, #Versioning-System)
- https://developer.apple.com/documentation/security/hardened-runtime
- https://developer.apple.com/documentation/security/resolving-common-notarization-issues
- https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution
- https://developer.apple.com/documentation/xcode/preparing-your-app-for-distribution
- https://developer.apple.com/documentation/xcode/customizing-the-build-schemes-for-a-project
- https://developer.apple.com/documentation/xcode/setting-up-your-project-to-use-xcode-cloud
- https://developer.apple.com/documentation/bundleresources/information-property-list/cfbundleshortversionstring
- https://developer.apple.com/documentation/bundleresources/information-property-list/cfbundleversion
- https://developer.apple.com/documentation/bundleresources/entitlements
- https://developer.apple.com/news/?id=saqachfa (2024-08-06)
- https://support.apple.com/guide/security/gatekeeper-and-runtime-protection-sec5599b66df/web
- https://support.apple.com/en-us/102445 (HT202491 «Safely open apps on your Mac»)
- https://developer.apple.com/library/archive/qa/qa1827/_index.html
- https://developer.apple.com/library/archive/featuredarticles/XcodeConcepts/Concept-Schemes.html
- https://developer.apple.com/documentation/xcode-release-notes/xcode-11-release-notes
- Xcode-сгенерированные `.xcscheme` (кanon формата, не документы Apple):
  https://raw.githubusercontent.com/iina/iina/master/iina.xcodeproj/xcshareddata/xcschemes/iina.xcscheme ,
  https://raw.githubusercontent.com/p0deje/Maccy/master/Maccy.xcodeproj/xcshareddata/xcschemes/Maccy.xcscheme ,
  https://raw.githubusercontent.com/sindresorhus/Gifski/master/Gifski.xcodeproj/xcshareddata/xcschemes/Gifski.xcscheme ,
  https://raw.githubusercontent.com/onevcat/Kingfisher/master/Kingfisher.xcodeproj/xcshareddata/xcschemes/Kingfisher.xcscheme
- Вторичное (не Apple) описание раскладки shared vs user schemes: https://pewpewthespells.com/blog/managing_xcode.html
