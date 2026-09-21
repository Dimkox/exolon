# P1-11 release-layer verifier — DRAFT analysis + run transcript

> **Статус 2026-09-21 (имплементация):** инструмент выпущен из черновика в
> `evidence/release_layer_check.py`; черновик `release_layer_check.draft.py` удалён, чтобы в пакете
> не осталось второй, уже неверной версии. Всё, что ниже, — дословный протокол репетиции на
> пред-фиксном дереве и не правится; расхождения с финалом перечислены в §9 в конце файла.


Изменение: `20260921-close-audit-finding-p1-11-release-layer-for-the-2e7698`
Дерево на момент прогона: branch `codex/release-layer-p1-11-20260921`, HEAD `d4c7a58` (product tree
не тронут: `git status --porcelain` → только untracked `engineering/changes/20260921-…/`).
Инструмент: `evidence/release_layer_check.draft.py` (этот же каталог). Linux-only, Xcode не вызывается.

## 1. Что измерено на текущем дереве (факты, а не проза)

| Факт | Значение | Источник |
|---|---|---|
| `Info.plist` парсится | да | `plistlib` |
| `CFBundleShortVersionString` | литерал `0.3` | plistlib |
| `CFBundleVersion` | литерал `1` | plistlib |
| остальные 9 ключей plist | 4 с `$(…)`, 4 литерала, 1 bool | сниманЕ-digest `8801d6fb…210f` |
| `MARKETING_VERSION` | `0.5` в **обоих** target-конфигах (`800…003` Debug, `800…004` Release), 0 вне их | адресный построчный читальщик pbxproj |
| `CURRENT_PROJECT_VERSION` | `1` в обоих target-конфигах, 0 вне | то же |
| `INFOPLIST_FILE` / `GENERATE_INFOPLIST_FILE=NO` | 2/2 в target-конфигах | то же |
| `ENABLE_HARDENED_RUNTIME` | 0 блоков (deliberately deferred) | то же |
| shared scheme | 0 файлов; путь `Exolon.xcodeproj/xcshareddata/xcschemes/Exolon.xcscheme` отсутствует | путь-классификатор shared/user |
| native target / test target | 1 / 0 (`500000000000000000000001` Exolon, `Exolon.app`, `com.apple.product-type.application`) | читальщик pbxproj |
| датированных отчётов в `engineering/reports/` | 2; blob'ы совпадают с HEAD и с pin-коммитами `bcacf30` / `7c1068e` | sha1 blob id + `git rev-parse` |
| `shared_xcschemes` в `v3_measurements.py` | пин `0`, извлечён через `ast` (AnnAssign), не grep | AST |
| runbook `engineering/runbooks/macos-probe.sh` | 2 устаревших EXPECTED-утверждения: «no shared scheme» (стр. 64) и «CFBundleShortVersionString=0.3» (стр. 86); шага archive нет | детектор по EXPECTED-строкам |

Главная содержательная находка: **лаг P1-11 наполовину уже закрыт в pbxproj** — `MARKETING_VERSION = 0.5`
и `CURRENT_PROJECT_VERSION = 1` лежат в нужных блоках. Красные только plist-литералы, схема, записи
о deferred/cutover и нацеливание runbook. То есть правка `Info.plist` → подстановки меняет собираемую
версию с `0.3` на `0.5`; это видимое изменение поведения, а не косметика.

## 2. Репетиция «после фикса» (главный результат)

Через `cp -a` в `/tmp/p11fix` (product-дерево не трогалось) применён плановый фикс целиком:
plist → подстановки, написан shared scheme по канону Xcode, runbook пере-нацелен, в `requirements.md`
записаны cutover и deferral. Результат:

* `release_layer_check.draft.py --root /tmp/p11fix` → **exit 0, `RESULT: RELEASE_LAYER_READY`**, 0 красных AC, 26/26 контролей.
* `v3_measurements.py --root /tmp/p11fix` → **exit 1**: `НЕСОВПАДЕНИЯ: {"shared_xcschemes": [0, 1]}` — landmine подтверждён эмпирически.

Анти-landmine-проверки (обе — на scratch-копиях):

1. «Починить v3 удалением схемы»: v3 снова зелёный (`ALL_V3_MEASUREMENTS_MATCH_REPORT`), но верификатор
   даёт **exit 1, red_ac=10**, в т.ч. `shared_scheme_count = 0 RED ожидалось 1`. Запрещённый ремонт краснеет.
