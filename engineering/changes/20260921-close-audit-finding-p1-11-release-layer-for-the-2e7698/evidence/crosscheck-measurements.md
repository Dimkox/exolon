# Cross-check измерений для P1-11 (release layer) — независимая пере-проверка трёх отчётных клеймов

- Дата: 2026-09-21. HEAD: `d4c7a58b81397dc1c08a5410bb0db64e2dc0dfc5`, branch `codex/release-layer-p1-11-20260921`.
- Хост: Linux (Swift 6.4 toolchain есть, Xcode/xcodebuild/codesign — нет; macOS-специфика проверялась статически + синтетическими контролями).
- **/tmp-репродукция: `/tmp/exolon-p1-11-xcheck`** (rsync -a всего дерева, включая `.git`; после всех экспериментов возвращена в чистое состояние — `git status --porcelain` = только untracked-каталог этого evidence-дро).
- `python3 scripts/grok_verify.py --mode pr` **не запускался** (пишет receipts от имени route) — выводы по (i)/(ii)/(iii) ниже извлечены **из исходников** верификатора; файл и строки указаны.

## Итоговая таблица

| # | Клейм | Вердикт | Команда измерения | Наблюдённые числа | Результат контроля |
|---|-------|---------|-------------------|-------------------|--------------------|
| 1 | `v3_measurements.py` пинит `shared_xcschemes: 0` ⇒ добавление `.xcscheme` детерминированно даёт exit 1 | **HOLDS** | `python3 evidence/v3_measurements.py` (реальное дерево) и `--root /tmp/exolon-p1-11-xcheck` (мутации) | реал. дерево: RC=**0**, строка вывода `shared_xcschemes = 0`; в дереве 0 файлов `*.xcscheme` (find, без `.git`); пин :84, замер :367 (`root.glob("**/*.xcscheme")`), mism :372, ok :374, `RESULT` :386, `return 0/1` :387, `sys.exit` :391 | +1 scheme → RC=**1**, единственный mismatch `{"shared_xcschemes": [0, 1]}`; control-декой `.txt` со словом xcscheme → RC=0; удаление scheme → RC=0 (детерминированно) |
| 2 | `Info.plist` уже живёт на build-setting подстановке при `GENERATE_INFOPLIST_FILE = NO` ⇒ `$(MARKETING_VERSION)`/`$(CURRENT_PROJECT_VERSION)` — не новый механизм | **HOLDS** (с находкой: версии уже расходятся 0.3 vs 0.5) | `grep -n`/чтение `Exolon/Resources/Info.plist`, `Exolon.xcodeproj/project.pbxproj`; мутация на /tmp-копии | plist: 4 значения `$(...)` — `$(DEVELOPMENT_LANGUAGE)` :6, `$(EXECUTABLE_NAME)` :8, `$(PRODUCT_BUNDLE_IDENTIFIER)` :10, `$(PRODUCT_NAME)` :14; литералы `0.3` :18, `1` :20. pbxproj: `GENERATE_INFOPLIST_FILE = NO` :1420 (Debug-конфиг цели) и :1439 (Release), `INFOPLIST_FILE=…Info.plist` :1421/:1440, `MARKETING_VERSION = 0.5` :1424/:1443, `CURRENT_PROJECT_VERSION = 1` :1418/:1437 | `INFOPLIST_PREPROCESS` и `INFOPLIST_EXPAND_BUILD_SETTINGS`: **0** вхождений в проекте (grep по всему дереву; только упоминания в evidence-маркдауне) ⇒ существующие 4 ключа уже полагаются на дефолт Xcode. Мутация E5 на /tmp: замена `0.3`→`$(MARKETING_VERSION)`, `1`→`$(CURRENT_PROJECT_VERSION)` → XML парсится, v3 RC остаётся **0** (эти поля v3 невидимы) — значит верификатор релизного слоя, а не v3, обязан утверждать единство версии |
| 3 | `macos-probe.sh` §A решает «shared scheme» по подстроке из `xcodebuild -list`, а :97 берёт hardened runtime из дампа entitlements | **HOLDS** | Чтение `engineering/runbooks/macos-probe.sh` :62–:70, :86–:97, :151 + Linux-контроль `/tmp/p3_ctl.sh` (дословный реплейс case-паттерна и формата вывода двух codesign-команд) | :66 `LIST=$(xcodebuild -project "$TARGET" -list 2>&1 \| tr '\n' '\|')`; :69 `*"Schemes"*"Exolon"* → PRESENT`; :70 иначе ABSENT; :97 `hardened_runtime=$(codesign -d --entitlements :- … \| head -c 200)`; :95 `codesign -dv … head -c 300` (не ассертится) | Контроль A: дамп «0 схем»→ABSENT, дамп «автоген-only, 0 общих схем на диске»→**PRESENT** (ложноположительный переворот), «shared»→PRESENT — дискриминатора нет. Контроль B: `grep -Ec 'flags=0x[0-9a-f]+\(.*runtime'` по дампу `--entitlements` = **0** (команда физически не содержит флаг), по дампу `--verbose=4` = **1** |

