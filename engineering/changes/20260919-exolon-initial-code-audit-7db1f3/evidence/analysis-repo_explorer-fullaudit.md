# Полный инвентарь репозитория и карта дельт (overlay + продукт)

**Agent:** repo_explorer (read-only), route `7db1f3f0b126`
**Дата:** 2026-09-20
**HEAD на момент анализа:** `b8aee42` (`codex/factory-updated-20260920`)
**Метод:** все утверждения ниже подтверждены командами, выполненными в `<repo>`; вывод команд цитируется сокращённо, но дословно. Всё, что не проверено напрямую, помечено «Гипотеза».

---

## 0. Рамки прогона (что делал и чего не делал)

- Файлы не редактировал (кроме этого отчёта), `.env`/ключи не читал, не ставил и не пушил ничего.
- Проверки импорта/тестов запускались с `python3 -B` (без записи `.pyc`), чтобы не менять дерево; подтверждение: после прогонов `git status --porcelain -uall` дал тот же список untracked, что и до.

---

## 1. Дельта `403eb13..b8aee42`

```
git diff --stat 403eb13..b8aee42 | tail -1
 24 files changed, 1477 insertions(+), 4 deletions(-)
git diff --name-status 403eb13..b8aee42
```

| Область | Файлы | Изменение |
|---|---|---|
| Продукт (игра) | `Exolon/`, `Exolon.xcodeproj/`, игровые доки | **0 файлов** — игра не тронута (`git diff --name-status` не содержит ни одной игровой пути) |
| `factory/src` | `adaptive_factory/landing_http.py` | M (+41/−4) |
| `factory/tests` | `test_execution_contracts.py` (+214), `test_execution_service.py` (+815) | A |
| `engineering/changes/…man-5b75d3/` | 20 файлов пакета изменений (brief/architecture/change-spec/route/state/tasks/test-plan/release/rollback/requirements + evidence: README, analysis×3, code-review, test-review, focused-verification.md, full-verification.json, regression-runner.py.txt) | A |
| `engineering/runbooks/` | `factory-source.json` | A |
| корень | `decisions.md` | A |

Коммиты и авторство:

```
git show b8aee42 --format='%H %an %ae %ad%n%s' --no-patch
b8aee429e… Codex codex@local Sun Sep 20 01:35:22 2026 +0300
chore: update installed factory to upstream 9007895
git show 403eb13:decisions.md → «decisions.md NOT at 403eb13»
```

### 1.1 Что именно изменено в `landing_http.py`

```
git diff 403eb13..b8aee42 -- factory/src/adaptive_factory/landing_http.py
```

Добавлены таблица фиксированных причин провала `_DRAFT_FAILURE_REASONS` (17 кодов `draft_*`) и функция `_draft_failure_reason(error)`; в `HttpLandingNormalizer` терминальный статус `needs_human` вместо жёсткого `http_outcome_unusable` теперь получает отображённый локальный код; комментарий в коде: «Contract details can contain model-supplied keys; only emit fixed local codes». То есть закрытие канала утечки произвольного `error.code` (данных модели) в терминальный reason.

### 1.2 Источник пина апстрима

`engineering/runbooks/factory-source.json` (прочитан целиком): upstream `https://github.com/Dimkox/adaptive-grok-build-pro`, `source_commit=90078959…`, `previous_source_commit=26a0d3db…` (= коммит 403eb13 «…factory 2.0.18 at 26a0d3d»), `product_version: 2.0.18`, `managed_file_count: 346`, изменённый managed-файл ровно один — `landing_http.py` (с дigest), а два новых тестовых модуля явно объявлены как `supplemental_upstream_test_modules`.

### 1.3 ModuleNotFoundError: было → стало

Доказательство прошлых падений (untrusted-твеждение из отчёта) подтверждается локальным receipt-файлом:

```
cat .grok-stack/runtime/receipts/7db1f3f0b126/verification.json
  … ModuleNotFoundError: No module named 'factory.tests.test_execution_contracts'
  (test_api.py:291 через __import__, test_postgres_integration.py:48 через from … import valid_packet)
  Ran 100 tests … FAILED (errors=3), receipt status: "fail"
```

Сейчас (`b8aee42`):

