# Requirements — закрытие P1-11 (release layer): один источник истины для версии бандла + общая схема с Archive

> Typed authority: [`change-spec.yaml`](change-spec.yaml). Этот Markdown объясняет контекст
> и не может переопределить типизированные ID, риск, acceptance criteria, forbidden outcomes
> и области approvals.

Change: `20260921-close-audit-finding-p1-11-release-layer-for-the-2e7698`
Авторитет находки: `engineering/reports/exolon-full-audit-20260920-v3.md:36` (строка P1-11)
и `engineering/reports/exolon-full-audit-20260920-v3.md:130` (backlog).

## Finding в терминах измеряемого

P1-11 «Релизный слой не годен для публикации» опирается на три клаузы доказательств:
**версии**, **схема**, **подпись**. Это изменение закрывает первые две и осознанно оставляет
третью открытой (см. §Отсрочка) — находка фиксируется как **закрытая частично**.

Клауза «версии» — не «версия устарела», а **два источника истины для одного идентификатора**:
`Exolon/Resources/Info.plist` нёс литералы `0.3` / `1`, тогда как `project.pbxproj` нёс
`MARKETING_VERSION = 0.5` и `CURRENT_PROJECT_VERSION = 1` в обоих target-конфигах, а
`GENERATE_INFOPLIST_FILE = NO` означал, что в бандл печатается литерал plist.

## Acceptance criteria

Каждый AC — бинарное утверждение, измеряемое `evidence/release_layer_check.py` на Linux
(48 AC-строк, 29 контролей), либо явно помеченное как macOS-only и потому **не** засчитываемое.

| AC | Утверждение | Измерение (имена в верификаторе) |
| --- | --- | --- |
| AC-001 | Идентификатор версии имеет один источник: plist отдаёт `CFBundleShortVersionString`/`CFBundleVersion` подстановками, литералов в этих двух значениях нет, остальные 9 ключей plist не тронуты | `plist_version_keys_substituted=2`, `plist_version_keys_literal=0`, `plist_nonversion_untouched=1`, `plist_key_count=11` |
| AC-002 | Обе подстановки ссылаются на настройки, лежащие **в target-конфигах**, а не «где-то в файле» | `marketing_version_in_target_configs=2`, `marketing_version_outside_target_configs=0`, `project_version_in_target_configs=2`, `project_version_outside_target_configs=0`, `infoplist_file_setting_in_target_configs=2`, `generate_infoplist_off_in_target_configs=2` |
| AC-003 | Общая схема существует ровно одна, по каноническому пути, и не заезжает в `xcuserdata` | `shared_scheme_count=1`, `shared_scheme_path_exact=1`, `user_scheme_count=0` |
| AC-004 | Схема адресует реальный единственный native target и продукт Xcode-канона: действия на месте, архивация — Release, запуск — Debug | `scheme_actions_required=4`, `scheme_build_entry_flags_yes=5`, `scheme_build_for_archiving_yes=1`, `scheme_buildable_refs_total=4`, `scheme_blueprint_guid_is_exolon=1`, `scheme_runnable_is_application=1`, `scheme_archive_build_configuration="Release"`, `scheme_launch_build_configuration="Debug"`, `scheme_buildable_refs_bad_container=0` |
| AC-005 | Тест-таргет не ввезён, висячих testable-ссылок нет | `test_target_count=0`, `native_target_count=1`, `scheme_dangling_test_refs=0` |
| AC-006 | Runbook `engineering/runbooks/macos-probe.sh` пере-нацелен: не остаётся EXPECTED, утверждающих старый gap, и появляется archive-шаг той же схемой | `runbook_stale_gap_claims=0`, `runbook_archive_step_present=1` |
| AC-007 | Отсрочка hardening записана plan-документом, а не молча пропущена | `hardened_runtime_key_count=0` **⇒** `hardened_deferral_recorded=1` (токен `ENABLE_HARDENED_RUNTIME` в plan-файлах пакета) |
| AC-008 | Владение landmine записано: red-состояние `v3_measurements.py` после добавления схемы — ожидаемый cutover | `v3_pin_shared_xcschemes=0`, `v3_shared_scheme_cutover_owned=1` (токен `shared_xcschemes` в plan-файлах) |
| AC-009 | Датированные доказательства не переписаны | `reports_dated_count=2`, `reports_blob_mismatches=0` (worktree == HEAD == pin-коммит) |
| AC-010 | macOS-половина не засчитана на Linux: собранные `0.5`/`1`, отсутствие неразвёрнутых `$(`, разрешаемость `-scheme Exolon` и archive доказывает только macOS | у верификатора нет ни одного AC про собранный бандл; доказательства — `engineering/runbooks/macos-probe.sh` §C/§B2 и `evidence/perfile/macos-validation-handout-v2.md` |

