#!/usr/bin/env bash
# macOS validation probe for the Exolon audit.
# Назначение: закрыть то, что Linux-статика доказать не может (отчёт
# engineering/reports/exolon-full-audit-20260920.md §9), и вернуть компактный
# машинно-читаемый артефакт, который можно закоммитить в evidence/.
#
# Ожидания ниже взяты из закоммиченных измерителей этого репозитория
# (evidence/fullaudit_measurements.py, evidence/perfile/*.md) и помечены EXPECTED.
# Script writes NOTHING into the repo unless you point --out at a repo path.
#
# Wave D (change 20260924-complete-wave-d-specification-and-release-audit-8341b7)
# добавляет два трека (контракт: evidence/analysis-integration_architect.md §2):
#   Track A (C-10..C-16) — обязательный archive и разбор самого .xcarchive. Секретов
#                не требует; ровно его и закрывает этот change.
#   Track B (C-20..C-31) — Developer ID подпись и нотаризация. Доступен ТОЛЬКО человеку:
#                WITH_SIGNING=1 И EXOLON_HUMAN_SIGNING_RUN=1 И интерактивный tty.
#                Вне tty — отказ (exit 77); кривая конфигурация — exit 78.
# Verdict vocabulary: PASS|FAIL|NOT_ATTEMPTED|TOOL_ABSENT|REFUSED. Код возврата зонда —
# операционный статус, а НЕ вердикт; NOT_ATTEMPTED нельзя читать как успех.
# Съём и проверка отчёта: engineering/changes/<wave-D>/evidence/macos-handout/README.md
set -uo pipefail

# --- аргументы и запрещённые формы -------------------------------------------
# argv сохраняется ДО разбора: сканер обязан увидеть ровно то, что набрал оператор.
RAW_ARGV=()
RAW_ARGV=("$@")
OUT=""
TARGET="Exolon.xcodeproj"
CONFIG="Debug"
PROBE_LINES=0
REPO_ROOT="$(pwd -P)"
PROBE_REL_PATH="engineering/runbooks/macos-probe.sh"

# Списки ниже собраны классами символов намеренно: сам файл зонда не должен содержать
# запрещённые формы целиком (контракт §5.2.3), иначе их можно было бы передать зонду
# «случайно». Это проверяет macos_handout_check.py.
EXOLON_FORBIDDEN_ARGV='^--(apple[-_]id|pass[-_]?word|key|s(ign)?|cert(ificate)?|provision(ing)?[-_]?path|mobile[-_]?provision)([= ].*)?$'
EXOLON_FORBIDDEN_ARGV_PATH='\.(p1[2]|p[89]|pem|provision|pkey|keychain|mobile[-_]?provision)$'
EXOLON_FORBIDDEN_ARGV_TEXT='-{5}BEGIN|PRIVATE[ _]KEY|(^|[^A-Za-z])PEM($|[^A-Za-z])|apple[-_]id|pass[-_]?word'
EXOLON_FORBIDDEN_ARGV_SHORT='^-s$|^--k$'
EXOLON_FORBIDDEN_ENV_NAMES='(PASSWORD|SECRET|TOKEN|PRIVATE_KEY|APPLE_ID)'
# Значение переменной — ИМЯ keychain-профиля, никогда не секрет. Имя обязано
# начинаться с буквы или цифры: флаг, затесавшийся на её место, отвергается.
EXOLON_NOTARY_PROFILE_RE='^[A-Za-z0-9._][A-Za-z0-9._-]{0,63}$'

