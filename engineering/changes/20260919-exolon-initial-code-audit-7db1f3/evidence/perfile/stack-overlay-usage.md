# Стек-оверлей: что исполняется, а что мёртвый груз

Объект: установленный в `<repo>` Adaptive Grok Build Pro (HEAD `52795d1`).
Метод: только чтение дерева + запуск read-only веток CLI + перезагенерация evidence-скриптов в
песочнице `/tmp/lane-stack/`. `grok_verify` не запускался (передан другому владельцу).

Инвентарь (измерено):

| Компонент | Объём |
|---|---|
| `.grok-stack/adaptive_grok/` | 32 модуля, 21 071 LOC |
| `factory/` (продукт стека, не exolon) | 74 py, src 25 413 + tests 13 368 LOC |
| `scripts/grok_*.py` | 13 |
| `.grok/agents/` | 21 `.md` (273 строки) + 21 `.toml` |
| `.agents/skills/` | 16 каталогов (15 из `managed.json` + неуправляемый `seo-landing`), 28 `.md`, 1 659 строк |
| корневые hook-шимы | 9 × 34 строки |
| **продукт `Exolon/` + `.xcodeproj`** | 300 файлов, **4 227 Swift LOC**, 125 TMX, 282 ресурса, 1,8 МБ |

Пропорция: машинно проверяемого кода стека в этом дереве ~10× больше, чем кода продукта, — и
ни одна строка продукта не проверяется ни одной проверкой гейта.

## Итог

- Из **13** скриптов следы вывода в дереве оставили **8**; **5** (`grok_architecture`,
  `grok_governance`, `grok_artifacts`, `grok_history`, `grok_deploy`) не давали вывода никогда — они
  упираются в отсутствие конфигурации: нет `architecture/`, `governance/`,
  `workflow/manifest.json`, historical-снапшота — и в `write_agent: null` / stale-evidence.
  Измерено живым запуском, не чтением.
- За ними — **14 154 LOC (67,2 % стека)** недостижимы в этом дереве:
  `architecture.py` 3497 + `architecture_fitness.py` 2759 + `architecture_diff.py` 1218 +
  `architecture_diagrams.py` 293 + `queue_provenance.py` 1088 + `governance.py` 2940 +
  `workflow_artifacts.py` 1768 + `history.py` 491 + `deploy.py` 100. Ещё 1 070 LOC
  (`demo.py`+`demo_http.py` 505, `python_test_runner.py` 308, `protected_write.py` 257) не имеют ни
  импортёров, ни достижимого места вызова.
- **«RESULT: PASS» в `state.json` («10 checks, 0 fail») — это 10 проверок, из которых 5 вакуумны
  (ноль объектов проверки или только whitespace), 4 проверяют стек и `factory`, а не продукт, и 1 —
  самоконтроль отпечатка. Покрытие Swift-продукта — 0 %.** Три проверки помечены `SKIP … not
  configured`, ещё ~10 никогда не появляются в отчёте даже как SKIP (молча инертны).
- Агенты: **0 из 21** достижимы в CLI, который реально ведёт этот репозиторий; скиллы: **16 из 16**
  живы. Обязательное правило «use only `allowed_agents`» буквально невыполнимо.
- Хуки: **ни один из 9 типов не сработал здесь ни разу** — ни одного артефакта hook-слоя. Контракт
  (роутинг, stop-gate, защищённая запись, circuit breaker) в этом дереве advisory.
- Линт-скоуп вырезает `engineering/` полностью; **измеренная цена**: `bandit -c bandit.yaml -r
  engineering` сканирует **0 LOC** и возвращает exit 0, а сгенерированный evidence-артефакт
  `linux-static-audit.md` **уже не совпадает** со своим генератором (207 строк / 10 316 Б против
  перегенерированных 208 / 10 317 Б) — расхождение внёс коммит `52795d1`, который правил
  *машинно-сгенерированный* файл, чтобы удовлетворить гейт `git-diff-check`. Ни одна проверка этого
  не детектит.

## Что реально исполняется

Артефакты в `.grok-stack/runtime/` (всё untracked; `.gitignore` в репозитории отсутствует):

