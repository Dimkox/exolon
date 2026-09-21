# Release-layer surface map для закрытия P1-11 (repo_explorer, route `2e76988444b0`)

Снимок: ветка `codex/release-layer-p1-11-20260921`, HEAD `d4c7a58`, base маршрута
`403eb1322d645154307ce11bf91be89e2082e1dd` (= merge-base с `origin/main`, `git merge-base` подтверждён).
`tree_fingerprint` на момент съёма — `d0c623b7425821f742e88d35eec299d1ca472c2a6628eb0306a8e1dcdc32ed31`
(снят `adaptive_grok.util.tree_fingerprint`; изменится от появления этого же файла — ожидаемо).
Режим: только чтение; продуктовые файлы не тронуты; `grok_verify` не запускался (он пишет receipt и
тянет `factory-postgres-exit` ≈160–250 с docker-контейнером, см. §3).

Факты из постановки задачи проверены — все подтвердились, кроме одного: `Info.plist` не 24 строки,
а 28 (`wc -l`), что само по себе находка (§7.1).

---

## 1. Носители build/version identity (полный перечет)

### 1.1 Артефактные (попадают в бандл / определяют его)

| носитель | значение | evidence |
|---|---|---|
| `Exolon/Resources/Info.plist:17-18` | `CFBundleShortVersionString` = литерал `0.3` | `awk 'NR>=17&&NR<=20'` |
| `Exolon/Resources/Info.plist:19-20` | `CFBundleVersion` = литерал `1` | там же |
| `Exolon/Resources/Info.plist:21-22` | `LSMinimumSystemVersion` = литерал `10.14` (не `$(MACOSX_DEPLOYMENT_TARGET)`) | там же |
| `Exolon/Resources/Info.plist:5-6,7-8,9-10,13-14` | **подстановки уже живые**: `$(DEVELOPMENT_LANGUAGE)`, `$(EXECUTABLE_NAME)`, `$(PRODUCT_BUNDLE_IDENTIFIER)`, `$(PRODUCT_NAME)` | доказывает, что `$(MARKETING_VERSION)` в этом же plist механически легален |
| `Exolon.xcodeproj/project.pbxproj:1418` / `:1437` | `CURRENT_PROJECT_VERSION = 1` (Debug / Release) | grep |
| `Exolon.xcodeproj/project.pbxproj:1424` / `:1443` | `MARKETING_VERSION = 0.5` (Debug / Release); `grep -c 'MARKETING_VERSION = 0.5'` = **2** | проверено локально |
| `project.pbxproj:1420` / `:1439` | `GENERATE_INFOPLIST_FILE = NO` | grep |
| `project.pbxproj:1421` / `:1440` | `INFOPLIST_FILE = Exolon/Resources/Info.plist` | grep |
| `project.pbxproj:1415-1416` / `:1434-1435` | `CODE_SIGN_IDENTITY = "-"`, `CODE_SIGN_STYLE = Manual` | grep |
| `project.pbxproj:1419` / `:1438` | `DEVELOPMENT_TEAM = ""` (пустая строка, а не отсутствие ключа) | grep |
| `project.pbxproj:1394` / `:1406` (уровень проекта) и `:1423` / `:1442` (уровень таргета) | `MACOSX_DEPLOYMENT_TARGET = 10.14` — дублировано на обоих уровнях | grep |
| `ENABLE_HARDENED_RUNTIME` | **отсутствует во всех 4 `XCBuildConfiguration`** (блоки 1388–1449) | `grep -n HARDENED` → 0 совпадений |
| `project.pbxproj:5` | `objectVersion = 51` | grep |
| `project.pbxproj:1051` / `:1054` / `:1059` | `LastUpgradeCheck = 1020`, `CreatedOnToolsVersion = 10.2`, `compatibilityVersion = "Xcode 9.3"` | grep |
| `project.pbxproj:1049` | `BuildIndependentTargetsInParallel = 1` | grep |
| `project.pbxproj:1028-1041` | единственный `PBXNativeTarget` = `500000000000000000000001 /* Exolon */`, `buildConfigurationList = 900000000000000000000002`, `productReference = 200000000000000000000010`, `productType = com.apple.product-type.application` | read |
| `project.pbxproj:318` | product-ref `200000000000000000000010 /* Exolon.app */` (`sourceTree = BUILT_PRODUCTS_DIR`) | read |
| `project.pbxproj:1462` | `XCConfigurationList` таргета | read |

Целостность носителей на текущем дереве (для будущего re-bind):
`project.pbxproj` = **1474 строки / 133 718 байт / sha256 `d7393eb6a52014c30f61f9a2ee46782ecbbea8d397b130806afb969886bbe81a`**;
`Info.plist` = **28 строк / 932 байта / sha256 `3e26005fbfc4c7a16ec8e94b3c1c9c8fa4f5e7c7d1ea71c55c7f79132c05bd75`**.
Оба digest'а зафиксированы в закоммиченном отчёте предыдущего маршрута — см. §4.3.

### 1.2 Носители «номера шага» в продукте (третий-пятый слой версии)

| носитель | evidence |
|---|---|
| заголовок окна `"Exolon Remake — Step 9 Rebase"` | `Exolon/Platform/macOS/AppDelegate.swift:16` |
| титульный лейбл `"STEP 10"` | `Exolon/GameCore/GameScene.swift:832` |
| ключи `UserDefaults` `Exolon.Step10.*` (7 штук) | `Exolon/GameCore/GameState.swift:25-31` |
| комментарий «through Step 9» | `Exolon/GameCore/GameScene.swift:624` |
| заголовок и обещания README («Step 9 Rebase», «125-zone project») | `README.md:1`, `README.md:6` |

### 1.3 Чего нет (и это часть находки)

- **Нет `VERSION`-файла** — `git ls-files | grep -v /` даёт 18 корневых файлов без `VERSION`;
  при этом `VERSION` объявлен носителем идентичности в `.grok-stack/config/policy.json:13` (control-plane)
  и `:56` (protected), а fallback-копия списка — `.grok-stack/adaptive_grok/_policy_legacy.py:18-30`.
  `AGENTS.md:26` требует «update README.md so it matches this tree: current VERSION» — носителя нет.
- **Нет `CHANGELOG.md`, нет `Makefile`** (оба тоже в protected/control-plane списках).
- **Нет ни одного packaging-скрипта продукта.** Единственный исполнительный носитель сборки —
  `engineering/runbooks/macos-probe.sh` (см. §2). Полный перечёт носителей `xcodebuild|actool|productbuild|notarytool|hdiutil|altool|xcrun`
  по не-factory-файлам даёт только `engineering/runbooks/*` и markdown-отчёты; в `scripts/` — только
  `grok_*`-утилиты стека, ни одна не собирает `.app`.
