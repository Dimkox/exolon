# Test plan — P1-11 release layer

Главный автоматический артефакт — закоммиченный самопроверяющийся верификатор
`evidence/release_layer_check.py` (stdlib-only, Linux, ничего не пишет, git только читает):
48 бинарных AC-строк и 29 контролей; rc=0 ⇔ «все AC совпали с пост-фиксным EXPECTED **и** каждый
контроль перевернулся». Формат и коды возврата повторяют `v3_measurements.py`, поэтому инструмент
можно вшивать в следующий прогон аудита без нового парсера.

## Risk-based scenarios

| Priority | Scenario | Evidence |
| --- | --- | --- |
| P0 | Версия бандла перестала иметь второй источник: plist отдаёт подстановки, литералов нет, остальные 9 ключей не тронуты (digest) | AC-001: `plist_version_keys_*`, `plist_nonversion_untouched`; контроль `untouched_guard_flips_on_unrelated_edit` |
| P0 | Подстановка ссылается на настройки именно target-конфигов (project-level `grep -c` такого не доказывает) | AC-002: `*_in_target_configs=2`, `*_outside_target_configs=0`; контроль `marketing_moves_between_blocks` |
| P0 | Неразвёрнутый placeholder не может уехать в релиз | macOS: `macos-probe.sh` §C `plist_unexpanded_placeholders=0`; Linux: AC-002 + AC-010 |
| P0 | Общая схема с Archive@Release существует, одна, и адресует реальный уникальный таргет | AC-003/AC-004; контроли `user_scheme_not_shared`, `bogus_blueprint_flips`, `archiving_no_flips`, `archive_config_flips`, `container_prefix_casing_rejected` |
| P1 | «Починить v3, удалив схему» красится, а не молча проходит | AC-003 `shared_scheme_count=1` + AC-008 `v3_shared_scheme_cutover_owned=1`; анти-landmine прогон см. `analysis-verifier-draft.md` §2 |
| P1 | Тихий перевод Run/Debug на Release или тест-таргета в схеме не проходит | `launch_config_flips`, `dangling_test_flips`, `test_target_count=0`, `scheme_dangling_test_refs=0` |
| P1 | Отсрочка hardening не может быть «забыта»: без записи в plan-документах вердикт красный | AC-007 `hardened_deferral_recorded=1`; контроль `deferral_record_ignores_brief_echo` (автоген `brief.md` и `evidence/` намеренно исключены из планового текста) |
| P1 | Датированные доказательства не переписываются | AC-009 `reports_blob_mismatches=0` (worktree==HEAD==pin); контроли `append_only_wrong_pin_flips`, `append_only_worktree_edit_flips` |
| P1 | Зелёный вердикт causally привязан к фиксу | контроль `undo_fix_is_red`: четыре независимых отката (plist / scheme / runbook / записи) и точное объединение их красных множеств |
| P2 | Runbook не врёт про «нет схемы» после фикса | AC-006 `runbook_stale_gap_claims=0`, `runbook_archive_step_present=1`; контроль `runbook_stale_flips` |

## Automated checks

- Unit: в продукте 0 тест-таргетов и нет Python/Swift тестового контура для этого слоя
  (`tests/`, `requirements.txt` в дереве отсутствуют); проверка поведения — сам верификатор,
  его мутационные контроли живут внутри него и обязаны переворачиваться.
- Integration: `python3 evidence/release_layer_check.py --root .` (rc=0) плюс контрольный
  `python3 engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/v3_measurements.py`
  (ожидаемый rc=1 на `shared_xcschemes` — cutover, не регрессия).
- Contract: контракт формата — «одна строка на AC + `controls:` + `RESULT:` + rc», как у
  `v3_measurements.py`; JSON-режим (`--json`) даёт те же счётчики.
- E2E: только macOS-контур (§C/§B2 probe + handout-v2), на Linux не эмулируется и не засчитывается (AC-010).
- Static analysis: `python3 scripts/grok_verify.py --mode pr` (git-diff-check, secret-scan,
  change-spec, workflow-artifacts, ruff/bandit над `scripts/`, source-stability). Отдельно
  `ruff check` + `python3 -m py_compile` на файле верификатора: **состав проверок гейта его не
  покрывает** — `QUALITY_PY_PATHS` в `.grok-stack/adaptive_grok/verification.py` не включает
  `engineering/`, и `ruff.toml`/`bandit.yaml` исключают `engineering` целиком.
  Поэтому `bandit -c bandit.yaml` на этом файле даёт «No issues» ложно (Total lines of code: 0),
  а без конфига поднимает B404/B603/B607 (субпроцесс `git` только на чтение), B405/B314
  (`xml.etree` по **своему** файлу схемы из дерева, не по сетевому XML) и B324 (SHA1 как
  идентификатор git-blob, не как криптография). Всё принято осознанно; линтер-гейт для
  `evidence/**` — отдельная находка стека, не этот change.

## Manual checks (машины владельца, один прогон)

1. `xcodebuild -project Exolon.xcodeproj -target Exolon -configuration Debug build` → первый в истории
   проекта успешный type-check (это же M-01′).
2. `plutil -extract CFBundleShortVersionString raw build/Debug/Exolon.app/Contents/Info.plist` → `0.5`
   (не `0.3`, не `$(MARKETING_VERSION)`); `CFBundleVersion` → `1`; `grep -c '$(' …` → 0.
3. `xcodebuild -project Exolon.xcodeproj -scheme Exolon -showdestinations` → rc=0 со списком
   destinations (доказывает, что загрузчик схем разобрал файл).
4. `WITH_ARCHIVE=1 engineering/runbooks/macos-probe.sh --out /tmp/probe.txt` →
   `archive_rc` и `archive_path_present`; отказ допустим только по подписи, не по «нет схемы».
5. `codesign -d --verbose=4 build/Debug/Exolon.app | grep -o 'flags=0x[0-9a-f]*(.*)'` → зафиксировать
   фактическое отсутствие токена `runtime` (это и есть доказательство корректности отсрочки, а не пропуск).
6. Один ручной прогон игры после смены plist (About/титул, HighScore и checkpoint в `defaults`
   `com.exolon.remake` должны пережить пересборку).