| Артефакт | Создан | Состояние на HEAD |
|---|---|---|
| `active-route.json` `7db1f3f0b126` | 11:42:22 (upd. 2026-09-20T01:46:42) | `intent=review`, `risk=low`, `write_agent: null` |
| `routes/1f980b5df386.json` | 11:40:50 | сирота: `status=routed`, `change_id: null`, intent `release`, human_gates ×2 — не продвигался |
| `routes/d6e0aac4aae9.json` | 11:41:05 | сирота: `status=routed`, `change_id: null`, intent `bugfix`, write `frontend_implementer` — не продвигался |
| `active-change.json` | — | пакет `…7db1f3` |
| `approvals.json` | 11:50:58 / 11:51:17 | **оба grant просрочены** (12:20:58 / 12:21:17) и привязаны к `git_head 403eb13` (сейчас `52795d1`) |
| `receipts/7db1f3f0b126/{verification,code_review,test_review}.json` | 01:51 / 03:07 | 3 kinds из 7; `security_review`, `data_review`, `release_review`, `bitrix_review`, `deploy` — ни одного |

Роуты записаны по `session_id: "exolon-initial-audit-20260919"` — **у всех трёх одинаковому**,
человечески читаемому. Хук `_lib.session_id()` вернул бы `session_id` из payload CLI (UUID) либо
`manual`; все три роута старше первой Grok-сессии в этом репозитории (11:46). Вывод: маршрутизацию
вызвали вручную через `grok_route.py --session …`, а не `UserPromptSubmit`.

Скрипты (13). «Вывод в дереве» = оставленный файл; «живой запуск» = мой read-only прогон сегодня:

| Скрипт | Исполнялся здесь? | Мера / причина отсутствия вывода |
|---|---|---|
| `grok_route` | **да** | 3 файла в `routes/` (2 сироты) |
| `grok_change` | **да** | `active-change.json` + 2 пакета; набор из 10 файлов пакета ровно = `.grok-stack/templates/change/`; `state.json` — 6 переходов draft→ready |
| `grok_verify` | **да** | `receipts/…/verification.json`, 13 проверок (10 pass / 3 skip / 0 fail), `RESULT: PASS` |
| `grok_review` | **да** | `code_review.json`, `test_review.json` (оба `pass`, оба stale) |
| `grok_approve` | **да** | 2 delegated grant в `approvals.json`, оба истекли |
| `grok_spec` | **да** (read-only) | валидируется, `ok: true`, digest `be6e62f8…` = `spec_digest` в receipt → CLI и гейт читали один документ |
| `grok_status` | вывод есть, артефакта нет | 2 433 Б stdout; `agents: {'active': {}, 'history': []}`; 5 evidence gaps |
| `grok_doctor` | вывод есть, артефакта нет | exit 0, ~60 строк PASS; `PASS tool:grok: grok 1.0.38` |
| `grok_architecture` | **никогда** | exit 2, `{"code":"io","error":"… No such file or directory: 'architecture'"}` — нет `architecture/system.yaml` |
| `grok_governance` | **никогда** | exit 2, `governance authority topology is unavailable: … 'governance'` — нет `governance/` |
| `grok_artifacts` | **никогда** | exit 1, `{"code":"route","error":"active route has no valid writer"}` — двойной блок: нет `workflow/manifest.json` **и** `write_agent: null` |
| `grok_history` | **никогда** | exit 2, `input: object field limit exceeded` — нужного historical-снапшота в дереве нет ни одного |
| `grok_deploy` | **никогда** | exit 1: `missing or stale local evidence: verification…; code_review…; test_review…`; кроме того, файла `VERSION` нет → `_version()` вернул бы `0.0.0` |

Молча инертные подмодули (нет ни одного импортёра из `scripts/`, `.grok/hooks/`, корневых шимов):
`demo_http.py` (188, импортёров **ноль**), `demo.py` (317, импортируется только `demo_http`),
`protected_write.py` (257, импортёров **ноль**), `manifest.py` (272, только `doctor`, и тот сам
печатает `INFO manifest: not generated yet`). `python_test_runner.py` (308) импортируется
`verification.py`, но вызывается только под веткой `has_unittest_files`, которая здесь `False`
(нет корневого `tests/`) → **никогда не исполняется**.

## SKIP-поверхность гейта

Из записанного receipt (13 записей): `pass` = git-diff-check, change-spec, secret-scan,
contract-structure, sql-safety, ruff, bandit, factory-unit, factory-postgres-exit,
source-stability; `skip` = architecture, governance, workflow-artifacts; `fail` = ∅.