```
PYTHONPATH=.:factory/src python3 -B -c "import importlib; …"
OK   factory.tests.test_execution_contracts
OK   factory.tests.test_execution_service
OK   factory.tests.test_api
OK   factory.tests.test_postgres_integration   (и ещё 9 модулей — все OK)

PYTHONPATH=.:factory/src python3 -B -m unittest factory.tests.test_execution_contracts factory.tests.test_execution_service
Ran 31 tests in 0.412s — OK
```

Дополнительно собственный evidence пакета `5b75d3` фиксирует, что после обновления полный прогон зелёный:

```
python3 -B -c "… full-verification.json …"
status: pass … factory-postgres-exit pass exit=0
```

**Вывод по Q1:** да, обновление добавило ровно те два тестовых модуля, отсутствие которых вызывало 3 ERROR в `unittest discover`; их исходники присутствуют, импортируются и проходят на системном Python 3.12. Caveat: хост-окружение уже содержит зависимости factory в `~/.local/lib/python3.12/site-packages` (проверено: `fastapi.__file__=<home>/.local/…`), поэтому «чистоклоновый» прогон всё равно требует venv из `factory/pyproject.toml` (или `uv run --project factory`, как делает `run_disposable_exit.py`; `uv` на хосте есть: `<home>/.local/bin/uv`).

---

## 2. Инвентарь оверлея (фактория)

Общее: `git ls-files | wc -l` = **673** трекаемых файла; разбивка верхнего уровня:

```
git ls-files | awk -F/ '{print $1}' | sort | uniq -c | sort -rn
  300 Exolon   140 factory   75 .grok   66 .grok-stack   30 .agents
   20 engineering   13 scripts   11 schemas   + 26 одиночных файлов корня
```

### 2.1 `factory/src/adaptive_factory` — 25 026 строк

```
wc -l factory/src/adaptive_factory/*.py | tail -1  → 25026 total
```

58 top-level модулей + `adapters/` (base/codex/grok, 4 файла) + `resources/` (20 SQL-миграций `001..020`, `landing_pdf_worker.py`, 1 JSON-schema, `__init__.py`). Полный перечень с LOC:

```
wc -l factory/src/adaptive_factory/*.py | sort -n
      3 __init__.py           49 landing_failover_cli.py      50 landing_backend_api.py
     67 landing_observation.py 80 landing_failover_contracts.py 85 landing_host_config.py
     92 landing_host.py       94 landing_extra_providers.py  103 semantic_adjudication.py
    109 landing_failover_config.py 120 landing_failover_transport.py 123 landing_server.py
    128 landing_failover_journal.py 129 landing_media.py     132 landing_sse.py 132 pricing.py
    172 landing_publication_cli.py 174 cli.py  177 landing_failover.py  177 m7_autonomy_bridge.py
    181 models.py  197 settings.py  218 shadow_evaluation.py  220 landing_coordinator.py
    225 landing_evaluation.py  247 state.py  249 migrations.py  266 landing_runtime.py
    268 server.py  285 contracts.py  323 landing_backup.py  361 recovery.py
    375 landing_artifact_retention.py  382 admin.py  400 landing_http.py  430 workspace.py
    441 protocol.py  468 semantic_bridge.py  486 semantic_repair.py  488 semantic_contracts.py
    497 execution_contracts.py  556 landing_normalizer.py  560 landing_service.py
    619 landing_provider.py  632 landing_intake.py  648 brokers.py  708 landing_contracts.py
    749 landing_sqlite_store.py  758 landing_renderer.py  778 landing_live_executors.py
    904 shadow_contracts.py  932 landing_artifact.py  982 autonomy.py  990 service.py
   1392 api.py  4615 store.py
```

Кластеры: execution-plane (`api/service/store/state/models/brokers/workspace/recovery/execution_contracts/semantic_*`), landing-конвейер (~25 модулей `landing_*`), autonomy/shadow/m7-мосты. Зависимости (третьесторонние импорты в src):

```
grep -rhoE "^\s*(import|from)\s+(fastapi|httpx|uvicorn|psycopg|pypdf|…)" factory/src … | sort | uniq -c
     5 fastapi   3 httpx   17 psycopg   1 starlette   2 uvicorn
модули: admin api cli landing_backend_api landing_failover_transport landing_host
        landing_live_executors migrations server store
```

