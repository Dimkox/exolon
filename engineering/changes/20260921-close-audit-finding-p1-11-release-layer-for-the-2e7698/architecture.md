# Architecture — релизный слой Exolon: идентификатор версии, общая схема, доказательство

> Typed authority: [`change-spec.yaml`](change-spec.yaml)

## Где теперь истина

| Факт | Единственный источник | Что от него зависит |
| --- | --- | --- |
| MARKETING_VERSION (`0.5`) | `Exolon.xcodeproj/project.pbxproj`, target-конфиги `800…003` (Debug) и `800…004` (Release) | `Info.plist:CFBundleShortVersionString` = `$(MARKETING_VERSION)`; About/Finder/`mdls`; probe §C сверяет собранный бандл с `xcodebuild -showBuildSettings` |
| CURRENT_PROJECT_VERSION (`1`) | те же target-конфиги | `Info.plist:CFBundleVersion` = `$(CURRENT_PROJECT_VERSION)` |
| Путь plist | `INFOPLIST_FILE = Exolon/Resources/Info.plist` в target-конфигах; `GENERATE_INFOPLIST_FILE = NO` | механизм подстановки уже использовался четырьмя ключами (`DEVELOPMENT_LANGUAGE`, `EXECUTABLE_NAME`, `PRODUCT_BUNDLE_IDENTIFIER`, `PRODUCT_NAME`) — новых настроек изменение не вносит |
| Архивируемая конфигурация | `Exolon.xcodeproj/xcshareddata/xcschemes/Exolon.xcscheme`, `ArchiveAction buildConfiguration = "Release"` | `xcodebuild -scheme Exolon archive`; до этого archive не было на что вешать (общих схем — 0) |

`LSMinimumSystemVersion` остаётся литералом `10.14` и **совпадает** с `MACOSX_DEPLOYMENT_TARGET`:
P1-11 — про расходящийся идентификатор, а не про всякий литерал. Подстановка floor'а отложена в тот же
change, где deployment target будет валидироваться на реальной машине.

## Почему схема — часть архитектуры, а не удобства

`Archive` — действие схемы. Без общего `.xcscheme` в дереве нет артефакта, называющего конфигурацию
архивации и архивируемый продукт; handout это и фиксировал («`-target Exolon` обязателен, а не
стилистичен»). Схема добавляется без правки `project.pbxproj`: Xcode не хранит общие схемы в объектном
графе проекта — отсюда минимальность диффа (2 строки plist + 1 новый файл).

Канон формы (четыре `BuildableReference`, `ArchiveAction` без собственной ссылки,
Test/Launch/Analyze = Debug, Profile/Archive = Release, `ReferencedContainer = "container:…"`) взят
по фактической форме вывода Xcode, а не по «достаточной для парсера»: самодельная форма, которую
парсер XML принимает, — это ровно тот тихий отказ, который ловит AC-004 и probe §B2.

## Доказательная цепочка и её границы

1. `evidence/release_layer_check.py` — закоммиченный самопроверяющийся Linux-инструмент: 48 бинарных
   AC + 29 контролей, каждый контроль обязан перевернуться. rc=0 ⇔ состояние пост-фикса **и**
   причинность (контроль `undo_fix_is_red`: четыре независимых отката плана, каждый красит только свои AC).
   Это единственный Linux-авторитет изменения: `grok_verify --mode pr` не видит ни `.plist`, ни
   `.pbxproj`, ни `.xcscheme` (проверено по исходникам верификатора).
2. `engineering/runbooks/macos-probe.sh` §C/§B2 — доказательство семантики на macOS: подстановка
   сработала (`version_single_source=MATCH`, `plist_unexpanded_placeholders=0`), схема резолвится
   (`showdestinations_rc=0`), archiveattempt отдельный (`WITH_ARCHIVE=1`).
3. `evidence/perfile/macos-validation-handout-v2.md` — протокол одной сессии, закрывающей и M-01.

## Владельчество landmine (обязательно к прочтению до «починки»)

`engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/v3_measurements.py` пинит
`shared_xcschemes = 0` и считает его как `root.glob("**/*.xcscheme")`. Добавление общей схемы
детерминированно делает этот закоммиченный измеритель красным: `НЕСОВПАДЕНИЯ: {"shared_xcschemes": [0, 1]}`.

Это **ожидаемый cutover, а не регрессия**, и он принадлежит этому изменению. Пин не правится:
v3 фиксирует состояние аудированного коммита. Правка «чтобы всё было зелёное» — удаление схемы —
красится самим `release_layer_check.py` (`shared_scheme_count=0 RED ожидалось 1`). Владелец перехода:
этот пакет; авторитет после перехода на `release_layer_check.py` по клаузам версии и схемы.

## Сосуществование с датированными доказательствами

Датированные артефакты (`engineering/reports/exolon-full-audit-20260920*.md`,
`.../7db1f3/evidence/**`, `v3_measurements.py`) в этом изменении **не редактируются** — правило
append-only машинно проверено AC-009 (сверка blob worktree == HEAD == pin-коммит). Дельта закрытия
живёт здесь и в `release.md`; следующий прогон аудита пересоберёт отчёт целиком (так же, как v3
заменил v2), а не будет править предыдущий.
