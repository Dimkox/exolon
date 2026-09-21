# Release plan — P1-11 release layer (идентичность версии, shared scheme, отсрочка подписи)

## Deployment

Продукта это изменение не деплоит: релизный **слой** дерева становится пригодным для публикации,
самого артефакта (`.xcarchive`, notarization, Release на GitHub) этот change не создаёт.
Порядок выкладки:

1. PR этого маршрута → внешний App-owned Trust CI на точном head (`adaptive-trust-ci/verified@<policy-sha12>`)
   → мерж только после зелёного check и всех нужных подписанных approvals.
2. Одна macOS-сессия владельца: `engineering/runbooks/macos-probe.sh --out …` c `WITH_ARCHIVE=1`
   (протокол — `evidence/perfile/macos-validation-handout-v2.md`). Этот прогон закрывает и M-01′
   (первый type-check), и доказательство подстановки версии, и разрешаемость `-scheme Exolon`.
3. Только после зелёного M-01′ — отдельный change на клаузу «подпись» (см. §Deferred).

## Feature flags / staged rollout

Флагов нет. Изменение плоскотекстовое и обратимое одной ревизией. Видимое потребителю отличие ровно
одно: About/Finder/`mdls` начинают показывать `0.5` вместо `0.3` (это и был лаг P1-11).
Канарейка — первая же macOS-сборка: `version_single_source=MATCH` и
`plist_unexpanded_placeholders=0` в выводе probe.

## Metrics and alerts

- `release_layer_check.py` rc (0 = релизный слой соответствует EXPECTED и все контроли перевернулись);
  запускается в следующем прогоне аудита как обычный измеритель.
- `v3_measurements.py` rc: после merge обязан быть **1** на ключе `shared_xcschemes` (0 → 1).
  Это ожидаемый cutover-сигнал: датированный пин фиксирует состояние аудированного коммита и
  не правится задним числом. Владение переходом — этот пакет; «чинить» его удалением схемы
  запрещено и красится самим `release_layer_check.py`.
- macOS: `version_single_source`, `build_version_single_source`, `plist_unexpanded_placeholders`,
  `showdestinations_rc`, `archive_rc`, `codesign_flags`.

## Go/no-go criteria

Go (все четыре проверяемы на Linux до merge):

- `python3 evidence/release_layer_check.py --root .` → rc=0, `RESULT: RELEASE_LAYER_READY`,
  0 красных AC, 29/29 контролей OK;
- `python3 scripts/grok_verify.py --mode pr` → PASS на этом же отпечатке;
- `git diff --name-only 403eb13..HEAD -- Exolon Exolon.xcodeproj engineering Exolon/Resources` →
  ровно три продукта-пути: `Exolon/Resources/Info.plist`,
  `Exolon.xcodeproj/xcshareddata/xcschemes/Exolon.xcscheme`, `engineering/runbooks/macos-probe.sh`
  (`project.pbxproj` в списке быть не должно: см. §Deferred);
- ревью `security_reviewer` и `release_reviewer` по фактическому диффу, receipts привязаны к финальному отпечатку.

No-go / откат к переработке: любой из первых двух пунктов красный; либо в диффе появился
четвёртый продукт-файл без отдельного approval; либо владелец отказывает в gate `scope_and_design_approval`
на отсрочке hardening (тогда (b) возвращается в этот change: ровно 2 таб-индентированные строки
`ENABLE_HARDENED_RUNTIME = YES;` в **обоих** target-конфигах, AC-008 симметрии обязан остаться зелёным,
и нужен отдельный macOS-прогон с `codesign`-флагом `runtime`).

## Deferred (записано, а не пропущено)

- `ENABLE_HARDENED_RUNTIME` — не включён ни в один конфиг. Причина: при ad-hoc
  `CODE_SIGN_IDENTITY = "-"` / `CODE_SIGN_STYLE = Manual` / пустом `DEVELOPMENT_TEAM` флаг не меняет
  исход Gatekeeper и недоступность нотаризации, но включает рантайм-принуждение (library validation,
  запрет unsigned executable memory, ограничения отладки) для бинарника, чья первая успешная сборка
  ещё не доказана. Отсюда и требование атрибуции: не смешивать с изменением, которое впервые
  устанавливает собираемость.
  Следующий шаг: change сразу после зелёного M-01′; контроль
  `codesign -d --verbose=4 "$APP" 2>&1 | grep -o 'flags=0x[0-9a-f]*(.*)'` → токен `runtime`,
  негативный контроль — дамп до-фиксной сборки токена не содержит; отдельное решение — нужен ли
  `.entitlements` (`com.apple.security.get-task-allow` для отладки Debug).
- Подписные материалы (Developer ID, сертификаты, `.entitlements`, нотаризация, MAS) — вне периметра
  репозитория навсегда: AGENTS.md запрещает агенту создавать или использовать человеческие ключи
  approvals и читать подписные секреты.
- `LSMinimumSystemVersion` → `$(MACOSX_DEPLOYMENT_TARGET)`, иконка приложения,
  `LSApplicationCategoryType`, `NSHumanReadableCopyright`, миграция на `GENERATE_INFOPLIST_FILE = YES`,
  XCTest-таргет, `objectVersion`/upgrade проекта — каждый своим change (аргументы:
  `evidence/analysis-architect.md` §1.D и §4).
- Номер версии (0.5 vs 0.3) этим change **не** назначается: удалён только двойной источник истины.
