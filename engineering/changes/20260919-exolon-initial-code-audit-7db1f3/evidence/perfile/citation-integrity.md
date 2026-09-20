# Целостность цитат в markdown репозитория (HEAD `52795d1`)

Лейн read-only. Основание отсчёта — `52795d13d879ad477a3023cae69978436ff82d1a`; «существует на HEAD»
= `git cat-file -e HEAD:<путь>`. Все номера строк, которые встречаются в этом файле как ссылки на
документы, взяты из `git show HEAD:<файл>`, потому что три отчёта в `engineering/reports/` в момент
прогона параллельно редактировались другими лейнами (в рабочем дереве они длиннее на 3–11 строк).

Во время этого прогона (после съёма слепка `52795d1`) в репозитории появился коммит `ff6710b`
(«docs(audit): v3 correction pass…»): авторитет перенесён на
`engineering/reports/exolon-full-audit-20260920-v3.md`, а в v1/v2 добавлены корректирующие баннеры.
Это не меняет ни одного вывода ниже — все перечисленные связки «цитата → носитель» в теле v2 остаются
(номера строк сдвинулись на +11 из-за баннера: `76 → 87`, `65 → 76`, `68 → 79`, `55 → 66`), — но часть
из них теперь признана в шапке того же файла (`:7`: «падения на 16 px в данных нет», «28 → 27 jsonschema»).

Масштаб: 73 документа охвата (`README.md`, `ORIGINAL_MECHANICS.md`, `LEVEL_COMPILER_AUDIT.md`,
`AGENTS.md`, `decisions.md`, `factory/README.md`, `engineering/reports/*.md`,
`engineering/changes/**/*.md`, `engineering/changes/**/{state.json,change-spec.yaml}`); из них 30
отслеживаются на HEAD, цитаты найдены в 56. Извлечено скриптом (`/tmp/lane-cite/extract.py`,
`verify2.py`, `verify4.py`, `verify11.py`, `verify12.py`, `final_table.py`) **6297** цитатоподобных
вхождений: `файл:строка` — 1680, пути в backticks — 2839, относительные пути — 873, `§N` — 685,
Issue/PR-ссылки — 112, `/tmp/...` — 94, «см. ...» — 14. Для каждого: (а) существование цели,
(б) наличие приписанного факта (чтение cited-строк / grep цели), (в) «было верно» — `git show`/
`git log -S`.

Экран автоматикой: из 1680 `файл:строка`-ссылок 399 приходятся на трекнутые документы; у 240 из них
заявленный в строке идентификатор найден прямо в cited-диапазоне (зачтено без ручной сверки), 159
потребовали ручного чтения цели — из них и сложились пункты MISATTRIBUTED 13-22; остальные
оказались корректными ссылками на соседние строки того же кода (ложные срабатывания экрана — тоже
проверены вручную). Оставшиеся 1281 ссылок принадлежат in-flight черновикам лэйнов (их нет на HEAD);
они прогнаны тем же экраном, и их выходы за EOF и голые якоря попали в D7 и D8.

## Итог

| класс | уникальных объектов | цитирующих строк |
| --- | ---: | ---: |
| DANGLING | 213 | 490 |
| MISATTRIBUTED | 22 | 32 |
| STALE | 5 | 10 |

(«уникальный объект» = один битый носитель или одна связка «цитата → не тот носитель»; «цитирующих
строк» = сколько раз этот дефект повторён в текстах.)

Отдельно (не битые цитаты, а способ доказывания): четыре документа доказательной волны —
`evidence/code-review-fullaudit-final.md`, `evidence/test-review-fullaudit-final.md`,
`evidence/perfile/*` и `engineering/reports/exolon-full-audit-20260920-v3.md` — на HEAD не
отслеживаются вообще (`git ls-files` пуст), а их собственные ссылки на `evidence/...` и `:NNN`
проверены этим лейном на текущем дереве.

## DANGLING