`RESULT: PASS` печатает `scripts/grok_verify.py:29` из `report['status']`, а статус считается по
`failures = [r for r in results if r.status == 'fail']` (`verification.py:1133`) и
`overall = "fail" if counts["fail"] else "pass"` (`verification.py:1060`).
**SKIP не может завалить гейт — по построению.**

Явные SKIP и их причина (конфиг, а не продукт):

| Проверка | Условие срабатывания | Здесь |
|---|---|---|
| `architecture` | `active_architecture_binding()` — нужен `architecture/system.yaml` + adoption-маркер (`receipts.py:208-240`) | каталога нет → `skip`, `{"configured": false}` |
| `governance` | `_governance_is_configured()` — нужен каталог `governance/` (`receipts.py:342`) **и** успешно пройденный `architecture` | нет ни того, ни другого → `skip` |
| `workflow-artifacts` | нужен `engineering/changes/<id>/workflow/manifest.json` (`verification.py:279-297`) | файла нет ни в одном из 2 пакетов → `skip` |

Молча отсутствующие (не попадают в отчёт вообще — ни pass, ни skip):

- `php-lint`, `composer-validate`, `phpunit/phpstan/phpcs/deptrac`, `bitrix-policy` — профили
  `php`/`bitrix` не запрошены и PHP-файлов нет (`php 8.3.6` в окружении установлен, пин в
  `toolchain.json` живёт зря).
- node-семейство (`_node`) — **два осиротевших роута просят профиль `frontend`**, но
  `package.json` в корне отсутствует → `return []`, ни одной строки отчёта.
- `python-unittest` + **`coverage`** — нет корневого `tests/` → вся ветка мертва; `coverage 5.x`
  установлен, `.coveragerc` с `fail_under = 74` **никогда не применялся**.
- `pilot-unittest` (нет `pilot/`), `semgrep` (нет конфига; бинарника тоже нет), `trivy-config`
  (бинарник `trivy 0.74.0` **установлен**, но `_TRIVY_FILES` ищет только корневые
  `Dockerfile/Containerfile/docker-compose*.yml`, а `factory/compose.yaml` в glob не попадает).

Что этот PASS **не** покрывает из рисков продукта:

1. **Сборка и типы Swift**: 4 227 LOC, `Exolon.xcodeproj` — нет ни `xcodebuild`, ни swiftc, ни
   SwiftLint. В `.grok-stack/**` и `scripts/**` подстрока `swift` встречается ровно один раз
   (`architecture.py:720`, список расширений для architecture-модели) — и тот путь мёртв, т.к.
   `architecture` не сконфигурирован.
2. **Данные 125 уровней и ассеты** (282 ресурса): ни одна проверка не читает `.tmx`/атрибуты —
   `contract-structure` отработал по **0** объектам, `sql-safety` — **0** находок на 55 изменённых
   файлах, в которых нет ни `.sql`, ни `.php`.
3. **Секреты**: `secret-scan` — 3 regex по 55 изменённым файлам (в основном `.md`), а не по дереву.
4. **change-spec**: `gate`-валидация требует, чтобы у каждой AC была `evidence`, и для
   `kind == "test"` проверяет **только существование пути** (`spec.py:707-717`,
   `test evidence path does not exist`). Ни суффикс, ни запускаемость не проверяются: `AC-004` и
   `AC-005` «доказаны» existence'ом отчёта `.md`, `AC-003` — существованием `linux_static_audit.py`.
   Отсюда `criterion_mapped: 8/8` и `evidence_counts.test: 9` = девять существующих путей, а не
   девять исполненных тестов.
5. **Смещение объекта проверки**: `ruff`+`bandit`+`factory-unit` (51 тест)
   +`factory-postgres-exit` (201 тест, **158,001 с** — доминирующая стоимость гейта) валидируют
   стек и `factory/`, то есть инструмент, а не exolon.