Из них psycopg в `store.py` импортируется лениво (внутри функций), fastapi в `api.py` — на уровне модуля. `factory/pyproject.toml`: deps `fastapi==0.128.2, httpx==0.28.1, uvicorn==0.48.0, psycopg[binary]==3.3.4, pypdf==6.18.1`; 6 console-scripts. В дереве также присутствуют игнорируемые артефакты локальногоEditable-install: `factory/src/adaptive_factory.egg-info/` и `__pycache__/` (см. Q4).

### 2.2 `factory/tests` — 13 файлов, 13 368 строк

```
wc -l factory/tests/*.py | sort -n
    9 __init__.py  214 test_execution_contracts.py  216 run_disposable_exit.py
  240 test_state.py  264 test_contracts.py  329 test_service.py  602 test_migrations.py
  716 test_server.py  815 test_execution_service.py  1167 test_api.py
 1548 postgres_restart_probe.py  7248 test_postgres_integration.py
```

Импорты тестов (полный уничифицированный срез `grep -hE '^\s*(import|from)\s' factory/tests/*.py | sort -u`): только stdlib (`unittest`, `json`, `hashlib`, `concurrent.futures`, `dataclasses`, `contextlib`, `copy`, `datetime`), `adaptive_factory.*` и `factory.tests.*`. **Прямых третьесторонних импортов в тестах нет (pytest не используется нигде: `grep -l "import unittest"` даёт все 9 тестовых модулей; `pytest` в `factory/pyproject.toml` не упомянут).** Транзитивно тесты опираются на хост-пакеты (fastapi и др., см. оговорку в §1.3) и на PostgreSQL 17 (`factory/compose.yaml: postgres:17-alpine`, loopback-порт `${FACTORY_POSTGRES_PORT:-55432}`; `postgres_restart_probe.py` — 1548 строк проб).

### 2.3 `factory/contracts` — заполнен, не пустой

```
find factory/contracts -type f | …
  jsonschema/  28 файлов (landing-*, semantic-*, shadow-*, m7-*, ready-for-pr-bundle,
               earned-autonomy, operator-handoff-proposal, static-landing-spec и др.)
  openapi/      7 файлов: factory-control.v1, factory-execution.v1/v2/v3,
               factory-semantic.v1, landing-dogfood.v1, landing-failover.v1
  schemas/      4 файла: execution-event.v1, execution-invocation.v1,
               task-packet.v1, workspace-result.v1
```

Потребители в коде: `factory/tests/test_api.py` читает `contracts/openapi/factory-control.v1.json`, `factory-execution.v1.json` и каталог `contracts/` (`grep -n "contracts" factory/tests/test_api.py` → строки 321, 706, 961, 1007). В `factory/src` прямых загрузчиков `contracts/jsonschema` не найдено (`grep -rln "factory/contracts|contracts/jsonschema|CONTRACT_ROOT" factory/src/adaptive_factory/*.py scripts` → пусто). 1 из 7 openapi ссылается на `jsonschema/`. **Гипотеза:** jsonschema-каталог — внешние/архивные контракты (потребители вне этого дерева, напр. доверенный CI или операторские тулзы), в репозитории они только перенесены upstream.

### 2.4 `scripts/grok_*.py` — 13 файлов, 946 строк (все — тонкие CLI к `.grok-stack/adaptive_grok`)

```
grep -n "description=" scripts/grok_*.py
```

| Скрипт | Одна строка назначения (из argparse/docstring) |
|---|---|
| grok_approve.py | Материализация локального delegated-grant (actions: `git-push-branch`, `git-push-tag`, `github-release`) |
| grok_architecture.py | «Inspect executable architecture evidence» (модель `architecture/system.yaml`+`rules.yaml`) |
| grok_artifacts.py | Компиляция недоверенных workflow-артефактов в advisory-проекции |
| grok_change.py | Управление durable-пакетами изменений `engineering/changes/` |
| grok_deploy.py | «Prepare human-owned publish commands. Never executes tag, push, or release» |
| grok_doctor.py | Health-check: toolchain-пины и install-офферы |
| grok_governance.py | Валидация/проекция governance-доказательств |
| grok_history.py | Учёт снапшота локальных доказательств без изменения runtime |
| grok_review.py | Запись fingerprint-bound review-receipt |
| grok_route.py | Создание/просмотр adaptive task-route |
| grok_spec.py | Валидация typed change-spec'ов (digest/fingerprint/coverage) |
| grok_status.py | Печать активной route/change/agent-состояния |
| grok_verify.py | Прогон route-selected verification + receipt (`--mode fast|pr|release`) |

