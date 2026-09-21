# Независимое ревью аудита `exolon-full-audit-20260920.md`

**Агент:** `code_reviewer` (read-only), маршрут `7db1f3f0b126`, HEAD `b8aee42`.
**Объект ревью:** артефакт аудита (`engineering/reports/exolon-full-audit-20260920.md` + evidence
`analysis-{repo_explorer,architect,docs_researcher}-fullaudit.md`), НЕ продуктовый код.
**Дата проверки:** 2026-09-20. Все измерения ниже выполнены в текущем рабочем дереве заново.

## Вердикт: **PASS**

Ни одной существенной (material) ошибки в аудите не найдено. Я independently перепроверил 20
нагрузочных утверждений из §1, §3, §4 (B-01..B-06, D-01..D-03), §5, §6, §8 и ключевой отказ от C1 —
каждое воспроизводится (см. таблицу). Числа согласованы: отчёт ↔ evidence ↔ receipt ↔ дерево.
Контроль честности соблюдён: Linux-статика нигде не выдаётся за продуктовую валидацию, play/runtime
помечены гипотезами и вынесены в §9 macOS-чеклист.

Найдены только **низкосеверитетные** дефекты точности (число мутационного контроля C1, одна двусмысленная
формулировка про клетки будки, пара label/скоуп-нюансов). Они не меняют продуктовых выводов и не вводят
в заблуждение относительно валидации — **FAIL не объявляется**.

### Объём подтверждения продукта
- `git diff --stat 403eb13 b8aee42 -- Exolon Exolon.xcodeproj` → **пусто** (exit 0) — продукт не тронут ✓
- `git status --porcelain` → 8 untracked-записей (collapsed): 5×runtime, `__pycache__`, `engineering/reports/`,
  пакет 7db1f3; корневой `.gitignore` отсутствует (`ls` → No such file) ✓
- `.grok-stack/runtime/receipts/7db1f3f0b126/verification.json`: `status: pass`, **13 проверок**
  (git-diff-check, change-spec, architecture=skip, governance=skip, workflow-artifacts=skip, secret-scan,
  contract-structure, sql-safety, ruff, bandit, factory-unit, factory-postgres-exit, source-stability),
  в stdout `factory-postgres-exit`: `Ran 201 tests in 164.555s — OK` ✓

## Таблица проверенных утверждений