6. Текущее состояние: **все три receipt уже stale** — `validate_evidence` возвращает 5 gap'ов
   (`verification: stale…`, `code_review: stale… + spec binding stale`, `test_review: stale… +
   spec binding stale`), отпечаток `8d782be4…` → `2e3e62c5…`. Ни одного PASS, привязанного к HEAD
   `52795d1`, не существует. Причины two-fold: (а) `changed_files()` включает untracked
   (`git ls-files --others --exclude-standard`), а `_fingerprint_noise` фильтрует
   `__pycache__`/`.coverage`/`.grok-stack/runtime/`, но **не `.qwen/`** — в последнем receipt в
   `changed_files` лежит `.qwen/tmp/s-9233a5a8-…/qwen-skill-args-loop.txt`, т.е. каждый скретч-писк
   CLI сам сбрасывает гейт; (б) `.gitignore` в репозитории нет вообще.

## Агенты и скиллы

- `managed.json`: 21 агент, 15 скиллов, 9 типов хуков, 13 скриптов.
- **Агенты: 0 / 21 зарегистрировано.** CLI, ведущий этот репозиторий (Qwen Code
  `<home>/.local/lib/qwen-code`), строит реестр из `.qwen/agents` (строка `.qwen/agents` есть в
  бандле) — такого каталога нет ни в проекте (`.qwen/` содержит только `tmp/`), ни в `~/.qwen/`.
  Фактический реестр: `general-purpose`, `Explore`, `statusline-setup`, `review-agent`,
  `claude-code`, `codex` — шесть built-in/extension типов, ни одного имени из стека. Формат тоже
  не совпадает: `.grok/agents/*.md` использует frontmatter `effort`, а `.toml` c
  `sandbox_mode`/`developer_instructions` — формат Grok.
- **Скиллы: 16 / 16 доступны** CLI из `.agents/skills/` (все 15 управляемых + `seo-landing`,
  которого в `managed.json` нет, — расхождение манифеста). То есть `primary_skill:
  adaptive-delivery` и `workflow_skills` реально загружаются, а `allowed_agents` — нет.
- **Наблюдение (как постановка задачи требует зафиксировать буквально):** активный роут
  `7db1f3f0b126` предписывает `review_agents = [code_reviewer, test_reviewer]` и
  `allowed_agents = [repo_explorer, architect, docs_researcher, code_reviewer, test_reviewer]`;
  **ни одно из этих имён нельзя запустить** в driving CLI. Обязательное правило контракта
  «Use only `allowed_agents`» / «Do not spawn an agent that the active route did not select»
  (`AGENTS.md`, п. 5–9 «Mandatory entrypoint») в этом дереве буквально невыполнимо: ревью
  `code_review`/`test_review` записаны в `receipts/` вручную через `grok_review.py`, отчёты к ним
  написаны агентами вне списка. Механизм выбора агента (SubagentStart/Stop hook) тоже молчит
  (см. «Хуки»), так что нарушение ничем не детектируется.
- `grok_doctor.py` выдаёт `PASS agent:<name>.toml` × 21 — это проверка **корректности формата
  файлов**, а не достижимости: doctor подтверждаетwell-formedness мёртвой полезной нагрузки.
- Осиротевшие роутыNaming: `1f980b5df386` требует `security_reviewer` + `release_reviewer` и двух
  human gates, `d6e0aac4aae9` — `frontend_implementer`; ни один агент недоступен, ни один пакет
  изменений не заведён, статус застыл в `routed`.

## Хуки

- **Регистрации для текущего CLI нет.** `~/.qwen/settings.json` (ред. 2026-09-20 00:54) — ключей
  `hooks` **0**; проектного `.qwen/settings.json` **нет**. При этом сам механизм CLI поддерживает:
  в бандле события `SessionStart` (123 упоминания), `SessionEnd` (87), `UserPromptSubmit` (80),
  `PreToolUse` (70), `PostToolUse` (58), `SubagentStop` (49), `SubagentStart` (37), `PreCompact`
  (28), `Stop` (24) — то есть все 9 типов из `managed.json`.
- Соседний факт не в пользу «никогда не работало»: бэкап `settings.json.bak-20260915` **содержал**
  блок `hooks.SessionStart` (`qwen185-guard`), а в текущем `settings.json` его нет — то есть
  hook-механика на этом хосте была включена и later сброшена.
- Оверлей регистрирует хуки только в **Grok**-формате: `.grok/hooks.json` +
  `.grok/hooks/adaptive.json` (одинаковые 9 событий) + `.grok/config.toml` (`[features] hooks =
  true`, с комментарием «Project hooks require `/hooks-trust` in the Grok TUI» и «v2.0.4 hooks are
  fail-open»). Grok здесь установлен (`grok 1.0.38`) и **реально открывал этот репозиторий**:
  `~/.grok/sessions/%2Fhome%2Fpall%2Fprojects%2Fexolon` — 7 сущностей, 11:46–12:08 19.09, больше
  нечего. Но и под Grok хуки не исполнились — см. меру.
