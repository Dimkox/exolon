# Гигиена публичного репозитория: машинные следы, креды, происхождение

Срез: HEAD `52795d13d879ad477a3023cae69978436ff82d1a`, только отслеживаемый git-ом контент
(`git grep` по индексу). Отдельный слой — метаданные коммитов, они не являются содержимым файлов.
Дискиплайн: read-only, ни один чужой файл не изменён.

## Итог

| Метрика | Число |
|---|---|
| Отслеживаемых файлов | 703 (`git ls-files \| wc -l`) |
| Хитов с машинно-локальным путём `/home/...` | 7 строк / 8 вхождений токена, 3 файла (`git grep -n -I -E '/home/' \| wc -l`) |
| Хитов `/Users/...` | 0 (`git grep -n -I -E '/Users/' \| wc -l`) |
| Windows-пользовательских путей (`C:\Users`, `C:/Users`) | 0 (`git grep -n -I -E '[A-Za-z]:\\Users\|C:/Users' \| wc -l`) |
| Хостнейм `<host>` | 4 строки, 4 файла (`git grep -n -I -E '\b<host>\b' \| wc -l`) |
| `localhost` | 2 строки (`git grep -n -I -i 'localhost' \| wc -l`) |
| `127.0.0.1` / `0.0.0.0` | 20 строк, все — фикстуры тестов и bind-конфиг (`git grep -n -I -E '127\.0\.0\.1\|0\.0\.0\.0' \| wc -l`) |
| e-mail в отслеживаемом содержимом | 1 строка, синтетическая (`landing-renderer@invalid.local`) |
| Личный e-mail в метаданных коммитов | 1 адрес на 2 из 4 коммитов (`git log --pretty='%ae' \| sort \| uniq -c`) |
| URL на несуществующий/приватный репозиторий | 7 строк, 6 файлов; `curl` → HTTP 404 |
| PEM-заголовки / JWT / `gh[pousr]_`,`AKIA`,`AIza`,`xox` / `sk-`,`Bearer` | 0 / 0 / 0 / 0 |
| URL вида `scheme://user:pass@host` | 0 (`git grep -n -I -E 'https?://[^/[:space:]]*[^/[:space:]]@' \| wc -l`) |
| Длинные блоки: `*.tmx` (данные слоёв) / вне tmx | 251 / 380 строк |
| Файлы-креденшалы (`.env`, `*.pem`, `*.key`, `id_rsa*`) в индексе | 0 действующих; единственное совпадение маски — шаблон `factory/.env.example`; на диске вне индекса — 0 (`find` см. ниже) |
| Носители заявок о происхождении: `.tmx` с `zoneSource` | 121 файл (`git grep -l -I 'zoneSource' -- '*.tmx' \| wc -l`) |
| LICENSE / NOTICE / THIRD-PARTY для игрового контента в корне | 0 (отсутствуют) |

Вердикт по слою публикации — **fail**: единственный класс реальных утечек (машинные пути +
хостнейм) целиком внесён документами самого аудита и лежит в 5 отслеживаемых файлах; продуктовое
дерево (`Exolon/`, `tools/`, `schemas/`, `assets/`, сборочные скрипты) чисто — 0 хитов
(`git grep -n -I -E '/home/\|/Users/\|\b<host>\b' -- 'Exolon/**' 'tools/**' 'assets/**' 'schemas/**' \| wc -l` → 0).

## Машинные пути и имена

Классификация: **(a)** безобидный repo-относительный или синтетический путь,
**(b)** машинно-локальный путь, раскрывающий имя пользователя, **(c)** URL на приватный/несуществующий репозиторий.

### (b) Раскрытие имени пользователя — 8 вхождений, 3 отслеживаемых файла

Отличное от нуля множество токенов (`git grep -h -o -E '/home/[A-Za-z0-9._/-]+' \| sort \| uniq -c`):