2. «Фикс без записи о владении cutover / без записи о deferred»: **exit 1, red_ac=2** —
   `v3_shared_scheme_cutover_owned = 0` и `hardened_deferral_recorded = 0`. Причём `deferral_record_ignores_brief_echo`
   доказывает, что автогенерённый `brief.md` (в нём уже есть фраза «hardened runtime») запись не засчитывает,
   и что ссылка на `shared_xcschemes` в самом этом верификаторе (он в `evidence/`) тоже не засчитывается.

## 3. Три дефекта, которые нашлись именно потому, что верификатор самопроверяемый

1. **Общий стэк массивов в читальщике pbxproj.** Два `XCConfigurationList` с одноимённым массивом
   `buildConfigurations` слились в один список → «target-конфиги» = все 4 блока, и контроль
   `marketing_moves_between_blocks` не переворачивался. починено: массив хранится per-object.
2. **Выведенное имя проекта вместо литерала.** `project_name` брался из `glob("*.xcodeproj")` **с суффиксом**,
   и синтетика «после фикса» строила `Container:Exolon.xcodeproj.xcodeproj` — самосогласованно зелёный
   мусор. На репетиции это всплыло как `scheme_buildable_refs_bad_container = 5`. починено: пин
   `EXPECTED["project_name"] = "Exolon"` литеральный, AC `project_name`/`xcodeproj_dir_count` сверяют
   вывод с реальностью, а контроль `container_pin_is_literal_not_derived` обязан краснить удвоенный суффикс.
3. **Контроли, привязанные к текущему состоянию.** `deferral_record_ignores_brief_echo`,
   `absent_scheme_is_red`, `runbook_stale_flips` изначально утверждали «сейчас красным быть» — на
   починенном дереве они ломались сами. починено: каждый стал инверсией входа (мутация ctx), а не снимком.

## 4. Решение по landmine (что именно пинит верификатор)

`v3_pin_shared_xcschemes = 0` — пин **остаётся** 0: закоммиченный измеритель аудита фиксирует состояние
аудированного коммита и не должен редактироваться задним числом. Поэтому после добавления схемы v3
краснеет намеренно, и AC `v3_shared_scheme_cutover_owned` требует, чтобы это владение было записано в
плановом документе change-пакета (`requirements.md`/`architecture.md`/`tasks.md`/`test-plan.md`/
`release.md`/`rollback.md`/`change-spec.yaml`; `brief.md` и `evidence/` исключены). Одновременно
`shared_scheme_count = 1` закрывает дверь в «удали схему и всё починится».

## 5. Полный прогон на ТЕКУЩЕМ дереве (дословно)

Команда: `python3 engineering/changes/20260921-close-audit-finding-p1-11-release-layer-for-the-2e7698/evidence/release_layer_check.draft.py --root .`
Код возврата: **1** (ожидаемо: 15 красных AC при 26/26 зелёных контролей).