- **Мера инертности (5 из 5 hook-артефактов отсутствуют):** `post_tool_use.py` пишет
  `.grok-stack/runtime/last-fingerprint.json`; `pre_tool_use.py` — `tool-denials.json`;
  `pre_compact.py` — `handoff.json`; `session_end.py` — `last-session-end.json`;
  `subagent_start|stop.py` — `agent-state.json`. В `.grok-stack/runtime/` лежат **только**
  `active-change.json`, `active-route.json`, `approvals.json`, `receipts/`, `routes/`, `.gitkeep`.
  Косвенно подтверждает `grok_status`: `agents: {'active': {}, 'history': []}`.
- Что от этого становится advisory-only (по коду, а не по декларации):
  1. `UserPromptSubmit`-роутинг → контрактный «обязательный entrypoint» не навязывается; роуты
     создавали руками (см. выше), два из них брошены.
  2. `Stop`-гейт (`stop_gate.py`) — и сам по себе уже soft: в коде комментарий «Soft: report gaps
     but DO NOT block stop (was hard block → agent loop)». Даже активный, он не блокировал бы.
  3. `PreToolUse` защищённая запись (`protected_paths` из `policy.json`: `.grok-stack/**`,
     `scripts/grok_*.py`, шимы, `AGENTS.md`, `.env`, `*.pem`, `bitrix/**`) — принуждения нет;
     плюс `protected_write.py` (257 LOC) не импортируется вообще ниоткуда.
  4. Circuit breaker на повторные отказы (`tool-denials.json`, exact/objective fingerprint) — мёртв.
  5. `SubagentStart/Stop` контроль состава агентов → нарушение `allowed_agents` невидимо.
  6. `SessionStart`/`PreCompact` инъекция контекста маршрута и `handoff.json` → `START_HERE`-цикл
     не поддерживается автоматически.
  7. `PostToolUse` авто-инвалидация receipt'ов при изменении дерева → receipts протухают молча
     (что и observвано: 3 stale, а `state.json` всё ещё утверждает «PASS»).
  Остаются принудительными только то, что CLI делает сам (запрет `git push` в защищённую ветку —
  средствами хоста, не стека).

## Линт-скоуп

Три конфига, все с вырезанным `engineering`:

- `ruff.toml`: `exclude = [.git, .grok-stack/runtime, dist, packages, **engineering**, examples,
  __pycache__]`; `select = [E4, E7, E9, F]`, `ignore = [E402]` — узкий correctness-набор.
- `bandit.yaml`: `exclude_dirs: [tests, **engineering**, dist, packages, examples,
  .grok-stack/runtime]`; `skips: B101, B404, B603, B607`.
- `.coveragerc`: `source = [.grok-stack/adaptive_grok, scripts]`, `omit = [tests/*, __pycache__,
  .grok-stack/runtime/*, engineering/*]`, `fail_under = 74`.
- Плюс `QUALITY_PY_PATHS` (`verification.py:815-830`) физически не содержит `engineering/`,
  `factory/tests`, `factory/**` кроме `factory/src/adaptive_factory`, и ничего Swift.

Следствие: **747 строк evidence-генераторов** (`linux_static_audit.py` 557 + `fullaudit_measurements.py`
190) лежат вне ruff, вне bandit, вне coverage.

Измеренная цена (песочница `/tmp/lane-stack`, репозиторий не тронут):

1. **`bandit -c bandit.yaml -q -r engineering` сканирует 0 LOC и выходит 0** (`metrics._totals.loc
   = 0`), тогда как `-r scripts` даёт `loc = 833`. `exclude_dirs` срабатывает и при явной передаче
   пути — гейт показывает зелёный `bandit: pass` по несуществующему объёму.