```
3 <repo>
1 <worktree>/verified-exolon
1 <worktree>/exolon
1 <repo>/Exolon.xcodeproj/project.pbxproj
1 <home>/.local/bin/uv
1 <home>/.local/
```

Построчно (`git grep -n -I -E '/home/'`):

- `engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/analysis-docs_researcher-fullaudit.md:8` — эхо команды `$ cd <repo> && git log --oneline -3 && git rev-parse HEAD`
- `.../evidence/analysis-repo_explorer-fullaudit.md:6` — «все утверждения ниже подтверждены командами, выполненными в `<repo>`»
- `.../evidence/analysis-repo_explorer-fullaudit.md:86` — два токена: `<home>/.local/bin/uv` и `<home>/.local/`
- `.../evidence/analysis-repo_explorer-fullaudit.md:265` — `<repo>  b8aee42 [codex/factory-updated-20260920]`
- `.../evidence/analysis-repo_explorer-fullaudit.md:266` — `<worktree>/exolon  403eb13 [codex/update-factory-20260920]`
- `.../evidence/analysis-repo_explorer-fullaudit.md:267` — `<worktree>/verified-exolon  b8aee42 (detached HEAD)`
- `.../evidence/test-review.md:13` — `<repo>/Exolon.xcodeproj/project.pbxproj`

Это имя пользователя (`pall`) и структура домашнего каталога машины-разработчика, опубликованные
в публичном репозитории. Строки 265–267 дополнительно раскрывают существование служебного
каталога `.exolon-factory-update-20260920` вне рабочего дерева.

### (b) Хостнейм — 4 строки

`git grep -n -I -E '\b<host>\b'`:

- `engineering/changes/20260919-exolon-initial-code-audit-7db1f3/brief.md:15` — «Exolon was imported into a <host>/factory workspace…»
- `.../evidence/analysis-repo_explorer.md:7` — «**Host:** Linux `<host>` <kernel> x86_64 (Ubuntu)» — хостнейм + точное ядро + дистрибутив (отпечаток машины)
- `engineering/changes/20260919-update-the-installed-adaptive-grok-build-pro-man-5b75d3/release.md:3` — «Install the verified update branch on <host>…»
- `.../20260919-update-the-installed-adaptive-grok-build-pro-man-5b75d3/tasks.md:8` — «install this commit on <host>…»

### (a) Безобидные (не требуют правки)

- `.agents/skills/seo-landing/references/tech-spec.md:176` — `http://localhost:8000` в тексте вендорного скилла как пример сервирования.
- `factory/tests/test_migrations.py:277` — строка-фикстура `"localhost:5432\n"` в юнит-тесте парсера.
- 20 строк `127.0.0.1` / `0.0.0.0` в `factory/compose.yaml`, `factory/.env.example`, `factory/tests/*.py`, `.grok-stack/adaptive_grok/demo_http.py` — loopback-bind и тестовые DSN; никакого реального секрета.
- `factory/src/adaptive_factory/landing_renderer.py:34` — `FIXED_COMMIT_EMAIL = "landing-renderer@invalid.local"`: зарезервированный TLD, псевдо-автор для воспроизводимости сборки. Единственный e-mail в отслеживаемом содержимом.
- `.../evidence/analysis-repo_explorer-fullaudit.md:38` — `b8aee429e… Codex codex@local Sun Sep 20 01:35:22 2026 +0300` — цитата `git log` с идентичностью агента (не человека).
- 13 URI на зарезервированных TLD (`.invalid`, `.local`) как `$id` JSON-схем и в тестах (`git grep -n -I -E 'https?://[A-Za-z0-9._-]+\.(invalid\|local\|test\|example)' \| wc -l`) — заглушки, не внешние адреса.
- Пути в `.grok-stack/config/policy.json` и denylist-политиках (`_policy_legacy.py:28,32,33`, `manifest.py:14,52,53`) — шаблоны исключений, а не указатели на реальные файлы.

