#!/usr/bin/env bash
# macOS validation probe for the Exolon audit.
# Назначение: закрыть то, что Linux-статика доказать не может (отчёт
# engineering/reports/exolon-full-audit-20260920.md §9), и вернуть компактный
# машинно-читаемый артефакт, который можно закоммитить в evidence/.
#
# Ожидания ниже взяты из закоммиченных измерителей этого репозитория
# (evidence/fullaudit_measurements.py, evidence/perfile/*.md) и помечены EXPECTED.
# Script writes NOTHING into the repo unless you point --out at a repo path.
set -uo pipefail

OUT=""
TARGET="Exolon.xcodeproj"
CONFIG="Debug"
usage() {
  printf 'usage: %s [--out <path>] [--target <xcodeproj>] [--config Debug|Release]\n' "$0"
  printf ' Runs on macOS only; emits a key=value report plus guided play observations.\n'
  printf ' WITH_ARCHIVE=1 adds the -scheme Exolon archive attempt (slow, Release build).\n'
}
while [ $# -gt 0 ]; do
  case "$1" in
    --out) OUT="${2:-}"; shift 2 ;;
    --target) TARGET="${2:-}"; shift 2 ;;
    --config) CONFIG="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'unknown argument: %s\n' "$1" >&2; usage; exit 2 ;;
  esac
done

if [ "$(uname -s)" != "Darwin" ]; then
  printf 'FATAL: этот зонд исполняется только на macOS (uname=%s). На Linux он обязан перевернуться — см. README/runbook.\n' "$(uname -s)" >&2
  exit 75
fi
if [ ! -d "$TARGET" ]; then
  printf 'FATAL: %s не найден — запускай из корня репозитория\n' "$TARGET" >&2
  exit 66
fi

emit() { printf '%s\n' "$*"; }
have() { command -v "$1" >/dev/null 2>&1; }