| # | Утверждение аудита (§) | Команда / метод (независимо) | Результат |
|---|---|---|---|
| 1 | **C1 отказ (§1.1, §3):** фактич. код `−16` не режет пол L01S10; exclusion y=112..224; floor intact | python-реплика `buildCollisionRects`+`subtract` на L01S10.tmx (map 35×24, tile 16, pxH=384; capsule 368,176,32×80 tiledRect) | **TRUE.** 9 collision-rect; exclusion=(352,112,96,112) снимает **5** клеток объёма будки (x=368..448, y=128..208), **0** клеток пола (пол y=64..80 и y=80..96, верх платформы y=96, до exclusion 16px) |
| 2 | **C1 мутационный контроль (§3):** «−32→1 клетка, −48→2 клетки» | тот же скрипт: `−16`→`−32`/`−48` в x и y (height фикс. +32) | **НЕ сходится.** −32 → **0** floor-rect; −48 → **1** floor-rect (x=272..560,y=80..96). Non-blindness доказана, но фигура «1/2» не воспроизводится; coord «x=0..288,y=224..240» в architect не существует как rect L01S10 |
| 3 | **O7 (§3,§4):** 10/10 карт с beam содержат обе ветки up+down ⇒ 50 хитов | python-обход 125 TMX по `sourceBlock beam_up/beam_down` | **TRUE.** beam_up=10, beam_down=10, both=10, any=10; список `L02S11,15,17;L03S01,13,19;L04S18;L05S11,15,17` — совпал с evidence |
| 4 | **D-02 (§4):** 5 первых зон (000-003, 006) без `imagelayer` | python: `root.find('imagelayer') is None` | **TRUE.** 5 файлов `L01S01,S02,S03,S04,S07` = зоны 0,1,2,3,6 |
| 5 | **D-03 (§4):** `coordinateMode=tiledRect` ровно 1/125; две геометрии exclusion | grep python + TMXLevelRuntime.swift:304 vs :377 | **TRUE.** 1 файл (L01S10); capsule `max(96,w+64)` @304, marker `w+32` @377; у capsule `x` без `max(0,...)` (асимметрия vs :375) ✓ |
| 6 | **B-01 (§4):** 35 exact / 90 без локального пола | разбор `/tmp/b01_measured.json` | **TRUE.** exact=35, non-exact=90 (void 89 + 16_above 1) |
| 7 | **B-01/B-02 refs:** fallback-плоскость и допуск 1.5px | grep Player.swift | **TRUE.** `landOnFallbackFloorIfNeeded` @291-296 (`position.y=standingCenterY` @294), `footY > fallbackGroundY + 1.5` @198, `refreshGroundSupport` @182, спавн из `vitorc` + `groundY=min(rect.maxY)` в init |
| 8 | **B-04 (§4):** zlib/gzip→throw→fatalError; makeMap без проверки непустоты; мусор→0 | grep TMXMapLoader.swift | **TRUE.** `throw unsupportedCompression` @307-308 (диапазон 305-333), `makeMap` @155 без guard на width/height/layers, `int()??0` @346 / `cgfloat→0` @349; fatalError в TMXLevelRuntime @53 |
| 9 | **B-05 (§4):** `loadCheckpoint()` не вызывается | `grep -rn loadCheckpoint Exolon/` | **TRUE.** ровно 1 совпадение = определение @GameState.swift:40, 0 вызовов |
| 10 | **B-06 (§4):** resign чистит только `.keyboard`; `pausePressPending` не сбрасывается | read InputState.swift:57-90, GameView.swift:42-43 | **TRUE.** `windowDidResignKey` → `reset(source:.keyboard)`; `reset(source:)` @57-60 НЕ трогает `pausePressPending` (только `resetAll` @66) и не зовёт `resetGamepad` @80 |
| 11 | **C5 (§3):** стик-UP ≠ jump | grep GamepadInput.swift | **TRUE.** `leftThumbstick` @71 ставит только `.menuUp`; `dpad.up` @60-61 ставит `.jump`+`.menuUp` |
| 12 | **V1 (§3):** сборка 0.5, бандл 0.3 | grep pbxproj + Info.plist | **TRUE.** `MARKETING_VERSION=0.5` @1424/1443, `GENERATE_INFOPLIST_FILE=NO`, `CFBundleShortVersionString` = литерал `0.3` @Info.plist:18 |
| 13 | **V2 (§3):** ключи `Exolon.Step10.*` | grep GameState.swift | **TRUE.** 7 ключей @25-31 |
| 14 | **§1.2/§2:** `swiftc -frontend -parse` 18/18 PASS | swiftc 6.4 по всем `Exolon/**/*.swift` + control слом. swift | **TRUE/воспроизводимо.** PASS=18 FAIL=0; контроль отклонил битый swift. (swift `6.4` vs «6.4.0» в тексте — тривиально) |
| 15 | **§1.3:** xmllint 125/125 well-formed + control | xmllint --noout по TMX + битый XML | **TRUE/воспроизводимо.** 125 OK / 0 bad; контроль отклонил битый XML |
| 16 | **§5 цифры:** LOC 25026 / 21071 / 13368, ~14× продукта | `wc -l` | **TRUE.** factory/src=25026, tests=13368, `.grok-stack/adaptive_grok/*.py`=**21071**; продукт=4227 → 59465/4227=**14.07×**. (весь `.grok-stack/*.py`=21105, +34 = `templates/hook_root_shim.py`) |
| 17 | **§6 PR/ветки:** PR #1 (DRAFT) на head `codex/update-factory-20260920` | `gh pr view 1 --json isDraft,state,headRefName` | **TRUE.** `state=OPEN, isDraft=true, headRefName=codex/update-factory-20260920` |
| 18 | **§5 factory README:** 7 из 8 относительных ссылок битые | python-разрыв links + `os.path.exists` | **TRUE (7 broken).** Битые: 5×`runbooks/l5-*`, `runtime/landing-failover.example.json`, `../DARK_FACTORY_ROADMAP.md`, `m4-v2.0.13-...`. Знаменатель «8» = doc-ссылки (плюс 2 JSON openapi резолвятся) —minor |
| 19 | **§5 manifest:** sha256 `landing_http.py` = манифестный; `managed_file_count=346` | sha256sum + `factory-source.json` | **TRUE.** `21c03d67…ca01ddc` совпал с `changed_managed_files`; `managed_file_count:346` ✓ |
| 20 | **§1.5/§4 D-01:** LEVEL_COMPILER_AUDIT объявляет тип 11=56 («rocket launchers») | `grep "Action counts"` LEVEL_COMPILER_AUDIT.md:5 | **TRUE (характеристика документа верна).** `11=56, 15=7, 17=10` — реинтерпретация типа 11=BOTTOM остаётся за docs_researcher-джойном |