### (c) URL на несуществующий/приватный репозиторий — 7 строк, 6 файлов

`git grep -n -I 'ai-dark-factory-landing'`; проверка доступности
(`curl -s -o /dev/null -m 12 -w '%{http_code}' https://github.com/<repo>`) → **404**:

- `factory/src/adaptive_factory/landing_renderer.py:24` — `TARGET_REPOSITORY_ID = "github.com/Dimkox/ai-dark-factory-landing"`
- `factory/contracts/jsonschema/landing-backend-capability.v1.schema.json:27`
- `factory/contracts/jsonschema/landing-failover-config.v1.schema.json:44`
- `factory/contracts/jsonschema/landing-failover-result.v1.schema.json:51`
- `factory/contracts/openapi/landing-failover.v1.json:41`
- `factory/contracts/openapi/landing-failover.v1.json:109`
- `factory/contracts/openapi/landing-dogfood.v1.json:82` — заголовок `X-Repository-ID`, который «must exactly match trusted repository configuration»

Контракты зашивают идентификатор репозитория, который снаружи не резолвится (приватный либо ещё
не созданный). Это не утечка, но документированного объяснения в дереве нет.

Для сравнения, остальные упоминаемые адреса живые и публичные (тот же `curl`):
`Dimkox/exolon` 200, `Dimkox/adaptive-grok-build-pro` 200, `rusarh/exolon-esl` 200,
`newagebegins/exolon` 200, `aleksandr-alhoff/seo-landing` 200. `git remote -v` →
`origin https://github.com/Dimkox/exolon.git` (совпадает с опубликованным).

### Вне содержимого файлов: метаданные коммитов

`git log --pretty='%ae' | sort | uniq -c`:

```
2 <owner-email>
2 codex@local
```

Личный адрес `<owner-email>` (2 коммита) опубликован в метаданных публичного репозитория, хотя в
отслеживаемом содержимом его нет (`git grep -n -I 'mail\.ru' \| wc -l` → 0). Устранение требует
переписывания истории — необратимая операция, здесь только фиксируется, не выполняется.

## Внесено ли это самим аудитом

Да — на 100%. Все хиты класса (b) находятся в отчётах и доказательствах Change-пакета
`20260919-exolon-initial-code-audit-7db1f3`, сгенерированных инструментами этого дерева;
ни один хит не принадлежит продукту.

Построчная разбивка по пакету
(`git grep -n -I -E '/home/\|/Users/\|\b<host>\b\|codex@local' -- 'engineering/changes/20260919-exolon-initial-code-audit-7db1f3/**'`
→ 10 строк в 5 файлах):

| Файл (внутри `engineering/changes/20260919-exolon-initial-code-audit-7db1f3/`) | Хитов | Отслеживается на HEAD? |
|---|---|---|
| `brief.md` | 1 (хостнейм, :15) | да |
| `evidence/analysis-repo_explorer-fullaudit.md` | 6 (:6, :38, :86×2-токена, :265, :266, :267) | да |
| `evidence/analysis-docs_researcher-fullaudit.md` | 1 (:8) | да |
| `evidence/analysis-repo_explorer.md` | 1 (:7, хостнейм+ядро) | да |
| `evidence/test-review.md` | 1 (:13) | да |
| `evidence/perfile/mechanic-fidelity.md` | 1 | **нет** (untracked) |
| `evidence/perfile/figures-audit.md` | 2 | нет |
| `evidence/perfile/tmx-census.md` | 2 | нет |
| `evidence/perfile/stack-overlay-usage.md` | 2 | нет |
| `evidence/perfile/corpus-consistency.md` | 1 | нет |
| `evidence/perfile/compiler-doc-remap.md` | 1 | нет |
| `evidence/fullaudit-b01-spawn.json` | 0 | да |
| `evidence/linux-static-audit.json` | 0 | да |
| `evidence/linux-static-audit.md` | 0 | да |
| `evidence/synthesis.md`, `evidence/README.md`, `evidence/code-review*.md`, `evidence/analysis-architect*.md`, `evidence/fullaudit_measurements.py`, `evidence/linux_static_audit.py` | 0 | да |

