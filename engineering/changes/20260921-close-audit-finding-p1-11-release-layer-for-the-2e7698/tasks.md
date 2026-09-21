# Tasks — P1-11 release layer: один источник версии, shared scheme с Archive, пере-нацеленный probe, закоммиченный верификатор

Владелец записи: один (main agent как write owner маршрута `2e76988444b0`, `write_agent: null`).
Аналитическая волна (`repo_explorer`, `architect`, `docs_researcher`) уже лежит в `evidence/`.

- [x] Заморозить контракты и ожидаемое поведение: типизированный [`change-spec.yaml`](change-spec.yaml)
      (AC-001…AC-010, INV-001…INV-004, FORBID-001…FORBID-006) + `requirements.md` с таблицей измерений.
- [x] Карактеризующий тест до поведения продукта: `evidence/release_layer_check.py` написан и запущен
      на пред-фиксном дереве (rc=1, 15 красных AC) — фикс фиксируется только тем, что тот же инструмент
      становится зелёным, а контроль `undo_fix_is_red` требует, чтобы каждый из четырёх откатов плана
      снова красил свои AC.
- [x] Минимальный вертикальный срез:
      `Exolon/Resources/Info.plist` (2 строки: литералы → `$(MARKETING_VERSION)` / `$(CURRENT_PROJECT_VERSION)`),
      `Exolon.xcodeproj/xcshareddata/xcschemes/Exolon.xcscheme` (новый файл, канон Xcode, 4 `BuildableReference`,
      `ArchiveAction buildConfiguration = "Release"`),
      `engineering/runbooks/macos-probe.sh` (§A дискриминатор shared-vs-generated вместо подстроки `-list`,
      §C сравнение с `xcodebuild -showBuildSettings` вместо grep-литерала `0.5`, §B2 `-scheme`/archive,
      `codesign -d --verbose=4` вместо `--entitlements` для hardened runtime).
      `project.pbxproj` не тронут: `ENABLE_HARDENED_RUNTIME` отложен (см. `release.md`).
- [x] Качество маршрута: `python3 scripts/grok_verify.py --mode pr` (git-diff-check, secret-scan,
      change-spec, workflow-artifacts, ruff/bandit, source-stability) + прогон верификатора
      `python3 evidence/release_layer_check.py --root .` (rc=0) и контрольный прогон
      `v3_measurements.py` (ожидаемый rc=1 как cutover-сигнал, владение записано в `architecture.md`).
- [ ] Независимые ревью по маршруту: `security_reviewer`, `release_reviewer` → отчёты в `evidence/`,
      receipts `security_review` / `release_review`.
- [ ] Связать доказательства с финальным отпечатком дерева и закрыть PR (Merge — только после
      внешнего App-owned Trust CI на точном head; локальные receipts властью над merge не обладают).

## Что остаётся после этого change (не «забыто», а отдельно)

1. Клауза «подпись» P1-11: `ENABLE_HARDENED_RUNTIME` + `.entitlements` + реальный signing identity —
   отдельным change сразу после зелёного M-01′, с контролем `codesign … flags=…(runtime)` и одним
   ручным прогоном (gamepad/HUD/audio).
2. `LSMinimumSystemVersion` → `$(MACOSX_DEPLOYMENT_TARGET)`, иконка приложения,
   `LSApplicationCategoryType`, copyright — релизная оболочка следующим change.
3. macOS-подтверждение (`evidence/perfile/macos-validation-handout-v2.md`): первый в истории проекта
   type-check, подстановка версий в собранном бандле, разрешаемость `-scheme Exolon`, attempt archive.
4. Следующий прогон аудита обязан пересобрать строку P1-11 в статус «частично закрыта»
   (identities+scheme закрыты, подпись открыта) — датированный отчёт задним числом не правится (AC-009).