### 2.5 `schemas/*.schema.json` — 11 файлов, потребители найдены

Файлы: architecture-rules, architecture-system, canonical-example, change-spec, change-spec-v1, debt-entry, governance-handoff-v1, governance-rule, workflow-convergence-report-v1, workflow-source-v1, workflow-task-graph-v1.

```
grep -rln "…schema.json" --include='*.py' .grok-stack scripts
 change-spec(-v1).schema.json → .grok-stack/adaptive_grok/spec.py
 architecture-{system,rules}, canonical-example, debt-entry, governance-rule,
 governance-handoff-v1        → .grok-stack/adaptive_grok/{architecture,architecture_diff,
                                 architecture_fitness,governance}.py
```

Не найдены потребители в `.py` для `workflow-convergence-report-v1`, `workflow-source-v1`, `workflow-task-graph-v1` (их упоминает только verification-мусорный grep по md/json). **Гипотеза:** они относятся к непроектному here workflow-artifacts-профилю (`grok_artifacts.py`) или оставлены upstream на будущее.

### 2.6 `.grok/` (75 трекаемых файлов)

- `agents/`: **21 роль** (каждая в паре `.md`+`.toml`): ai_architect, ai_implementer, architect, bitrix_architect, bitrix_implementer, bitrix_reviewer, code_reviewer, data_architect, data_implementer, data_reviewer, docs_researcher, frontend_implementer, general_implementer, integration_architect, integration_implementer, php_implementer, release_reviewer, repo_explorer, security_reviewer, task_analyst, test_reviewer. Тот же список из 21 зафиксирован в `.grok-stack/config/managed.json` (`"agents": […]`, проверено выводом head -25).
- `hooks/`: 10 файлов, 1005 строк (`_lib.py` 464, `pre_tool_use.py` 316 — ядро; docstring: «PreToolUse — soft policy gate (fail-open)», `stop_gate.py` 52 — «Stop gate — soft (warn only, never block stop)»).
- Конфигурация хуков в двух копиях: `.grok/hooks.json` и `.grok/hooks/adaptive.json` — одинаковый набор из 9 событий (ниже §2.9), с двухступенчатым failover: канонический `.grok/hooks/<name>.py`, затем корневой шим, затем печать `{}`.
- `skills/`: 15 каталогов (adaptive-delivery … verification-evidence). В `.agents/skills/` — 16: тот же набор **плюс `seo-landing`** (`diff <(ls .grok/skills) <(ls .agents/skills)` → `> seo-landing`); у seo-landing есть `UPSTREAM.md`/`LICENSE` — сторонний бандл.
- `config.toml`: Grok-конфиг (`default = "grok-4.6"`, `hooks = true`, комментарий «v2.0.4 hooks are fail-open»).

### 2.7 `.grok-stack/` (66 трекаемых, 75 файлов на диске без `__pycache__` — 9 untracked, см. Q4)