| подкласс | уникальных | вхождений |
| --- | ---: | ---: |
| D1. Пути, обязательные по контракту `AGENTS.md`, и пустые каркасы `engineering/` | 16 | 80 |
| D2. Machine-local runtime-стейт оверлея, цитируемый как доказательство | 13 | 78 |
| D3. Внешние входы дизассемблирования, на которые ссылается `ORIGINAL_MECHANICS.md` | 6 | 20 |
| D4. Мёртвые относительные ссылки и команда внутри `factory/README.md` | 8 | 9 |
| D5. Доказательства первой волны в `/tmp` (нет даже на этом хосте) | 12 | 33 |
| D6. Скратч per-file лэйнов (голые имена + живые `/tmp/lane-*`, `/tmp/perfile-*`) | 129 | 238 |
| D7. `файл:строка` за концом файла (явно названный файл) | 3 | 3 |
| D8. Голые `:NNN`-ссылки, которые не может разместить ни один названный в строке файл | 25 | 25 |
| D9. Внутренний ID, на который ссылается «см. Q4», нигде не определён | 1 | 4 |

**D1.** `START_HERE.md`, `PROJECT_STATE.json`, `mistakes.md`, `VERSION`, `trust-ci/`, `architecture/`,
`architecture/system.yaml`, `architecture/rules.yaml`, `architecture/generated/`, пустые
`engineering/adr`, `engineering/reviews`, `engineering/contracts/{openapi,asyncapi,schemas}`.
`AGENTS.md:11,12,55,57,72` предписывает их читать/вести, `AGENTS.md:20` — operate из `trust-ci/`,
`AGENTS.md:27` — держать ссылки README на `architecture/system.yaml`, `architecture/rules.yaml`,
`architecture/generated/`; `AGENTS.md:151` — хранить отчёты ревью в change package **или**
`engineering/reviews/`. Ни одного из этих путей на HEAD нет (`ls -d architecture trust-ci` → No such
file; `find engineering/contracts -type f` → 0; в README ссылок на архитектуру нет вовсе).

**D2.** `.grok-stack/runtime/active-route.json`, `active-change.json`, `approvals.json`,
`last-fingerprint.json`, `receipts/7db1f3f0b126/{verification,code_review,test_review}.json` — в Git
из каталога отслеживается только `.grok-stack/runtime/.gitkeep`. Ссылки: `AGENTS.md:12,49,57`,
`evidence/README.md:3`, `exolon-full-audit-20260920.md:115`,
`analysis-repo_explorer-fullaudit.md:60,215`, `architecture.md:22`,
`code-review.md:53`, `code-review-fullaudit.md:24`. Формально это разрешено `AGENTS.md:12` («machine-local … may
legitimately be absent in a fresh clone»), но как **ссылка на доказательство** в fresh clone не
разрешается ни во что.

**D3.** `data_zone_data.asm`, `data_zone_blocks.asm` (`ORIGINAL_MECHANICS.md:5`),
`actions_enemy_trajectory.asm` (`:96`), `game_init_actions.asm` (`:170`), `actions_*.asm` (`:6`),
`rusarh/exolon-esl` (`:4`). Внешние входы, ни пути, ни URL-носителя в дереве нет.

**D4.** Отдельный парсер markdown-ссылок (`re.findall(r"\[..\]\((..)\)")`, base = `factory/`): в
`factory/README.md` 11 относительных вхождений / 10 уникальных целей, мёртвы 8 вхождений /
7 уникальных: `../DARK_FACTORY_ROADMAP.md`, `../engineering/runbooks/{l5-production-runtime,
l5-filesystem-publication, l5-provider-failover, l5-runtime-observation-2026-09-15,
m4-v2.0.13-local-control-plane}.md`, `runtime/landing-failover.example.json`; живы только
`../README.md` и 2 ссылки на `contracts/openapi/*.json`. Плюс `factory/README.md:86` предписывает
`python3 scripts/grok_landing_publish.py --help` — в `scripts/` 13 файлов, этого нет.