2. **Фактический случай рассогласования генератора и артефакта**: перегенерация
   `linux_static_audit.py` даёт `linux-static-audit.md` **208 строк / 10 317 Б**, в дереве
   закоммичено **207 / 10 316 Б** (расхождение — пустая строка после 207-й);
   `linux-static-audit.json` при этом совпадает побайтово. Виновник — HEAD-коммит `52795d1`
   («docs: normalize trailing whitespace in audit markdown for **git-diff-check gate**»,
   `…/linux-static-audit.md | 1 -`): чтобы пройти whitespace-гейт, человек отредактировал
   машинно-сгенерированный evidence-файл, и генератор перестал его воспроизводить. Детектора нет:
   единственный в стеке компаратор «сгенерировано ≠ закоммичено» — `compare_generated()` для
   architecture-диаграмм, а ветка `architecture` в `SKIP`. То есть **гейт по whitespace сломал
   воспроизводимость собственного evidence-артефакта, и об этом не сообщит ни одна проверка.**
   Стоимость — подорванная доверительная цепочка: любой вывод в отчётах, сославшийся на цифры из
   этого `.md`, больше не воспроизводим «из коробки», хотя в данном случае потеря ровно одна
   пустая строка (содержательных расхождений 0).
3. Контрольный случай обязан был перевернуться — перевернулся: `fullaudit_measurements.py` сегодня
   воспроизводит `fullaudit-b01-spawn.json` **побайтово** (125 ключей, 0 расхождений,
   tally `exact 35 / void 89 / 16_above 1`) и печатает `ALL_MEASUREMENTS_MATCH_REPORT`, exit 0.
   Значит сломан не генератор, а **проза отчёта относительно артефакта** — задокументировано в
   `evidence/test-review-fullaudit-final.md` (F-07: §4/§9.4 ссылались на несуществующий
   `16_below`). Встроенный self-control генератора в гейт не заведён: `spec.py` от AC-003 требует
   лишь существования пути к `.py`, запускать его некому.
4. Что стоит *расширение* скоупа (честная оценка): под **тем же** правилом репозитория
   (`--select E4,E7,E9,F`) `engineering` + `factory/tests` дают ровно 9 × `E402`, а `E402` уже
   глобально в `ignore` → **0 находок, расширение ruff бесплатно**. А вот `bandit -r
   engineering/changes` без конфига даёт **5 находок, из них 2 × MEDIUM `B314`**
   (`xml.etree.ElementTree` на непроверенных TMX в обоих генераторах) + 2 × LOW `B405` +
   `B101`; `bandit.yaml` их не скипает → включение `engineering` в bandit **сломает гейт**, пока не
   добавлен hardening (defusedxml/`resolve_entities=False`) или осознанный `# nosec` с обоснованием.

## Предлагаемый трим

Порог: убирать только то, удаление чего не снимает ни одной проверки, которая сейчас даёт `pass`.
Сегодня `pass` дают: git-diff-check, change-spec, secret-scan, contract-structure, sql-safety,
ruff, bandit, factory-unit, factory-postgres-exit, source-stability. Всё остальное — SKIP, молчит
или падает.

Убрать из consumer-дерева (**15 224 LOC стека = 72,3 %**, с 9 корневыми шимами — 15 530):

1. `grok_architecture.py` + `architecture.py`, `architecture_fitness.py`, `architecture_diff.py`,
   `architecture_diagrams.py`, `queue_provenance.py` (**8 855 LOC**) и `.grok-stack/templates/
   architecture/*.example.yaml` — нет `architecture/system.yaml`, CLI exit 2, проверка в SKIP. Если
   архитектура не планируется к внедрению, `AGENTS.md` («README before push»: ссылки на
   `architecture/system.yaml`, `rules.yaml`, `generated/`) обязан быть снят, иначе контракт
   требует несуществующих файлов.
2. `grok_governance.py` + `governance.py` (**2 940 LOC**) — нет `governance/`.
3. `grok_artifacts.py` + `workflow_artifacts.py` (**1 768 LOC**) — нет ни одного
   `workflow/manifest.json`, плюс второй блок (`write_agent: null`).
4. `grok_history.py` + `history.py` (**491 LOC**) — ни одного снапшота.
5. `grok_deploy.py` + `deploy.py` (**100 LOC**) — нет `VERSION`, receipt kind `deploy` не
   заводился ни разу.
6. `demo.py` + `demo_http.py` + `.grok-stack/demo/` (**505 LOC**) — нулевых импортёров два раза.
7. `python_test_runner.py` (**308 LOC**) — вызов мёртв без корневого `tests/`.
8. `protected_write.py` (**257 LOC**) — нулевых импортёров; плюс 9 корневых шимов (306 строк) и
   `.grok/hooks/` (включая `_policy_legacy.py` 645 + `policy.py` 96), **если** хуки не будут
   зарегистрированы (см. п. 11). Иначе — не трим, а регистрация.