## Отсрочка (это не «забыли», это решение с причиной)

`ENABLE_HARDENED_RUNTIME` в этом изменении **не включается** ни в один конфиг. Причина: при ad-hoc
`CODE_SIGN_IDENTITY = "-"` и `CODE_SIGN_STYLE = Manual` hardened runtime не меняет ни исход
Gatekeeper, ни нотаризацию (нужен Developer ID), но добавляет рантайм-ограничения (library
validation, запрет unsigned executable memory, ограничения отладки) бинарнику, у которого
**первая успешная сборка ещё не доказана** (M-01 в handout ожидает именно её). Включать флаг в том
же изменении, которое впервые устанавливает собираемость, значит потерять атрибуцию отказа.
Порядок: M-01′ зелёный → отдельный change с контролем
`codesign -d --verbose=4 "$APP" | grep -o 'flags=0x[0-9a-f]*(.*)'` → токен `runtime`.

## Failure and edge cases

- Если Xcode не подставит настройки, бандл покажет литерал `$(MARKETING_VERSION)` — это ловит §C
  probe (`plist_unexpanded_placeholders` обязан быть 0) и AC-010, а не Linux-вердикт.
- Если схему написать «на глаз», отказ будет тихим: `-scheme Exolon` просто перестанет резолвиться.
  Отсюда AC-004 (структура + перекрёстная сверка `BlueprintIdentifier` с pbxproj) и §B2 probe.
- Регистр префикса контейнера (`Container:` вместо `container:`) — реальная ошибка черновика
  верификатора: самосогласованные синтетики были зелёными со значением, которое Xcode в контейнер
  не разворачивает. Контроль `container_prefix_casing_rejected` обязан краснить заглавную форму.
- Формулировка маршрута требует «enable the hardened runtime». Явное сужение области до
  «записать отсрочку» — решение по gate `scope_and_design_approval`, обосновано выше и в
  `evidence/analysis-architect.md` §2; владелец может переопределить отдельным change.

## Governance context

Каталога `governance/` в этом дереве нет (проверено), canonical-правил, примеров и долгов по
губернанс-конттуру этот change не создаёт и не отзывает. Прикладные правила, которым он следует,
— AGENTS.md (append-only к датированным доказательствам, никаких секретов и подписных ключей в
дереве, доставка только через PR) и правило repo «каждый зонд обязан иметь контроль, который
обязан перевернуться».

- Applicable rule IDs: нет (governance-реестр отсутствует).
- Canonical-example deviations and evidence: нет.
- Intentional debt created, repaid, or accepted: принята часть долга P1-11 — клауза «подпись»
  (hardened runtime / Developer ID / нотаризация) остаётся открытой осознанно, AC-007.

## Non-functional requirements

- Security: подписи, ключей и секретов в дереве не появляется; `DEVELOPMENT_TEAM` не заполняется.
- Reliability: откат = один `git revert`; состояния не затрагиваются (bundle id `com.exolon.remake`
  не менялся ⇒ HighScore/checkpoint-ключи `defaults` живы в обе стороны).
- Performance: нет.
- Observability: `release_layer_check.py` rc + строка на AC; rc `v3_measurements.py` как
  cutover-сигнал; probe-строки `version_single_source=MATCH|MISMATCH`,
  `plist_unexpanded_placeholders`, `codesign_flags`, `showdestinations_rc`, `archive_rc`.