**D5.** `/tmp/docsaudit/` и 8 скриптов в нём (`docaudit.py`, `names.py`, `blocks.py`, `imgnames.py`,
`pbx.py`, `pbx2.py`, `mech.py`, `final_table.py`) — на них построены метрики джойна
(`970/72/370`) и «27 имён»; `/tmp/b01_measured.json` — разбивка B-01 первой волны
(`code-review-fullaudit.md:38,77`, `test-review-fullaudit.md:38,100`);
`/tmp/exolon-factory-exit{,2,3}.log` — «Логи factory-контуров»
(`exolon-full-audit-20260920.md:111`); `/tmp/Exolon.zip`. Всё это удалено и на этом хосте
(`ls /tmp/exolon-factory-exit*.log` → нет; есть только посторонний `…-fresh.log`).

**D6.** 129 голых имён скратча без пути и без Git-носителя: `tmx_probe.py` (12 ссылок),
`cabin_probe.py` (7), `step_model.swift` (6), `chain.py`, `lsa.py`, `fam_patched.py`,
`visualdup.py`, `gidcheck.py`, `gifcheck.py`, `final.py`, `join2.py`, `inventory.py`, `audit.py`,
`names.py`, `out.txt`, `shipcheck.py`, `jump_latch.swift`, `farm_sim.swift`, `ctl10.gif`,
`unknown-flag.log`, `no-postgres-run.log`, `exolon-factory-exit-mine.log`,
`/tmp/lane-{pbx,timing,crash,graph,score,perf,remap,mechanics,census}/…`,
`/tmp/perfile-{assets,figures,gamescene,player,runtime}/…`. Часть физически жива в `/tmp` этого
хоста, в Git — ничего: цитата «доказательство лежит в `cabin_probe.py`» не воспроизводима cloning'ом.

**D7.** `evidence/analysis-architect.md:300` → `ORIGINAL_MECHANICS.md:45-48,701-704` (файл 170
строк); `evidence/perfile/player-input.md:8` → `GameCore/Levels/TMXTileMapRenderer.swift:115-151`
(файл 150 строк; сам первичный аудит цитирует корректные `115-149`);
`evidence/perfile/spritekit-lifecycle.md:62` → `GameScene.swift:1075-1133` и `:1120-1133` (файл
1130 строк; `1131-1133` не существует).

**D8.** 25 ссылок вида `` `:NNN` ``, номер не помещается ни в один файл, названный в строке:
`analysis-architect-fullaudit.md:575` («`TMXLevelRuntime.swift:159` … плюс `:1081`» — в 533-строчном
файле 1081 нет), `analysis-docs_researcher-fullaudit.md:605` (после `AppDelegate.swift:16` — «HUD
`:67,656,984`», «титул `:832`»; в `AppDelegate.swift` 42 строки),
`perfile/gamescene.md:62,69,75,118`, `perfile/obstacles.md:47,54`, `perfile/economy-score.md:155,156,169`,
`perfile/state-hud-weapons.md:60,68`, `perfile/spritekit-lifecycle.md:57,60,62,70`,
`perfile/timing-concurrency.md:237,342`, `perfile/player-input.md:89`, `perfile/runtime.md:120`.
Содержательная часть почти всегда верна в **другом** файле (см. MISATTRIBUTED 15, 18) — дефект
формы: у ссылки нет названного носителя.

**D9.** `analysis-repo_explorer-fullaudit.md:137,209,212,215` — четыре «см. Q4»/«см. Q4-находку»;
`Q4` не определён ни в одном файле (`grep -rn Q4 --include=*.md` возвращает только эти ссылки и
пересчёт в `perfile/corpus-consistency.md`).

## MISATTRIBUTED

Цель существует, но приписанный факт ей не принадлежит или лежит в другом месте.

### A. Авторитетный отчёт `engineering/reports/exolon-full-audit-20260920.md`

1. **`:76`** — «`AGENTS.md` ссылается на отсутствующие … `scripts/install_into.py`». В `AGENTS.md`
   подстроки `install_into` нет; `VERSION` там только прозаически («current VERSION», `:26`), не путь.
   Реальный носитель перечисления — `.grok-stack/config/policy.json:9,13,21,56,64` (как и говорит
   собственный evidence-отчёт `analysis-repo_explorer-fullaudit.md:279`).