- **Нет `.xcconfig`**, нет `*.entitlements`, нет `.xcassets`/`.icns` (подтверждено `git ls-files` по суффиксам;
  `ASSETCATALOG_COMPILER_APPICON_NAME` и `CODE_SIGN_ENTITLEMENTS` в pbxproj отсутствуют).
- **Нет `xcshareddata/`**: `Exolon.xcodeproj/` содержит ровно один файл (`ls -la` → `project.pbxproj`);
  `find . -name '*.xcscheme'` → 0; `git ls-files | grep -c xcscheme` → 0.

---

## 2. Как продукт собирается/валидируется сегодня и что перевернётся в зонде

### 2.1 Два хоста

- **Linux (этот хост):** `xcodebuild` отсутствует (`command -v xcodebuild` → ABSENT), `swiftc` есть
  (`/opt/swift/usr/bin/swiftc`). Продукт здесь не собирается: валидация — только статика и данные
  (`evidence/linux_static_audit.py`, `evidence/v3_measurements.py`, `evidence/fullaudit_measurements.py`)
  плюс исполняемый Linux-контур одного загрузчика (`evidence/harness/run.sh`, который сам себя
  запрещает на macOS: `run.sh:19-21` → `exit 75`).
- **macOS:** единственный артефакт — `engineering/runbooks/macos-probe.sh` (объём 161 строка,
  `exit 0` на `:161`),
  ожидающий машины, которой нет: `engineering/changes/20260919-.../tasks.md:26` — «ждут машину (ни локально,
  ни по ssh её нет)». Авторитет ожиданий — `engineering/reports/exolon-full-audit-20260920-v3.md:185-193`.

Зонд вызывает сборку формой `-target`, а не `-scheme`: `macos-probe.sh:79`
`xcodebuild -project "$TARGET" -target Exolon -configuration "$CONFIG" build`.
Каталог сборки по умолчанию для `-target` — `$(SRCROOT)/build`, и зонд ищет продукт именно там:
`macos-probe.sh:82` `APP="$(find "$(dirname "$TARGET")/build" -maxdepth 3 -name 'Exolon.app' -print -quit …)"`.

### 2.2 Полный перечёт assertions зонда и их реакция на три изменения

Ниже — **каждая** проверка, её EXPECTED-носитель и что с ней станет.
`(a)` = появился shared scheme; `(b)` = `Info.plist` переведён на `$(MARKETING_VERSION)`/`$(CURRENT_PROJECT_VERSION)`;
`(c)` = добавлен `ENABLE_HARDENED_RUNTIME = YES`.

| строка зонда | утверждение / EXPECTED | (a) scheme | (b) substitutions | (c) hardened runtime |
|---|---|---|---|---|
| `:64` | `## A. Scheme discovery (EXPECTED: no shared scheme — см. evidence/perfile/pbxproj-build.md)` | **становится ложью как заголовок** | нет | нет |
| `:66` | `LIST="$(xcodebuild -project "$TARGET" -list 2>&1 | tr '\n' '|')"` | вывод теперь содержит `Schemes:` + `Exolon` | нет | нет |
| `:69` | `*"Schemes"*"Exolon"*) emit "verdict_shared_scheme=PRESENT (unexpected: аудит finding no .xcscheme in tree)"` | **сработает ветка PRESENT и сама позовёт себя «unexpected»** — артефакт будет читаться как аномалия | нет | нет |
| `:70` | `*) emit "verdict_shared_scheme=ABSENT (matches audit: 0 .xcscheme)"` | **перестанет печататься** (это и есть «значение перевернулось») | нет | нет |
| `:79` | форма сборки `-target Exolon` | формально работает и со scheme, но перестаёт быть единственно возможной; потеряется покрытие archive-экшена | нет | нет |
| `:81` | `build_rc=$?` (без EXPECTED-аннотации) | не меняется | не меняется | **может смениться** при попытке ad-hoc + hardened без entitlements — фиксировать rc |
| `:86` | `## C. Bundle version truth (EXPECTED: CFBundleShortVersionString=0.3 при MARKETING_VERSION=0.5 — P1 из pbxproj-лагa)` | нет | **ложь как заголовок** — ожидаемое значение становится `0.5` | нет |
| `:88` | `plist_CFBundleShortVersionString=$(plutil -extract CFBundleShortVersionString raw "$PL" …)` — ожидаемое выводится только из заголовка `:86` | нет | **значение с `0.3` на `0.5`; при `--mode fast` без сборки — то же самое в секции C** | нет |
| `:89` | `plist_CFBundleVersion=$(plutil -extract CFBundleVersion raw "$PL" …)` (ожидалось `1`) | нет | **значение = `$(CURRENT_PROJECT_VERSION)` = `1`, то есть числом не отличается — контроль недифференцирующий, нужен отдельный зонд подстановки** | нет |
| `:90` | `plist_LSMinimumSystemVersion=…` | нет | нет | нет |
| `:91` | `plist_marker_version_present=$(grep -c 'MARKETING_VERSION = 0.5' "${TARGET}/project.pbxproj")` — факт. значение **2** | нет | **не меняется (2)** — подстановка в plist не трогает pbxproj; при этом строка *не замечит* bump версии: если `MARKETING_VERSION` станет `0.6`, счётчик даст 0 без всякого EXPECTED-разъяснения | нет |
| `:92` | `bundle_resources_tmx=… (EXPECTED 125)` | нет | нет | нет |
| `:93` | `bundle_has_gif=… (EXPECTED 0 — gif не в Resources phase)` | нет | нет | нет |
| `:94` | `bundle_has_generated_terrain=… (EXPECTED 1 …)` | нет | нет | нет |
| `:95` | `codesign=$(codesign -dv "${APP}" 2>&1 | tr '\n' '|' | head -c 300)` | нет | нет | **недостаточен**: `-dv` (verbose=1) печатает `flags=0x…(runtime)` не на всех версиях тулчейна, а `head -c 300` + склейка в одну строку делают сравнение позиционным; `EXPECTED` на строке нет вовсе. Для (c) нужен явный зонд вида `codesign -dvvv … | grep -c '(runtime)'` |
| `:96` | `spctl=$(spctl -a -vv "${APP}" 2>&1 | tr '\n' '|' | head -c 200)` | нет | нет | **без EXPECTED**; при ad-hoc подписи и без notarization `spctl` остаёт reject → артефакт не отличит (c) от её отсутствия |
| `:97` | `hardened_runtime=$(codesign -d --entitlements :- "${APP}" 2>&1 | head -c 200)` | нет | нет | **структурно слеп**: ключ называется hardened, но меряет *entitlements*. hardened-runtime без entitlements-файла blob не даёт → вывод не изменится. Это единственный «контроль» на (c) в зонде, и он его не видит |
| `:102` | `## D. Persisted defaults (EXPECTED: ключи Exolon.Step10.*, …)` | нет | нет | нет |
| `:114-141` | секция E: 15 ручных `ask`/`record` с EXPECTED-аргументом (`E1…E15`) | нет | нет | нет |
| `:149` | `- он не заменяет XCTest (в продукте 0 тестов)` | нет | нет | нет |
| `:151` | `- сборка Debug не эквивалентна релизу: подпись ad-hoc/Manual, ENABLE_HARDENED_RUNTIME отсутствует.` | нет | нет | **становится утверждением неверна — обязана быть переписана** |
| `:154-157` | секция G: `product_log_calls`/`level_warp_calls`/`checkpoint_reader_calls` | нет | нет | нет |