Счёт по untracked-файлам: `grep -rIcn -E '/home/' <пакет> \| grep -v ':0$'` — 9 вхождений в 6
файлах каталога `evidence/perfile/`; `git ls-files '…/evidence/perfile/*' | wc -l` → 0, т.е. весь
`perfile/` (21 файл на момент среза) в индекс не попадает и наружу не публикуется. Отдельно
`evidence/code-review-fullaudit-final.md` (1 вхождение) — тоже untracked.

Итого в опубликованном виде требуют правки ровно 5 отслеживаемых файлов (10 строк).
Каталог `.grok-stack/runtime/` в индексе представлен только файлом `.gitkeep`
(`git ls-files '.grok-stack/runtime*'`); `active-change.json`, `active-route.json`,
`approvals.json`, `receipts/`, `routes/` — untracked и наружу не уходят.
В короне дерева собственного `.gitignore` нет (`git ls-files \| grep gitignore` → только
`factory/.gitignore`), поэтому защита `runtime/` держится на неизвестированности, а не на правиле.

## Проверка на креды (что НЕ читалось)

Ни одного подлиного секрета не найдено. Проверенные классы:

| Класс | Результат | Команда |
|---|---|---|
| PEM-заголовки (`BEGIN … PRIVATE/CERTIFICATE/OPENSSH/PGP`) | 0 реальных; 2 совпадения — литеры проекций governance: `.grok-stack/adaptive_grok/governance.py:83` и `scripts/grok_governance.py:73` (`<!-- BEGIN ADAPTIVE GROK GOVERNANCE PROJECTION: {name} -->`) | `git grep -n -I -E 'BEGIN [A-Z ]*(PRIVATE\|PUBLIC\|CERTIFICATE\|RSA\|EC\|OPENSSH\|PGP)'` |
| JWT-подобные токены (`eyJ….eyJ….`) | 0 | `git grep -n -I -E 'eyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.'` |
| GitHub `gh[pousr]_`, AWS `AKIA`/`ASIA`, `AIza…`, Slack `xox…` | 0 | `git grep -n -I -E 'gh[pousr]_[A-Za-z0-9]{16,}\|AKIA[0-9A-Z]{16}\|xox[baprs]-\|ASIA[0-9A-Z]{16}\|AIza[0-9A-Za-z_-]{30,}'` |
| `sk-…` / `Bearer …` | 0 | `git grep -n -I -E 'sk-[A-Za-z0-9]{20,}\|Bearer [A-Za-z0-9._-]{30,}'` |
| DSN с паролем (`scheme://user:pass@`) | 0 для `http(s)`; 7 строк `postgresql://user:…@127.0.0.1` — все плейсхолдеры/фикстуры (`git grep -n -I -E 'postgresql://[^@]+@' \| wc -l` → 7: `.env.example` ×2, `factory/README.md` ×1, `run_disposable_exit.py` ×1, `test_migrations.py` ×3) | `git grep -n -I -E 'https?://[^/[:space:]]*[^/[:space:]]@' \| wc -l` → 0 |
| Присвоения `password/secret/token/api_key = "…"` | 32 строки, все тестовые константы, разорванные склейкой (`"execution-" + "identity-credential"`), loopback DSN и `.env.example`-плейсхолдеры | `git grep -n -I -E '(://[^/[:space:]]*:[^/@[:space:]]+@\|(password\|passwd\|secret\|token\|api_?key\|private_?key)[[:space:]]*[:=][[:space:]]*["'"'"'][^"'"'"']{6,})' \| wc -l` → 32 |
| Длинные base64 (≥120 символов) | 4 строки, все — `<data encoding="base64">` карт: `Exolon/Resources/L01S04.tmx:15,18,28,31` | `git grep -n -I -E '[A-Za-z0-9+/]{120,}={0,2}'` |
| Длинные hex (≥64) | 631 строка: 251 в `*.tmx` (тайловые слои) + 380 вне карт | `git grep -n -I -E '\b[0-9a-fA-F]{64,}\b' \| wc -l` |