2. **`:55`** (строка O8, «Где») — `LevelObstacles.swift:699,718-723,431-478`. `:699`
   (`guard isActive, !player.isDying`) и `:718-723` (`collectBonusIfTouched → isActive = false`) ✓;
   `431-478` в этом же файле — класс `BubbleEnemy` (`:428`), к пусковой отношения не имеет.
   «Списки destructibles» — `TMXLevelRuntime.swift:431-447` (`addDestructible`) и
   `GameScene.swift:407-415,437-454`; числа `431-478` совпадают с диапазоном именно там.
3. **`:59`** (D-03) — «две разных геометрии exclusion для одного класса `capsule`
   (`max(96,w+64)` у маркера vs `w+32` у `source_marker`)» при якорях `TMXLevelRuntime.swift:304,377`.
   `:304` = `width: max(96, trigger.width + 64)` внутри `case "capsule":` (`:291`); `:377` =
   `width: trigger.width + 32` внутри `source_marker`/`changing_room` (`:371`). Подписи переставлены,
   и «одного класса» неверно: это два разных типа объектов.
4. **`:53`** (B-05) — главный тезис «`GamePersistence.loadCheckpoint()` не вызывается нигде» при якоре
   `GameState.swift:24-31`; в этом диапазоне только enum ключей (`:25-31` — 7 литералов
   `Exolon.Step10.*` ✓), а `loadCheckpoint()` — `GameState.swift:40-51`.
5. **`:49` и `:98`** (B-01 и §9.4) — «90 без локального пола» и «взять крайние: 16-px подъём vs
   **падение**» атрибутированы `evidence/fullaudit-b01-spawn.json`. Counter по закоммиченному файлу:
   `exact 35 / void 89 / 16_above 1` (`16_below` — 0). «Без локального пола» = 89, а кейса «падение на
   16 px», ради которого в чеклист поставлен пункт, в артефакте нет.
6. **`:65`** — «`factory/contracts` заполнен (**28 jsonschema** + 7 openapi)»:
   `factory/contracts/jsonschema/` = 27 файла, `openapi/` = 7 ✓ (плюс 4 в отдельном
   `factory/contracts/schemas/`); 28 не даёт ни одна команда.
7. **`:68`** — «`factory/README.md`: 7 из **8** относительных ссылок битые»: по замеру D4 — 7 мёртвых
   уникальных из 10 (8 мёртвых вхождений из 11); знаменатель «8» не восстанавливается.
8. **`:40`** (строка V3) — «все **27 имён `SKTexture(imageNamed:)`** резолвятся на диске»: узкая
   метрика даёт 23 вызова и 17 уникальных литералов; 27 получается только широкой выборкой
   (`imageNamed:` + `image:` + `imageName =`). Число верное, единица названа неверно.
9. **`:69`** — «добавлен один src-файл (`landing_http.py`, …) + 2 тест-модуля»:
   `git diff --name-status 403eb13 b8aee42` = 23 `A` + 1 `M`, и этот `M` — `landing_http.py`
   (`git cat-file -e 403eb13:factory/src/adaptive_factory/landing_http.py` ✓ файл был и раньше).
10. **`:78`** — «два внешних worktree в `~/.exolon-factory-update-20260920`»:
    `git worktree list` → `<worktree>/exolon` и
    `/…/verified-exolon`; `ls -d ~/.exolon-factory-update-20260920` → путь не существует.
11. **`:16`** (§1.5) — «контроль **0/370** на нерелевантном индексе»: собственный evidence
    (`analysis-docs_researcher-fullaudit.md:159`) — «370 из 370 (**кроме 3**) не матчатся», и в
    детализации это `blk_anim_pump {(10,): 2}` + `blk_changing_room {(12,): 1}`. Цифра «0/370» — не из
    дерева; «970 кортежей» той же строки ✓ воспроизводится (подсчёт по `LEVEL_COMPILER_AUDIT.md`).
12. **`:28`** (§2, таблица инструментов) — «снятие **9** ModuleNotFoundError-ошибок прогона 19.09»:
    артефакты говорят 3 (`exolon-initial-audit.md:48` — «100 тестов, 3 ERROR»;
    `analysis-repo_explorer-fullaudit.md:63,300`); «9» в дереве нет.

### B. Доказательная волна и общая память