**Вывод по §2:** (a) ломает ровно одну пару строк (`:64`, `:69-70`) плюс заголовок-ссылку;
(b) ломает `:86` и *содержательный* смысл `:88-89`, причём `:89` после правки **не различает** правильное
и неправильное (оба дают `1`) — нужен контроль, читающий сам plist на наличие `$(MARKETING_VERSION)`;
(c) не ломает ни одну строку, потому что ни одна строка её не проверяет — то есть правка (c)
пройдёт зондом молча. Это и есть главный дефицит, который обязан закрыть новый верификатор.

Отдельный операционный риск (для обоих пунктов «как собирается»): запуск `macos-probe.sh` на macOS
создаёт в корне репозитория `build/`, `DerivedData`-производные и `project.xcworkspace/`, а `.gitignore`
(`.gitignore:1-25`) **не содержит** ни `build/`, ни `*.xcworkspace`, ни `xcuserdata/`, ни `DerivedData/`.
`adaptive_grok/util.py:129-142` (`_fingerprint_noise`) их тоже не исключает, а `changed_files()`
(`util.py:145-162`) считает и untracked-файлы (`git ls-files --others --exclude-standard`) — значит
после прогона на macOS fingerprint и все receipt'ы разъедутся на тысячи путей. Правка `.gitignore` —
protected/control-plane путь (см. §6), то есть требует гранта.

---

## 3. Что реально проверяет `python3 scripts/grok_verify.py --mode pr`

Точка входа `scripts/grok_verify.py:18-30` → `adaptive_grok.verification.verify()`
(`.grok-stack/adaptive_grok/verification.py:1070-1159`), `raise SystemExit(0 if report['status'] == 'pass' else 1)`
(`scripts/grok_verify.py:30`). Профили маршрута: `base` + `frontend`
(`.grok-stack/config/quality-profiles/base.json`, `.../frontend.json`).

Список проверок, которые фактически запускаются на этом дереве (выведен из кода, не из прогона):

1. `git-diff-check` — `verification.py:594-652`: `git diff --check` (worktree), `git diff --cached --check` (index)
   и, для `pr|release`, `git diff --check <base>..HEAD` по каждому выбранному диапазону
   (`:606-621`): route base `403eb13…` и локальная цель PR `refs/remotes/origin/main`
   (`_select_local_pr_target`, `:392-460`; `origin/HEAD` не задан → `refs/remotes/origin/main`, merge-base = `403eb13`).
   **Это единственная проверка, реагирующая на хвостовые пробелы и на «нет пустой строки в EOF»**
   (`\ No newline at end of file`). Уже кусалась: коммит `52795d1` называется
   «docs: normalize trailing whitespace in audit markdown for git-diff-check gate», и об этом прямо
   написано в `engineering/reports/exolon-full-audit-20260920-v3.md:167-168` и в шапке
   `evidence/harness/last-run.txt:2` («хвостовые пробелы в строках вывода сняты — иначе они роняют git-diff-check»).
2. `change-spec` — `:752-795`; активный spec берётся из `.grok-stack/runtime/active-change.json`
   (`engineering/changes/20260921-close-audit-finding-p1-11-release-layer-for-the-2e7698/change-spec.yaml`),
   `gate=True`. Схема — `schemas/change-spec.schema.json` (`spec.py:13` `SCHEMA_PATH`), паттерны id:
   `^AC-[0-9]{3,6}$`, `^OBJ-…`, `^INV-…`, `^FORBID-…`, `^SIG-…` (`schemas/change-spec.schema.json:9-12`);
   `evidence` — ровно один ключ из `{test, receipt, production_signal, attestation}`
   (`schemas/change-spec.schema.json:14-22`), `test` обязан совпасть с `^[A-Za-z0-9_./:-]+$`
   (без пробелов и `#`). **Существование файла-ссылки `test` не проверяется** (`spec.py` не содержит
   `exists`/`is_file`). Сейчас `acceptance_criteria` в спеке — пустой список (проверено разбором), а
   `delivery_expected=true` + активный spec есть → падения не будет, но и покрытия нет.
3. `architecture` → **skip** («architecture is not configured»): `verification.py:82`, каталогов
   `architecture/` и `governance/` в дереве нет.
4. `governance` → **skip** (то же, `:222`).
5. `workflow-artifacts` → **skip**: активный change есть и путь у него канонический, но нет
   `engineering/changes/<id>/workflow/manifest.json` (`:279` — «no active change», `:294` — «not configured»).
   Именно здесь живёт единственный в стеке markdown-лимит: `MAX_MARKDOWN_LINES = 20_000` /
   `MAX_MARKDOWN_LINE_LENGTH = 8_192` (`.grok-stack/adaptive_grok/workflow_artifacts.py:23-24`,
   `_bounded_markdown` `:303-308`), и он применяется **только к workflow-артефактам**, не к `evidence/*.md`.
   → «реакции на число строк в markdown» в `--mode pr` для нашего пакета нет.
6. `secret-scan` — `:654-670`: для **каждого изменённого файла** (включая новые untracked) читает до
   2 МБ и ищет `-----BEGIN … PRIVATE KEY-----`, `AKIA[0-9A-Z]{16}`,
   `(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*["'][^"']{12,}["']` (`:656-659`).
   `.xcscheme`/`.plist` попадают в этот обход как обычный текст; совпадений не дают.