## Детали CLAIM 1

- Замер :367 — `len(list(root.glob("**/*.xcscheme")))`. Это **не только shared**: любой `.xcscheme` в любом месте дерева, включая не-committed `xcuserdata/…/xcschemes/`, инвертирует rc. Для планирования P1-11 это важнее формулировки клейма: добавление общей схемы (нужной для Archive) **гарантированно** ломает закоммиченный самопроверяющий измеритель аудита, и это надо учитывать в плане (либо обновить EXPECTED в v3, либо новый верификатор релизного слоя должен стать авторитетным — v3 пинит «0» как finding-baseline 2026-09-20).
- Верность репродукции: `git rev-parse HEAD` в копии = `d4c7a58b…` (тот же); `rsync -rn --checksum -i --exclude=.git` между оригиналом и копией — пустой вывод (0 контентных различий); `git status --porcelain` идентичен.
- Полный лог экспериментов: `/tmp/e1_baseline.txt` (RC=0), `/tmp/e2_decoy.txt` (RC=0), `/tmp/e3_scheme.txt` (RC=1; `shared_xcschemes = 1 ✗ ожидалось 0`), `/tmp/e4_revert.txt` (RC=0), `/tmp/v3_real_tree.txt` (реальное дерево, RC=0).

## Детали CLAIM 2

- Находка (никто не спрашивал, но она load-bearing для плана): **версии уже рассинхронизированы** — `Info.plist` несёт `0.3`, `project.pbxproj` несёт `MARKETING_VERSION = 0.5` в обоих конфигурациях. Замена литералов на подстановки изменит эффективную версию бандла с 0.3 на 0.5 (сам probe это и ожидает: :86 `EXPECTED: CFBundleShortVersionString=0.3 при MARKETING_VERSION=0.5`). Before/after-ожидания §C probe обязаны быть обновлены тем же изменением.
- Оговорка: окончательное доказательство подстановки возможно только macOS-сборкой (`xcodebuild -showBuildSettings | grep INFOPLIST_EXPAND_BUILD_SETTINGS` + `plutil -extract` из собранного бандла); на Linux доказуемо ровно то, что механизм подстановки уже используется четырьмя ключами при `GENERATE_INFOPLIST_FILE = NO` и ни один project-side preprocessor-флаг не выставлен — то есть новых настроек замена не вносит.

## Детали CLAIM 3 — корректные дискриминаторы для macOS

- Shared scheme: проверка файла на диске + факта коммита: `[ -f Exolon.xcodeproj/xcshareddata/xcschemes/Exolon.xcscheme ]` и `git ls-files -- '*.xcscheme'` (это ровно то, что уже измеряет v3:367 и §A probe не видит).
- Hardened runtime: `codesign -d --verbose=4 "$APP" 2>&1` и поиск `flags=0x10000(runtime)` (бит 0x10000; регэксп-класс: `flags=0x[0-9a-f]+\(.*runtime`). `codesign -d --entitlements` для этого неприменим: он печатает plist энтайтлментов, где флага нет даже при включённом runtime.

## Дополнительно: на что реагирует `scripts/grok_verify.py --mode pr` (только из исходников; НЕ исполнялся)