Из 380 «вне карт» длинных блоков 198 — quoted-строки ровно из 64 hex, и все они стоят под
ключами целостности, а не под ключами доступа
(`git grep -h -o -E '"[a-z_0-9]+"\s*:\s*"[0-9a-f]{64}"' \| sed -E 's/:.*//' \| sort \| uniq -c`):
`"sha256"` ×125 (`evidence/linux-static-audit.json` — поштучные хэши файлов, которые аудировали),
`tool_policy_digest`/`prompt_template_digest`/`pdf_decoder_digest`/`output_schema_digest`/`decoder_digest` ×8
(`factory/contracts/jsonschema/landing-backend-capability.v1.schema.json`),
`base_fingerprint` ×3 (`.grok-stack/adaptive_grok/demo.py:22`,
`20260919-exolon-initial-code-audit-7db1f3/route.json:15`,
`20260919-update-the-installed-adaptive-grok-build-pro-man-5b75d3/route.json:18`) и
`tree_fingerprint` ×1 (`…5b75d3/evidence/full-verification.json:5`).
Значения в `.grok-stack/adaptive_grok/governance.py:44-48`, `architecture_fitness.py:142-148` и
`architecture.py:1097` — те же sha256-дайджесты схем, только ключом служит путь к файлу
(`_GOVERNANCE_SCHEMA_DIGESTS`), а не строка-имя.
Плюс 172 `sha256:`-хэша блокировки зависимостей
(`grep -n -o -E 'sha256:[0-9a-f]{64}' factory/uv.lock \| wc -l` → 172).

Файлы-креденшалы: `git ls-files` по маскам `.env$|\.env.|.pem|.key|.p12|.pfx|id_rsa|id_ed25519|.npmrc|.netrc|credentials|secrets|keystore`
даёт ровно один результат — `factory/.env.example`. Файлы с такими именами вне индекса
(`find . -path ./.git -prune -o \( -iname '*.pem' -o -iname '*.key' -o -iname '.env' -o -iname 'id_rsa*' -o -iname '*credentials*' -o -iname '*.p12' \) -print`)
— 0 результатов, то есть рабочего файла секрета в дереве нет.
Маска шире (`-name '.env*' -o -name '*token*' -o -name '*secret*'`) находит только
`factory/src/adaptive_factory/resources/019_usage_token_components.sql` (миграция схемы учёта
токенов, не значение токена) и тот же `factory/.env.example`.

### Пути, названные, но не открытые и не прочитанные

Правило слой-а: файлы окружения, ключей и локальных хранилищ разрешений не читались и не
перечислялись по содержимому. Только пути и факт, что они оставлены непрочитанными:

- `factory/.env.example` — отслеживаемый шаблон; значения получены исключительно из строк grep
  (`:6`, `:9`), файл целиком не открывался. `FACTORY_MIGRATOR_DATABASE_URL` и
  `FACTORY_DATABASE_URL` содержат буквальные плейсхолдеры `replace-owner-for-local-use` /
  `replace-runtime-for-local-use`, то есть не являются действующим паролем.
- `$HOME/.qwen/.env` — упоминается как параметр CLI в `factory/README.md:69`
  (`--qwen-env-file "$HOME/.qwen/.env"`). Файл вне репозитория, не читался.
- `.grok-stack/runtime/approvals.json` — локальное хранилище разрешений; untracked, не читался
  (перечислено только имя через `ls .grok-stack/runtime`).