13. `evidence/analysis-architect.md:182` — «`sourceHazards` is declared …
    (`TMXLevelRuntime.swift:29`)»: `:29` = `forceFields`, `sourceHazards` = `:28` (и так же на
    `403eb13` — проверено `git show`, ⇒ не сдвиг, а ошибка якоря). Парная цитата
    `analysis-architect-fullaudit.md:46` (`:28`) корректна.
14. `evidence/analysis-docs_researcher.md:267` — три якоря в `LEVEL_COMPILER_AUDIT.md`:
    «Zone 009 = `L01S10` has type 12 (`:16`); Zone 008 = `L01S09` has type 13 (`:13`); Zone 035 =
    `L02S11` has type 17 (`:35`)». Данные начинаются со строки 8 (`000 L01S01`), значит правильно
    `:17 / :16 / :43`. На названных строках лежат чужие экраны: `:13` = `005 L01S06`,
    `:16` = `008 L01S09`, `:35` = `027 L02S03` (сами типы 12/13/17 в нужных строках есть).
15. `evidence/analysis-docs_researcher-fullaudit.md:605` — «README/`AppDelegate.swift:16` =
    «Step 9 Rebase», HUD `:67,656,984` = «STEP 9», титул `:832` = «STEP 10»»: прочитанные факты
    принадлежат `GameScene.swift` (`:67` = `stepLabel.text = "STEP 9 · ALL 125 ORIGINAL ZONES"`,
    `:656`, `:984` — `STEP 9 · …`, `:832` = `addMenuLabel("STEP 10", …)`), а ближайший названный файл
    `AppDelegate.swift` вмещает 42 строки.
16. `evidence/analysis-architect-fullaudit.md:423` — «опечатка в `sourceX`/`sourceY` роняет объект в
    (0,0) (`TMXLevelRuntime.swift:345-346`)»: `:345-346` = `case "light_floor":` + `addStaticSprite`;
    `Int(object.properties["sourceX"] ?? "") ?? 0` — `:353-354`.
17. `evidence/analysis-architect-fullaudit.md:498` — «`buildCollisionRects` обходит
    `for row in 0..<collision.height` (`TMXTileMapRenderer.swift:124`)»: `:124` =
    `while column < collision.width {`, цикл по строкам — `:122`.
18. `evidence/analysis-architect-fullaudit.md:575,588` — якорь без имени файла `:1081`
    («на каждый кадр отрисовки») принадлежит `GameScene.swift:1081`
    (`for rect in currentLevel.terrainRects { addDebugRect(…) }`), а не `TMXLevelRuntime.swift:159`,
    после которого он написан; `:588` — «`includedLevels` зашита (`GameScene.swift:56`)»,
    объявление на `:53`, `:56` = `backgroundColor = .black`.
19. `evidence/analysis-repo_explorer-fullaudit.md:100,103,287` — «`factory/src/adaptive_factory` —
    **25 026** строк» с командой `wc -l factory/src/adaptive_factory/*.py`: для названного каталога
    целиком рекурсивно — **25 413** (387 строк в `adapters/`), т.е. метка «каталог» приписана
    неполному замеру.
20. `evidence/code-review-fullaudit.md:48` — «**§5 цифры:** LOC **25026** / 21071 / 13368 … **TRUE**»:
    §5 отчёта (`:65`) содержит `25 413`; ревью подтвердило число, которого в проверяемом разделе нет
    (в `code-review-fullaudit-final.md:87` те же цифры уже сведены к `25 413` ✓).
21. `evidence/test-review-fullaudit.md:53,57,58,59,60,62,64` — систематический сдвиг на −1 в
    ссылках на нумерованный список `§9` авторитетного отчёта: B-01 → «§9.3» (нужно §9.4, `:98`),
    B-05 → «§9.7» (нужно §9.8, `:102`), B-06 → «§9.8» (нужно §9.9, `:103`), O8 → «§9.4»
    (нужно §9.5, `:99`), O7 → «§9.5» (нужно §9.6, `:100`), D-02 → «§9.9» (нужно §9.10, `:104`),
    «отсылка к первичному §11.2/11.3» → «§9.10» (нужно §9.11, `:105`). Пункты §9.1/§9.2 при этом
    названы верно.