- `adaptive_grok/`: **29 модулей, 21 071 строка.** Вершины: `architecture.py` 3497, `governance.py` 2940, `architecture_fitness.py` 2759, `workflow_artifacts.py` 1768, `verification.py` 1158, `queue_provenance.py` 1088, `architecture_diff.py` 1218, `spec.py` 833, `receipts.py` 746, `_policy_legacy.py` 645; полный построчный вывод `wc -l` — в журнале прогона.
- `config/`: `managed.json` (21 agents), `policy.json` (schema v2, control_plane_paths — см. Q4-находку), `routing.json` (analysis-wolнs: `max_parallel_analysis: 10`, `write_roles` 7 реализаторов, reasoning default low), `toolchain.json` (пины python≥3.10 built 3.12.3 и др.), `quality-profiles/` 9 профилей (ai/base/bitrix/contracts/data/frontend/infra/integration/php), `python-test-requirements.txt` (`pytest==9.1.1, pytest-xdist==3.8.0, pytest-cov==7.1.0, coverage==7.15.4` — но pytest в тестах factory не используется; сам хост его не имеет: `python3 -m pytest` → «No module named pytest»).
- `templates/`: каркасы пакетов изменений (change/*), architecture примеры, `ci/README.md`, `hook_root_shim.py`.
- `demo/`: index.html + assets + sample-артефакты (демо-стенд оверлея, к аудиту не представал).
- `runtime/`: трекается только `.gitkeep`; на диске 9 untracked json (см. Q4): `active-route.json` (route 7db1f3f0b126, intent=review, write_agent=null, base_commit 403eb13), `active-change.json` (пакет 7db1f3), `approvals.json`, `routes/{1f980b5df386,7db1f3f0b126,d6e0aac4aae9}.json`, `receipts/7db1f3f0b126/{verification,code_review,test_review}.json` — **verification и test_review со статусом `fail`** (прошлый прогон аудита), code_review `pass`. Все receipt'ы привязаны к fingerprint дерева `af18ac77…` эпохи 403eb13+untracked → по определению устарели на b8aee42.

### 2.8 Корневые 9 `*.py` hook-файлов

```
md5sum *.py  → один и тот же хэш ca96c2c4620395a23e265f811f843bf3 для всех 9
```

Все 9 — **побайтово идентичные шимы** (964 байта): через `runpy.run_path` диспатчат в `.grok/hooks/<то же имя>.py`; если канонический файл отсутствует — печатают `{}` (для `pre_tool_use.py` — `{"decision":"allow"}`), т.е. fail-open. События по `.grok/hooks.json`: `session_start→SessionStart`, `user_prompt_submit→UserPromptSubmit`, `pre_tool_use→PreToolUse`, `post_tool_use→PostToolUse`, `pre_compact→PreCompact`, `subagent_start→SubagentStart`, `subagent_stop→SubagentStop`, `stop_gate→Stop`, `session_end→SessionEnd`.

### 2.9 Что НЕ является оверлеем (продукт, для полноты)

`find Exolon -type f | wc -l` = 300; `*.swift` = 18 файлов / 4227 строк; `*.tmx` = 125; `Exolon.xcodeproj/project.pbxproj` — 1 файл. Корневые доки продукта: `README.md` (1443 б — Step 9 archive notes), `ORIGINAL_MECHANICS.md`, `LEVEL_COMPILER_AUDIT.md`.

---

## 3. Состояние `engineering/`

```
find engineering -type d -empty | sort
  engineering/adr
  engineering/contracts/asyncapi
  engineering/contracts/openapi
  engineering/contracts/schemas
  engineering/reviews
```

- **Все пять каталогов-каркасов пустые** (adr, contracts/{openapi,asyncapi,schemas}, reviews). Git пустые каталоги не хранит → в fresh clone их вообще не будет.
- `engineering/changes/` — два пакета:
  - `20260919-exolon-initial-code-audit-7db1f3` — **UNTRACKED целиком** (`git ls-files engineering/changes/20260919-exolon-initial-code-audit-7db1f3 engineering/reports | wc -l` → `0`). `state.json`: status=`approved` (история draft→scoped→approved, до verifying/reviewing в state не доходил). Доказательства на диске полные: analysis×3, synthesis, code-review, test-review, linux-static-audit.{md,json}, linux_static_audit.py, change-spec.yaml, route/state/tasks/test-plan/release/rollback — но **в Git не зафиксированы**, а парные им receipts (runtime) имеют `status: fail` (verification/test_review) и привязаны к старому fingerprint.
  - `20260919-update-the-installed-adaptive-grok-build-pro-man-5b75d3` — **закоммичен в b8aee42**. `state.json`: status=`ready`, полные переходы draft→scoped→approved→implementing→verifying→reviewing→ready; evidence включает `full-verification.json` со `status: pass` (все проверки incl. `factory-postgres-exit pass exit=0`), code-review/test-review/focused-verification — комплект доказательств сам для себя полный.
- `engineering/reports/` — 2 файла, **оба untracked**: `exolon-initial-audit.md` (429 строк, от 2026-09-19, HEAD=403eb13) и `exolon-initial-audit-backlog.md` (48 строк).
- `engineering/runbooks/` — только `factory-source.json` (см. §1.2). **Находка:** `factory/README.md` ссылается на 5 рунбуков `../engineering/runbooks/l5-*.md` и `m4-v2.0.13-local-control-plane.md` — ни одного нет (`grep -o` + `ls`), плюс ссылка `runtime/landing-failover.example.json` — каталог `factory/runtime` отсутствует (`ls: cannot access 'factory/runtime'`). Сломанные ссылки унаследованы от upstream-пакета.

---

## 4. Git-гигиена

```
git remote -v
origin  https://github.com/Dimkox/exolon.git (fetch/push)

git for-each-ref --format='%(refname:short) -> upstream:%(upstream:short) head:%(objectname:short)' refs/heads refs/remotes
codex/factory-initial-audit      -> upstream:  head:403eb13
codex/factory-updated-20260920   -> upstream:  head:b8aee42   (текущая; БЕЗ upstream)
codex/update-factory-20260920    -> upstream:  head:403eb13   (занята внешним worktree)
origin/codex/update-factory-20260920 head:b8aee42
origin/main                          head:403eb13

git worktree list
<repo>                                   b8aee42 [codex/factory-updated-20260920]
<worktree>/exolon   403eb13 [codex/update-factory-20260920]
<worktree>/verified-exolon  b8aee42 (detached HEAD)
```

- **Ни одна локальная ветка не имеет upstream.** Содержимое `b8aee42` ушло на remote под *другим именем* `origin/codex/update-factory-20260920`; локальная `codex/factory-updated-20260920` — непривязанная однофамилица с тем же коммитом. Локальная `codex/update-factory-20260920` отстала на 1 коммит (её checkout — в worktree за пределами репозитория).
- GitHub-сторона (только чтение, `gh pr list --repo Dimkox/exolon --state all`):
  `[{"number":1,"state":"OPEN","headRefName":"codex/update-factory-20260920","title":"chore: update installed factory to upstream 9007895"}]` — **открыт единственный PR #1** (обновление фактории). Аудит-пакет 7db1f3 не имеет ни коммитов, ни PR.
- **Untracked-артефакты (`git status --porcelain -uall`, всего 49 файлов до добавления этого отчёта; проверка пересчётом `grep -c '^??'`):**
  - 18 × `.grok-stack/adaptive_grok/__pycache__/*.pyc` — НЕ игнорируются (`git check-ignore` → NOT-IGNORED), т.к. `factory/.gitignore` действует только под `factory/`;
  - 9 × `.grok-stack/runtime/*` (active-change, active-route, approvals, routes/3, receipts/7db1f3/3) — НЕ игнорируются (трекается лишь `.gitkeep`);
  - 20 × пакет аудита `7db1f3` — НЕ игнорируются;
  - 2 × `engineering/reports/*.md` — НЕ игнорируются.
- Игнорируемое (`git status --porcelain --ignored` → `!!`): `.ruff_cache/` (самоигнорируется своим авто-генерируемым `.gitignore` со `*`), `factory/src/adaptive_factory.egg-info/`, `factory/**/__pycache__/`, `.pytest_cache/` (правила из `factory/.gitignore: *.egg-info/ __pycache__/ .pytest_cache/`).
- **Корневой `.gitignore` в репозитории отсутствует** (`cat .gitignore` → exit 1; `ls .gitignore` → No such file) — при этом `.grok-stack/config/policy.json` перечисляет `.gitignore`, `trust-ci/**`, `VERSION`, `CHANGELOG.md`, `mistakes.md`, `scripts/install_into.py`, `scripts/package_stack.py` как control-plane пути; файлов `.gitignore`, `VERSION`, `CHANGELOG.md`, `mistakes.md`, каталогов `trust-ci/`, `architecture/` и обоих installer-скриптов в дереве **нет** (проверено `ls`). `AGENTS.md` предписывает вести `mistakes.md`, ссылается на `architecture/system.yaml` и `trust-ci/` — ни одного, ни другого нет; `README.md` не содержит architecture-ссылок, обязательных по контракту. **Гипотеза:** оверлей установлен неполно (инсталлятор upstream не донёс шаблонный слой), либо AGENTS.md/policy.json переписаны под целевое состояние, которого этот rebase-архив ещё не достигает. Это первоклассный объект аудита: декларация контракта расходится с деревом.

---

## 5. Поверхность удара: что НИКОГДА не_review'ировалось ни одним аудитом

Из отчёта-предшественника (untrusted) видно его покрытие: игра (`Exolon/`, pbxproj, TMX-механики, ввод/коллизии/кабина/зоны), продуктовые доки и только запуск factory-тестов как источник side-evidence (`grep -n '^#' engineering/reports/exolon-initial-audit.md`: разделы 4–11 про игру; §1 таблица «factory-postgres-exit … Это оверлей factory 2.0.18, не игра»). Никогда не инвентаризировались и не рецензировались:

1. `factory/src/adaptive_factory` — 25 026 строк Python (весь execution plane + landing pipeline + autonomy/shadow/semantic мосты); ревью был только диф `landing_http.py` в рамках чужого пакета 5b75d3 (code-review от авторов изменения, не независимый продуктовый аудит).
2. `.grok-stack/adaptive_grok` — 21 071 строка ядра оверлея (роутинг, receipts, verification, governance, architecture, queue_provenance, protected_write) — это фактически исполняемый policy-код, управляющий агентами и гейтами.
3. `.grok/hooks` (+9 корневых шимов, hooks.json/adaptive.json) — живой policy- enforcement в сессиях агентов.
4. `scripts/` (946 строк) и `schemas/` (11 контрактов) — CLI-контракты оверлея.
5. `factory/contracts` (39 контрактных файлов) — ни разу не сверялись с кодом (в §2.3 найдено лишь частичное покрытие test_api.py).
6. Runtime-состояние и paperwork: `engineering/changes/7db1f3` + `engineering/reports` не закоммичены (риск потери единственного носителя по AGENTS.md «дизайны должны жить в репо»); расхождение имён веток local/remote и 3 worktree; каркасные пустые каталоги `engineering/{adr,reviews,contracts/*}`; битые README-ссылки factory; отсутствующий корневой `.gitignore` при 27 «мусорных» untracked-файлах.
7. `.agents/skills/seo-landing` — сторонний бандл с UPSTREAM.md/LICENSE, не завязан на роутинг `.grok-stack/config` (`seo-landing` отсутствует в managed.json).

---

## 6. Итоговые ключевые выводы (для synthesis)

1. Дельта `403eb13..b8aee42` чистая и узкая: 1 файл src (фикс утечки reason в landing_http), 2 upstream-тестовых модуля (+1029 строк), пакет изменений 5b75d3 + runbook + decisions.md; игра не тронута.
2. Прошлые 3 ModuleNotFoundError-ошибки устранены на источнике: оба файла присутствуют, импортируются, 31 новый тест проходит; собственный полный прогон 5b75d3 зелёный, включая postgres-exit. Прежний fail-receipt аудита 7db1f3 остаётся в runtime как устаревший fingerprint.
3. Оверлей массивнее продукта: ~48 тыс. строк Python (factory-src 25.0k + stack 21.1k) + 13.4k тестов против 4.2k строк Swift — и он никогда не был предметом аудита.
4. Главный гигиенический дефект — отсутствие корневого `.gitignore` + untracked-результатов аудита (22 файла) и runtime-стейта (9 файлов): они одновременно «не Git-контент» по декларации AGENTS.md и не игнорируемые, т.е. каждый `git add -A` случайно их коммитит; при этом policy.json/AGENTS.md ссылаются на файлы/каталоги, которых в дереве нет (trust-ci, VERSION, mistakes.md, install_into.py, architecture/).
5. Текущая ветка `codex/factory-updated-20260920` не имеет upstream и дублирует content remote-ветки `codex/update-factory-20260920` с открытым PR #1 — имя локальной ветки в постановке задачи не соответствует ни одному remote-рефу.