- `.grok-stack/runtime/active-change.json`, `active-route.json`, `receipts/`, `routes/` —
  untracked машинное состояние, не читались.
- `trust-ci/env/*.env`, `trust-ci/runtime/**` — пути-исключения из политик
  (`.grok-stack/adaptive_grok/_policy_legacy.py:33`, `.grok-stack/config/policy.json:94`);
  каталог `trust-ci/` в этом дереве отсутствует, читать нечего.
- `.env`, `.env.*`, `**/*.pem`, `**/*.key`, `**/id_rsa`, `**/credentials*` — denylist-шаблоны из
  `.grok-stack/adaptive_grok/_policy_legacy.py:28,32` и `.grok-stack/config/policy.json:44-47,82-85`;
  это записи политики, а не существующие файлы.

## Заявки о происхождении

Отдельные утверждения об источнике, которые дерево делает само о себе:

1. **`zoneSource` в 121 карте** (`git grep -l -I 'zoneSource' -- '*.tmx' | wc -l` → 121;
   всего вхождений свойства — 121 из 1357 `<property>`-строк). Уникальные формулировки
   (`git grep -h -o -E '<property name="zoneSource" value="[^"]*"' | sed -E 's/.*value="//;s/"$//' \| sort \| uniq -c`):
   - `rusarh/exolon-esl asm/data_zone_data.asm` — ×117, например `Exolon/Resources/L01S09.tmx:6`
   - `rusarh/exolon-esl original zone_data.asm + original walkthrough` — ×2, `L01S05.tmx:7`, `L01S06.tmx:7`
   - `rusarh/exolon-esl data_zone_data.asm + verified object behavior` — ×1, `L01S07.tmx:7`
   - `rusarh/exolon-esl data_zone_data.asm + actions_mines.asm` — ×1, `L01S08.tmx:7`
2. **Ссылки на другой внешний репозиторий в 4 картах** — `originalSource` / `referenceSource` /
   `referenceObjects` со значением `newagebegins/exolon …`:
   `Exolon/Resources/L01S01.tmx:6`, `L01S02.tmx:6`, `L01S03.tmx:6`, `L01S04.tmx:6` (последняя —
   `referenceObjects="newagebegins/exolon L01S04"`).
3. **Заявка на авторство оригинала и на дизассемблирование** — `ORIGINAL_MECHANICS.md:4`:
   «Rafaelle Cecco's 1987 game as disassembled in `rusarh/exolon-esl`»; там же
   `:3` «Sources of truth for this remake:», `:5` «`data_zone_data.asm` / `data_zone_blocks.asm`
   for all 125 zone layouts and action markers», `:6` «The individual `actions_*.asm` routines for
   behaviour».
4. **Имена внешних ASM-модулей, на которые ссылается дерево** — 6 уникальных
   (`git grep -h -o -E '[A-Za-z_]+\.asm' -- '*.tmx' ORIGINAL_MECHANICS.md \| sort \| uniq -c`):
   `data_zone_data.asm` ×120, `zone_data.asm` ×2, `game_init_actions.asm` ×1 (`ORIGINAL_MECHANICS.md:170`),
   `data_zone_blocks.asm` ×1, `actions_mines.asm` ×1 (`L01S08.tmx:7`),
   `actions_enemy_trajectory.asm` ×1 (`ORIGINAL_MECHANICS.md:96`).
5. **Прямолинейный перенос байтовых таблиц** — `ORIGINAL_MECHANICS.md:96`: «The six trajectory
   byte tables in `actions_enemy_trajectory.asm` must be ported literally, not replaced by generic
   homing/patrol AI».
6. **Имена ассетов, подразумевающие внешний источник** — 118 файлов вида
   `Exolon/Resources/zone_NNN_original.png` (`git ls-files '*.png' | grep -c '_original\.png$'` → 118)
   плюс 2 `zone0NN_scenery.png` и `generated_terrain.png`/`step5_tiles.png`. Суффикс `_original`
   — неявное утверждение «взято из оригинала»; ни один из этих 153 PNG не имеет sidecar-ноты.