22. `decisions.md:9` — «refuted … **with a mutation control (shifting the exclusion 32/48 px does cut
    floor cells**; the shipped formula does not)»: тот же контроль аннулирован эрраттой авторитетного
    отчёта — `exolon-full-audit-20260920.md:32`: «Тот же дефект породил **неверные числа «мутационного
    контроля» у архитектора (−32→1, −48→2)**; faithful-мутация независимой проверки: смещение порога
    до ≤95 px прорезает пол». Носители отменённых чисел (`analysis-architect-fullaudit.md:616,648`)
    эрратума не получили.

## STALE

Было верно, изменено более поздним коммитом; доказательство — `git show` / `git log --diff-filter=A`.

1. **`exolon-full-audit-20260920.md:17` и `:75`** — «доказательства первичного аудита живут только в
   рабочем дереве (untracked)», «8 untracked-записей `git status`: … оба отчёта `engineering/reports/`,
   пакет аудита 7db1f3». Сдвинул **`bcacf30`** («docs: full repository audit at b8aee42»), которым эти
   же файлы и внесены: `git log --diff-filter=A -- engineering/reports/exolon-full-audit-20260920.md`
   → `bcacf30` (как и `exolon-initial-audit.md`, бэклог, весь пакет 7db1f3, `decisions.md`).
   На HEAD в untracked — 10 записей, и это уже не отчёты, а `-final`-ревью, `evidence/perfile/` и
   runtime-стейт.
2. **`exolon-full-audit-20260920.md:78`** — «текущая локальная ветка `codex/factory-updated-20260920`
   — её неотправленный однофамилец; upstream-трекинга нет ни у одной локальной ветки». Сдвинул
   **`52795d1`**: `git for-each-ref refs/remotes/origin` → `origin/codex/factory-updated-20260920 =
   52795d1`, `git branch -vv` → `[origin/codex/factory-updated-20260920]`.
3. **`exolon-initial-audit.md:45,48,51`** — «git-diff-check | FAIL», «factory-postgres-exit | FAIL …
   100 тестов, 3 ERROR», «Квитанция … `verification.json` **со статусом fail**». Два сдвига:
   **`b8aee42`** добавил `factory/tests/test_execution_contracts.py` и `test_execution_service.py`
   (`git diff --name-status 403eb13 b8aee42`), на которых `ModuleNotFoundError` исчезает;
   **`52795d1`** («normalize trailing whitespace in audit markdown **for git-diff-check gate**») —
   `git diff --check 403eb13 HEAD` → rc=0. Тот же receipt на диске сейчас: `status: pass`,
   `git-diff-check: pass`, `factory-postgres-exit: pass` (Ran 201 tests, OK),
   `created_at: 2026-09-20T03:07:02` (после `bcacf30 02:01:33` и `52795d1 02:08:11`).
4. **`analysis-repo_explorer-fullaudit.md:215`** — «receipts/…: **verification и test_review со
   статусом `fail`**, code_review `pass`; все receipt'ы привязаны к fingerprint `af18ac77…` эпохи
   403eb13+untracked». Те же файлы на диске сейчас: все три `status: pass`,
   `tree_fingerprint: 8d782be4…`. Документировано самим отчётом (`…:115` — «перезаписываются на
   финальном дереве»), но цитата в тексте осталась прежней; git-доказательства сдвига нет, потому что
   носитель вне Git (частично это D2, а не классический коммитный stale).
5. **Шапки снимка** — `exolon-full-audit-20260920.md:3` («**HEAD:** `b8aee42`») и
   `exolon-initial-audit.md:3` («полный аудит, HEAD `b8aee42`»): на HEAD это два коммита назад.
   Содержательная часть ярлыка («продукт идентичен `403eb13`») остаётся истинной:
   `git diff --stat 403eb13 HEAD -- Exolon Exolon.xcodeproj README.md ORIGINAL_MECHANICS.md
   LEVEL_COMPILER_AUDIT.md` пуст. Сюда же — `exolon-initial-audit-backlog.md:15`
   («Внешние тикеты **не** создавались»), снятое `bcacf30`, в котором тот же отчёт записал `#155/#157`.