7. `contract-structure` — `:699-723`: JSON/YAML **только если имя пути содержит `contract`/`schema`/`openapi`/`asyncapi`**.
   XML и plist не парсятся вообще.
8. `sql-safety` — `:725-741`: только `.sql`/`.php`.
9. `ruff` + `bandit` — `:840-860`, пути `QUALITY_PY_PATHS` (`:815-834`) =
   `.grok-stack/adaptive_grok`, `scripts`, `tests`, `.grok/hooks`, корневые `*_tool_use.py`/`session_*.py`/
   `stop_gate.py`/`subagent_*.py`/`user_prompt_submit.py`/`pre_compact.py`, `factory/src/adaptive_factory`.
   **`engineering` исключён явно**: `ruff.toml:9` и `bandit.yaml:3`.
   → новый `scripts/<name>.py` будет обложен ruff (`select = ["E4","E7","E9","F"]`, `line-length = 120`,
   `target-version = py310`) и bandit (skips `B101,B404,B603,B607`); скрипт-верификатор в
   `engineering/changes/.../evidence/` не проверяется ничем. `ruff check scripts` на текущем дереве — «All checks passed!».
10. `factory-unit` — `:994-1004` (`python3 -m unittest factory.tests.test_{contracts,state,migrations,service}`).
11. `factory-postgres-exit` — `:1005-1021`: при `mode in {pr,release}` гоняет `factory/tests/run_disposable_exit.py`
    (docker, ≈160–250 с по `evidence/test-review-fullaudit.md:26`); обходится через
    `GROK_VERIFY_CAPABILITY=repository-sandbox` → `skip` (`:1006-1014`).
12. `source-stability` — `:1119-1131`: сверяет `tree_fingerprint` до и после проверок.
13. PHP/composer/node/semgrep/trivy/pytest/coverage/python-unittest — **не срабатывают**:
    нет `package.json`, нет корневых `pyproject.toml`/`requirements.txt`/`setup.py` (он только в `factory/`),
    нет каталога `tests/`, нет `semgrep.yaml`/`.semgrep/`, нет `Dockerfile`/`docker-compose*.y*ml`
    (есть `factory/compose.yaml`, который не совпадает с `docker-compose*`-глобом, поэтому trivy не вызывается).

Итоговый вердикт и запись receipt'а: `status='pass' if not failures` (`:1147`), причём `skip`
не может завалить вердикт — это уже зафиксировано как дефект гейта в
`engineering/reports/exolon-full-audit-20260920-v3.md:179-181`. Receipt пишется только если
`governance != fail` и fingerprint не уехал (`:1150-1156`); после любой правки дерева он стухает.

**Прямо на вопрос «как ведёт себя новый XML/plist-файл»:** `verification.py` **не содержит ни одного
упоминания** `.swift`, `.tmx`, `.xcodeproj`, `.xcscheme`, `.plist` (проверено: `grep -c` → 0). Новый
scheme-файл для гейта — просто «изменённый файл»: попадает в `changed_files()`, в `secret-scan`,
в fingerprint и в `git diff --check`. Никакой structural-валидации XML не происходит; единственная
реальная угроза падения гейта — хвостовой пробел/отсутствие финального перевода строки в любом
новом или отредактированном файле, плюс разъезд fingerprint по §3.12.

---

## 4. Закоммиченные измерители и артефакты, которые утверждают ТЕКУЩИЕ пробелы

### 4.1 Соломятся (rc≠0 / «MISMATCH») сразу после закрытия gap