7. **Заявки на «оригинальность» в README и картах** — `README.md:6` «keeps the existing 125-zone
   project and original-visual pipeline»; `L01S05.tmx:6`/`L01S06.tmx:6` `step9Corrected="authoritative
   original zone 00N layout"`; `L01S07.tmx:6`/`L01S08.tmx:6` `step9Progress="original zone 00N source
   reconstruction"`; `LEVEL_COMPILER_AUDIT.md:1` — заголовок «# Original level compiler audit».
8. **Вендорный скилл с корректно оформленным происхождением** (контрастный пример, он в дереве есть):
   `.agents/skills/seo-landing/UPSTREAM.md:3` «Repository: https://github.com/aleksandr-alhoff/seo-landing»,
   `:6` «License: MIT, Copyright (c) 2026 Aleksandr Alhov», подкреплённые
   `.agents/skills/seo-landing/LICENSE` и разделом «Provenance and license»
   (`.agents/skills/seo-landing/README.md:42`).
9. **Идентификаторы внешних репозиториев в коде и контрактах**:
   `engineering/runbooks/factory-source.json:3` — `upstream_repository:
   https://github.com/Dimkox/adaptive-grok-build-pro`;
   `factory/src/adaptive_factory/landing_artifact.py:35` — `CONTROL_REPOSITORY_ID =
   "github.com/Dimkox/adaptive-grok-build-pro"`; 7 строк `github.com/Dimkox/ai-dark-factory-landing`
   (см. (c) выше).

### Что дерево о происхождении НЕ документирует

- **LICENSE для самого проекта отсутствует**: единственный лицензионный файл во всём дереве —
  `.agents/skills/seo-landing/LICENSE` (относится к вендорному скиллу).
  `git ls-files \| grep -i -E 'licen[cs]e\|notice\|copyright\|third[-_]part(y\|ies)\|attribut'` → 1 строка.
  В корне отслеживаемые файлы — только `README.md`, `AGENTS.md`, `ORIGINAL_MECHANICS.md`,
  `LEVEL_COMPILER_AUDIT.md`, `decisions.md` и hook-скрипты.
- **Нет NOTICE / THIRD-PARTY-NOTICES / COPYRIGHT / ATTRIBUTION** ни в одном каталоге.
- **README ни словом не упоминает происхождение**: `grep -n -i -E 'cecco\|licen\|copyright\|third-party\|attribut\|exolon-esl\|rusarh\|newagebegins' README.md` → 0 совпадений при 23 строках файла. Все атрибутивные утверждения живут в `ORIGINAL_MECHANICS.md` и в свойствах `.tmx`, куда читатель с главной страницы не попадает.
- **Не указан источник 118 `*_original.png`**: ни лицензии на artwork, ни формата
  «взято из / перерисовано / сгенерировано», ни ссылки на конкретный внешний дамп в дереве нет.
- **Не зафиксирован ни коммит, ни версия внешних ASM-файлов**: ссылки вида
  `rusarh/exolon-esl asm/data_zone_data.asm` не содержат ни URL, ни commit SHA, ни контрольной
  суммы, ни даты — воспроизвести заявленный источник по дереву нельзя (в отличие от
  `engineering/runbooks/factory-source.json`, где для другого апстрима хэши файлов есть).
- **Не документирован статус `newagebegins/exolon`**: 4 карты называют его ссылкой, без описания
  отношений и без лицензии.
- **Не объяснён несуществующий `Dimkox/ai-dark-factory-landing`** (404), зашитый в контракты как
  обязательное значение заголовка.

Оценку законности перечисленного отчёт не содержит: зафиксированы только сами заявления и
отсутствующие артефакты.

Вердикт: fail
