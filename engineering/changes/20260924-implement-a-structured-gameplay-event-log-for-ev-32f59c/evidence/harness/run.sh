#!/usr/bin/env bash
# Исполняемый Linux-контур wave A: структурированный журнал событий + четыре исправления
# конечного автомата (P1-9 / P1-4 / P1-8 / P1-6).
#
# Компилирует и запускает НАСТОЯЩИЕ продуктовые файлы (GameConstants, InputState, GameState,
# Player и всё под GameCore/Diagnostics/) за четырёхстрочным стабом CoreGraphics (CGVector).
# SpriteKit не стабится намеренно (integration_architect §1): то, что решает игру, проверяется на
# реальных Foundation-типах, а не на реплике GameScene.
#
# Артефакты (JSONL) пишутся строго ВНЕ клона: непротрекениченный лог внутри дерева обнуляет
# every fingerprint-bound receipt этой маршрутизации (brief ruling 2).
#
# Запуск: ./run.sh                       (артефакты - в ${TMPDIR}/exolon-harness-$$/)
#         ./run.sh | tee last-run.txt    (как в контуре 2026-09-19)
#         EXOLON_HARNESS_OUT=/tmp/dir ./run.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../../../.." && pwd)"
SWIFTC="${SWIFTC:-/opt/swift/usr/bin/swiftc}"
ARTIFACTS="${EXOLON_HARNESS_OUT:-${TMPDIR:-/tmp}/exolon-harness-$$}"

if [ "$(uname -s)" = "Darwin" ]; then
  printf 'FATAL: на macOS этот контур не нужен — собирай таргет Exolon (xcodebuild -project Exolon.xcodeproj -target Exolon -configuration Debug build)\n' >&2
  exit 75
fi
command -v "$SWIFTC" >/dev/null 2>&1 || { printf 'FATAL: нет swiftc (%s)\n' "$SWIFTC" >&2; exit 69; }
[ -d "$ROOT/Exolon/GameCore/Diagnostics" ] || { printf 'FATAL: %s не найден — запускай из клона репозитория\n' "$ROOT/Exolon/GameCore/Diagnostics" >&2; exit 66; }
case "$ARTIFACTS" in
  "$ROOT"/*) printf 'FATAL: каталог артефактов %s лежит внутри клона — логи вне дерева (brief ruling 2)\n' "$ARTIFACTS" >&2; exit 73 ;;
esac
mkdir -p "$ARTIFACTS"
printf 'ARTIFACTS=%s\n' "$ARTIFACTS"

PRODUCT=(
  "$ROOT/Exolon/GameCore/GameConstants.swift"
  "$ROOT/Exolon/GameCore/InputState.swift"
  "$ROOT/Exolon/GameCore/GameState.swift"
  "$ROOT/Exolon/GameCore/Player/Player.swift"
  "$ROOT/Exolon/GameCore/Diagnostics/GameplayEventSink.swift"
  "$ROOT/Exolon/GameCore/Diagnostics/GameplayEventLog.swift"
  "$ROOT/Exolon/GameCore/Diagnostics/FixedTickDriver.swift"
  "$ROOT/Exolon/GameCore/Diagnostics/StageBoundaryLedger.swift"
  "$ROOT/Exolon/GameCore/Diagnostics/LauncherBonusState.swift"
)

printf '\n== 1. стаб модуля CoreGraphics (1-строка + CGVector; логики нет) ==\n'
"$SWIFTC" -emit-module -emit-library -module-name CoreGraphics \
  -emit-module-path "$ARTIFACTS/CoreGraphics.swiftmodule" \
  -o "$ARTIFACTS/libCoreGraphics.so" "$HERE/coregraphics_shim.swift"
printf 'shim built: %s/libCoreGraphics.so\n' "$ARTIFACTS"

printf '\n== 2. сборка контура (-O, как в измерениях M1..M11) ==\n'
"$SWIFTC" -O -I "$ARTIFACTS" -L "$ARTIFACTS" -lCoreGraphics \
  "${PRODUCT[@]}" "$HERE/main.swift" -o "$ARTIFACTS/harness"
printf 'built: %s/harness (%s файлов продукта, без единой правки)\n' "$ARTIFACTS" "${#PRODUCT[@]}"

printf '\n== 3. прогоны: обычный + два варианта с откатанным фиксом ==\n'
# Контрольные варианты обязаны ПЕРЕВОРАЧИВАТЬ предикаты A и B (AC-002/AC-003):
# это тот же собранный продуктовый код с аргументами инициализации, откатывающими фикс.
run_variant() {
  local name="$1" revert="$2" outdir="$3"
  mkdir -p "$outdir"
  printf -- '--- %s (EXOLON_REVERT=%s) -> %s\n' "$name" "${revert:-none}" "$outdir"
  EXOLON_HARNESS_OUT="$outdir" EXOLON_REVERT="${revert:-none}" \
    LD_LIBRARY_PATH="$ARTIFACTS" "$ARTIFACTS/harness"
}
run_variant "fixed" "" "$ARTIFACTS/fixed"
run_variant "revert-p1-9" "p1_9" "$ARTIFACTS/revert-p1-9"
run_variant "revert-p1-8" "p1_8" "$ARTIFACTS/revert-p1-8"

printf '\n== 4. негативный контроль: без стаба сборка обязана упасть ==\n'
if "$SWIFTC" "${PRODUCT[@]}" "$HERE/main.swift" -o "$ARTIFACTS/harness-no-shim" 2>"$ARTIFACTS/no-shim.err"; then
  printf 'FATAL: собралось без стаба — контроль не перевернулся, вывод выше невалиден\n' >&2
  exit 1
fi
printf 'OK: без стаба не собирается (%s)\n' "$(head -1 "$ARTIFACTS/no-shim.err" | cut -c1-90)"

printf '\n== 5. артефакты ==\n'
find "$ARTIFACTS" -name "*.jsonl" -o -name "manifest.json" -o -name "contract.txt" | sort | sed "s|^|  |"
printf 'OK: контур зелёный; артефакты в %s (вне клона)\n' "$ARTIFACTS"
