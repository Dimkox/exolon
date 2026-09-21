# Close audit finding P1-11 (release layer) for the Exolon macOS game: make bundle version identity single-sourced from build settings, add a shared Xcode scheme with an Archive action, enable the hardened runtime, update the macOS probe expectations that assert the old gaps, and add a committed self-checking release-layer verifier.

> Typed authority: [`change-spec.yaml`](change-spec.yaml). This Markdown explains context and cannot override typed IDs, risk, acceptance criteria, forbidden outcomes, or approval scopes.

Change ID: `20260921-close-audit-finding-p1-11-release-layer-for-the-2e7698`
Created: 2026-09-21T04:43:07+00:00
Risk: high
Complexity: high-risk
Domains: frontend

## Problem

Формулировка маршрута требует «enable the hardened runtime»; в этом изменении она
**не** выполняется и причина записана (см. Scope/Constraints и `release.md` §Deferred): при
ad-hoc `CODE_SIGN_IDENTITY = "-"` флаг ничего не меняет ни в Gatekeeper, ни в нотаризации,
но добавляет рантайм-принуждение бинарнику, чья первая успешная сборка ещё не доказана.
Сужение области — решение по gate `scope_and_design_approval`, владелец может переопределить
отдельным change (условие: зелёный M-01′).

Сама находка (`engineering/reports/exolon-full-audit-20260920-v3.md:36`) измеряла три
клаузы: версии, схема, подпись. Версии имели **два источника истины** — литералы plist при
build-настройках таргета; общей схемы не было ни одной, поэтому действие Archive не на что
было повесить; ожидания macOS-probe утверждали старый gap как ожидаемое состояние.

## Outcome

После сборки на macOS About/Finder/`mdls` показывают `0.5` (значение `MARKETING_VERSION`),
а не устаревший литерал `0.3`; в дереве есть одна общая схема `Exolon`, пригодная для
`xcodebuild -scheme Exolon archive`; probe больше не ждёт «нет схемы» и «версия 0.3»;
и всё, что вообще проверяемо на Linux, проверяется закоммиченным самопроверяющимся
инструментом (`evidence/release_layer_check.py`), а не прозой в отчёте.

## Scope

### In scope

- `Exolon/Resources/Info.plist`: `CFBundleShortVersionString` → `$(MARKETING_VERSION)`,
  `CFBundleVersion` → `$(CURRENT_PROJECT_VERSION)`; остальные ключи не тронуты (digest).
- `Exolon.xcodeproj/xcshareddata/xcschemes/Exolon.xcscheme`: новый общий файл схемы по
  канону Xcode, `buildForArchiving = "YES"`, `ArchiveAction@Release`, `LaunchAction@Debug`.
- `engineering/runbooks/macos-probe.sh`: пере-нацеливание §A/§C/§F, дискриминатор
  «общая vs автосгенерированная» схема, §B2 (`-scheme`, `-showdestinations`, archive attempt),
  чтение hardened runtime из `codesign -d --verbose=4` flags вместо дампа энтитлментов.
- Change-пакет: типизированный `change-spec.yaml`, планы, `evidence/release_layer_check.py`
  (48 AC, 29 обязательных переворотов), `evidence/perfile/macos-validation-handout-v2.md`.

### Out of scope

- Включение hardened runtime в сборку, `.entitlements`, любые подписные identity,
  команды и секреты (токен настройки и причина отсрочки названы плановыми документами —
  `release.md` §Deferred, а не этим автогенированным файлом).
- Выбор самого номера версии (0.5 ↔ 0.3): устраняется двойной источник, а не назначается число.
- `project.pbxproj` (включая `objectVersion`/upgrade проекта), любой `Exolon/*.swift`,
  XCTest-таргеты, иконка приложения, `LSMinimumSystemVersion`, `LSApplicationCategoryType`,
  миграция на `GENERATE_INFOPLIST_FILE = YES`, нотаризация и App Store.
- Правка датированных отчётов и `v3_measurements.py` (append-only, машинно проверено AC-009).

## Constraints

- Backward compatibility: публичного API нет; поведение игры не меняется; bundle id остаётся
  `com.exolon.remake`, поэтому `defaults`-состояния (HighScore, checkpoint) не затрагиваются.
  Откат — один `git revert`.
- Data/privacy: миграций и записей в хранилища нет; секреты и ключи в дерево не попадают.
- Performance: нет.
- Operational: `v3_measurements.py` после merge ожидаемо красный на `shared_xcschemes`
  (0 → 1) — это владеемый этим пакетом cutover, а не регрессия; удаление схемы ради зелёного v3
  запрещено (FORBID-004). Окончательная семантика подстановки и живость схемы доказываются только
  на macOS (AC-010), Linux-вердикт их не засчитывает.