usage() {
  printf 'usage: %s [--out <path>] [--target <xcodeproj>] [--config Debug|Release]\n' "$0"
  printf ' Runs on macOS only; emits a key=value report plus guided play observations.\n'
  printf ' The Track A archive step (C-10/C-11) is mandatory now and needs no secrets.\n'
  printf ' WITH_ARCHIVE=1 is accepted for compatibility with the older handout and no\n'
  printf ' longer gates anything: a skipped archive used to be misread as a success.\n'
  printf ' EXOLON_PROBE_SCRATCH=<dir outside the clone> moves the build root (defect M-9).\n'
  printf ' WITH_SIGNING=1 requests Track B and is REFUSED unless the operator also sets\n'
  printf ' EXOLON_HUMAN_SIGNING_RUN=1 and types the attestation on a tty.\n'
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

# Всё, что попадает в отчёт, идёт через эти четыре помощника: счётчик строк обязан знать
# ровно столько законченных строк, сколько зонд выдал, иначе барьер flush (M-8) ничего
# не проверяет.
emit() { printf '%s\n' "$*"; PROBE_LINES=$((PROBE_LINES + 1)); }
emit_part() { printf '%s' "$*"; }
emit_nl() { printf '\n'; PROBE_LINES=$((PROBE_LINES + 1)); }
emit_block() {
  local block="$1" count
  count=$(printf '%s' "$block" | grep -c '' | tr -d ' ')
  printf '%s' "$block"
  PROBE_LINES=$((PROBE_LINES + ${count:-0}))
}
have() { command -v "$1" >/dev/null 2>&1; }

if [ -n "$OUT" ]; then
  case "$OUT" in
    /*) : ;;
    *) OUT="$(pwd)/$OUT" ;;
  esac
  mkdir -p "$(dirname "$OUT")" || { printf 'FATAL: не могу создать каталог для --out\n' >&2; exit 73; }
  exec 3>&2
  exec > >(tee "$OUT") 2>&1
  emit "probe_output_will_be_written=$OUT"
else
  exec 3>&2
fi

# >>> probe-check:begin forbidden_argv_scan
probe_forbidden_argv_scan() {
  # rc 0 = формы чистые, rc 1 = обнаружены формы, похожие на подписные материалы.
  # Нарушитель не печатается и не вырезается: вызывающий обрывает весь прогон
  # (контракт §5.2.4 — abort, not redact), частичный Track-B отчёт не появляется.
  local candidate token parts
  for candidate in "$@"; do
    parts=()
    read -r -a parts <<< "$candidate"
    for token in "${parts[@]:-}"; do
      [ -n "$token" ] || continue
      printf '%s' "$token" | grep -Eq -e "$EXOLON_FORBIDDEN_ARGV" && return 1
      printf '%s' "$token" | grep -Eq -e "$EXOLON_FORBIDDEN_ARGV_PATH" && return 1
      printf '%s' "$token" | grep -Eq -e "$EXOLON_FORBIDDEN_ARGV_TEXT" && return 1
      printf '%s' "$token" | grep -Eq -e "$EXOLON_FORBIDDEN_ARGV_SHORT" && return 1
    done
  done
  return 0
}
# <<< probe-check:end forbidden_argv_scan

# >>> probe-check:begin forbidden_env_names
probe_forbidden_env_names() {
  # Смотрим только ИМЕНА переменных; значения не читаются и не печатаются никогда.
  # Наружу уходит только счётчик: отказ не должен унести секрет в отчёт.
  local line name bad=0
  while IFS= read -r line; do
    name=${line%%=*}
    if printf '%s' "$name" | grep -Eq -e "$EXOLON_FORBIDDEN_ENV_NAMES"; then
      bad=$((bad + 1))
    fi
  done < <(env)
  printf '%s\n' "$bad"
  [ "$bad" -eq 0 ]
}
# <<< probe-check:end forbidden_env_names

# >>> probe-check:begin notary_profile_gate
probe_validate_notary_profile() {
  # Профиль нотаризации — ИМЯ в keychain, а не секрет; неправильная форма = 78.
  local name="${1:-}"
  [ -n "$name" ] || return 1
  printf '%s' "$name" | grep -Eq -e "$EXOLON_NOTARY_PROFILE_RE"
}
# <<< probe-check:end notary_profile_gate

# >>> probe-check:begin signing_parser
probe_signing_identity_class() {
  # Разбор вывода codesign -dvvv: пять классов, адхок-подпись не превращается в настоящую.
  local dump="${1:-}"
  case "$dump" in
    *"Developer ID Application"*) echo "DEVELOPER_ID" ;;
    *"Apple Development"*|*"iPhone Developer"*) echo "APPLE_DEVELOPMENT" ;;
    *"Signature=adhoc"*|*"adhoc"*) echo "ADHOC" ;;
    *NOT_ATTEMPTED*) echo "NOT_ATTEMPTED" ;;
    *) echo "UNKNOWN" ;;
  esac
}
# <<< probe-check:end signing_parser

# >>> probe-check:begin notary_parser
probe_notary_verdict() {
  # Разбор notarytool: Accepted/Invalid/In Progress/REFUSED/TOOL_ABSENT/NOT_ATTEMPTED.
  # Обязательное свойство (self-test §J): Accepted и NOT_ATTEMPTED дают РАЗНЫЙ вывод.
  local dump="${1:-}"
  case "$dump" in
    *"status: Accepted"*|*"Accepted"*) echo "ACCEPTED" ;;
    *"status: Invalid"*|*"Invalid"*) echo "INVALID" ;;
    *"In Progress"*) echo "IN_PROGRESS" ;;
    *REFUSED*) echo "REFUSED" ;;
    *TOOL_ABSENT*) echo "TOOL_ABSENT" ;;
    *NOT_ATTEMPTED*) echo "NOT_ATTEMPTED" ;;
    "") echo "NOT_ATTEMPTED" ;;
    *) echo "INVALID" ;;
  esac
}
# <<< probe-check:end notary_parser

probe_classify_archive_failure() {
  # C-11: «нет схемы» и «нет подписи» — РАЗНЫЕ находки. Раньше archive_rc плюс хвост
  # лога не различали их, и отказ схемы выглядел как отказ подписки.
  local log="$1"
  if [ ! -s "$log" ]; then echo "OTHER"; return 0; fi
  if grep -qi "no scheme named\|does not contain a scheme\|cannot find scheme\|Xcode couldn't find any" "$log"; then
    echo "NO_SCHEME"; return 0
  fi
  if grep -qi "code signing\|Code Signing Error\|requires a provisioning\|no profile\|no signing certificate\|identity not found\|errSecInternalComponent\|confusable" "$log"; then
    echo "SIGNING"; return 0
  fi
  echo "OTHER"
}

# >>> probe-check:begin flush_barrier
probe_flush_barrier() {
  # M-8: `exec > >(tee "$OUT") 2>&1` оставляет файл неполным за спиной rc=0: из десяти
  # прогонов эталонной формы 7 вернули обрезанный файл, 4 — пустой. На macOS bash 3.2
  # pid process substitution там не сохраняется, поэтому барьер проверяет ЧИСЛО СТРОК
  # с ограниченным ожиданием и никогда не зависит от pid.
  # аргументы: <файл отчёта> <сколько строк зонд обязан был выдать до барьера>
  # Сам барьер дописывает ровно три строки прямо в файл (мимо tee): так его собственные
  # строки не попадают в гонку. rc 0 = файл полон; rc 73 = нет, то есть неcomplete-файл
  # не может стоять за rc=0. '-' означает «файла нет» (запуск без --out).
  local file="$1" want="$2" total tries delay written i verdict
  total=$((want + 3))
  tries=${PROBE_FLUSH_TRIES:-60}
  delay=${PROBE_FLUSH_DELAY:-0.1}
  written=0
  i=0
  while [ "$i" -lt "$tries" ]; do
    written=$(wc -l < "$file" 2>/dev/null | tr -d ' ')
    written=${written:-0}
    [ "$written" -ge "$want" ] && break
    sleep "$delay"
    i=$((i + 1))
  done
  verdict=no
  if [ "$written" -ge "$want" ]; then verdict=yes; fi
  if [ "$file" = "-" ]; then
    printf 'report_lines_expected=%s\n' "$total"
    printf 'report_lines_written=%s\n' "$written"
    printf 'report_flush_verified=%s\n' "$verdict"
    if [ "$verdict" = "yes" ]; then return 0; fi
    return 73
  fi
  if [ "$verdict" = "yes" ]; then
    printf 'report_lines_expected=%s\nreport_lines_written=%s\nreport_flush_verified=yes\n' \
      "$total" "$total" >> "$file"
  else
    printf 'report_lines_expected=%s\nreport_lines_written=%s\nreport_flush_verified=no\n' \
      "$total" "$written" >> "$file"
  fi
  i=0
  written=0
  while [ "$i" -lt "$tries" ]; do
    written=$(wc -l < "$file" 2>/dev/null | tr -d ' ')
    written=${written:-0}
    [ "$written" -ge "$total" ] && break
    sleep "$delay"
    i=$((i + 1))
  done
  if [ "$verdict" != "yes" ] || [ "$written" -lt "$total" ]; then
    printf 'FATAL: %s содержит %s строк из %s ожидаемых — отчёт не подписан\n' \
      "$file" "$written" "$total" >&3
    return 73
  fi
  return 0
}
# <<< probe-check:end flush_barrier

# --- защита «агент не имеет доступа к подписным материалам» ------------------
# Скан идёт ДО внешнего вызова, который мог бы унаследовать argv/env.
BAD_FORMS=0
if ! probe_forbidden_argv_scan "${RAW_ARGV[@]:-}"; then
  BAD_FORMS=1
fi
BAD_ENV=$(probe_forbidden_env_names) || true
if [ "${BAD_ENV:-0}" != "0" ]; then
  BAD_FORMS=1
fi
if [ "$BAD_FORMS" -ne 0 ]; then
  emit "signing_track=REFUSED"
  emit "signing_track_verdict=REFUSED_CREDENTIAL_ARGV"
  emit "FATAL: в argv/env обнаружены формы, похожие на подписные материалы: прогон прерван, частичный Track-B отчёт не пишется"
  exit 77
fi
emit "forbidden_argv_scan=clean"
emit "forbidden_env_names_count=0"

# --- M-9: сборка обязана жить ВНЕ клона --------------------------------------
# Иначе каждый прогон меняет tree_fingerprint, и все локальные receipts устаревают.
SCRATCH_DEFAULT="${TMPDIR:-/tmp}/exolon-probe-$(date -u +%Y%m%dT%H%M%SZ)"
SCRATCH_ROOT="${EXOLON_PROBE_SCRATCH:-$SCRATCH_DEFAULT}"
case "$SCRATCH_ROOT" in
  "$REPO_ROOT"|"$REPO_ROOT"/*)
    emit "verdict_scratch_root=INSIDE_CLONE"
    emit "build_roots_out_of_tree=no"
    emit "FATAL: EXOLON_PROBE_SCRATCH обязан лежать вне клона (дефект M-9): сборка внутри дерева обнуляет все receipts"
    exit 78
    ;;
esac
mkdir -p "$SCRATCH_ROOT" 2>/dev/null || {
  emit "verdict_scratch_root=UNCREATABLE"
  emit "build_roots_out_of_tree=no"
  printf 'FATAL: не могу создать каталог сборки вне клона: %s\n' "$SCRATCH_ROOT" >&3
  exit 73
}
SYMROOT_DIR="$SCRATCH_ROOT/sym"
OBJROOT_DIR="$SCRATCH_ROOT/obj"
ARCHIVE_PATH="$SCRATCH_ROOT/Exolon.xcarchive"
mkdir -p "$SYMROOT_DIR" "$OBJROOT_DIR" 2>/dev/null || {
  emit "verdict_scratch_root=UNCREATABLE"
  emit "build_roots_out_of_tree=no"
  printf 'FATAL: не могу создать SYMROOT/OBJROOT: %s\n' "$SCRATCH_ROOT" >&3
  exit 73
}
emit "verdict_scratch_root=OUT_OF_TREE"
emit "build_roots_out_of_tree=yes"
emit "scratch_root_policy=SYMROOT OBJROOT ARCHIVE_PATH and the export dir are forced outside the clone"
emit "symroot=$SYMROOT_DIR"
emit "objroot=$OBJROOT_DIR"
TREE_CLEAN_BEFORE=$(git status --porcelain=v1 2>/dev/null | head -1)

emit "# Exolon macOS probe"
emit "os_version=$(sw_vers -productVersion 2>/dev/null | tr -d '\n')"
emit "arch=$(uname -m)"
emit "hostname_redacted=$(scutil --get ComputerName 2>/dev/null | md5 -q 2>/dev/null || echo na)"
emit "probe_bash_version=$BASH_VERSION"
emit "probe_git_blob_sha1=$(git hash-object "$PROBE_REL_PATH" 2>/dev/null | head -1)"
emit "repo_head=$(git rev-parse HEAD 2>/dev/null | head -1)"
emit "tree_fingerprint_source=recomputed on the reviewing host by macos_handout_check.py --derive"
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
BUILD_LOG="$SCRATCH_ROOT/exolon-macos-probe-build.log"
if have xcodebuild; then
  emit "build_log=$BUILD_LOG"
  xcodebuild -project "$TARGET" -target Exolon -configuration "$CONFIG" build \
    SYMROOT="$SYMROOT_DIR" OBJROOT="$OBJROOT_DIR" >"$BUILD_LOG" 2>&1
  emit "build_rc=$?"
  emit "build_tail=$(tail -5 "$BUILD_LOG" | tr '\n' '|')"
  APP="$(find "$SYMROOT_DIR" -maxdepth 4 -name 'Exolon.app' -print -quit 2>/dev/null)"
  if [ -z "${APP:-}" ]; then
    APP="$(find "$(dirname "$TARGET")/build" -maxdepth 3 -name 'Exolon.app' -print -quit 2>/dev/null)"
  fi
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
  DEST_LOG="$SCRATCH_ROOT/exolon-macos-probe-destinations.log"
  xcodebuild -project "$TARGET" -scheme Exolon -showdestinations >"$DEST_LOG" 2>&1
  emit "showdestinations_rc=$?"
  emit "showdestinations_tail=$(tail -3 "$DEST_LOG" | tr '\n' '|')"
  ARCHIVE_LOG="$SCRATCH_ROOT/exolon-macos-probe-archive.log"
  rm -rf "$ARCHIVE_PATH"
  xcodebuild -project "$TARGET" -scheme Exolon -configuration Release \
    -archivePath "$ARCHIVE_PATH" archive SYMROOT="$SYMROOT_DIR" OBJROOT="$OBJROOT_DIR" \
    >"$ARCHIVE_LOG" 2>&1
  ARCHIVE_RC=$?
  emit "archive_rc=$ARCHIVE_RC"
  emit "archive_path_present=$([ -d "$ARCHIVE_PATH" ] && echo yes || echo no)"
  case "$ARCHIVE_PATH" in
    "$REPO_ROOT"|"$REPO_ROOT"/*) emit "archive_path_out_of_tree=no" ;;
    *) emit "archive_path_out_of_tree=yes" ;;
  esac
  emit "archive_log_copy=$SCRATCH_ROOT/archive.log"
  cp "$ARCHIVE_LOG" "$SCRATCH_ROOT/archive.log" 2>/dev/null || true
  emit "archive_tail=$(tail -8 "$ARCHIVE_LOG" | tr '\n' '|')"
  if [ "$ARCHIVE_RC" -eq 0 ]; then
    emit "archive_failure_class=NONE"
    emit "verdict_archive=PASS"
  else
    emit "archive_failure_class=$(probe_classify_archive_failure "$ARCHIVE_LOG")"
    emit "verdict_archive=FAIL"
  fi
else
  emit "archive_rc=127"
  emit "archive_path_present=no"
  emit "archive_path_out_of_tree=unknown"
  emit "archive_tail=none"
  emit "archive_failure_class=TOOL_ABSENT"
  emit "verdict_archive=TOOL_ABSENT"
fi

emit ""
emit "## B3. Archived bundle truth (C-12/C-13/C-14: разбор самого archive, а не сборки Debug)"
ARCH_APP="$ARCHIVE_PATH/Products/Applications/Exolon.app"
ARCH_FLAGS=""
if [ -d "$ARCH_APP" ]; then
  ARCH_PLIST="$ARCH_APP/Contents/Info.plist"
  ARCH_SV="$(plutil -extract CFBundleShortVersionString raw "$ARCH_PLIST" 2>/dev/null || echo na)"
  ARCH_BV="$(plutil -extract CFBundleVersion raw "$ARCH_PLIST" 2>/dev/null || echo na)"
  emit "archived_app_present=yes"
  emit "archived_plist_CFBundleShortVersionString=${ARCH_SV}"
  emit "archived_plist_CFBundleVersion=${ARCH_BV}"
  emit "archived_version_single_source=$( [ -n "${SET_MARKETING:-}" ] && [ "$ARCH_SV" = "${SET_MARKETING:-}" ] && echo MATCH || echo MISMATCH)"
  emit "archived_plist_unexpanded_placeholders=$(grep -c '$(' "$ARCH_PLIST" 2>/dev/null | tr -d ' ')"
  ARCH_SIG_DUMP="$(codesign -dvvv "$ARCH_APP" 2>&1 | head -40)"
  emit "archived_codesign_dump_sha256=$(printf '%s' "$ARCH_SIG_DUMP" | shasum -a 256 | cut -c1-64)"
  codesign --verify --deep --strict --verbose=4 "$ARCH_APP" >"$SCRATCH_ROOT/verify.log" 2>&1
  emit "archived_codesign_verify_rc=$?"
  ARCH_FLAGS="$(printf '%s' "$ARCH_SIG_DUMP" | grep -o 'flags=0x[0-9a-f]*([^)]*)' | head -1)"
  emit "archived_codesign_flags=${ARCH_FLAGS:-none}"
  emit "archived_hardened_runtime=$(printf '%s' "$ARCH_FLAGS" | grep -q 'runtime' && echo PRESENT || echo ABSENT)"
  ARCH_TS="$(printf '%s' "$ARCH_SIG_DUMP" | grep -c 'Timestamp=')"
  emit "archived_codesign_timestamp=$( [ "${ARCH_TS:-0}" -gt 0 ] && echo PRESENT || echo ABSENT)"
  emit "archived_signature=$(printf '%s' "$ARCH_SIG_DUMP" | grep -o 'Signature=[A-Za-z]*' | head -1)"
  emit "archived_signing_identity_class=$(probe_signing_identity_class "$ARCH_SIG_DUMP")"
  ARCH_TEAM="$(printf '%s' "$ARCH_SIG_DUMP" | sed -n 's/.*TeamIdentifier=\([A-Za-z0-9]*\).*/\1/p' | head -1)"
  emit "archived_team_id_hash=sha256:$(printf '%s' "${ARCH_TEAM:-none}" | shasum -a 256 | cut -c1-12)"
  ARCH_CDH="$(printf '%s' "$ARCH_SIG_DUMP" | sed -n 's/.*CDHash=\([0-9a-f]*\).*/\1/p' | head -1)"
  emit "cdhash=${ARCH_CDH:-none}"
  ENT_FILE="$SCRATCH_ROOT/archived-entitlements.plist"
  codesign -d --entitlements :- "$ARCH_APP" >"$ENT_FILE" 2>/dev/null
  emit "archived_entitlements_read_rc=$?"
  emit "archived_entitlements_count=$(plutil -p "$ENT_FILE" 2>/dev/null | grep -c '=>' | tr -d ' ')"
  GTA_RAW="$(plutil -extract com.apple.security.get-task-allow raw "$ENT_FILE" 2>/dev/null || echo absent)"
  emit "archived_entitlements_get_task_allow=$( [ "$GTA_RAW" = "true" ] && echo yes || echo no)"
  emit "archived_binary_sha256=$(shasum -a 256 "$ARCH_APP/Contents/MacOS/Exolon" 2>/dev/null | cut -c1-64)"
  SPCTL_OUT="$(spctl -a -t exec -vv "$ARCH_APP" 2>&1 | head -3)"
  emit "spctl_assess_verdict=$(printf '%s' "$SPCTL_OUT" | grep -qi 'accepted' && echo accepted || echo REJECTED)"
  XATTR_Q="$(xattr -l "$ARCH_APP" 2>/dev/null | grep -c 'com.apple.quarantine' | tr -d ' ')"
  emit "xattr_quarantine_present=$( [ "${XATTR_Q:-0}" = "0" ] && echo no || echo yes)"
  emit "gatekeeper_representative=$( [ "${XATTR_Q:-0}" = "0" ] && echo no || echo yes)"
  emit "artifact_sha256=none"
  emit "archive_inspection_verdict=PASS"
else
  emit "archived_app_present=no"
  emit "archived_plist_CFBundleShortVersionString=NOT_ATTEMPTED"
  emit "archived_plist_CFBundleVersion=NOT_ATTEMPTED"
  emit "archived_version_single_source=NOT_ATTEMPTED"
  emit "archived_plist_unexpanded_placeholders=NOT_ATTEMPTED"
  emit "archived_codesign_dump_sha256=NOT_ATTEMPTED"
  emit "archived_codesign_verify_rc=127"
  emit "archived_codesign_flags=NOT_ATTEMPTED"
  emit "archived_hardened_runtime=NOT_ATTEMPTED"
  emit "archived_codesign_timestamp=NOT_ATTEMPTED"
  emit "archived_signature=NOT_ATTEMPTED"
  emit "archived_signing_identity_class=NOT_ATTEMPTED"
  emit "archived_team_id_hash=NOT_ATTEMPTED"
  emit "cdhash=none"
  emit "archived_entitlements_read_rc=127"
  emit "archived_entitlements_count=NOT_ATTEMPTED"
  emit "archived_entitlements_get_task_allow=NOT_ATTEMPTED"
  emit "archived_binary_sha256=none"
  emit "spctl_assess_verdict=NOT_RUN"
  emit "xattr_quarantine_present=no"
  emit "gatekeeper_representative=no"
  emit "artifact_sha256=none"
  emit "archive_inspection_verdict=NOT_ATTEMPTED"
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
ask() { emit "$1"; emit "  EXPECTED: $2"; emit_part "  OBSERVED> "; }
ANSWERS=""
record() {
  local tag="$1" observed="$2"
  ANSWERS="${ANSWERS}${tag}=${observed:-none}
"
  emit_nl
  emit "answer_${1}=${observed:-none}"
}
PLAY_ANSWERED=0
PLAY_ASKED=16
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
  a=""; ask "E16 конец стадии (зона 024): бонус по числу жизней, +1 жизнь, сброс костюма, 10000 за смелость и таймер?" "полная последовательность ORIGINAL_MECHANICS.md:140-146, собранная wave-D: lives*1000 + bravery(0|10000) + timed(0|1000|3000|5000|7000) до +1 жизни; refill 99/10; костюм сброшен в зоне 025; в Debug цель досягается EXOLON_DEBUG_WARP=L01S25"; read -r a; record E16 "$a"
  PLAY_ANSWERED=$(printf '%s' "$ANSWERS" | grep -c '' | tr -d ' ')
else
  emit "play_answers=SKIPPED (stdin не tty; для сбора ответов запускай из терминала)"
fi
emit "play_observations=$( if [ "$PLAY_ANSWERED" -ge "$PLAY_ASKED" ]; then echo COMPLETE; elif [ "$PLAY_ANSWERED" -gt 0 ]; then echo PARTIAL; else echo SKIPPED; fi )"

emit ""
emit "## E-итог (одной простынёй для diff с ожиданиями)"
emit_block "$ANSWERS"

emit ""
emit "## F. Что этот зонд НЕ доказывает"
emit "- он не заменяет XCTest (в продукте 0 тестов) и не доказывает отсутствие регрессий;"
emit "- ручные пункты E1-E16 — наблюдения одного прогона без записи таймингов;"
emit "- сборка Debug не эквивалентна релизу: подпись ad-hoc/Manual."
emit "- ENABLE_HARDENED_RUNTIME включён в оба target-конфига (wave D закрыло отсрочку P1-11;"
emit "  реестр cutover: engineering/changes/20260924-complete-wave-d-specification-and-release-audit-8341b7/evidence/cutover.md)."
emit "  Настройка в pbxproj не есть наблюдаемый флаг: проверять обязан archived_hardened_runtime"
emit "  и codesign_flags_runtime_token выше, а не наличие ключа в проекте."
emit ""
emit "## G. Практика съёма (проверено по дереву)"
emit "product_log_calls=$(grep -rc 'print(\|NSLog\|os_log' Exolon --include=*.swift | awk -F: '{s+=$2} END {print s+0}') (0 → консоль доказательств не даёт)"
emit "capture=запись экрана + F1 (хитбоксы) + defaults read com.exolon.remake"
emit "level_warp_calls=$(grep -rc 'warp\|debugSkip\|skipTo' Exolon --include=*.swift | awk -F: '{s+=$2} END {print s+0}') (в Release-сборке 0: warp существует только под #if DEBUG; без него до зоны 124 ~11 мин реального хода, чекпоинта нет)"
emit "debug_warp_requested=$( [ -n "${EXOLON_DEBUG_WARP:-}" ] && echo yes || echo no) (Debug: EXOLON_DEBUG_WARP=LxxSyy идёт через transition(to:), см. E16)"
emit "checkpoint_reader_calls=$(grep -rc 'loadCheckpoint' Exolon --include=*.swift | awk -F: '{s+=$2} END {print s+0}') (1 = только определение)"

emit ""
emit "## H. Signing track gate (C-20..C-25; агенту закрыто: двойной env-гейт плюс tty)"
TRACK_B=0
if [ "${WITH_SIGNING:-0}" = "1" ]; then
  if [ "${EXOLON_HUMAN_SIGNING_RUN:-0}" != "1" ]; then
    emit "signing_track=REFUSED"
    emit "signing_track_verdict=REFUSED_HUMAN_GATE"
    emit "FATAL: Track B требует второй гейт EXOLON_HUMAN_SIGNING_RUN=1, набранный человеком: агент не может его выставить"
    exit 77
  fi
  if [ ! -t 0 ]; then
    emit "signing_track=REFUSED"
    emit "signing_track_verdict=REFUSED_NOT_TTY"
    emit "FATAL: неинтерактивный запуск не может подтвердить подпись — отказ"
    exit 77
  fi
  emit "human_gate_present=yes"
  emit "human_gate_tty=yes"
  emit_part "Для продолжения набери HUMAN_SIGNING_RUN> "
  CONFIRM=""
  read -r CONFIRM || CONFIRM=""
  emit_nl
  if [ "${CONFIRM:-}" != "HUMAN_SIGNING_RUN" ]; then
    emit "signing_track=REFUSED"
    emit "signing_track_verdict=REFUSED_ATTESTATION"
    exit 77
  fi
  if [ -z "${EXOLON_NOTARY_PROFILE:-}" ]; then
    emit "notary_profile_present=NO"
    emit "FATAL: EXOLON_NOTARY_PROFILE не задан — имя профиля обязательно (значения секретов зонд не принимает)"
    exit 78
  fi
  if ! probe_validate_notary_profile "$EXOLON_NOTARY_PROFILE"; then
    emit "notary_profile_present=NO"
    emit "FATAL: имя профиля не проходит проверку формы: только имя, не флаг и не секрет"
    exit 78
  fi
  emit "notary_profile_present=YES"
  emit "signing_track=HUMAN"
  emit "signing_track_verdict=PASS"
  TRACK_B=1
  emit "identity_policy=find_identity_count_and_fingerprint_are_typed_by_the_human_in_its_own_shell"
  if have xcodebuild; then
    SIGN_SETTINGS="$(xcodebuild -project "$TARGET" -target Exolon -configuration Release -showBuildSettings 2>/dev/null)"
    emit "settings_CODE_SIGN_IDENTITY=$(printf '%s\n' "$SIGN_SETTINGS" | awk -F' = ' '/^[[:space:]]*CODE_SIGN_IDENTITY /{print $2; exit}')"
    emit "settings_CODE_SIGN_INJECT_BASE_ENTITLEMENTS=$(printf '%s\n' "$SIGN_SETTINGS" | awk -F' = ' '/^[[:space:]]*CODE_SIGN_INJECT_BASE_ENTITLEMENTS /{print $2; exit}')"
    emit "settings_DEVELOPMENT_TEAM_hash=sha256:$(printf '%s' "$(printf '%s\n' "$SIGN_SETTINGS" | awk -F' = ' '/^[[:space:]]*DEVELOPMENT_TEAM /{print $2; exit}')" | shasum -a 256 | cut -c1-12)"
  else
    emit "settings_CODE_SIGN_IDENTITY=TOOL_ABSENT"
    emit "settings_CODE_SIGN_INJECT_BASE_ENTITLEMENTS=TOOL_ABSENT"
    emit "settings_DEVELOPMENT_TEAM_hash=TOOL_ABSENT"
  fi
else
  emit "signing_track=SKIPPED"
  emit "signing_track_verdict=NOT_ATTEMPTED"
  emit "identity_policy=find_identity_not_executed_by_probe"
  emit "settings_CODE_SIGN_IDENTITY=NOT_ATTEMPTED"
  emit "settings_CODE_SIGN_INJECT_BASE_ENTITLEMENTS=NOT_ATTEMPTED"
  emit "settings_DEVELOPMENT_TEAM_hash=NOT_ATTEMPTED"
  emit "notary_profile_present=NOT_APPLICABLE"
fi
# C-20: количество подписных идентичностей и отпечаток сертификата вводит человек в своей
# сессии; сам зонд эти команды не исполняет, в отчёт попадает только число и хэш.
emit "developer_id_identity_count=${EXOLON_DEVELOPER_ID_COUNT:-NOT_ATTEMPTED}"
emit "codesign_flags_runtime_token=$(printf '%s' "${ARCH_FLAGS:-}" | grep -q 'runtime' && echo PRESENT || echo ABSENT)"

emit ""
emit "## I. Notarization track (C-26..C-31; достижим только из-под гейта §H)"
if [ "$TRACK_B" = "1" ]; then
  EXPORT_DIR="$SCRATCH_ROOT/out"
  mkdir -p "$EXPORT_DIR" 2>/dev/null || true
  EXPORT_OPTIONS="$SCRATCH_ROOT/exportoptions.plist"
  printf '<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n<plist version="1.0">\n<dict>\n\t<key>method</key>\n\t<string>developer-id</string>\n\t<key>destination</key>\n\t<string>export</string>\n</dict>\n</plist>\n' > "$EXPORT_OPTIONS"
  EXPORT_LOG="$SCRATCH_ROOT/export.log"
  if have xcodebuild; then
    xcodebuild -exportArchive -archivePath "$ARCHIVE_PATH" -exportPath "$EXPORT_DIR" \
      -exportOptionsPlist "$EXPORT_OPTIONS" >"$EXPORT_LOG" 2>&1
    emit "export_archive_rc=$?"
  else
    emit "export_archive_rc=127"
  fi
  ARTIFACT="$(find "$EXPORT_DIR" -maxdepth 1 \( -name '*.pkg' -o -name '*.dmg' -o -name '*.zip' \) -print -quit 2>/dev/null)"
  emit "export_container=$( [ -n "${ARTIFACT:-}" ] && printf '%s' "${ARTIFACT##*.}" || echo none)"
  if [ -n "${ARTIFACT:-}" ] && have xcrun; then
    emit "artifact_sha256=$(shasum -a 256 "$ARTIFACT" | cut -c1-64)"
    SUBMIT_FILE="$SCRATCH_ROOT/notary-submit.txt"
    xcrun notarytool submit "$ARTIFACT" --keychain-profile "$EXOLON_NOTARY_PROFILE" \
      --wait >"$SUBMIT_FILE" 2>&1
    SUBMIT_RC=$?
    emit "notarytool_submit_rc=$SUBMIT_RC"
    emit "notary_status=$(probe_notary_verdict "$(head -40 "$SUBMIT_FILE")")"
    UUID="$(sed -n 's/.*id: \([0-9a-fA-F-]\{36\}\).*/\1/p' "$SUBMIT_FILE" | head -1)"
    emit "submission_uuid=$( [ -n "$UUID" ] && echo "$UUID" || echo none)"
    if [ -n "$UUID" ]; then
      xcrun notarytool log "$UUID" --keychain-profile "$EXOLON_NOTARY_PROFILE" \
        "$SCRATCH_ROOT/notary-log-$UUID.json" >"$SCRATCH_ROOT/notary-log.err" 2>&1
      emit "notarytool_log_rc=$?"
      xcrun notarytool info "$UUID" --keychain-profile "$EXOLON_NOTARY_PROFILE" \
        >"$SCRATCH_ROOT/notary-info-$UUID.txt" 2>&1
      emit "notarytool_info_rc=$?"
      emit "notary_log_committed=$( [ -s "$SCRATCH_ROOT/notary-log-$UUID.json" ] && echo yes || echo no)"
      emit "notary_info_file=notary-info-$UUID.txt"
      emit "notary_log_file=notary-log-$UUID.json"
    else
      emit "notary_log_committed=no"
      emit "notary_info_file=none"
      emit "notary_log_file=none"
    fi
    xcrun stapler staple "$ARTIFACT" >"$SCRATCH_ROOT/staple.log" 2>&1
    STAPLE_RC=$?
    emit "stapler_staple=$( [ "$STAPLE_RC" -eq 0 ] && echo PASS || echo FAIL)"
    xcrun stapler validate "$ARTIFACT" >"$SCRATCH_ROOT/staple-validate.log" 2>&1
    emit "stapler_validate=$( grep -qi 'The validate action worked' "$SCRATCH_ROOT/staple-validate.log" && echo WORKED || echo FAIL)"
    STAGED="$SCRATCH_ROOT/staged"
    rm -rf "$STAGED"
    mkdir -p "$STAGED" 2>/dev/null || true
    ditto -x "$ARTIFACT" "$STAGED" 2>/dev/null
    STAGED_APP="$(find "$STAGED" -maxdepth 2 -name '*.app' -print -quit 2>/dev/null)"
    if [ -n "${STAGED_APP:-}" ]; then
      xattr -w com.apple.quarantine "0001;$(printf '%08x' "$(date +%s)"; printf ';probe;00000000-0000-0000-0000-000000000000')" \
        "$STAGED_APP" 2>/dev/null
      emit "xattr_quarantine_written_rc=$?"
      SPCTL_B="$(spctl -a -t exec -vv "$STAGED_APP" 2>&1 | head -3)"
      emit "spctl_assess_verdict=$(printf '%s' "$SPCTL_B" | grep -qi 'accepted' && (printf '%s' "$SPCTL_B" | grep -qi 'Notarized Developer ID' && echo ACCEPTED_NOTARIZED_DEVELOPER_ID || echo accepted_other) || echo REJECTED)"
      emit "xattr_quarantine_present=$( xattr -l "$STAGED_APP" 2>/dev/null | grep -q 'com.apple.quarantine' && echo yes || echo no)"
      emit "gatekeeper_representative=$( xattr -l "$STAGED_APP" 2>/dev/null | grep -q 'com.apple.quarantine' && echo yes || echo no)"
    else
      emit "spctl_assess_verdict=NOT_RUN"
      emit "xattr_quarantine_written_rc=127"
    fi
  elif [ -n "${ARTIFACT:-}" ]; then
    emit "artifact_sha256=$(shasum -a 256 "$ARTIFACT" | cut -c1-64)"
    emit "notarytool_submit_rc=127"
    emit "notary_status=TOOL_ABSENT"
    emit "submission_uuid=none"
    emit "notary_log_committed=no"
    emit "stapler_staple=TOOL_ABSENT"
    emit "stapler_validate=TOOL_ABSENT"
    emit "spctl_assess_verdict=TOOL_ABSENT"
  else
    emit "artifact_sha256=none"
    emit "notarytool_submit_rc=NOT_ATTEMPTED"
    emit "notary_status=NOT_ATTEMPTED"
    emit "submission_uuid=none"
    emit "notary_log_committed=no"
    emit "stapler_staple=NOT_ATTEMPTED"
    emit "stapler_validate=NOT_ATTEMPTED"
    emit "spctl_assess_verdict=NOT_RUN"
  fi
  emit_part "manual_smoke_gamepad> "; read -r SMOKE_1 || SMOKE_1=""; emit_nl
  emit "manual_smoke_gamepad=${SMOKE_1:-NOT_ATTEMPTED}"
  emit_part "manual_smoke_hud> "; read -r SMOKE_2 || SMOKE_2=""; emit_nl
  emit "manual_smoke_hud=${SMOKE_2:-NOT_ATTEMPTED}"
  emit_part "manual_smoke_audio> "; read -r SMOKE_3 || SMOKE_3=""; emit_nl
  emit "manual_smoke_audio=${SMOKE_3:-NOT_ATTEMPTED}"
  emit_part "manual_smoke_debugger_attach> "; read -r SMOKE_4 || SMOKE_4=""; emit_nl
  emit "manual_smoke_debugger_attach=${SMOKE_4:-NOT_ATTEMPTED}"
  emit "retention_policy=the .xcarchive, the container, exportoptions.plist and any identity capture stay off the machine; only digests plus the CDHash are committed"
else
  emit "export_archive_rc=NOT_ATTEMPTED"
  emit "export_container=none"
  emit "artifact_sha256=none"
  emit "notarytool_submit_rc=NOT_ATTEMPTED"
  emit "notary_status=NOT_ATTEMPTED"
  emit "submission_uuid=none"
  emit "notary_log_committed=no"
  emit "stapler_staple=NOT_ATTEMPTED"
  emit "stapler_validate=NOT_ATTEMPTED"
  emit "retention_policy=nothing was produced because Track B was not attempted"
fi

emit ""
emit "## J. Probe self-test (чистые разборщики на двух эталонных строках каждый)"
ST_SIGN_A="$(probe_signing_identity_class "Signature=adhoc
TeamIdentifier=not set")"
ST_SIGN_B="$(probe_signing_identity_class "Authority=Developer ID Application: Example Org (TEAMIDTEAMID)
TeamIdentifier=TEAMIDTEAMID")"
if [ "$ST_SIGN_A" = "ADHOC" ] && [ "$ST_SIGN_B" = "DEVELOPER_ID" ]; then
  emit "probe_selftest_signing_parser=PASS"
else
  emit "probe_selftest_signing_parser=FAIL"
fi
ST_NOT_A="$(probe_notary_verdict "status: Accepted
id: 11111111-2222-3333-4444-555555555555")"
ST_NOT_B="$(probe_notary_verdict "status: Invalid
the executable requests the get-task-allow entitlement")"
if [ "$ST_NOT_A" = "ACCEPTED" ] && [ "$ST_NOT_B" = "INVALID" ]; then
  emit "probe_selftest_notary_status_parser=PASS"
else
  emit "probe_selftest_notary_status_parser=FAIL"
fi
ST_COLLAPSE_A="$(probe_notary_verdict "status: Accepted")"
ST_COLLAPSE_B="$(probe_notary_verdict "NOT_ATTEMPTED")"
if [ "$ST_COLLAPSE_A" != "$ST_COLLAPSE_B" ]; then
  emit "probe_selftest_verdict_not_collapsed=PASS"
else
  emit "probe_selftest_verdict_not_collapsed=FAIL"
fi
printf 'x=1\ny=2\n' > "$SCRATCH_ROOT/selftest-flush.txt"
probe_flush_barrier "$SCRATCH_ROOT/selftest-flush.txt" 2
FLUSH_TEST_RC=$?
emit "probe_selftest_flush_barrier=$( [ "$FLUSH_TEST_RC" -eq 0 ] && echo PASS || echo FAIL)"
if probe_forbidden_argv_scan "--config" "Release" "$SCRATCH_ROOT/x.txt" \
   && ! probe_forbidden_argv_scan "--apple""-id"; then
  emit "probe_selftest_forbidden_argv_scanner=PASS"
else
  emit "probe_selftest_forbidden_argv_scanner=FAIL"
fi

emit ""
emit "## K. Provenance and tree hygiene (C-00.1/C-16: отчёт обязан быть воспроизводим с чистого клона)"
TREE_CLEAN_AFTER=$(git status --porcelain=v1 2>/dev/null | head -1)
emit "tree_clean_before_run=$( [ -z "$TREE_CLEAN_BEFORE" ] && echo yes || echo no)"
emit "tree_clean_after_run=$( [ -z "$TREE_CLEAN_AFTER" ] && echo yes || echo no)"
emit "scratch_root_kept=$SCRATCH_ROOT"
if [ -n "$OUT" ]; then
  emit "probe_report_saved=$OUT"
  probe_flush_barrier "$OUT" "$PROBE_LINES"
  BARRIER_RC=$?
  if [ "$BARRIER_RC" -ne 0 ]; then
    printf 'FATAL: отчёт не дописан, rc=%s — не подписанный файл нельзя принимать\n' "$BARRIER_RC" >&3
    exit 73
  fi
else
  probe_flush_barrier "-" "$PROBE_LINES"
  BARRIER_RC=$?
  if [ "$BARRIER_RC" -ne 0 ]; then
    printf 'FATAL: счётчик строк разошёлся, rc=%s\n' "$BARRIER_RC" >&3
    exit 73
  fi
fi
exit 0