```text
root=/home/pall/projects/exolon head=d4c7a58 branch=codex/release-layer-p1-11-20260921
pbxproj blocks parsed=620 (headers=24 + single-line=596), XCBuildConfiguration=4, target configs={'800000000000000000000003': 'Debug', '800000000000000000000004': 'Release'}, unbalanced=[]
plist non-version digest=8801d6fb59cb69443ac24775101583ecc48ca6cbd3280c035bd3bb7bdc87210f
project_name                               = 'Exolon'
xcodeproj_dir_count                        = 1
plist_parses                               = 1
plist_key_count                            = 11
plist_version_keys_present                 = 2
plist_version_keys_substituted             = 0   RED ожидалось 2
plist_version_keys_literal                 = 2   RED ожидалось 0
plist_nonversion_untouched                 = 1
pbxproj_parses                             = 1
native_target_count                        = 1
test_target_count                          = 0
target_config_names                        = {'800000000000000000000003': 'Debug', '800000000000000000000004': 'Release'}
marketing_version_in_target_configs        = 2
marketing_version_value                    = '0.5'
marketing_version_outside_target_configs   = 0
project_version_in_target_configs          = 2
project_version_value                      = '1'
project_version_outside_target_configs     = 0
infoplist_file_setting_in_target_configs   = 2
generate_infoplist_off_in_target_configs   = 2
hardened_runtime_key_count                 = 0
hardened_deferral_recorded                 = 0   RED ожидалось 1
shared_scheme_count                        = 0   RED ожидалось 1
shared_scheme_path_exact                   = 0   RED ожидалось 1
user_scheme_count                          = 0
scheme_xml_parses                          = 0   RED ожидалось 1
scheme_blueprint_is_native_target          = 0   RED ожидалось 1
scheme_blueprint_guid_is_exolon            = 0   RED ожидалось 1
scheme_actions_required                    = 0   RED ожидалось 4
scheme_build_entry_flags_yes               = 0   RED ожидалось 5
scheme_build_for_archiving_yes             = 0   RED ожидалось 1
scheme_buildable_refs_total                = 0   RED ожидалось 5
scheme_buildable_refs_missing_attrs        = 0
scheme_buildable_refs_not_primary          = 0
scheme_buildable_refs_bad_container        = 0
scheme_buildable_refs_bad_name             = 0
scheme_runnable_is_application             = 0   RED ожидалось 1
scheme_dangling_test_refs                  = 0
reports_dated_count                        = 2
reports_blob_mismatches                    = 0
v3_pin_shared_xcschemes                    = 0
v3_shared_scheme_cutover_owned             = 1
runbook_stale_gap_claims                   = 2   RED ожидалось 0
runbook_archive_step_present               = 0   RED ожидалось 1
runbook stale claims: ['no shared scheme', 'CFBundleShortVersionString\\s*=\\s*0\\.3']
schemes: shared=[] user=[]
controls:
  OK  plist_rejects_truncated
  OK  substitution_probe_flips_on_literal
  OK  untouched_guard_flips_on_unrelated_edit
  OK  reader_balance_detects_unclosed
  OK  reader_target_cfg_list_derived
  OK  marketing_moves_between_blocks
  OK  marketing_delete_flips_count
  OK  marketing_value_is_typed
  OK  hardened_key_mutation_detected
  OK  deferral_record_ignores_brief_echo
  OK  user_scheme_not_shared
  OK  synthetic_scheme_can_be_green
  OK  bogus_blueprint_flips
  OK  missing_canon_attr_flips
  OK  wrong_container_flips
  OK  archiving_no_flips
  OK  dangling_test_flips
  OK  scheme_garbage_rejected
  OK  container_pin_is_literal_not_derived
  OK  absent_scheme_is_red
  OK  cutover_needs_record
  OK  cutover_pin_is_ast_not_grep
  OK  runbook_stale_flips
  OK  append_only_wrong_pin_flips
  OK  append_only_worktree_edit_flips
  OK  post_fix_dry_run_is_all_green
mismatches: 15
RESULT: NOT_READY (red_ac=15 bad_controls=0)
```

## 6. Красные AC сейчас → что их снимает

| Красный AC сейчас | Снимает |
|---|---|
| `plist_version_keys_substituted` 0, `plist_version_keys_literal` 2 | (a) `$(MARKETING_VERSION)` / `$(CURRENT_PROJECT_VERSION)` вместо литералов |
| `shared_scheme_count`, `shared_scheme_path_exact`, `scheme_xml_parses`, `scheme_blueprint_is_native_target`, `scheme_blueprint_guid_is_exolon`, `scheme_actions_required`, `scheme_build_entry_flags_yes`, `scheme_build_for_archiving_yes`, `scheme_buildable_refs_total`, `scheme_runnable_is_application` (10 шт.) | (b) shared scheme `Exolon.xcodeproj/xcshareddata/xcschemes/Exolon.xcscheme` на таргет `500000000000000000000001`, продукт `Exolon.app`, контейнер `Container:Exolon.xcodeproj`, Build-запись со всеми пятью `buildFor*=YES`, `TestableReference` на несуществующий тест-таргет запрещён |
| `hardened_deferral_recorded` | (c) явная запись «ENABLE_HARDENED_RUNTIME = DELIBERATELY DEFERRED» в плановом документе (не в `evidence/`, не в `brief.md`) |
| `runbook_stale_gap_claims` 2, `runbook_archive_step_present` 0 | (d) пере-нацеливание `engineering/runbooks/macos-probe.sh`: ожидания «no shared scheme» и «CFBundleShortVersionString=0.3» снимает, появляется archive-шаг той же схемой |

Зелёные AC, которые фикс обязан НЕ сломать: `plist_nonversion_untouched` (digest остальных ключей),
`marketing_version_*`, `project_version_*`, `infoplist_file_setting_in_target_configs`,
`generate_infoplist_off_in_target_configs`, `hardened_runtime_key_count = 0`, `test_target_count = 0`,
`reports_blob_mismatches = 0` (датированные отчёты не переписываются), `v3_pin_shared_xcschemes = 0`
(закоммиченный измеритель аудита не правится задним числом).