- `engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/v3_measurements.py:84`
  `EXPECTED["shared_xcschemes"] = 0`, измерение `:367`
  `got["shared_xcschemes"] = len(list(root.glob("**/*.xcscheme")))`, сверка `:372`,
  вердикт `:374` (`"ok": not mism and all(controls.values())`), `return 0 if out["ok"] else 1` (`:387`).
  ⇒ **любой новый `*.xcscheme` в дереве роняет v3-измеритель в rc=1** со строкой
  `shared_xcschemes = 1   ✗ ожидалось 0`. Сюда же: `:85 test_targets` (измерение `:368` regex'ом по pbxproj)
  и `:86 product_xctest_files` (`:369`). Это ожидаемое и правильное поведение — но его надо
  явным образом переутвердить в том же коммите, что и scheme, иначе соседний lane останется красным.
- `v3_measurements.py:356-358` читает pbxproj regex'ом `(\w{24}) /* generated_terrain\.png in Resources \*/` —
  не про версию, но зависит от pbxproj; смена формата/отступов pbxproj правкой Xcode его может сломать.

### 4.2 Молча устареют (не падают, но печатают неверное)

- `engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/linux_static_audit.py:436-438`
  вытаскивает `CFBundleShortVersionString` и `MARKETING_VERSION`; `:495-496` пишет их в markdown;
  `:478` и `:551` **перезаписывают закоммиченные** `linux-static-audit.json` и `.md`;
  `return 0` безусловно (`:554`) — падения нет.
  Закоммиченные значения, которые станут неверны: `evidence/linux-static-audit.md:12`
  «Info.plist CFBundleShortVersionString: 0.3» и `:13` «pbxproj MARKETING_VERSION: ['0.5']».
  При переходе на `$(MARKETING_VERSION)` regex `:436` вернёт литерал `$(MARKETING_VERSION)` — то есть
  артефакт не «починится», а станет бессмысленным: нужен отдельный measure «resolved vs literal».
  ⚠️ Дополнительный дефект, уже задокументирован: `exolon-full-audit-20260920-v3.md:169-172` — генератор
  `.md` **не воспроизводит побайтово** закоммиченный файл (`md bytes equal: False`, `json bytes equal: True`),
  а перезапуск роняет `git-diff-check`. Любая попытка «пересобрать артефакт» упрётся сюда.
- `evidence/fullaudit_measurements.py` — version/scheme-зондов нет (только cabin/beam/spawn,
  `:113-178`); не сломается, но и не поможет. Единственная его «запись артефакта» —
  `fullaudit-b01-spawn.json` (`:171`), вердикт — `:185-186`.
- `engineering/runbooks/macos-probe.sh` — см. §2.2 (строки `:64`, `:69-70`, `:86`, `:88-91`, `:95-97`, `:151`).

### 4.3 Markdown-утверждения, обязанные быть обновлёнными или переоформленными

| носитель | что утверждает | строка |
|---|---|---|
| `engineering/reports/exolon-full-audit-20260920-v3.md:36` | сама формулировка P1-11 (plist `0.3`, `CFBundleVersion=1` литерал, `.xcscheme` — **0**, ad-hoc/Manual, нет `ENABLE_HARDENED_RUNTIME`) | `:36` |
| `engineering/reports/exolon-full-audit-20260920-v3.md:130` | P1-11 в списке «релизный слой (версии/схема/подпись)» | `:130` |
| `engineering/reports/exolon-full-audit-20260920-v3.md:137` | «отсутствие иконки/shared scheme» | `:137` |
| `engineering/reports/exolon-full-audit-20260920.md:91` | «shared `.xcscheme` отсутствует — сборка только явным `-target Exolon`» | `:91` |
| `engineering/reports/exolon-full-audit-20260920.md:55` | «V1 0.5 vs 0.3 … плюс ключи `Exolon.Step10.*` — третий след версии» | `:55` |
| `engineering/reports/exolon-full-audit-20260920.md:98` | P3-строка V1/V2 и «T2 (нет shared scheme)» | `:98` |
| `engineering/reports/exolon-full-audit-20260920.md:107` | macOS-чеклист п.1 «факт. версия бандла (0.3 vs 0.5)» | `:107` |
| `engineering/reports/exolon-initial-audit.md:40,153,155,159,350,368` | таблица версий и «Зафиксировать фактический CFBundleShortVersionString» | те же |
| `engineering/reports/exolon-initial-audit.md:165` | «Нет shared scheme. Сборка только через явный `-target Exolon`» | `:165` |
| `engineering/reports/exolon-initial-audit-backlog.md:38,42,58` | V1 «MARKETING_VERSION 0.5 vs plist 0.3», T2 «Нет `.xcscheme`», шаг 5 «Записать фактический CFBundleShortVersionString» | те же |
| `evidence/perfile/pbxproj-build.md:10-11` | **fingerprint-носки**: «pbxproj (1474 строки, 133 718 байт, objectVersion = 51)», «Info.plist (24 строки)» — второе уже неверно (28) | `:10-11` |
| `evidence/perfile/pbxproj-build.md:27` / `:29` | «`.xcscheme` в репозитории (любых, включая `xcshareddata`) — **0**», «расхождение версии продукта (pbx `0.5` против бандла `0.3`) — есть, P1» | `:27`, `:29` |
| `evidence/perfile/pbxproj-build.md:135,138,140,142-146` | строки таблицы build settings с якорями `Info.plist:18`, `Info.plist:20`, `Info.plist:21`, «`ENABLE_HARDENED_RUNTIME` отсутствует», «`CODE_SIGN_IDENTITY -`» | те же |
| `evidence/perfile/pbxproj-build.md:190-196,215,222,225` | scheme-слой: «`find . -name "*.xcscheme" …` → **0 совпадений**», «В `Exolon.xcodeproj/` ровно один файл — `project.pbxproj`», «Файла `.gitignore` в репозитории нет», и следствия «`P1` релизный артефакт врёт о себе», «build number не эволюционирует», «архив и notarization недостижимы» | те же |
| `evidence/perfile/pbxproj-build.md:93` | «`Info.plist` … **не** входит в `PBXResourcesBuildPhase` — при `INFOPLIST_FILE` это единственно верное состояние» (не «чинить») | `:93` |
| `evidence/perfile/pbxproj-build.md:311` (вердикт) | «Вердикт: fail … артефакт выходит с неверной версией (`0.3` вместо `0.5`, build number навсегда `1`)» | хвост файла |
| `evidence/perfile/state-hud-weapons.md:63,66,126-128,151-155,163` | SH-08/SH-11 с якорями `Info.plist:18,20 ↔ project.pbxproj:1418,1420,1424,1437,1439,1443` и «`find Exolon.xcodeproj -type f` → только `project.pbxproj`» | те же |
| `evidence/perfile/macos-validation-handout.md:29-31` | «`-target Exolon` обязателен, а не стилистичен: в репозитории **ноль** `.xcscheme`-файлов» | `:29-31` |
| `evidence/perfile/macos-validation-handout.md:137` (M-01) | ожидание прогона: «`CFBundleShortVersionString` = **0.3** … `CFBundleVersion` = **1** … подпись ad-hoc», с колонкой контроля «собралось 0.5 ⇒ вывод V1 неверен» | `:137` |
| `evidence/perfile/ui-text-localization.md:203-204,229` | якоря `project.pbxproj:1424,1443` / `1420,1439` | те же |
| `evidence/perfile/timing-concurrency.md:55,252,255` | якоря `project.pbxproj:1396` и `:1394,1406,1423,1442` | те же |
| `evidence/perfile/economy-score.md:182` | якорь `project.pbxproj:1425` (`PRODUCT_BUNDLE_IDENTIFIER`) | `:182` |
| `evidence/code-review.md:40` | «`project.pbxproj:1420-1424`, `Info.plist:17-18`» | `:40` |
| `evidence/code-review-fullaudit.md:44` | «`MARKETING_VERSION=0.5` @1424/1443 … литерал `0.3` @Info.plist:18» | `:44` |
| `evidence/code-review-fullaudit-final.md:106,125` | «отсутствие shared `.xcscheme` ✓ (`find . -name '*.xcscheme'` → пусто; в `Exolon.xcodeproj` ровно `project.pbxproj`)» и «V1/V2: 0.5 vs 0.3 … `Info.plist:18`» | `:106`, `:125` |
| `evidence/test-review-fullaudit-final.md:43` | AC-008 «подтверждено мной: `find . -name '*.xcscheme'` → пусто» | `:43` |
| `evidence/test-review.md:76` | «Version 0.3 vs 0.5 … needs a built-app check» | `:76` |
| `evidence/analysis-repo_explorer.md:60-61,123-130,205` | «**No** `xcshareddata` / `.xcscheme` on disk», таблица 0.5/0.3, **`project.pbxproj` SHA-256 `d7393eb6…` (1474 lines)** и **`Info.plist` SHA-256 `3e26005f…`** | `:64`, `:130` |
| `evidence/analysis-architect-fullaudit.md:630-631` | «собирается ли таргет … что реально покажет `GENERATE_INFOPLIST_FILE = NO` при `MARKETING_VERSION = 0.5` против `CFBundleShortVersionString = 0.3`» | `:630-631` |
| `evidence/linux-static-audit.md:12-13` | см. §4.2 | `:12-13` |
| `decisions.md:15` | «the committed self-checking tool `evidence/v3_measurements.py` (rc=0 iff the report matches, 11 flipping controls) exists to make that class of error visible» | `:15` |

### 4.4 Особая категория: «связность цитат» — то, что рвётся от *любой* вставки строк

`evidence/perfile/citation-integrity.md:3-8` объявляет слепок `52795d1` и **прямо опирается** на
тождество продуктового дерева: «Продуктовое дерево на этом слепке идентично `403eb13`:
`git diff --stat 403eb13 HEAD -- Exolon Exolon.xcodeproj README.md …` пуст, поэтому ни одна ссылка в
Swift/TMX не могла «уплыть» по содержимому». Правка `Info.plist`/`project.pbxproj`/`README.md`
делает это обоснование **неверным**, и §4.3-якоря (`pbxproj:1418/1420/1424/1437/1439/1443`,
`Info.plist:18/20/21`) разъедутся.
Там же, `citation-integrity.md:22-27`, задокументирован механизм: после баннерных коммитов
«каждый якорь `:NN` в `exolon-full-audit-20260920.md` на новом дереве — это `:NN+11`».
`citation-integrity.md:48` фиксирует **числа строк самих инструментов**: `evidence/privacy_gate.sh` (57),
`engineering/runbooks/macos-probe.sh` (161) — оба совпадают с фактом сейчас (проверено `wc -l`), и
оба станут ложью после правки зонда.

**Практический вывод:** если вставлять `ENABLE_HARDENED_RUNTIME` *дописыванием* строк в блоки
`XCBuildConfiguration`, сдвинутся все 6+ файлов-носителей якорей. Дешевле по цене изменений —
править значения на месте (не меняя число строк pbxproj) и/или явно переоформить якоря одним
документом-эратумом в новом change-пакете, а не молча.

---

## 5. Структура самопроверяющегося верификатора, которую надо копировать

Эталон — `engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/v3_measurements.py`
(391 строка). Канон в `.py`-блобах:

1. **Docstring-контракт** (`:1-14`): «rc=0 ⇔ все замеры совпали с EXPECTED (то есть с цифрами в
   `engineering/reports/exolon-full-audit-20260920-v3.md`). Каждый зонд имеет контроль, который обязан
   дать другое число; если контроль не переворачивается — итог rc=1». Плюс явно запрещённый метод
   («regex-разбор TMX неприменим») с цифрами собственного провала (`:9-12`).
2. **Единственный словарь ожиданий** `EXPECTED: dict[str, object]` (`:35-88`), значения = ровно те
   числа, что напечатаны в отчёте. Никаких «>» и «≈».
3. **Механизм замера → `got[...]`** (`:186-370`), `root` ищётся вверх от файла (`find_root`, `:92-100`)
   и переопределяется `--root` (`:183`), то есть запускаемо на копии.
4. **Мутационные контроли** в отдельном `controls: dict[str, bool]`: они *не* проверяют значение,
   а проверяют, что зонд различает состояния. Типовые формы, все в этом файле:
   - инверсия входных данных: `piston_class(delta=PISTON_TRAVEL)` → «поднять все поршни»
     (`:271-272`), матчер без подстроки `beam_` (`:246-248`),
   - мутация, обязанная создать новый класс эквивалентности, причём обязательно на члене
     дубликат-пары — с комментарием, почему иначе контроль «не перевернулся» бы (`:212-221`),
   - partition-инвариант: сумма классов = число объектов (`:273`, `:300`),
   - «различаю ли я вообще две меры»: `controls["counters_are_counters_not_names"] =
     got["loadcheckpoint_calls"] < len(re.findall(r"loadCheckpoint", joined))` (`:370`) — прямой
     контроль на то, что счётчик не подменили именем.
5. **Сверка и выход** (`:372-387`):
   `mism = {k: (v, got.get(k)) for k, v in EXPECTED.items() if got.get(k) != v}`;
   `"ok": not mism and all(controls.values())` — **оба условия необходимы**;
   `RESULT: ALL_V3_MEASUREMENTS_MATCH_REPORT`/`MISMATCH`; `return 0 if out["ok"] else 1`.
   Текстовый режим печатает `ключ = значение   ✗ ожидалось …` построчно (`:380-383`) — то есть
   diff-пригоден и человекочитаем; `--json` (`:376-379`) даёт `{root, measured, controls, mismatches, ok}`.
6. **Байт-воспроизводимость артефактов** — отдельная, уже проваленная дисциплина:
   `fullaudit_measurements.py:171` пишет `fullaudit-b01-spawn.json` рядом с собой, а
   `:180-186` даёт `return 0 if not failed else 1` с stderr-строкой
   `ALL_MEASUREMENTS_MATCH_REPORT`/`MISMATCH: [...]` (`:185`). У `linux_static_audit.py` такой
   сверки нет и он всегда `return 0` (`:554`) — вот почему его `.md`-артефакт и разехался (§4.2).
7. **Контур с само-недоверием в bash** (`privacy_gate.sh:41-50`): после основных проверок делается
   *положительный* контроль — подсаживается заведомо «грязная» строка в `.git/qwen-privacy-probe.$$`
   и, если она не найдена, `hits += 1000` (`:49`) → FAIL. Формулировка-инвариант в шапке: «Обязан иметь
   положительный контроль: без него «пусто» ничего не значит» (`:7`), а печатный вердикт —
   `RESULT: PASS (0 совпадений, контроль перевернулся)` (`:57`).
8. **Сигнатурные коды выхода в bash-контуре** (оба файла одинаковые): `75` = не тот хост,
   `66` = нет репозитория/цели, `73` = не могу создать каталог вывода, `69` = нет инструмента,
   `2` = неизвестный аргумент (`macos-probe.sh:25`, `:29-31`, `:33-36`, `:44-46`;
   `harness/run.sh:19-21`, `:23-24`, `:27-28`, `:41-43`).
   `harness/run.sh:59-61` — «негативный контроль: без стаба сборка обязана упасть», с `exit 1`
   и фразой «контроль не перевернулся, вывод выше невалиден».

**Что из этого переносится на release-layer-верификатор (в виде шаблона, не решения):** словарь
`EXPECTED` с `shared_xcschemes = 1`, `info_plist_short_version = "$(MARKETING_VERSION)"`,
`info_plist_build_version = "$(CURRENT_PROJECT_VERSION)"`, `hardened_runtime_yes_configs = 2`,
`codesign_flags_contain_runtime = <только после macOS-прогона>`, плюс контроли (i) «regex plist обязан
различать литерал и `$(`-подстановку», (ii) «подстановка pbx-значения на заведомо другое обязана изменить
меру», (iii) partition-инвариант по 4 `XCBuildConfiguration`, и обязательно
положительный контроль по образцу `privacy_gate.sh:46-56`. Сложность: часть мер (codesign flags,
`spctl`, archive) **невыполнима на Linux** — значит верификатор обязан иметь два слоя:
`linux-static-реализуемо` и `macos-only`, с явной пометкой `unverified`, а не `skip` (см. §3, пункт про
`SKIP не может завалить вердикт`).

---

## 6. Managed-stack: что задевается новыми файлами, есть ли коллизии

Владелец определяется не списком файлов, а двумя артефактами:

- `.grok-stack/config/managed.json` — закрытые перечни имён: `agents` (21), `skills` (15),
  `hook_types` (9), `scripts` (13). Всё, кроме этих имён, вне стека не «managed».
  `doctor.py:45-72` сверяет эти перечни с `root/.grok/agents/<name>.toml` и
  `root/.agents/skills/<name>/SKILL.md` — новых записей в них добавление файлов в `Exolon.xcodeproj/`
  или `engineering/changes/…/evidence/` не требует.
- `.grok-stack/config/policy.json` → `control_plane_paths` (`:3-35`) и `protected_paths` (`:37-79`)
  (fallback-копия тех же списков — `_policy_legacy.py:18-30`). Механизм: `Edit/Write/apply_patch`
  на protected-путь требует грант (`_policy_legacy.py:620-624`), Bash-мутация control-plane пути
  блокируется с подсказкой (`policy.py:68-81`).

Проверено матчером стека (`_policy_legacy._matches_any`) на реальных путях:

| путь | control_plane | protected |
|---|---|---|
| `Exolon.xcodeproj/xcshareddata/xcschemes/Exolon.xcscheme` | **нет** | **нет** |
| `Exolon.xcodeproj/project.pbxproj` | нет | нет |
| `Exolon/Resources/Info.plist` | нет | нет |
| `Exolon.xcodeproj/project.xcworkspace/contents.xcworkspacedata` | нет | нет |
| `Exolon.xcodeproj/xcuserdata/…` | нет | нет (и `.gitignore` не покрывает) |
| `engineering/changes/<new>/evidence/<any>` | нет | нет |
| `engineering/reports/<any>.md` | нет | нет |
| `engineering/runbooks/<any>.sh` | нет | нет |
| `engineering/runbooks/publish-v*.md` | **да** | **да** |
| `scripts/release_layer_check.py` | нет | нет |
| `scripts/grok_*.py` | **да** | **да** |
| `README.md`, `.gitignore`, `AGENTS.md`, `VERSION`, `CHANGELOG.md`, `Makefile`, `decisions.md`, `mistakes.md` | **да** | **да** |
| корневые `*_tool_use.py`, `*_compact.py`, `session_*.py`, `stop_gate.py`, `subagent_*.py`, `user_prompt_submit.py` | **да** | **да** |

Ответы по существу:

1. **`Exolon.xcodeproj/xcshareddata/xcschemes/Exolon.xcscheme` ни с чем не коллидирует** — ни
   stack-owned glob не покрывает `Exolon.xcodeproj/**`, ни `managed.json`, ни `manifest.py`
   (его `EXCLUDED_PARTS`/`EXCLUDED_FILES` — `manifest.py:10-15` — про `build`/`dist`/`.env`/`*.sha256`,
   а не про scheme).
2. **`engineering/changes/…/evidence/*` не коллидирует** с защищёнными путями; единственный
   stack-гейт на этом пути — `change-spec` (`verification.py:752-795`), который требует ровно один
   активный spec по `active-change.json`, и лимиты `workflow_artifacts.py:23-24`, которые до
   `evidence/` не применяются.
3. **Что задевается реально:** правка `README.md` (обязательна по `AGENTS.md:26`, «update README.md
   so it matches this tree: current VERSION») — protected/control-plane путь
   (`policy.json:11` control-plane / `:54` protected) ⇒ нужен точный грант на `README.md`.
   Аналогично `.gitignore` (`policy.json:9`/`:52`; если добавлять `build/`, `xcuserdata/`,
   `DerivedData/`) и `decisions.md`/новый `mistakes.md` (контракт `AGENTS.md` section
   «Agent self-learning»).
   `engineering/runbooks/macos-probe.sh` и `engineering/reports/*` — свободны.
   `engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/**` — свободны
   (обновлять измерители можно без гранта).
4. **Манифест пакета стека не пострадает**: `manifest.py` сканирует корень целиком
   (`is_included_relative_path`, `:57-71`), но `MANIFEST.sha256` в репозитории нет
   (`doctor.py:85-94` → `info: "not generated yet; packaging creates it"`), так что коллизии
   «новый tracked-файл vs манифест» нет.
5. Число managed-файлов как зафиксированная метрика (`engineering/runbooks/factory-source.json:8`
   `managed_file_count: 346`) от добавления файла под `Exolon.xcodeproj/` или в `evidence/` не меняется —
   он считает файлы стека, и это отдельно подтверждено в
   `evidence/code-review-fullaudit-final.md:87`.

---

## 7. Найденные по ходу несоответствия (не из постановки)

1. **`evidence/perfile/pbxproj-build.md:11` врёт про размер plist**: «`Exolon/Resources/Info.plist`
   (24 строки)», факт — 28 строк / 932 байта. Якоря `Info.plist:18/20/21` при этом верны, то есть
   расхождение только в счётчике.
2. **Тот же файл, `:195`, и `engineering/reports/exolon-full-audit-20260920.md:87` утверждают
   «Файла `.gitignore` в репозитории нет» / «Нет `.gitignore`».** `.gitignore` есть и отслеживается
   (`git ls-files` → `.gitignore`), добавлен в диапазоне `403eb13..HEAD`. Эти утверждения уже ложны;
   follow-up не должен их «чинить» молча, но обязан не переносить в новый отчёт.
3. **Смещённый якорь:** `evidence/perfile/pbxproj-build.md:198` цитирует
   `engineering/reports/exolon-full-audit-20260920.md:79` как источник утверждения об отсутствии
   scheme, а фактически это `:91` — ровно тот сдвиг «+11», который предсказан в
   `citation-integrity.md:22-27`.
4. **Зонд не имеет ни одного числового EXPECTED на секцию C** — единственная количественная строка,
   `:91`, меряет не бандл, а pbxproj, и не имеет аннотации; `:95-97` не имеют ожиданий вовсе.
   То есть артефакт macOS-прогона сегодня **нельзя** сверить с ожиданием автоматически — только глазами.
5. **Зонд не умеет различать (c)** (см. §2.2, строки `:97` и `:151`): даже после добавления
   `ENABLE_HARDENED_RUNTIME = YES` прогон ничего не покажет.
6. `Exolon/Resources/Info.plist` не входит в `PBXResourcesBuildPhase` — правильно
   (`perfile/pbxproj-build.md:129-133`); при правке plist не надо «чинить» его членство в фазах.

---

## 8. Итоговая карта правок (для архитектора, не решение)

Минимальное замыкающее множество носителей P1-11 и всё, что обязано за ним последовать в том же
дереве, — в порядке возрастания цены:

1. `Exolon/Resources/Info.plist:18,20` → `$(MARKETING_VERSION)` / `$(CURRENT_PROJECT_VERSION)`
   (прецедент подстановок уже есть в `:6,8,10,14`); `:22` (`LSMinimumSystemVersion`) — тот же класс
   долга, но вне формулировки P1-11.
2. `project.pbxproj:1415-1416` и `:1434-1435` (оба target-конфига) → подпись/hardened runtime.
   Цена: сдвиг якорей §4.4. Дешёвый вариант — правка на месте без вставки строк.
3. Новый `Exolon.xcodeproj/xcshareddata/xcschemes/Exolon.xcscheme` (blueprint `500000000000000000000001`,
   `BuildableName = Exolon.app`, product-ref `200000000000000000000010`) + Archive action.
4. `.gitignore` (+`build/`, `xcuserdata/`, `*.xcworkspace`, `DerivedData/`) — protected, нужен грант.
5. `engineering/runbooks/macos-probe.sh` — строки `:64`, `:69-70`, `:86`, `:88-91`, `:95-97`, `:151`;
   после правки обновить счётчик строк в `citation-integrity.md:48` (сейчас 161).
6. `evidence/v3_measurements.py:84-86` — EXPECTED-значения scheme/target (rc=1 до правки, §4.1).
7. `evidence/linux_static_audit.py:436-438,495-496` — различать literal vs `$(…)`; учесть
   §4.2 byte-repro-defect.
8. Новый release-layer-верификатор по шаблону §5 (место: `scripts/` ⇒ под ruff+bandit,
   `engineering/…/evidence/` ⇒ вне любой линтер-зоны; решение о месте — за архитектором, оба пути
   легальны и ни один не protected).
9. Документ-эратум для §4.3/§4.4 (якоря и «find → 0 совпадений» в 12 markdown-носителях).

---

## Краткое резюме (10 самых load-бearing фактов)

1. Версия продукта живёт в **пяти** несведённых носителях: `Info.plist:18` = `0.3`, `Info.plist:20` = `1`,
   `pbxproj:1424/1443` = `MARKETING_VERSION 0.5` (grep-счётчик = 2), `pbxproj:1418/1437` = `CURRENT_PROJECT_VERSION 1`,
   плюс «Step 9»/`STEP 10`/`Exolon.Step10.*` в `AppDelegate.swift:16`, `GameScene.swift:832`, `GameState.swift:25-31`.
2. Подстановки в `Info.plist` **уже работают** (`:6,8,10,14` = `$(DEVELOPMENT_LANGUAGE)`/`$(EXECUTABLE_NAME)`/
   `$(PRODUCT_BUNDLE_IDENTIFIER)`/`$(PRODUCT_NAME)`) ⇒ переход на `$(MARKETING_VERSION)` механичен, `GENERATE_INFOPLIST_FILE = NO` (`:1420/1439`) не мешает.
3. Схем нет: `find . -name '*.xcscheme'` → 0, в `Exolon.xcodeproj/` ровно один файл; единственный
   синтаксис сборки — `-target Exolon` (`macos-probe.sh:79`).
4. `macos-probe.sh` **не детектирует hardened runtime вообще**: `:97` меряет entitlements вместо `flags=…(runtime)`,
   `:95-97` без EXPECTED, а инвариант `:151` утверждает отсутствие `ENABLE_HARDENED_RUNTIME` текстом.
5. Правка scheme ломает закоммиченный измеритель: `v3_measurements.py:84` `EXPECTED["shared_xcschemes"]=0`
   при измерении `:367` ⇒ rc=1 (`:387`) с момента добавления любого `.xcscheme`.
6. `linux_static_audit.py` никогда не падает (`return 0`, `:554`), но **перезаписывает**
   `linux-static-audit.md:12-13` / `.json`, которые сейчас утверждают «0.3» и «['0.5']»;
   побайтовая воспроизводимость `.md` уже сломана (`exolon-full-audit-20260920-v3.md:169-172`).
7. `grok_verify --mode pr` **слеп к продукту**: 0 упоминаний `.swift/.tmx/xcodeproj/.plist/.xcscheme` в
   `verification.py`; реальная угроза — `git-diff-check` (`verification.py:594-652`, хвостовые пробелы/EOF)
   и разъезд `tree_fingerprint`; `engineering/` исключён из ruff (`ruff.toml:9`) и bandit (`bandit.yaml:3`).
8. Ни один путь правки не protected, **кроме** `README.md` и `.gitignore` (оба control-plane+protected,
   `.grok-stack/config/policy.json:9,11` и `:52,54`) ⇒ нужен точный грант; `Exolon.xcodeproj/**` и
   `engineering/changes/.../evidence/**` коллизий со стеком не имеют (проверено матчером).
9. Вставка строк в `pbxproj` до строки 1418 сдвигает якоря в **7** markdown-носителях
   (`pbxproj-build.md`, `state-hud-weapons.md`, `ui-text-localization.md`, `timing-concurrency.md`,
   `economy-score.md`, `macos-validation-handout.md`, `code-review*.md`) и разрушает предпосылку
   `citation-integrity.md:3-8` («дерево идентично `403eb13`»).
10. Шаблон верификатора готов к копированию — `v3_measurements.py`: `EXPECTED`-словарь + `got` +
    `controls` (инверсия входа, мутация, partition, «различаю ли я две меры») +
    `"ok": not mism and all(controls.values())` + `RESULT:`-строка + `return 0/1`;
    положительный контроль по образцу `privacy_gate.sh:46-56`.
