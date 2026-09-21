# macOS validation handout v2 — релизный слой после P1-11

Дата: 2026-09-21. Дерево: ветка `codex/release-layer-p1-11-20260921`, база маршрута `403eb13`.
Заменяет по содержанию `engineering/changes/20260919-exolon-initial-code-audit-7db1f3/evidence/perfile/macos-validation-handout.md`
в части версий и схем. Датированный оригинал **не правится**: он остаётся доказательством состояния
на 2026-09-20, и именно его контрольная строка «собралось 0.5 ⇒ вывод V1 неверен» теперь является
**успехом** этого изменения, а не фальсификацией (см. M-01′ ниже).

Хост исполнителя — Linux: Xcode/xcodebuild/codesign недоступны, поэтому весь этот лист ожиданий
рассчитан на один прогон владельцем и ни один его пункт не засчитывается Linux-вердиктом
(`evidence/release_layer_check.py` AC-010 в `requirements.md`).

## M-01′. Первая сборка и подстановка версии (главный пункт)

```bash
xcodebuild -project Exolon.xcodeproj -target Exolon -configuration Debug build
plutil -extract CFBundleShortVersionString raw build/Debug/Exolon.app/Contents/Info.plist
plutil -extract CFBundleVersion           raw build/Debug/Exolon.app/Contents/Info.plist
grep -c '$(' build/Debug/Exolon.app/Contents/Info.plist
```

| Что наблюдаем | Ожидание | Если иначе |
| --- | --- | --- |
| сборка | `** BUILD SUCCEEDED **` — первый в истории проекта type-check | падение = находка вне P1-11; фиксировать лог целиком, релизный слой тут ни при чём (plist и схема не участвуют в компиляции Swift) |
| `CFBundleShortVersionString` | `0.5` (= `MARKETING_VERSION` из target-конфигов) | `0.3` ⇒ подстановка не применена; литерал `$(MARKETING_VERSION)` ⇒ имя настройки недоступно этому Xcode. Оба случая — forward-fix одной строкой plist (см. `rollback.md`), и новая находка уровнем P2 |
| `CFBundleVersion` | `1` (= `CURRENT_PROJECT_VERSION`) | аналогично |
| `grep -c '$('` | `0` — неразвёрнутых подстановок в собранном бандле быть не может | ≥1 ⇒ запрещённое состояние (AC-003 в плане); какой именно ключ — смотреть `plutil -p` |
| контрольная сверка | `xcodebuild -project Exolon.xcodeproj -target Exolon -configuration Debug -showBuildSettings \| awk '/ MARKETING_VERSION \| CURRENT_PROJECT_VERSION/{print}'` даёт те же значения | расхождение = probe напечатает `version_single_source=MISMATCH` |

## M-02′. Схема адресуется (то, ради чего добавлялся файл)

```bash
xcodebuild -project Exolon.xcodeproj -list -json        # схемы: общие vs автосгенерированные
xcodebuild -project Exolon.xcodeproj -scheme Exolon -showdestinations
```

rc=0 и непустой список destinations доказывают, что загрузчик схем разобрал файл: схема не просто
лежит в `xcshareddata`, она живая. rc≠0 ⇒ схема битая (атрибут/ссылка/префикс контейнера) — это и есть
главный остаточный риск изменения, на Linux непроверяемый; правка локальна (один файл).

Отдельно: `-scheme Exolon` теперь доступен, но `-target Exolon` **остаётся** маршрутом сборки в probe
(§B) — fallback, на который опирался прежний протокол, снимать его в том же коммите нельзя.

## M-03′. Попытка archive (отдельный флаг, медленно)

```bash
WITH_ARCHIVE=1 engineering/runbooks/macos-probe.sh --out /tmp/probe-p1-11.txt
```

Ожидание честное, а не желаемое: `archive_rc` может быть ненулевым **из-за подписи**
(ad-hoc `CODE_SIGN_IDENTITY = "-"`, пустой `DEVELOPMENT_TEAM`). Значение ровно одно: провал
класса «нет схемы / нечего архивировать» означал бы, что M-02′ не прошёл, а провал по подписке —
что работа схемы в порядке и находка переходит к клаузе «подпись». Фиксировать вывод полностью.

## M-04′. Hardened runtime: зафиксировать отсрочку фактом

```bash
codesign -d --verbose=4 build/Debug/Exolon.app 2>&1 | grep -o 'flags=0x[0-9a-f]*(.*)'
```

Ожидание на этом дереве: токена `runtime` **нет** (`ENABLE_HARDENED_RUNTIME` намеренно не включён —
причина и порядок: `../../release.md` §Deferred). Это не провал, а подтверждение того, что отсрочка
соответствует дереву. Прежняя строка probe (`codesign -d --entitlements :-`) флаг не видела физически —
энтитлментов в проекте нет; теперь probe печатает `codesign_flags` и производный `hardened_runtime=`.

**M-01′ зелёный — предусловие для того, чтобы вообще снимать отсрочку.** Пока первая сборка не
доказана, включать hardening нельзя: отказ нельзя атрибуить. Change на hardening — отдельный, сразу
после зелёного M-01′, с негативным контролем на до-фиксной сборке и одним ручным прогоном
(геймпад/HUD/звук/отладка).

## Что закрывает этот прогон

Одна сессия владельца закрывает одновременно (1) лакуну «проект никогда не собирался» (M-01′),
(2) доказательство подстановки идентификатора версии — то есть половину P1-11, закрытую на Linux
только структурно, и (3) факт адресности схемы (M-02′) с попыткой archive (M-03′). Результат
возвращается как артефакт probe (`--out`) в `evidence/` этого пакета; ничего из него не должно
становиться зелёным задним числом.