## Что закрывает гейт, а что нет

Закрывает (подтверждено независимыми пересчётами над деревом):

- все `evidence/*`- и `engineering/**`-ссылки двух отчётов и `change-spec.yaml` разрешаются на HEAD
  (`fullaudit_measurements.py`, `fullaudit-b01-spawn.json`, `linux_static_audit.py`,
  `linux-static-audit.{md,json}`, `analysis-*-fullaudit.md`, `{code,test}-review-fullaudit.md`);
- якоря первичного аудита в Swift/TMX/pbx / plist: из ~190 проверенных `файл:строка` ни одного
  уходящего за файл или мимо строки — таблицы `§4.3`, `§5.1`, `§6`, `§8`, `§9.3`, `§10` сошлись
  строка-в-строку (`AppDelegate.swift:16`, `GameScene.swift:832`, `GameView.swift:50-67`,
  `GamepadInput.swift:49-91`, `InputState.swift:70-77`, `Player.swift:137-178,232-240,252-258`,
  `TMXLevelRuntime.swift:264-269,297-306,356-360,361-365,409-413`,
  `LevelObstacles.swift:341-345,718-723,746-756`, `GameConstants.swift:25-31`, README:15/23,
  `ORIGINAL_MECHANICS.md:30`, `LEVEL_COMPILER_AUDIT.md:5`); продукт с `403eb13` не менялся, так что
  ни одна из них не могла «уплыть»;
- числовые утверждения, которые удалось пересобрать: `970` кортежей, `125` экранов, `18` Swift-файлов,
  `282` файла в `Exolon/Resources` (125/153/3 + plist), `118` `zone_*_original.png`,
  LOC `25 413 / 13 368 / 21 071 / 21 105 / 4 227`, `+1477/−4` и 24 файла на `403eb13..b8aee42`,
  пустой diff продукта, `sha256 landing_http.py` = манифестный (`21c03d67…ca01ddc`),
  `double_launcher` 19 объектов / 18 карт, `blk_gunMachine_BOTTOM` 18, `waggon+mushroom` 33,
  `teleport` 70 (35 пар), beam-пары 10 карт, `tiledRect` ровно 1/125, 127 `source_marker` (51
  необработанный), `XCTest`-файлов 0, `try!/as!` 0, корневого `.gitignore` нет;
- внешние Issue/PR-ссылки живы и соответствуют тезисам (read-only `gh`): `Dimkox/adaptive-grok-build-pro`
  #155 OPEN, #157 OPEN, апстрим PR #22 MERGED; `Dimkox/exolon` PR #1 OPEN, `isDraft: true`.

Не закрывает (и не может закрыть) локальный гейт:

- ни одна цитата из D2/D5/D6 не воспроизводима в fresh clone: квитанции, `/tmp`-логи и скратч-скрипты
  не являются Git-контентом; закоммиченный носитель есть только для B-01
  (`fullaudit-b01-spawn.json`) и для замеров (`fullaudit_measurements.py`), и именно поэтому
  расхождения MISATTRIBUTED 5/11/12 остаются неисправленными в тексте отчётов;
- статус `grok_verify`/`grok_review` mutable: один путь на HEAD-дереве даёт `pass`, а описан в
  первичном аудите как `fail` (STALE 3, 4) — снимка квитанции в Git нет;
- состояние веток/remote/PR (STALE 1, 2, 5) лежит вне дерева полностью;
- контрактозависимые пути (D1) — не опечатка аудитов, а неисполнимый контракт: mandatory-entrypoint
  файлы, `trust-ci/`, `architecture/*` отсутствуют, каркасы `engineering/{adr,reviews,contracts/*}`
  пустые, README без architecture-ссылок, `.gitignore` нет ⇒ D6-скратч не может попасть в репозиторий
  даже случайно, а значит цитаты вида «доказательство в `cabin_probe.py`» методологически не
  закрываемы;
- противоречие «общая память ↔ отчёт» (`decisions.md:9` против эрратты `:32`) локальный гейт не
  ловит вообще: он проверяет fingerprint, а не непротиворечивость утверждений.

Вердикт: fail