## 7. Проверки, которые были выполнены

* `ruff check` на draft-файл: `All checks passed!`
* `python3 -m py_compile`: OK.
* Продуктовое дерево не изменено: `git diff --stat -- Exolon Exolon.xcodeproj engineering/runbooks` пуст;
  `git status --porcelain` = только untracked каталог change-пакета.
* Прогон на трёх scratch-деревьях (`/tmp/p11fix`, `/tmp/p11noscheme`, `/tmp/p11norecord`) — коды 0, 1, 1.
* Авто-определение корня репо без `--root` (запуск из `evidence/`): тот же результат.
* `--json`: валидный JSON, `mismatches=15`, `controls=26`, `ok=false` (счётчики совпадают с текстовым режимом).
* Размер черновика: 892 строки, 44 бинарных AC, 26 контролей.

## 8. Ограничения черновика (что должно быть решено на этапе имплементации)

1. `scheme_buildable_refs_total = 5` — пин под каноническую схему с Build/Test-MacroExpansion/Launch/Profile/Archive.
   Если Xcode 15+ сгенерирует другую форму (например без MacroExpansion), пин надо синхронно поменять
   в `EXPECTED` и в комментарии — это осознанный human gate, а не «починить под факт».
2. `reports_*` пинят blob'ы `bcacf30`/`7c1068e`. Если владелец решит дописать отчёт (append-only новым
   файлом с новой датой) — AC `reports_dated_count`/пины обновляются в том же коммите, что и новый отчёт.
3. `plist_key_count = 11` и digest защищают от «заодно поправим LSMinimumSystemVersion»; если легитимно
   понадобится правка ключа — это отдельный change, digest пересчитывается здесь.
4. Верификатор ничего не пишет и не вызывает `xcodebuild`/`plutil`: вся семантика подстановок
   (`$(MARKETING_VERSION)` → `CFBundleShortVersionString`) остаётся зоной macOS-проуника §C; Linux-доказательство
   ограничено тем, что источник истины один и он в build settings.
5. Формат вывода (одна строка на AC + `controls:` + `RESULT:`) и коды возврата повторяют
   `v3_measurements.py`, поэтому его можно вшивать в `grok_verify --mode pr` без нового парсера.

## 9. Корректура репетиции тем же прогоном (2026-09-21, после имплементации)

Три утверждения §1–§8 оказались неверны — их опроверг сам инструмент, когда стал закоммиченным:

1. §6/`GOOD_SCHEME`: `ReferencedContainer` пинился формой `Container:Exolon.xcodeproj`. Xcode пишет
   строчную `container:`; поскольку все синтетики строились тем же хелпером, зелёными были и
   мусорные значения (тот же класс ошибки, что и `Exolon.xcodeproj.xcodeproj` из §3.2). Финал:
   пин строчной формы + контроль `container_prefix_casing_rejected`, обязанный краснить заглавную.
2. §5/`scheme_buildable_refs_total = 5`: лишняя ссылка появилась из неканонической вложенной
   `BuildActionEntries` внутри `ArchiveAction`. Xcode своей ссылки в ArchiveAction не пишет —
   финальный пин `4`, и ровно четыре `BuildableReference` в файле схемы.
3. §7: «26 контролей / 15 красных AC при rc=1» — снимок пред-фиксного дерева. Финал: **48 AC**
   (добавлены `target_cfg_symmetric`, `hardened_symmetric`, `scheme_archive_build_configuration`,
   `scheme_launch_build_configuration`) и **29 контролей**; контроль `post_fix_dry_run_is_all_green`
   удалён как после имплементации превращающийся в сравнение дерева с самим собой, вместо него
   `undo_fix_is_red` (четыре независимых отката → свои красные AC, полный откат → ровно объединение).

На текущем (починенном) дереве: `release_layer_check.py --root .` → `RESULT: RELEASE_LAYER_READY`,
rc=0, red_ac=0, bad_controls=0; `v3_measurements.py` → rc=1 c единственным
`НЕСОВПАДЕНИЯ: {"shared_xcschemes": [0, 1]}` — landmine из §2 подтверждён на продуктивном дереве и
принадлежит этому пакету (`architecture.md` §Владельчество landmine, AC-008).