9. Bitrix/PHP-слой: `bitrix_checks.py` (98), 3 `bitrix_*` агента, скилл `bitrix-development`,
   профили `php/bitrix`, пины php/composer в `toolchain.json` — `repo.kind = generic`,
   `domains = []`, PHP-файлов 0.
10. `factory/` (**25 413 + 13 368 LOC**) из *гейта* этого продукта: `factory-unit` и
    `factory-postgres-exit` (158 с, ~всё время прогонов) проверяют не exolon. Минимальный
    консервативный шаг — вынести в отдельный `--profile stack` (по умолчанию выключен), оставив
    запуск по явной команде. Полная миграция — в репозиторий стека.
11. Агенты: либо `cp .grok/agents/*.md → .qwen/agents/` с правкой frontmatter (убрать `effort`,
    добавить `tools`) и удалением 21 `.toml`, либо признать 0/21 и **переписать `AGENTS.md` и
    `routing.json` на реальные имена CLI** (`general-purpose`, `Explore`, `review-agent`).
    Второй вариант дешевле и убирает невыполнимое обязательство; первый возвращает смысл правилу
    `allowed_agents`. `code_reviewer`/`test_reviewer` при любом раскладе стоит маппить на
    `review-agent`, который в CLI уже есть.
12. Каркас и схемы: пустые untracked `engineering/adr/`, `engineering/reviews/`,
    `engineering/contracts/{openapi,asyncapi,schemas}` и 8 из 10 `schemas/*.json`
    (architecture/governance/workflow-серии) — удалить вместе с пп. 1–4; `schemas/change-spec*.json`
    оставить, они реально читаются (`load_schema()`).
13. Не трим, а обязательная заплатка к триму: **`.gitignore`** (его нет) минимум на
    `.qwen/`, `__pycache__/`, `.grok-stack/runtime/`, `.ruff_cache/`. Без него untracked скретч CLI
    входит в `changed_files()`/`tree_fingerprint()` и гарантированно обесценивает каждый receipt
    (наблюдено в `changed_files` последнего receipt).
14. Линт-скоуп: добавить `engineering/**/*.py` в ruff (бесплатно по п. 4) и в `bandit` — после
    hardening XML-парсинга в двух генераторах; и **завести проверку свежести evidence**: либо
    прогон `fullaudit_measurements.py` как `test`-доказательство (у него уже есть must-fail
    контроль), либо запрет ручных правок файлов, помеченных как сгенерированные (иначе случай
    `52795d1 → linux-static-audit.md` повторится).

Оставить как есть (исполняется и даёт реальный `pass`): `verification.py` в ветках
git-diff/change-spec/secret-scan/contracts/sql/ruff/bandit/source-stability, плюс
`router.py`+`state.py`+`receipts.py`+`spec.py`+`util.py`+`change.py`+`doctor.py`+`toolchain.py`
(в сумме ~3,3 к LOC) и `policy.json`/`routing.json`/`managed.json`/`quality-profiles/*`.

Вердикт: fail

Объект вердикта — не продукт Exolon, а заявка оверлея на то, что его гейты проверяют этот
репозиторий. Она не выдерживает: `RESULT: PASS` (`state.json`: «10 checks, 0 fail») на HEAD
`52795d1` не подкреплён ни одним действующим receipt (все 3 stale, оба delegated grant просрочены),
покрывает 0 % Swift-продукта и 0 % данных уровней, три проверки скрыты за `SKIP … not configured`,
14 154 LOC стека (67,2 %) недостижимы по конфигу ещё до учёта 1 070 LOC без импортёров, hook-слой не исполнился ни разу (5/5 артефактов
отсутствуют), 0/21 агентов доступны при обязательном правиле `allowed_agents`, а whitespace-гейт
уже сломал воспроизводимость собственного evidence-артефакта без какого-либо детектора.
Локальные находки тривиально обратимы (п. 13–14 и регистрация хуков — один файл, без правок кода),
поэтому fail — это «не выставлять PASS как evidence готовности продукта, пока не закрыто», а не
«переделывать стек».