Точка входа `scripts/grok_verify.py:19 → adaptive_grok.verification.verify(root,'pr',record=True)`. Состав проверок pr-режима: `git-diff-check` (:1095→:594), `change-spec` (:1080→:750), `architecture`, `governance`, `workflow-artifacts` (:267–:360), `secret-scan` (:1100→:648), `contracts` (:1101→:699), `sql-safety` (:1102→:725), условные php/bitrix/frontend, semgrep (конфигов в репо нет → не создаётся), trivy (нет Dockerfile/compose → не создаётся), `_python` = ruff+bandit (:818–:857; `tests/`, `pyproject.toml`, `requirements.txt`, `setup.py` в репо отсутствуют → pytest/unittest-ветки не заводятся), `source-stability` (:1118). Роут сейчас: `quality_profiles=[base, frontend]`, `base_commit=403eb132…`; `frontend` вызывает `_node`, но `package.json` нет → `[]` (:995–:996).

- Механизм реакции на **любые** из трёх мутаций: `tree_fingerprint` (util.py:170) = SHA256(HEAD + путь+контент каждого файла из `changed_files` (util.py:134: `git diff --cached`, `git diff`, `git ls-files --others --exclude-standard`, плюс `base...HEAD`)); `.gitignore` не скрывает ни `*.xcscheme`, ни pbxproj, ни evidence-файлы ⇒ каждый новый/изменённый файл меняет отпечаток ⇒ все прошлые receipts считаются stale (receipts.py:702) и на повторном прогоне workflow-artifacts/receipt-гейт переворачивается; `source-stability` падает, если дерево меняется во время прогона (:1118–:1132).
- (i) новый `.xcscheme`: попадает в `changed_files` даже untracked → отпечаток; `secret-scan` читает содержимое (:653–:666; три regex, для схем обычно чисто); после коммита в ветку его range `base..HEAD` сканируется `git diff --check` только на whitespace (:601/:610–:616) — таб-индентированный XML Xcode-схем проходит. Содержимое схемы как таковое не парсит никто; swift/xcodebuild/plist-проверок в верификаторе нет (grep `swift|xcodebuild|plist` по verification.py = 0).
- (ii) правка `project.pbxproj`: то же — отпечаток + secret-scan + whitespace; содержательных проверок pbxproj в `grok_verify` нет (контент pbxproj читает только v3-измеритель, и то лишь для `generated_terrain`/`unit-test` regex — правка `MARKETING_VERSION` на них не влияет).
- (iii) новые файлы под `engineering/changes/<id>/evidence/`: в `changed_files` → отпечаток; `change-spec` проверяет только пути `…/change-spec.yaml` (:751–:753) — evidence-файлы валидации spec не получают; `workflow-artifacts` завязан на манифест активного change: обычные новые evidence-файлы, не перечисленные в манифесте, контентно не проверяются, но если артефакт перечислен в манифесте — его digest-сходимость падает (:310–:330). ruff/bandit эти файлы не видят: `QUALITY_PY_PATHS` (:818) = фиксированный tuple без `engineering/` ⇒ новый самописный release-layer-верификатор, положенный в evidence/, линтером `grok_verify` не покрывается; в `scripts/` — покрывается (ruff и bandit на хосте установлены).

## Команды-источники для повторения

```bash
python3 engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/v3_measurements.py   # RC=0
rsync -a /home/pall/projects/exolon/ /tmp/exolon-p1-11-xcheck/ && rsync -rn --checksum -i --exclude=.git /home/pall/projects/exolon/ /tmp/exolon-p1-11-xcheck/   # пусто = верно
mkdir -p /tmp/exolon-p1-11-xcheck/Exolon.xcodeproj/xcshareddata/xcschemes && touch /tmp/exolon-p1-11-xcheck/Exolon.xcodeproj/xcshareddata/xcschemes/Exolon.xcscheme
python3 /tmp/exolon-p1-11-xcheck/engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/v3_measurements.py --root /tmp/exolon-p1-11-xcheck   # RC=1, mism={shared_xcschemes:[0,1]}
bash /tmp/p3_ctl.sh   # контроль A/B клейма 3
```