if [ -n "$OUT" ]; then
  case "$OUT" in
    /*) : ;;
    *) OUT="$(pwd)/$OUT" ;;
  esac
  mkdir -p "$(dirname "$OUT")" || { printf 'FATAL: не могу создать каталог для --out\n' >&2; exit 73; }
  exec > >(tee "$OUT") 2>&1
  printf 'probe_output_will_be_written=%s\n' "$OUT"
fi

emit "# Exolon macOS probe"
emit "os_version=$(sw_vers -productVersion 2>/dev/null | tr -d '\n')"
emit "arch=$(uname -m)"
emit "hostname_redacted=$(scutil --get ComputerName 2>/dev/null | md5 -q 2>/dev/null || echo na)"
if have xcodebuild; then
  emit "xcodebuild=$(xcodebuild -version 2>/dev/null | tr '\n' ' ')"
  emit "sdk=[$(xcodebuild -showsdks 2>/dev/null | awk '/macOS/{printf "%s ", $NF}')]"
else
  emit "xcodebuild=ABSENT"
  emit "verdict_toolchain=FAIL_NO_XCODE"
fi

emit ""
emit "## A. Scheme discovery (EXPECTED: shared scheme present in xcshareddata and tracked by git — закрытие P1-11)"
# Дискриминатор обязан различать ОБЩУЮ схему и автосгенерированную Xcode: современный
# Xcode печатает Exolon в -list даже когда ни одного .xcscheme на диске нет, поэтому
# подстрока по выводу -list (как было до P1-11) не даёт доказательства.
if have xcodebuild; then
  LIST_JSON="$(xcodebuild -project "$TARGET" -list -json 2>/dev/null)"
  SHARED_SCHEME_FILE="$TARGET/xcshareddata/xcschemes/Exolon.xcscheme"
  if [ -n "$LIST_JSON" ]; then
    emit "list_json_schemes=$(printf '%s' "$LIST_JSON" | tr -d '\n ' | grep -o '"scheme":\[[^]]*\]' | head -1)"
  else
    emit "list_json_schemes=UNAVAILABLE"
  fi
  emit "shared_scheme_file_present=$([ -f "$SHARED_SCHEME_FILE" ] && echo yes || echo no)"
  emit "shared_scheme_tracked=$(git ls-files --error-unmatch "$SHARED_SCHEME_FILE" >/dev/null 2>&1 && echo yes || echo no)"
  case "$(git ls-files -- "$SHARED_SCHEME_FILE" | wc -l | tr -d ' ')" in
    1) emit "verdict_shared_scheme=PRESENT (EXPECTED after P1-11)" ;;
    *) emit "verdict_shared_scheme=ABSENT (REGRESSION: нет общего файла схемы в xcshareddata — см. finding P1-11)" ;;
  esac
fi

emit ""
emit "## B. Build"
BUILD_LOG="${TMPDIR:-/tmp}/exolon-macos-probe-build.log"
if have xcodebuild; then
  emit "build_log=$BUILD_LOG"
  xcodebuild -project "$TARGET" -target Exolon -configuration "$CONFIG" build \
    >"$BUILD_LOG" 2>&1
  emit "build_rc=$?"
  emit "build_tail=$(tail -5 "$BUILD_LOG" | tr '\n' '|')"
  APP="$(find "$(dirname "$TARGET")/build" -maxdepth 3 -name 'Exolon.app' -print -quit 2>/dev/null)"
  emit "app_path_found=${APP:-none}"
  if [ -n "${APP:-}" ]; then
    emit "## C. Bundle version truth (EXPECTED: собранные версия/билд равны build settings, неразвёрнутых подстановок не осталось)"
    PL="${APP}/Contents/Info.plist"
    SV="$(plutil -extract CFBundleShortVersionString raw "$PL" 2>/dev/null || echo na)"
    BV="$(plutil -extract CFBundleVersion raw "$PL" 2>/dev/null || echo na)"
    SETTINGS="$(xcodebuild -project "$TARGET" -target Exolon -configuration "$CONFIG" -showBuildSettings 2>/dev/null)"
    SET_MARKETING="$(printf '%s\n' "$SETTINGS" | awk -F' = ' '/^[[:space:]]*MARKETING_VERSION /{print $2; exit}')"
    SET_PROJECT="$(printf '%s\n' "$SETTINGS" | awk -F' = ' '/^[[:space:]]*CURRENT_PROJECT_VERSION /{print $2; exit}')"
    emit "settings_MARKETING_VERSION=${SET_MARKETING:-none}"
    emit "settings_CURRENT_PROJECT_VERSION=${SET_PROJECT:-none}"
    emit "plist_CFBundleShortVersionString=${SV}"
    emit "plist_CFBundleVersion=${BV}"
    emit "version_single_source=$( [ -n "$SET_MARKETING" ] && [ "$SV" = "$SET_MARKETING" ] && echo MATCH || echo MISMATCH)"
    emit "build_version_single_source=$( [ -n "$SET_PROJECT" ] && [ "$BV" = "$SET_PROJECT" ] && echo MATCH || echo MISMATCH)"
    emit "plist_unexpanded_placeholders=$(grep -c '$(' "$PL" 2>/dev/null | tr -d ' ')"
    emit "plist_LSMinimumSystemVersion=$(plutil -extract LSMinimumSystemVersion raw "$PL" 2>/dev/null || echo na)"
    emit "bundle_resources_tmx=$(ls "${APP}/Contents/Resources"/*.tmx 2>/dev/null | wc -l | tr -d ' ') (EXPECTED 125)"
    emit "bundle_has_gif=$(ls "${APP}/Contents/Resources"/*.gif 2>/dev/null | wc -l | tr -d ' ') (EXPECTED 0 — gif не в Resources phase)"
    emit "bundle_has_generated_terrain=$(ls "${APP}/Contents/Resources/generated_terrain.png" 2>/dev/null | wc -l | tr -d ' ') (EXPECTED 1 — файл в бандле, но 0/117 карт его не рисуют)"
    emit "codesign=$(codesign -dv "${APP}" 2>&1 | tr '\n' '|' | head -c 300)"
    emit "spctl=$(spctl -a -vv "${APP}" 2>&1 | tr '\n' '|' | head -c 200)"
    # Подпись: --entitlements печатает plist энтитлментов, где флага hardening нет
    # физически; hardened runtime наблюдается только в словах flags= из -d --verbose=4.
    SIGN_FLAGS="$(codesign -d --verbose=4 "${APP}" 2>&1 | grep -o 'flags=0x[0-9a-f]*([^)]*)' | head -1)"
    emit "codesign_flags=${SIGN_FLAGS:-none}"
    emit "hardened_runtime=$(printf '%s' "$SIGN_FLAGS" | grep -q 'runtime' && echo PRESENT || echo ABSENT)"
  fi
fi

emit ""
emit "## B2. Scheme addressability (EXPECTED: -scheme Exolon разрешается; отказ возможен только по подписке, не по «нет схемы»)"
if have xcodebuild; then
  DEST_LOG="${TMPDIR:-/tmp}/exolon-macos-probe-destinations.log"
  xcodebuild -project "$TARGET" -scheme Exolon -showdestinations >"$DEST_LOG" 2>&1
  emit "showdestinations_rc=$?"
  emit "showdestinations_tail=$(tail -3 "$DEST_LOG" | tr '\n' '|')"
  if [ "${WITH_ARCHIVE:-0}" = "1" ]; then
    ARCHIVE_PATH="${TMPDIR:-/tmp}/Exolon.xcarchive"
    ARCHIVE_LOG="${TMPDIR:-/tmp}/exolon-macos-probe-archive.log"
    rm -rf "$ARCHIVE_PATH"
    xcodebuild -project "$TARGET" -scheme Exolon -configuration Release \
      -archivePath "$ARCHIVE_PATH" archive >"$ARCHIVE_LOG" 2>&1
    emit "archive_rc=$?"
    emit "archive_path_present=$([ -d "$ARCHIVE_PATH" ] && echo yes || echo no)"
    emit "archive_tail=$(tail -8 "$ARCHIVE_LOG" | tr '\n' '|')"
  else
    emit "archive_rc=SKIPPED (запусти WITH_ARCHIVE=1, чтобы собрать archive той же схемой)"
  fi
fi

emit ""
emit "## D. Persisted defaults (EXPECTED: ключи Exolon.Step10.*, CONTINUE ничего не читает — evidence/perfile/economy-score.md ECO-07)"
APP_DOMAIN="com.exolon.remake"
DOM="$(defaults read "$APP_DOMAIN" 2>/dev/null | tr '\n' '|')"
emit "defaults_domain=${APP_DOMAIN}"
emit "defaults_domain_present=$([ -n "$DOM" ] && echo yes || echo no)"
emit "defaults_keys=$(printf '%s' "$DOM" | grep -o 'Exolon\.Step10\.[A-Za-z]*' | sort -u | tr '\n' ' ')"
emit "high_score_line=$(printf '%s' "$DOM" | grep -o 'HighScore = [0-9]*' | head -1)"
emit "checkpoint_line=$(printf '%s' "$DOM" | grep -o 'Exolon\.Step10\.[A-Za-z]* = [^|]*' | grep -i 'checkpoint\|zone' | head -3 | tr '\n' '|')"

emit ""
emit "## E. Play-наблюдения (ручные; каждое = одно слово ok/fail + цифра, если есть)"
emit "ожидания взяты из закоммиченных замеров; при расхождении — это и есть находка."
ask() { printf '%s\n' "$1"; printf '  EXPECTED: %s\n' "$2"; printf '  OBSERVED> '; }
ANSWERS=""
record() {
  local tag="$1" observed="$2"
  ANSWERS="${ANSWERS}${tag}=${observed:-none}
"
  printf '\n'
  emit "answer_${1}=${observed:-none}"
}
if [ -t 0 ]; then
  a=""; ask "E1 заголовок окна и HUD: какой номер шага показан?" "в окне и HUD «Step 9», на титуле «STEP 10», ключи defaults «Exolon.Step10.*» (4 носителя)"; read -r a; record E1 "$a"
  a=""; ask "E2 зона 009 (L01S10): стой в кабине на полу — проваливаешься?" "нет (пол y=64..96 цел, запас 16 px)"; read -r a; record E2 "$a"
  a=""; ask "E3 зона 009: один UP в кабине?" "EXOSKELETON ON, БЕЗ прыжка"; read -r a; record E3 "$a"
  a=""; ask "E4 зона 009: держишь UP >=2 шага в кабине?" "README обещает без прыжка; лаги предсказывают прыжок +26 px (PI-01/TC-01) — зафиксируй факт"; read -r a; record E4 "$a"
  a=""; ask "E5 кабины L02S10/L03S11/L04S16/L05S10 (зоны 034/060/090/109): проваливаешься?" "запас 0 px: касание рёбер зависит от семантики CGRect.intersects на Apple"; read -r a; record E5 "$a"
  a=""; ask "E6 спавн: сколько карт из 125 подъезжают/уезжают по вертикали за первый кадр?" "по правилу кода: 37 чисто / 59 подъём +16 / 29 падение -16 (мой прогон)"; read -r a; record E6 "$a"
  a=""; ask "E7 поршни: задень выпущенный поршень без костюма в зонах с y=384-маркерами (например L01S12)?" "летальны по площади 1 из 46 (L01S03); 2 (обе в L01S10 — README-фикс y=320) касаются ног ВПРИТЫК, т.е. их исход = вопрос семантики касания рёбер CGRect на Apple; 43 стоят ниже уровня ног"; read -r a; record E7 "$a"
  a=""; ask "E8 зона 006: после бонуса double launcher стреляет ли пусковая?" "нет навсегда (O8)"; read -r a; record E8 "$a"
  a=""; ask "E9 beam-пара (зона 035 = L02S11): сколько выстрелов до снятия?" "50 вместо 25 (RT-06/OBST-06); прыжком/приседом не переходишь: union 0..384"; read -r a; record E9 "$a"
  a=""; ask "E10 зона 124: title -> SPACE -> SPACE, очки растут?" "ферма: +9000 за цикл, до потолка 999999 (GS-01/ECO-01)"; read -r a; record E10 "$a"
  a=""; ask "E11 CONTINUE после перезапуска процесса?" "пункта CONTINUE на холодном старте НЕ видно вовсе: clearCheckpoint() вызывается при старте (:690/:722/:951), loadCheckpoint() не вызывается ниоткуда (единственное вхождение — определение GameState.swift:40); живёт только HighScore"; read -r a; record E11 "$a"
  a=""; ask "E12 выстрел вправо, стоя у правого края (x>512)?" "пуля гаснет в <=16 px: kill-граница 528, игрока отпускает до 544 (SH-01)"; read -r a; record E12 "$a"
  a=""; ask "E13 потеря фокуса окна с зажатой кнопкой движения + Cmd+Q?" "нет авто-паузы; меню нет вовсе (SH-06/LC-23/TC-07)"; read -r a; record E13 "$a"
  a=""; ask "E14 зоны 000-003 и 006: фон отсутствует как слой — как выглядит?" "5 карт без imagelayer (D-02)"; read -r a; record E14 "$a"
  a=""; ask "E15 стик-UP в кабине/телепорте?" "не срабатывает: стик даёт только .menuUp (PI-07/C5)"; read -r a; record E15 "$a"
else
  emit "play_answers=SKIPPED (stdin не tty; для сбора ответов запускай из терминала)"
fi

emit ""
emit "## E-итог (одной простынёй для diff с ожиданиями)"
printf '%s' "$ANSWERS"

emit ""
emit "## F. Что этот зонд НЕ доказывает"
emit "- он не заменяет XCTest (в продукте 0 тестов) и не доказывает отсутствие регрессий;"
emit "- ручные пункты E1-E15 — наблюдения одного прогона без записи таймингов;"
emit "- сборка Debug не эквивалентна релизу: подпись ad-hoc/Manual."
emit "- ENABLE_HARDENED_RUNTIME = DELIBERATELY DEFERRED вне этого изменения (причина и"
emit "  следующий шаг: engineering/changes/20260921-close-audit-finding-p1-11-release-layer-for-the-2e7698/release.md);"
emit "  виден он только как токен runtime в codesign_flags выше; включать его до первой"
emit "  успешной сборки (M-01) нельзя — иначе отказ нельзя атрибуить между (a)/(c) и флагом."
emit ""
emit "## G. Практика съёма (проверено по дереву)"
emit "product_log_calls=$(grep -rc 'print(\|NSLog\|os_log' Exolon --include=*.swift | awk -F: '{s+=$2} END {print s+0}') (0 → консоль доказательств не даёт)"
emit "capture=запись экрана + F1 (хитбоксы) + defaults read com.exolon.remake"
emit "level_warp_calls=$(grep -rc 'warp\|debugSkip\|skipTo' Exolon --include=*.swift | awk -F: '{s+=$2} END {print s+0}') (0 → до зоны 124 идёт ~11 мин реального хода, чекпоинта нет)"
emit "checkpoint_reader_calls=$(grep -rc 'loadCheckpoint' Exolon --include=*.swift | awk -F: '{s+=$2} END {print s+0}') (1 = только определение)"
if [ -n "$OUT" ]; then
  printf 'probe_report_saved=%s\n' "$OUT"
fi
exit 0