## Находки

### Suggestion (низкая северити)
- **S-1 — C1: цифра мутационного контроля не воспроизводится.** §3/§1.1 asserts «−32 режет 1 клетку,
  −48 — 2 клетки», architect приводит rect `x=0..288, y=224..240`. При верной мутации литерала `16`→`32`/`48`
  (x и y; height = `trigger.height+32` фикс.) независимый замер даёт **−32→0** и **−48→1** floor-rect
  (срезается `x=272..560, y=80..96`). Приведённый architect rect на координатной сетке L01S10 отсутствует.
  Первичный вывод (−16→0, floor цел, снимаются 5 клеток будки) — **корректен и воспроизводим**; поправить
  только контрольные числа/координаты, иначе «замер не слепой» выглядит как подгонка.
- **S-2 — §1 п.1 формулировка «клетки внутри будки (y=128..208) вообще не солидны» двусмысленна.**
  В исходном Collision-слое эти 5 клеток **солидны** (gid≠0) — именно поэтому exclusion их удаляет.
  Не-солидны они только ПОСЛЕ вычитания. Переформулировать («после исключения become pass-through»),
  иначе читатель заключит, что exclusion — no-op.

### Nice-to-have (очень низкая)
- **N-1 — §1.4/§5 «21 071 LOC policy-кода в `.grok-stack`».** Точное число 21071 относится к
  `.grok-stack/adaptive_grok/*.py`; весь `.grok-stack/*.py` = 21105 (лишние 34 строки — не-policy
  `templates/hook_root_shim.py`). repo_explorerscoped верно; в сводном отчёте сузить подпись до `adaptive_grok`.
- **N-2 — §4 B-05 «6 ключей пишутся».** `GameState.swift:25-31` определяет **7** ключей `Exolon.Step10.*`
  (highScore пишется отдельно через `saveHighScore`). Указать, какие именно 6, или писать «7 ключей-констант».

### Наблюдение (не дефект)
- Под-разбивка B-01 в architect-прозе (59 вверх / 29 вниз / 2 void) не совпадает с метками
  `/tmp/b01_measured.json` (89 `void` / 1 `16_above`) — это разные измерения; отчёт же утверждает только
  верховый итог **35/90**, который сходится. `/tmp`-артефакты эфемерны и вне git — §10 честно указывает
  воспроизводящие команды.

## Контроль честности и согласованность (отдельная проверка из ТЗ)
- Разделение confirmed / hypothesis / macOS-pending: **соблюдено последовательно.** §1.2 явно ограничивает
  потолок Linux-валидации («Тип-чек и сборка невозможны без Apple SDK»); §4 колонка «Статус» различает
  «код+данные» vs «play-гипотеза»; runtime-эффекты (B-02 «идёт по воздуху», B-06 поведение SKView) помечены
  runtime-hypothesis и продублированы как шаги §9 macOS-чеклиста.
- **Нет ни одного места, где Linux-статика подаётся как продуктовая/рантайм-валидация** → оснований для
  Critical нет.
- Ключевые числа согласованы между отчётом, evidence и receipt: **201 тест** (receipt stdout + §1.4),
  **35/90** (JSON), **10/10 beam** (перебор), **18/18 parse** (swiftc), **25026/21071/13368** (wc), **4227**
  продукта, **~14×** (14.07) — все сходятся.

## Итог
Артефакт аудита Достоверен: нагрузочные утверждения воспроизводятся из дерева, отказ от C1 математически
верен, продуктовый код не менялся, контроль честности выдержан. Рекомендуемые правки — только точность
цифр/формулировок (S-1, S-2) и скоуп-подписи (N-1, N-2). **Verdict = PASS.**
